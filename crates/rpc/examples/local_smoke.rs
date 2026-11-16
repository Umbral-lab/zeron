//! Single-device local smoke driver (`scripts/local-offline-smoke.sh` runs it).
//!
//! Connects to one running engine over its localhost IPC port and proves the
//! local core end to end with the deterministic mock harness — no edge, no
//! account, no network:
//!
//! - `run <port> <data_dir> <workspace_dir> <state_file>`: creates a space and
//!   a chat, queues a run, waits for the assistant entry to land `complete`
//!   with the mock transcript and for the session to go idle, then records the
//!   ids in `<state_file>`.
//! - `verify <port> <data_dir> <state_file>`: after an engine restart, proves
//!   the recorded space, chat and completed transcript are still there and
//!   that the run was not executed a second time.
//!
//! Prints `PASS`/`FAIL` lines; exits nonzero on failure.

use std::time::{Duration, Instant};

use zeron_rpc::{RpcClient, connect_ipc, methods};

const STEP_TIMEOUT: Duration = Duration::from_secs(90);
const MOCK_TEXT: &str = "Mock harness reporting in.";

fn fail(message: &str) -> ! {
    eprintln!("FAIL: {message}");
    std::process::exit(1);
}

fn pass(message: &str) {
    println!("PASS: {message}");
}

/// Subscribe to a watch-stream and poll items until `predicate` returns `Some`.
/// A stream that ends is resubscribed (the engine ends watch streams at
/// lifecycle boundaries); the step deadline bounds the whole wait.
async fn wait_stream<T>(
    client: &RpcClient,
    method: &str,
    params: serde_json::Value,
    what: &str,
    mut predicate: impl FnMut(&serde_json::Value) -> Option<T>,
) -> T {
    let deadline = Instant::now() + STEP_TIMEOUT;
    loop {
        let mut rx = match client.subscribe(method, params.clone()).await {
            Ok(rx) => rx,
            Err(err) => fail(&format!("{what}: subscribe {method} failed: {err}")),
        };
        loop {
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                fail(&format!(
                    "{what}: timed out after {}s",
                    STEP_TIMEOUT.as_secs()
                ));
            }
            match tokio::time::timeout(remaining, rx.recv()).await {
                Ok(Some(item)) => {
                    if let Some(found) = predicate(&item) {
                        return found;
                    }
                }
                Ok(None) => {
                    tokio::time::sleep(Duration::from_millis(300)).await;
                    break;
                }
                Err(_) => fail(&format!(
                    "{what}: timed out after {}s",
                    STEP_TIMEOUT.as_secs()
                )),
            }
        }
    }
}

fn apply_transcript_item(
    current: &mut Vec<zeron_doc::SessionMessageEntry>,
    item: &serde_json::Value,
) -> Result<(), String> {
    let frame: zeron_doc::TranscriptFrame =
        serde_json::from_value(item.clone()).map_err(|err| err.to_string())?;
    zeron_doc::apply_transcript_frame(current, frame).map_err(|err| err.to_string())
}

/// Completed assistant entries in the chat that carry the mock transcript.
async fn completed_mock_entries(client: &RpcClient, chat_id: &str, at_least: usize) -> usize {
    let mut transcript = Vec::new();
    wait_stream(
        client,
        methods::WATCH_DOC_MESSAGES,
        serde_json::json!({ "chatId": chat_id }),
        "assistant transcript",
        |item| {
            apply_transcript_item(&mut transcript, item)
                .unwrap_or_else(|err| fail(&format!("assistant transcript: {err}")));
            let complete = transcript
                .iter()
                .filter(|entry| {
                    entry.role == zeron_doc::MessageRole::Assistant
                        && entry.status == Some(zeron_doc::MessageStatus::Complete)
                        && serde_json::to_string(entry)
                            .map(|text| text.contains(MOCK_TEXT))
                            .unwrap_or(false)
                })
                .count();
            (complete >= at_least).then_some(complete)
        },
    )
    .await
}

async fn row_present(client: &RpcClient, method: &str, id: &str, what: &str) {
    wait_stream(client, method, serde_json::json!({}), what, |item| {
        item.as_array()?
            .iter()
            .any(|row| row.get("id").and_then(|v| v.as_str()) == Some(id))
            .then_some(())
    })
    .await;
}

async fn run(client: &RpcClient, workspace_dir: &str, state_file: &str) {
    let device = client
        .call(methods::LOCAL_DEVICE, serde_json::json!({}))
        .await
        .unwrap_or_else(|err| fail(&format!("LocalDevice: {err}")));
    let device_id = device
        .get("deviceId")
        .and_then(|v| v.as_str())
        .unwrap_or_else(|| fail("LocalDevice reply missing deviceId"))
        .to_string();
    pass(&format!(
        "engine answers over local IPC (device {device_id})"
    ));

    // What a viewer does on attach: list each agent's models without forcing
    // a refresh. Whatever the answer, it must not cost an outbound connection
    // (an installed agent CLI contacts its provider when started) — the
    // egress probe around this smoke is the assertion.
    for harness in ["claude-code", "codex", "mock"] {
        let reply = client
            .call(
                methods::LIST_MODELS,
                serde_json::json!({ "harness": harness, "force": false }),
            )
            .await;
        match reply {
            Ok(models) => println!(
                "note: unforced ListModels {harness}: {} rows",
                models.as_array().map_or(0, Vec::len)
            ),
            Err(err) => println!("note: unforced ListModels {harness}: {err}"),
        }
    }

    let space_id = uuid::Uuid::new_v4().to_string();
    client
        .call(
            methods::MUTATE,
            serde_json::json!({
                "op": "createSpace",
                "spaceId": space_id,
                "deviceId": device_id,
                "path": workspace_dir,
            }),
        )
        .await
        .unwrap_or_else(|err| fail(&format!("createSpace: {err}")));
    let chat_id = uuid::Uuid::new_v4().to_string();
    client
        .call(
            methods::MUTATE,
            serde_json::json!({
                "op": "createChat",
                "chatId": chat_id,
                "spaceId": space_id,
                "config": {
                    "harness": "mock",
                    "model": null,
                    "reasoning": null,
                    "sandbox": "workspace-write",
                },
            }),
        )
        .await
        .unwrap_or_else(|err| fail(&format!("createChat: {err}")));
    row_present(client, methods::WATCH_SPACES, &space_id, "space row").await;
    row_present(client, methods::WATCH_CHATS, &chat_id, "chat row").await;
    pass(&format!("space + chat created ({chat_id})"));

    client
        .call(
            methods::QUEUE_COMMAND,
            serde_json::json!({
                "chatId": chat_id,
                "command": {
                    "kind": "run",
                    "messageId": uuid::Uuid::new_v4().to_string(),
                    "request": {
                        "prompt": "local smoke: report in",
                        "model": null,
                        "reasoning": null,
                        "cwd": workspace_dir,
                        "sandbox": "workspace-write",
                        "autoApprove": true,
                        "resume": null,
                    },
                },
            }),
        )
        .await
        .unwrap_or_else(|err| fail(&format!("QueueCommand: {err}")));
    completed_mock_entries(client, &chat_id, 1).await;
    pass("mock run executed locally and landed complete");

    wait_stream(
        client,
        methods::WATCH_SESSIONS,
        serde_json::json!({}),
        "session idle",
        |item| {
            item.as_array()?
                .iter()
                .any(|session| {
                    session.get("chatId").and_then(|v| v.as_str()) == Some(chat_id.as_str())
                        && session.get("status").and_then(|v| v.as_str()) == Some("idle")
                })
                .then_some(())
        },
    )
    .await;
    pass("session went idle");

    let state = serde_json::json!({ "spaceId": space_id, "chatId": chat_id });
    std::fs::write(state_file, state.to_string())
        .unwrap_or_else(|err| fail(&format!("write {state_file}: {err}")));
}

async fn verify(client: &RpcClient, state_file: &str) {
    let raw = std::fs::read_to_string(state_file)
        .unwrap_or_else(|err| fail(&format!("read {state_file}: {err}")));
    let state: serde_json::Value =
        serde_json::from_str(&raw).unwrap_or_else(|err| fail(&format!("parse state: {err}")));
    let id = |key: &str| {
        state
            .get(key)
            .and_then(|v| v.as_str())
            .unwrap_or_else(|| fail(&format!("state file lacks {key}")))
            .to_string()
    };
    let (space_id, chat_id) = (id("spaceId"), id("chatId"));
    row_present(
        client,
        methods::WATCH_SPACES,
        &space_id,
        "space row after restart",
    )
    .await;
    row_present(
        client,
        methods::WATCH_CHATS,
        &chat_id,
        "chat row after restart",
    )
    .await;
    pass("space + chat survived the engine restart");

    let complete = completed_mock_entries(client, &chat_id, 1).await;
    // Give a wrongly re-dispatched run time to show up before counting.
    tokio::time::sleep(Duration::from_secs(5)).await;
    let settled = completed_mock_entries(client, &chat_id, 1).await;
    if complete != 1 || settled != 1 {
        fail(&format!(
            "expected exactly one completed run after restart, saw {complete} then {settled}"
        ));
    }
    pass("completed transcript survived; the run was not executed twice");
}

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let usage = "usage: local_smoke run <port> <data_dir> <workspace_dir> <state_file> | \
                 local_smoke verify <port> <data_dir> <state_file>";
    let (mode, port, data_dir) = match args.as_slice() {
        [mode, port, data_dir, ..] => (
            mode.as_str(),
            port.parse::<u16>().unwrap_or_else(|_| fail(usage)),
            std::path::PathBuf::from(data_dir),
        ),
        _ => fail(usage),
    };
    let client = connect_ipc(port, Some(&data_dir))
        .await
        .unwrap_or_else(|err| fail(&format!("connect ipc :{port}: {err}")));
    match (mode, &args[3..]) {
        ("run", [workspace_dir, state_file]) => run(&client, workspace_dir, state_file).await,
        ("verify", [state_file]) => verify(&client, state_file).await,
        _ => fail(usage),
    }
    println!("PASS: local smoke {mode} complete");
}
