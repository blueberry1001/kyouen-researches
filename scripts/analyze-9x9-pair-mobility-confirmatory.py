#!/usr/bin/env python3
import argparse
import csv
import math
from collections import Counter, defaultdict


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("result_csv")
    return p.parse_args()


def binom_tail(k, n):
    return sum(math.comb(n, i) for i in range(k, n + 1)) / (2 ** n)


def main():
    args = parse_args()
    with open(args.result_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("empty result CSV")

    pair_col = "pair_child_outcome"
    other_col = "other_child_outcome"
    for c in (pair_col, other_col):
        if c not in rows[0]:
            raise SystemExit(f"missing column: {c}")

    totals = Counter()
    by_class = defaultdict(Counter)
    for r in rows:
        pair = r[pair_col]
        true = r[other_col]
        if pair == "LOSS" and true == "WIN": label = "pair_only"
        elif pair == "WIN" and true == "LOSS": label = "true_only"
        elif pair == "LOSS" and true == "LOSS": label = "both_loss"
        elif pair == "WIN" and true == "WIN": label = "both_win"
        else: raise SystemExit(f"unexpected outcomes: {pair}, {true}")
        totals[label] += 1
        cls = r.get("cause_class", "all")
        by_class[cls][label] += 1

    d = totals["pair_only"] + totals["true_only"]
    k = totals["true_only"]
    p_one = binom_tail(k, d) if d else 1.0
    p_two = min(1.0, 2 * min(binom_tail(k, d), binom_tail(d-k, d))) if d else 1.0

    print(f"n={len(rows)}")
    for label in ("pair_only", "true_only", "both_loss", "both_win"):
        print(f"{label}={totals[label]}")
    print(f"discordant={d}")
    print(f"true_only_fraction_among_discordant={k/d if d else float('nan'):.9f}")
    print(f"one_sided_exact_p_true_gt_pair={p_one:.12g}")
    print(f"two_sided_exact_p={p_two:.12g}")

    if any(cls != "all" for cls in by_class):
        print("by_class:")
        for cls in sorted(by_class):
            c = by_class[cls]
            print(f"  {cls}: pair_only={c['pair_only']} true_only={c['true_only']} both_loss={c['both_loss']} both_win={c['both_win']}")


if __name__ == "__main__":
    main()
