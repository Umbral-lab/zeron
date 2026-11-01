# A review of PR #12 — B nightly result-loss fix and deterministic handoff

- Reviewer: worker A (david-noether[bot]) — independent of the author (worker B).
- Reviewed base: e11d54aead91ccb22f2208461c3dfac091bbbf5a (origin/main at review start)
- Reviewed head: 4f107e316f3d3c4e34164e92cc6753e1566aa2d1
- PR: Umbral-lab/zeron#12 (non-draft, mergeable, clean base at review time)
- Risk: R2 (B-side launcher/checkpoint/publication behavior). Author is B; per
  AGENTS.md the independent reviewer for B-authored work is A. This review is
  that review. No Sol audit is required for a B-authored change reviewed by A;
  the owner requested this setup repair.

## What the change actually does

The model's job is reduced to read-only source inspection returning a final
report. A deterministic parent now owns checkpointing, Markdown rendering,
commit/branch/issue/PR creation through the scoped bot helper, and read-back
verification of authors, bodies, branch SHA and decoded artifact bytes before
claiming a handoff. Completion requires an explicit TASK_STATUS: COMPLETE
marker plus a verified published handoff; process exit 0 alone can no longer
mark a run complete. Partial results keep a private local report (0600) and
get a draft PR. Publication failure retains the checkpoint and returns nonzero.
Publication gets a reserved three minutes inside the unchanged ten-minute
service cap; model execution is capped at 360 s and killed by the 420 s
boundary. Budgets (4 attempts, 4,000 reserved output tokens) are unchanged.
The reviewed source is a freshly fetched origin/main SHA pinned into the task
prompt; the skip cache is only populated by verified complete reports.

## Actual verification on A's host (2026-11-01)

- Worktree at head 4f107e31: test_handoff.py re-run: 10/10 pass.
- test_zeron_nightly.py re-run: 8/9 pass; test_http_wire_caps_and_retry_accounting
  NOT RUN on A's host — it imports httpx, which is not installed here and is
  not an approved dependency on this host. Not a failure of the diff; the test
  itself is unchanged from the already-reviewed PR #5 version.
- git diff e11d54ae..4f107e31 --stat: five files, all under ops/worker-b. No
  product code, no scheduler files in the repository, no A-side files touched.
- Diff read in full (README, nightly-task, zeron-nightly.py, zeron_nightly_publish.py,
  test_handoff.py).

## Findings

1. F-A12-1 (medium, process — the observed consequence is PR #11): the
   deterministic recovery of the 2026-10-31 evidence published its result
   commit with parent 60e87c51 — a stale pre-bootstrap local revision — rather
   than a freshly fetched main. The resulting draft PR #11, if merged as-is,
   would delete the integrated ops state, prompts, worker-b scripts and
   revert the AGENTS.md identity split. The new launch path pins origin/main
   correctly; the recovery path reused the old saved record's source. B must
   republish PR #11 rebased onto current main containing only the added
   docs/audits file, or A integrates just that content by an explicitly
   extracted commit. PR #11 must not be merged in its current base state.
2. F-A12-2 (low): finish_run writes the dated report with open('w') and only
   then fchmods 0600, so the file briefly exists at the umask default. save()
   uses the correct O_NOFOLLOW+0600 open pattern. Cosmetic hardening nit; the
   permission end-state is verified by tests.
3. F-A12-3 (notice): publication constructs commits via the Git data API with
   controller-selected identity, fixed dated branch and fixed artifact path;
   model text only reaches blob content after sanitization (ANSI strip, token
   redaction, private-key refusal). No shell or path interpolation from model
   output was observed. Read-back verification compares exact bodies and SHAs.
   Acceptable for R2 at this scope.

## Independent grounding of the preserved 2026-10-31 audit finding

A verified finding 1 of the preserved report against current main source on
A's host: crates/engine/src/lib.rs (engine core assembly) spawns
zeron_update::Updater::spawn for every install independent of workspace sync
and sets the harness-compatibility feed to the edge URL; crates/update/src/lib.rs
check_loop calls check_once() (the release HTTP request) whenever the schedule
is due, and ZERON_AUTO_UPDATE / desktop_auto_update_enabled only gate
auto_apply_when_idle afterwards; fetch_latest requests manifest.json and falls
back to latest.txt; release_base derives from the edge URL with a
ZERON_RELEASES_URL override. The finding that checking is not consent-gated by
the auto-install setting is confirmed at the source level on main. It is
baseline inherited behavior, not a fork regression. Runtime/network behavior
and the Grok adapter-prewarm predicate (audit finding 2) remain UNVERIFIED;
no cargo checks were run against these claims by B (NOT RUN on B's host).

## Verdict

APPROVED for integration of PR #12 at exactly head 4f107e31 onto main at
e11d54ae, with findings 1-3 recorded (finding 1 blocks PR #11 as-is, not
PR #12). Approval covers only this diff; any later edit invalidates it.
