# Task OPS-001A — A-side run-window guard and receipt

ID / title: OPS-001A / minimal worker-A run receipt and policy mapping (first bounded piece of OPS-001)
Milestone / user outcome: M0 / the owner gains a verifiable, deterministic record that nightly runs respect the declared window, and a truthful map of which policy rules are actually enforced on A's host.
Status / risk: ready_for_review / R2 (scheduler and runtime-policy semantics; no product/runtime behavior changed)
Owner worker / model route: A / self-hosted Qwen route (qwen3.8-flash-next-iq3_xxs, custom provider)
Dependencies: none beyond BASE-001 baseline. Splits the open OPS-001 item "minimal A-side run receipt plus policy mapping" recorded in ops/STATE.md.
Acceptance criteria:
1. A deterministic, stdlib-only guard computes the OPERATIONS.md window (nominal 01:00 Europe/Madrid, deadline = earlier of the local 05:00 UTC instant and 4 real elapsed hours after the 01:00 UTC instant, 15-minute late-start grace, phase cutoffs derived from the deadline) using timezone-aware instants, never a fixed UTC offset and never local wall-clock field arithmetic: the ZoneInfo conversion to UTC happens before min() and before the 4-hour cap, so the recorded max_elapsed_hours always equals the real UTC span.
2. Same-date admission is idempotent and persisted before work (exclusively-created atomic link, 0600, fsync before the link), outside the repository; a finalized receipt refuses further work and re-finalizing returns the original checkpoint unchanged; a past-deadline check refuses continuation; a start before the nominal open is EARLY, writes no receipt, and every non-OK/non-OK_LATE_GRACE receipt refuses work.
3. Actual tests cover ordinary nights, both DST transition nights, grace boundaries, duplicate admission, finalization refusal and phase derivation; all pass on A's host.
4. A sanitized mapping document records, per policy section, which rule is enforced by which actual control on A's host, verified vs NOT ENFORCED, with tonight's actual run evidence.
Non-goals: not the operator's enforcement snapshot; no budget counters, no quota telemetry, no leases/locking service, no changes to B's launcher, no product code changes, no new schedules.
Allowed paths/components / permission scope: ops/worker-a/run_window_guard.py, ops/worker-a/test_run_window_guard.py, ops/tasks/OPS-001A.md, docs/OPERATIONS_POLICY_MAPPING.md; receipts written only under $ZERON_A_STATE_DIR / $HERMES_HOME/state/zeron-worker-a (outside Git).
Base revision / branch / worktree: main e3f01754 / task/ops-001a-run-receipt / /opt/data/home/tmp/wt-ops001a
Lease ID / fencing generation: single-integrator mode; lease = this task record, owner A, run Umbral-lab/zeron:2026-10-31 (closed at run end).
Expected verification and evidence: python3 ops/worker-a/test_run_window_guard.py on A's host; a real same-date admission receipt created for the 2026-10-31 run plus a duplicate-readback demonstration; sanitized receipt summary in this record.
Result revision / changed files: head recorded on the branch at push time (see PR).
Actual checks: PASS 20/20 guard unit tests (python3 3.14.9, Europe/Madrid zoneinfo present); PASS real admit for 2026-10-31 (actual start 00:01:00Z, OK admission, deadline 04:00:00Z) with duplicate readback reused, no re-dispatch. NOT RUN: broader suites (not affected); UI evidence (headless, not applicable); B-side launcher behaviors (different host, not verifiable from A).
Remaining concerns / next step: OPERATIONS.md's DST prose ("shorten the autumn night", "spring may be only three elapsed hours") does not match arithmetic for this 01:00–05:00 window — both transition nights are exactly 4 elapsed hours; needs an owner/reviewer wording decision. Hermes cron schedule is a UTC cron expression with no timezone field (see mapping). Next: independent B review of this branch; then the remaining OPS-001 dry-run items 1-9 on the actual launcher.
Rollback / data impact: revert the branch; receipts stay outside Git and can be deleted independently. No existing file modified.

## Review round (worker B, umbral-labs-dev[bot] claude-opus-5-5, review 5907329673 at head d0fcab13)

Findings F-B1..F-B4 are all resolved on this branch; F-B5 is deferred by owner decision. A confirms each finding
against real execution before changing anything:

- F-B1 (DST/elapsed arithmetic) confirmed. Live probe at d0fcab13: compute_window(2026-10-25) gave nominal
  2026-10-24T23:00Z, local close 2026-10-25T04:00Z, deadline 04:00Z while the old code still reported
  max_elapsed_hours 4.0 - a 5-real-hour run under a 4h cap. Root cause: min()/MAX_ELAPSED were applied to local
  datetimes and datetime arithmetic on two values sharing one ZoneInfo object subtracts as naive local times, so
  01:00 CEST -> 05:00 CET looked like 4 hours. Fix: convert both boundaries to UTC instants first, then min() and
  the cap. Corrected values: 2026-10-25 deadline 03:00Z, 4 real hours; 2026-03-29 deadline 03:00Z, 3 real hours;
  2026-11-15 (normal night) 04:00Z, 4 real hours. docs/OPERATIONS.md already described this rule; this card's
  earlier claim that the OPERATIONS.md prose did not match the arithmetic was inverted and is corrected above.
- F-B2 (EARLY persisted, then accepted by assert_can_work) confirmed by B's probe; fixed two ways: EARLY writes no
  receipt at all (a later in-window admit still creates the single receipt), and assert_can_work refuses every
  verdict outside OK / OK_LATE_GRACE, including SKIP_LATE_START and SKIP_WINDOW_CLOSED receipts.
- F-B3 (finalize rewrites a finalized receipt) confirmed; finalize_run now returns the existing checkpoint
  unchanged and marks already_finalized.
- F-B4 (admission "atomic open" not fold-safe) applied as a review fold-in on this A-owned branch: the receipt is
  written to a private temp file in the same directory, fsynced, then placed with os.link (exclusively-created;
  FileExistsError keeps the existing receipt); no partial canonical file is ever observable and no leftover temp
  file remains. Because A authored this fold-in, it is explicitly submitted for B's independent review as part of
  the new head, not as a self-cleared change.
- F-B5 (OPS-001A/OPS-001C share a branch) is deferred: the owner decommissioned the Hermes worker B model route and
  the candidate-review-v2 controller (issue #3 comment 6885182532, 2026-11-14T22:50Z) and directed direct review;
  branch splitting is an R2 structure change that waits for owner approval. Recorded openly in PR #8, not hidden.

Actual checks for this round (A's host, python3 3.13.5, Europe/Madrid zoneinfo present, receipts in a private
temporary directory): PASS 32/32 guard unit tests at the new head. Red-then-green evidence: the new
test_run_window_guard.py, run unchanged against the reviewed base d0fcab13, fails 10 tests -
test_dst_autumn_night_elapsed_hours and test_dst_spring_night_elapsed_hours (the two window tests whose previous
assertions encoded the wall-clock bug), test_autumn_clock_change_night_is_capped_to_four_real_hours,
test_max_elapsed_hours_equals_the_real_utc_span and test_no_night_exceeds_four_real_elapsed_hours (F-B1 sweep),
test_early_start_writes_no_receipt, test_in_window_admission_still_possible_after_an_early_dispatch,
test_assert_can_work_refuses_a_non_admitted_receipt and test_assert_can_work_refuses_window_closed_receipt (F-B2),
and test_second_finalize_returns_the_original_checkpoint (F-B3) - and passes 32/32 against the new head. The two
F-B4 tests (no leftover partial artifact, duplicate admission never overwrites) pass at both revisions: they are
regression guards for the fold-in, not red-first evidence, and are stated as such. NOT RUN: Rust suites (no Rust
file changed); UI evidence (headless host); B-side launcher behavior (other host). Receipts for 2026-11-15 stay
outside Git.
