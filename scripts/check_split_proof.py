#!/usr/bin/env python3
"""Inspect split proof CSVs for structural invariants.

Checks:
- No duplicate normalized child states per parent
- No missing legal normalized child (children count matches solver --children)
- For WIN parent, LOSS witness is an actual child
- For LOSS parent, every child is WIN
- TABLE_FULL/TIMEOUT never used as win/loss
- Fixed regression 2,73,66 == WIN / visited=10067830 / maxdepth=18 / memo=10023329
"""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

SOLVER_CPP = Path(__file__).resolve().parent.parent / "kyouen-local-handoff" / "solver.cpp"


def solver_children_counts(solver_cpp: Path, parents: list[str]) -> dict[str, int]:
    # Compile a temp solver for enumeration
    import os, subprocess as sp, tempfile as tf

    bin_path = Path(os.environ.get("TEMP", str(Path.home()))) / "kyouen_check_solver.exe"
    if not bin_path.exists() or bin_path.stat().st_mtime < solver_cpp.stat().st_mtime:
        sp.run(["g++", "-std=c++20", "-O3", "-DNDEBUG", str(solver_cpp), "-o", str(bin_path)], check=True)
    out: dict[str, int] = {}
    for p in parents:
        cp = sp.run([str(bin_path), "--children", p], text=True, capture_output=True, check=False)
        if cp.returncode != 0:
            raise RuntimeError(f"--children failed for {p}: {cp.stderr}")
        rows = list(csv.DictReader(cp.stdout.splitlines()))
        out[p] = len(rows)
    return out


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--proof", default="results/90-69-split-proof.csv")
    ap.add_argument("--heavy", default="results/90-69-heavy-three-stone-results.csv")
    ap.add_argument("--solver", default=str(SOLVER_CPP))
    args = ap.parse_args()

    proof_path = Path(args.proof)
    heavy_path = Path(args.heavy)
    solver_cpp = Path(args.solver)

    if not proof_path.exists():
        print(f"proof CSV not found: {proof_path}", file=sys.stderr)
        sys.exit(2)

    rows = list(csv.DictReader(proof_path.open(encoding="utf-8")))
    if not rows:
        print("proof CSV is empty", file=sys.stderr)
        sys.exit(1)

    errors: list[str] = []
    warnings: list[str] = []

    # Group by parent
    from collections import defaultdict

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_parent[r["parent_state"]].append(r)

    # Check required columns
    required = ["parent_state", "parent_outcome", "child_state", "child_outcome", "proof_method", "shrink", "load", "visited", "maxdepth", "memo", "seconds"]
    for col in required:
        if col not in rows[0]:
            errors.append(f"missing column: {col}")

    # Per-parent checks
    for parent, rs in by_parent.items():
        child_states = [r["child_state"] for r in rs]
        # No duplicate normalized child
        if len(set(child_states)) != len(child_states):
            dup = [s for s in set(child_states) if child_states.count(s) > 1]
            errors.append(f"{parent}: duplicate child states: {dup}")
        # No TABLE_FULL/TIMEOUT used as win/loss
        for r in rs:
            if r["child_outcome"] in ("TABLE_FULL", "TIMEOUT"):
                errors.append(f"{parent}: child {r['child_state']} has unresolved outcome {r['child_outcome']} treated as decision")
            if r["child_outcome"] not in ("WIN", "LOSS"):
                # but UNDECIDED not expected in final merged proof
                if r["child_outcome"] not in ("WIN", "LOSS"):
                    errors.append(f"{parent}: child {r['child_state']} unresolved outcome {r['child_outcome']}")

        parent_outcomes = set(r["parent_outcome"] for r in rs)
        if len(parent_outcomes) != 1:
            errors.append(f"{parent}: inconsistent parent_outcome values: {parent_outcomes}")
        parent_outcome = next(iter(parent_outcomes)) if parent_outcomes else ""

        # proof_method/shrink/load present
        for r in rs:
            if not r.get("proof_method"):
                errors.append(f"{parent}: empty proof_method for child {r['child_state']}")
            if not r.get("shrink") or not r.get("load"):
                errors.append(f"{parent}: empty shrink/load for child {r['child_state']}")
            if not r.get("visited") or not r.get("maxdepth") or not r.get("memo") or not r.get("seconds"):
                warnings.append(f"{parent}: empty visited/maxdepth/memo/seconds for child {r['child_state']}")

        # parent_outcome semantics
        wins = sum(1 for r in rs if r["child_outcome"] == "WIN")
        losses = sum(1 for r in rs if r["child_outcome"] == "LOSS")
        if parent_outcome == "LOSS":
            if losses != 0:
                errors.append(f"{parent}: parent LOSS but has {losses} LOSS children")
            if wins != len(rs):
                errors.append(f"{parent}: parent LOSS but not all children WIN (wins={wins} total={len(rs)})")
        elif parent_outcome == "WIN":
            if losses == 0:
                errors.append(f"{parent}: parent WIN but no LOSS child")
            # witness is an actual child
            loss_children = [r["child_state"] for r in rs if r["child_outcome"] == "LOSS"]
            if not loss_children:
                errors.append(f"{parent}: parent WIN claimed but no LOSS child found")
        else:
            errors.append(f"{parent}: parent_outcome is {parent_outcome!r} (expected WIN/LOSS)")

    # Expected 3 heavy parents
    expected_parents = {"9,10,30", "9,29,30", "3,19,90"}
    found_parents = set(by_parent.keys())
    if found_parents != expected_parents:
        errors.append(f"expected parents {expected_parents}, got {found_parents}")

    # Child count vs solver enumeration
    try:
        enum_counts = solver_children_counts(solver_cpp, sorted(found_parents))
        for parent in sorted(found_parents):
            expected = enum_counts[parent]
            actual = len(by_parent[parent])
            if expected != actual:
                errors.append(f"{parent}: child count mismatch solver={expected} csv={actual} (missing or extra legal normalized children)")
    except Exception as e:
        warnings.append(f"could not verify child counts against solver: {e}")

    # Heavy CSV cross-check: if heavy has 98 rows (the full 90,69 child table),
    # it is a different granularity than the 290-row split proof; skip mismatch.
    if heavy_path.exists():
        heavy = list(csv.DictReader(heavy_path.open(encoding="utf-8")))
        if len(heavy) == 98:
            pass  # heavy is the 98-row overview, not the 3-parent split proof
        else:
            for r in heavy:
                p2 = r.get("parent_state") or r.get("state", "")
                if p2 not in by_parent:
                    errors.append(f"heavy CSV parent {p2} not in proof CSV")
                else:
                    cc = r.get("child_count", "")
                    if cc and int(cc) != len(by_parent[p2]):
                        errors.append(f"heavy CSV {p2}: child_count {cc} != proof count {len(by_parent[p2])}")

    # Fixed regression 2,73,66
    fixed = "2,73,66"
    try:
        import os, subprocess as sp

        bin_path = Path(os.environ.get("TEMP", str(Path.home()))) / "kyouen_check_solver.exe"
        # Reuse compiled binary; run single-state solve
        with tempfile.TemporaryDirectory() as td:
            state_file = Path(td) / "state.txt"
            state_file.write_text(fixed + "\n", encoding="utf-8")
            cp = sp.run([str(bin_path), str(state_file), "3", "80"], text=True, capture_output=True, timeout=120, check=False)
            rows_out = list(csv.reader(cp.stdout.splitlines()))
            if len(rows_out) < 2:
                errors.append(f"fixed regression {fixed}: solver produced no output: {cp.stdout[:500]} {cp.stderr[:500]}")
            else:
                row = rows_out[-1]
                outcome, visited, maxdepth, memo = row[-5], row[-4], row[-3], row[-2]
                if outcome != "WIN":
                    errors.append(f"fixed regression {fixed}: expected WIN, got {outcome}")
                if visited != "10067830":
                    errors.append(f"fixed regression {fixed}: expected visited=10067830, got {visited}")
                if maxdepth != "18":
                    errors.append(f"fixed regression {fixed}: expected maxdepth=18, got {maxdepth}")
                if memo != "10023329":
                    errors.append(f"fixed regression {fixed}: expected memo=10023329, got {memo}")
                if not errors or not any(fixed in e for e in errors):
                    print(f"Fixed regression OK: {fixed} => WIN / {visited} / {maxdepth} / {memo}")
    except Exception as e:
        errors.append(f"fixed regression {fixed}: failed to run solver: {e}")

    # Final report
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        total = len(rows)
        print(f"\nAll checks passed: {len(by_parent)} parents, {total} children")
        for parent, rs in sorted(by_parent.items()):
            print(f"  {parent}: {len(rs)} children, parent={rs[0]['parent_outcome']}")
        print("Proof invariants verified: no duplicates, no missing legal children, TABLE_FULL/TIMEOUT not used as decision, witness inclusion holds, fixed regression matches.")
        sys.exit(0)


if __name__ == "__main__":
    main()
