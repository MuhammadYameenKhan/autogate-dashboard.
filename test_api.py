#!/usr/bin/env python3
"""
Seed parking events without live camera feed.

Usage examples:
  python test_api.py --count 20
  python test_api.py --count 30 --exit-ratio 0.4
  python test_api.py --base-url http://localhost:5000 --count 10 --delay-ms 100
"""

from __future__ import annotations

import argparse
import json
import random
import string
import time
import urllib.error
import urllib.request


def random_plate() -> str:
    prefix = "".join(random.choices(string.ascii_uppercase, k=3))
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{prefix}{suffix}"


def post_event(endpoint: str, payload: dict) -> tuple[bool, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            body = res.read().decode("utf-8", errors="replace")
            return True, body
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        return False, f"HTTP {err.code}: {body}"
    except Exception as err:  # noqa: BLE001
        return False, str(err)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create fake parking events for testing.")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Backend URL (default: http://localhost:5000)")
    parser.add_argument("--count", type=int, default=20, help="Total events to create")
    parser.add_argument("--exit-ratio", type=float, default=0.3, help="Fraction of events that should be exits (0.0-1.0)")
    parser.add_argument("--delay-ms", type=int, default=0, help="Delay between requests in milliseconds")
    parser.add_argument("--gate", default="gate1", help="Gate name/id")
    args = parser.parse_args()

    if args.count <= 0:
        raise SystemExit("--count must be > 0")
    if not (0 <= args.exit_ratio <= 1):
        raise SystemExit("--exit-ratio must be between 0 and 1")

    endpoint = f"{args.base_url.rstrip('/')}/api/parking/event"
    pool_size = max(5, args.count // 2)
    plate_pool = [random_plate() for _ in range(pool_size)]

    success = 0
    failed = 0

    print(f"Posting {args.count} events to {endpoint}")
    for i in range(1, args.count + 1):
        is_exit = random.random() < args.exit_ratio
        payload = {
            "plate_number": random.choice(plate_pool),
            "event_type": "exit" if is_exit else "entry",
            "gate": args.gate,
            "confidence": round(random.uniform(0.85, 0.99), 2),
        }
        ok, message = post_event(endpoint, payload)
        if ok:
            success += 1
            print(f"[{i}/{args.count}] OK  {payload['event_type']} {payload['plate_number']}")
        else:
            failed += 1
            print(f"[{i}/{args.count}] ERR {payload['event_type']} {payload['plate_number']} -> {message}")

        if args.delay_ms > 0:
            time.sleep(args.delay_ms / 1000)

    print("\nDone.")
    print(f"Success: {success}")
    print(f"Failed : {failed}")


if __name__ == "__main__":
    main()
