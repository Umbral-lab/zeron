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
- Toolchain live on A's host (owner decision 1 executed): GPUI apt packages
  installed by the owner plus libssl-dev (the CONTRIBUTORS.md gap); rustup
  pinned stable 1.99.1; cold full build of -p zeron succeeded 17:35 UTC
  (log zeron-target/build2.log, 0.9s incremental no-op; cargo flags one
  future-incompat dependency, proc-macro-error2 — retained notice). Shared
  CARGO_TARGET_DIR /opt/data/home/zeron-target for all worktrees.
- Queue (single-integrator mode; A owns this file):
  - BASE-001 ready_for_review: branch task/base-001-fork-baseline head
    5502aae0, now published as PR #6 (the morning push lacked the PR; fixed
    2026-10-30 evening). Awaiting B's independent review at that head.
  - BASE-003 ready_for_review: docs/CONNECTIONS_AND_LICENSES.md,
    ops/tasks/BASE-003.md and live license evidence; branch
    task/base-003-connection-license-map head a0ef50a2, PR #7. Awaiting B's
    review. Key findings: automatic vendor-edge update polling and harness
    compatibility fetches are mapped with file evidence; git pins
    zeronsh/zui and zeronsh/gpui-component report license NOASSERTION —
    release-blocking UNVERIFIED gap for M4; transitive audit of the 1155
    lockfile entries NOT RUN pending an owner/reviewed tooling decision.
  - B-SETUP (B's local nightly wake-up): PR #5 reviewed by A (nine tests
    re-run on A's host at head 61b12b45, 9/9; record at
    ops/mailboxes/worker-a/reviews/REVIEW-PR5.md) and integrated as merge
    7ca3a99d; merged files verified byte-identical and 9/9 re-run on the
    merged tree. B's owner-authorized local systemd timer is active on B's
    host; first scheduled unattended wake 2026-10-31 01:00 Europe/Madrid.
    Single-dispatcher rule: A will not dispatch B while that timer exists.
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
  exit 0; cargo test --locked -p zeron-update 18/18; live crates.io (69 direct
  deps) and GitHub license lookups; git ls-remote pins exist. NOT RUN:
  broader cargo suites, UI evidence (headless), transitive license audit.
- Last run usage: Qwen self-hosted route only (counted approximately via
  session dispatches; provider does not report totals); no Terra/Sol use.
- Next action (next scheduled run): consume B reviews of PR #6 and PR #7;
  read B's first nightly receipt/result after the 01:00 wake as OPS-001
  evidence; then the smallest remaining M0 slice (BASE-002 partial:
  headless-visible evidence such as CLI/log surfaces, or LOCAL-001 design
  prep strictly after BASE-003 review).
- Owner decisions open: transitive license-audit tooling (cargo-about or
  cargo-deny) approval or deferral; display path for UI evidence, or
  acceptance that BASE-002 visual acceptance stays NOT RUN on this host.
