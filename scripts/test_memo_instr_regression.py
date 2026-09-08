#!/usr/bin/env python3
"""Regression gate for the instrumented solver (prereg guard).

On short exactly-solvable states, compares three modes:
  frozen tmp-kb/parent_bench_native vs new binary OFF vs new binary ON.
Requires exact agreement on outcome, visited, memo_used, maxdepth, and
root-ordering diagnostics (bench_root unique/entered/first/witness).
ON mode additionally passes internal counter invariant checks.

Must pass before the 12-parent cohort starts. Must run under WSL/Linux.
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_BIN = REPO_ROOT / "tmp-kb" / "parent_bench_native"
NEW_BIN = REPO_ROOT / "tmp-kb" / "memo_instr_native"

# (comma state, root-diag depth); 4-stone children + one cheap 3-stone parent
STATES = [("13,52,57,76", 4), ("4,24,26,67", 4), ("14,64,74", 3)]


def run_exact(binary: Path, state: str, depth: int,
              instr: Path | None) -> tuple[dict[str, str], dict[str, str],
                                           list[dict[str, str]]]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = tmp.name
    try:
        cmd = [str(binary), tmp_path, "0", "90", "0", "0",
               "--root-depth", str(depth)]
        if instr is not None:
            cmd += ["--memo-instr-out", str(instr)]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True,
                              capture_output=True, timeout=3600)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        raise AssertionError(f"{binary.name} {state} rc={proc.returncode}\n"
                             f"{proc.stderr[-600:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert len(rows) == 1, (state, proc.stdout[-200:])
    bench: dict[str, str] = {}
    for line in proc.stderr.splitlines():
        if line.startswith("bench_root "):
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                bench[k] = v
    assert bench, f"no bench_root for {state}:\n{proc.stderr[-600:]}"
    drows: list[dict[str, str]] = []
    if instr is not None:
        with instr.open(newline="", encoding="utf-8") as f:
            drows = list(csv.DictReader(f))
    return rows[0], bench, drows


def check_invariants(state: str, row: dict[str, str],
                     drows: list[dict[str, str]]) -> None:
    tot_miss = tot_put = tot_look = 0
    for d in drows:
        v = {k: int(d[k]) for k in d if k not in ("depth",)}
        e = v["entry_lookup_calls"]
        assert e == v["entry_hit_win"] + v["entry_hit_loss"] + v["entry_miss"], d
        assert v["prefetch_calls"] == v["prefetch_hit_win"] + \
            v["prefetch_hit_loss"] + v["prefetch_miss"], d
        assert v["put_win"] + v["put_loss"] == v["entry_miss"], d
        assert v["put_win"] == v["solved_win_nodes"], d
        consumed = v["child_eval_from_cache_win"] + \
            v["child_eval_from_cache_loss"] + v["child_eval_recursive"]
        assert consumed <= v["prefetch_calls"], d
        assert v["child_eval_from_cache_win"] <= v["prefetch_hit_win"], d
        assert v["child_eval_from_cache_loss"] <= v["prefetch_hit_loss"], d
        assert v["child_eval_recursive"] <= v["prefetch_miss"], d
        assert v["nodes_cache_changes_first_child"] <= \
            v["nodes_cache_changes_full_order"], d
        assert v["actual_first_cached_loss"] <= \
            v["win_return_from_cached_loss_child"] <= \
            v["solved_win_nodes"], d
        assert v["visited_nonterminal_nodes"] <= v["entry_miss"], d
        tot_miss += v["entry_miss"]
        tot_put += v["put_win"] + v["put_loss"]
        tot_look += e
    assert tot_miss == int(row["visited"]), (state, tot_miss, row["visited"])
    assert tot_put == int(row["visited"]), (state, tot_put)
    assert tot_look >= int(row["visited"]), (state, tot_look)


def main() -> int:
    assert FROZEN_BIN.exists() and NEW_BIN.exists()
    for state, depth in STATES:
        fz, fzb, _ = run_exact(FROZEN_BIN, state, depth, None)
        of, ofb, _ = run_exact(NEW_BIN, state, depth, None)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                         encoding="utf-8") as itmp:
            instr_path = Path(itmp.name)
        try:
            on, onb, drows = run_exact(NEW_BIN, state, depth, instr_path)
        finally:
            instr_path.unlink(missing_ok=True)
        for tag, row in (("OFF", of), ("ON", on)):
            for c in ("outcome", "visited", "maxdepth", "memo"):
                assert row[c] == fz[c], (state, tag, c, row[c], fz[c])
            for c in ("unique", "entered", "first_lo", "first_hi",
                      "witness", "outcome"):
                got, want = (onb if tag == "ON" else ofb)[c], fzb[c]
                assert got == want, (state, tag, c, got, want)
        check_invariants(state, on, drows)
        print(f"  {state}: frozen==OFF==ON "
              f"({on['outcome']} visited={on['visited']} "
              f"maxdepth={on['maxdepth']} memo={on['memo']} "
              f"depthrows={len(drows)}) invariants ok")
    print("ALL INSTRUMENTATION REGRESSION TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
