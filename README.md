# duochecker

Alerts you the moment an **iPhone Duo** is available for in-store pickup at an Apple Store
within **30 miles of 20004** (downtown DC), plus **Apple Carlsbad and Apple UTC (San Diego), CA** and **Apple Quaker Bridge (Princeton), NJ**. It polls the same availability endpoint apple.com
uses for "Check availability at a store", for all 8 US models (Star White / Night Sky,
256GB–2TB), in a single request per check.

It uses Apple's `/shop/retail/pickup-message` endpoint, searched by ZIP, the same one
[abkicks516/iphone-duo-monitor](https://github.com/abkicks516/iphone-duo-monitor) uses. Apple
answers it from GitHub's servers, which it doesn't for `/shop/fulfillment-messages` (HTTP 541).
If Apple does throttle it (HTTP 541/429), the script backs off (60s, doubling up to 15 min).

## Runs on GitHub Actions (nothing to keep running)

`.github/workflows/check.yml` checks automatically:

- **Private repo:** once every ~5 minutes (GitHub often runs it late). Uses about 1 of the
  2,000 free minutes per check, so the free minutes last about a week.
- **Public repo:** every 60 seconds nonstop, free. Each run lasts ~5h40m and the next is queued
  behind it. The ntfy topic in the workflow becomes visible to anyone.

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
| `--zip` | `20004 92009:Carlsbad,UTC "08648:Quaker Bridge"` | ZIPs to watch; `ZIP:Store,Store` watches only those stores |
| `--radius` | `30` | miles |
| `--minutes` | forever | stop after this long |
| `--interval` | `60` | seconds between checks |
| `--parts MK1F4LL/A ...` | all 8 | only watch some models (see `PARTS` in the script) |
| `--once` | | check once and exit |
