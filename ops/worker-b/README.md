# B's local nightly wake-up — owner-authorized setup

## Purpose and scope

The owner explicitly clarified that daytime setup is authorized so B can work
starting tonight, while product work is confined to 01:00–05:00 Europe/Madrid.
A's computer will eventually run the shared controller, but A's availability is
NOT a prerequisite for this smaller local B job. This is one worker, not a third
agent or competing shared controller. Disable this local timer before handing B
admission to A's future controller; both must not dispatch B independently.

Task B-AUDIT-001 is an R0 source-evidence report on inherited update/adapter
startup behavior, not R2 implementation or independent approval of B's setup.
See nightly-task.md. A still owns integration. No product behavior was changed
as part of this setup.

## Installed configuration

The reviewed source copies here correspond to:

- `~/.hermes/profiles/zeron/scripts/zeron-nightly.py`
- `~/.hermes/profiles/zeron/scripts/test_zeron_nightly.py`
- `~/.hermes/profiles/zeron/nightly-task.md`
- `~/.config/systemd/user/zeron-worker-b-nightly.service`
- `~/.config/systemd/user/zeron-worker-b-nightly.timer`

The timer is configured for `*-*-* 01:00:00 Europe/Madrid`, without catch-up or
random delay. The script rejects dispatch outside 01:00–01:15. Its effective
window closes at the earlier of local 05:00 and four elapsed hours after 01:00,
including DST. Each actual job is further restricted to **ten minutes**, four
outbound model attempts, and 4,000 fully reserved generated tokens (1,000 maximum
per request), conservatively using the smaller allowance-mode caps. Early exit
is expected; B is not meant to consume all four hours.

The systemd user service has `RuntimeMaxSec=600`, `KillMode=control-group`, no
restart, and kill escalation enabled. The supervisor additionally terminates its
owned process group on its monotonic deadline. User lingering is enabled so the
timer does not depend on an interactive login. Checkpoint instructions precede
termination; no budget reset or automatic retry is allowed after an interrupted
same-date admission.

State/receipts and raw output stay outside Git under
`~/.hermes/profiles/zeron/nightly/`. Same-date admission is persistent and locked.
A completed source-audit result with issue/PR handles skips unchanged main on
later nights without an inference call. A saved provider/auth/payment/quota block
requires operator reconciliation; missing telemetry cannot clear it.

## Request boundary and route

The installed Hermes CLI delegates model work to a separate gateway. A CLI-only
HTTP patch was found insufficient by a real setup probe (ledger stayed at zero).
The final launcher therefore uses the installed embedded `AIAgent` API directly,
with the approved runtime provider resolver, so SDK attempts pass through the
in-process HTTP guard. It pins `gpt-6.1-sol` / `openai-codex` and rejects an
unexpected transport or model. Outbound attempt reservations are persisted
before sends, including HTTP-client/SDK retries and intercepted helper calls.
The guard puts `max_output_tokens` on the actual wire body, removes premium speed,
and refuses alternate inference origins/models. Optional titles/background
review, MCP and fallback routes are not admitted. No billable API-key fallback or
model switch was enabled in the chat profile.

The input-token metric/ceiling is **UNKNOWN**, not an exact enforced token limit;
this setup relies on the independent request, output-reservation and wall-clock
bounds when provider metrics are unavailable, as described in MODEL_BUDGET.md.
Fresh supported account usage is checked before admission and each intercepted
attempt, with the specified reserve and same-window consumption checks. These
readings are account-wide, not attributed solely to Zeron. This is a trusted-worker
process guard and task scope, not an adversarial OS sandbox or the complete
cross-machine OPS-001 solution. Independent review is pending; do not claim full
OPS-001 acceptance or approval of B-authored runtime code.

## Actual verification during setup

- Nine deterministic tests PASS: daytime/late-start refusal, DST deadlines,
  durable request/output caps, model pin, deadline refusal, low-quota UNKNOWN
  behavior, weekly consumption threshold, real termination of an owned sleeping
  subprocess, and mocked HTTP-wire output cap/retry/fallback refusal.
- `systemd-analyze --user verify` passes for the installed units.
- Starting the service in daytime produces a successful out-of-hours skip,
  rather than a product-work/model dispatch.
- A final embedded live setup-only request returned `READY`, exit 0, with exactly
  ONE recorded attempt and 1,000 reserved output tokens. The successful request
  traversed the HTTP guard with the actual output cap. This is connectivity and
  guard plumbing evidence, not proof that the assigned audit is completed.
- The earlier unguarded CLI-plumbing probe also returned READY; it was rejected
  as guard evidence and is not used by the scheduled launcher.
- No product audit or implementation ran during daytime. No unattended nightly
  execution is claimed until the next scheduled run produces its receipt.

Re-run tests with the installed Hermes bootstrapped interpreter, as used during
setup, or equivalent dependencies. Use `zeron-nightly.py --plan` to inspect
current admission without dispatching inference. Do not run a live task as a test
outside the permitted window.

## First-run inspection / rollback

After the wake-up inspect the local dated JSON receipt and log, systemd service
result, and the bot-authored audit issue/PR. A failed or partial run stays partial.
To stop this local automation: `systemctl --user disable --now
zeron-worker-b-nightly.timer`; stop ONLY its own service if needed. Preserve
receipts and uncommitted work. Never erase counters to retry the same night.
