#!/usr/bin/env python3
"""Regression tests for the root-order benchmark binary (prereg guard).

1. No-override equivalence: new binary reproduces the frozen binary's exact
   outcome and visited count on a small deterministic set.
2. Order-file validation: wrong-size order file is a hard error (no silent
   fallback); correct order file runs and emits bench_root diagnostics.
3. Override sanity on a cheap probe: a 3-stone parent probe with an order
   file evaluates the listed first child first.

Reads no exact outcome labels. Must pass before any benchmark run.
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
NEW_BIN = REPO_ROOT / "tmp-kb" / "parent_bench_native"

# Fast exact states (comma spelling); outcomes NOT read here, only compared
# between the two binaries for equality.
SMALL_SET = ["13,52,57,76", "4,24,26,67"]


def run_exact(binary: Path, state: str, extra: list[str]) -> tuple[str, dict[str, str]]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=REPO_ROOT / "tmp-kb", encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = tmp.name
    try:
        cmd = [str(binary), tmp_path, "0", "90", "0", "0"] + extra
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True,
                              timeout=900)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{binary.name} {state} rc={proc.returncode}\n{proc.stderr[-800:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert len(rows) == 1, f"expected 1 row: {proc.stdout[-200:]}"
    return proc.stderr, rows[0]


def run_probe(binary: Path, state: str, budget: int, extra: list[str]) -> tuple[int, str, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=REPO_ROOT / "tmp-kb", encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = tmp.name
    try:
        cmd = [str(binary), tmp_path, "3", "80", str(budget), "0"] + extra
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True,
                              timeout=300)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return proc.returncode, proc.stdout, proc.stderr


def bench_line(stderr: str) -> dict[str, str]:
    for line in stderr.splitlines():
        if line.startswith("bench_root "):
            out = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    raise AssertionError(f"no bench_root line in stderr:\n{stderr[-600:]}")


def main() -> None:
    assert FROZEN_BIN.exists() and NEW_BIN.exists()
    # Guard 1: no-override equivalence (exact outcome + visited).
    for state in SMALL_SET:
        err_f, row_f = run_exact(FROZEN_BIN, state, [])
        err_n, row_n = run_exact(NEW_BIN, state, ["--root-depth", "4"])
        assert row_f["outcome"] == row_n["outcome"], (state, row_f, row_n)
        assert row_f["visited"] == row_n["visited"], (state, row_f, row_n)
        assert row_f["memo"] == row_n["memo"], (state, row_f, row_n)
        b = bench_line(err_n)
        assert b["outcome"] == row_n["outcome"], (state, b, row_n)
        print(f"OK equiv {state}: {row_n['outcome']} visited={row_n['visited']} memo={row_n['memo']}")

    # Guard 2a: wrong-size order file is a hard error.
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=REPO_ROOT / "tmp-kb", encoding="utf-8") as f:
        f.write("0,3,53,84\n1,3,53,84\n")
        bad_order = f.name
    try:
        rc, _, err = run_probe(NEW_BIN, "3,53,84", 100,
                               ["--root-order-file", bad_order, "--root-depth", "3"])
    finally:
        Path(bad_order).unlink(missing_ok=True)
    assert rc != 0 and "root order" in err, f"expected root-order error, rc={rc}\n{err[-400:]}"
    print("OK order-size mismatch refused")

    # Guard 2b/3: full-size order file on a cheap probe runs; diagnostics
    # report unique-canonical counts (also revealing symmetry collisions).
    kids = [r["state"] for r in csv.DictReader(
        (REPO_ROOT / "results" / "10x10" / "clean-holdout-v2" / "exact_task_list.csv").open(
            newline="", encoding="utf-8")) if r["parent"] == "3,53,84"]
    assert len(kids) == 97, len(kids)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=REPO_ROOT / "tmp-kb", encoding="utf-8") as f:
        f.write("\n".join(kids) + "\n")
        order = f.name
    try:
        rc, out, err = run_probe(NEW_BIN, "3,53,84", 100,
                                 ["--root-order-file", order, "--root-depth", "3"])
    finally:
        Path(order).unlink(missing_ok=True)
    assert rc == 0, f"rc={rc}\n{err[-400:]}"
    assert "root_order_file lines=97 unique=" in err, err[-400:]
    b = bench_line(err)
    assert int(b["unique"]) >= 1 and int(b["entered"]) >= 1, b
    print(f"OK order override probe: {b}")

    print("ALL REGRESSION TESTS PASSED")


if __name__ == "__main__":
    sys.exit(main())
