# Milestones and initial backlog

Milestones are acceptance gates, not promises to finish on particular nights. Work from actual evidence. Do not open a dozen speculative branches or claim all upstream README features are implemented.

## M0 — Inspect and establish a safe baseline

Record repository identity, fork/default branch, base revision, dirty state, applicable instructions, actual host/tool versions and supported build targets. Compare relevant fork architecture with the pinned research. Inventory existing functions, broken paths, outbound connections, licenses and inherited CI/release/deploy workflows. Discover commands from the repository; run baseline checks and identify pre-existing failures.

Capture real UI baselines and a small set of representative user journeys. Choose a temporary isolated app identity/data root for tests. Document existing capabilities so Overseer ideas are not duplicated. Create the shortest viable implementation queue and an ADR for the local control plane.

Exit: truthful baseline report, usable development build or a precise blocker, connection/feature inventory, retained attribution, agreed first vertical slice, and operational preflight evidence. Stop broad discovery when these decisions are supported.

## M1 — Independent local core

Remove vendor runtime dependencies from the fork's supported local distribution, including hidden update/catalog behavior. Keep local security, persistence, headless operation and working agent adapters. Replace account-oriented UI with local ownership/settings, preserving visual language. Separate fork/upstream data and updater identity. Quarantine unused vendor deployment paths from the fork's build/CI, then remove dead code incrementally with evidence.

Exit: A01–A04, A07, A08 and applicable A10/A11 pass for the local core; a real configured harness works online, with clear provider errors when offline. No vendor account, backend, billing or telemetry dependency remains. Build-time downloads are documented separately from installed runtime behavior.

## M2 — One complete workflow inspired by Overseer

From the M0 gap analysis, choose the highest-value missing workflow. Preferred candidate: an attention-oriented view of durable tasks tied to isolated worktrees and a clear review/diff outcome. Reuse Zeron equivalents where available. Implement the entire path from native UI through durable state to lifecycle and error handling.

Add usage-aware scheduling only on top of reliable state and adapter capabilities. Keep budget readings honest and queues idempotent. Do not port Overseer's whole React/Go stack into the fork.

Exit: a real task can be started, observed, interrupted/recovered, reviewed and kept with reproducible evidence. A05, A06 and relevant A10/A11 pass. Require A09 here only if the selected workflow includes product scheduling or budget control; otherwise SCHED-001 has its own A09 gate before scheduling support can be claimed. The owner can identify the improvement in a short demonstration.

## M3 — Direct owned machines

Add or adapt explicit SSH-based machine enrollment and headless engine access. Keep per-machine identity, workspace permissions, revocation and connection state. Exercise a controlled remote fixture, including reconnect and uncertain outcomes. Preserve local usability without any enrolled machine online.

Exit: A12 passes with the required trust boundaries. No mandatory hub, vendor rendezvous, tunnel, relay or cloud sync has been introduced. If this milestone is deferred from an initial local release, document the scope honestly; it remains part of the project backlog.

## M4 — Release candidate and maintainability

Close data/recovery/security regressions, verify packaging and the supported platforms available to the project, finalize attribution and update the real README. Offer manual installation/export/backup instructions. Include an operational guide, limitations and rollback. A future fork update feed is optional and must be explicitly configured.

Exit: all acceptance rows in the declared release scope have evidence, R2 findings are resolved, no required checks are falsely green, and a reviewable release candidate exists. Publication or deployment is a distinct owner-authorized action.

## Seed tasks

These are queue seeds, not claims of work done. Split them only when that improves ownership or verification.

| ID | Task | Dependencies | Default owner / risk | Acceptance |
|---|---|---|---|---|
| BASE-001 | Pin fork and inspect build/architecture/CI | None | A / R0 research | Baseline revisions, commands, failures and platform limits recorded |
| BASE-002 | Capture visual and workflow baseline | BASE-001 | A; B may inspect evidence / R0 | Real screenshots and journeys, no demo-only proof |
| BASE-003 | Map outbound connections and license provenance | BASE-001 | A / R0 research | Source-backed inventory, removal/replacement decisions |
| OPS-001 | Verify external nightly controls | Runtime setup | A with owner-configured launcher / R2 | Dry run proves routing, caps, locks, deadlines and restart accounting |
| LOCAL-001 | Isolate fork data and application identity | BASE-001 | A / R2 | Side-by-side test preserves upstream data |
| LOCAL-002 | Remove vendor runtime paths and unsolicited checks | BASE-003, LOCAL-001 | A / R2 | Blocked-egress local core, correct optional-provider handling |
| LOCAL-003 | Prove durable lifecycle and recovery | LOCAL-001 | A / R2 | Crash, duplicate request, cancel and history tests |
| UX-001 | Adapt account/settings surfaces to local ownership | LOCAL-002, BASE-002 | A or B / R1 if presentation only | Actual UI evidence and no loss of authorization controls |
| FLOW-001 | Deliver one researched Overseer-inspired gap | M1 gates | A / R1 or R2 by behavior | Complete demonstrable path with acceptance tests |
| SCHED-001 | Persist queue and enforce scheduling/budget semantics | LOCAL-003, capability map | A / R2 | Duplicate/DST/unknown-quota/deadline cases |
| REMOTE-001 | Direct owned-machine trust and headless flow | M2 gates | A / R2 | A12 with scope and revocation evidence |
| RELEASE-001 | Package, document and verify candidate | Declared milestone gates | A / R2 | A13, limitations, notices and rollback |

OPS-001 is a development-operations prerequisite, not a reason to build a large custom orchestration platform. Use supported Hermes capabilities and a minimal external guard where needed. A supervised baseline may proceed before unattended execution is enabled.

## Choosing and stopping work

Each night targets one main user-visible outcome, with a small independent task for B only when useful. Dependencies and unresolved reviews take priority over new features. Cap work in progress at one task per worker and a small review queue; stop creating changes when the review queue cannot be processed within the budget.

Every seventh completed night, report accepted outcomes, remaining critical gaps, regressions, review backlog, actual model use/uncertainty and the next smallest milestone. Recommend continuing, narrowing scope or pausing. If three consecutive nights repeat a blocker or produce no accepted progress, stop repeating that activity and write a specific decision note. Do not self-delete or archive the repository; the owner decides the experiment's future.
