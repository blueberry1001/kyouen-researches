#!/usr/bin/env python3
"""Primary + secondary analysis for cache-aware vs cache-blind benchmark.

Reads results/10x10/cache-aware-vs-blind/summary_ab.csv, depth_ab.csv,
depth_visited.csv (after the verifier passes) and reports:

  primary: R_i = visited_blind / visited_aware per parent; median,
    geometric mean, arithmetic mean, aggregate visited ratio,
    improved/tie/worse counts, exact paired sign-test p-values.
  secondary: solver seconds / wall ratios, memo, maxdepth, recursive
    evaluations, cached omissions, cached-LOSS shortcuts, prefetch hit
    rates, put counts.
  depth: per-depth visited/recursive/cached/shortcut deltas (B - A).

Preregistered success criterion: median R > 1 AND >= 7/12 parents R > 1.

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
OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-below-root-confirmation-v2"
C1_OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-vs-blind"

COUNTERS = ["entry_lookup_calls", "entry_hit_win", "entry_hit_loss",
            "entry_miss", "prefetch_calls", "prefetch_hit_win",
            "prefetch_hit_loss", "prefetch_miss", "put_win", "put_loss",
            "child_eval_from_cache_win", "child_eval_from_cache_loss",
            "child_eval_recursive", "visited_nonterminal_nodes",
            "nodes_with_any_prefetch_hit",
            "nodes_cache_changes_first_child",
            "nodes_cache_changes_full_order", "actual_first_cached_loss",
            "fallback_first_cached_loss", "solved_win_nodes",
            "win_return_from_cached_loss_child"]


def load(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_c1(name: str) -> list[dict[str, str]]:
    with (C1_OUT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pct(a: float, b: float) -> str:
    return f"{100.0 * a / b:.2f}%" if b else "n/a"


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

    c1 = [r for r in load_c1("summary_ab.csv")
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
    lines = ["# Cache-aware below-root ordering confirmation V2 — analysis",
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
              "## Pooled C1+C2 (reference, secondary)",
              f"- C1: 12/12 improved, median={statistics.median(c1r):.6f}",
              f"- C2: {imp}/12 improved, median={med:.6f}",
              f"- pooled n={len(pooled)}: median={pmed:.6f} gmean={pgmean:.6f}",
              f"- direction consistency: C1 all-A "
              f"{'and C2 ' + ('all-A' if imp == 12 else f'{imp}/12-A')}",
              f"- C1 range: {min(c1r):.4f}-{max(c1r):.4f}; "
              f"C2 range: {min(rs):.4f}-{max(rs):.4f}"]
    text = "\n".join(lines) + "\n"
    print(text)
    (OUT / "analysis.md").write_text(text, encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps({
        "cohort": "confirmation-V2 (extended24 ranks 13-24)",
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
                             "c2_median_R": med,
                             "pooled_median_R": pmed,
                             "pooled_gmean_R": pgmean,
                             "c1_improved": c1imp, "c2_improved": imp},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
