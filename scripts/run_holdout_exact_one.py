#!/usr/bin/env python3
"""Solve one holdout exact task with the frozen holdout solver binary.

Usage: run_holdout_exact_one.py <parent> <batch> <pos> <state> <out_csv>

Appends a single WIN/LOSS row to out_csv (with header if new). Uses the same
tmp-kb/probe_holdout_native binary + shrink/load lineage as the probes
(shrink 0 / load 90 for full exactitude, budget 0 = unbounded).
Refuses to run if the solver sources changed since --build.
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from run_probe_holdout_independent import (  # noqa: E402
    SOLVER_BIN,
    require_fresh_solver,
)

SHRINK = "0"
LOAD = "90"

FIELDS = ["parent", "batch", "batch_position", "state", "outcome",
          "visited", "maxdepth", "memo", "seconds"]


def main() -> None:
    parent, batch, pos, state, out_csv = sys.argv[1:6]
    require_fresh_solver()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=SOLVER_BIN.parent, encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(SOLVER_BIN), str(tmp_path), SHRINK, LOAD, "0", "0"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise SystemExit(f"solver failed for {state}: rc={proc.returncode}\n{proc.stderr[-1000:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise SystemExit(f"expected 1 row, got {len(rows)}")
    row = rows[0]
    if row["outcome"] not in ("WIN", "LOSS"):
        raise SystemExit(f"non-exact outcome: {row['outcome']}")
    out = Path(out_csv)
    new = not out.exists() or out.stat().st_size == 0
    with out.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"parent": parent, "batch": batch, "batch_position": pos,
                    "state": row["state"], "outcome": row["outcome"],
                    "visited": row["visited"], "maxdepth": row["maxdepth"],
                    "memo": row["memo"], "seconds": row["seconds"]})
    print(f"{parent} {state} {row['outcome']} visited={row['visited']}")


if __name__ == "__main__":
    main()
