# REVIEW-PR5: independent review of worker B's local nightly wake-up setup

Review ID / task IDs: REVIEW-PR5 / B-SETUP (PR #5, issue #4; related OPS-001)
Reviewer worker / model route / UTC timestamp: A (david-noether[bot]) /
qwen3.8-flash-next-iq3_xxs self-hosted llama.cpp / 2026-10-30 ~19:20 UTC
Author worker(s) / independence check: authored by worker B
(umbral-labs-dev[bot]); A authored none of the reviewed code; review is
independent.
Reviewed base / head: base 60e87c51843f903484510652d975985f2ad3d448, head
61b12b45c2db4ff863ae9c4b56791e1a85fc90e8. Resulting integration tree after
merge is recorded in the merge commit fetched from main.
Scope actually inspected: full diff (7 files, +585 lines: .gitignore,
ops/worker-b README.md, nightly-task.md, zeron-nightly.py,
test_zeron_nightly.py, systemd service and timer units). zeron-nightly.py
read end to end (window math, quota ledger, HTTP guard, embedded AIAgent
launcher, supervisor kill path, admission/idempotency logic).
Checks independently verified on A's host:
1. All nine tests re-executed from a scratch copy against the exact head
   files, using this host's installed Hermes interpreter
   (/opt/hermes/.venv/bin/python3): 9 passed, 0 failed. Without the Hermes
   interpreter the httpx/guard test cannot import hermes_cli — expected,
   recorded as environment coupling, not a defect of B's code.
2. Static review of the guard allowlist: inference POST restricted to
   chatgpt.com /backend-api/codex/... with pinned gpt-6.1-sol, model
   substitution and service_tier removed, max_output_tokens rewritten on the
   wire body, alternate origins refused, 401/402/403/429 parks the route and
   exits without retry.
3. Window/deadline logic: admission only 01:00-01:15 Europe/Madrid, deadline
   is the earlier of local 05:00 and 4 elapsed hours, monotonic cutoff
   enforced before each reserve, durable same-date admission receipt written
   before any dispatch, per-date idempotency, skip when the completed
   source-audit packet matches unchanged main, route-block file survives
   UNKNOWN readings.
4. Process hygiene: start_new_session process group, SIGTERM then SIGKILL
   escalation on the supervisor deadline, systemd RuntimeMaxSec=600 +
   KillMode=control-group as a second layer, no restart, UMask 0077, no
   Persistent catch-up on the timer.
Findings:
- MEDIUM (design note, accepted): quota consumption observation is per-night
  only — the quota baseline is stored inside the dated receipt, so
  cumulative account drift across nights is not counted beyond the 70%
  reserve, the parked-route file and the per-night request/output caps. B's
  README states the caps honestly. Required outcome: A's future shared
  controller (OPS-001) must keep cross-run counters; do not treat this
  per-night design as the final OPS-001 answer.
- LOW: launch() couples to a literal launcher code string (runpy marker) and
  to hermes_cli internals. A Hermes version change makes the guard fail
  closed (refuses to dispatch) rather than silently bypass — acceptable,
  but B's next run after any Hermes update must re-verify the marker test.
- LOW: the guard allows all api.github.com hosts/methods (needed for B's
  bot handoffs). Combined with B's enabled terminal/file toolsets, egress
  scope depends on the task text, not only the guard. Acceptable for the
  bounded B-AUDIT-001 task; revisit if B's task scope widens.
- NOTICE: A cannot verify from A's host the installed copies on B's machine,
  the systemd timer's live state, lingering, or B's actual first-run
  receipt. Those remain B-host facts reported by B; labelled NOT VERIFIED
  (remote host), not claimed as A-verified.
- NOTICE: PR base 60e87c51 vs current main 9f1c6979 — merge tree re-checked
  after merge (files are disjoint from main-side changes); the nine tests
  were re-run from the merged tree after integration (see merge note in the
  PR thread).
Limits / unreviewed scope: B's host-side installation identity between repo
copies and installed files; actual first nightly receipt (will exist only
after the 01:00 wake-up).
Verdict: APPROVE for integration of the exact head 61b12b45 as the recorded
source of B's owner-authorized local setup. Not an OPS-001 acceptance; the
shared controller and the cross-run counters remain open under issue #3.
Conditions / follow-up: A disables/withholds any A-side dispatch of B while
B's local timer is active (single B dispatcher rule, stated in B's README);
after the first scheduled run, A consumes B's dated receipt/result packet;
OPS-001 dry-run items 1-9 stay open.
