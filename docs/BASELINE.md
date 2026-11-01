# Fork baseline (BASE-001)

Measured 2026-10-30 by worker A (commit identity david-noether[bot]) on host
e0f0e41ca9d6 at /opt/data/home/zeron. Every fact below came from an actual
command or file read in this checkout; anything not executed is labelled NOT RUN.

## Repository identity

- Remote origin: https://github.com/Umbral-lab/zeron (fetch and push URLs
  identical; no embedded token in the URL).
- Default branch main. HEAD at measurement:
  60e87c51843f903484510652d975985f2ad3d448, equal to origin/main after fetch.
- Pinned fork base: 369d42815190ea6c4865c92dc060c54d790f4dcd
  (upstream version-bump commit "Bump version to v0.2.130").
- Working tree clean; no local-only commits or uncommitted changes.
- Bootstrap commits 989b110c and 60e87c51 authored by Umbral Agent with the
  umbral-labs-dev[bot] noreply email (worker B, different machine). Inherited
  product commits retain their original upstream authors.

## Workspace structure

- Cargo workspace, resolver 2: 29 path crates under crates/ plus apps/zeron.
  Workspace version 0.2.130, edition 2024, license MIT, publish false.
- crates/: audio, client, doc, engine, harness, markdown, mcp, mobile,
  mobile-bindgen, notify, orb, preview, proto, rpc, sync, syntax, term,
  term-link, text, theme, ui, update, veil, visual, visual-gpu, voice,
  voice-media, voice-session, zatex.
- apps/: zeron (desktop app, has its own tests), android, ios, landing,
  www-redirect.
- edge/: TypeScript Cloudflare Worker plus Durable Objects service with
  wrangler.jsonc, wrangler.chat2test.jsonc and wrangler.transport-test.jsonc;
  CONTRIBUTOR rules say this infrastructure keeps its old comet name on purpose.
- dist/: packaging assets (zeron.desktop, icons, macos/, windows/, voice/).
- scripts/: packaging, probes, fixtures, e2e smoke helpers, and scripts/ops
  (worker B bootstrap diagnostics).
- Crate capability map: see ARCHITECTURE.md; do not duplicate it here.

## Toolchain pinned by the repo, and this host's state

- rust-toolchain.toml pins channel stable with components rustfmt and clippy.
- Linux builds need the GPUI system libraries listed in CONTRIBUTORS.md
  (libxkbcommon-dev, libxkbcommon-x11-dev, libwayland-dev, libx11-dev,
  libxcb1-dev, libx11-xcb-dev, libfontconfig1-dev, libfreetype-dev,
  libasound2-dev, libvulkan-dev, pkg-config, cmake, libwebkit2gtk-4.1-dev,
  libjson-glib-dev).
- This host: Linux 7.0.2-6-pve, 2 CPU cores, 251 GB RAM, 52 GB free on
  /opt/data, user hermes uid 10000, no sudo, no display server (DISPLAY empty).
- cargo, rustc and rustup are absent. node v26.12.1 and Python 3.14.9 present.
- Consequence: any Rust compile requires an operator root action (the apt
  package list) plus a rustup install, and will be slow on 2 cores.

## Discovered build and test commands (from CONTRIBUTORS.md, mirroring CI)

- cargo run -p zeron
- Dev isolation next to an installed app: ZERON_DATA_DIR and ZERON_IPC_PORT
  environment variables (example in CONTRIBUTORS.md uses ~/.zeron-dev, port 27700).
- cargo test --locked -p zeron-ui --lib -- --test-threads=1
- cargo test --locked -p zeron-engine --lib
- cargo test --locked -p zeron-harness (includes tests/ fixtures)
- cargo test --locked -p zeron-sync --lib
- cargo test --locked -p zeron-sync --features mock-server
  (verified 2026-10-31: plain -p zeron-sync without the feature fails to
  compile the integration test registry_client.rs because it imports the
  cfg-gated registry::mock_server module; this is inherited behavior, not a
  fork regression. With the feature: 83 passed, 2 ignored, 0 failed.)
- cargo test --locked -p zeron-proto (verified 2026-10-31: 98 passed, 0 failed)
- cargo test --locked -p zeron-preview
- cargo clippy --all-targets; format only changed code, no whole-file reformat.
- Account-free UI exercising: ZERON_HARNESS=mock with ZERON_MOCK_SUBAGENT,
  ZERON_MOCK_THINKING, ZERON_MOCK_TODO, ZERON_MOCK_DELAY_MS.

## CI automation inventory (.github/workflows, 13 files)

- push to main: deploy.yml auto-deploys the edge Workers, Durable Objects and
  R2 via wrangler, gated on a CLOUDFLARE_API_TOKEN secret and on changes under
  edge/ or deploy.yml itself; preview-tests.yml also runs on main pushes for
  its path set. Whether the fork repository currently has that secret: UNKNOWN.
- scheduled: cursor-sdk-update.yml daily at 09:17 UTC with contents:write,
  pull-requests:write and actions:write (it opens vendor SDK update PRs);
  release-profile-tests.yml daily at 07:17 UTC.
- tags and manual: release.yml on v* tags; testflight.yml workflow_dispatch only.
- PR path-gated: android.yml, cursor-compatibility.yml, linux-installer.yml,
  macos.yml verified individually; ui-tests.yml, voice-tests.yml and
  windows.yml triggers were NOT READ in this pass.
- Fork quarantine candidates for M1 (decision belongs to BASE-003/LOCAL-002):
  cursor-sdk-update.yml auto-PRs, deploy.yml vendor auto-deploy, the
  crates/update vendor update path.

## Outbound and vendor coupling seeds (input for BASE-003, not yet a full map)

- edge/ Cloudflare service (Workers, Durable Objects, R2, legacy comet names).
- deploy.yml and wrangler configs imply production Cloudflare dependency for the
  hosted sync/device rooms layer.
- apps/landing and apps/www-redirect are hosted web surfaces.
- crates/update exists (vendor update mechanism; behavior not yet inspected).
- WorkOS appears in recent inherited commit history (webhooks, directory);
  source-level map deferred to BASE-003.

## Platform support as declared by repository automation

- CI: Linux, macOS, Windows. Apps: Android and iOS with own workflows.
- A's current host can currently run only the non-Rust parts (git, Python ops
  diagnostics, Node scripts); it is a headless VM.

## Checks actually run on 2026-10-30

PASS:

- git fetch and read-back: main equals origin/main at
  60e87c51843f903484510652d975985f2ad3d448; clean tree; clean remote URL.
- GitHub App identity: helper whoami reports installation 173158300 covering
  Umbral-lab/zeron with target_repo_accessible true (live read probe). Write
  scope was verified the same day by an invalid-body POST returning 422 per the
  identity skill record, and is re-proven by this task branch push.
- python3 -m unittest discover -s scripts/ops -p test_*.py: 6 tests OK.
- python3 scripts/ops/preflight.py: import_integrity PASS for all 10 imported
  files, unattended_inference BLOCKED, model_dispatches 0.

NOT RUN (reason, not pass):

- cargo build / cargo test / cargo clippy: no Rust toolchain on this host;
  installation requires operator root apt actions and a window longer than this
  run had available; 2-core CPU.
- Real UI and visual baseline (BASE-002 input): headless host, app not buildable.
- Pre-existing test failure state: UNKNOWN until a toolchain exists.

## Headless core evidence added 2026-10-31 (toolchain live)

PASS (isolated disposable data dir under the agent scratch area; no real user
data; no login performed; local-only mode):

- cargo test --locked -p zeron-proto: 98 passed, 0 failed.
- cargo test --locked -p zeron-veil --lib: 16 passed, 0 failed (E2EE crate green).
- cargo test --locked -p zeron-rpc --lib: 25 passed, 0 failed.
- cargo test --locked -p zeron-sync --features mock-server: 83 passed,
  2 ignored, 0 failed (plain -p zeron-sync fails to compile the inherited
  registry_client integration test; command nuance recorded above).
- cargo test --locked -p zeron-harness: 482 + 87 + 10 passed across harness
  targets, but the muse integration target is FLAKY on this host:
  a_crash_mid_turn_reports_muses_last_words (crates/harness/tests/muse.rs:583,
  "harness protocol error: Muse stdout closed") failed in 4 of 11 isolated
  target-only runs (1 failure in the initial full-suite invocation, then 4
  failures across a 10-run isolated repeat with 6 passes) — a repeat-rate
  timing flake, not a one-off and not claimed as a fork regression; filed as
  issue-tracked evidence for a later bounded fix task (likely a pipe-read race
  in the test harness).
- cargo test --locked -p zeron-notify: 3 passed, 0 failed.
- No zeron-agent-control or zeron-i18n packages exist in this workspace
  (crate list verified: audio … zatex).
- zeron -V: 0.2.130 (debug build of main e3f01754).
- zeron --help: real headless CLI surface exists — headless, login, logout,
  status, sync, appshot, mcp, daemon, update subcommands.
- zeron status with an isolated ZERON_DATA_DIR: reports the vendor edge
  default https://edge.zeron.sh, Mode local only, Auth signed out, engine
  state, and loopback-only IPC binding (127.0.0.1, port via ZERON_IPC_PORT).
- zeron headless (30 s, then 25 s run): engine starts, assembles a per-data-dir
  device id, checkpoints the sync WAL, listens IPC on loopback only; SIGTERM
  produced a clean shutdown line. While running, zeron status reported
  running with the IPC port listening; zeron sync reported the device id with
  Workspace "no room (dialing or edge-less)" and no open chats.
- Data-dir contents after the runs: device-id, locks, ipc-token,
  local-profile.json, logs/, profiles/ — durable local state, no credentials.
- Startup logs of the two bounded headless runs showed no vendor update or
  release-fetch errors; the only warnings were the CLI's own short websocket
  probe disconnecting. The code-level auto-update poll mapped in BASE-003
  remains the authority for default egress behavior; this was not a network
  capture.

NOT RUN: headed UI rendering (headless host). This section partially informs
BASE-002 (CLI/log surfaces) but does not replace visual acceptance.
