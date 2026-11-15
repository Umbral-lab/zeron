# OPS-001B — Release-feed check consent (local-first default)

- Objective: make every scheduled poll of `{edge}/releases/manifest.json` a
  consent decision, so a local runtime is silent by default, and close the
  race where a running scheduler re-read the consent switch mid-flight.
- Risk: R2 (outbound network behavior, scheduling, environment-driven
  routing). Owner approval gate; Sol review required before integration.
- Branch / base: `task/ops-001b-release-check-consent`, base
  `origin/main` at `eb1958ba0e1efb18ce70c2a2e389ff6fe942b79f`.
- Dependencies: OPS-001A run-window guard (landed), worker B audit
  acceptance step 1 (`docs/audits/2026-11-01-worker-b.md`).

## What the baseline actually did (verified, not assumed)

`origin/main` has no consent switch for checks at all: `ZERON_UPDATE_CHECKS`
does not appear anywhere on `origin/main` at `eb1958ba`. Two unsolicited
egress paths exist:

1. Scheduled polls. `Updater::check_loop` re-evaluated
   `background_update_checks_enabled()` inside the loop on every wake, and a
   default desktop spawn polls the public release feed after a 2 s initial
   delay (engine role: 30 s). Reproduced on a throwaway worktree of
   `eb1958ba` (`/opt/data/home/tmp/wt-redbase`, probes kept uncommitted):
   the `default_desktop_checker_stays_local_until_the_user_asks` probe FAILS
   on baseline with 1 unsolicited request in 4.11 s
   (`/opt/data/home/zeron-target/red_final2.log`).
2. An auth-event wake. `crates/engine/src/lib.rs` spawned a task that called
   `updater.check_now()` whenever `EdgeConfig::token_changes` fired — a
   sign-in or token refresh performed a release-feed request with no user
   action. Reproduced by the baseline wake probe
   (`crates/update/tests/red_consent_wakes.rs`, temporary).

The consent *gate itself* is new work in this candidate; it is not something
main already had that merely misfired.

## Acceptance criteria and status

1. Local/woken runtime issues no release-feed request without consent —
   PASS on candidate: `crates/update/tests/local_default_no_scheduled_egress.rs`
   (spawn, 3.5 s wait, five wakes → 0 requests) and the engine-level
   `local_runtime_wakes_do_not_poll_releases_without_check_consent` in
   `crates/engine/tests/local_first.rs` (auth wake + two explicit pokes →
   request count unchanged after `check_now()` is skipped).
2. Explicit paths keep working with consent off — PASS: `check_now()` from
   "Check for Updates…" / `zeron update` is consent-independent
   (`tests::scheduled_check_requires_consent_and_explicit_check_does_not`).
3. Consent is decided once, at spawn, not re-read mid-loop — PASS:
   `Updater::spawn_role_with_delay` captures `background_consent` and the loop
   uses `self.background_consent`; consent-sensitive tests pass an explicit
   `consent_override` instead of mutating the shared process environment, so
   they no longer race each other.
4. User-facing documentation matches the new behavior — PASS: README claim
   "The app updates itself" replaced in all five locales, new
   `docs/reference/updates.md` states the defaults and both env switches.

## Non-goals

- No change to explicit update flows, staging, apply, or restart semantics.
- No new dependency, no scheduler rewrite, no edge/manifest server change.
- `install.sh` was NOT changed: whether a managed Linux service should set
  `ZERON_UPDATE_CHECKS=1` at install time is an owner decision (open).

## Verification actually run (2026-11-04, Debian 13, pinned stable)

- RED on baseline, isolated target dir `/opt/data/home/zeron-target-redbase`,
  worktree `/opt/data/home/tmp/wt-redbase` at `eb1958ba`:
  `test result: FAILED. 0 passed; 1 failed` — 1 unsolicited request,
  `left: 1 / right: 0` (`/opt/data/home/zeron-target/red_final2.log`).
- GREEN on candidate, isolated target dir `/opt/data/home/zeron-target-cand`:
  `cargo test --locked -p zeron-update` → lib tests `21 passed; 0 failed`,
  `local_default_no_scheduled_egress` → `1 passed; 0 failed`
  (`/opt/data/home/zeron-target/green_final2.log`).
- `cargo test --locked -p zeron-engine --test local_first` → `12 passed;
  0 failed`, includes the new wake test (`local_final.log`).
- `cargo test --locked -p zeron --test background_engine` → `1 passed;
  0 failed` (`bg_final.log`).
- Baseline contamination control: the first RED/GREEN attempt shared one
  `CARGO_TARGET_DIR` between worktrees and reused artifacts; both sides were
  re-run with dedicated target dirs before any conclusion was drawn.
- Test-harness defect found and fixed mid-run: the feed stub replied before
  reading the request, which broke reqwest connection reuse and made the
  green side fail spuriously. The failure was in the harness, not in the
  consent gate; the stub now reads the request before answering.

## Known notices (not introduced here)

- `cargo clippy --locked -p zeron-update --all-targets` fails with 5
  `unused_io_amount` errors on the candidate and the same 5 on `origin/main`
  at `eb1958ba` (lines shift only): pre-existing debt in the update crate's
  test helpers. No repo CI workflow runs clippy or fmt.
- `rustfmt --edition 2024 --check crates/engine/src/lib.rs` reports 25 diffs
  on the candidate and 25 on base main; no candidate-only fmt diff.
  `crates/update/src/lib.rs`, `crates/engine/tests/local_first.rs` and the new
  test file report 0 diffs.
- `crates/engine` lib test `remote_terminals::tests::a_terminal_rides_a_real_webrtc_pair_through_a_network_change` is flaky on both sides: 4/5 passes on the candidate, 4/5 on base main (`/tmp/flake_c1-5.log`, `/tmp/flake_b1-5.log`). Not caused by this change.
- UI evidence: NOT RUN (headless host).

## Rollback

Revert the single candidate commit / do not merge the PR. No migrations, no
persistence, no dependency changes; `Cargo.lock` untouched.
