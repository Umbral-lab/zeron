# A review of PR #21 (worker B): direct SSH transport to owned engines

- Reviewed base: d5ac5ae3 (main)
- Reviewed head: 2d05a2bc7c388b91169dd61f6dff0a7d4b58d6e0 (worker-b/direct-ssh-rpc, 1 commit, 5 files, +665/-0, no Cargo.lock change)
- Reviewer: worker A (david-noether[bot]); author: worker B (umbral-labs-dev[bot])
- Risk: R2 (new outbound SSH transport, authentication, process spawning). B-authored, A-reviewed per AGENTS.md.

## What the change does

Adds crates/rpc/src/ssh.rs: connect_ssh spawns OpenSSH with -W 127.0.0.1:<ipc_port>
(stdio forwarding only) and runs the existing RpcClient websocket over that pipe.
SshConnection owns the child and a pump task; close() and Drop stop the pump,
kill_on_drop plus explicit kill reap the child. Adds a runnable ssh_status example.
Fixes an inherited RpcClient Drop defect: pending subscription senders stayed alive
in Shared when only the reader task was aborted, so subscribers blocked forever.

## Security posture verified by reading the code

- Destination allowlist (ASCII alnum plus ._ - : @ [ ]) rejects option injection,
  leading dashes, empty parts, multiple @, whitespace/newlines/semicolons/subshells;
  ports must be nonzero; token must be non-blank and header-safe before ssh spawns.
- Hard ssh options: BatchMode, StrictHostKeyChecking=yes, VerifyHostKeyDNS=no,
  UpdateHostKeys=no, GlobalKnownHostsFile=none with an enrollment-specific
  UserKnownHostsFile, IdentitiesOnly with -i, publickey-only auth, no agent/X11
  forwarding, ProxyCommand/ProxyJump pinned to none, ControlPath none,
  ClearAllForwardings, ExitOnForwardFailure, ConnectTimeout 10, ConnectionAttempts 1,
  ServerAlive 15x2, terminator -- before the destination.
- Bearer travels only inside the encrypted SSH stream; server-side verification is
  the inherited constant-time bearer comparison (crates/rpc/src/server.rs,
  ipc_auth::constant_time_eq); error text redacts the token.
- No local listener is opened, no vendor relay, no new dependencies, no lockfile edit.

## Tests actually executed on A's host (isolated CARGO_TARGET_DIR /opt/data/home/zeron-target-pr21)

- cargo test --locked -p zeron-rpc at head: 29 lib + 13 integration + 1 + 0, 0 failed;
  2 ignored (the real-OpenSSH fixture test and one inherited ignored test).
- Independent RED reproduction on a throwaway worktree of d5ac5ae3 with only B's
  deterministic drop test copied in: dropping_rpc_client_releases_retained_subscriptions
  FAILED (Elapsed) without the client.rs clear() fix. B's RED/GREEN claim confirmed.
- cargo clippy --locked -p zeron-rpc --all-targets: exit 0. All 20 warnings are in
  files byte-unchanged from base (rpc: device_room.rs:577, ws.rs:72; the rest are
  zeron-sync/zeron-doc dependency-crate warnings from the inherited baseline).
  B's warning inventory matches exactly. No warnings in ssh.rs, tests/ssh.rs, ssh_status.rs.
- rustfmt --edition 2024 --check on all five changed files: clean. git diff --check: clean.
- git diff d5ac5ae3..2d05a2bc -- Cargo.lock: empty (no dependency changes).
- zeron-client --lib and zeron-sync --lib re-run at head on A's host: see PR comment
  for the recorded numbers (run separately due to build time).

## NOT RUN on A's host

- The ignored real-OpenSSH fixture test (tests/ssh.rs real_openssh_...): BLOCKED —
  openssh-server/sshd is not installed on A's host (openssh-client 10.0p1 is present).
  Owner one-package ask: openssh-server. B verified this workflow PASS on B's host
  (full RPC package 43 pass, real sshd + CLI workflow, revocation and reconnect cases).
- UI evidence: NOT RUN (headless host). No UI is touched by this change.

## Findings

- F-A21-1 (notice, non-blocking): the example usage string names the token file
  argument LOCAL_TOKEN_FILE while its doc comment correctly says it must contain the
  REMOTE engine's bearer. Suggest renaming the positional label to REMOTE_IPC_TOKEN_FILE
  in a later A-side CLI slice to avoid operator confusion.
- F-A21-2 (notice, non-blocking): UserKnownHostsFile is quoted as a single ssh-config
  list element; a path containing spaces works in the fixture (OpenSSH respects the
  quotes here) but a comma/space-heavy path could split as a list. A-side enrollment
  should write enrollment known_hosts files under a token-free path without commas.
- F-A21-3 (notice): an established session is not killed by revoking the SSH key;
  explicit close/disconnect is still required. This is documented in the test and is
  accepted inherited SSH semantics, not a defect of this transport.
- No blocking findings. Drop-clear is a strict improvement for all RpcClient users;
  a call in flight during drop now deterministically returns Closed instead of hanging.

## Verdict

APPROVED for integration at exactly d5ac5ae3 -> 2d05a2bc, conditional on the combined
tree re-test at the merge (rpc package suite on the merged tree). Host re-verification
of the real-OpenSSH test is deferred until openssh-server is installed on A's host.
Merging this transport crate does not change product behavior: no non-test caller of
connect_ssh exists yet; the CLI/enrollment slice is separate A-owned work (issue #20).
