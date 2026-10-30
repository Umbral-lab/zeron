# Outbound connections and license provenance (BASE-003)

Measured 2026-10-30 by worker A (commit identity david-noether[bot]) on
commit 9f1c6979 (main after PR #2 integration, fork base 369d4281 v0.2.130).
Every claim below cites a file in this checkout; lookups that were actually
executed are marked with their method. Hosts seen only inside test fixtures
are excluded from the runtime map and listed separately.

## A. Vendor-operated runtime infrastructure (current fork default)

1. Hosted edge service — the sync/registry/chat/device backend.
   - apps/zeron/src/lib.rs line 10: DEFAULT_EDGE_URL is https://edge.zeron.sh
     (Cloudflare Worker plus Durable Objects, edge/src).
   - crates/client/src/auth.rs line 30: PRODUCTION_EDGE_URL is the same host.
   - crates/client/src/live/urls.rs: registry room, chat room and device room
     WebSocket and HTTP endpoint shapes against that edge host.
   - Edge service code: edge/src (auth-routes, chat-room, device-room,
     registry, APNs push via api.push.apple.com and api.sandbox.push.apple.com
     in edge/src/apns.ts lines 27-28, WorkOS verify/JWKS in edge/src/auth.ts
     lines 74-75).
   - CI auto-deploys this infrastructure on push to main when a
     CLOUDFLARE_API_TOKEN secret exists (deploy.yml; secret presence in the
     fork: UNKNOWN, per BASE-001).

2. Vendor account authentication — WorkOS AuthKit.
   - crates/client/src/auth.rs lines 30-32 and 79-80: baked-in
     WORKOS_CLIENT_ID (client_01KWD0EAKZKD50YCQJNYSRE4BY) and
     https://api.workos.com authorize flow.
   - apps/zeron/src/lib.rs lines 10-34: DEFAULT_WORKOS_CLIENT_ID baked in;
     ZERON_WORKOS_CLIENT_ID env override; an explicitly empty value selects
     development auth (crates/engine/src/lib.rs around line 905).
   - Overrides exist: ZERON_EDGE_URL and ZERON_WORKOS_API_BASE
     (crates/engine/src/lib.rs line 759, crates/engine/src/managed.rs,
     apps/zeron/src/daemon.rs lines 29-30).

3. Self-update mechanism with unscheduled-start auto polling.
   - crates/update/src/lib.rs: CHECK_INTERVAL is 1 hour, DESKTOP_INITIAL_DELAY
     is 2 seconds and ENGINE_INITIAL_DELAY 20 seconds (lines 53-72), so a
     running install polls the release feed automatically after startup.
   - Default feed is {edge}/releases (release_base around line 327), i.e.
     vendor-hosted by default; ZERON_RELEASES_URL override is validated
     HTTPS-only without credentials/query/fragment (lines 300-315).
   - Advisory links for unmanaged installs point at
     https://github.com/zeronsh/zeron/releases (lines 320-324);
     apps/zeron/src/update_cli.rs line 75 offers the vendor installer
     https://zeron.sh/install.sh.
   - Windows release resolution lives in crates/update/src/windows.rs.

4. Harness compatibility manifest and vendor harness update channels
   (crates/engine/src/harness_updates.rs and compatibility.rs).
   - compatibility.rs lines 8-12: fetches {edge}/releases/harness-compatibility.json
     at most hourly with a local offline copy; a built-in fallback list is
     compiled in (compatibility.json).
   - Vendor release checks already installed by the user are polled on a
     schedule (CHECK_INTERVAL plus jitter, harness_updates.rs lines 730-735)
     against formulae.brew.sh (line 1279), registry.npmjs.org (line 2013),
     api.github.com latest/tags releases (lines 2035-2063) and
     api.meta.ai/muse-code/channels (line 1971).

5. Hosted web surfaces and vendor CI automation (not the app runtime, but
   fork-carried vendor operations): apps/landing, apps/www-redirect;
   .github/workflows cursor-sdk-update.yml (daily vendor SDK PRs) and
   deploy.yml (auto edge deploy) as inventoried in docs/BASELINE.md.

## B. Vendor CLI install paths (only when the user selects that harness)

crates/harness/src/acp/mod.rs install hints and pinned downloads:
- xAI grok: https://x.ai/cli/install.sh or npm package
  @xai-official/grok@1.0.4 (line 261 region; pinned npm version).
- Devin CLI: https://cli.devin.ai/install.sh (line 334 region).
- Firecrawl fx: https://fx.sh/setup.sh (line 399 region).
- Hermes agent: https://hermes-agent.nousresearch.com/install.sh (line 451
  region) — a user-selected open agent, not vendor-operated for this fork.
- Google Antigravity ACP server: fixed dl.google.com archive URLs with
  sha512 pins per platform (lines 503-600 region) and a registry lookup at
  raw.githubusercontent.com/agentclientprotocol/registry (line 596 region).
These are optional adapters: download and version metadata only after the
user installs or enables that harness; the antigravity archive is
platform-pinned with hashes. They are still vendor download paths that M1
must document as optional, never implicit.

## C. User-initiated provider and repository connections (kept)

- Model provider sign-in (explicit user action, official OAuth):
  crates/client/src/provider_login.rs — auth.openai.com (line 44),
  api.openai.com/auth (lines 374, 566), claude.com OAuth authorize,
  platform.claude.com token and api.anthropic.com profile (lines 37-40),
  localhost callback loopback only (lines 127-138).
- GitHub repository features (explicit user action):
  device flow start via the edge cloud vault (crates/client/src/cloud.rs
  around line 283; verification page https://github.com/login/device),
  GitHub App installation link cloud.rs line 925, repo git remotes
  cloud.rs line 899, and api.github.com commit reads in
  crates/engine/src/repos.rs line 1168. These are user-owned connections to
  user-chosen services and remain compatible with the charter.

## D. Test-only hosts (no runtime significance)

example.com, evil.example, example.test, edge.invalid, edge.example,
boat.test, sso.corp.example, api.example and 127.0.0.1 fixtures appear only
in tests and doc comments (for example crates/update/src/lib.rs lines
1644-1652, crates/client/src/live/urls.rs line 128, harness_updates.rs test
listener around line 4486). Counted in the raw URL inventory (docs/BASELINE.md)
but excluded here on purpose.

## E. Automated versus user-initiated summary (M1 target list)

Automatic outbound behavior in a default install, before any user action:
1. hourly self-update polling of the vendor edge release feed
   (crates/update, 2 s after desktop start);
2. hourly harness-compatibility manifest fetch from the vendor edge
   (crates/engine/src/harness_updates);
3. scheduled vendor release checks for harnesses the user previously
   installed (brew/npm/github/meta.ai channels);
4. WorkOS-based sign-in defaults baked into the binary;
5. fork CI: edge auto-deploy and daily vendor SDK PR automation.
M1/LOCAL-002 candidates, in priority order: local default with explicit
remote opt-in for the update feed and compatibility manifest; neutral or
removed WorkOS default; fork-quarantine deploy.yml and cursor-sdk-update.yml;
document optional vendor CLI installs as user-authorized only. None of these
are executed by this task (R0).

## F. License provenance

- Repository license: MIT, Copyright (c) 2026 Wing (LICENSE file, unchanged
  upstream attribution). Cargo.toml line 39 declares MIT with publish false.
  CONTRIBUTORS.md lines 173-174 bind contributions to the same MIT terms.
  Attribution obligations survive any fork renaming decision; the copyright
  holder line is an owner/product-name decision input, flagged for M4.
- Direct third-party crates: 69 declared workspace dependencies, all
  resolved in Cargo.lock and each queried live on the crates.io API at its
  locked version (probe direct-dep-licenses.json):
  - 39 external crates, licenses found: MIT (17), MIT OR Apache-2.0 (15),
    Apache-2.0 (4: alacritty_terminal, gethostname, gpui name hit on
    crates.io, similar), Apache-2.0 OR MIT (uuid), CC0-1.0 (notify),
    Unlicense OR MIT (ignore). All permissive.
  - 26 zeron-* path crates plus zatex: fork-local (no crates.io record),
    covered by the workspace MIT declaration.
- Git-pinned external forks (license gap, must resolve before redistribution):
  - gpui, gpui_platform, gpui_tokio: git pin of github.com/zeronsh/zui at
    rev b564a34413bb7ef1da04121c4a287758f94993d9 (Cargo.toml lines 108-115).
    GitHub reports license NOASSERTION with two files present in the repo
    root: LICENSE-APACHE and LICENSE-GPL. The Zed upstream gpui this fork
    descends from is MIT. The effective combined license of this pin is
    UNVERIFIED and is a release-blocking question for M4.
  - gpui-base: git pin of github.com/zeronsh/gpui-component at rev
    59f89243cea79dd70eb7a619b3930c374ef6958a (Cargo.toml line 116). GitHub
    reports NOASSERTION with LICENSE-APACHE present. Upstream
    641230676/gpui-component is dual MIT/Apache; the fork copy's complete
    license set is UNVERIFIED.
  - Both pinned revisions were verified live to exist on their remotes
    (git ls-remote, 2026-10-30).
- Edge service (edge/package.json, private): runtime deps jose ^6.0.11,
  loro-crdt ^1.13.7, loro-protocol ^0.3.0 (lockfile edge/package-lock.json
  present). Their package licenses were not individually queried this run:
  NOT RUN (recorded, deferred to the transitive audit below).
- Scale: Cargo.lock resolves 1155 package entries (measured by counting name
  entries in this checkout). A full transitive license audit was NOT RUN:
  it requires a tooling decision (cargo-about or cargo-deny install) that is
  a new-dependency choice under the charter and belongs to the owner or a
  reviewed task, not to an R0 scan.

## G. Verification actually executed on 2026-10-30

PASS (this run):
- Live crates.io queries for all 69 direct dependencies at locked versions
  (script + JSON evidence; license histogram reproduced above).
- GitHub API license lookups for zeronsh/zui, zeronsh/gpui-component and
  zeronsh/zeron; git ls-remote confirmation of both pinned revisions.
- Source citation spot-checks: every file and line region named above was
  opened in this checkout (grep plus targeted reads) on commit 9f1c6979.
- cargo fetch completed exit 0 with the shared CARGO_TARGET_DIR, confirming
  the whole lockfile still resolves on this host.
- cargo test --locked -p zeron-update: 18 passed, 0 failed, 0 ignored
  (log zeron-target/logs/base003-update-tests.log; behavior evidence for the
  auto-polling constants in section A3).
NOT RUN (reason, not pass):
- Transitive license audit of all 1155 lockfile packages (tooling decision
  pending, charter dependency rules).
- edge npm dependency license lookups (deferred to the same audit).
- Network capture of a running app to prove the static map is complete
  (headless host, GUI app; runtime egress proof requires a display path and
  a blocked-egress fixture — that is LOCAL-002 acceptance, not this R0 task).
