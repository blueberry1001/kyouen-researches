#!/usr/bin/env python3
"""Classify 9x9 first-move D4 orbits (excluding already-known center)."""
from __future__ import annotations

import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / ".slim" / "worktrees" / "research-properties" / "cpp" / "solvers" / "kyouen_solver_9.exe"
OUT = Path(__file__).resolve().parent / "first-moves-9x9.csv"
MEMO_POWER = 30
PARALLEL = 1
TIMEOUT_S = 5400

CLASSES = [
    (0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
    (1, 1), (1, 2), (1, 3), (1, 4),
    (2, 2), (2, 3), (2, 4),
    (3, 3), (3, 4),
]


def first_id(a: int, b: int) -> int:
    return b * 9 + a


def load_done() -> set[tuple[int, int]]:
    done: set[tuple[int, int]] = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("verdict") in {"FIRST_WIN", "FIRST_LOSS"}:
                    done.add((int(row["a"]), int(row["b"])))
    return done


def run_one(a: int, b: int) -> dict:
    fid = first_id(a, b)
    p = subprocess.run(
        [str(SOLVER), str(fid), str(MEMO_POWER)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
    )
    out = p.stdout + "\n" + p.stderr
    verdict = None
    if "leaves LOSS" in out:
        verdict = "FIRST_WIN"
    elif "leaves WIN" in out:
        verdict = "FIRST_LOSS"
    elif "memo table over" in out:
        verdict = "MEMO_OVER"
    stats: dict[str, str] = {}
    for token in out.replace("\n", " ").split():
        if "=" in token:
            k, v = token.split("=", 1)
            if k in {"states", "memo", "depth", "seconds", "visited"}:
                stats[k] = v
    return {
        "a": a,
        "b": b,
        "first_id": fid,
        "verdict": verdict or f"UNKNOWN rc={p.returncode}",
        "rc": p.returncode,
        **stats,
        "stderr_tail": (p.stderr or "")[-200:].replace("\n", " | "),
    }


def main() -> None:
    done = load_done()
    todo = [c for c in CLASSES if c not in done]
    print(f"done {len(done)}/{len(CLASSES)} remaining {len(todo)}", flush=True)
    if not todo:
        return
    newfile = not OUT.exists()
    with OUT.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "a", "b", "first_id", "verdict", "rc",
                "states", "memo", "depth", "seconds", "visited", "stderr_tail",
            ],
            extrasaction="ignore",
        )
        if newfile:
            w.writeheader()
        with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
            futs = {ex.submit(run_one, a, b): (a, b) for a, b in todo}
            for fut in as_completed(futs):
                a, b = futs[fut]
                try:
                    r = fut.result()
                except Exception as e:
                    r = {
                        "a": a, "b": b, "first_id": first_id(a, b),
                        "verdict": f"ERROR:{type(e).__name__}:{e}", "rc": -1,
                    }
                w.writerow(r)
                f.flush()
                print(
                    f"({r['a']},{r['b']}) -> {r['verdict']} "
                    f"states={r.get('states','')} seconds={r.get('seconds','')}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
