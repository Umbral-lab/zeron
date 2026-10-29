# Durable records and evidence packets

Use small Markdown or structured records as supported by the actual runner. The schemas below specify required meaning, not a requirement to build a new service. Do not create a file for every trivial thought. Use stable IDs and atomic writes. A owns canonical state; B writes immutable artifacts to its own mailbox.

## Task record

    ID / title:
    Milestone / user outcome:
    Status / risk R0-R2:
    Owner worker / model route:
    Dependencies:
    Acceptance criteria:
    Non-goals:
    Allowed paths/components / permission scope:
    Base revision / branch / worktree:
    Lease ID / fencing generation:
    Expected verification and evidence:
    Rollback / data impact:
    Budget/time allocation / checkpoint deadline:
    Result revision / changed files:
    Actual checks (PASS / FAIL / NOT RUN + reason):
    Remaining concerns / next step:

Accept a task only when its objective and acceptance criteria are small enough for the available time and budget. Update status truthfully; a useful partial patch can remain interrupted or ready_for_review.

## Review packet from author

    Task ID / risk / author worker:
    Base and head revisions / diff location:
    Why this change is needed:
    What changed for the user:
    Acceptance criteria and implementation map:
    Commands/checks, environment, results and evidence paths:
    Actual UI screenshots, if relevant:
    Data/security/network/compatibility implications:
    Known gaps and specific review questions:

Keep the narrative roughly 600–1,000 words or less; supply the actual diff/code by path rather than copying a full transcript. The reviewer must inspect it, not merely trust this packet. Redact secrets and use synthetic examples.

## Independent review record

    Review ID / task IDs:
    Reviewer worker / model route / UTC timestamp:
    Author worker(s) / independence check:
    Reviewed base / head / resulting integration tree if applicable:
    Scope actually inspected:
    Checks independently verified:
    Findings: severity, file/location, concrete failure, required outcome:
    Limits / unreviewed scope:
    Verdict: APPROVE | CHANGES_REQUESTED | INCOMPLETE | BLOCKED:
    Conditions / follow-up:

Approval is invalid if the relevant implementation or base changes. Do not manufacture a GitHub human/account approval; this record is agent evidence. Required platform reviews still apply.

## Launcher-owned run receipt

    Run ID / project identity / local date / Europe-Madrid zone:
    Nominal start / actual start / UTC deadline / monotonic cutoff:
    Effective policy version / capability checks:
    Job IDs / worker identities / actual provider-model routes:
    Admission IDs / persisted reservations / request outcomes:
    Request/input/generated usage (observed vs unknown):
    Quota source / sample time / window IDs / remaining / reset:
    Active leases / owned process groups:
    Final state / stop reason / uncertain actions:

Store sensitive runtime details outside the repository. Commit only sanitized summaries. Counters are controller-owned; an agent's report cannot reset or override them.

## Morning report

    Date / run ID / accepted revision:
    Outcome: what the owner can now do, or why no change was integrated.
    Completed: up to three changes with task/revision/evidence links.
    Quality: tests, real UI checks, review verdict and open material findings.
    Resources: routes used, request/token/time totals where observed;
               subscription readings and uncertainty; cap/stop reason.
    Preserved work: branches/checkpoints and interrupted operations.
    Next night: one primary objective and dependencies.
    Owner input: only exact decisions/actions required, or “None.”

Target 250–450 words. Spanish is permitted for the owner's report. Save locally by default. An idle night can be a few lines; do not invoke an LLM merely to produce it.

## Architecture decision record

    Decision ID / status / date:
    Requirement and observed constraint:
    Options considered:
    Decision and evidence:
    Security/data/licensing implications:
    Consequences / verification / rollback:

Use ADRs for meaningful tradeoffs such as remote transport or persistence changes, not every function or UI detail.

## Weekly continuation decision

    Accepted product outcomes and acceptance rows completed:
    Repeated blockers / regressions / review backlog:
    Actual resource use and missing measurements:
    Most important unresolved product risk:
    Recommendation: CONTINUE | NARROW_SCOPE | PAUSE_FOR_OWNER:
    Smallest next milestone and evidence needed:

Recommend based on useful outcomes, not agent activity. Never automatically delete, archive or abandon the repository because a report recommends pausing.
