#!/usr/bin/env python3
"""Run blind probe with one fresh solver process per child.

This is the correctness-first replacement for run_blind_probe_batch.py when
collecting child-comparable probe features. The historical runner passed the
whole batch to one Solver instance, so `memo` was cumulative across children.

Usage:
    python scripts/run_blind_probe_batch_isolated.py <parent> <batch_index> <stones>

Output:
    results/10x10/blind_probe_children/
      probe_isolated_<parent>_batch<batch>_<budget>.csv
      probe_isolated_<parent>_batch<batch>_<budget>.err

Each child is executed in a separate process, hence all memo/search statistics
start from a fresh Solver state.
"""

import csv
import io
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOLVER = REPO_ROOT / "scripts" / "probe_cert_solver"
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
FIXED_BUDGETS = {3: 1_000_000, 4: 10_000, 5: 10_000}
SHRINK = 3
LOAD = 80


def wsl_path(p: Path) -> str:
    p = p.resolve()
    parts = p.parts
    drive = parts[0].rstrip(":\\").lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace("\\", "/")


def run_one(state: str, budget: int) -> tuple[list[str], str]:
    # Keep the temporary file under the repo so the Windows->WSL path mapping
    # remains identical to the historical runner.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="probe_isolated_",
        dir=CHILDREN_DIR, delete=False, newline=""
    ) as tf:
        tf.write(state.rstrip() + "\n")
        tmp = Path(tf.name)

    try:
        cmd = [
            "wsl", "bash", "-c",
            f"cd {wsl_path(REPO_ROOT)} && "
            f"{wsl_path(SOLVER)} {wsl_path(tmp)} {SHRINK} {LOAD} {budget} 0",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode not in (0, 3):
            raise RuntimeError(
                f"solver rc={proc.returncode} for state={state}: "
                + proc.stderr.decode(errors="replace")
            )
        text = proc.stdout.decode(errors="replace")
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 2:
            raise RuntimeError(f"missing CSV row for state={state}: {text!r}")
        if len(rows) != 2:
            raise RuntimeError(f"expected exactly one task row, got {len(rows)-1}")
        return rows, proc.stderr.decode(errors="replace")
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: run_blind_probe_batch_isolated.py <parent> <batch_index> <stones>")
        raise SystemExit(2)

    parent = sys.argv[1]
    batch_index = int(sys.argv[2])
    stones = int(sys.argv[3])
    if stones not in FIXED_BUDGETS:
        raise SystemExit(f"unsupported stones={stones}")
    budget = FIXED_BUDGETS[stones]

    safe = parent.replace(",", "_")
    in_file = CHILDREN_DIR / f"children_{safe}_batch{batch_index}.txt"
    if not in_file.exists():
        raise SystemExit(f"Input file missing: {in_file}")

    states = [x.strip() for x in in_file.read_text().splitlines() if x.strip()]
    out_file = CHILDREN_DIR / f"probe_isolated_{safe}_batch{batch_index}_{budget}.csv"
    err_file = CHILDREN_DIR / f"probe_isolated_{safe}_batch{batch_index}_{budget}.err"

    header = None
    data_rows = []
    err_parts = []
    start = time.time()
    for i, state in enumerate(states, start=1):
        rows, err = run_one(state, budget)
        if header is None:
            header = rows[0]
        elif rows[0] != header:
            raise RuntimeError("solver CSV header changed between isolated runs")
        data_rows.append(rows[1])
        err_parts.append(f"===== {i}/{len(states)} {state} =====\n{err}")
        print(f"{parent} batch {batch_index}: isolated {i}/{len(states)} {state}")

    with out_file.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data_rows)
    err_file.write_text("\n".join(err_parts))

    elapsed = time.time() - start
    print(f"completed {len(states)} isolated probes in {elapsed:.1f}s")
    print(f"out={out_file}")
    print(f"err={err_file}")


if __name__ == "__main__":
    main()
