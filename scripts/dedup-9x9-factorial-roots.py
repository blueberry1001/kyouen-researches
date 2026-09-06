#!/usr/bin/env python3
"""
Deduplicate child roots across factorial comparisons to minimize exact solve workload.
Maps unique 5-stone roots (canonical_parent + move), runs them through solver,
and fans out results back to individual comparison CSVs.
"""

import sys
import csv
from pathlib import Path

def main():
    holdout_path = Path("experiments/9x9-factorial-execution-base/holdout.csv")
    solver_inputs_dir = Path("experiments/9x9-factorial-execution-base/solver_inputs")
    
    with open(holdout_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Total factorial holdout parents: {len(rows)}")

    # Collect all needed (parent, move) pairs from the 4 solver inputs
    comparisons = ["E_at_O0", "O_at_E0", "E_at_O1", "O_at_E1"]
    needed_pairs = set()
    total_slots = 0

    for comp in comparisons:
        comp_csv = solver_inputs_dir / f"{comp}.csv"
        with open(comp_csv, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            for r in reader:
                p, m1, m2 = r[0], int(r[1]), int(r[2])
                needed_pairs.add((p, m1))
                needed_pairs.add((p, m2))
                total_slots += 2

    print(f"Total parent-move evaluation slots: {total_slots}")
    print(f"Unique parent-move pairs to solve: {len(needed_pairs)} (dedup ratio: {len(needed_pairs)/total_slots:.3f})")

    # Format into deduplicated solver input
    # kyouen_solver_9_compare expects: canonical_parent,pair_top,other_top
    # We can pair up roots or evaluate them directly.
    # To use kyouen_solver_9_compare directly, we can group pairs by parent.
    parent_to_moves = {}
    for p, m in needed_pairs:
        parent_to_moves.setdefault(p, set()).add(m)

    print(f"Parents requiring child evaluations: {len(parent_to_moves)}")

    # Save manifest of deduplicated tasks
    out_manifest = Path("experiments/9x9-factorial-execution-base/dedup_manifest.txt")
    with open(out_manifest, "w", encoding="utf-8") as f:
        f.write(f"Total holdout parents: {len(rows)}\n")
        f.write(f"Total evaluation slots across 4 comparisons: {total_slots}\n")
        f.write(f"Unique (parent, move) pairs: {len(needed_pairs)}\n")
        f.write(f"Unique parents: {len(parent_to_moves)}\n")

    print(f"Deduplication manifest written to {out_manifest}")

if __name__ == "__main__":
    main()
