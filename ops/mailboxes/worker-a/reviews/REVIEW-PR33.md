# Review record: PR #33 (worker B LOCAL-002B implementation) — reviewed and integrated by worker A

- Reviewed base: 3049108af6f033fb7e7b86f9fbf30d15448dc522 (main, verified as pre-merge target via ls-remote before the advance; merge-base with the head is b880fbef)
- Reviewed head: 24bb816e3543ee9e98d05edbdbe6d8015c130645 (task/local-002b-offline-default)
- Stack audit: the branch's merge commit 49f645ea (PR #32 e3a7925d + PR #29 8875924f on b880fbef) carries main code byte-identically: git diff 3049108a 49f645ea over crates and apps is empty, so the PR #32 and #29 copies in the branch equal the already-integrated main copies. B's own change is d553cb33 (engine + docs) + 24bb816e (probe, smoke, driver): 9 files, 747 insertions / 4 deletions against main, Cargo.lock untouched.
- Risk: R2 (changes when the engine starts third-party agent CLIs). B-authored, so worker A is the independent reviewer per AGENTS.md; the worker-B lane did not author or review this candidate.

Executed on A's host at the exact head (detached review worktree, pinned rustc 1.99.1 / cargo 1.99.1, shared CARGO_TARGET_DIR, --locked):
- cargo test --locked -p zeron-engine --lib model_catalogs: 13 passed / 0 failed (matches B's 13 exactly, 4 new tests included).
- cargo test --locked -p zeron-engine --lib: 646 passed / 0 failed / 5 ignored in 133 s (matches B's counts exactly; remote_terminals passed this night).
- cargo build --locked -p zeron --no-default-features --bin zeron-engine: exit 0.
- cargo build --locked -p zeron-rpc --example local_smoke: exit 0.
- scripts/local-offline-smoke.sh --no-build: exit 4 SKIP with printed reason (this host forbids unprivileged user namespaces; strace and iproute2 absent). Negative control observed: the tooling reports SKIP, never a false PASS.
- clippy --locked -p zeron-engine --lib --tests: exit 0 with warnings only; the engine tree carries pre-existing lint debt (33 warning sites across engine files under clippy 1.99). Two warnings are new (F-A33-2).
- rustfmt --edition 2024 --check per-file on the four changed Rust files: clean (crate-level drift recorded in ops/STATE.md untouched).
- git diff --check 49f645ea 24bb816e: clean.
- Three-way merge preview into main 3049108a: clean (git merge-tree --write-tree exit 0, no conflict entries; GitHub mergeable=false was stale).

Code review of the engine change:
- The gate sits in model_catalogs::resolve, the single dispatch path of every LIST_MODELS request (local handle, cloud runner handle, scoped relay forward). Background_agent_discovery defaults false on EngineRpc and is wired from the same ZERON_AGENT_DISCOVERY env read at engine assembly used for ZERON_UPDATE_CHECKS in #29.
- Withheld listings serve the saved catalog for the same credential and binary context, else the harness's built-in rows, else the existing model catalog unavailable retry error. Built-in rows are never saved as a live answer; the lease, refresh task and CLI probe are untouched on the withheld path (tests assert zero probe calls and no catalog file created).
- Force and consent semantics preserve the pre-change behavior exactly; rollback is revert d553cb33 or ZERON_AGENT_DISCOVERY=1 without a revert. UI forcing verified in crates/ui/src/pickers.rs at head (picker open and refresh pass force true; settings and catalog loads do not), so the engine gate is the new default boundary and the UI boundary is unchanged.
- egress-probe tooling: probe.sh requires root or unprivileged user namespaces, exits 4 when unavailable, 0 when no attempt was recorded, 3 on an attempt; sink.py is loopback-only DNS/TCP capture; smoke driver local_smoke.rs uses only the pre-existing mock harness. No sudo, no cloud dependency, no secret.

Findings:
- F-A33-1 (retained notice): apps/zeron/src/daemon.rs CAPTURED_ENV does not forward ZERON_AGENT_DISCOVERY (nor ZERON_UPDATE_CHECKS from #29), so a consent value exported in the shell is not captured into the installed service unit; the new doc line says exported to the service environment, true for a foreground engine but not for the installed service. Suggested follow-up: one bounded card forwarding both consent variables via CAPTURED_ENV (or narrowing the doc wording).
- F-A33-2 (retained notice): two new clippy warnings in the new test code, cloned_ref_to_slice_refs at crates/engine/src/rpc.rs:5830 and :5844; cosmetic, std::slice::from_ref suggested. Not a regression of a green check (engine clippy already carries the fork lint debt).
- F-A33-3 (owner decision, from B's open finding 2): ListCommands also starts the agent CLI with no consent gate and no force flag; its trigger surface is unmeasured. Kept open with B's finding 1 (onboarding vendor screen, baked DEFAULT_EDGE_URL / WorkOS client id).

NOT RUN on A's host: egress smoke execution and the RED variant (no unprivileged user namespaces, no strace, no iproute2; the SKIP exit 4 was observed instead); UI/Xvfb evidence (headless host); clippy of the UI crates; B's screenshots exist only in B's workspace.

Verdict: APPROVED for the exact head 24bb816e on base 3049108a (GitHub review 5913711042, APPROVED, submitted 2026-11-16T00:18:36Z, head-pinned). Approval covers only this diff.

Integration (worker A, under the integration lock, run-2026-11-16, lease integrate-2026-11-16):
- Target verified equal to 3049108a via ls-remote before the advance; local merge --no-ff 2c0141805e25ffaaa753d7ee2adde62e20fd9a7b (parents 3049108a + 24bb816e); merged tree bcd84044668c12bad3dc5b838f32dfaea0818c1a equals the merge-tree preview exactly.
- Byte-identity re-verified after the merge: git diff 24bb816e 2c014180 over the nine reviewed paths is empty, so the unit-tested head is literally the integrated tree (A's host cannot re-run the egress smoke on the merged checkout for the same namespace reason; the engine/script code is byte-identical to the tested head).
- Pushed to main and read back (ls-remote 2c014180); GitHub confirms merged=true with merge_commit_sha exactly 2c014180; PR #33 closed/merged.
