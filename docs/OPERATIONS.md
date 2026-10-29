# Nightly execution and coordination

## Scope

This is the operating design for two Hermes developer workers. A non-model launcher/controller enforces time, admission, locks and budgets. It is not a third reasoning agent. The product being built may later have a scheduler, but the development loop must run independently of that unfinished feature.

The provided policy file is declarative project policy. It does not automatically configure Hermes. Verify the installed version and supported controls, map these requirements to actual settings, and record the effective configuration. Do not invent CLI flags, edit hidden runtime files blindly or claim scheduling works because the prompt mentions a time.

## Run identity and clock

One run ID is admitted for each project and Europe/Madrid local date, for example project:2026-10-30. Default start is 01:00 and local close is 05:00. The hard deadline is the earlier of that date's 05:00 instant and four elapsed hours after the nominal 01:00 start. Use timezone-aware calculations and a monotonic elapsed timer; restarts must not extend the original deadline.

This deliberately shortens the autumn clock-change night rather than allowing five hours of spending. The spring night may be only three elapsed hours. Store UTC instants plus the local zone/date; do not treat a fixed UTC offset as Europe/Madrid. A repeated scheduler event uses the same run ID and cannot start another run.

Admit a delayed start only within 15 minutes of nominal start and keep the original deadline. Otherwise skip that night. Do not wake later in the day to catch up. On resume from sleep/reboot, reconcile the run and refuse further work if its window has closed.

## Phases relative to the effective deadline

| Phase | Normal Madrid time | Rule |
|---|---|---|
| Preflight | 01:00–01:10 | Verify identity, resources, locks, state, routes, quota and actual pending work |
| Build | After preflight to deadline minus 60 minutes | A implements; B gets bounded optional jobs; both keep checkpoints |
| Freeze / audit | Deadline minus 60 to minus 40 minutes | Freeze and test one combined candidate; B/Sol conducts one continuous audit of at most 20 wall-clock minutes, including any immediate recheck |
| Close findings | Deadline minus 40 to minus 15 minutes | A may prepare scoped fixes and tests; changes not verified before the audit closed remain pending for the next night |
| Integration/report | Deadline minus 15 to minus 5 minutes | Integrate already reviewed, verified changes; write state/report; no new feature work |
| Shutdown | Last 5 minutes | Checkpoint, release leases, stop owned job processes, finish report |

Derive all phase times from the effective deadline, including DST and short runs. Prepare and test the candidate before the freeze; at the freeze, an unfinished or untested task stays on its branch and does not force the audit to wait. The single audit's wall-clock cap includes waiting and tools; target an initial review within 12 minutes/5 requests and reserve its remaining capacity for a ready scoped fix. UNKNOWN mode has the smaller cap defined in MODEL_BUDGET.md. Once the audit completes or expires, do not reopen it or start another audit. If tests cannot finish within the window, record them pending; do not cross the deadline or claim success.

## Workspaces and coordination

Maintain one canonical repository identity and default branch. Use separate worktrees/checkouts for A, B and serialized integration. Each task records its base, branch, files/components and owner. Only one worker owns overlapping shared components at a time. Reserve broad changes such as schemas, lockfiles and migrations explicitly.

The launcher enforces an operator-owned immutable effective policy snapshot, including model routes, stored outside worker write scope and identified by version/hash. Its counters, job/run locks and leases have the same boundary. Editing the repository's policy or a proposed guard implementation cannot change the current run's enforcement; expanding resources or authority requires owner activation for a future run. A owns canonical task state and integration decisions. B writes review/task artifacts to its own mailbox; A consumes them idempotently. Use unique IDs and atomic file replacement or a transactional local store. Two workers must not concurrently append to a shared JSON/Markdown file.

Prefer an already available queue/lease service on the execution host. If the existing runtime lacks safe shared state, start in a simpler single-integrator mode: A issues immutable task packets, B produces immutable result packets, and only A updates ops/STATE.md and task state. Do not build an elaborate distributed coordinator merely to begin this experiment.

For a shared host, require a run lock, per-worker lock, task lease and integration lock. Leases have owner identity, heartbeat and fencing generation. Expiry alone does not authorize stealing a live worker's checkout; reconcile liveness, revoke old ownership and fence stale writes first. If workers are on separate machines, require a verified common coordination mechanism before parallel writes; otherwise serialize them. Human changes always trigger a fresh state/diff check.

## Task and review lifecycle

Use queued → claimed → in_progress → ready_for_review → changes_requested or approved → integrated. Side states include blocked, interrupted and deferred. A transition records timestamp, actor, revision and evidence. “Tests running” and “awaiting review” are not done.

For each review, B or A reads the actual diff and relevant surrounding code, checks the stated acceptance and verifies representative evidence independently. Findings identify severity, file/location, failure scenario and required outcome. A verdict is APPROVE, CHANGES_REQUESTED, INCOMPLETE or BLOCKED. Missing evidence produces a limited/incomplete verdict, not automatic rejection of unrelated work.

Before the daily audit, A assembles the selected pending changes into one non-published candidate branch/tree, records its base and exact head, and tests that combined result. Assembly is not approval or publication. Freeze target writes by the workers while this candidate is reviewed. B's own portions still need A's independent review; B reviews A's portions and relevant interactions without claiming independence over its own code.

Only the integrator updates the real target, after checking unchanged target/base, reviewer independence, unchanged approved candidate and required checks. Serialize a compare-and-swap/fast-forward to that exact candidate and record the resulting revision. A target movement, candidate edit or conflict resolution requires renewed affected checks/review; defer if the audit has closed. Do not auto-resolve conflicts by preferring one side. Preserve remote protections and authorized write scope.

## Crash, uncertainty and failure handling

Persist admission before model dispatch. Use an idempotency key for each run/job/request when supported. Reserve capacity before starting; reconcile actual usage afterward. A timeout or crash does not refund uncertain usage. Keep counters across worker/model restarts. Never reset a budget by giving the same work a new task ID.

On restart, inspect receipts, process ownership, branches and existing artifacts before retrying. If a model/tool action may have completed, reconcile it with the affected resource. Mark uncertain outcomes explicitly. Do not duplicate a merge, task execution or external action because its response was lost.

For failures: one retry for a transient transport problem; two distinct unsuccessful engineering approaches before checkpoint/replan. Quota/auth/payment failures park the affected route. A compromised lock or invalid guard stops dependent work. A test failure gets diagnosis and a bounded fix, never a disabled check. Preserve partial work without marking it accepted.

At shutdown, terminate only process groups created for this run, after cooperative cancellation/checkpoint grace. Do not kill unrelated user agents, services or terminals. Record any intentionally persistent fixture/process and its owner; default is none. Stop new model admissions before hard termination so there is time for a truthful handoff.

## Launcher preflight and dry-run acceptance

Record the actual installed Hermes version and supported commands. Verify model/provider identities, supported authentication route, per-job working directories and tools, inference/auxiliary routes, time zone, effective permissions and the configured report path. Pin approved routes through supported operator controls. A missing requested model blocks that route; it does not authorize substitution.

Before enabling unattended runs, use disposable files and mocked calls where possible to demonstrate:

1. Duplicate wake events create one run and one worker of each identity.
2. A counter reaching its cap blocks the next provider attempt, including mocked SDK retries, helper calls and restarts; repository policy edits cannot raise the effective cap.
3. Low/unknown quota follows the configured branch; a known block survives a later UNKNOWN reading, and entering UNKNOWN cannot refill counters; no paid fallback or third model worker is created.
4. Terra cannot overlap Sol, and a model change retains B's authorship identity.
5. A stale lease or changed Git target cannot perform a write/merge.
6. A simulated short deadline stops owned jobs and preserves a resumable checkpoint.
7. Spring/fall DST calculations and missed-start rules give the intended deadline once.
8. An interrupted request remains charged/reserved until reconciled; shutdown/restart cannot refill budgets.
9. A no-work night does not call a model just to announce idleness.

If an essential guard is unavailable, report the missing capability and prepare its minimal implementation/configuration as a separate reviewed task. Supervised repository work can continue within known limits. Do not activate unattended GPT before request-count/routing/output bounds are enforceable.

## Practical Hermes notes

Hermes documentation describes per-job model/provider and timezone configuration, job working directories, fresh scheduled sessions and script-only jobs. Model pins are controlled through operator configuration; scheduled prompts must not attempt to rewrite them. Use the installed version's supported interface. [Official scheduled-task documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron).

Check both primary and auxiliary fallback routes, including compression and vision. A pinned primary alone does not prove every helper is bounded. [Official fallback documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers).

## Reporting and autonomy boundaries

Write one local morning report and updated state. Notifications are optional and require a configured, authorized destination. Do not repeatedly ask for routine implementation approval, send unsolicited external messages, publish releases, provision infrastructure, purchase credits or modify another repository.

No model needs to run for all four hours. If accepted scope is exhausted, reviews are budget-blocked, or only owner-dependent tasks remain, checkpoint and let the launcher end early. Do not create maintenance chores to fill time. Every week produce the short continuation assessment specified in ROADMAP.md.
