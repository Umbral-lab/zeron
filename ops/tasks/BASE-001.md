# Task record BASE-001

ID / title: BASE-001 — Pin fork and inspect build/architecture/CI baseline.
Milestone / user outcome: M0. The owner gets a truthful fork baseline: exact
revisions, real build/test commands, host limits, CI automation inventory and
honest NOT RUN labels, so later milestones and the two-worker loop build on
verified facts instead of assumptions.
Status / risk: ready_for_review / R0 (research and documentation only).
Owner worker / model route: A / qwen3.8-flash-next-iq3_xxs via custom provider
(self-hosted llama.cpp endpoint; see ops/STATE.md for the resolved route).
Dependencies: none. Bootstrap SETUP-001 handoff (commits 989b110c, 60e87c51).
Acceptance criteria:
1. Fork identity, default branch, base revision and dirty state recorded from
   live commands.
2. Discovered build/test commands and toolchain pin recorded from repo files.
3. Supported hosts and CI automation inventoried from .github/workflows.
4. Feasible baseline checks run with PASS/FAIL/NOT RUN labels and reasons.
5. Platform/toolchain gaps stated as precise blockers, not guesses.
Non-goals: no toolchain installation, no Rust build attempt, no product code
change, no schedule or policy edit, no outbound-connection deep map (BASE-003).
Allowed paths/components / permission scope: docs/BASELINE.md,
ops/tasks/BASE-001.md, ops/mailboxes/worker-a/** on the task branch only;
read-only inspection everywhere else; no writes in the main checkout.
Base revision / branch / worktree: 60e87c51843f903484510652d975985f2ad3d448;
branch task/base-001-fork-baseline; worktree /opt/data/home/zeron-wt/base-001.
Lease ID / fencing generation: none enforced yet (OPS-001 pending); single-A
single-task mode, recorded in ops/STATE.md.
Expected verification and evidence: git read-back, ops preflight and unittests
(PASS), CI/workflow file reads, toolchain probes (absent, recorded).
Rollback / data impact: delete the task branch only; no target or data impact.
Budget/time allocation / checkpoint deadline: bounded R0 pass inside the
supervised 2026-10-30 run; completed within it. No launcher receipt existed.
Result revision / changed files: recorded in the branch push (see git log on
task/base-001-fork-baseline): docs/BASELINE.md, ops/tasks/BASE-001.md,
ops/mailboxes/worker-a/reviews/REVIEW-SETUP-001.md.
Actual checks (PASS / FAIL / NOT RUN + reason):
- git fetch and identity probes: PASS (recorded in docs/BASELINE.md).
- scripts/ops unittests (6) and preflight: PASS on this checkout.
- cargo build/test/clippy: toolchain was later provisioned on A's host
  (owner decision 2026-10-30). Targeted suites verified 2026-10-31 — see the
  headless core evidence section of docs/BASELINE.md. Full-workspace test and
  clippy runs: NOT RUN.
- UI evidence: NOT RUN — headless host remains display-less; headless CLI and
  engine evidence now recorded as partial input to BASE-002.
Remaining concerns / next step: BASE-002 visual acceptance still needs an owner
display path or an accepted NOT RUN stance; one flaky harness muse test on the
2-core host should be re-checked in CI or on a faster machine. Worker B reviews
this branch; verdict and any findings land in B's mailbox per docs/OPERATIONS.md.
