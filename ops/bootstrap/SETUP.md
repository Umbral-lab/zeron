# Supervised bootstrap handoff

## Task SETUP-001

- Objective: install the owner's instruction kit into the existing fork without losing original rules; configure agent commit identity; prepare safe operational diagnostics.
- Author: worker B, actual interactive route GPT-6.1 Sol / openai-codex.
- Owner authorization: one-time setup on main; no history rewriting. Normal branch/worktree and A-only integration rules apply after bootstrap.
- Base: `369d42815190ea6c4865c92dc060c54d790f4dcd`.
- Checkout/remote: `/home/jetson/Dev/zeron`, `https://github.com/Umbral-lab/zeron`, main. Initial tracked tree was clean; only repo/ was untracked.
- Status: instruction import verified; diagnostic code ready for A/owner review; OPS-001 BLOCKED. No independent approval claimed.
- Risk: R0 instruction import; operational script/schedule changes require R2 scrutiny. No model-launching or enforcement code was implemented.
- Dependencies: owner-supplied kit; installed Hermes. Runtime activation additionally requires the missing inputs below.
- Scope: imported AGENTS/docs/ops, this bootstrap record, scripts/ops diagnostics, repository-local Git identity, and a paused script-only job in the zeron Hermes profile.
- Non-goals: product changes, full M0 build/UI baseline, implementing a budget controller, running an audit without a candidate, changing models, live unattended execution, release publication.
- Acceptance: original instruction bytes retained, inherited files intact, repo/ absent and excluded from Git, identity verified, deterministic diagnostic exercised, unattended inference not enabled.
- Allocation: supervised setup only; no launcher-supplied nightly budget, run ID or deadline exists. Stop at this checkpoint rather than starting implementation or a nightly audit.
- Rollback: preserve this commit/artifact, then revert it after coordination; revert local Git identity only to an operator-selected identity. Remove only job `31ab9d0c0fe6` and its named wrapper if abandoning setup. Never reset the checkout or delete unpreserved work.

## What was preserved

All ten instruction files were moved to matching canonical root/docs/ops paths.
`ops/bootstrap/import-manifest.json` records their original lengths and SHA-256
hashes. The original bytes remain intact; AGENTS.md and ops/STATE.md have appended
bootstrap annotations. Only Finder's .DS_Store metadata was discarded. repo/ is
absent, never staged, and now ignored.

The original CONTRIBUTORS.md, ARCHITECTURE.md, CONTEXT.md, README files, LICENSE
and THIRD_PARTY_NOTICES.md remain unchanged. AGENTS.md explicitly incorporates the
original contributor build/test, compatibility, UI, security, PR and license rules.
No vendor source, manifests, workflows or legal notices were changed.

Repository-local Git author and committer defaults:
`Umbral Agent <340979744+umbral-labs-dev[bot]@users.noreply.github.com>`.
The GitHub public account lookup returned login `umbral-labs-dev[bot]`, numeric ID
`340979744`, type Bot. The suffix occurs once; GitHub controls displayed bot identity.
No credential was read or changed and inherited commits retain their authors.

## Runtime evidence

- Installed CLI: Hermes Agent v0.22.5 (2026.9.24), local revision bf0203a794a0.
- Active runtime home: `/home/jetson/.hermes/profiles/zeron`.
- Current conversation runs Sol. Persisted config reports gpt-6.1-terra / openai-codex; this does not establish a nightly Sol pin. Neither was changed.
- Non-inference `hermes usage --provider openai-codex --json` succeeded at `2026-10-29T20:19:13.092622+00:00`: session 6% used, weekly 56% used. This historical sample is not a fresh admission reading, a complete ledger or attributable project consumption.
- Cron job `31ab9d0c0fe6`: `0 1 * * *`, **paused**, no_agent=true, local delivery, fixed project workdir. Read-back confirmed disabled and next_run_at=null.
- Wrapper: `/home/jetson/.hermes/profiles/zeron/scripts/zeron-bootstrap-preflight.py` runs only the repository's read-only diagnostic. Its execution was tested directly, not through an unattended scheduler tick.
- The installed cron CLI/tool exposes no per-job timezone option, despite current online docs describing one. No explicit profile timezone was found by the targeted config lookup. The paused expression is NOT claimed to be mapped to Europe/Madrid; an operator must verify a supported timezone mapping before activation. Do not edit job storage blindly.
- The diagnostic always reports unattended inference BLOCKED. It is not an admission guard, quota meter, immutable policy boundary, controller or proof of enforcement. Resuming it would only produce diagnostics, never launch workers.

## Actual verification

PASS:

- `python3 -m unittest discover -s scripts/ops -p 'test_*.py' -v`: six tests passed (retained originals, append-only annotations, tampering, missing files, staging residue, missing/present prompts never enabling inference).
- `python3 scripts/ops/preflight.py`: ten imported files, import_integrity PASS, errors empty, unattended_inference BLOCKED, zero model dispatches.
- Direct execution of the installed wrapper returned the same diagnostic.
- `git diff --check`.
- `git diff --exit-code 369d42815190ea6c4865c92dc060c54d790f4dcd -- CONTRIBUTORS.md ARCHITECTURE.md CONTEXT.md 'README*' LICENSE THIRD_PARTY_NOTICES.md`: unchanged.
- Cron read-back: exactly one zeron-profile job, paused and script-only. No existing jobs were modified.

NOT RUN: product builds, Rust suites, real UI baselines, OPS-001 dry-run matrix,
provider model-availability probes, worker concurrency/lease tests, independent
review, scheduled tick. No synthetic approval or product acceptance is implied.

## Owner authorization for automation

The owner explicitly approved automations after supplying the worker prompts.
Permission to configure the planned automation is therefore not an outstanding
blocker. This approval does not establish that a functioning launcher exists or
change the documented model/budget limits. The only installed job on B's host is
currently a paused, script-only diagnostic, not a nightly worker launcher.
The controller host and cross-machine handoff mechanism must be established with
A before activating worker execution; do not create independent competing
schedulers or present the diagnostic as working development automation.

## Required next inputs and work

1. RESOLVED: the owner supplied `prompts.zip`. All four Markdown files are installed byte-for-byte under `docs/agent-prompts/`: `00_BOOTSTRAP.md` and `01_BUILDER.md` belong to A; `02_GPT_WORKER.md` is B/Terra and `03_SOL_AUDIT.md` is B/Sol. B uses the prompt matching the launcher's actual model selection; receiving these files does not admit an audit or authorize model/schedule changes.
2. Operator must resolve A's exact configured Qwen provider/model identifier; no default-profile inspection or guessed substitution was performed.
3. A/owner independently reviews B-authored diagnostic code and scheduler setup. B cannot independently approve its own setup with a Sol identity switch. Independent review remains required for acceptance and activation, not for publishing the handoff commit. The owner clarified that A runs on another computer: keep the authorized GitHub remote updated so A can fetch work and review artifacts. Use task branches after bootstrap; do not treat pushing a branch as approval or permission to integrate it.
4. Assign OPS-001 to A with a bounded task packet, budget/deadline and operator-owned effective policy; verify request-boundary metering including SDK/auxiliary calls, output limits, durable counters, fallback pins, locks/fencing, quota blocks, shutdown, DST and restart behavior against OPERATIONS.md's nine cases. This is a separate R2 implementation if no controller exists.
5. Verify supported Europe/Madrid schedule mapping, isolated A/B/integrator worktrees, actual model availability and fresh quota telemetry. Only the operator may activate reviewed controls and inference jobs. Do not simply resume this diagnostic expecting workers to run.
6. A then owns canonical state, queue and integration. B writes immutable review artifacts under ops/mailboxes/worker-b/ on B's branch/worktree. A must supply the frozen exact base/head candidate and evidence before B's bounded daily Sol audit.

No nightly product progress, enforced budget, remote push authority, deployment or
release authorization is asserted by this bootstrap.
