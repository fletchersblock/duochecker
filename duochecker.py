#!/usr/bin/env python3
"""Watch Apple Store in-store pickup availability for iPhone Duo near a ZIP code.

Polls Apple's pickup endpoint (the same one apple.com uses for "Check availability")
and sends an alert the moment any configured model shows up at a store in range.

Standard library only. Run `python3 duochecker.py --help` for options.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# US (LL/A) iPhone Duo part numbers.
PARTS = {
    "MK1E4LL/A": "Star White 256GB",
    "MK1G4LL/A": "Star White 512GB",
    "MK1J4LL/A": "Star White 1TB",
    "MK1Q4LL/A": "Star White 2TB",
    "MK1F4LL/A": "Night Sky 256GB",
    "MK1H4LL/A": "Night Sky 512GB",
    "MK1L4LL/A": "Night Sky 1TB",
    "MK1R4LL/A": "Night Sky 2TB",
}

ENDPOINT = "https://www.apple.com/shop/fulfillment-messages"
PRODUCT_URL = "https://www.apple.com/shop/buy-iphone/iphone-duo"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept": "application/json",
    "Referer": PRODUCT_URL,
}


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def fetch_stores(part, zip_code):
    query = urllib.parse.urlencode({
        "fae": "true",
        "pl": "true",
        "mts.0": "regular",
        "mts.1": "compact",
        "parts.0": part,
        "location": zip_code,
        "searchNearby": "true",
    })
    req = urllib.request.Request(f"{ENDPOINT}?{query}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    return data.get("body", {}).get("content", {}).get("pickupMessage", {}).get("stores", [])


def store_distance(store):
    try:
        return float(store.get("storedistance"))
    except (TypeError, ValueError):
        # Fall back to parsing "12.3 mi".
        try:
            return float(str(store.get("storeDistanceWithUnit", "")).split()[0].replace(",", ""))
        except (IndexError, ValueError):
            return float("inf")


def check(parts, zip_code, radius):
    """Return {(part, store_number): description} for every in-stock hit within radius."""
    hits = {}
    for part in parts:
        try:
            stores = fetch_stores(part, zip_code)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            log(f"  {PARTS.get(part, part)}: request failed ({e})")
            continue
        nearby = [s for s in stores if store_distance(s) <= radius]
        found = []
        for s in nearby:
            avail = s.get("partsAvailability", {}).get(part, {})
            if avail.get("pickupDisplay") == "available":
                quote = avail.get("pickupSearchQuote", "Available")
                desc = (f"{PARTS.get(part, part)} at Apple {s.get('storeName')} "
                        f"({s.get('storeDistanceWithUnit', '?')}): {quote}")
                hits[(part, s.get("storeNumber"))] = desc
                found.append(s.get("storeName"))
        status = f"IN STOCK at {', '.join(found)}" if found else "none"
        log(f"  {PARTS.get(part, part)}: {status} ({len(nearby)} stores within {radius:g} mi)")
        time.sleep(1)
    return hits


def notify(title, body, ntfy_topic):
    print("\a", end="", flush=True)
    if ntfy_topic:
        try:
            req = urllib.request.Request(
                f"https://ntfy.sh/{ntfy_topic}",
                data=body.encode(),
                headers={"Title": title, "Priority": "urgent", "Tags": "iphone,rotating_light",
                         "Click": PRODUCT_URL},
            )
            urllib.request.urlopen(req, timeout=15).close()
        except urllib.error.URLError as e:
            log(f"ntfy push failed: {e}")
    system = platform.system()
    try:
        if system == "Darwin":
            script = f"display notification {json.dumps(body)} with title {json.dumps(title)} sound name \"Glass\""
            subprocess.run(["osascript", "-e", script], check=False)
        elif system == "Linux":
            subprocess.run(["notify-send", "-u", "critical", title, body], check=False)
    except FileNotFoundError:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", default=os.environ.get("DUO_ZIP", "20004"))
    ap.add_argument("--radius", type=float, default=float(os.environ.get("DUO_RADIUS", 30)),
                    help="miles (default 30)")
    ap.add_argument("--interval", type=int, default=int(os.environ.get("DUO_INTERVAL", 60)),
                    help="seconds between checks (default 60)")
    ap.add_argument("--parts", nargs="+", default=list(PARTS),
                    help="part numbers to watch (default: every US iPhone Duo model)")
    ap.add_argument("--ntfy", default=os.environ.get("NTFY_TOPIC"),
                    help="ntfy.sh topic for phone push alerts")
    ap.add_argument("--once", action="store_true", help="check once and exit (exit 0 = stock found)")
    args = ap.parse_args()

    log(f"Watching {len(args.parts)} models within {args.radius:g} mi of {args.zip}"
        + (f", pushing to ntfy.sh/{args.ntfy}" if args.ntfy else ""))

    seen = {}
    while True:
        log("Checking...")
        hits = check(args.parts, args.zip, args.radius)
        new = {k: v for k, v in hits.items() if k not in seen}
        if new:
            body = "\n".join(new.values())
            log("*** IN STOCK ***\n" + body)
            notify("iPhone Duo in stock!", body, args.ntfy)
        seen = hits  # forget stores that sold out, so a restock alerts again
        if args.once:
            sys.exit(0 if hits else 1)
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
