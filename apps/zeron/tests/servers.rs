//! Exercise the actual zeron executable. The ignored workflow requires OpenSSH
//! and runs a real, disposable headless engine and loopback SSH server.
#![cfg(unix)]

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Duration;

use serde_json::{Value, json};
use tokio::io::{AsyncBufReadExt, BufReader};

const BIN: &str = env!("CARGO_BIN_EXE_zeron");

fn cli(root: &Path, args: &[&str]) -> std::process::Output {
    Command::new(BIN)
        .args(["server"])
        .args(args)
        .env_clear()
        .env("PATH", "/usr/bin:/bin")
        .env("HOME", root.join("home"))
        .env("ZERON_DATA_DIR", root.join("client data"))
        .env("RUST_LOG", "error")
        .output()
        .unwrap()
}

fn success(output: std::process::Output) -> Value {
    assert!(
        output.status.success(),
        "CLI failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).expect("server commands must emit clean JSON")
}

#[test]
fn offline_list_does_not_start_an_engine_or_create_a_workspace() {
    let root = tempfile::tempdir().unwrap();
    fs_create_home(root.path());
    assert_eq!(success(cli(root.path(), &["list"])), json!([]));
    assert!(!root.path().join("client data").exists());
    let failure = cli(root.path(), &["status", "unknown"]);
    assert!(!failure.status.success());
    assert!(!root.path().join("client data/ipc-token").exists());
}

#[test]
fn commands_are_in_the_app_and_invalid_names_cannot_escape_storage() {
    let root = tempfile::tempdir().unwrap();
    fs_create_home(root.path());
    let help = cli(root.path(), &["--help"]);
    assert!(help.status.success());
    let help = String::from_utf8(help.stdout).unwrap();
    for command in [
        "add",
        "list",
        "status",
        "sessions",
        "connect",
        "disconnect",
        "remove",
    ] {
        assert!(help.contains(command), "missing command {command}");
    }
    assert!(!cli(root.path(), &["status", "../escape"]).status.success());
    assert!(!root.path().join("escape.json").exists());
    assert!(!root.path().join("client data/ipc-token").exists());
}

fn fs_create_home(root: &Path) {
    std::fs::create_dir_all(root.join("home")).unwrap();
}

fn key(path: &Path) {
    let output = Command::new("ssh-keygen")
        .args(["-q", "-t", "ed25519", "-N", "", "-f"])
        .arg(path)
        .output()
        .expect("ssh-keygen required for explicit real-SSH test");
    assert!(output.status.success(), "fixture key generation failed");
}

struct Sshd {
    child: std::process::Child,
    port: u16,
    user: String,
    known_hosts: PathBuf,
    identity: PathBuf,
}
impl Drop for Sshd {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl Sshd {
    async fn start(root: &Path, ipc_port: u16) -> Self {
        key(&root.join("host-key"));
        key(&root.join("client-key"));
        let user = String::from_utf8(Command::new("id").arg("-un").output().unwrap().stdout)
            .unwrap()
            .trim()
            .to_owned();
        let public = std::fs::read_to_string(root.join("client-key.pub")).unwrap();
        std::fs::write(root.join("authorized_keys"), format!(
            "restrict,port-forwarding,permitopen=\"127.0.0.1:{ipc_port}\",command=\"/bin/false\" {public}"
        )).unwrap();
        let reservation = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = reservation.local_addr().unwrap().port();
        let path = root.display();
        std::fs::write(root.join("sshd_config"), format!(
            "Port {port}\nListenAddress 127.0.0.1\nHostKey {path}/host-key\nPidFile {path}/sshd.pid\n\
             AuthorizedKeysFile {path}/authorized_keys\nAllowUsers {user}\n\
             AuthenticationMethods publickey\nPubkeyAuthentication yes\nPasswordAuthentication no\n\
             KbdInteractiveAuthentication no\nUsePAM no\nStrictModes no\nAllowTcpForwarding local\nPermitTTY no\nLogLevel ERROR\n"
        )).unwrap();
        let known_hosts = root.join("known hosts, fixture");
        std::fs::write(
            &known_hosts,
            format!(
                "[127.0.0.1]:{port} {}",
                std::fs::read_to_string(root.join("host-key.pub")).unwrap()
            ),
        )
        .unwrap();
        drop(reservation);
        let program = if Path::new("/usr/sbin/sshd").exists() {
            "/usr/sbin/sshd"
        } else {
            "sshd"
        };
        let child = Command::new(program)
            .args(["-D", "-e", "-f"])
            .arg(root.join("sshd_config"))
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(std::fs::File::create(root.join("sshd.log")).unwrap())
            .spawn()
            .expect("sshd required for explicit real-SSH test");
        let mut server = Self {
            child,
            port,
            user,
            known_hosts,
            identity: root.join("client-key"),
        };
        tokio::time::timeout(Duration::from_secs(3), async {
            loop {
                if let Some(status) = server.child.try_wait().unwrap() {
                    panic!(
                        "fixture sshd exited {status}: {}",
                        std::fs::read_to_string(root.join("sshd.log")).unwrap()
                    );
                }
                if tokio::net::TcpStream::connect(("127.0.0.1", port))
                    .await
                    .is_ok()
                {
                    break;
                }
                tokio::time::sleep(Duration::from_millis(20)).await;
            }
        })
        .await
        .unwrap();
        server
    }

    fn enroll(&self, root: &Path, ipc_port: u16) -> std::process::Output {
        cli(
            root,
            &[
                "add",
                "prod",
                &format!("{}@127.0.0.1", self.user),
                "--remote-ipc-token-file",
                root.join("remote-data/ipc-token").to_str().unwrap(),
                "--ssh-port",
                &self.port.to_string(),
                "--ipc-port",
                &ipc_port.to_string(),
                "--known-hosts",
                self.known_hosts.to_str().unwrap(),
                "--identity",
                self.identity.to_str().unwrap(),
            ],
        )
    }
}

async fn monitor(
    root: &Path,
) -> (
    tokio::process::Child,
    tokio::io::Lines<BufReader<tokio::process::ChildStdout>>,
) {
    let mut process = tokio::process::Command::new(BIN)
        .args(["server", "connect", "prod"])
        .env_clear()
        .env("PATH", "/usr/bin:/bin")
        .env("HOME", root.join("home"))
        .env("ZERON_DATA_DIR", root.join("client data"))
        .env("RUST_LOG", "error")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true)
        .spawn()
        .unwrap();
    let mut lines = BufReader::new(process.stdout.take().unwrap()).lines();
    let line = tokio::time::timeout(Duration::from_secs(20), lines.next_line())
        .await
        .unwrap()
        .unwrap()
        .expect("monitor must report its connection");
    assert_eq!(
        serde_json::from_str::<Value>(&line).unwrap()["status"],
        "connected"
    );
    (process, lines)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
#[ignore = "requires OpenSSH ssh/ssh-keygen/sshd; runs actual headless zeron and CLI"]
async fn real_engine_and_ssh_enrollment_status_monitor_revocation_and_offline() {
    let temp = tempfile::Builder::new()
        .prefix("zeron-server-e2e-")
        .tempdir()
        .unwrap();
    let root = temp.path();
    fs_create_home(root);
    let reservation = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let ipc_port = reservation.local_addr().unwrap().port();
    drop(reservation);
    let log = std::fs::File::create(root.join("engine.log")).unwrap();
    let mut engine = tokio::process::Command::new(BIN)
        .arg("headless")
        .env_clear()
        .env("PATH", "/usr/bin:/bin")
        .env("HOME", root.join("home"))
        .env("ZERON_DATA_DIR", root.join("remote-data"))
        .env("ZERON_IPC_PORT", ipc_port.to_string())
        .env("ZERON_EDGE_URL", "http://127.0.0.1:9")
        .env("ZERON_HARNESS", "mock")
        .env("ZERON_AUTO_UPDATE", "0")
        .env("RUST_LOG", "warn")
        .stdin(Stdio::null())
        .stdout(Stdio::from(log.try_clone().unwrap()))
        .stderr(Stdio::from(log))
        .kill_on_drop(true)
        .spawn()
        .unwrap();
    let token_file = root.join("remote-data/ipc-token");
    tokio::time::timeout(Duration::from_secs(15), async {
        loop {
            if let Some(status) = engine.try_wait().unwrap() {
                panic!(
                    "headless engine exited {status}: {}",
                    std::fs::read_to_string(root.join("engine.log")).unwrap()
                );
            }
            if token_file.exists()
                && tokio::net::TcpStream::connect(("127.0.0.1", ipc_port))
                    .await
                    .is_ok()
            {
                break;
            }
            tokio::time::sleep(Duration::from_millis(25)).await;
        }
    })
    .await
    .expect("actual headless engine must start");
    let bearer = zeron_rpc::ipc_auth::read_token(&token_file)
        .unwrap()
        .unwrap();
    let ready = zeron_rpc::connect_ws(&format!("ws://127.0.0.1:{ipc_port}"), Some(&bearer))
        .await
        .unwrap();
    tokio::time::timeout(
        Duration::from_secs(15),
        ready.call(zeron_rpc::methods::ENGINE_READY, Value::Null),
    )
    .await
    .unwrap()
    .unwrap();
    drop(ready);
    let ssh = Sshd::start(root, ipc_port).await;

    let enrolled = success(ssh.enroll(root, ipc_port));
    assert_eq!(enrolled["status"], "enrolled");
    assert_eq!(enrolled["engine"]["workspaceScope"], "local");
    let record_path = root.join("client data/servers/prod.json");
    let original = std::fs::read(&record_path).unwrap();
    assert!(!String::from_utf8_lossy(&original).contains(&bearer));
    assert!(
        !ssh.enroll(root, ipc_port).status.success(),
        "duplicate enrollment must not overwrite"
    );
    assert_eq!(std::fs::read(&record_path).unwrap(), original);
    assert_eq!(success(cli(root, &["list"]))[0]["name"], "prod");
    assert_eq!(
        success(cli(root, &["status", "prod"]))["status"],
        "reachable"
    );
    assert!(
        success(cli(root, &["sessions", "prod"]))
            .get("sessions")
            .is_some()
    );

    let (mut connected, mut lines) = monitor(root).await;
    let sessions = tokio::time::timeout(Duration::from_secs(3), lines.next_line())
        .await
        .unwrap()
        .unwrap()
        .unwrap();
    assert!(
        serde_json::from_str::<Value>(&sessions)
            .unwrap()
            .get("sessions")
            .is_some()
    );
    // This PID belongs to the child we just spawned and still own.
    unsafe {
        libc::kill(connected.id().unwrap() as libc::pid_t, libc::SIGINT);
    }
    assert!(
        tokio::time::timeout(Duration::from_secs(5), connected.wait())
            .await
            .unwrap()
            .unwrap()
            .success()
    );
    let mut disconnected = false;
    while let Some(line) = lines.next_line().await.unwrap() {
        disconnected |= serde_json::from_str::<Value>(&line).unwrap()["status"] == "disconnected";
    }
    assert!(disconnected);

    let (mut connected, mut lines) = monitor(root).await;
    assert_eq!(
        success(cli(root, &["disconnect", "prod"]))["status"],
        "disconnectRequested"
    );
    assert!(
        tokio::time::timeout(Duration::from_secs(5), connected.wait())
            .await
            .unwrap()
            .unwrap()
            .success()
    );
    let mut saw_disconnect = false;
    while let Some(line) = lines.next_line().await.unwrap() {
        saw_disconnect |= serde_json::from_str::<Value>(&line).unwrap()["status"] == "disconnected";
    }
    assert!(saw_disconnect);
    assert_eq!(
        success(cli(root, &["list"]))[0]["name"],
        "prod",
        "disconnect must retain enrollment"
    );

    let (mut connected, mut lines) = monitor(root).await;
    assert_eq!(success(cli(root, &["remove", "prod"]))["status"], "removed");
    assert!(
        tokio::time::timeout(Duration::from_secs(5), connected.wait())
            .await
            .unwrap()
            .unwrap()
            .success()
    );
    let mut observed_disconnect = false;
    while let Some(line) = lines.next_line().await.unwrap() {
        observed_disconnect |=
            serde_json::from_str::<Value>(&line).unwrap()["status"] == "disconnected";
    }
    assert!(
        observed_disconnect,
        "removing enrollment must disconnect an existing monitor"
    );
    assert!(ssh.identity.exists() && ssh.known_hosts.exists() && token_file.exists());

    success(ssh.enroll(root, ipc_port));
    let good: Value = serde_json::from_slice(&std::fs::read(&record_path).unwrap()).unwrap();
    let mut changed = good.clone();
    changed["engineIdentity"]["deviceId"] = json!("not-the-enrolled-engine");
    std::fs::write(&record_path, serde_json::to_vec(&changed).unwrap()).unwrap();
    let denied = cli(root, &["status", "prod"]);
    assert!(!denied.status.success());
    assert!(String::from_utf8_lossy(&denied.stderr).contains("identity changed"));
    std::fs::write(&record_path, serde_json::to_vec(&good).unwrap()).unwrap();

    let mut wrong_token = bearer.clone();
    wrong_token.replace_range(..1, if bearer.starts_with('0') { "1" } else { "0" });
    zeron_rpc::ipc_auth::write_token(&token_file, &wrong_token).unwrap();
    let denied = cli(root, &["status", "prod"]);
    assert!(!denied.status.success());
    assert!(String::from_utf8_lossy(&denied.stderr).contains("401"));
    assert!(!String::from_utf8_lossy(&denied.stderr).contains(&wrong_token));
    zeron_rpc::ipc_auth::write_token(&token_file, &bearer).unwrap();
    assert_eq!(
        success(cli(root, &["status", "prod"]))["status"],
        "reachable"
    );

    let (mut live_monitor, mut offline_events) = monitor(root).await;
    engine.kill().await.unwrap();
    engine.wait().await.unwrap();
    assert!(
        !tokio::time::timeout(Duration::from_secs(5), live_monitor.wait())
            .await
            .unwrap()
            .unwrap()
            .success()
    );
    let mut saw_offline = false;
    while let Some(event) = offline_events.next_line().await.unwrap() {
        saw_offline |= serde_json::from_str::<Value>(&event).unwrap()["status"] == "disconnected";
    }
    assert!(
        saw_offline,
        "engine loss must be surfaced, never left falsely connected"
    );
    assert!(
        !cli(root, &["status", "prod"]).status.success(),
        "offline server must not become a local fallback"
    );
    assert_eq!(success(cli(root, &["list"]))[0]["name"], "prod");
    success(cli(root, &["remove", "prod"]));
    assert_eq!(success(cli(root, &["list"])), json!([]));
    assert!(
        !root.join("client data/ipc-token").exists(),
        "server commands must never start a local engine"
    );
    println!(
        "actual zeron binary + headless engine + OpenSSH: enrollment, status, sessions, Ctrl-C, revoke, re-enroll, identity/token rejection and offline behavior PASS"
    );
}
