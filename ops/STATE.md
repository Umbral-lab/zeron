# Project state

This is the initial template. No implementation, build, test, schedule or runtime setup has been performed by this package. Worker A is the sole canonical writer; the launcher stores enforceable counters and locks separately.

## Identity and authority

- Fork path / remote: to be discovered from the actual checkout.
- Default branch / pinned starting revision: not yet recorded.
- Organization / product name: not finalized by this package.
- Scope: local-first Zeron fork; user-chosen AI providers and direct owned-machine connections allowed.
- Excluded repository: Noether.
- Effective remote push / PR / merge authority: not yet verified.
- External report delivery: none configured.
- Policy version/hash: record after owner/runtime configuration.

## Current position

- Milestone: M0, not started.
- Unattended preflight: NOT VERIFIED.
- Baseline build / tests / visual evidence: NOT RUN.
- Current accepted revision: not yet recorded.
- Active run ID / effective deadline: none.
- Current main objective: establish a truthful fork baseline and verified operational controls.

## Active task and review queue

No tasks have been claimed. Initial queue seeds are in docs/ROADMAP.md. Keep only current task IDs, states, owners, revisions and links here; detailed history belongs in per-task records and reports.

## Decisions and blockers

- Confirm actual configured Qwen route; do not infer an identifier from its display label.
- Verify Terra/Sol availability and authentication through the installed Hermes runtime.
- Map the declarative policy to enforceable runtime controls before unattended execution.
- Use the actual host as the first verified development target; record other platform gaps.

## Last run and next action

- Last run: none.
- Usage and quota observations: none; unknown is not zero.
- Next action: execute the supervised bootstrap prompt.
- Next owner decision: only if bootstrap finds a required capability, permission or product ambiguity not resolved by the charter.

## Compact handoff rule

Keep this file to approximately one page after initialization. Update current facts and links; do not append entire logs or conversations. Preserve older reports separately. Never store secrets or real credential values here.

## Supervised bootstrap overlay (owner-authorized main setup)

The text above is the preserved source template, not current execution evidence.
Current checkout: `https://github.com/Umbral-lab/zeron`, `main`, starting at
`369d42815190ea6c4865c92dc060c54d790f4dcd`. Worker B/Sol imported the instruction
kit without changing inherited product code or documentation. See
[bootstrap/SETUP.md](bootstrap/SETUP.md) for setup evidence and remaining blockers.
No nightly run, product build, independent review or runtime enforcement has been
verified. Unattended inference is BLOCKED. A resumes canonical state ownership
after this owner-authorized bootstrap; B uses its own mailbox thereafter.

## Current position (worker A; supersedes the earlier 2026-10-30 overlays; imported prefix bytes preserved)

- Runs 2026-10-30: three A activities on this date — morning bootstrap-baseline
  run (job 4103065fd3d6, 08:37 UTC, bounded R0), owner-directed integration of
  PR #2 (18:02 UTC, merge 660343fe, prompts byte-verified, AGENTS.md identity
  split b7705159 resolved the identity wording decision), and an owner-fired
  daytime test of the nightly-builder configuration (~19:06 UTC start,
  supervised, outside the 01:00 Europe/Madrid product window by owner
  instruction; not an unattended nightly; no schedule created or enabled).
- Bootstrap closed (BASE-001 verified facts below); the nightly run starting
  2026-10-31 00:00 UTC follows docs/agent-prompts/01_BUILDER.md.
- Runs 2026-10-31: one bounded scheduled nightly run (job 4103065fd3d6,
  actual start 00:01 UTC, deadline 04:00 UTC, phase cutoffs freeze 03:00 /
  close-findings 03:30 / integration 03:45 / shutdown 03:55 UTC; A-guard
  receipt run-2026-10-31, verdict OK, finalized at close). First nightly
  under 01_BUILDER.md.
- Toolchain live on A's host (owner decision 1 executed): GPUI apt packages
  installed by the owner plus libssl-dev (the CONTRIBUTORS.md gap); rustup
  pinned stable 1.99.1; cold full build of -p zeron succeeded 17:35 UTC
  (log zeron-target/build2.log, 0.9s incremental no-op; cargo flags one
  future-incompat dependency, proc-macro-error2 — retained notice). Shared
  CARGO_TARGET_DIR /opt/data/home/zeron-target for all worktrees.
- Queue (single-integrator mode; A owns this file):
  - BASE-001 ready_for_review: branch task/base-001-fork-baseline, stable
    review head c78e2601 (PR #6, base 7ca3a99d). Nightly run added
    verified targeted evidence to docs/BASELINE.md: zeron-proto 98/98;
    zeron-sync 83 pass + 2 ignored only with --features mock-server (plain
    invocation fails to compile the inherited registry_client integration
    test — recorded baseline nuance, not a regression); zeron-veil --lib
    16/16; zeron-rpc --lib 25/25; zeron-notify 3/3; zeron-harness
    482+87+10 pass across targets; headless CLI evidence (version 0.2.130,
    subcommand surface, status with local-only mode and signed-out auth,
    loopback-only IPC, engine start and clean shutdown under an isolated
    disposable data dir); zeron-agent-control and zeron-i18n package names
    verified absent. Flaky inherited test a_crash_mid_turn_reports_muses_-
    last_words failed 4/11 isolated target runs — filed as issue #9, not a
    claimed regression. UI evidence still NOT RUN (headless). Awaiting B's
    independent review at head c78e2601.
  - BASE-003 ready_for_review: docs/CONNECTIONS_AND_LICENSES.md,
    ops/tasks/BASE-003.md and live license evidence; branch
    task/base-003-connection-license-map head a0ef50a2, PR #7. Awaiting B's
    review. Key findings: automatic vendor-edge update polling and harness
    compatibility fetches are mapped with file evidence; git pins
    zeronsh/zui and zeronsh/gpui-component report license NOASSERTION —
    release-blocking UNVERIFIED gap for M4; transitive audit of the 1155
    lockfile entries NOT RUN pending an owner/reviewed tooling decision.
  - OPS-001A ready_for_review (run 2026-10-31): A-side run-window guard +
    receipts (ops/worker-a/run_window_guard.py, 20/20 tests PASS on host,
    incl. both DST transition nights) + docs/OPERATIONS_POLICY_MAPPING.md +
    ops/tasks/OPS-001A.md; branch task/ops-001a-run-receipt, stable review
    head d0fcab13 (PR #8, base e3f01754). Live same-date receipt created
    pre-work (outside Git, 0600); duplicate admission reused; run finalized
    at close with stop reason. R2: needs B/Sol review before integration.
    Findings: F-1 OPERATIONS.md DST prose contradicts verified arithmetic
    (both 01:00–05:00 transition nights are exactly 4.0 elapsed hours;
    wording decision needed, R0); F-2 Hermes cron job stores a bare UTC
    expression 0 0 * * * with no timezone field — live guard verdict probe:
    OK on CET nights and on the spring-changeover night (deadline 03:00Z),
    SKIP_LATE_START on every CEST night (arrives 02:00 local) and on the
    autumn-changeover night; forecast recorded for 2026-11-01 (CET, OK).
    Structural schedule-timezone gap until the owner sets the cron timezone;
    NOT ENFORCED on A's host (operator-owned controller gap, F-3).
  - B-SETUP (B's local nightly wake-up): PR #5 reviewed by A (nine tests
    re-run on A's host at head 61b12b45, 9/9; record at
    ops/mailboxes/worker-a/reviews/REVIEW-PR5.md) and integrated as merge
    7ca3a99d; merged files verified byte-identical and 9/9 re-run on the
    merged tree. B's owner-authorized local systemd timer is active on B's
    host; first scheduled unattended wake 2026-10-31 01:00 Europe/Madrid.
    Single-dispatcher rule: A will not dispatch B while that timer exists.
    First scheduled wake 2026-10-31 01:00 CET: A polled branches, open PRs
    and issues at 00:10, 01:13, 01:34, 01:55, 02:09 and 02:16 UTC — no
    B-authored artifact arrived (no B-AUDIT-001 issue/PR, no reviews on
    PRs #6/#7/#8). Observation posted to issue #4 (comment 6537674990).
    Whether B's timer ran is NOT VERIFIED from A's host; B's own
    receipt/ledger holds the reason. B receipt remains NOT VERIFIED.
  - BASE-002 unblocked (toolchain + binary exist); still NOT STARTED: real
    UI evidence needs a display path — remains NOT RUN on headless host.
  - OPS-001 open (issue #3): declarative policy only; no launcher receipt or
    immutable snapshot on A's host; dry-run items 1-9 largely NOT VERIFIED;
    carried findings from REVIEW-PR5 (per-night quota baseline, launcher
    coupling, guard egress breadth, B-host facts NOT VERIFIED). Next A step:
    a minimal A-side run receipt plus policy mapping as a separate reviewed
    task before any unattended claim.
- Worker A runtime (unchanged): provider custom, base_url
  http://192.168.10.244:8080/v1, model qwen3.8-flash-next-iq3_xxs
  (self-hosted llama.cpp; unmetered — quota UNKNOWN by nature, never treated
  as unlimited). ops/policy.json import-locked; this line is the record.
  Terra/Sol: NOT VERIFIED from A's host (B-host concern).
- Credential handling (unchanged notices): GitHub App helper verified; repo
  identity david-noether[bot]; every remote write this run used the explicit
  bot credential helper; a global credential.helper store still exists and
  remains an operator hardening item.
- Checks verified 2026-10-30 evening: DNS recovered; origin/main fetch
  read-back; App whoami; 9/9 B tests (twice, incl. merged tree); cargo fetch
  exit 0; cargo test --locked -p zeron-update 18/18; cargo test --locked -p
  zeron-client --lib 35/35; live crates.io (69 direct
  deps) and GitHub license lookups; git ls-remote pins exist. NOT RUN:
  broader cargo suites, UI evidence (headless), transitive license audit.
- Checks verified 2026-10-31 nightly: A-guard admit/status/finalize live
  (verdict OK, deadline 04:00Z, duplicate admission reused, receipts 0600
  outside Git; one defect found and fixed in-run: the finalize rewrite left
  tonight's live receipt 0644 — now 0600-enforced with a regression assert,
  head d0fcab13); guard unit tests 20/20; cargo test --locked targeted suites
  as listed under BASE-001 above; zeron binary --help/-V/status/headless/
  sync exercised under an isolated disposable ZERON_DATA_DIR with no login
  and loopback IPC only (no vendor-edge contact observed in those logs);
  muse flake measured over 11 isolated target runs; remote-write probes:
  App whoami, PR mergeable=true/clean-base for #6/#7/#8, main branch
  protection API 403 for the App (protection state NOT VERIFIED — operator
  item). NOT RUN: full-workspace test/clippy run, UI evidence (headless),
  transitive license audit, B-host state.
- Last nightly usage: Qwen self-hosted route only (one agent session plus
  bounded deterministic probes and waits; provider does not report totals —
  quota UNKNOWN, never treated as unlimited); no Terra/Sol/GPT use; no
  retry storm after one expired-token remint.
- Next action (next scheduled run, forecast 2026-11-01 OK verdict): consume
  B reviews of PRs #6 (c78e2601), #7 (a0ef50a2) and #8 (d0fcab13); integrate
  approved candidates only under the integration lock; read B's wake receipt
  via issue #4 as OPS-001 evidence; if B artifacts are still absent after a
  second night, flag the B-wake failure to the owner instead of re-dispatching.
- Owner decisions open: transitive license-audit tooling (cargo-about or
  cargo-deny) approval or deferral; display path for UI evidence, or
  acceptance that BASE-002 visual acceptance stays NOT RUN on this host;
  set the zeron-worker-a cron timezone to Europe/Madrid (or re-pin the
  expression) so CEST-period and autumn-changeover nights are not silently
  skipped by the A guard (finding F-2, R2 scheduling change — owner-gated);
  OPERATIONS.md DST wording correction (F-1, R0) once B concurs.
