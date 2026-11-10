# REMOTE-002: server-side per-project workspace grants (issue #20 acceptance slice)

Status: prepared locally by worker A on 2026-11-09; not pushed, no PR yet —
the implementation with tests will open the reviewable handoff. Deliberately
not opened as a docs-only PR: candidate-review-v2 skips docs-only candidates
by design, and a crates/ implementation PR opened now would out-rank the
pinned OPS-001B candidate #29 in B's single nightly selection.

Objective: extend merged REMOTE-001 (B's SSH transport, A-side review integrated
in PR #21/PR #23) so an enrolled owned-server session can be limited to specific
project workspaces instead of the whole remote engine.

Grounded source facts (verified by reading current main 1b169f16):
- Remote engine auth is a single all-or-nothing bearer: engine mints
  {data_dir}/ipc-token (crates/rpc/src/ipc_auth.rs issue_token, engine
  crates/engine/src/lib.rs:1147 set_ipc_token_file, :1230 comment) and
  serve_ws_listener/serve_ws_socket (crates/rpc/src/server.rs:145-197)
  accept any connection presenting it — full access to all RPC methods.
- Workspace-scoped methods already identify workspaces as device+folder pairs
  ("Spaces registry (device+folder pairs)", crates/rpc/src/lib.rs:132; the
  device-local workspace filesystem group at lib.rs:193-199).
- Client enrollment already exists: apps/zeron/src/servers.rs stores named,
  owner-only enrollment JSON with enrollmentId identity checks and has
  verify/re-enroll flows (servers.rs:19-46, 111-162). connect_ssh is the only
  transport (crates/rpc/src/ssh.rs, pinned hosts, loopback, bounded handshake).

Named decisions this task must resolve (recommendation, to be tested):
- D1 Enforcement point: remote engine only. Client-side filtering is not a
  security boundary (AGENTS.md: a localhost listener still needs authorization;
  the token grants everything the client can already present).
- D2 Grant store: an owner-only grants file under the remote engine data_dir,
  same write discipline as ipc-token (0600, exclusive create, symlink-safe),
  mapping session/enrollment identity to an allow-set of workspace
  device+folder identities. No grants file = today's behavior, byte-compatible.
- D3 Session binding: scope at bearer presentation — serve_ws_socket binds a
  session capability from the grants file after bearer_matches; workspace-scoped
  dispatch rejects non-granted identities. Alternative rejected: per-method
  re-read of the grants file on every call (no session identity, TOCTOU churn).
- D4 CLI surface: extend the existing servers command family with explicit
  grant add/remove/list on the A side, pushing grant intents to the enrolled
  machine through the already-verified enrollment identity path. Do not create
  a parallel CLI (PR #23 commands stay canonical).

Non-goals: no transport changes (ssh.rs untouched); no vendor relay; no UI
implementation in this task (native enrollment/server-picker UI remains a
separate slice that needs a display path — headless host, evidence NOT RUN).

Acceptance criteria:
1. Default single-user local and default enrolled behavior unchanged when no
   grants file exists (byte-compatible ipc-token path, existing tests pass).
2. Synthetic-fixture rpc tests prove a granted session reaches granted
   workspaces and a non-granted workspace call is refused on the server side.
3. Headless CLI grounding of grant add/remove/list at the apps/zeron level.
4. R2 review: B/Sol review of the exact head before integration; <=12 code
   files so candidate-review-v2 selects it once #29 is decided.

Risk: R2 (authorization enforcement, persistence). Rollback: revert commit;
absence of a grants file restores current semantics.

Open owner-level question recorded here, not decided by A: docs-only PRs #6
and #7 have had zero reviews for 9 nights because candidate-review-v2 skips
docs-only candidates to save model budget. Reviewing them needs either an
owner-approved docs lane in B's controller or owner acceptance that BASE-001/
BASE-003 wait until a code-carrying change touches the same files.

Implementation resolution (worker A, run-2026-11-10, opened as a reviewable PR):
- D1 resolved as recommended: enforcement is entirely server-side. A new
  ScopedRpcService in crates/rpc/src/grants.rs wraps the engine service for
  grant sessions; workspace-targeted calls outside the grant's space allow-set
  are refused with a capability error before the engine sees them, and a
  workspace call the grant cannot identify by space id is also refused.
- D2 resolved with one concrete refinement: the grants file is
  {data_dir}/ipc-grants.json (owner-only 0600 write discipline, exclusive
  create, symlink-safe replace, same as ipc-token), but each grant carries its
  own bearer token bound to an allow-set of workspace space ids (the
  device+folder pair identity the Spaces registry already uses on this fork).
  Absence of the file is byte-compatible today's behavior; the main ipc-token
  keeps full access.
- D3 resolved as recommended: binding happens at bearer presentation in
  serve_ws_socket (main token first, then grant bearers), producing a
  per-session WorkspaceScope. No per-method re-read of the grants file.
  New named behavior beyond the card: if the grants file exists but cannot be
  read or parsed, the handshake refuses every session with 503 (fail closed)
  instead of falling back to full access.
- D4 resolved with a scope limit recorded honestly: the servers CLI now has
  grant-add / grant-list / grant-revoke, and they maintain the grants file of
  the engine on the same host as the CLI (the remote machine runs the same
  servers family). The card's "push grant intents through the enrollment path"
  variant (operating a remote engine's grants file from the client machine)
  was NOT built in this slice; it is a follow-up slice needing its own task.
- Acceptance status: criteria 1-3 have executed test evidence on the PR head
  (see the PR body); criterion 4 awaits worker B review of the exact head.
