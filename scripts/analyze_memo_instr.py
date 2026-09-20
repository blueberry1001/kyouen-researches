#!/usr/bin/env python3
"""Mechanism analysis for the below-root memo instrumentation cohort.

Reads results/10x10/memo-instrumentation/summary.csv + depth.csv and
reports the preregistered quantities:

  A. memo hit rates (entry, prefetch, WIN/LOSS split)
  B. recursion omission via cached children (overall + by depth)
  C. ordering effects (first-child / full-order changes, cached-LOSS first)
  D. direct WIN proof shortcut rate
  E. depth distribution of hits, omission, ordering changes, shortcuts

Prints tables to stdout and writes analysis.md next to the inputs.
Run only after verify_10x10_memo_instrumentation.py passes.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "results" / "10x10" / "memo-instrumentation"

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


def pct(a: int, b: int) -> str:
    return f"{100.0 * a / b:.2f}%" if b else "n/a"


def load(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict[str, int]]) -> dict[str, int]:
    tot = {c: 0 for c in COUNTERS}
    for r in rows:
        for c in COUNTERS:
            tot[c] += r[c]
    return tot


def report_block(title: str, tot: dict[str, int]) -> list[str]:
    e = tot["entry_lookup_calls"]
    ehit = tot["entry_hit_win"] + tot["entry_hit_loss"]
    p = tot["prefetch_calls"]
    phit = tot["prefetch_hit_win"] + tot["prefetch_hit_loss"]
    consumed = (tot["child_eval_from_cache_win"]
                + tot["child_eval_from_cache_loss"]
                + tot["child_eval_recursive"])
    cached = (tot["child_eval_from_cache_win"]
              + tot["child_eval_from_cache_loss"])
    nt = tot["visited_nonterminal_nodes"]
    sw = tot["solved_win_nodes"]
    return [
        f"### {title}",
        f"- entry: lookups={e} hits={ehit} "
        f"(WIN={tot['entry_hit_win']} LOSS={tot['entry_hit_loss']}) "
        f"rate={pct(ehit, e)}",
        f"- prefetch: calls={p} hits={phit} "
        f"(WIN={tot['prefetch_hit_win']} LOSS={tot['prefetch_hit_loss']}) "
        f"rate={pct(phit, p)}",
        f"- recursion omission: cached={cached} consumed={consumed} "
        f"omission={pct(cached, consumed)} "
        f"(fromWIN={tot['child_eval_from_cache_win']} "
        f"fromLOSS={tot['child_eval_from_cache_loss']} "
        f"recursive={tot['child_eval_recursive']})",
        f"- ordering: nonterm={nt} "
        f"first-change={tot['nodes_cache_changes_first_child']} "
        f"({pct(tot['nodes_cache_changes_first_child'], nt)}) "
        f"full-change={tot['nodes_cache_changes_full_order']} "
        f"({pct(tot['nodes_cache_changes_full_order'], nt)})",
        f"- cached-LOSS first: actual={tot['actual_first_cached_loss']} "
        f"({pct(tot['actual_first_cached_loss'], nt)}) "
        f"fallback={tot['fallback_first_cached_loss']} "
        f"({pct(tot['fallback_first_cached_loss'], nt)})",
        f"- WIN shortcut: {tot['win_return_from_cached_loss_child']}/{sw} "
        f"solved-WIN = {pct(tot['win_return_from_cached_loss_child'], sw)}",
    ]


def main() -> int:
    summary = load("summary.csv")
    depth = [{**r, **{c: int(r[c]) for c in COUNTERS}} for r in
             load("depth.csv")]
    lines = ["# Below-root memo instrumentation — mechanism analysis", ""]
    tot = aggregate(depth)
    lines += report_block(
        f"OVERALL ({len(summary)} parents, "
        f"visited={sum(int(r['exact_visited']) for r in summary)})", tot)
    lines += ["", "## Per-parent", "",
              "| parent | outcome | visited | entry hit | prefetch hit | "
              "omission | firstΔ | fullΔ | shortcut |",
              "|---|---|---|---|---|---|---|---|---|"]
    by_parent: dict[str, list[dict[str, int]]] = {}
    for r in depth:
        by_parent.setdefault(r["parent"], []).append(r)
    for s in summary:
        t = aggregate(by_parent[s["parent"]])
        consumed = (t["child_eval_from_cache_win"]
                    + t["child_eval_from_cache_loss"]
                    + t["child_eval_recursive"])
        cached = (t["child_eval_from_cache_win"]
                  + t["child_eval_from_cache_loss"])
        ehit = t["entry_hit_win"] + t["entry_hit_loss"]
        phit = t["prefetch_hit_win"] + t["prefetch_hit_loss"]
        lines.append(
            f"| {s['parent']} | {s['outcome']} | {s['exact_visited']} | "
            f"{pct(ehit, t['entry_lookup_calls'])} | "
            f"{pct(phit, t['prefetch_calls'])} | "
            f"{pct(cached, consumed)} | "
            f"{pct(t['nodes_cache_changes_first_child'], t['visited_nonterminal_nodes'])} | "
            f"{pct(t['nodes_cache_changes_full_order'], t['visited_nonterminal_nodes'])} | "
            f"{pct(t['win_return_from_cached_loss_child'], t['solved_win_nodes'])} |")
    lines += ["", "## Per-depth (all parents)", "",
              "| depth | miss | entry hit | prefetch hit | omission | "
              "firstΔ | fullΔ | shortcut |",
              "|---|---|---|---|---|---|---|---|"]
    by_depth: dict[int, list[dict[str, int]]] = {}
    for r in depth:
        by_depth.setdefault(int(r["depth"]), []).append(r)
    for d in sorted(by_depth):
        t = aggregate(by_depth[d])
        consumed = (t["child_eval_from_cache_win"]
                    + t["child_eval_from_cache_loss"]
                    + t["child_eval_recursive"])
        cached = (t["child_eval_from_cache_win"]
                  + t["child_eval_from_cache_loss"])
        ehit = t["entry_hit_win"] + t["entry_hit_loss"]
        phit = t["prefetch_hit_win"] + t["prefetch_hit_loss"]
        lines.append(
            f"| {d} | {t['entry_miss']} | "
            f"{pct(ehit, t['entry_lookup_calls'])} | "
            f"{pct(phit, t['prefetch_calls'])} | "
            f"{pct(cached, consumed)} | "
            f"{pct(t['nodes_cache_changes_first_child'], t['visited_nonterminal_nodes'])} | "
            f"{pct(t['nodes_cache_changes_full_order'], t['visited_nonterminal_nodes'])} | "
            f"{pct(t['win_return_from_cached_loss_child'], t['solved_win_nodes'])} |")
    lines += [""]
    for s in summary:
        lines += report_block(f"parent {s['parent']}",
                              aggregate(by_parent[s["parent"]])) + [""]
    text = "\n".join(lines)
    print(text)
    (OUT / "analysis.md").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
