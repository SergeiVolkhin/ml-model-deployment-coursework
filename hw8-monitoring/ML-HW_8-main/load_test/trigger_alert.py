"""Trigger an SLO-breaching load against ml_service and (optionally) probe Grafana for the firing alert.

Usage:
    python load_test/trigger_alert.py --mode degraded --requests 500 --workers 20 --probe-grafana-api

Requires the docker-compose stack to be running locally with ML service on :8000 and Grafana on :3000.
LATENCY_MODE on the service-side controls injected latency; set it via .env then `docker compose up -d ml_service`.
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from typing import Any

import httpx

DEFAULT_TARGET = "http://localhost:8000/predict"
DEFAULT_GRAFANA = "http://localhost:3000"
GRAFANA_ALERTS_PATH = "/api/alertmanager/grafana/api/v2/alerts"


async def _send_one(client: httpx.AsyncClient, target: str, user_id: int) -> float | None:
    start = time.perf_counter()
    try:
        r = await client.post(target, json={"user_id": user_id, "features": [0.1, 0.2, 0.3]}, timeout=30.0)
        r.raise_for_status()
        return time.perf_counter() - start
    except Exception as exc:
        print(f"  request {user_id} failed: {exc}", file=sys.stderr)
        return None


async def _worker(
    name: int,
    queue: asyncio.Queue[int],
    client: httpx.AsyncClient,
    target: str,
    latencies: list[float],
    progress: dict[str, int],
    total: int,
) -> None:
    while True:
        try:
            user_id = queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        lat = await _send_one(client, target, user_id)
        if lat is not None:
            latencies.append(lat)
        progress["done"] += 1
        if progress["done"] % 50 == 0 or progress["done"] == total:
            done = progress["done"]
            print(f"  progress: {done}/{total} ({100 * done / total:.1f}%)")
        queue.task_done()


async def drive_load(target: str, requests: int, workers: int) -> list[float]:
    print(f"firing {requests} requests at {target} with {workers} concurrent workers")
    queue: asyncio.Queue[int] = asyncio.Queue()
    for i in range(requests):
        queue.put_nowait(i)
    latencies: list[float] = []
    progress = {"done": 0}
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            *(_worker(w, queue, client, target, latencies, progress, requests) for w in range(workers))
        )
    elapsed = time.perf_counter() - started
    print(f"finished {len(latencies)}/{requests} successful requests in {elapsed:.1f}s")
    return latencies


def report_client_side_stats(latencies: list[float]) -> None:
    if not latencies:
        print("no successful requests, cannot compute stats")
        return
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)

    def q(p: float) -> float:
        idx = max(0, min(n - 1, int(round(p * (n - 1)))))
        return sorted_lat[idx]

    print("client-side latency statistics:")
    print(f"  count : {n}")
    print(f"  mean  : {statistics.mean(sorted_lat):.3f} s")
    print(f"  p50   : {q(0.50):.3f} s")
    print(f"  p95   : {q(0.95):.3f} s")
    print(f"  p99   : {q(0.99):.3f} s")
    print(f"  max   : {sorted_lat[-1]:.3f} s")


async def probe_grafana_alerts(base_url: str, user: str, password: str) -> None:
    url = base_url.rstrip("/") + GRAFANA_ALERTS_PATH
    print(f"probing Grafana alerts: {url}")
    try:
        async with httpx.AsyncClient(auth=(user, password), timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            payload: list[dict[str, Any]] = r.json()
    except Exception as exc:
        print(f"  probe failed: {exc}", file=sys.stderr)
        return

    if not payload:
        print("  Grafana reports no active alerts yet (rule may still be pending - wait ~2m after sustained breach)")
        return

    print(f"  {len(payload)} alert(s) reported by Grafana Alertmanager:")
    for entry in payload:
        labels = entry.get("labels", {})
        status = entry.get("status", {})
        state = status.get("state") if isinstance(status, dict) else status
        active_at = entry.get("startsAt") or entry.get("activeAt")
        print(f"    - alertname={labels.get('alertname')} severity={labels.get('severity')} state={state} startsAt={active_at}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Drive ml_service load and optionally probe Grafana alerts")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="POST /predict endpoint")
    parser.add_argument("--mode", choices=["normal", "degraded"], default="degraded", help="Hint only; LATENCY_MODE is set on the server side via env")
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--probe-grafana-api", action="store_true", help="After load, query Grafana alerts API and print state")
    parser.add_argument("--grafana-url", default=DEFAULT_GRAFANA)
    parser.add_argument("--grafana-user", default="admin")
    parser.add_argument("--grafana-password", default="admin")
    args = parser.parse_args()

    print(f"mode hint: {args.mode} (effective behaviour controlled by LATENCY_MODE env on ml_service)")
    latencies = asyncio.run(drive_load(args.target, args.requests, args.workers))
    report_client_side_stats(latencies)

    if args.probe_grafana_api:
        asyncio.run(probe_grafana_alerts(args.grafana_url, args.grafana_user, args.grafana_password))

    if args.mode == "degraded" and latencies:
        p95 = sorted(latencies)[int(round(0.95 * (len(latencies) - 1)))]
        if p95 < 1.0:
            print("  warning: client-side p95 < 1s - проверьте, что LATENCY_MODE=degraded на ml_service контейнере")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
