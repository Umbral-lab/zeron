# OPS-001E — update-lane clippy debt: the five unhandled read amounts in zeron-update test mocks

Objective: make `cargo clippy --locked -p zeron-update --lib --tests` green on this fork so the
update-lane required check that OPS-001B already lists can actually be satisfied by future PRs,
instead of every candidate inheriting a red baseline check.

Trigger evidence (worker A, 2026-11-15 nightly run, A's host, cargo stable 1.99.1):
- Baseline b880fbef4e132d7d79da1d3edeb9e151affa69e3: clippy exit 101, 5 deny-level
  `unused_io_amount` errors, crates/update/src/lib.rs:1476, 1508, 1546, 1571, 1595.
- Integrated main 53e2bc65016dd0cad41d303561f5b30ebf295f45: identical 5 sites, identical exit 101.
- PR #29 candidate tree (main + 8875924f): identical 5 errors at 1522, 1554, 1592, 1617, 1641,
  shifted only by that PR's additions. Introduced upstream by a67871f8 ("Prevent whale replay from
  starving desktop networking"); six `socket.read(&mut request)` sites exist at both b880fbef and
  the PR #29 head, five of them unbound. Inherited failure, not a regression created by the fork or
  by PR #29.

Acceptance criteria:
1. No clippy error remains in zeron-update lib or test targets.
2. The assertion value is actually used, not discarded: each mock server now binds the read amount
   and asserts it is greater than zero, so a mock that accepted a connection but never read the
   request fails loudly instead of silently proceeding to write a response.
3. `cargo test --locked -p zeron-update --lib --tests` stays green, and
   `rustfmt --edition 2024 --check crates/update/src/lib.rs` reports no diff.
4. No product code path changes: every edited line is inside `#[cfg(test)] mod tests` (the module
   begins at line 1462 of the base file) and the only non-test read site, line 2047
   `let _ = socket.read(&mut request).await;`, is already lint-clean and stays untouched.

Non-goals: no change to update, network or consent behavior; no change to any other crate's clippy
state; the engine-wide rustfmt drift (25 hunks at b880fbef in files untouched here) is out of scope
and stays recorded as baseline debt.

Risk: R1. Test-module-only change with a contained failure mode (a mock assertion failing in a test).
Ambiguity note: it edits the same file OPS-001B edits, so it lands strictly after PR #29 to avoid
concurrent modification of a shared file.

Dependencies: main d6c04ec1b83cd9d76fd05157fd39998fe80ffdc6 (PR #29 merged) as the base.

Owner: worker A (builder). Reviewer: worker B (A-authored change; A cannot be its own independent
reviewer). Branch: task/ops-001e-update-clippy-debt. Base revision: d6c04ec1.

Verification performed on A's host (logs kept at /opt/data/home/zeron-target/logs-1115):
- red baseline: clippy exit 101 with the 5 errors at base d6c04ec1 (recorded in the nightly notes
  above and re-measured on this branch's base checkout).
- green after fix: see the PR body; both commands and their exact counts are recorded there.
- NOT RUN: real update/network behavior (not touched), UI evidence (headless host), Windows matrix.

Rollback: revert the single commit; no persistence, no schema, no dependency change.
