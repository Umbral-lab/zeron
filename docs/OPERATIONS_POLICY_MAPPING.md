# Policy-to-control mapping on worker A's host

Maps ops/policy.json (declarative) to the actual verified controls on A's host,
per docs/OPERATIONS.md ("map these requirements to actual settings, and record
the effective configuration"). Evidence dates are the 2026-10-31 nightly run
(Umbral-lab/zeron:2026-10-31). This document records status only; it enforces
nothing, and editing it cannot change launcher enforcement.

Legend: ENFORCED = a real control does it on this host; SELF-GUARDED = upheld by
A's own discipline plus this repo's guard script, not by an external controller;
NOT ENFORCED = no control exists on this host; B-HOST = control exists only on
worker B's machine (NOT VERIFIED from A).

## Schedule and window

| Policy rule | Actual control on A's host | Status |
|---|---|---|
| One run per project local date, Europe/Madrid semantics | Hermes cron job 4103065fd3d6 "zeron-worker-a", schedule expression 0 0 * * * (bare UTC; no timezone field in the stored job; verified from /opt/data/cron/jobs.json). Guard verdict probe run live 2026-10-31 against the committed guard: nominal 01:00 Europe/Madrid equals 00:00Z on CET nights (UTC+1) and 23:00Z of the previous day on CEST nights (UTC+2), so the UTC cron lands exactly at nominal on CET nights (verdict OK), 60 minutes late on CEST nights (verdict SKIP_LATE_START — the guard skips, per the no-catch-up rule), also SKIP_LATE_START on the autumn changeover day (e.g. 2026-10-25: cron 00:00Z is 1.0 h past that local date's nominal 23:00Z), and OK on the spring changeover night (2027-03-28: cron 00:00Z equals nominal exactly, deadline 03:00Z). Net effect under the current bare-UTC job: every CEST-period and autumn-changeover night is skipped until the schedule timezone is fixed — a structural gap, not a guard defect. | PARTIAL / ENFORCED-with-gap |
| Duplicate wake events create one run | Hermes cron wrote one admission file with an admission_id and request_id before dispatch (verified live 2026-10-31 00:00:50Z); the A-side guard additionally refuses a second same-date admission via exclusive-create receipt (test-verified 20/20). | ENFORCED (two layers) |
| Deadline = earlier of local 05:00 and 4 elapsed hours, DST-aware | ops/worker-a/run_window_guard.py computes it timezone-aware; tonight's window: nominal 2026-10-31T00:00:00Z, deadline 2026-10-31T04:00:00Z. No external controller enforces it for A. | SELF-GUARDED |
| 15-minute late-start grace, keep original deadline; later starts skip the night | Guard implements and test-covers it (boundary at exactly 15 minutes admitted; 16 minutes skipped). Not enforced externally. | SELF-GUARDED |
| Phase cutoffs derived from the effective deadline | Guard computes freeze/close-findings/integration/shutdown from the deadline; tonight 03:00Z / 03:20Z / 03:45Z / 03:55Z. A follows them; no external stop. | SELF-GUARDED |
| Monotonic elapsed timer; restarts do not extend the deadline | Receipt stores the fixed deadline computed from the nominal start; assert-can-work refuses past-deadline continuation even after a restart. | SELF-GUARDED |
| Operator-owned immutable policy snapshot outside worker write scope | No such snapshot exists on A's host. ops/policy.json is a repo file any worker could edit; nothing outside the repo enforces it for A. B's host has its own guard (PR #5, A-reviewed) — B-HOST, NOT VERIFIED from A. | NOT ENFORCED (A) |

Documented discrepancy (finding F-1): OPERATIONS.md says the autumn clock-change
night is deliberately shortened and the spring night may be only three elapsed
hours. Verified arithmetic with Europe/Madrid zoneinfo: for the 01:00–05:00
window, 2026-10-25 gives 01:00 CEST (23:00Z) to 05:00 CET (04:00Z) = exactly
4.0 elapsed hours, and 2027-03-28 gives 01:00 CET (00:00Z) to 05:00 CEST
(03:00Z) = exactly 4.0 elapsed hours. The window spans the changeover on both
nights, so neither is shorter. The "earlier of 05:00 local and +4h" rule is
what the guard enforces; the prose needs an owner/reviewer correction.

## Models and routes

| Policy rule | Actual control on A's host | Status |
|---|---|---|
| A uses the owner's configured Qwen route, no substitution | config.yaml: model.default = qwen3.8-flash-next-iq3_xxs, provider = custom, providers.custom.base_url = http://192.168.10.244:8080/v1 (self-hosted llama.cpp), active_model/active_provider match; cron job stores model: null (inherits the pinned default). The requested label "qwen 3.8 flash next" resolves to this runtime identifier. | ENFORCED |
| Terra/Sol availability and pins | Not configured or verified on A's host; B's launcher pins gpt-6.1-sol/openai-codex in its own reviewed source — B-HOST. | NOT VERIFIED (A) |
| No automatic paid fallback | No fallback provider chain is configured in config.yaml (auxiliary section commented; compression enabled using the same main route). Nothing forbids the owner from adding one. | SELF-GUARDED / NOT ENFORCED |
| Auxiliary model requests counted (titles, compression, vision) | Context compression is enabled and rides the same self-hosted route; the Hermes runtime does not expose a request counter on this host, so counts remain UNKNOWN (never treated as unlimited). | NOT ENFORCED |

## Budgets, quotas and accounting

| Policy rule | Actual control on A's host | Status |
|---|---|---|
| A nightly/task caps (180/40 requests, 60 min/task, 2 failed approaches) | No durable counter exists on A's host. A applies them as discipline; the run receipt bounds wall-clock by construction. Honest estimate method: session dispatch counting, provider reports no totals. | SELF-GUARDED |
| B combined caps, Terra/Sol caps, unknown-quota mode | Implemented only in B's own launcher guard on B's host (10 min/4 attempts/4000 tokens per job as installed) — B-HOST, NOT VERIFIED from A. | NOT ENFORCED (A) |
| Subscription telemetry and admission thresholds | No quota reading exists for A's self-hosted route (structurally UNKNOWN). A's route is unmetered; the GPT reading gap for B is B-host territory. A never reports UNKNOWN as unlimited. | NOT APPLICABLE (A route) / UNKNOWN |
| Persist admission before dispatch; uncertain usage not refunded | Hermes cron admission file exists pre-dispatch (verified tonight). A-side guard persists its own receipt on admit. No per-request ledger on A's host. | PARTIAL |
| Counters persist across restarts; a new task ID does not reset a budget | No A-side counter exists to persist; the same-date guard receipt does persist and blocks a second run identity on the same date. | PARTIAL |

## Concurrency, leases and integration

| Policy rule | Actual control on A's host | Status |
|---|---|---|
| At most 2 model workers, 1 per active task | Hermes spawn-ledger tracks spawned processes (1 unrelated dashboard entry observed); no model-worker admission control exists on A's host. A honors the limit by discipline and spawned no workers tonight. | SELF-GUARDED |
| Run lock / worker lock / task lease with heartbeat and fencing | Not implemented. Single-integrator mode per OPERATIONS.md fallback: this task record is the lease statement, closed at run end. | NOT ENFORCED (accepted fallback) |
| Integration lock; sole integrator | Held by convention: A is the only writer of main on this host; B has no merge rights exercised. GitHub branch protection status NOT CHECKED. | SELF-GUARDED |
| A owns canonical state (ops/STATE.md); B uses its own mailbox | Honored in practice; no technical lock. | SELF-GUARDED |

## Remote-write authority

Verified tonight as david-noether[bot] (App installation 173158300 covers
Umbral-lab/zeron): read GET git/refs 200; PR/issue listing 200. Scope used:
push task branches, open/update PRs and issue comments on the fork; merges only
into main where protections allow. No releases, no external message delivery
(job deliver target is local). No tokens in remote URLs; credential helper path
per skill noether-bot-identity. A global credential.helper store still exists
(operator hardening item, unchanged).

## Actual run evidence recorded 2026-10-31 (sanitized)

- Hermes cron admission for this run: admission file present, admission_id
  041d95faddca4eafa9534c0760877600, request_id b5163fe42a704b38bdc9ddea0e3105aa,
  created 00:00:50Z; job workdir /opt/data/home/zeron; deliver target local.
- A-side guard admission receipt run-2026-10-31.json (outside Git, mode 0600):
  actual_start 2026-10-31T00:01:00Z, verdict OK, deadline 2026-10-31T04:00:00Z,
  remaining at start 3.98 h; duplicate re-admission returned DUPLICATE and
  reused the original receipt (no re-dispatch).
- Guard verdict probe over representative nights (committed guard, 2026-10-31):
  2026-11-01 OK (elapsed 0.0 h); 2027-03-28 OK (0.0 h, deadline 03:00Z);
  2026-10-24, 2026-10-25, 2027-04-01, 2027-06-15, 2027-10-24 all
  SKIP_LATE_START (elapsed 1.0 h). This is the schedule-timezone gap of the
  row above, measured against the code B is asked to review.
- Guard unit tests: 20/20 PASS on python3 3.14.9 with system zoneinfo.
- NOT RUN: dry-run items 3, 4, 7 partial only (see OPS-001A record); anything
  requiring B's host, quota readings or a display.

## What must change before unattended claims

1. Owner decision on finding F-1 (DST prose vs arithmetic) — wording only, R0.
2. Cron schedule timezone handling: either a supported timezone field in the
   job or a documented UTC-expression swap at each DST boundary; otherwise
   CEST nights arrive 60 minutes late and the guard must skip them.
3. If A-side caps must be real: a durable per-run counter outside worker write
   scope (launcher-owned), per OPERATIONS.md. Until then A's night is honest
   but self-guarded, and OPS-001 stays open.
