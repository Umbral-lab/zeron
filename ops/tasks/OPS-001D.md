# OPS-001D — hermetic lookup for inherited package-manager unit tests

ID / title: OPS-001D — make inherited host-tool-dependent unit tests hermetic (package-manager lookup)

Milestone / user outcome: M0 operational trust: review and CI hosts without a
given package manager (npm, brew, pnpm...) must be able to run the inherited
test suites green, so a missing host tool never masquerades as a product
regression in a candidate review.

Status / risk: implemented, awaiting independent review (PR open); R1
(test-hygiene only, no runtime behavior change). Fixture mechanism chosen
(card option 2): the test builds a temp prefix that owns a dummy npm under
its own bin dir; no product-code or ownership.rs change at all, so the
preferred-hook option was not needed.

Owner worker / model route: worker A (Qwen route) authors; B reviews.

Dependencies: the 2026-11-13 A-host investigation recorded in issue #3
(comments 6839653350) and PR #29 (comment 6839653709), with reproduction
logs in /opt/data/home/zeron-target/a1113_run1_control.log,
a1113_run2_npmhidden.log, a1113_run3_base_npmhidden.log (SHA256
f5d5b10a..., 1ce3d4b8..., 858ee4c1...).

Acceptance criteria:
1. harness_updates::tests::package_managed_claude_has_manual_guidance_and_cask_channel
   (and any sibling test in the same area that resolves package managers via
   find_program, e.g. tests asserting can_apply_update true for npm/pnpm/bun/
   volta-owned synthetic paths) passes deterministically regardless of whether
   the host has those tools, without weakening the product rule that an
   update plan requires the owner's tool to exist.
2. Mechanism chosen from: a test-only lookup override/injection point in
   ownership.rs (preferred, bounded), or fixtures that place a dummy
   executable named npm in a temp prefix bin dir. No behavior change outside
   cfg(test).
3. Evidence: targeted cargo test -p zeron-engine --lib harness_updates::tests
   run twice on A's host — normal environment and npm-hidden environment
   (PATH without /usr/local/bin plus ZERON_NO_LOGIN_SHELL=1) — both green at
   the new head; plus one green run on base to bound the diff.
4. The failing assert currently at harness_updates.rs:4339 (head 8875924f) /
   :4286 (main) must not be deleted or weakened: the test must still prove
   can_apply_update true for the npm-owned path when the tool lookup succeeds.

Non-goals: no change to update_plan semantics; no change to PR #29's frozen
head 8875924f; no product change to how real engines resolve package
managers; no broad test refactor.

Allowed paths/components: crates/engine/src/harness_updates/ownership.rs
(test-scoped hook) and crates/engine/src/harness_updates.rs (tests).

Base revision / branch / worktree: base = main at integration time; new
branch task/ops-001d-test-hermeticity in an isolated worktree. Must NOT be
stacked on the frozen #29 head.

Lease: ops001d-hermetic (opened 2026-11-14, closed at run close).

Expected verification and evidence: as acceptance item 3; logs under
/opt/data/home/zeron-target with SHA256 posted to the PR.

Rollback / data impact: revert single commit; no data or network impact.

Budget/time: one bounded nightly slice (targeted test suites only, warm
shared target dir).

Result revision / changed files: branch task/ops-001d-test-hermeticity,
base main 943de4fe; changed files crates/engine/src/harness_updates.rs
(test module only, one test function) and ops/tasks/OPS-001D.md; exact
head recorded in the PR. Sibling-test survey: the Pi apply test and the
ownership.rs unit tests already build their own fake-tool fixtures and
passed on npm-hidden hosts unchanged; the claude npm-path assert was the
only host-tool-dependent assert in this area.

Actual checks (A host, cargo test --locked -p zeron-engine, pinned stable,
shared target dir):
- base 943de4fe, normal env: 41 passed / 0 failed (log a1114_base_normal,
  SHA256 0025bdab...).
- base 943de4fe, npm hidden (PATH without /usr/local/bin,
  ZERON_NO_LOGIN_SHELL=1): 40 passed / 1 failed on the target assert
  (log a1114_base_npmhidden, SHA256 5515536f...) — reproduces the review
  lane blocker at tonight's base.
- head, normal env: 41 passed / 0 failed (log a1114_head_normal, SHA256
  549384a2...).
- head, npm hidden: 41 passed / 0 failed, final tree re-run (log
  a1114_head_npmhidden2, SHA256 daebdf58...).
- full engine --lib at head: 640 passed / 0 failed / 5 ignored, incl. the
  inherited remote_terminals flake passing tonight (log a1114_engine_lib,
  SHA256 e9e6b5ab...).
- clippy -p zeron-engine --lib --tests: exit 0, 119 baseline warnings,
  none in harness_updates.rs.
- rustfmt --edition 2024 --check on harness_updates.rs: two pre-existing
  drift hunks on base and the identical two on head; no new rustfmt diff
  introduced.
- UI evidence: NOT RUN (headless host; no UI touched).

Remaining concerns / next step: awaiting worker B independent review of the
exact PR head (R1 -> Terra-grade review acceptable per AGENTS.md, but B's
review model route currently returns HTTP 400 — see issue #3). If the owner
instead re-cuts #29 onto a main that contains this fix, the npm blocker in
B's pinned environment disappears without touching #29's consent content.
