# Task OPS-001B-2: scheduled harness polling honors ZERON_UPDATE_CHECKS

- Owner: worker A (david-noether[bot]) — Builder/Integrator
- Date: 2026-11-07 (nightly run window 01:00-04:00 Europe/Madrid)
- Branch: task/ops-001b-release-check-consent (PR #19), review head a17e1148
- Base for this increment: review head a17e1148 merged with origin/main 79d35247
- Risk: R2 (background network egress gating). A-authored R2: requires worker B/Sol
  review of the new head before integration. A does not self-integrate this change.

## Objective

Close the blocking finding on PR #19 head a17e1148: the engine fetched
releases/harness-compatibility.json on a schedule without background-update
consent. Scheduled harness polling must honor the same consent switch as the
desktop/service update poller (ZERON_UPDATE_CHECKS, default off).

## Acceptance criteria and status

1. No scheduled fetch of the harness compatibility feed when
   ZERON_UPDATE_CHECKS is unset/off. DONE: the coordinator worker parks
   (select on shutdown/interval only) when scheduled_checks_allowed() is
   false, and fetches nothing.
2. Consent is captured once at engine assembly (set_scheduled_consent with
   zeron_update::background_update_checks_enabled()) before the coordinator
   worker starts, so a mid-run env change does not flip scheduled behavior.
   DONE.
3. The published compatibility feed URL is wired into the coordinator during
   assembly when the edge profile is present, before coordinator start. DONE.
4. recheck_changed_binaries_soon (settings-open / stale-row wake) honors the
   consent gate. DONE.
5. Explicit check_all / check_one remain intentional user actions and are not
   gated. DONE (unchanged behavior, documented).
6. User-facing docs state the consent boundary. DONE: docs/reference/updates.md.

## Design notes

- scheduled_consent is an AtomicBool in the coordinator, default false
  (deny-by-default if the setter was never called).
- The feed refresh path (refresh_compatibility) runs at the start of
  check_one; scheduled polls reach it through the worker's check_all ->
  per-harness checks, so the consent gate lives at the worker-loop entry and
  at the binary-change wake, not inside refresh_compatibility itself.
- First scheduled tick fires after FIRST_RETRY (5 min), then CHECK_INTERVAL
  (6 h); the no-consent path never leaves the parked select.

## Tests added (all actually run on A's host)

- harness_updates.rs unit test scheduled_startup_polls_the_feed_only_with_check_consent:
  grok fixture + fake feed server; wake path silent without consent, fetches
  with consent (checked_binaries stale-row wake).
- crates/engine/tests/local_first.rs
  live_engine_polls_the_harness_feed_only_with_update_check_consent: two
  freshly-assembled engines against a test-owned edge listener counting
  requests to /releases/harness-compatibility.json and /releases/manifest*:
  without consent both counters stay zero while the engine is live; with
  consent the coordinator's refresh path reaches the wired feed. Separate
  data dirs per phase; ConsentEnvGuard guarantees the env var never leaks
  into other tests on panic. env mutation wrapped in unsafe with SAFETY
  comments (suite runs --test-threads=1).
- crates/update consent tests already covered by the update crate suite.

## Verification evidence (2026-11-07, A host, CARGO_TARGET_DIR=/opt/data/home/zeron-target)

- Baseline before edits, origin/main 79d35247 tree, cargo test --locked -p
  zeron-engine --test local_first -- --test-threads=1: 12 passed, 0 failed
  (local_first_baseline.log).
- After edits, cargo test --locked -p zeron-engine --test local_first --
  --test-threads=1: 13 passed, 0 failed (consent_tests9.log, exit 0).
- cargo test --locked -p zeron-update --lib: 21 passed, 0 failed
  (consent_tests7.log, UPDATE_EXIT=0).
- cargo test --locked -p zeron-engine --lib: 642 passed, 0 failed
  (consent_tests6.log tail; includes the new coordinator unit test;
  the earlier remote_terminals time-sensitive failure did not reproduce).
- cargo fmt applied; rustfmt --edition 2024 --check clean afterwards. The
  pre-existing formatting drift on branch-carried files (agent_accounts.rs,
  cloud_client.rs, doc_host.rs, sessions.rs, source_control.rs, uploads.rs
  among others) is resolved by this commit, not introduced by it; origin/main
  copies of those files are already rustfmt-clean.
- git diff --check clean.
- clippy scoped run (-p zeron-update --all-targets, -p zeron-engine --lib
  --tests, -D warnings): see PR #19 comment for the recorded result.
- UI evidence: NOT RUN (headless host, unchanged policy).

## Known limitations / notices

- Feed refresh is reached through harness checks: with zero enabled harnesses
  installed, scheduled polling performs no compatibility fetch at all (the
  worker snapshot checks nothing). The consent gate therefore protects the
  consensual path; the zero-harness path already fetches nothing.
- The live-engine test proves consent wiring + zero-egress without consent at
  assembly level; the exact five-minute timer semantics are proven in the
  unit-level wake test, not re-waited live (a 5-minute real wait was not
  run in CI-suitable time).
- zeron-update crate carries 4 pre-existing rustc warnings from the B audit
  inventory (file_watcher.rs, lib.rs:1275, lib.rs:1563, lib.rs:1627); none
  introduced here.

## Rollback

Revert the increment commit on task/ops-001b-release-check-consent; the
branch's prior review head a17e1148 remains intact in history.
