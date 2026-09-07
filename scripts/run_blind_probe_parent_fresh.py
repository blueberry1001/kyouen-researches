#!/usr/bin/env python3
"""Corrected blind-probe runner: one solver process per child.

This intentionally does not reuse the historical batch runner because the
native solver keeps one Solver object for every row in an input file.
"""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "scripts" / "probe_cert_solver"
DIR = ROOT / "results" / "10x10" / "blind_probe_children"
BUDGETS = {3: 1_000_000, 4: 10_000, 5: 10_000}
SHRINK, LOAD = 3, 80


def wsl_path(p: Path) -> str:
    p = p.resolve(); parts = p.parts
    drive = parts[0].rstrip(":\\").lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace("\\", "/")


def run_one(state: str, budget: int) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir=DIR, encoding="utf-8") as f:
        f.write(state + "\n"); tmp = Path(f.name)
    try:
        cmd = ["wsl", "bash", "-c",
               f"cd {wsl_path(ROOT)} && {wsl_path(SOLVER)} {wsl_path(tmp)} {SHRINK} {LOAD} {budget} 0"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        tmp.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"solver rc={proc.returncode} state={state}: {proc.stderr[-500:].decode(errors='replace')}")
    rows = list(csv.DictReader(proc.stdout.decode().splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected one row for {state}, got {len(rows)}")
    return rows[0]


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_blind_probe_parent_fresh.py <parent> <stones>")
    parent, stones = sys.argv[1], int(sys.argv[2])
    budget = BUDGETS[stones]; safe = parent.replace(",", "_")
    batch_files = sorted(DIR.glob(f"children_{safe}_batch*.txt"))
    if not batch_files:
        raise SystemExit(f"no batch files for {parent}")
    for bp in batch_files:
        bi = int(bp.stem.split("batch")[-1])
        out = DIR / f"probe_fresh_{safe}_batch{bi}_{budget}.csv"
        states = [x.strip() for x in bp.read_text(encoding="utf-8").splitlines() if x.strip()]
        rows = [run_one(s, budget) for s in states]
        fields = list(rows[0].keys())
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        # Freshness invariant: absolute memo must describe only this child.
        # It may exceed visited slightly due to bookkeeping, but not by batch-scale accumulation.
        bad = [r for r in rows if int(r["memo"]) > max(int(r["visited"]) * 3, budget * 3)]
        if bad:
            raise RuntimeError(f"freshness sanity check failed in batch {bi}: {len(bad)} suspicious rows")
        print(f"{parent} batch {bi}: wrote {len(rows)} fresh probes -> {out.name}")


if __name__ == "__main__":
    main()
