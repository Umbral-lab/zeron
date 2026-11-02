# A independent review — PR #18 (Muse crash diagnostics, product code)

Reviewer: worker A (david-noether[bot]). Date: 2026-11-02 nightly run.
Reviewed base: 5fdb150f. Reviewed head: c65b9407 (branch
worker-b/muse-crash-diagnostics). Task: fix for issue #9 (flaky inherited muse
crash-mid-turn last-words test, 4/11 failure rate measured on A's host
2026-10-31). Risk class: R2 (product code); reviewer is the other worker per
AGENTS.md.

## Actual evidence on A's host (Debian 13 x86_64, 2 cores, warm shared target)

- cargo test --locked -p zeron-harness --test muse -- --test-threads=1:
  18 passed, 0 failed (16 baseline + the 2 new regressions ran; count checked
  with an a_crash name filter: 2 selected / 16 filtered).
- Same targeted command repeated 10 times: 10 ok / 0 fail. The two crash tests
  pass deterministically on A's host.
- Independent RED reproduction: with only crates/harness/src/muse/mod.rs
  reverted to the 5fdb150f version, the new test
  a_crash_after_stdout_closes_still_reports_muses_last_words fails with
  "harness protocol error: Muse stdout closed", cargo exit 101 — matching B's
  RED evidence. The fixed file was then restored and git diff --exit-code HEAD
  confirmed the tree clean at the reviewed head.
- Baseline sanity on unmodified main: a_crash_mid_turn_reports_muses_last_words
  10/10 ok on A's host this night (flake is timing-dependent; B's new fixture
  forces stdout EOF before exit deterministically, which is the sound way to pin
  the race).
- cargo fmt -p zeron-harness --check flags one pre-existing diff in
  crates/harness/src/codex/mod.rs, untouched by this PR (retained baseline
  notice, not introduced by #18).
- cargo clippy --locked -p zeron-harness --tests fails with 2 pre-existing
  deny-level findings in crates/harness/src/skills.rs (non-octal
  Permissions::from_mode(0) at lines 883 and 920, present on main 5fdb150f).
  Not introduced by this PR; recorded as a baseline clippy finding for a future
  bounded task.
- NOT RUN: full-workspace suites, UI evidence (headless host).

## Diff assessment

- muse/mod.rs: replaces the immediate try_wait after a protocol error with a
  250 ms tokio timeout around child.wait(), matching the existing Pi driver
  pattern; exited children yield the crash message with the bounded stderr
  tail, still-live children keep the protocol-error path unchanged. Imports
  (std::time::Duration, tokio) already present.
- fake-muse.py: adds a close_stdout scenario step that closes the stream and
  the underlying descriptor; os import present.
- muse.rs: two new tests — delayed-exit crash must report the real last words;
  live-after-EOF must finish with a protocol error within 3 s and must not
  falsely claim exit. Scenario builder derives from the existing crash.ndjson,
  so the fixture stays anchored to the inherited scenario.
- No dependency, lockfile, Markdown or launcher changes. Scope matches the PR
  claim exactly.

## Verdict

APPROVE for merge at exactly head c65b9407. Issue #9 stays open until the
integrated main is re-verified; close on integration confirmation.
