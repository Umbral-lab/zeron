# LOCAL-002C — daemon consent-variable capture (finding F-A33-1)

- Objective: make `zeron daemon install` carry the two consent variables that
  integrated work (OPS-001B `ZERON_UPDATE_CHECKS`, LOCAL-002B
  `ZERON_AGENT_DISCOVERY`) documented as user-facing switches into the
  systemd/launchd unit it writes, so a service run honours the same consent
  contract as a shell run.
- Source finding: F-A33-1, recorded by worker A in review 5913711042 of PR #33
  (retained follow-up, 2026-11-16). `apps/zeron/src/daemon.rs` `CAPTURED_ENV`
  whitelists env keys baked into the unit at install time; the whitelist never
  gained the two consent keys although docs/reference/updates.md documents
  both variables for "desktop and service" runs. A unit file rendered before
  this card therefore runs the service with both consents silently off,
  whatever the installing shell had set.
- Acceptance criteria:
  1. `CAPTURED_ENV` includes `ZERON_UPDATE_CHECKS` and `ZERON_AGENT_DISCOVERY`
     (captured only when set, same as every other key).
  2. A unit test locks both keys in the whitelist and asserts the rendered
     systemd unit carries their Environment lines, so a future whitelist edit
     that drops a consent key fails deterministically.
  3. No product-behavior change for installs that do not set the variables
     (both remain default-off; forwarding an opt-in variable cannot weaken the
     consent boundary).
- Non-goals: install.sh behavior (`ZERON_UPDATE_CHECKS=1` in the curl|sh unit
  stays an open owner decision); `EnvironmentFile=-%h/.zeron/env` semantics;
  any engine or update-crate change; the REMOTE-002 enrollment-path grant
  push follow-up.
- Risk: R1 — bounded local unit-file rendering logic; failure mode is a
  missing/extra Environment line in a user-written unit. Not R2: it forwards
  user-set opt-in values, adds no network or execution behavior.
- Dependencies: main f39b4d934ab53bcc924d741f0a72252805c1c0ee (contains both
  consent implementations and their docs).
- Owner: worker A (implementation and integration); worker B review of the
  exact head required before integration (A-authored).
- Expected files: `apps/zeron/src/daemon.rs` (whitelist + test),
  `docs/reference/updates.md` (one service-capture sentence), this card.
- Branch/worktree: `task/local-002c-captured-env` at
  `/opt/data/home/zeron-wt/local-002c`, base f39b4d93.
- Verification: `cargo test --locked -p zeron --no-default-features` lib
  target base 13/0 vs head (14 expected); servers integration target unchanged;
  clippy scoped to -p zeron; per-file rustfmt; `git diff --check`; Cargo.lock
  untouched. UI evidence NOT RUN (headless host; no UI touched).
- Rollback: revert the single commit on the branch; no data or state migration
  involved.
