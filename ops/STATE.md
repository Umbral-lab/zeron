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

## Current position (worker A; supersedes the earlier 2026-10-30/31 overlays; imported prefix bytes preserved)

- Runs 2026-10-30: three A activities on this date — morning bootstrap-baseline
  run (job 4103065fd3d6, 08:37 UTC, bounded R0), owner-directed integration of
  PR #2 (18:02 UTC, merge 660343fe, prompts byte-verified, AGENTS.md identity
  split b7705159 resolved the identity wording decision), and an owner-fired
  daytime test of the nightly-builder configuration (~19:06 UTC start,
  supervised, outside the 01:00 Europe/Madrid product window by owner
  instruction; not an unattended nightly; no schedule created or enabled).
- Bootstrap closed (BASE-001 verified facts below); the nightly run starting
  2026-10-31 00:00 UTC follows docs/agent-prompts/01_BUILDER.md.
- Runs 2026-10-31: one bounded scheduled nightly run (job 4103065fd3d6,
  actual start 00:01 UTC, deadline 04:00 UTC, phase cutoffs freeze 03:00 /
  close-findings 03:30 / integration 03:45 / shutdown 03:55 UTC; A-guard
  receipt run-2026-10-31, verdict OK, finalized at close). First nightly
  under 01_BUILDER.md.
- Toolchain live on A's host (owner decision 1 executed): GPUI apt packages
  installed by the owner plus libssl-dev (the CONTRIBUTORS.md gap); rustup
  pinned stable 1.99.1; cold full build of -p zeron succeeded 17:35 UTC
  (log zeron-target/build2.log, 0.9s incremental no-op; cargo flags one
  future-incompat dependency, proc-macro-error2 — retained notice). Shared
  CARGO_TARGET_DIR /opt/data/home/zeron-target for all worktrees.
- Queue (single-integrator mode; A owns this file):
  - BASE-001 ready_for_review: branch task/base-001-fork-baseline, stable
    review head c78e2601 (PR #6, base 7ca3a99d). Nightly run added
    verified targeted evidence to docs/BASELINE.md: zeron-proto 98/98;
    zeron-sync 83 pass + 2 ignored only with --features mock-server (plain
    invocation fails to compile the inherited registry_client integration
    test — recorded baseline nuance, not a regression); zeron-veil --lib
    16/16; zeron-rpc --lib 25/25; zeron-notify 3/3; zeron-harness
    482+87+10 pass across targets; headless CLI evidence (version 0.2.130,
    subcommand surface, status with local-only mode and signed-out auth,
    loopback-only IPC, engine start and clean shutdown under an isolated
    disposable data dir); zeron-agent-control and zeron-i18n package names
    verified absent. Flaky inherited test a_crash_mid_turn_reports_muses_-
    last_words failed 4/11 isolated target runs — filed as issue #9, not a
    claimed regression. UI evidence still NOT RUN (headless). Awaiting B's
    independent review at head c78e2601.
  - BASE-003 ready_for_review: docs/CONNECTIONS_AND_LICENSES.md,
    ops/tasks/BASE-003.md and live license evidence; branch
    task/base-003-connection-license-map head a0ef50a2, PR #7. Awaiting B's
    review. Key findings: automatic vendor-edge update polling and harness
    compatibility fetches are mapped with file evidence; git pins
    zeronsh/zui and zeronsh/gpui-component report license NOASSERTION —
    release-blocking UNVERIFIED gap for M4; transitive audit of the 1155
    lockfile entries NOT RUN pending an owner/reviewed tooling decision.
  - OPS-001A ready_for_review (run 2026-10-31): A-side run-window guard +
    receipts (ops/worker-a/run_window_guard.py, 20/20 tests PASS on host,
    incl. both DST transition nights) + docs/OPERATIONS_POLICY_MAPPING.md +
    ops/tasks/OPS-001A.md; branch task/ops-001a-run-receipt, stable review
    head d0fcab13 (PR #8, base e3f01754). Live same-date receipt created
    pre-work (outside Git, 0600); duplicate admission reused; run finalized
    at close with stop reason. R2: needs B/Sol review before integration.
    Findings: F-1 OPERATIONS.md DST prose contradicts verified arithmetic
    (both 01:00–05:00 transition nights are exactly 4.0 elapsed hours;
    wording decision needed, R0); F-2 Hermes cron job stores a bare UTC
    expression 0 0 * * * with no timezone field — live guard verdict probe:
    OK on CET nights and on the spring-changeover night (deadline 03:00Z),
    SKIP_LATE_START on every CEST night (arrives 02:00 local) and on the
    autumn-changeover night; forecast recorded for 2026-11-01 (CET, OK).
    Structural schedule-timezone gap until the owner sets the cron timezone;
    NOT ENFORCED on A's host (operator-owned controller gap, F-3).
  - B-SETUP (B's local nightly wake-up): PR #5 reviewed by A (nine tests
    re-run on A's host at head 61b12b45, 9/9; record at
    ops/mailboxes/worker-a/reviews/REVIEW-PR5.md) and integrated as merge
    7ca3a99d; merged files verified byte-identical and 9/9 re-run on the
    merged tree. B's owner-authorized local systemd timer is active on B's
    host; first scheduled unattended wake 2026-10-31 01:00 Europe/Madrid.
    Single-dispatcher rule: A will not dispatch B while that timer exists.
    First scheduled wake 2026-10-31 01:00 CET fired but lost its result:
    four attempts exhausted in three tool rounds with no file or GitHub
    handoff (cause recorded in B's README failure section). B repaired its
    launcher (deterministic checkpoint/publication outside the model budget)
    and republished the recovered evidence same-day: issue #10 + draft PR #11
    (result PARTIAL) plus fix PR #12. A reviewed PR #12 independently at head
    4f107e31 (test_handoff 10/10 re-run on A's host; test_http_wire_caps...
    NOT RUN on A's host — httpx not installed here, test unchanged from the
    reviewed PR #5 version) and integrated it as merge 1bb666f9; merged tree
    byte-identical for ops/worker-b and re-tested 10/10. Review record:
    ops/mailboxes/worker-a/reviews/REVIEW-PR12.md. Open finding F-A12-1: B's
    recovery published PR #11 with parent 60e87c51 (stale pre-bootstrap
    revision) — merging it as-is would delete integrated ops state; next B
    action is a rebased republish or A-side explicit extraction. B's second
    wake (2026-11-01 01:00 CET, fixed pipeline) outcome NOT VERIFIED at A's
    close (~00:40 UTC, before B's job window). Reviews of A's PRs #6/#7/#8
    remain outstanding from B.
  - BASE-002 unblocked (toolchain + binary exist); still NOT STARTED: real
    UI evidence needs a display path — remains NOT RUN on headless host.
  - OPS-001 open (issue #3): declarative policy only; no launcher receipt or
    immutable snapshot on A's host; dry-run items 1-9 largely NOT VERIFIED;
    carried findings from REVIEW-PR5 (per-night quota baseline, launcher
    coupling, guard egress breadth, B-host facts NOT VERIFIED). Next A step:
    a minimal A-side run receipt plus policy mapping as a separate reviewed
    task before any unattended claim.
  - OPS-001B next A-owned task (added 2026-11-01, R2, not started): the
    release-check consent boundary. B's preserved 2026-10-31 audit finding 1
    (release checking not consent-gated by the auto-install setting) is now
    source-grounded by A on current main: Updater::spawn runs for every
    install independent of workspace sync (crates/engine/src/lib.rs core
    assembly); check_loop issues check_once HTTP whenever due while
    ZERON_AUTO_UPDATE / desktop_auto_update_enabled gate only
    auto_apply_when_idle (crates/update/src/lib.rs); fetch_latest does
    manifest.json with latest.txt fallback; release_base derives from the
    edge URL with a ZERON_RELEASES_URL override. Baseline inherited behavior,
    not a fork regression. B's finding 2 (conditional Grok adapter npm
    prewarm at startup) remains UNVERIFIED — predicate reachability needs
    deterministic resolver fixtures. Acceptance direction from B's packet:
    default local startup/idle issues no release requests without explicit
    permission; checking vs installing separated; explicit user-triggered
    checks preserved. Inherited local_first test expects release requests
    after check_now — changing this is an R2 product decision needing owner
    visibility and B/Sol review.
  - OPS-001B status 2026-11-08: PR #19 (head ef4f86f6) closed without merge,
    replaced by PR #29 = bounded re-cut: branch task/ops-001b-consent-narrow,
    single commit 8875924faccee44842e4506a5f87b48b4dcae6f9 directly on main
    3b99095e, diff exactly 13 files (927+/46-) with every consent file
    byte-identical to ef4f86f6 (verified empty diff on all 13 paths). Closes
    B's 2026-11-07 blocking scope finding (92-path diff). The ~79 rustfmt-drift
    files stay at main's content; ef4f86f6 is retained locally as
    drift/ops-001b-rustfmt-20261108 for a possible separate bounded formatting
    task (nothing pushed). Correction recorded in the task record: the previous
    claim that origin/main copies of the drift files were rustfmt-clean was
    false — main 3b99095e is the unformatted side (e.g. crates/audio/src/aec.rs).
    Unmerged: awaits Sol review of PR #29's exact head.
- Worker A runtime (unchanged): provider custom, base_url
  http://192.168.10.244:8080/v1, model qwen3.8-flash-next-iq3_xxs
  (self-hosted llama.cpp; unmetered — quota UNKNOWN by nature, never treated
  as unlimited). ops/policy.json import-locked; this line is the record.
  Terra/Sol: NOT VERIFIED from A's host (B-host concern).
- Nightly usage 2026-11-06: Qwen self-hosted route only (one agent session +
  bounded deterministic build/test probes; provider does not report totals —
  quota UNKNOWN, never treated as unlimited). No Terra/Sol/GPT use, no
  provider error retries, no new schedules; B ran its own jobs on B's host.
- Credential handling (unchanged notices): GitHub App helper verified; repo
  identity david-noether[bot]; every remote write this run used the explicit
  bot credential helper; a global credential.helper store still exists and
  remains an operator hardening item.
- Checks verified 2026-10-30 evening: DNS recovered; origin/main fetch
  read-back; App whoami; 9/9 B tests (twice, incl. merged tree); cargo fetch
  exit 0; cargo test --locked -p zeron-update 18/18; cargo test --locked -p
  zeron-client --lib 35/35; live crates.io (69 direct
  deps) and GitHub license lookups; git ls-remote pins exist. NOT RUN:
  broader cargo suites, UI evidence (headless), transitive license audit.
- Checks verified 2026-10-31 nightly: A-guard admit/status/finalize live
  (verdict OK, deadline 04:00Z, duplicate admission reused, receipts 0600
  outside Git; one defect found and fixed in-run: the finalize rewrite left
  tonight's live receipt 0644 — now 0600-enforced with a regression assert,
  head d0fcab13); guard unit tests 20/20; cargo test --locked targeted suites
  as listed under BASE-001 above; zeron binary --help/-V/status/headless/
  sync exercised under an isolated disposable ZERON_DATA_DIR with no login
  and loopback IPC only (no vendor-edge contact observed in those logs);
  muse flake measured over 11 isolated target runs; remote-write probes:
  App whoami, PR mergeable=true/clean-base for #6/#7/#8, main branch
  protection API 403 for the App (protection state NOT VERIFIED — operator
  item). NOT RUN: full-workspace test/clippy run, UI evidence (headless),
  transitive license audit, B-host state.
- Checks verified 2026-11-01 nightly: guard admit OK_LATE_GRACE (start
  00:01:40Z, deadline 04:00Z, receipts 0600 outside Git); remote reads via App
  token (PR/issue listing, review lists); B test suites re-run on A's host at
  PR #12 head (10/10 handoff; 8/9 + 1 NOT RUN httpx-missing on the inherited
  file); merged-tree byte-identity diff for ops/worker-b and 10/10 re-run on
  main 1bb666f9 before push; A source grounding of audit finding 1 against
  crates/engine/src/lib.rs and crates/update/src/lib.rs on main (no cargo run
  needed for these reads). NOT RUN: full-workspace cargo suites, clippy, UI
  evidence (headless), B-host state, B's 2026-11-01 wake outcome.
- Last nightly usage 2026-11-01: Qwen self-hosted route only (one agent
  session plus bounded deterministic probes; provider does not report totals —
  quota UNKNOWN, never treated as unlimited); no Terra/Sol/GPT use; no error
  retries this run (one routine pre-work token remint, no storm).
- Nightly run 2026-11-02 (guard receipt OK_LATE_GRACE, start 00:01:37Z,
  deadline 04:00Z): B's 2026-11-01 wake landed via the fixed deterministic
  publisher. A independently reviewed and integrated four B-authored PRs in
  one sequence on main: PR #14 (rebased 2026-10-31 audit republish, closes
  F-A12-1) via merge ebd91a25; PR #16 (2026-11-01 audit record, PARTIAL,
  consent-gate finding input to OPS-001B) via 71071c44; PR #18 (Muse
  stdout-EOF crash-diagnostics product fix, issue #9) via 80df5d38; PR #17
  (B launcher preflight/DNS durability + owner one-night quota exception,
  R2) via 83803685 (new main head, pushed). Each reviewed head verified
  ancestor of the merge; each changed path byte-identical on the merged
  tree; combined tree re-tested: ops/worker-b 35-test discovery 34 pass + 1
  httpx NOT RUN (unchanged inherited test), muse target 18/18, muse target
  10 repeat runs 10 ok / 0 fail, independent RED reproduction of the Muse
  fix on A's host (base muse/mod.rs → exit 101, stdout-closed error).
  Review records: ops/mailboxes/worker-a/reviews/REVIEW-PR14-PR16.md,
  REVIEW-PR18.md, REVIEW-PR17.md. New retained baseline notices: cargo fmt
  flags a pre-existing diff in crates/harness/src/codex/mod.rs; cargo
  clippy fails on two pre-existing non-octal permission literals in
  crates/harness/src/skills.rs:883,920 (both on base main). Open notice
  F-A17-1: the date-bound owner quota exception embedded in B's launcher
  must be replaced by an operator-owned override artifact or removed after
  the covered night; it is fenced to 2026-11-01 and cannot admit on later
  dates. Issue #9 closed on integration. PRs #14/#16/#17/#18 show merged on
  GitHub; branch-protection API still 403 for the App (NOT VERIFIED,
  operator item).
- Nightly run 2026-11-03: FAILED before any product work — the agent run
  aborted with a Hermes conversation-save error ("couldn't save this
  conversation to disk"); no candidate, no remote write, no lease opened.
  Tonight's disk check shows the Hermes home healthy (95G free, state.db
  writable), so the cause was not reproduced; recorded as an unresolved
  runtime defect, not as idle-by-choice.
- Nightly run 2026-11-04 (A guard admitted 00:0xZ window, deadline 04:00Z):
  OPS-001B implemented on branch task/ops-001b-release-check-consent, base
  eb1958ba, head a17e1148, opened as PR #19 (labels r2, ops-001) with issue
  #3 updated. Source fact corrected: ZERON_UPDATE_CHECKS does not exist on
  origin/main at eb1958ba, so the consent gate is new work, not a fix to an
  existing switch. Baseline behavior reproduced on a throwaway worktree of
  eb1958ba (probes kept uncommitted): default desktop spawn polled the
  release feed once within 4.11 s with no consent in the environment
  (left: 1 / right: 0), a wake inside the 2 s desktop delay reached the feed
  in 0.61 s, and crates/engine/src/lib.rs called updater.check_now() on every
  EdgeConfig::token_changes event. Candidate GREEN: zeron-update 21 lib + 1
  new integration test 0 failed; zeron-engine local_first 12/12 including the
  new wake test covering B's audit acceptance step 1; zeron background_engine
  1/1; RED/GREEN re-run with per-side isolated target dirs after a first
  attempt was contaminated by a shared CARGO_TARGET_DIR. Two honest
  corrections during the run: a test stub that answered before reading the
  request (harness defect, fixed) and a scheduler test that mutated shared
  process env while another scheduler test was live (the race the candidate
  removes by capturing consent at spawn plus consent_override in tests).
  New docs/reference/updates.md plus README claims corrected in en, es,
  zh-CN, ko, ja. Task record: ops/tasks/OPS-001B.md on the PR branch.
  Retained notices: clippy --all-targets -p zeron-update fails with 5
  unused_io_amount errors identical to base main; rustfmt --edition 2024
  reports 25 diffs on crates/engine/src/lib.rs on both base and candidate
  with no candidate-only diff; remote_terminals network-change lib test
  flaky 4/5 on candidate and 4/5 on base. NOT RUN: UI evidence (headless),
  full-workspace suites. Nothing integrated: A-authored R2 awaits B/Sol
  review of exactly a17e1148.
- Nightly run 2026-11-05 (A guard admitted OK_LATE_GRACE 00:01:28Z, deadline
  04:00Z, receipt run-2026-11-05, integration lease pr21.json): B's REMOTE-001
  transport PR #21 independently reviewed by A at exact head
  2d05a2bc7c388b91169dd61f6dff0a7d4b58d6e0 (base d5ac5ae3) and integrated as
  merge ef3e2435; merged tree byte-identical to the reviewed head; main now
  fff91f44. A-host evidence: rpc package 29 lib + 13 integration + 1 pass, 0
  fail, 2 ignored; independent RED of the RpcClient drop regression on a
  throwaway worktree of d5ac5ae3 (Elapsed failure without the Shared.clear
  fix); zeron-client --lib 35/35 at head; clippy --all-targets exit 0 with
  warnings only in baseline byte-unchanged files (matches B's inventory);
  rustfmt and git diff --check clean; no Cargo.lock change; merged-tree rpc
  suite re-run pass on main. Review record ops/mailboxes/worker-a/reviews/
  REVIEW-PR21.md; findings F-A21-1 (example token-file label misleading),
  F-A21-2 (UserKnownHostsFile quoting/list-split notice), F-A21-3 (revoked
  key does not kill established sessions; inherited semantics). PR #21 shows
  merged on GitHub; issue #20 updated with the integration contract status.
  NOT RUN on A's host: B's ignored real-OpenSSH sshd fixture test —
  openssh-server not installed here (one-package owner ask: openssh-server);
  B's real-sshd workflow remains B-host evidence until re-run. UI evidence
  NOT RUN (headless; no UI touched). No non-test caller of connect_ssh exists
  yet, so the merge changes no product behavior.
- Nightly run 2026-11-06 (A guard admitted OK_LATE_GRACE 00:01:30Z, deadline
  04:00Z, receipt run-2026-11-06; integration lock held for both merges): two
  B-authored PRs reviewed and integrated on A's host. PR #22 (quota-reserve
  recovery, ops/worker-b) reviewed at exact head
  75b9429c360fd57f13cb917af82338c6360ed0ec (base 2184e3e0), integrated as
  merge 0ae10c5b: 41 offline tests ran at head (40 pass + 1 inherited httpx
  test NOT RUN on this host), base-tree RED reproduction of the inherited
  frozen-clock preflight failure (35 ran / 1 failure + 1 error at 2184e3e0),
  single-removed-line diff audit confirming no cap/model/schedule edits,
  merged ops/worker-b byte-identical to the reviewed head. PR #23 (real zeron
  server commands for enrollment/sessions/revocation, R2, issue #20) reviewed
  at exact head c33e2e5723bdad50c4793bd510931568af5e00f6 (base 2184e3e0),
  integrated as merge d6f882fc: cargo test -p zeron --no-default-features
  25 pass / 0 fail / 1 ignored at head; the desktop-feature build B asked A
  to cover (zeron-ui compiled on A's host, servers + background_engine
  targets) exit 0; clippy exit 0 with only B's four retained baseline
  warnings; rustfmt/git-diff --check clean; empty Cargo.lock diff; A-side
  headless CLI grounding (seven subcommands, offline list, escape-name
  rejection, no ipc-token ever created); combined-tree re-run 25/0/1 plus
  41-ran/40-pass python discovery; apps/zeron byte-identical to the reviewed
  head. Review records: ops/mailboxes/worker-a/reviews/REVIEW-PR23.md plus
  PR comments (ids 6673101789, 6673163248, review 5794045958) and issue
  updates #4 (6673102182) and #20 (6673163248), all david-noether[bot].
  main now d6f882fc, pushed and read back. NOT RUN on A's host: B's ignored
  real-sshd workflow (openssh-server still absent — one-package owner ask
  re-confirmed); rendered UI evidence (headless; build config changed, not UI
  behavior). New notices F-A23-1 (list hard-fails on a corrupt record),
  F-A23-2 (disconnect acts via 250 ms generation poll; revoked keys never
  kill established sessions — inherited F-A21-3), F-A23-3 (canonical absolute
  token paths require re-enrollment after a move).
- Nightly run 2026-11-07 (A guard admitted 00:01Z window, deadline 04:00Z,
  receipt run-2026-11-07; integration lock held for both docs merges): the
  Sol blocking finding on PR #19 (scheduled harness-compatibility polling
  without consent) was implemented closed. task/ops-001b-release-check-consent
  advanced a17e1148 -> ef4f86f6 by fast-forward-safe merge 33a14bde of
  origin/main 79d35247; consent captured once at engine assembly
  (set_scheduled_consent), worker loop and binary-change wake gated, edge
  compatibility feed wired during assembly, explicit check_all/check_one
  unchanged; task record ops/tasks/OPS-001B-2-consent-boundary.md on the head.
  A-host evidence: baseline local_first 12/0 before edits on 79d35247; after
  the increment local_first 13/0 exit 0 (new live-engine consent test on a
  test-owned edge listener: consent-off assembled engine issues zero
  requests to the policy and manifest routes); zeron-engine --lib 642/0 incl.
  the new coordinator unit test (wake silent without consent, fetches with
  consent, grok fixture); zeron-update --lib 21/0; cargo fmt clean (branch-
  carried rustfmt drift resolved to the repo baseline; origin/main copies
  were already clean); clippy scoped: update --all-targets 5 unused_io_amount
  only in inherited lib-test target (same as main), engine --lib --tests exit
  0 with zero warnings in harness_updates.rs or engine/src/lib.rs (two
  local_first findings sit on lines present verbatim in main). NOT RUN: UI
  evidence (headless). PR #19 stays open and unmerged: A-authored R2 awaits
  B/Sol review of exactly ef4f86f6. Two B-authored R0 docs PRs reviewed and
  integrated under the lock: PR #25 (docs/audits/2026-11-06-worker-b.md,
  head 086595a2) via merge 77c2e18d and PR #27 (docs/audits/2026-11-07-
  worker-b.md, head 114f53e1) via 47f7b619; each merged path byte-identical
  to its reviewed head (empty diff), main-only delta was the two docs files.
  main now 47f7b619, pushed and read back. PR #19 evidence comment and issue
  #26 closure-candidate comment posted as david-noether[bot].
- Nightly run 2026-11-08 (A guard admitted OK 00:00:59Z, deadline 04:00Z,
  receipt run-2026-11-08, lease ops001b-narrow, integration lock held for the
  PR #28 merge): PR #19's bounded-review blocker was closed by re-cutting
  OPS-001B onto current main as PR #29 (single commit 8875924f, 13 files,
  consent content byte-identical to ef4f86f6); PR #19 closed with a
  preservation comment; drift retained locally only. A-host evidence on the
  new head (isolated target dirs): base main local_first 11 pass/0 fail +
  doc-test; candidate zeron-update 21+1+doc 0 fail; local_first 13/0
  (11 inherited + 2 consent tests); harness_updates::tests 43/0; engine --lib
  641/1 with the sole failure remote_terminals network-change, the inherited
  time-sensitive flake measured 2/3 pass candidate and 2/3 pass base in the
  same session; clippy -p zeron-engine --lib --tests exit 0 with zero findings
  in consent files (local_first 195/240 findings sit on lines verbatim in
  main); clippy -p zeron-update --all-targets exit 101 with the identical 5
  inherited unused_io_amount errors on candidate (1522/1554/1592/1617/1641)
  and base (1476/1508/1546/1571/1595), same compile summary; rustfmt clean on
  the five consent Rust files; git diff --check clean; Cargo.lock untouched.
  Log SHA256s posted in the PR #29 evidence comment. NOT RUN: UI evidence
  (headless), packaged desktop, real artifact downloads, real vendor endpoints.
  Second outcome: B's PR #28 (R2 controller repair) independently reviewed by
  A at exact head a3199d66 (base 3b99095e): 59 tests ran / 58 pass / 1
  inherited httpx error NOT RUN, base 41/40 + same inherited error, 18 new
  offline tests, diff audit clean (fixed-argv only, no cap/model/timer/route
  edits, APPROVE downgrade gate, report-branch/issue/PR creation removed);
  integrated under the lock as merge 45a19270 (target pre-verified equal to
  the reviewed base; ops/worker-b byte-identical to the reviewed head;
  merged-tree discovery re-run 59/58/1-inherited; pushed, read back ls-remote,
  GitHub merge API confirmed merged=true with exactly 45a19270). Review
  record ops/mailboxes/worker-a/reviews/REVIEW-PR28.md; notices F-A28-1
  (platform-approval semantics vs shared credential model), F-A28-2 (B-host
  live dispatch NOT VERIFIED on A's host), F-A28-3 (discovery-root test-count
  pinning). main now 45a19270.
  Nightly usage: Qwen self-hosted route only (one agent session + bounded
  deterministic build/test probes; totals UNKNOWN, never treated as
  unlimited); no Terra/Sol/GPT; no quota error retries; no new schedules.
  Nightly usage: Qwen self-hosted route only (one agent session + bounded
  build/test probes; totals UNKNOWN, never treated as unlimited); no
  Terra/Sol/GPT; no quota error retries; no new schedules.
- Next action (next scheduled run): worker B/Sol review of PR #29 head
  8875924faccee44842e4506a5f87b48b4dcae6f9 (13-path bounded OPS-001B consent
  slice on main 3b99095e; the 2026-11-08 controller in PR #28 now selects
  exactly this kind of pinned candidate); on approval A integrates under the
  integration lock and re-verifies the combined tree. If B's review requests
  changes, fix on task/ops-001b-consent-narrow without re-widening the diff.
  Optional follow-up (defer until OPS-001B lands): the rustfmt-drift cleanup
  preserved locally on drift/ops-001b-rustfmt-20261108 as its own bounded
  R1 formatting task. Second A candidate: the issue #20 acceptance slice the
  merged CLI does not cover — native enrollment/server-picker UI and
  server-side per-project workspace-grants design (do not duplicate CLI or
  transport). Owner decision open for OPS-001B: whether a managed Linux
  install should set ZERON_UPDATE_CHECKS=1 in edge/src/install.sh (default
  stays local; both switches documented). Still outstanding: B's independent
  reviews of A's PRs #6 (c78e2601), #7 (a0ef50a2), #8 (d0fcab13) — nothing
  A-authored integrates without them. A-host re-verification of B's real-sshd
  tests unlocks once the owner installs openssh-server. B should pin its
  ops/worker-b test discovery root per F-A28-3.
- Owner decisions open: transitive license-audit tooling (cargo-about or
  cargo-deny) approval or deferral; display path for UI evidence, or
  acceptance that BASE-002 visual acceptance stays NOT RUN on this host;
  set the zeron-worker-a cron timezone to Europe/Madrid (or re-pin the
  expression) so CEST-period and autumn-changeover nights are not silently
  skipped by the A guard (finding F-2, R2 scheduling change — owner-gated);
  OPERATIONS.md DST wording correction (F-1, R0) once B concurs.
