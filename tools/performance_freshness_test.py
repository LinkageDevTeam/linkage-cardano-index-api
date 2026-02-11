"""
Freshness test for the Cardano Index API.
Measures how up-to-date price data is (cache age, propagation from DEX).

Usage:
  Ensure the API is running, then:
  python -m tools.performance_freshness_test [--base-url URL] [--api-key KEY] [--samples N]

Example:
  python -m tools.performance_freshness_test --samples 5
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Test data freshness of Cardano Index API")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--api-key",
        default="demo-api-key-please-change",
        help="API key for Authorization header",
    )
    parser.add_argument(
        "--index-id",
        default="cardano-defi",
        help="Index ID (default: cardano-defi)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of price requests to sample (default: 5)",
    )
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/indexes/{args.index_id}/price"
    headers = {"Authorization": f"Bearer {args.api_key}"}

    print(f"Freshness test: GET {url}")
    print(f"Samples: {args.samples}\n")

    cache_ages: List[Optional[int]] = []
    timestamps: List[str] = []

    with httpx.Client(timeout=30.0) as client:
        for i in range(args.samples):
            try:
                r = client.get(url, headers=headers)
                if r.status_code != 200:
                    print(f"  Sample {i+1}: HTTP {r.status_code}")
                    continue
                data = r.json()
                ts = data.get("timestamp")
                age = data.get("cache_age_seconds")
                timestamps.append(ts)
                cache_ages.append(age)
                print(f"  Sample {i+1}: timestamp={ts}, cache_age_seconds={age}")
            except Exception as e:
                print(f"  Sample {i+1}: error {e}")
            if i < args.samples - 1:
                time.sleep(1)  # 1 second between samples to see cache age grow

    # Summary
    ages = [a for a in cache_ages if a is not None]
    if ages:
        print("\n--- Freshness summary ---")
        print(f"Cache age (seconds): min={min(ages)}, max={max(ages)}, avg={sum(ages)/len(ages):.1f}")
        print("Interpretation: Price data is at most (cache_ttl_seconds) old; cache_age_seconds shows how long ago the data was fetched.")
    else:
        print("\nNo cache_age_seconds in responses (data may be uncached or schema not updated).")


if __name__ == "__main__":
    main()
