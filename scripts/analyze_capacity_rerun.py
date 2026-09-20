#!/usr/bin/env python3
"""Primary + secondary analysis for the capacity-rescued rerun.

Reads results/10x10/cache-aware-below-root-capacity-rerun/summary_ab.csv,
depth_ab.csv, depth_visited.csv (after the verifier passes) and reports:

  primary: R_i = visited_blind / visited_aware per parent; median,
    geometric mean, arithmetic mean, aggregate visited ratio,
    improved/tie/worse counts, exact paired sign-test p-values.
  secondary: solver seconds / wall ratios, memo, maxdepth, recursive
    evaluations, cached omissions, cached-LOSS shortcuts, prefetch hit
    rates, put counts, depth-wise deltas, C1 and historical-C2
    descriptive comparison.
  capacity: per-depth memo usage vs the enlarged 90% ceilings
    (headroom check that motivated the rerun).

Preregistered success criterion: median R > 1 AND >= 7/12 parents R > 1.
No effect-size threshold.

Writes analysis.md, summary.json next to the inputs. Prints tables.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-below-root-capacity-rerun"
C1_OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-vs-blind"
C2_OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-below-root-confirmation-v2"

COUNTERS = ["entry_lookup_calls", "entry_hit_win", "entry_hit_loss",
            "entry_miss", "prefetch_calls", "prefetch_hit_win",
            "prefetch_hit_loss", "prefetch_miss", "put_win", "put_loss",
            "child_eval_from_cache_win", "child_eval_from_cache_loss",
            "child_eval_recursive", "visited_nonterminal_nodes",
            "nodes_with_any_prefetch_hit",
            "nodes_cache_changes_first_child",
            "nodes_cache_changes_full_order",
            "actual_first_cached_loss", "fallback_first_cached_loss",
            "solved_win_nodes", "win_return_from_cached_loss_child"]

# Enlarged physical powers -> 90% load entry ceilings per depth
# (two-table depths sum both sub-tables).
DEPTH_CEILING = {
    12: (2 ** 28 + 2 ** 25) * 90 // 100,
    13: (2 ** 28 + 2 ** 26) * 90 // 100,
    14: (2 ** 28 + 2 ** 25) * 90 // 100,
    15: (2 ** 27) * 90 // 100,
    16: (2 ** 24) * 90 // 100,
}


def load(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_dir(base: Path, name: str) -> list[dict[str, str]]:
    with (base / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sign_test_p(n: int, k: int) -> tuple[float, float]:
    """Exact two-sided doubling p and one-sided (A-better direction) p."""
    if n == 0:
        return float("nan"), float("nan")
    lo = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(lo + 1)) / 2 ** n
    return min(1.0, 2 * tail), sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def main() -> int:
    summary = load("summary_ab.csv")
    depth = load("depth_ab.csv")
    visited = load("depth_visited.csv")
    a = {r["parent"]: r for r in summary if r["condition"] == "cache-aware"}
    b = {r["parent"]: r for r in summary if r["condition"] == "cache-blind"}
    assert set(a) == set(b) and len(a) == 12, (len(a), len(b))

    parents = sorted(a)
    ratios: dict[str, float] = {}
    for p in parents:
        va, vb = int(a[p]["exact_visited"]), int(b[p]["exact_visited"])
        ratios[p] = vb / va if va else float("nan")
    rs = [ratios[p] for p in parents]
    med = statistics.median(rs)
    gmean = math.exp(sum(math.log(r) for r in rs) / len(rs))
    mean = sum(rs) / len(rs)
    tot_a = sum(int(a[p]["exact_visited"]) for p in parents)
    tot_b = sum(int(b[p]["exact_visited"]) for p in parents)
    agg = tot_b / tot_a
    imp = sum(1 for r in rs if r > 1)
    tie = sum(1 for r in rs if r == 1)
    worse = sum(1 for r in rs if r < 1)
    n_eff = imp + worse
    p_two, p_one = sign_test_p(n_eff, imp)
    success = med > 1 and imp >= 7

    sec_a = sum(float(a[p]["solver_seconds"]) for p in parents)
    sec_b = sum(float(b[p]["solver_seconds"]) for p in parents)
    wall_a = sum(float(a[p]["wall_seconds"]) for p in parents)
    wall_b = sum(float(b[p]["wall_seconds"]) for p in parents)
    memo_a = sum(int(a[p]["exact_memo"]) for p in parents)
    memo_b = sum(int(b[p]["exact_memo"]) for p in parents)

    ca = {c: 0 for c in COUNTERS}
    cb = {c: 0 for c in COUNTERS}
    for r in depth:
        t = ca if r["condition"] == "cache-aware" else cb
        for c in COUNTERS:
            t[c] += int(r[c])

    def mech(t: dict[str, int]) -> dict[str, str]:
        pre = t["prefetch_calls"]
        phit = t["prefetch_hit_win"] + t["prefetch_hit_loss"]
        cached = (t["child_eval_from_cache_win"]
                  + t["child_eval_from_cache_loss"])
        consumed = cached + t["child_eval_recursive"]
        return {
            "prefetch_hit_rate": f"{phit / pre:.6f}" if pre else "n/a",
            "omission_rate": f"{cached / consumed:.6f}" if consumed else "n/a",
            "shortcut_rate": (f"{t['win_return_from_cached_loss_child'] / t['solved_win_nodes']:.6f}"
                              if t["solved_win_nodes"] else "n/a"),
            "recursive": str(t["child_eval_recursive"]),
            "cached": str(cached),
            "puts": str(t["put_win"] + t["put_loss"]),
        }

    ma, mb = mech(ca), mech(cb)

    by_depth: dict[int, dict[str, dict[str, int]]] = {}
    for r in depth:
        d = int(r["depth"])
        slot = by_depth.setdefault(d, {"cache-aware": {c: 0 for c in COUNTERS},
                                       "cache-blind": {c: 0 for c in COUNTERS}})
        for c in COUNTERS:
            slot[r["condition"]][c] += int(r[c])
    vis: dict[tuple[str, str], dict[int, int]] = {}
    for r in visited:
        vis.setdefault((r["parent"], r["condition"]), {})[int(r["depth"])] = int(r["visited"])

    # Per-depth memo usage vs enlarged ceilings, from raw stdout rows.
    memo_used: dict[str, dict[int, int]] = {c: {} for c in ("cache-aware", "cache-blind")}
    memo_cap: dict[str, dict[int, int]] = {c: {} for c in ("cache-aware", "cache-blind")}
    for p in parents:
        for cond in ("cache-aware", "cache-blind"):
            raw = OUT / "raw" / (p.replace(",", "_") + "_" + cond.replace("-", "_")) / "stdout.txt"
            rows = list(csv.DictReader(raw.read_text(encoding="utf-8").splitlines()))
            row = rows[0]
            # stdout labels: d9..d21 map to table order d9,d10,d11,d11b,d12a,
            # d12b,d13a,d13b,d14a,d14b,d15,d16,d17 -> depth sums per label
            # pair: (12:d13+d14),(13:d15+d16),(14:d17+d18),(15:d19),(16:d20)
            u = {k: int(v) for k, v in row.items() if k.startswith("memo_used_")}
            c = {k: int(v) for k, v in row.items() if k.startswith("memo_capacity_")}
            for d in range(9, 22):
                memo_used[cond].setdefault(d, 0)
                memo_cap[cond].setdefault(d, 0)
            for d in range(9, 22):
                memo_used[cond][d] += u[f"memo_used_d{d}"]
                memo_cap[cond][d] += c[f"memo_capacity_d{d}"]
    depth_used = {  # aggregate per real depth
        12: lambda m: m[13] + m[14],
        13: lambda m: m[15] + m[16],
        14: lambda m: m[17] + m[18],
        15: lambda m: m[19],
        16: lambda m: m[20],
    }

    c1 = [r for r in load_dir(C1_OUT, "summary_ab.csv")
          if r["condition"] in ("cache-aware", "cache-blind")]
    c1a = {r["parent"]: int(r["exact_visited"]) for r in c1
           if r["condition"] == "cache-aware"}
    c1b = {r["parent"]: int(r["exact_visited"]) for r in c1
           if r["condition"] == "cache-blind"}
    c1r = [c1b[p] / c1a[p] for p in c1a]
    pooled = rs + c1r
    pmed = statistics.median(pooled)
    pgmean = math.exp(sum(math.log(r) for r in pooled) / len(pooled))
    c1imp = sum(1 for r in c1r if r > 1)

    c2 = [r for r in load_dir(C2_OUT, "summary_ab.csv")
          if r["condition"] in ("cache-aware", "cache-blind")]
    c2a = {r["parent"]: int(r["exact_visited"]) for r in c2
           if r["condition"] == "cache-aware"}
    c2b = {r["parent"]: int(r["exact_visited"]) for r in c2
           if r["condition"] == "cache-blind"}
    c2r = {p: c2b[p] / c2a[p] for p in c2a}
    overlap = [p for p in parents if p in c2r]

    lines = ["# Cache-aware below-root ordering capacity-rescued rerun — analysis",
             "",
             "## Primary: R = visited_blind / visited_aware",
             "",
             "| parent | visited A | visited B | R |",
             "|---|---|---|---|"]
    for p in parents:
        lines.append(f"| {p} | {a[p]['exact_visited']} | {b[p]['exact_visited']} "
                     f"| {ratios[p]:.6f} |")
    lines += ["",
              f"- median R = {med:.6f}",
              f"- geometric mean R = {gmean:.6f}",
              f"- arithmetic mean R = {mean:.6f}",
              f"- aggregate visited ratio = {agg:.6f} "
              f"({tot_b}/{tot_a})",
              f"- improved(A better)={imp} tie={tie} worse={worse}",
              f"- exact paired sign test: two-sided p={p_two:.6f}, "
              f"one-sided(A better) p={p_one:.6f} (n_eff={n_eff})",
              f"- prereg criterion (median>1 and >=7/12): "
              f"{'PASS' if success else 'FAIL'}",
              "",
              "## Secondary",
              f"- solver seconds: A={sec_a:.1f} B={sec_b:.1f} "
              f"ratio={sec_b / sec_a:.4f}" if sec_a else "- solver seconds n/a",
              f"- wall seconds: A={wall_a:.1f} B={wall_b:.1f} "
              f"ratio={wall_b / wall_a:.4f}" if wall_a else "- wall n/a",
              f"- final memo: A={memo_a} B={memo_b}",
              f"- A mechanism: prefetch_hit={ma['prefetch_hit_rate']} "
              f"omission={ma['omission_rate']} shortcut={ma['shortcut_rate']} "
              f"recursive={ma['recursive']} cached={ma['cached']} "
              f"puts={ma['puts']}",
              f"- B mechanism: prefetch_hit={mb['prefetch_hit_rate']} "
              f"omission={mb['omission_rate']} shortcut={mb['shortcut_rate']} "
              f"recursive={mb['recursive']} cached={mb['cached']} "
              f"puts={mb['puts']}",
              "",
              "## Depth deltas (B - A, all parents)",
              "",
              "| depth | visited Δ | recursive Δ | cached Δ | shortcut Δ |",
              "|---|---|---|---|---|"]
    for d in sorted(by_depth):
        va = sum(vis.get((p, "cache-aware"), {}).get(d, 0) for p in parents)
        vb = sum(vis.get((p, "cache-blind"), {}).get(d, 0) for p in parents)
        sa, sb = by_depth[d]["cache-aware"], by_depth[d]["cache-blind"]
        lines.append(
            f"| {d} | {vb - va} | "
            f"{sb['child_eval_recursive'] - sa['child_eval_recursive']} | "
            f"{(sb['child_eval_from_cache_win'] + sb['child_eval_from_cache_loss']) - (sa['child_eval_from_cache_win'] + sa['child_eval_from_cache_loss'])} | "
            f"{sb['win_return_from_cached_loss_child'] - sa['win_return_from_cached_loss_child']} |")
    lines += ["",
              "## Capacity headroom (enlarged 90% ceilings, worst of A/B)",
              "",
              "| depth | used (max cond) | ceiling | occupancy |",
              "|---|---|---|---|"]
    for d in (12, 13, 14, 15, 16):
        ua = depth_used[d](memo_used["cache-aware"])
        ub = depth_used[d](memo_used["cache-blind"])
        u = max(ua, ub)
        ceil = DEPTH_CEILING[d]
        lines.append(f"| {d} | {u} | {ceil} | {100 * u / ceil:.2f}% |")
    lines += ["",
              "## Pooled C1 + capacity rerun (reference, secondary)",
              f"- C1: 12/12 improved, median={statistics.median(c1r):.6f}",
              f"- capacity rerun: {imp}/12 improved, median={med:.6f}",
              f"- pooled n={len(pooled)}: median={pmed:.6f} gmean={pgmean:.6f}",
              f"- C1 range: {min(c1r):.4f}-{max(c1r):.4f}; "
              f"rerun range: {min(rs):.4f}-{max(rs):.4f}",
              "",
              "## Historical C2 (descriptive only; C2 endpoint INCOMPLETE)",
              f"- C2 completed-parent R overlap with this cohort: "
              f"{len(overlap)} parents"]
    for p in overlap:
        lines.append(f"  - {p}: C2 R={c2r[p]:.6f} rerun R={ratios[p]:.6f}")
    text = "\n".join(lines) + "\n"
    print(text)
    (OUT / "analysis.md").write_text(text, encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps({
        "cohort": "capacity rerun (extended24 ranks 13-24)",
        "per_parent_R": {p: ratios[p] for p in parents},
        "median_R": med, "gmean_R": gmean, "mean_R": mean,
        "aggregate_R": agg, "total_visited": {"A": tot_a, "B": tot_b},
        "improved": imp, "tie": tie, "worse": worse,
        "sign_test_two_sided_p": p_two, "sign_test_one_sided_p": p_one,
        "criterion_pass": success,
        "seconds": {"A": sec_a, "B": sec_b},
        "wall": {"A": wall_a, "B": wall_b},
        "memo": {"A": memo_a, "B": memo_b},
        "mechanism": {"A": ma, "B": mb},
        "pooled_reference": {"c1_median_R": statistics.median(c1r),
                             "rerun_median_R": med,
                             "pooled_median_R": pmed,
                             "pooled_gmean_R": pgmean,
                             "c1_improved": c1imp, "rerun_improved": imp},
        "historical_c2_descriptive": {p: c2r[p] for p in overlap},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
