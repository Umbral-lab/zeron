# Project state

This is the initial template. No implementation, build, test, schedule or runtime setup has been performed by this package. Worker A is the sole canonical writer; the launcher stores enforceable counters and locks separately.

## Identity and authority

- Fork path / remote: to be discovered from the actual checkout.
- Default branch / pinned starting revision: not yet recorded.
- Organization / product name: not finalized by this package.
- Scope: local-first Zeron fork; user-chosen AI providers and direct owned-machine connections allowed.
- Excluded repository: Noether.
- Effective remote push / PR / merge authority: not yet verified.
- External report delivery: none configured.
- Policy version/hash: record after owner/runtime configuration.

## Current position

- Milestone: M0, not started.
- Unattended preflight: NOT VERIFIED.
- Baseline build / tests / visual evidence: NOT RUN.
- Current accepted revision: not yet recorded.
- Active run ID / effective deadline: none.
- Current main objective: establish a truthful fork baseline and verified operational controls.

## Active task and review queue

No tasks have been claimed. Initial queue seeds are in docs/ROADMAP.md. Keep only current task IDs, states, owners, revisions and links here; detailed history belongs in per-task records and reports.

## Decisions and blockers

- Confirm actual configured Qwen route; do not infer an identifier from its display label.
- Verify Terra/Sol availability and authentication through the installed Hermes runtime.
- Map the declarative policy to enforceable runtime controls before unattended execution.
- Use the actual host as the first verified development target; record other platform gaps.

## Last run and next action

- Last run: none.
- Usage and quota observations: none; unknown is not zero.
- Next action: execute the supervised bootstrap prompt.
- Next owner decision: only if bootstrap finds a required capability, permission or product ambiguity not resolved by the charter.

## Compact handoff rule

Keep this file to approximately one page after initialization. Update current facts and links; do not append entire logs or conversations. Preserve older reports separately. Never store secrets or real credential values here.

## Supervised bootstrap overlay (owner-authorized main setup)

The text above is the preserved source template, not current execution evidence.
Current checkout: `https://github.com/Umbral-lab/zeron`, `main`, starting at
`369d42815190ea6c4865c92dc060c54d790f4dcd`. Worker B/Sol imported the instruction
kit without changing inherited product code or documentation. See
[bootstrap/SETUP.md](bootstrap/SETUP.md) for setup evidence and remaining blockers.
No nightly run, product build, independent review or runtime enforcement has been
verified. Unattended inference is BLOCKED. A resumes canonical state ownership
after this owner-authorized bootstrap; B uses its own mailbox thereafter.

## Current-state overlay (worker A, 2026-10-30, appended; imported prefix bytes preserved)

- Milestone M0 in progress. BASE-001 is ready_for_review on branch
  task/base-001-fork-baseline (commit
  5502aae07d7360f404c0aaedb7d591054e09bb65, base 60e87c51843f903484510652d975985f2ad3d448):
  docs/BASELINE.md, ops/tasks/BASE-001.md and A's review at
  ops/mailboxes/worker-a/reviews/REVIEW-SETUP-001.md. Push to origin was blocked
  by a container-wide DNS outage for github.com and api.github.com starting about
  08:46 UTC after successful reads at 08:40 UTC; no remote mutation occurred.
  Work is preserved in worktree /opt/data/home/zeron-wt/base-001.
- A's independent review of B's SETUP-001 artifacts: APPROVE scoped at head
  60e87c51. Open items: the paused job 31ab9d0c0fe6 on B's host cannot be
  verified from A's host; the AGENTS.md commit-identity wording conflicts with
  the owner-configured worker A identity — A commits as david-noether[bot] per
  the loaded charter and flags AGENTS.md for owner clarification.
- Worker A runtime resolved: provider custom, base_url
  http://192.168.10.244:8080/v1, model qwen3.8-flash-next-iq3_xxs (self-hosted
  llama.cpp; unmetered, so quota readings on this route are UNKNOWN by nature).
  ops/policy.json is import-locked (fully hashed in the manifest), so its
  worker_a_runtime_identifier field stays null and this line is the record.
  Terra/Sol live availability: NOT VERIFIED from A's host (B-host concern).
- Toolchain blocker: host e0f0e41ca9d6 (2 cores, headless, user hermes, no
  sudo) has no cargo, rustc or rustup. Linux builds need the GPUI apt package
  list from CONTRIBUTORS.md, an operator root action. BASE-002 (visual and
  workflow baseline) is blocked behind that decision; pre-existing Rust test
  failure state is UNKNOWN.
- Run 2026-10-30 (first on A's host): Hermes cron job 4103065fd3d6 was created
  08:22 UTC and fired 08:37 UTC, outside the nominal 01:00 Europe/Madrid
  window, with no launcher run receipt or policy snapshot; only bounded R0 work
  was performed. The job has no per-job model or timezone pin (schedule
  0 0 * * *, host clock UTC). No schedule, policy or permission change was made.
- Queue: BASE-001 ready_for_review. OPS-001 blocked (missing owner prompts
  docs/agent-prompts/02_GPT_WORKER.md and 03_SOL_AUDIT.md; no enforcement
  snapshot). BASE-002 blocked on the toolchain decision. Next unblocked primary:
  BASE-003 outbound-connection and license-provenance map (R0, no toolchain).
- Credential handling: GitHub App helper verified for Umbral-lab/zeron; remote
  URL clean; repo-local git identity david-noether[bot]. All pushes tonight use
  an explicit bot credential helper with the credential store reset for
  github.com, because a global credential.helper store still exists; removing
  or reordering it is an operator hardening item.
- Next action: once network recovers, fetch-verify origin/main still equals
  60e87c51, then push task/base-001-fork-baseline and this state commit
  (bot helper). B reviews BASE-001. Owner decisions needed: toolchain
  provisioning (root apt plus rustup on this host, or a designated build host),
  AGENTS.md identity wording, and the two missing prompt files.
