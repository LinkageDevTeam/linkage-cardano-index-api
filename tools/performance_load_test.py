"""
Performance load test for the Cardano Index API.
Measures: requests per second and success rate under concurrent load.

Usage:
  Ensure the API is running (e.g. uvicorn main:app), then:
  python -m tools.performance_load_test [--base-url URL] [--concurrent N] [--duration SEC] [--api-key KEY]

Example:
  python -m tools.performance_load_test --concurrent 10 --duration 30
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx


async def run_single_request(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    endpoint: str,
) -> Tuple[bool, float, int]:
    """Run one request; return (success, latency_seconds, status_code)."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {"Authorization": f"Bearer {api_key}"}
    start = time.perf_counter()
    try:
        r = await client.get(url, headers=headers, timeout=30.0)
        elapsed = time.perf_counter() - start
        return r.status_code == 200, elapsed, r.status_code
    except Exception:
        elapsed = time.perf_counter() - start
        return False, elapsed, 0


async def worker(
    worker_id: int,
    base_url: str,
    api_key: str,
    endpoints: List[str],
    duration_seconds: float,
    results: list,
) -> None:
    """One worker: repeatedly hit endpoints in round-robin until duration_seconds elapsed."""
    end_time = time.perf_counter() + duration_seconds
    idx = 0
    async with httpx.AsyncClient() as client:
        while time.perf_counter() < end_time:
            endpoint = endpoints[idx % len(endpoints)]
            ok, lat, status_code = await run_single_request(client, base_url, api_key, endpoint)
            results.append((ok, lat, status_code))
            idx += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test Cardano Index API")
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
        "--concurrent",
        type=int,
        default=10,
        help="Number of concurrent clients (default: 10)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--index-id",
        default="cardano-defi",
        help="Index ID to use for /price and /volume (default: cardano-defi)",
    )
    args = parser.parse_args()

    endpoints = [
        "/indexes",
        f"/indexes/{args.index_id}/price",
    ]
    results: List[Tuple[bool, float, int]] = []
    duration_seconds = float(args.duration)

    print(f"Load test: {args.concurrent} concurrent clients, {args.duration}s duration")
    print(f"Endpoints: {endpoints}")
    print(f"Base URL: {args.base_url}")
    print("Running...")

    start = time.perf_counter()
    async def run_all() -> None:
        tasks = [
            asyncio.create_task(
                worker(i, args.base_url, args.api_key, endpoints, duration_seconds, results)
            )
            for i in range(args.concurrent)
        ]
        await asyncio.gather(*tasks)

    asyncio.run(run_all())
    elapsed = time.perf_counter() - start

    total = len(results)
    ok = sum(1 for success, _, _ in results if success)
    failed = total - ok
    rps = total / elapsed if elapsed > 0 else 0
    latencies = [lat for _, lat, _ in results]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    # Collect status code breakdown
    from collections import Counter
    status_counts: Counter = Counter(sc for _, _, sc in results)

    print("\n--- Results ---")
    print(f"Total requests:  {total}")
    print(f"Successful:      {ok}")
    print(f"Failed:          {failed}")
    print(f"Success rate:    {100 * ok / total:.1f}%" if total else "N/A")
    print(f"Wall clock:      {elapsed:.2f}s")
    print(f"Requests/sec:    {rps:.2f}")
    print(f"Avg latency:     {avg_latency*1000:.0f} ms")

    if failed > 0 or len(status_counts) > 1:
        print("\n--- Status code breakdown ---")
        for code, count in sorted(status_counts.items()):
            label = "connection error" if code == 0 else f"HTTP {code}"
            print(f"  {label}: {count}")


if __name__ == "__main__":
    main()
