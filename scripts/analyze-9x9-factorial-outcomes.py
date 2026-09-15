#!/usr/bin/env python3
import argparse
import csv
import math
from pathlib import Path

COMPARISONS = {
    "E_at_O0": ("sample_E_at_O0", "top_T", "top_TE"),
    "O_at_E0": ("census_O_at_E0", "top_T", "top_TO"),
    "E_at_O1": ("sample_E_at_O1", "top_TO", "top_raw"),
    "O_at_E1": ("census_O_at_E1", "top_TE", "top_raw"),
}


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def binom_two_sided_equal_tail(k, n):
    """Exact two-sided binomial p-value for p=0.5 using probability ordering.

    Under p=0.5 all outcomes with the same distance from n/2 have equal
    probability, so summing outcomes with probability <= P(X=k) is exact.
    """
    if n == 0:
        return 1.0
    pk_num = math.comb(n, k)
    total_num = sum(math.comb(n, j) for j in range(n + 1) if math.comb(n, j) <= pk_num)
    return min(1.0, total_num / (2 ** n))


def holm_adjust(raw):
    m = len(raw)
    order = sorted(range(m), key=lambda i: raw[i])
    adjusted = [1.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * raw[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def normalize_result_row(row):
    """Accept either analyzer-native added_* columns or solver other_* columns.

    kyouen_solver_9_compare emits other_top / other_child_outcome. Treat those
    as the component-added side without changing outcome meaning.
    """
    out = dict(row)
    if "added_child_outcome" not in out and "other_child_outcome" in out:
        out["added_child_outcome"] = out["other_child_outcome"]
    if "added_top" not in out and "other_top" in out:
        out["added_top"] = out["other_top"]
    return out


def parse_result_map(path):
    rows = [normalize_result_row(r) for r in read_csv(path)]
    if not rows:
        raise SystemExit(f"empty solver result: {path}")
    required = {
        "canonical_parent",
        "pair_top",
        "added_top",
        "pair_child_outcome",
        "added_child_outcome",
    }
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"solver result {path} missing columns: {sorted(missing)}")
    out = {}
    for r in rows:
        parent = r["canonical_parent"]
        if parent in out:
            raise SystemExit(f"duplicate canonical_parent in {path}: {parent}")
        out[parent] = r
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("holdout_csv")
    p.add_argument("summary_csv")
    for label in COMPARISONS:
        p.add_argument(f"--{label}", required=True, help=f"solver output for {label}")
    args = p.parse_args()

    holdout = read_csv(args.holdout_csv)
    if not holdout:
        raise SystemExit("empty holdout CSV")
    by_parent = {r["canonical_parent"]: r for r in holdout}
    if len(by_parent) != len(holdout):
        raise SystemExit("duplicate canonical_parent in holdout CSV")

    summaries = []
    raw_p = []

    for label, (member, left_col, right_col) in COMPARISONS.items():
        result_path = getattr(args, label)
        results = parse_result_map(result_path)
        expected = {p for p, r in by_parent.items() if truthy(r[member])}
        actual = set(results)
        if actual != expected:
            missing = sorted(expected - actual)[:5]
            extra = sorted(actual - expected)[:5]
            raise SystemExit(
                f"{label}: solver result parent set mismatch; "
                f"missing={len(expected-actual)} {missing}, "
                f"extra={len(actual-expected)} {extra}"
            )

        both_loss = both_win = left_only = right_only = 0
        for parent in sorted(expected):
            h = by_parent[parent]
            r = results[parent]
            expected_left = int(h[left_col])
            expected_right = int(h[right_col])
            if int(r["pair_top"]) != expected_left or int(r["added_top"]) != expected_right:
                raise SystemExit(
                    f"{label}: move mismatch for {parent}: "
                    f"expected {expected_left}/{expected_right}, got "
                    f"{r['pair_top']}/{r['added_top']}"
                )
            lo = r["pair_child_outcome"].strip().upper()
            ro = r["added_child_outcome"].strip().upper()
            if lo not in {"WIN", "LOSS"} or ro not in {"WIN", "LOSS"}:
                raise SystemExit(f"{label}: bad outcome for {parent}: {lo}/{ro}")
            if lo == "LOSS" and ro == "LOSS":
                both_loss += 1
            elif lo == "WIN" and ro == "WIN":
                both_win += 1
            elif lo == "LOSS" and ro == "WIN":
                left_only += 1
            else:
                right_only += 1

        discordant = left_only + right_only
        n = len(expected)
        p_raw = binom_two_sided_equal_tail(right_only, discordant)
        raw_p.append(p_raw)
        baseline_loss_rate = (both_loss + left_only) / n if n else ""
        added_loss_rate = (both_loss + right_only) / n if n else ""
        if n:
            delta_loss_rate = added_loss_rate - baseline_loss_rate
            change_rate = discordant / n
        else:
            delta_loss_rate = ""
            change_rate = ""
        summaries.append({
            "comparison": label,
            "n": n,
            "both_loss": both_loss,
            "both_win": both_win,
            "baseline_only_loss": left_only,
            "component_added_only_loss": right_only,
            "discordant": discordant,
            "component_added_fraction_discordant": (
                right_only / discordant if discordant else ""
            ),
            "exact_two_sided_p": p_raw,
            "baseline_loss_rate": baseline_loss_rate,
            "added_loss_rate": added_loss_rate,
            "delta_loss_rate": delta_loss_rate,
            "change_rate": change_rate,
        })

    adjusted = holm_adjust(raw_p)
    for row, p_adj in zip(summaries, adjusted):
        row["holm_adjusted_p"] = p_adj
        row["reject_fwer_0.05"] = int(p_adj < 0.05)
        if row["discordant"]:
            a = row["component_added_only_loss"]
            b = row["baseline_only_loss"]
            row["direction"] = "added_better" if a > b else ("baseline_better" if a < b else "tie")
        else:
            row["direction"] = "no_discordance"

    fields = [
        "comparison", "n", "both_loss", "both_win",
        "baseline_only_loss", "component_added_only_loss", "discordant",
        "component_added_fraction_discordant", "exact_two_sided_p",
        "holm_adjusted_p", "reject_fwer_0.05", "direction",
        "baseline_loss_rate", "added_loss_rate", "delta_loss_rate", "change_rate",
    ]
    with open(args.summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summaries)

    print("familywise_method=Holm exact two-sided binomial, alpha=0.05")
    for r in summaries:
        print(
            f"{r['comparison']}: n={r['n']} discordant={r['discordant']} "
            f"baseline_only={r['baseline_only_loss']} "
            f"added_only={r['component_added_only_loss']} "
            f"p={r['exact_two_sided_p']:.8g} "
            f"holm={r['holm_adjusted_p']:.8g} "
            f"direction={r['direction']} "
            f"base_loss={r['baseline_loss_rate']} "
            f"added_loss={r['added_loss_rate']} "
            f"delta_loss={r['delta_loss_rate']} "
            f"change={r['change_rate']}"
        )
    print(f"summary={Path(args.summary_csv)}")


if __name__ == "__main__":
    main()
