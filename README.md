# duochecker

Alerts you the moment an **iPhone Duo** is available for in-store pickup at an Apple Store
within **30 miles of 20004** (downtown DC). It polls the same availability endpoint apple.com
uses for "Check availability at a store", for all 8 US models (Star White / Night Sky,
256GB–2TB), in a single request per check.

Request format, part numbers and throttling behavior follow
[drallgood/inventory-checker-app](https://github.com/drallgood/inventory-checker-app), a macOS
app that does the same thing. Searches are anchored on Apple Carnegie Library (`R516`), which is
next to 20004, and distances are measured from it. If Apple flags the traffic (HTTP 541/429), the
script backs off (60s, doubling up to 15 min) instead of hammering it.

## Get alerts on your phone (ntfy)

1. Install the free **ntfy** app (iOS / Android).
2. Subscribe to a hard-to-guess topic, e.g. `duo-dc-8f3k2q`. Anyone who knows the name can
   read it, so don't use something obvious.

## Run it (best: on your own computer)

```sh
python3 duochecker.py --ntfy duo-dc-8f3k2q
```

Checks every 60 seconds and alerts (phone push + desktop notification + terminal bell) as
soon as a store gets stock, and again if a store sells out and restocks. Needs only Python 3,
nothing to install. Leave it running and keep your computer awake.

Options:

| Flag | Default | |
|---|---|---|
| `--store` | `R516` | Apple Store to search around (Carnegie Library, DC) |
| `--radius` | `30` | miles from that store |
| `--interval` | `60` | seconds between checks |
| `--parts MK1F4LL/A ...` | all 8 | only watch some models (see `PARTS` in the script) |
| `--once` | | check once and exit |

## GitHub Actions: doesn't work

Apple returns HTTP 541 (its bot block) to GitHub's servers, so the workflow's schedule is off.
A manual run still sends a test alert to the ntfy topic in `.github/workflows/check.yml`.
