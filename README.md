# duochecker

Alerts you the moment an **iPhone Duo** is available for in-store pickup at an Apple Store
within **30 miles of 20004** (downtown DC). It polls the same availability endpoint apple.com
uses for "Check availability at a store", for all 8 US models (Star White / Night Sky,
256GB–2TB).

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
| `--zip` | `20004` | |
| `--radius` | `30` | miles |
| `--interval` | `60` | seconds between checks |
| `--parts MK1F4LL/A ...` | all 8 | only watch some models (see `PARTS` in the script) |
| `--once` | | check once and exit |

## Or: GitHub Actions (no computer needed)

`.github/workflows/check.yml` runs a check every ~5 minutes. Add a repo secret
**NTFY_TOPIC** (Settings → Secrets and variables → Actions) with your topic name. It's slower
than running locally, it re-alerts on every run while something is in stock, and Apple
sometimes blocks cloud IPs. Disable the workflow once you have your phone.
