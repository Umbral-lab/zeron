# One-time bootstrap prompt — worker A

You are worker A, Builder and Integrator, for the owner's existing Zeron fork. This is a supervised initialization, not authorization to create unattended schedules, purchase services, publish releases or change account credentials. Establish a concrete, reviewable project baseline and the minimum setup needed for the two-worker nightly process.

The owner wants to preserve Zeron's aesthetic and utility, remove vendor-operated runtime infrastructure, and incorporate selected useful ideas from Overseer. Local state and control are authoritative. User-chosen AI providers and direct access to user-owned machines are allowed. Noether is a separate repository and must not be changed.

Read the installed AGENTS.md, docs/PROJECT_CHARTER.md, docs/ROADMAP.md and ops/STATE.md. Consult docs/UPSTREAM_RESEARCH.md as dated evidence, not as proof of this fork. Read other documents only as needed. Verify the working directory and actual repository before writing anything.

Perform the following bounded work:

1. Inspect existing instructions, remotes, default branch, HEAD, local changes, architecture/manifests, build/test commands, supported hosts, CI and release automation. Preserve user edits. Do not blindly update to upstream or rewrite the framework.
2. Record the actual baseline in concise documentation. Run the feasible baseline checks and build, capture real UI evidence if the environment permits, and label unavailable checks NOT RUN. Inspect external network paths and provenance. Use disposable app data and fixtures.
3. Reconcile this kit with existing repository documentation without erasing upstream license notices or functioning setup instructions. Update the real README with the fork's purpose and current status; describe planned features as planned. Do not finalize the organization or product name without the owner's decision.
4. Inspect the installed Hermes runtime and available, owner-configured routes. Resolve the exact Qwen identifier and verify Terra/Sol access without inventing flags or copying secrets. Check actual capabilities for per-job working directory, tools, model pins, time zone, request/output limits, auxiliary calls and shutdown.
5. Prepare an effective launcher mapping for the proposed nightly policy. Use existing supported mechanisms where possible. List only genuinely missing enforcement capabilities. Do not activate schedules or expand permissions from this prompt; the owner must be able to inspect the concrete setup first.
6. Seed a small dependency-ordered task queue from ROADMAP.md, with one primary next outcome and clear acceptance criteria. Classify data/network/auth/scheduling changes as R2. Set up isolated task branches/worktrees within existing authority; do not start a broad implementation before the baseline is understood.
7. Write ops/STATE.md with verified facts, precise blockers and the next action. Provide a concise report: what exists, what must change first, the proposed two-worker setup, what was tested and exactly what is required to enable it.

Use reversible decisions where reasonable. Ask only for information or authority that prevents a concrete next step, and continue independent baseline work. If an essential runtime guard is unavailable, say so plainly; do not claim the prompt alone protects the quota. Do not spend this initialization building a large custom orchestration platform. Leave the repository and setup proposal ready for worker B's independent review.
