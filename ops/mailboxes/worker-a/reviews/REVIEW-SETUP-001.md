# Review record REVIEW-SETUP-001 (worker A reviews worker B)

Review ID / task IDs: REVIEW-SETUP-001 / SETUP-001.
Reviewer worker / model route / UTC timestamp: A (david-noether[bot]) /
qwen3.8-flash-next-iq3_xxs, custom provider, self-hosted llama.cpp /
2026-10-30T08:44Z.
Author worker(s) / independence check: B (Umbral Agent commit identity,
umbral-labs-dev[bot], on a different host). Reviewer is a distinct worker and
distinct machine route; independence holds.
Reviewed base / head: base 369d42815190ea6c4865c92dc060c54d790f4dcd, head
60e87c51843f903484510652d975985f2ad3d448. B's commits are 989b110c (15 files:
instruction docs, ops bootstrap, ops/policy.json, scripts/ops) and 60e87c51
(4-line SETUP.md clarification). No vendor product code, manifests or legal
notices touched.
Scope actually inspected: scripts/ops/preflight.py and scripts/ops/
test_preflight.py line by line; ops/bootstrap/import-manifest.json; the prefix
hash semantics; the full file lists of both B commits; inherited product files
left unchanged (matches bootstrap claims).
Checks independently verified (run by A on A's host):
- python3 -m unittest discover -s scripts/ops: 6 tests OK.
- python3 scripts/ops/preflight.py: import_integrity PASS, 10 files,
  unattended_inference BLOCKED, model_dispatches 0, zero network or
  subprocess use observed (code confirms neither).
Findings:
1. Info — preflight.py always reports BLOCKED regardless of state. Correct
   fail-safe; it is a diagnostic, not a guard, as its own docstring says.
   No change requested.
2. Info — import integrity verifies only the first N bytes of each imported
   file; appended annotations are not hash-covered. This matches the declared
   prefix-retention rule. Accepted; residual risk (annotation tampering is
   undetectable) is low because annotations are agent-owned records, not the
   owner's kit bytes.
3. Low / scope — the paused script-only cron job 31ab9d0c0fe6 lives on B's
   host profile (/home/jetson/.hermes/profiles/zeron) and cannot be read from
   A's host. Its paused state remains B's recorded evidence, not A-verified
   fact. Activation on that host requires operator verification there.
4. Medium / owner decision — commit identity conflict: AGENTS.md says future
   commits in this checkout use Umbral Agent with the umbral-labs-dev[bot]
   email, while the owner-configured worker A charter and cron job mandate
   david-noether[bot] via GitHub App installation 173158300. A commits tonight
   as david-noether[bot] per the loaded skill. AGENTS.md wording needs an
   owner-level clarification distinguishing A and B identities. Not a defect
   in B's diff.
Limits / unverified scope: B's host scheduler state, B's host git identity,
GitHub-side display of bot identities, and anything outside the two B commits.
Verdict: APPROVE (scoped) — SETUP-001 repository artifacts (diagnostics,
import manifest, ops/docs bootstrap) are approved at head
60e87c51843f903484510652d975985f2ad3d448 for R0 operational use, with
findings 3 and 4 carried into ops/STATE.md as open items. No product
acceptance is implied, and this approval does not authorize any scheduler
activation.
Conditions / follow-up: owner resolves the commit-identity conflict wording;
operator verifies the B-host paused job before any activation; OPS-001 remains
its own R2 task with its own review.
