# Owner-authorized local worker B night task: B-AUDIT-001

The owner explicitly instructed B to begin useful work tonight without waiting for A, who will be configured later. This is B's temporary LOCAL wake-up, not A's shared controller or an independent review of B-authored code. The owner authorizes this setup during daytime; PRODUCT WORK is allowed only 01:00–05:00 Europe/Madrid. The launcher grants at most 600 wall-clock seconds, FOUR outbound model attempts and 4,000 reserved generated tokens total. You have at most three tool rounds: batch deterministic reads and writes. Do not spawn models, create jobs, change routes or bypass the guard. Stop early when done.

Actual route: GPT-6.1 Sol through openai-codex, standard speed, medium effort. Read AGENTS.md and docs/MODEL_BUDGET.md if needed; their owner-supplied instructions apply. The owner-directed supervised baseline audit scope is the exception to waiting for an A-authored candidate. Do not pretend this is independent approval of any implementation. The original nightly caps still constrain this smaller local task. A alone integrates.

Working directory: /home/jetson/Dev/zeron. Assigned branch: audit/local-core-egress, initially based on 60e87c51843f903484510652d975985f2ad3d448. Confirm repository, branch and dirty state; preserve edits. Do not update canonical ops/STATE.md. Allowed implementation is ONLY an audit Markdown document under docs/audits/ and your own immutable task/result artifacts. No product/runtime/scheduler changes.

Objective: deliver a source-backed, tightly scoped local-core egress baseline audit with actionable acceptance for A. Review these concrete source paths, rather than exploring the whole project:
- apps/zeron/src/lib.rs: default edge and auth configuration.
- crates/ui/src/lib.rs and app_update.rs: desktop startup checker and auto-install gating.
- crates/engine/src/lib.rs around 1017–1051: local updater and adapter-prewarm startup.
- crates/update/src/lib.rs: release_base, fetch_latest, Updater::spawn_role/check_loop and desktop_auto_update_enabled.
- crates/engine/tests/local_first.rs around 316–355: inherited test expects release requests in local mode.
- crates/harness/src/acp/mod.rs around 239–256 and 1256–1292; crates/harness/src/adapter_install.rs around 352–414 and 518–583: conditional Grok adapter install at boot.

Inspect actual source before asserting findings. Two likely release blockers to verify are unsolicited vendor update checks despite local/no-auto-install mode, and conditional npm installation at ordinary startup without an explicit install action. Describe prerequisites precisely; do not say all systems always download, invent a network capture or call inherited behavior a new regression. Keep findings separate with severity, source locations, trigger, impact, required outcome and specific test acceptance. No fixes to R2 code; A owns implementation.

Acceptance: one concise English report with pinned source/base/head, reproducible observations, actual checks, limitations, prioritized findings and minimal next tasks. Attempt only targeted checks feasible within the cap. Rust/cargo were not on PATH or ~/.cargo/bin at setup; if still absent, say NOT RUN (toolchain unavailable), not PASS. No installation or full compilation in this task. Actual rendered/network/runtime verification remains pending. Baseline report risk R0; proposed updater/install fixes R2. The overall product/audit verdict is INCOMPLETE, not fabricated independent approval.

Publish the deliverable during this run: create/update a bot-authored issue for B-AUDIT-001, commit the Markdown report as Umbral Agent, push audit/local-core-egress and open a PR for A. Keep issue and PR descriptions synchronized with exact base/head and verification. Use ONLY the authenticated app helper, never bare gh for writes:
`python3 /home/jetson/.hermes/profiles/zeron/scripts/zeron-github-app.py issue ...`
`python3 /home/jetson/.hermes/profiles/zeron/scripts/zeron-github-app.py api ...`
`python3 /home/jetson/.hermes/profiles/zeron/scripts/zeron-github-app.py git push origin audit/local-core-egress`
PR edits may need REST PATCH instead of gh pr edit. The helper holds the owner-authorized key and ephemeral repository-scoped credentials; never display tokens/key contents. Read back created objects to verify bot authorship and remote results. No merge.

Write a compact result JSON to /home/jetson/.hermes/profiles/zeron/nightly/YYYY-MM-DD-result.json using the Europe/Madrid run date: {"task":"B-AUDIT-001","status":"complete" or "partial","issue_url":"...","pr_url":"...","head":"...","checks":[...],"next_action":"..."}. If the guard or toolchain blocks completion, preserve partial findings and explicitly report the missing capability. Save useful evidence before the final request. No daytime continuation and no attempt to spend the whole four-hour window. A completed audit of unchanged main will be skipped deterministically on later nights.
