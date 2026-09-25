#!/usr/bin/env python3
"""Execute the frozen F-E R-external 4-stone holdout exact solves.

Fresh FlatMemo81 process per state. No memo sharing. No outcome-cache load.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "10x10" / "f-e-r-external-holdout"
MANIFEST = OUT_DIR / "sampling_manifest.csv"
OUT_CSV = OUT_DIR / "exact_outcomes.csv"
RUN_MANIFEST = OUT_DIR / "solver_run_manifest.json"
SOLVER = ROOT / "cpp" / "solvers" / "kyouen_solver_10_f_e_plain.exe"
SOLVER_SRC = ROOT / "cpp" / "solvers" / "kyouen_solver_10_f_e_plain.cpp"
MEMO_POWER = 28
TIMEOUT_S = 600


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 36:
        raise SystemExit(f"expected 36 manifest rows, got {len(rows)}")
    return rows


def write_run_manifest(rows: list[dict[str, str]]) -> None:
    protocol = {
        "format": 1,
        "prereg": "docs/10X10_F_E_R_EXTERNAL_HOLDOUT_PREREG.md",
        "sampling_manifest_sha256": sha256_file(MANIFEST),
        "solver_binary": str(SOLVER.relative_to(ROOT)),
        "solver_binary_sha256": sha256_file(SOLVER) if SOLVER.exists() else "",
        "solver_source_sha256": sha256_file(SOLVER_SRC),
        "memo_power": MEMO_POWER,
        "timeout_seconds": TIMEOUT_S,
        "fresh_process_per_state": True,
        "memo_sharing": "forbidden",
        "outcome_cache_load": "forbidden",
        "labels_used_before_manifest": False,
        "states": [r["raw_state"] for r in rows],
    }
    RUN_MANIFEST.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if not SOLVER.exists():
        raise SystemExit(f"missing solver binary: {SOLVER}")
    rows = load_manifest()
    write_run_manifest(rows)

    completed = set()
    if OUT_CSV.exists():
        with OUT_CSV.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                completed.add(r.get("raw_state") or r.get("state"))
    pending = [r for r in rows if r["raw_state"] not in completed]
    print(f"pending={len(pending)} completed={len(completed)}", flush=True)

    fields = [
        "index",
        "stratum",
        "canonical_key",
        "raw_state",
        "sigma_d",
        "outcome",
        "visited",
        "memo_used",
        "seconds",
        "wall_seconds",
    ]
    new_file = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
    out_f = OUT_CSV.open("a" if not new_file else "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_f, fieldnames=fields)
    if new_file:
        writer.writeheader()
        out_f.flush()

    for row in pending:
        state = row["raw_state"]
        inp = OUT_DIR / f"_task_{row['index']}.txt"
        inp.write_text(state + "\n", encoding="ascii")
        t0 = time.time()
        try:
            proc = subprocess.run(
                [str(SOLVER), str(inp), str(MEMO_POWER)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=TIMEOUT_S,
            )
            wall = time.time() - t0
            parsed = list(csv.DictReader(proc.stdout.splitlines()))
            if len(parsed) != 1:
                outcome, visited, memo_used, seconds = "ERROR_parse", "", "", ""
            else:
                pr = parsed[0]
                outcome = pr["outcome"]
                visited = pr["visited"]
                memo_used = pr["memo_used"]
                seconds = pr["seconds"]
        except subprocess.TimeoutExpired:
            wall = time.time() - t0
            outcome, visited, memo_used, seconds = "TIMEOUT", "", "", ""
        finally:
            inp.unlink(missing_ok=True)

        writer.writerow(
            {
                "index": row["index"],
                "stratum": row["stratum"],
                "canonical_key": row["canonical_key"],
                "raw_state": state,
                "sigma_d": row["sigma_d"],
                "outcome": outcome,
                "visited": visited,
                "memo_used": memo_used,
                "seconds": seconds,
                "wall_seconds": f"{wall:.6f}",
            }
        )
        out_f.flush()
        print(
            f"[{int(row['index']):02d}/{len(rows)}] {state} {outcome} "
            f"visited={visited} wall={wall:.1f}s",
            flush=True,
        )

    out_f.close()
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
