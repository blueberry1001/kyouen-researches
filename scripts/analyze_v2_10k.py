#!/usr/bin/env python3
"""P4-P6: join frozen 10k probes with V2 exact outcomes; rank + cost analysis.

Frozen ranking (identical to V2 1M): corrected_key from
analyze_probe_holdout_preregistered (LOSS first / PROBE by memo ascending /
WIN last; 4th-move index tiebreak).

Outputs (all under results/10x10/clean-holdout-v2/):
  probe_10000_parent_results.csv / probe_10000_summary.json   (P4)
  p6_10k_first_loss_cost.csv / .json                          (P5)
  probe_10k_vs_1m.csv / .json                                 (P6)
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2 = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from analyze_probe_holdout_preregistered import (  # noqa: E402
    auc_from_order,
    corrected_key,
    first_loss_rank,
    norm_state,
    random_median,
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def spearman(a: list[float], b: list[float]) -> float | None:
    """Spearman rank correlation with average-tie ranks; None if degenerate."""
    n = len(a)
    if n < 2:
        return None

    def ranks(xs: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: xs[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((y - mb) ** 2 for y in rb)
    if va == 0 or vb == 0:
        return None
    return cov / math.sqrt(va * vb)


def main() -> None:
    tasks = load_csv(V2 / "exact_task_list.csv")
    probes10k = {(r["parent"].strip(), norm_state(r["state"])): r
                 for r in load_csv(V2 / "independent_probe_10000.csv")}
    probes1m = {(r["parent"].strip(), norm_state(r["state"])): r
                for r in load_csv(V2 / "independent_probe_1000000.csv")}
    exact = {(r["parent"].strip(), norm_state(r["state"])): r
             for r in load_csv(V2 / "exact_outcomes.csv")}
    assert len(probes10k) == 1136 == len(tasks) == len(exact) == len(probes1m)

    # File order per parent = frozen task-list order.
    file_order: dict[str, list[str]] = {}
    for t in tasks:
        file_order.setdefault(t["parent"].strip(), []).append(norm_state(t["state"]))

    parents = sorted(file_order)
    assert len(parents) == 12

    prev = {r["parent"].strip(): r for r in load_csv(V2 / "preregistered_parent_results.csv")}

    p4_rows, p5_rows, p6_rows = [], [], []
    aucs, ranks = [], []
    for p in parents:
        children = file_order[p]
        m = len(children)
        ex = {s: exact[(p, s)]["outcome"].strip().upper() for s in children}
        loss = sum(1 for s in children if ex[s] == "LOSS")
        p10 = {s: probes10k[(p, s)] for s in children}
        p1m = {s: probes1m[(p, s)] for s in children}

        # ---- P4: 10k ranking ----
        non_probe = sum(1 for s in children if p10[s]["probe_outcome"].strip().upper() != "PROBE")
        order10 = sorted(children, key=lambda s: corrected_key(p, s, p10[s]))
        order1m = sorted(children, key=lambda s: corrected_key(p, s, p1m[s]))
        rank10 = first_loss_rank(order10, ex)
        rank1m = int(prev[p]["first_loss_rank"])
        auc10 = auc_from_order(order10, ex)
        auc1m = float(prev[p]["auc"])
        if auc10 is not None:
            aucs.append(auc10)
        ranks.append(rank10)
        top1 = ex[order10[0]]
        top5 = sum(1 for s in order10[:5] if ex[s] == "LOSS")
        rho = spearman([int(p10[s]["memo"]) for s in children],
                       [int(p1m[s]["memo"]) for s in children])
        med = random_median(m, loss)
        p4_rows.append({
            "parent": p, "m": m, "loss": loss,
            "first_loss_rank_10k": rank10, "random_median": med,
            "normalized_rank_10k": round(rank10 / m, 6),
            "auc_10k": round(auc10, 6) if auc10 is not None else "",
            "top1_outcome_10k": top1, "top5_loss_10k": top5,
            "non_probe_rows_10k": non_probe,
            "first_loss_rank_1m": rank1m, "auc_1m": auc1m,
            "rank_diff_10k_minus_1m": rank10 - rank1m,
            "auc_diff_10k_minus_1m": round(auc10 - auc1m, 6) if auc10 is not None else "",
            "memo_order_spearman_10k_vs_1m": round(rho, 4) if rho is not None else "",
        })

        # ---- P5: total solver cost (solver-reported seconds only) ----
        probe_cost_10k = sum(float(p10[s]["seconds"]) for s in children)
        probe_cost_1m = sum(float(p1m[s]["seconds"]) for s in children)

        def exact_cost_to_first_loss(order: list[str]) -> tuple[int, float]:
            total = 0.0
            for i, s in enumerate(order, 1):
                total += float(exact[(p, s)]["seconds"])
                if ex[s] == "LOSS":
                    return i, total
            return m + 1, total

        pos_a, cost_a = exact_cost_to_first_loss(children)      # file order
        pos_10, cost_10 = exact_cost_to_first_loss(order10)     # 10k memo order
        pos_1m, cost_1m = exact_cost_to_first_loss(order1m)     # 1M memo order
        total_a = cost_a
        total_10 = probe_cost_10k + cost_10
        total_1m = probe_cost_1m + cost_1m
        p5_rows.append({
            "parent": p, "m": m,
            "pos_first_loss_file_order": pos_a,
            "exact_cost_file_order_s": round(cost_a, 2),
            "probe_all_cost_10k_s": round(probe_cost_10k, 2),
            "pos_first_loss_10k_order": pos_10,
            "exact_cost_10k_order_s": round(cost_10, 2),
            "total_cost_10k_s": round(total_10, 2),
            "ratio_10k_over_file": round(total_10 / cost_a, 4) if cost_a > 0 else "",
            "saving_10k_vs_file_s": round(cost_a - total_10, 2),
        })
        p6_rows.append({
            "parent": p,
            "probe_cost_10k_s": round(probe_cost_10k, 2),
            "probe_cost_1m_s": round(probe_cost_1m, 2),
            "probe_cost_ratio_10k_over_1m": round(probe_cost_10k / probe_cost_1m, 4),
            "total_cost_10k_s": round(total_10, 2),
            "total_cost_1m_s": round(total_1m, 2),
            "total_cost_ratio_10k_over_1m": round(total_10 / total_1m, 4),
            "rank_10k": rank10, "rank_1m": rank1m,
            "cheaper": "10k" if total_10 < total_1m else ("tie" if total_10 == total_1m else "1m"),
        })

    # ---- P4 globals ----
    rank_sorted = sorted(ranks)
    summary = {
        "parents": 12,
        "all_probe_unresolved": all(r["non_probe_rows_10k"] == 0 for r in p4_rows),
        "first_loss_ranks_10k_by_parent": {r["parent"]: r["first_loss_rank_10k"] for r in p4_rows},
        "rank_sum_10k": sum(ranks),
        "rank_median_10k": statistics.median(rank_sorted),
        "rank_max_10k": max(ranks),
        "rank_mean_10k": statistics.mean(ranks),
        "mean_auc_10k": statistics.mean(aucs),
        "median_auc_10k": statistics.median(aucs),
        "rank_sum_1m": 12,
        "mean_auc_1m": 0.7707509851330077,
        "median_auc_1m": 0.786732143208613,
    }

    # ---- P5 globals ----
    ratios5 = [r["ratio_10k_over_file"] for r in p5_rows if r["ratio_10k_over_file"] != ""]
    gmean = math.exp(statistics.mean(math.log(x) for x in ratios5))
    improved = sum(1 for x in ratios5 if x < 1.0)
    ties = sum(1 for x in ratios5 if x == 1.0)
    cost5 = {
        "parents": 12,
        "median_ratio_10k_over_file": statistics.median(ratios5),
        "geometric_mean_ratio_10k_over_file": round(gmean, 4),
        "mean_ratio_10k_over_file": statistics.mean(ratios5),
        "improved": improved, "tie": ties, "worse": 12 - improved - ties,
        "aggregate_file_order_s": round(sum(r["exact_cost_file_order_s"] for r in p5_rows), 2),
        "aggregate_total_10k_s": round(sum(r["total_cost_10k_s"] for r in p5_rows), 2),
        "aggregate_probe_10k_s": round(sum(r["probe_all_cost_10k_s"] for r in p5_rows), 2),
    }

    # ---- P6 globals ----
    cheaper10k = sum(1 for r in p6_rows if r["cheaper"] == "10k")
    cost6 = {
        "parents": 12,
        "parents_where_10k_total_cheaper_than_1m": cheaper10k,
        "parents_where_1m_total_cheaper": sum(1 for r in p6_rows if r["cheaper"] == "1m"),
        "mean_probe_cost_ratio_10k_over_1m": statistics.mean(r["probe_cost_ratio_10k_over_1m"] for r in p6_rows),
        "median_total_cost_ratio_10k_over_1m": statistics.median(r["total_cost_ratio_10k_over_1m"] for r in p6_rows),
        "aggregate_total_10k_s": cost5["aggregate_total_10k_s"],
        "aggregate_total_1m_s": round(sum(r["total_cost_1m_s"] for r in p6_rows), 2),
    }

    def write_csv(path: Path, rows: list[dict]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv(V2 / "probe_10000_parent_results.csv", p4_rows)
    (V2 / "probe_10000_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_csv(V2 / "p6_10k_first_loss_cost.csv", p5_rows)
    (V2 / "p6_10k_first_loss_cost.json").write_text(json.dumps(cost5, indent=2) + "\n")
    write_csv(V2 / "probe_10k_vs_1m.csv", p6_rows)
    (V2 / "probe_10k_vs_1m.json").write_text(json.dumps(cost6, indent=2) + "\n")

    print("== P4 summary =="); print(json.dumps(summary, indent=2))
    print("== P5 summary =="); print(json.dumps(cost5, indent=2))
    print("== P6 summary =="); print(json.dumps(cost6, indent=2))
    print("== per-parent P4 ==")
    for r in p4_rows:
        print(f"{r['parent']:<10} m={r['m']:<4} loss={r['loss']:<3} rank10k={r['first_loss_rank_10k']:<3} "
              f"auc10k={r['auc_10k']} top1={r['top1_outcome_10k']:<4} top5={r['top5_loss_10k']} "
              f"rank1m={r['first_loss_rank_1m']} rho={r['memo_order_spearman_10k_vs_1m']}")
    print("== per-parent P5 ==")
    for r in p5_rows:
        print(f"{r['parent']:<10} Af pos={r['pos_first_loss_file_order']:<3} cost={r['exact_cost_file_order_s']:<9} "
              f"B10k probe={r['probe_all_cost_10k_s']:<8} pos={r['pos_first_loss_10k_order']:<3} "
              f"total={r['total_cost_10k_s']:<9} ratio={r['ratio_10k_over_file']}")


if __name__ == "__main__":
    main()
