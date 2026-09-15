#!/usr/bin/env python3
"""Exact finite-population descriptive table for O census comparisons."""
import csv
import hashlib
from pathlib import Path

COMPARISONS = {
    "O_at_E0": ("census_O_at_E0", "top_T", "top_TO"),
    "O_at_E1": ("census_O_at_E1", "top_TE", "top_raw"),
}


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize(row):
    out = dict(row)
    if "added_child_outcome" not in out and "other_child_outcome" in out:
        out["added_child_outcome"] = out["other_child_outcome"]
    return out


def main():
    holdout = read_csv("artifacts/9x9-factorial-holdout.csv")
    by_parent = {r["canonical_parent"]: r for r in holdout}
    rows_out = []
    for label, (member, left_col, right_col) in COMPARISONS.items():
        results = {
            r["canonical_parent"]: normalize(r)
            for r in read_csv(f"artifacts/solve/merged/{label}.csv")
        }
        expected = [p for p, r in by_parent.items() if truthy(r[member])]
        n = both_loss = both_win = left_only = right_only = 0
        for parent in expected:
            h = by_parent[parent]
            r = results[parent]
            assert int(r["pair_top"]) == int(h[left_col])
            assert int(r["added_top"]) == int(h[right_col])
            lo = r["pair_child_outcome"].strip().upper()
            ro = r["added_child_outcome"].strip().upper()
            n += 1
            if lo == "LOSS" and ro == "LOSS":
                both_loss += 1
            elif lo == "WIN" and ro == "WIN":
                both_win += 1
            elif lo == "LOSS" and ro == "WIN":
                left_only += 1
            else:
                right_only += 1
        baseline_loss_rate = (both_loss + left_only) / n
        added_loss_rate = (both_loss + right_only) / n
        rows_out.append(
            {
                "comparison": label,
                "population_type": "finite_eligible_census",
                "n": n,
                "both_loss": both_loss,
                "both_win": both_win,
                "baseline_only_loss": left_only,
                "component_added_only_loss": right_only,
                "discordant": left_only + right_only,
                "baseline_loss_rate": baseline_loss_rate,
                "added_loss_rate": added_loss_rate,
                "delta_loss_rate": added_loss_rate - baseline_loss_rate,
                "change_rate": (left_only + right_only) / n,
                "interpretation": (
                    "exact descriptive quantity on the pre-fixed "
                    "unobserved eligible finite population; not a sampling estimate"
                ),
            }
        )
    out = Path("artifacts/solve/o-census-finite-population.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    for r in rows_out:
        print(
            f"{r['comparison']}: n={r['n']} "
            f"base_loss={r['baseline_loss_rate']:.6f} "
            f"added_loss={r['added_loss_rate']:.6f} "
            f"delta={r['delta_loss_rate']:.6f} "
            f"change={r['change_rate']:.6f}"
        )
    print(f"sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
