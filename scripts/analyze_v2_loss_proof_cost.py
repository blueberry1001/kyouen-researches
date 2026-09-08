#!/usr/bin/env python3
"""Analyze proof cost *conditional on exact LOSS* in the frozen 10x10 V2 cohort.

No solver runs are performed. Inputs are the completed V2 child-level exact
outcomes, frozen fresh 10k probes, and completed parent benchmark raw rows.

The key separation is:
  1. LOSS-vs-WIN classification signal.
  2. Proof-cost signal *within exact LOSS children*.

The second question matters for a WIN parent because, once a LOSS child is
chosen, the parent solver still has to prove that LOSS. A ranking can therefore
be excellent at finding LOSS children and still be harmful if it prefers
expensive LOSS proofs.

All feature comparisons in this script are descriptive/exploratory. They do not
retroactively change any preregistered parent-benchmark endpoint.
"""
from __future__ import annotations

import csv
import itertools
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "results" / "10x10" / "clean-holdout-v2"
BENCH = ROOT / "results" / "10x10" / "parent-benchmark"

# Reuse exactly the determinant predicate used by the V2 task generator.
sys.path.insert(0, str(ROOT / "scripts"))
from generate_v2_holdout_children import forbidden  # noqa: E402


def norm_state(s: str) -> str:
    return "-".join(
        str(x)
        for x in sorted(
            int(v) for v in s.replace(",", "-").split("-") if v != ""
        )
    )


def pts_of(s: str) -> tuple[int, ...]:
    return tuple(int(v) for v in norm_state(s).split("-"))


def parent_pts(parent: str) -> set[int]:
    return set(pts_of(parent))


def added_move(parent: str, state: str) -> int:
    diff = set(pts_of(state)) - parent_pts(parent)
    if len(diff) != 1:
        raise ValueError(f"expected exactly one added move: parent={parent} state={state}")
    return next(iter(diff))


def d4_point(p: int, k: int) -> int:
    x, y = p % 10, p // 10
    nx = (x, 9 - x, x, 9 - x, y, 9 - y, y, 9 - y)
    ny = (y, y, 9 - y, 9 - y, x, x, 9 - x, 9 - x)
    return ny[k] * 10 + nx[k]


def bits_key(points: tuple[int, ...]) -> tuple[int, int]:
    lo = hi = 0
    for p in points:
        if p < 64:
            lo |= 1 << p
        else:
            hi |= 1 << (p - 64)
    return lo, hi


def canonical_bits(state: str) -> tuple[int, int]:
    pts = pts_of(state)
    keys = [
        bits_key(tuple(sorted(d4_point(p, k) for p in pts)))
        for k in range(8)
    ]
    # C++ Bits::operator< compares hi first, then lo.
    return min(keys, key=lambda z: (z[1], z[0]))


def legal_move_count(state: str) -> int:
    pts = pts_of(state)
    assert len(pts) == 4
    n = 0
    pset = set(pts)
    for v in range(100):
        if v in pset:
            continue
        if not any(
            forbidden(*trio, v)
            for trio in itertools.combinations(pts, 3)
        ):
            n += 1
    return n


def rankdata(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=xs.__getitem__)
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        # Average of 1-based ranks i+1 ... j.
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 2:
        return float("nan")
    mx, my = statistics.mean(x), statistics.mean(y)
    dx = [a - mx for a in x]
    dy = [b - my for b in y]
    den = math.sqrt(sum(a * a for a in dx) * sum(b * b for b in dy))
    return (
        sum(a * b for a, b in zip(dx, dy)) / den
        if den
        else float("nan")
    )


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(rankdata(x), rankdata(y))


def kendall_tau_b(x: list[float], y: list[float]) -> float:
    """O(n^2) Kendall tau-b; n is <100 per parent here."""
    if len(x) != len(y) or len(x) < 2:
        return float("nan")
    concordant = discordant = ties_x = ties_y = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx = (x[i] > x[j]) - (x[i] < x[j])
            dy = (y[i] > y[j]) - (y[i] < y[j])
            if dx == 0 and dy == 0:
                # Tied in both variables: excluded from both tie-only counts.
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx == dy:
                concordant += 1
            else:
                discordant += 1
    den = math.sqrt(
        (concordant + discordant + ties_x)
        * (concordant + discordant + ties_y)
    )
    return (concordant - discordant) / den if den else float("nan")


def auc_loss_low_score(rows: list[dict], score_key: str) -> float:
    """AUC where a *smaller* score is predicted to be more LOSS-like.

    Ties receive 0.5. This uses all exact children for a parent, unlike the
    conditional proof-cost correlations which use LOSS children only.
    """
    losses = [r for r in rows if r["outcome"] == "LOSS"]
    wins = [r for r in rows if r["outcome"] == "WIN"]
    if not losses or not wins:
        return float("nan")
    good = tied = 0
    for l in losses:
        for w in wins:
            if l[score_key] < w[score_key]:
                good += 1
            elif l[score_key] == w[score_key]:
                tied += 1
    return (good + 0.5 * tied) / (len(losses) * len(wins))


def proof_cost_rank(losses: list[dict], selected: dict) -> int:
    # Competition/min rank: 1 + number strictly cheaper.
    return 1 + sum(x["visited"] < selected["visited"] for x in losses)


def gmean(xs: list[float]) -> float:
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def median_finite(xs: list[float]) -> float:
    ys = [x for x in xs if not math.isnan(x)]
    return statistics.median(ys) if ys else float("nan")


def fmt(x: float) -> str:
    return "nan" if math.isnan(x) else f"{x:.4f}"


def main() -> None:
    exact: dict[tuple[str, str], dict] = {}
    with (V2 / "exact_outcomes.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r["parent"].strip()
            s = norm_state(r["state"])
            exact[(p, s)] = r

    probes: dict[tuple[str, str], dict] = {}
    with (V2 / "independent_probe_10000.csv").open(
        newline="", encoding="utf-8"
    ) as f:
        for r in csv.DictReader(f):
            p = r["parent"].strip()
            s = norm_state(r["state"])
            probes[(p, s)] = r

    bench: dict[tuple[str, str], dict] = {}
    with (BENCH / "parent_benchmark_raw.csv").open(
        newline="", encoding="utf-8"
    ) as f:
        for r in csv.DictReader(f):
            bench[(r["parent"], r["strategy"])] = r

    if set(exact) != set(probes):
        missing_probe = sorted(set(exact) - set(probes))
        missing_exact = sorted(set(probes) - set(exact))
        raise RuntimeError(
            "exact/probe task-set mismatch: "
            f"missing_probe={len(missing_probe)} missing_exact={len(missing_exact)}"
        )

    all_by_parent: dict[str, list[dict]] = defaultdict(list)
    loss_by_parent: dict[str, list[dict]] = defaultdict(list)

    for (p, s), er in exact.items():
        pr = probes[(p, s)]
        lo, hi = canonical_bits(s)
        rec = {
            "parent": p,
            "state": s,
            "move": added_move(p, s),
            "outcome": er["outcome"].strip().upper(),
            "visited": int(er["visited"]),
            "exact_seconds": float(er["seconds"]),
            "exact_memo": int(er["memo"]),
            "exact_maxdepth": int(er["maxdepth"]),
            "memo10k": int(pr["memo"]),
            "probe_seconds10k": float(pr["seconds"]),
            "probe_maxdepth10k": int(pr["maxdepth"]),
            "legal": legal_move_count(s),
            "lo": lo,
            "hi": hi,
        }
        all_by_parent[p].append(rec)
        if rec["outcome"] == "LOSS":
            loss_by_parent[p].append(rec)

    # Child-level LOSS table: useful for later exploratory feature work without
    # repeatedly joining the raw files.
    child_fields = [
        "parent",
        "state",
        "move",
        "visited",
        "exact_seconds",
        "exact_memo",
        "exact_maxdepth",
        "memo10k",
        "probe_seconds10k",
        "probe_maxdepth10k",
        "legal",
        "hi",
        "lo",
        "proof_cost_rank",
    ]
    child_out = BENCH / "loss_proof_cost_children.csv"
    with child_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=child_fields)
        w.writeheader()
        for p in sorted(loss_by_parent):
            losses = loss_by_parent[p]
            for x in sorted(losses, key=lambda r: (r["visited"], r["hi"], r["lo"])):
                row = {k: x[k] for k in child_fields if k != "proof_cost_rank"}
                row["proof_cost_rank"] = proof_cost_rank(losses, x)
                w.writerow(row)

    rows: list[dict] = []
    for p in sorted(loss_by_parent):
        losses = loss_by_parent[p]
        all_children = all_by_parent[p]
        costs = [x["visited"] for x in losses]
        legal = [x["legal"] for x in losses]
        memo = [x["memo10k"] for x in losses]
        pdepth = [x["probe_maxdepth10k"] for x in losses]
        psec = [x["probe_seconds10k"] for x in losses]
        moves = [x["move"] for x in losses]
        cheapest = min(costs)
        cheapest_items = [x for x in losses if x["visited"] == cheapest]

        # Exploratory conditional-LOSS rules. These pretend LOSS membership is
        # known and ask only which LOSS would be cheap to prove.
        legal_rule = min(losses, key=lambda x: (x["legal"], x["hi"], x["lo"]))
        legal_memo_rule = min(
            losses,
            key=lambda x: (x["legal"], x["memo10k"], x["hi"], x["lo"]),
        )
        memo_rule = min(losses, key=lambda x: (x["memo10k"], x["hi"], x["lo"]))

        legal_sorted = sorted(losses, key=lambda x: (x["legal"], x["hi"], x["lo"]))
        cheapest_ids = {(x["hi"], x["lo"]) for x in cheapest_items}

        selected: dict[str, dict | None] = {}
        for strategy in ("A", "B"):
            br = bench[(p, strategy)]
            key = (int(br["root_first_lo"]), int(br["root_first_hi"]))
            hit = [x for x in losses if (x["lo"], x["hi"]) == key]
            # If the first entered child is not LOSS, no selected-LOSS cost is
            # attributed here. In the both-entered=1 subgroup of a WIN parent,
            # this must be exactly one LOSS child.
            selected[strategy] = hit[0] if len(hit) == 1 else None

        rec: dict[str, object] = {
            "parent": p,
            "n_children": len(all_children),
            "n_loss": len(losses),
            "rho_legal_vs_loss_visited": spearman(legal, costs),
            "tau_legal_vs_loss_visited": kendall_tau_b(legal, costs),
            "rho_memo10k_vs_loss_visited": spearman(memo, costs),
            "tau_memo10k_vs_loss_visited": kendall_tau_b(memo, costs),
            "rho_probe_maxdepth10k_vs_loss_visited": spearman(pdepth, costs),
            "tau_probe_maxdepth10k_vs_loss_visited": kendall_tau_b(pdepth, costs),
            "rho_probe_seconds10k_vs_loss_visited": spearman(psec, costs),
            "tau_probe_seconds10k_vs_loss_visited": kendall_tau_b(psec, costs),
            "rho_move_vs_loss_visited": spearman(moves, costs),
            "tau_move_vs_loss_visited": kendall_tau_b(moves, costs),
            "auc_memo10k_loss_vs_win": auc_loss_low_score(all_children, "memo10k"),
            "auc_legal_loss_vs_win": auc_loss_low_score(all_children, "legal"),
            "cheapest_loss_visited": cheapest,
            "legal_rule_loss_visited": legal_rule["visited"],
            "legal_rule_cost_rank": proof_cost_rank(losses, legal_rule),
            "legal_rule_over_cheapest": legal_rule["visited"] / cheapest,
            "legal_memo_rule_loss_visited": legal_memo_rule["visited"],
            "legal_memo_rule_cost_rank": proof_cost_rank(losses, legal_memo_rule),
            "legal_memo_rule_over_cheapest": legal_memo_rule["visited"] / cheapest,
            "memo_rule_loss_visited": memo_rule["visited"],
            "memo_rule_cost_rank": proof_cost_rank(losses, memo_rule),
            "memo_rule_over_cheapest": memo_rule["visited"] / cheapest,
            "legal_top1_contains_cheapest": int(
                any((x["hi"], x["lo"]) in cheapest_ids for x in legal_sorted[:1])
            ),
            "legal_top3_contains_cheapest": int(
                any((x["hi"], x["lo"]) in cheapest_ids for x in legal_sorted[:3])
            ),
            "legal_top5_contains_cheapest": int(
                any((x["hi"], x["lo"]) in cheapest_ids for x in legal_sorted[:5])
            ),
            "min_legal_tie_size": sum(x["legal"] == legal_rule["legal"] for x in losses),
            "A_entered": int(bench[(p, "A")]["root_entered"]),
            "B_entered": int(bench[(p, "B")]["root_entered"]),
        }
        for strategy in ("A", "B"):
            x = selected[strategy]
            if x is None:
                rec[f"{strategy}_first_is_loss"] = 0
                rec[f"{strategy}_selected_loss_visited"] = ""
                rec[f"{strategy}_selected_loss_cost_rank"] = ""
                rec[f"{strategy}_selected_over_cheapest"] = ""
            else:
                rec[f"{strategy}_first_is_loss"] = 1
                rec[f"{strategy}_selected_loss_visited"] = x["visited"]
                rec[f"{strategy}_selected_loss_cost_rank"] = proof_cost_rank(losses, x)
                rec[f"{strategy}_selected_over_cheapest"] = x["visited"] / cheapest

        a = selected["A"]
        b = selected["B"]
        if a is not None and b is not None:
            rec["B_selected_over_A_selected"] = b["visited"] / a["visited"]
        else:
            rec["B_selected_over_A_selected"] = ""

        rows.append(rec)

    fields = list(rows[0].keys())
    out = BENCH / "loss_proof_cost_analysis.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print("== conditional LOSS proof-cost analysis ==")
    print(f"parents={len(rows)} exact_loss_children={sum(int(r['n_loss']) for r in rows)}")

    corr_names = (
        "rho_legal_vs_loss_visited",
        "tau_legal_vs_loss_visited",
        "rho_memo10k_vs_loss_visited",
        "tau_memo10k_vs_loss_visited",
        "rho_probe_maxdepth10k_vs_loss_visited",
        "tau_probe_maxdepth10k_vs_loss_visited",
        "rho_probe_seconds10k_vs_loss_visited",
        "tau_probe_seconds10k_vs_loss_visited",
        "rho_move_vs_loss_visited",
        "tau_move_vs_loss_visited",
    )
    for name in corr_names:
        print(f"median_{name}={fmt(median_finite([float(r[name]) for r in rows]))}")

    print(
        "median_auc_memo10k_loss_vs_win="
        f"{fmt(median_finite([float(r['auc_memo10k_loss_vs_win']) for r in rows]))}"
    )
    print(
        "median_auc_legal_loss_vs_win="
        f"{fmt(median_finite([float(r['auc_legal_loss_vs_win']) for r in rows]))}"
    )

    print("\n== exploratory conditional-LOSS cheap rules ==")
    for rule in ("legal_rule", "legal_memo_rule", "memo_rule"):
        ratios = [float(r[f"{rule}_over_cheapest"]) for r in rows]
        ranks = [int(r[f"{rule}_cost_rank"]) for r in rows]
        print(
            f"{rule}: median_over_cheapest={statistics.median(ratios):.4f} "
            f"gmean_over_cheapest={gmean(ratios):.4f} "
            f"median_cost_rank={statistics.median(ranks):.2f} "
            f"cheapest={sum(x == 1 for x in ranks)}/{len(ranks)}"
        )

    for k in (1, 3, 5):
        hits = sum(int(r[f"legal_top{k}_contains_cheapest"]) for r in rows)
        print(f"legal_top{k}_contains_cheapest={hits}/{len(rows)}")

    tied = [r for r in rows if int(r["min_legal_tie_size"]) > 1]
    if tied:
        base = [float(r["legal_rule_over_cheapest"]) for r in tied]
        memo_tie = [float(r["legal_memo_rule_over_cheapest"]) for r in tied]
        print(
            "min-legal ties: "
            f"parents={len(tied)} "
            f"memo_better={sum(m < b for m, b in zip(memo_tie, base))} "
            f"tie={sum(m == b for m, b in zip(memo_tie, base))} "
            f"memo_worse={sum(m > b for m, b in zip(memo_tie, base))}"
        )

    print("\n== benchmark-selected first LOSS ==")
    for strategy in ("A", "B"):
        ratios = [
            float(r[f"{strategy}_selected_over_cheapest"])
            for r in rows
            if r[f"{strategy}_selected_over_cheapest"] != ""
        ]
        ranks = [
            int(r[f"{strategy}_selected_loss_cost_rank"])
            for r in rows
            if r[f"{strategy}_selected_loss_cost_rank"] != ""
        ]
        print(f"{strategy}_first_is_loss={len(ratios)}/{len(rows)}")
        if ratios:
            print(
                f"{strategy}_selected_over_cheapest_median="
                f"{statistics.median(ratios):.4f}"
            )
            print(
                f"{strategy}_selected_over_cheapest_gmean="
                f"{gmean(ratios):.4f}"
            )
            print(
                f"{strategy}_selected_loss_cost_rank_median="
                f"{statistics.median(ranks):.2f}"
            )
            print(
                f"{strategy}_selected_cheapest_count="
                f"{sum(r == 1 for r in ranks)}/{len(ranks)}"
            )

    # Cleanest mechanism subgroup: each strategy entered exactly one root child.
    # Since every benchmark parent is WIN, that one entered child must be LOSS.
    # No earlier root child exists, so cross-root-child memo pollution cannot
    # explain A/B cost differences.
    s1 = [
        r
        for r in rows
        if int(r["A_entered"]) == 1 and int(r["B_entered"]) == 1
    ]
    print("\n== S1: A_entered=1 && B_entered=1 ==")
    print(f"parents={len(s1)}")
    if s1:
        if not all(
            int(r["A_first_is_loss"]) == 1 and int(r["B_first_is_loss"]) == 1
            for r in s1
        ):
            raise RuntimeError("S1 invariant failed: first entered child should be LOSS")

        a_oracle = [float(r["A_selected_over_cheapest"]) for r in s1]
        b_oracle = [float(r["B_selected_over_cheapest"]) for r in s1]
        b_over_a = [float(r["B_selected_over_A_selected"]) for r in s1]
        a_ranks = [int(r["A_selected_loss_cost_rank"]) for r in s1]
        b_ranks = [int(r["B_selected_loss_cost_rank"]) for r in s1]

        print(
            f"A_native_over_oracle_median={statistics.median(a_oracle):.4f} "
            f"gmean={gmean(a_oracle):.4f} "
            f"oracle_exact={sum(r == 1 for r in a_ranks)}/{len(s1)}"
        )
        print(
            f"B_10k_over_oracle_median={statistics.median(b_oracle):.4f} "
            f"gmean={gmean(b_oracle):.4f} "
            f"oracle_exact={sum(r == 1 for r in b_ranks)}/{len(s1)}"
        )
        print(
            f"B_over_A_selected_loss_median={statistics.median(b_over_a):.4f} "
            f"gmean={gmean(b_over_a):.4f} "
            f"B_cheaper={sum(x < 1 for x in b_over_a)}/{len(s1)} "
            f"B_worse={sum(x > 1 for x in b_over_a)}/{len(s1)}"
        )
        print("parent,A/oracle,B/oracle,B/A,A_rank,B_rank")
        for r in s1:
            print(
                f"{r['parent']},"
                f"{float(r['A_selected_over_cheapest']):.4f},"
                f"{float(r['B_selected_over_cheapest']):.4f},"
                f"{float(r['B_selected_over_A_selected']):.4f},"
                f"{int(r['A_selected_loss_cost_rank'])},"
                f"{int(r['B_selected_loss_cost_rank'])}"
            )

    print(f"\nwrote {out.relative_to(ROOT)}")
    print(f"wrote {child_out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
