# A independent review — PR #17 (B launcher preflight/resume, R2)

Reviewer: worker A (david-noether[bot]). Date: 2026-11-02 nightly run.
Reviewed base: 5fdb150f. Reviewed head: ecad39d1 (branch
worker-b/fix-preflight-resume). Risk class: R2 — process execution, retry
policy, quota gate behavior on worker B's host. Author: worker B; I am the
independent reviewer per AGENTS.md.

## Actual evidence on A's host

- python3 -m unittest discover (ops/worker-b, at the reviewed head): 35 tests,
  34 pass, 1 error — test_http_wire_caps_and_retry_accounting requires httpx,
  not installed and not approved on A's host. That test file is unchanged by
  this PR (verified via git diff; the httpx import is inherited from the
  PR #5/PR #12 version already reviewed). Recorded as NOT RUN on A's host, not
  as a failure of this diff.
- test_preflight.py 12/12 and test_handoff.py 14/14 pass on A's host, including
  the new tests: DNS gets exactly one persisted retry; attempt cap survives a
  restart; launch failure writes the receipt before any network and never
  dispatches; auth failure is not transport-retried; owner resume only for
  proven pre-model failures; no automatic late start; quota block is
  checkpointed and not dispatched; override expires and does not change the
  default; override only clears the reserve after a fresh reading; exhaustion,
  auth and consumption blocks survive the override; quota recovery is once and
  only on the owner-approved date; usage transport timeout becomes UNKNOWN
  instead of crashing startup.
- py_compile clean on all four scripts.
- Diff scope verified with git diff 5fdb150f..ecad39d1 --stat: five files, all
  under ops/worker-b. No product code, no Cargo changes, no ops/policy.json
  change. The import lock on ops/policy.json is respected.

## Design assessment

- Startup/DNS fix: the admission record and a pending result packet are saved
  before any network call; fetch attempts are durably capped at 2 with the
  counter persisted before each attempt; only a transient-transport whitelist
  retries; auth/payment/uncertain errors never retry; a best-effort notice to
  issue #4 is verified read-back and a failure to notify is recorded locally,
  never fatal. Report files open O_NOFOLLOW with 0600 before writing.
- Publication base fix (F-A12-1/F-A12-2): publish now reads the live main ref
  and parents the report commit to it, distinct from the reviewed source;
  recovery uses a new -rebased branch and never force-updates. Verified by the
  two corresponding tests.
- One-night quota exception: activation requires the explicit operator CLI flag
  AND a same-date approval record AND a pre-model-failure state (zero recorded
  requests, no model_started_at, once only). The reserve threshold (70%) is
  bypassed only under that conjunction; a hard 100% exhaustion check was added
  and is not bypassable; observed-consumption thresholds and the rule that
  UNKNOWN cannot clear a known block are preserved; route-block.json is honored
  unless the same-date override is active. The exception is fenced to
  2026-11-01 by the quota_resume_allowed date check and by the same-date rule
  in quota_override_active: on 2026-11-02 (this run) it cannot admit anything.
  B reports the actual covered night ran three model requests under the
  explicit owner instruction; that usage claim is B-host evidence, NOT VERIFIED
  on A's host.

## Findings

- F-A17-1 (notice, non-blocking, recorded): embedding a date-bound exception
  plus a quoted owner instruction in launcher source is an acceptable one-night
  recovery mechanism but becomes stale code after the covered date. Follow-up
  task (owner-visible): replace with an operator-owned override artifact outside
  the worker-writable tree, or remove the clause once the covered night is
  closed. This PR must not become a template for agent-side budget changes.
- No blocking findings.

## Verdict

APPROVE for merge at exactly head ecad39d1, conditional on F-A17-1 being
carried as an open notice for the next owner-visible cleanup decision.
