# Review record: PR #28 (worker B controller repair) — reviewed and integrated by worker A

- Reviewed base: 3b99095e2a31adf3593197ddad26057b8367f80a (main, verified as pre-merge target)
- Reviewed head: a3199d6681c1c47aa658d07405bc0279ae856540 (merge-base equals the reviewed base; single commit)
- Diff: 7 files, all under ops/worker-b, 743 insertions / 299 deletions (nightly-task.md, test_audit_review.py new, test_handoff.py rewritten, test_zeron_nightly.py, zeron-nightly.py, zeron_audit.py new, zeron_nightly_publish.py)
- Risk: R2 (worker-B launcher/review controller: model dispatch wiring, remote publication, executed-check execution)

Executed on A's host at the exact head (fresh worktree, offline suites):
- python3 -m unittest discover -p test_*.py in ops/worker-b: 59 ran / 58 pass / 1 error
  (test_zeron_nightly.test_http_wire_caps_and_retry_accounting ModuleNotFoundError: httpx —
  inherited host gap, unchanged inherited test; recorded NOT RUN, not pass).
- Base tree at 3b99095e in a second isolated worktree: 41 ran / 40 pass / same single inherited
  httpx error. Candidate adds 18 new offline tests; failure profile identical on both sides.

Diff audit:
- Zero diff lines touch request/token/minute caps, MODEL pins, the systemd timer/service files
  or provider routing. run_budget_seconds derives from the existing ledger inference_deadline,
  clamped to [1,360].
- Fixed-argv command construction only (git fetch/show/diff with 40-hex SHA validation; PR text
  cannot inject commands). select_candidate pins exact base/head, excludes drafts and self-authored
  PRs, refuses truncated (>=100) discovery, skips heads with a decisive same-head review, enforces
  a 12-file bounded scope.
- Publication narrowed: nightly report branch + issue + PR creation removed; one read-back-verified
  review posts only on the existing candidate PR; model APPROVE downgrades to INCOMPLETE unless
  coverage is complete, planned checks executed with recorded returncodes/logs, findings resolved
  and bounded scope holds. supervise deadline expiry returns 124 consistently.

Findings:
- F-A28-1 (retained notice): an APPROVE posts as a platform review under B's bot identity while
  the shared GitHub credential model cannot provide two distinct platform reviewers; branch
  protection state remains NOT VERIFIED for the App (operator item). Platform merge authority
  must keep honoring required human review; this controller is not platform approval semantics.
- F-A28-2 (NOT RUN on A's host): real Sol/B-host dispatch, ledger wiring at launch, timer
  activation and live candidate reviews are B-host evidence; verified here only as offline
  deterministic tests. No real model dispatch was executed from this controller on A's host.
- F-A28-3 (notice): test count depends on discovery root (A used ops/worker-b: 59 head / 41
  base); pin the invocation in B's README so both hosts compare the same suite.

Verdict: APPROVED for the exact head a3199d66 on base 3b99095e, with retained notices. Approval
covers only this diff.

Integration (worker A, under the integration lock, run-2026-11-08):
- Local merge 45a1927022f013d4db8ad6b00ead9606b51875ed on main; target verified equal to the
  reviewed base before the advance; ops/worker-b paths byte-identical to the reviewed head on the
  merged tree (empty diff); merged-tree discovery re-run 59 ran / 58 pass / 1 inherited NOT RUN.
- Pushed to main and read back (ls-remote 45a19270); GitHub merge API confirmed merged=true with
  merge_commit_sha exactly 45a19270. PR #28 closed/merged; integration comment posted.
