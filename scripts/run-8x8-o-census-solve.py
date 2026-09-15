#!/usr/bin/env python3
"""Sharded exact solve of frozen 8x8 required roots (full census).

Reads artifacts/8x8-o-required-roots.csv (frozen) and runs
cpp/solvers/kyouen_solver_8_root.exe on shards. Writes per-shard logs and a
merged outcomes CSV. Does not alter strata or success criteria.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTS = ROOT / "artifacts" / "8x8-o-required-roots.csv"
OUT_DIR = ROOT / "artifacts" / "8x8-o-solve"
MERGED = ROOT / "artifacts" / "8x8-o-census-outcomes.csv"
MANIFEST = ROOT / "artifacts" / "8x8-o-solve-manifest.json"
SOLVER = ROOT / "cpp" / "solvers" / "kyouen_solver_8_root.exe"
if not SOLVER.exists():
    SOLVER = ROOT / "cpp" / "solvers" / "kyouen_solver_8_root"

MEMO_POWER = 26


def load_roots():
    rows = []
    with ROOTS.open(newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "canonical_parent": r["canonical_parent"],
                    "move": int(r["move"]),
                    "stratum": r["stratum"],
                    "canonical_child5": r["canonical_child5"],
                }
            )
    return rows


def write_shard_input(path: Path, rows):
    with path.open("w", newline="") as f:
        f.write("canonical_parent,move\n")
        for r in rows:
            f.write(f'"{r["canonical_parent"]}",{r["move"]}\n')


def run_shard(shard_id: int, rows) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inp = OUT_DIR / f"shard-{shard_id:03d}.in.csv"
    outp = OUT_DIR / f"shard-{shard_id:03d}.out.csv"
    errp = OUT_DIR / f"shard-{shard_id:03d}.err.log"
    codep = OUT_DIR / f"shard-{shard_id:03d}.exit.txt"
    write_shard_input(inp, rows)
    t0 = time.time()
    with outp.open("w") as out, errp.open("w") as err:
        proc = subprocess.run(
            [str(SOLVER), str(inp), str(MEMO_POWER)],
            stdout=out,
            stderr=err,
            cwd=str(ROOT),
        )
    codep.write_text(str(proc.returncode) + "\n")
    elapsed = time.time() - t0
    # Count result rows (exclude header)
    n_out = 0
    if outp.exists():
        with outp.open() as f:
            n_out = sum(1 for line in f if line.strip()) - 1
    return {
        "shard_id": shard_id,
        "expected_rows": len(rows),
        "result_rows": max(n_out, 0),
        "exit_code": proc.returncode,
        "seconds": elapsed,
        "input": str(inp.relative_to(ROOT)),
        "output": str(outp.relative_to(ROOT)),
        "stderr": str(errp.relative_to(ROOT)),
        "ok": proc.returncode == 0 and n_out == len(rows),
    }


def main():
    if not ROOTS.exists():
        print(f"missing {ROOTS}", file=sys.stderr)
        return 1
    if not SOLVER.exists():
        print(f"missing solver {SOLVER}", file=sys.stderr)
        return 1

    roots = load_roots()
    n = len(roots)
    # Shards: balance by index; 8x8 roots are cheap, use ~8-12 shards.
    n_shards = min(12, max(1, n // 40))
    shards = [[] for _ in range(n_shards)]
    for i, r in enumerate(roots):
        shards[i % n_shards].append(r)

    print(f"roots={n} shards={n_shards} memo_power={MEMO_POWER}")
    t0 = time.time()
    results = []
    # Parallel but limited; each solver instance uses its own memo.
    workers = min(n_shards, 8)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_shard, i, rows): i for i, rows in enumerate(shards)}
        for fut in as_completed(futs):
            res = fut.result()
            results.append(res)
            print(
                f"shard {res['shard_id']}: rows {res['result_rows']}/{res['expected_rows']} "
                f"exit={res['exit_code']} {res['seconds']:.2f}s ok={res['ok']}"
            )
    total_s = time.time() - t0

    # Merge outputs.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged_rows = []
    for res in sorted(results, key=lambda r: r["shard_id"]):
        outp = ROOT / res["output"]
        with outp.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                merged_rows.append(row)

    with MERGED.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "canonical_parent",
                "move",
                "child_outcome",
                "visited",
                "seconds",
                "memo_used",
            ],
        )
        w.writeheader()
        for row in merged_rows:
            w.writerow(row)

    import json

    all_ok = all(r["ok"] for r in results)
    manifest = {
        "roots_total": n,
        "shards": n_shards,
        "workers": workers,
        "memo_power": MEMO_POWER,
        "wall_seconds": total_s,
        "all_shards_ok": all_ok,
        "shards_detail": sorted(results, key=lambda r: r["shard_id"]),
        "merged_rows": len(merged_rows),
        "merged_file": str(MERGED.relative_to(ROOT)),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in manifest if k != "shards_detail"}, indent=2))
    return 0 if all_ok and len(merged_rows) == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
