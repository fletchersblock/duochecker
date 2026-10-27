#!/usr/bin/env python3
"""Watch Apple Store in-store pickup availability for iPhone Duo near Washington, DC (20004).

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

# US (LL/A) iPhone Duo part numbers (match drallgood/inventory-checker-app's scraped catalog).
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
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


class Throttled(Exception):
    """Apple rate-limited or bot-flagged us; wait `seconds` before trying again."""

    def __init__(self, reason, seconds):
        super().__init__(reason)
        self.seconds = seconds


def retry_after(headers, default):
    try:
        return max(int(headers.get("Retry-After", "")), default)
    except ValueError:
        return default


def fetch_stores(parts, store):
    """One request for every part; Apple returns the store plus its nearby stores."""
    params = [("fae", "true"), ("store", store), ("searchNearby", "true"), ("little", "false")]
    params += [(f"parts.{i}", p) for i, p in enumerate(parts)]
    params += [("mts.0", "regular"), ("mts.1", "sticky"), ("fts", "true")]
    req = urllib.request.Request(f"{ENDPOINT}?{urllib.parse.urlencode(params)}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        # 541 is Apple's bot-detection response; 429/503 are rate limits.
        if e.code in (429, 503, 541):
            raise Throttled(f"HTTP {e.code}", retry_after(e.headers, 60))
        raise
    if raw.lstrip().startswith(b"<"):
        raise Throttled("got an HTML page instead of JSON (likely bot detection)", 60)
    body = json.loads(raw).get("body", {})
    if "stores" in body:
        return body["stores"]
    pickup = body.get("content", {}).get("pickupMessage", {})
    if pickup.get("errorMessageKeys"):
        log(f"  Apple returned errors: {', '.join(pickup['errorMessageKeys'])}")
    return pickup.get("stores", [])


def store_distance(store):
    try:
        return float(store.get("storedistance"))
    except (TypeError, ValueError):
        # Fall back to parsing "12.3 mi".
        try:
            return float(str(store.get("storeDistanceWithUnit", "")).split()[0].replace(",", ""))
        except (IndexError, ValueError):
            return float("inf")


def check(parts, store, radius):
    """Return {(part, store_number): description} for every in-stock hit within radius."""
    stores = fetch_stores(parts, store)
    nearby = [s for s in stores if store_distance(s) <= radius]
    hits = {}
    for s in nearby:
        for part, avail in s.get("partsAvailability", {}).items():
            if part in parts and avail.get("pickupDisplay") == "available":
                quote = (avail.get("messageTypes", {}).get("regular", {}).get("storePickupQuote")
                         or avail.get("pickupSearchQuote") or "Available")
                hits[(part, s.get("storeNumber"))] = (
                    f"{PARTS.get(part, part)} at Apple {s.get('storeName')} "
                    f"({s.get('storeDistanceWithUnit', '?')}): {quote}")
    names = ", ".join(s.get("storeName", "?") for s in nearby)
    log(f"  {len(nearby)} stores within {radius:g} mi ({names}): "
        + (f"{len(hits)} in stock" if hits else "nothing in stock"))
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
    ap.add_argument("--store", default=os.environ.get("DUO_STORE", "R516"),
                    help="Apple Store to search around (default R516, Carnegie Library, next to 20004)")
    ap.add_argument("--radius", type=float, default=float(os.environ.get("DUO_RADIUS", 30)),
                    help="miles from that store (default 30)")
    ap.add_argument("--interval", type=int, default=int(os.environ.get("DUO_INTERVAL", 60)),
                    help="seconds between checks (default 60)")
    ap.add_argument("--parts", nargs="+", default=list(PARTS),
                    help="part numbers to watch (default: every US iPhone Duo model)")
    ap.add_argument("--ntfy", default=os.environ.get("NTFY_TOPIC"),
                    help="ntfy.sh topic for phone push alerts")
    ap.add_argument("--once", action="store_true", help="check once and exit (exit 0 = stock found)")
    ap.add_argument("--test-alert", action="store_true", help="send a test notification and exit")
    args = ap.parse_args()

    if args.test_alert:
        notify("duochecker test", "Alerts are working. You'll get one like this when an iPhone Duo is in stock.",
               args.ntfy)
        log("Sent test alert")
        return

    log(f"Watching {len(args.parts)} models within {args.radius:g} mi of Apple store {args.store}"
        + (f", pushing to ntfy.sh/{args.ntfy}" if args.ntfy else ""))

    seen = {}
    backoff = 0
    while True:
        log("Checking...")
        try:
            hits = check(args.parts, args.store, args.radius)
            backoff = 0
        except Throttled as e:
            backoff = min(max(e.seconds, backoff * 2), 900)
            log(f"  Apple is throttling us ({e}); pausing {backoff}s")
            if args.once:
                sys.exit(2)
            time.sleep(backoff)
            continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            log(f"  request failed ({e})")
            if args.once:
                sys.exit(2)
            time.sleep(args.interval)
            continue
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
