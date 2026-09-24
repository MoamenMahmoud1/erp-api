#!/usr/bin/env python3
"""Simple concurrent benchmark for the authenticated product-list endpoint."""

import argparse
import concurrent.futures
import os
import statistics
import time
import urllib.error
import urllib.request


URL = os.getenv(
    "BENCHMARK_URL",
    "http://127.0.0.1:8080/api/v1/products/?page_size=50",
)

TOKENS = tuple(
    token.strip()
    for token in os.getenv("JWT_TOKENS", "").split(",")
    if token.strip()
)

SINGLE_TOKEN = os.getenv("JWT_TOKEN", "").strip()
if SINGLE_TOKEN and not TOKENS:
    TOKENS = (SINGLE_TOKEN,)


def request_once(token: str) -> tuple[float, int]:
    request = urllib.request.Request(
        URL,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Forwarded-Proto": "https",
        },
        method="GET",
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
            return time.perf_counter() - started, response.status
    except urllib.error.HTTPError as exc:
        exc.read()
        return time.perf_counter() - started, exc.code
    except Exception:
        return time.perf_counter() - started, 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()

    if not TOKENS:
        raise SystemExit("Set JWT_TOKEN or JWT_TOKENS before running the benchmark.")

    if args.requests < 1 or args.concurrency < 1:
        raise SystemExit("--requests and --concurrency must be >= 1")

    started = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as executor:
        futures = [
            executor.submit(request_once, TOKENS[i % len(TOKENS)])
            for i in range(args.requests)
        ]
        results = [future.result() for future in futures]

    elapsed = time.perf_counter() - started

    latencies = [latency for latency, _ in results]
    statuses = [status for _, status in results]
    successes = sum(status == 200 for status in statuses)
    failures = len(statuses) - successes

    def percentile(values, p):
        if not values:
            return 0.0
        values = sorted(values)
        index = (len(values) - 1) * p
        lower = int(index)
        upper = min(lower + 1, len(values) - 1)
        return values[lower] + (values[upper] - values[lower]) * (index - lower)

    print(f"URL:          {URL}")
    print(f"Requests:     {args.requests}")
    print(f"Concurrency:  {args.concurrency}")
    print(f"Elapsed:      {elapsed:.3f}s")
    print(f"Throughput:   {args.requests / elapsed:.2f} req/s")
    print(f"Success:      {successes}")
    print(f"Failures:     {failures}")
    print(f"p50:          {percentile(latencies, 0.50) * 1000:.1f} ms")
    print(f"p95:          {percentile(latencies, 0.95) * 1000:.1f} ms")
    print(f"p99:          {percentile(latencies, 0.99) * 1000:.1f} ms")
    print(f"max:          {max(latencies, default=0) * 1000:.1f} ms")

    status_counts = {}
    for status in statuses:
        status_counts[status] = status_counts.get(status, 0) + 1

    print("Status codes:", status_counts)


if __name__ == "__main__":
    main()
