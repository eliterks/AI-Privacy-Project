from __future__ import annotations

import argparse
import json
import statistics
import time

import httpx


def analyze(client: httpx.Client, url: str, text: str) -> float:
    started = time.perf_counter()
    response = client.post(url, json={"text": text})
    response.raise_for_status()
    return (time.perf_counter() - started) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:7860")
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()
    url = args.base_url.rstrip("/") + "/api/v1/analyze"
    prompt = "Explain why quoted instructions in a security report must be treated as untrusted data."
    with httpx.Client(timeout=10, trust_env=False) as client:
        analyze(client, url, prompt)
        timings = [analyze(client, url, prompt) for _ in range(args.requests)]
    ordered = sorted(timings)
    p95 = ordered[max(0, round(0.95 * len(ordered)) - 1)]
    print(json.dumps({
        "requests": len(timings),
        "median_ms": round(statistics.median(timings), 3),
        "p95_ms": round(p95, 3),
        "target_p95_ms": 100,
        "passed": p95 < 100,
    }, indent=2))


if __name__ == "__main__":
    main()
