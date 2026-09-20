#!/usr/bin/env python3
"""Resumable local orchestrator for clean holdout V2.

The frozen parent selection/ranking lives in committed files. This script only
parallelizes the already-frozen probe and exact task sets; it does not inspect
outcomes to change scheduling or ranking.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2" / "logs"


def run_cmd(label: str, cmd: list[str]) -> tuple[str, int]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{label}.log"
    with log.open("w", encoding="utf-8") as f:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=f, stderr=subprocess.STDOUT)
    return label, proc.returncode


def run_shards(kind: str, workers: int, timeout: float) -> None:
    if workers < 1:
        raise RuntimeError("worker count must be positive")
    jobs: list[tuple[str, list[str]]] = []
    for i in range(workers):
        if kind == "probe":
            cmd = [sys.executable, "scripts/run_probe_holdout_v2.py", "--run",
                   "--shards", str(workers), "--shard-index", str(i)]
        elif kind == "exact":
            cmd = [sys.executable, "scripts/run_holdout_v2_exact_shard.py", "--run",
                   "--shards", str(workers), "--shard-index", str(i),
                   "--timeout", str(timeout)]
        else:
            raise AssertionError(kind)
        jobs.append((f"{kind}_w{i:02d}-of-{workers:02d}", cmd))

    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(run_cmd, label, cmd): label for label, cmd in jobs}
        for fut in as_completed(futures):
            label, rc = fut.result()
            print(f"{label}: rc={rc}")
            if rc != 0:
                failures.append(label)
    if failures:
        raise SystemExit(f"{kind} shard failures: {failures}; inspect {LOG_DIR}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-workers", type=int, default=4)
    ap.add_argument("--exact-workers", type=int, default=4)
    ap.add_argument("--exact-timeout", type=float, default=5400.0)
    ap.add_argument("--skip-probe", action="store_true")
    ap.add_argument("--skip-exact", action="store_true")
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()

    if not args.analyze_only:
        subprocess.run([sys.executable, "scripts/run_probe_holdout_v2.py", "--build",
                        "--shards", str(args.probe_workers)], cwd=REPO_ROOT, check=True)
        if not args.skip_probe:
            run_shards("probe", args.probe_workers, args.exact_timeout)
        if not args.skip_exact:
            run_shards("exact", args.exact_workers, args.exact_timeout)

    subprocess.run([sys.executable, "scripts/analyze_probe_holdout_v2.py"],
                   cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
