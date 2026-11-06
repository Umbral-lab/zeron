# Task OPS-001A — A-side run-window guard and receipt

ID / title: OPS-001A / minimal worker-A run receipt and policy mapping (first bounded piece of OPS-001)
Milestone / user outcome: M0 / the owner gains a verifiable, deterministic record that nightly runs respect the declared window, and a truthful map of which policy rules are actually enforced on A's host.
Status / risk: ready_for_review / R2 (scheduler and runtime-policy semantics; no product/runtime behavior changed)
Owner worker / model route: A / self-hosted Qwen route (qwen3.8-flash-next-iq3_xxs, custom provider)
Dependencies: none beyond BASE-001 baseline. Splits the open OPS-001 item "minimal A-side run receipt plus policy mapping" recorded in ops/STATE.md.
Acceptance criteria:
1. A deterministic, stdlib-only guard computes the OPERATIONS.md window (nominal 01:00 Europe/Madrid, deadline = earlier of local 05:00 and 4 elapsed hours, 15-minute late-start grace, phase cutoffs derived from the deadline) using timezone-aware instants, never a fixed UTC offset.
2. Same-date admission is idempotent and persisted before work (exclusive atomic create, 0600), outside the repository; a finalized receipt refuses further work; a past-deadline check refuses continuation.
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
