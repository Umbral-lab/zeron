# Architecture direction and acceptance evidence

This describes required outcomes and preferred implementation directions. It does not claim the fork already implements them. Record deviations and decisions in small architecture decision records (ADRs), with alternatives, evidence, consequences and a rollback path.

## 1. Begin from the real fork

Pin the fork revision and the upstream references. Inspect existing instructions, manifests, entry points, persistence, IPC, adapters, tests, CI and release workflows. The upstream snapshot in UPSTREAM_RESEARCH.md is evidence, not a migration command. Do not automatically rebase an older fork to current upstream or reproduce upstream's recent rewrite.

Prefer the existing native UI → local engine → adapter/process architecture. Retain working Loro/SQLite persistence and typed IPC where present. A component named sync may contain indispensable local durability. Separate local state mechanisms from remote transport instead of deleting by directory name.

Create a capability map for each currently supported agent: discover/version, authentication status, start, stream, input, approvals/questions, cancel, resume, usage, model selection and working-directory isolation. Unsupported capabilities must be visible. Check the installed Hermes interface; do not invent ACP support or command flags.

## 2. Local ownership and lifecycle

The local engine owns sessions, durable events, queue state, process handles and project/worktree associations. The UI is a client of that state, not the only place it exists. Use stable request and session identifiers, versioned schemas and atomic writes/transactions. Bound diagnostic logs, caches and transient replay buffers. Preserve durable user history unless the user explicitly deletes it or enables a disclosed retention policy; an export option is not consent to deletion.

Start, cancel and recovery operations need idempotent semantics. An uncertain response is not permission to execute again. After a restart, reconcile recorded intent with processes and existing results. Reattach where safely supported; otherwise mark interrupted and require a deliberate resume. Document when “resume” starts a new agent context and retain provenance.

Separate the fork's application identity, data directory, IPC namespace, caches and update settings from upstream. First-run migration is opt-in and works on a copy with backup/export and rollback. Never automatically reuse a logged-in upstream cloud profile or erase it. Keep compatible local sessions/attachments accessible through a tested import path if import is offered.

## 3. Connection policy

Maintain an inventory with source location, initiator, destination, purpose, trigger, data sent, consent, offline behavior and replacement/removal decision. Include application code, engine children, web content, dependencies, install scripts, scheduled tasks and release automation.

| Category | Default | Required behavior |
|---|---|---|
| Vendor auth, cloud sync, billing, storage, telemetry | Removed from shipped runtime | No fallback, hidden entitlement or vendor credential required |
| Local engine and IPC | Enabled | Local authorization and process/path boundaries |
| User-selected model/provider | Disabled until configured | Explicit destination; errors never silently route to another provider |
| Git remotes | Explicit operation | No automatic push or unexpected credential exposure |
| Owned remote machines | Explicit enrollment | Direct authenticated connection, scoped permissions, revocation |
| Application/harness updates and catalogs | Off by default | Manual or explicitly opted-in checks; offline mode suppresses them |
| Images, fonts, previews and auxiliary model calls | Bundled/local by default | No automatic fetch of untrusted external resources |

Strict offline mode disables all outbound network paths under application control, including background checks. Implement enforceable controls and request observation rather than relying only on UI toggles or URL searches. If a spawned third-party harness can make independent connections beyond the app's control, document that boundary and enforce offline tests through OS/container network controls. Never claim a UI switch alone sandboxes arbitrary subprocesses.

Updates must not install the original vendor's binary over the fork. Initial distribution can use owner-built artifacts and manual installation. A later update channel requires explicit owner configuration, artifact integrity verification, preserved app identity and rollback. Do not auto-publish releases or remove legal references while eliminating runtime endpoints. Historical links and copyright notices are not runtime dependencies.

## 4. Direct owned-machine management

Preserve a headless engine where the fork provides one. Use an optional direct transport, preferably existing SSH mechanisms, with host key verification and explicit enrollment. Avoid designing a new cryptographic protocol. Use user-managed keys/system agent; do not centralize private keys or provider tokens in a new database.

Associate every task with its machine and allowed workspace. Remote actions execute on that machine with the granted identity, not a global administrator. The owning engine must enforce workspace and capability limits; client UI declarations are insufficient. SSH agent forwarding and provider-secret forwarding are off by default and require deliberate user authority. Show connection state and last observation time. Disconnection leaves local features usable, records uncertain remote outcomes and does not relaunch the task on another machine. Cancellation must distinguish “requested” from “confirmed.”

Revocation must define and enforce the removal of future access and relevant trust material. Explain whether already-running remote jobs continue and whether previously copied credentials require separate revocation; deleting a local host entry cannot erase authority already granted elsewhere. Authentication, command scoping, reconnect behavior and file transfer are reviewed explicitly. Assume enrolled peers can be compromised; do not grant access to all local workspaces just because they belong to one account. NAT traversal and relay infrastructure are deferred, with clear errors for unreachable hosts.

## 5. Local security

Retain owner-only token files, authenticated IPC and existing checks. Bind local services narrowly. Browser-accessible endpoints need origin validation and defenses against CSRF/DNS rebinding; loopback is not sufficient authorization. Privileged actions require explicit capabilities, and every path must remain inside its allowed root after symlink/canonical-path resolution.

Run previews in an isolated origin/context with no access to privileged RPC or credentials. Treat rendered markup, terminal control sequences, links, uploaded filenames, tool arguments and repository content as untrusted. Prevent command injection, unsafe archive extraction and path traversal. Do not log complete secrets; use disposable fixtures in tests.

Use OS credential storage or the harness's supported credential mechanism. Surface provider sign-in failures without asking users to paste tokens into chat. Removing vendor login must preserve provider login and local authorization as distinct concepts.

## 6. Scheduling and budget controls in the PRODUCT

Product scheduling is a feature under development. The two workers' nightly development schedule is a separate external operational mechanism, described in OPERATIONS.md. Do not make the development loop depend on the unfinished product scheduler.

Persist task identity, intended time/zone, selected machine/model, capabilities, permission profile and state transitions. Enforce concurrency and atomic claim/lease ownership. Preserve job identity across retries. Handle duplicate requests, missed windows, DST, app restart, cancellation and quota delays without surprise catch-up work.

Represent observed usage with source, timestamp, account/window identifiers, reset time and unknown/stale states. Do not infer remaining subscription allowance from API prices or token counts. Strict budget mode blocks new work on missing/stale/invalid readings and applies independent request/time limits. A user may explicitly choose a less strict mode; it must remain visibly distinct and must not bypass hard execution limits. “Start now” cannot silently bypass a safety or spending cap.

## 7. Acceptance matrix

Each row needs a reproducible procedure, environment, relevant revision, result and evidence path. Use deterministic fixtures for lifecycle coverage and real integrations for claimed end-to-end functionality. A mocked adapter alone does not prove real-provider integration.

| ID | Scenario | Passing evidence |
|---|---|---|
| A01 | Launch and idle with egress blocked | No app account, no hidden vendor attempts; local UI usable; observed traffic includes child processes |
| A02 | Local work offline | Existing history, attachments, project navigation, diffs, settings and queue work without external assets |
| A03 | Agent lifecycle | Deterministic offline harness plus one configured real harness demonstrate start, streaming, questions/approvals, cancel and truthful resume support |
| A04 | Durable recovery | UI/engine kill and restart preserve records; known running or interrupted state; no silent duplicate execution |
| A05 | Duplicate/uncertain start | Repeated request and lost response produce one effective execution with a durable receipt |
| A06 | Concurrent editing | Separate worktrees, respected task ownership, no overwritten user changes; exact reviewed result integrated once |
| A07 | Data isolation/import | Fork and upstream run side by side; import on a disposable copy preserves source; failure leaves recoverable backup; storage limits do not silently delete user history |
| A08 | Network policy | Startup, idle, settings, update, usage and session actions obey disabled categories; enabled requests have a documented destination/purpose |
| A09 | Limits and schedules | Known low quota, unknown/stale quota, 429, restart, duplicate wake, DST, missed start and deadline all produce the documented state without extra model calls |
| A10 | IPC/preview/path boundaries | Untrusted origin, HTML, shell arguments, symlink escape and malicious attachment cannot gain privileged access |
| A11 | UI continuity | Real rendered main flows preserve layout/themes; keyboard navigation, focus, loading/error/empty states and long content remain usable |
| A12 | Owned remote machine | Verified host identity, scoped work, disconnect/reconnect and revocation work; local app survives remote absence |
| A13 | Packaging and provenance | Required platform build checks recorded; shipped artifact uses fork identity, bundles assets and retains notices; no vendor deploy/release surprises |

Do not label A12 complete before direct-machine support exists. A release milestone may declare it deferred only if the release scope and README say so. Similarly, unsupported platforms and unavailable real-harness checks remain explicit gaps.

## 8. Decision discipline

Baseline startup, memory and representative UI response timing before setting performance gates. Avoid arbitrary benchmark targets without measurements. Review material regression against that baseline. Keep compatibility/version fixtures for adapter protocols and preserve expected errors when upstream CLIs change.

Choose the smallest architecture that satisfies the matrix. A new service, database, protocol, dependency or abstraction needs a concrete requirement. Keep the explanation short enough that a future agent can understand why it exists.
