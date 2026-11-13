# OPS-001C: fixed check-plan support for worker-A ops candidates

- Objective: make A-authored operational candidates under ops/worker-a/ reviewable
  by the integrated candidate-review-v2 controller. Before this change,
  check_plan() had no supported executable check for ops/worker-a/ paths, so
  PR #8 (OPS-001A run-window guard, head d0fcab13, 20/20 guard tests passing on
  A's host since 2026-10-31) is permanently filtered as "No supported executable
  check plan" and can never receive a B/Sol verdict.
- Acceptance criteria:
  1. check_plan returns exactly one bounded fixed-argv entry
     python3 -m unittest discover -s ops/worker-a -p test_*.py for candidates
     touching ops/worker-a/, and no extra plan entries otherwise.
  2. The existing ops/worker-b plan argv is byte-unchanged (pinned by a test).
  3. Controller discovery suite passes on A's host at this head (inherited
     httpx-missing test recorded NOT RUN on this host, unchanged).
  4. No change to selection order, caps, models, timers, routes or publication
     rules; PR body cannot inject commands (fixed-argv rule preserved).
- Non-goals: docs-only candidate review (BASE-001 #6 / BASE-003 #7 remain
  intentionally skipped by candidate-review-v2 as a model-budget decision;
  reviewing them needs an owner decision or a separate B docs lane — recorded
  in issue #3, not decided here). No re-review of already-decisive heads.
- Risk: R2 (audit routing for future candidate selection). Review requirement:
  B/Sol review of the exact head before integration; B's own controller runs
  the fixed ops/worker-b discovery over this diff.
- Dependencies: none beyond main 1b169f16 (candidate-review-v2 controller).
- Owner: worker A (author and integrator-after-review).
- Files: ops/worker-b/zeron_audit.py (one rule generalized),
  ops/worker-b/test_audit_review.py (two tests), this record.
- Branch / base: task/ops-001c-worker-a-check-plan from 1b169f16.
- Verification: A-host python3 -m unittest discover -s ops/worker-b; targeted
  proof that the new argv actually passes on the real PR #8 tree (20 tests OK
  in the task/ops-001a-run-receipt worktree).
- Rollback: revert the single commit; PR #8 stays filtered as before.

Sequencing note: this candidate contains no crates/ or apps/ paths, so
candidate-review-v2 group sorting keeps product candidate PR #29 ahead of it
in B's single nightly selection. Opening this PR does not delay the OPS-001B
re-review.
