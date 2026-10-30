# BASE-003 task record

ID / title: BASE-003 — outbound connection map and license provenance
Milestone / user outcome: M0, a source-backed inventory that tells the owner
which vendor infrastructure the fork currently depends on and which licenses
must be verified before any fork redistribution.
Status / risk: ready_for_review / R0 (research and documentation only).
Owner worker / model route: A / Qwen route (qwen3.8-flash-next-iq3_xxs,
self-hosted llama.cpp).
Dependencies: BASE-001 (baseline, docs/BASELINE.md).
Acceptance criteria:
1. Every category of runtime outbound connection is identified with
   file-level source evidence and classified vendor-hosted, third-party,
   user-optional or test-only.
2. Automated (unsolicited) outbound behavior is separated from
   user-initiated behavior.
3. License provenance covers the workspace license, direct third-party
   dependencies with actual queried license identifiers, git-pinned vendor
   forks, the edge service npm dependencies and the lockfile scale.
4. Removal/replacement decisions are framed as concrete M1 candidates, not
   silently executed.
Non-goals: no code changes, no dependency removal, no CI changes, no license
audit of all transitive lockfile packages (recorded as a follow-up tooling
decision).
Allowed paths/components: docs/CONNECTIONS_AND_LICENSES.md,
ops/tasks/BASE-003.md only. No runtime or product file touched.
Base revision / branch / worktree: 9f1c6979eb95f3adbef3eede7d8b78e5041aebfb
(main after PR #2 integration) / task/base-003-connection-license-map /
/opt/data/home/zeron-wt/base-003.
Lease ID / fencing generation: single-integrator mode (A only); no external
lease service exists yet (OPS-001 open).
Expected verification and evidence: source citations verified by grep/read in
this checkout; crates.io and GitHub license lookups by script
(direct-dep-licenses.json preserved by the run); targeted cargo test of the
update crate as behavior evidence for the auto-polling finding.
Rollback / data impact: none (documentation only).
Budget/time allocation: within the nightly A caps (60 task minutes / 40 task
requests); no build beyond targeted crates.
Result revision / changed files: see branch commits in the PR.
Actual checks: recorded in docs/CONNECTIONS_AND_LICENSES.md Verification
section and the PR review packet.
Remaining concerns / next step: B independent review; LOCAL-002 consumes the
M1 candidates list; full transitive license audit needs a tooling decision.
