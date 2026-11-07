# Updates

Zeron never contacts the release feed on its own. Every path that reaches
`{edge}/releases/manifest.json` or `{edge}/releases/harness-compatibility.json`
is a decision somebody made.

| Path | Who decides | Default |
| --- | --- | --- |
| App menu: "Check for Updates…" | You, once per click. | Always available. |
| `zeron update` (headless) | You, once per command. | Always available. |
| Scheduled background check (hourly wall clock, desktop and service) | `ZERON_UPDATE_CHECKS` | Off. |
| Harness CLI update polls (engine worker: startup pass, periodic re-check, wake on an outside binary change or a Settings view opening) | `ZERON_UPDATE_CHECKS` | Off. |
| Service applies a found update and restarts in a quiet window | `ZERON_AUTO_UPDATE=1`, managed installs only | Off. |
| Desktop installs a found update on quit | `ZERON_AUTO_UPDATE=0` turns it off | On. |

`ZERON_UPDATE_CHECKS=1` (also `true` or `yes`) grants the scheduled check: the
running app or service then polls the public release feed on its own clock and
publishes "update available" when something newer exists. The same consent
gates the harness CLI worker: it fetches the published compatibility policy
and each registry's latest version only on scheduled passes and wakes while
consent is granted. Unset, `0`, `false` or
`no` leaves the runtime silent — no manifest request, no harness policy or
latest-version lookup, no download, nothing sent; harness rows keep showing
what is already known locally. Explicit actions — "Check for Updates…",
`zeron update`, and the harness update/apply commands from Settings or the
CLI — are your request, not the app's, and work with the background check
off. Consent is read once when the checker starts, so a value exported in the service
environment or the desktop session is the one that counts for that process.

An update that was already found is a separate decision. On the desktop it is
staged and installed on quit unless `ZERON_AUTO_UPDATE=0`. On a managed headless
install nothing is applied without `ZERON_AUTO_UPDATE=1`, and even then the
download is staged first and applied only while no run or terminal is active, so
sessions never die to an update.

`zeron update` and "Check for Updates…" work with the background check off: they
are your request, not the app's.
