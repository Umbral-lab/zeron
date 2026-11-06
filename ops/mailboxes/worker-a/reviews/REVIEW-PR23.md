# A review record — PR #23 (worker B): zeron server commands

Task: REMOTE-001 CLI slice (issue #20). Worker B authored; worker A reviewed and integrated.
Risk: R2 (new network connections to user-owned machines, credential file handling, persistence, new CLI surface in the shipping app).
Reviewed base: 2184e3e0d76fa3655fb2b5591c283487abc36827 (main at review start)
Reviewed head: c33e2e5723bdad50c4793bd510931568af5e00f6 (branch worker-b/server-cli, merge-base verified equal to the base)
Integrated as: merge d6f882fc5ed18d2e69b82c01441ac197367c4d2e on main (after PR #22 merge 0ae10c5b; ops/worker-b paths are disjoint from this PR's paths)

## What the change does

- New zeron_app::servers module (apps/zeron/src/servers.rs) plus a zeron server subcommand:
  add / list / status / sessions / connect / disconnect / remove.
- Enrollment verifies the remote engine over the integrated zeron_rpc::ssh transport (PR #21),
  pins engineIdentity (deviceId + workspaceScope), stores a private enrollment record
  (owner-only 0600 in an owner-only 0700 registry dir) that references — never copies —
  the remote IPC bearer, known_hosts and identity files.
- Registry writers share one flock and use tempfile atomic persist (noclobber for new
  enrollments), plus an enrollmentId generation so a stale local monitor or a racing
  disconnect cannot resurrect a removed or re-enrolled identity.
- connect maintains a live session monitor; Ctrl-C, explicit disconnect, removal/re-enrollment
  (generation change, polled every 250 ms) or remote closure stop it; no replay, no local fallback.
- Offline commands (list/remove/disconnect) touch no network and never start a local engine.
- desktop becomes a Cargo feature (default); --no-default-features builds the real CLI +
  headless engine without graphics libraries; Appshot and the headed default branch are gated.
- All remote-derived output passes through terminal_safe control/bidi escaping while remaining
  valid JSON.

## Tests actually run on A's host (Debian 13 x86_64, headless)

1. cargo test --locked -p zeron --no-default-features -- --test-threads=1 at the reviewed
   head, isolated CARGO_TARGET_DIR /opt/data/home/zeron-target-pr23: exit 0.
   Counts verified against the log: 13 lib (incl. 9 new servers.rs unit tests) + 8 bin +
   1 background_engine + 1 noop_browser + 2 servers integration offline = 25 pass,
   0 fail, 1 ignored (the real-SSH workflow). Matches B's claimed 25 + 1 ignored.
2. cargo clippy --locked -p zeron --no-default-features --all-targets --no-deps at head:
   exit 0; 4 warnings, all in baseline byte-unchanged files: crates/sync/src/registry.rs:322,
   crates/preview/src/mux.rs:368, crates/engine/src/agent_accounts.rs:3732,
   apps/zeron/build.rs:19 — exactly B's retained inventory. Zero warnings in servers.rs,
   tests/servers.rs or main.rs/lib.rs changes.
3. rustfmt --edition 2024 --check on the four changed Rust files: clean. git diff --check: clean.
   Cargo.lock diff: empty (tempfile was already a workspace pin and a dev-dep here).
4. Default (desktop) build requested by B from A: cargo test --locked -p zeron
   --test servers --test background_engine at the reviewed head on the A host with zeron-ui
   compiled (shared warm target cache): exit 0, servers 2 pass + 1 ignored,
   background_engine 1 pass. This closes B's NOT RUN desktop-build item on A's host.
5. Combined-tree re-run on integrated main d6f882fc: full cargo test --locked -p zeron
   --no-default-features suite re-executed in the isolated target dir: exit 0, aggregated
   25 passed / 0 failed / 1 ignored. ops/worker-b discovery from the #22 merge re-run on
   the same combined tree: 41 ran / 40 pass / 1 inherited httpx test NOT RUN.
6. Headless CLI evidence (A's own grounding on the merged tree, isolated disposable
   ZERON_DATA_DIR under the agent scratch dir, env -i with a fresh HOME):
   server --help shows all seven subcommands; server list prints [] and creates no data
   content; server status ../escape is rejected by the name validator; server status
   unknown fails closed; after all calls the data dir contains only the empty owner-only
   servers registry and zero files — no ipc-token, so no local engine was started.

## NOT RUN (recorded honestly)

- B's ignored real-SSH workflow (actual zeron + actual headless engine + disposable sshd):
  openssh-server is not installed on A's host (openssh-client 10.0p1 only; ssh-keygen exists).
  The owner's one-package ask from last night (openssh-server) is re-confirmed as the only
  blocker for A-host re-verification. B's real-sshd run remains B-host evidence.
- Rendered UI evidence: NOT RUN (headless host). The desktop feature gate changes build
  configuration, not UI behavior; default desktop compile + tests pass on A's host.

## Findings

- F-A23-1 (notice): Registry::list hard-fails if any single enrollment record is corrupt
  (load is not error-tolerant), so one damaged record makes list unusable until manual
  removal. Fail-closed is defensible; note for the future enrollment UI.
- F-A23-2 (notice): disconnect/removal stop local monitors within the 250 ms generation
  poll but do not terminate an already-established SSH session of another live connect
  process faster than that poll, and per F-A21-3 revoking an SSH key never kills an
  established session. Remote authority is the selected SSH account/engine until the
  server-side workspace-grants slice (issue #20 A-side acceptance).
- F-A23-3 (notice): the 64-hex bearer validation in token() rejects a provider API key by
  shape and the error text never echoes the file content (test-verified); enrollment
  records store canonical absolute paths, which is correct but means moving a token file
  breaks the enrollment until re-enroll — acceptable fail-closed behavior.
- No blocking findings. No non-test caller of the registry exists outside the server
  subcommand, so normal app startup behavior is unchanged.

## Verdict

Approved for integration at head c33e2e57 and the exact merged tree d6f882fc
(apps/zeron byte-identical to the reviewed head). Next A-owned work per issue #20:
native enrollment/server-picker UI slice and server-side workspace grants —
not started this night.
