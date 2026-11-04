# Updates

Zeron never contacts the release feed on its own. Every path that reaches
`{edge}/releases/manifest.json` is a decision somebody made.

| Path | Who decides | Default |
| --- | --- | --- |
| App menu: "Check for Updates…" | You, once per click. | Always available. |
| `zeron update` (headless) | You, once per command. | Always available. |
| Scheduled background check (hourly wall clock, desktop and service) | `ZERON_UPDATE_CHECKS` | Off. |
| Service applies a found update and restarts in a quiet window | `ZERON_AUTO_UPDATE=1`, managed installs only | Off. |
| Desktop installs a found update on quit | `ZERON_AUTO_UPDATE=0` turns it off | On. |

`ZERON_UPDATE_CHECKS=1` (also `true` or `yes`) grants the scheduled check: the
running app or service then polls the public release feed on its own clock and
publishes "update available" when something newer exists. Unset, `0`, `false` or
`no` leaves the runtime silent — no manifest request, no download, nothing sent.
Consent is read once when the checker starts, so a value exported in the service
environment or the desktop session is the one that counts for that process.

An update that was already found is a separate decision. On the desktop it is
staged and installed on quit unless `ZERON_AUTO_UPDATE=0`. On a managed headless
install nothing is applied without `ZERON_AUTO_UPDATE=1`, and even then the
download is staged first and applied only while no run or terminal is active, so
sessions never die to an update.

`zeron update` and "Check for Updates…" work with the background check off: they
are your request, not the app's.
