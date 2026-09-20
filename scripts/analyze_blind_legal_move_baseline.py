#!/usr/bin/env python3
"""Analyze the solver's legal-move-count baseline on the frozen blind 3-stone set.

This script is deliberately independent of probe_memo because the historical
shared-solver memo feature is order-contaminated.  It reconstructs the exact
10x10 legal-move count for every child state from the game rule, then asks:

* how strongly LOSS children concentrate at small legal-move counts;
* how many solver-default adjacent/rank ties are actually legal-count ties;
* how much freedom remains for a secondary tie-break feature;
* what first-LOSS rank is guaranteed/possible if only legal_move_count is used.

The last item reports an interval per parent: optimistic ordering puts LOSS
first inside each equal-count tie group; pessimistic ordering puts LOSS last.
That separates the strength of the primary legal-count feature from accidental
ordering inside std::sort ties.
"""
from __future__ import annotations

import csv
import itertools
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANKINGS = ROOT / "results" / "10x10" / "blind-probe-rankings.csv"
N = 10
V = N * N


def det3(a00: int, a01: int, a02: int,
         a10: int, a11: int, a12: int,
         a20: int, a21: int, a22: int) -> int:
    return (
        a00 * (a11 * a22 - a12 * a21)
        - a01 * (a10 * a22 - a12 * a20)
        + a02 * (a10 * a21 - a11 * a20)
    )


def forbidden4(ids: tuple[int, int, int, int]) -> bool:
    m: list[list[int]] = []
    for v in ids:
        x, y = v % N, v // N
        m.append([x * x + y * y, x, y, 1])
    d = 0
    for col in range(4):
        minor = [[m[r][c] for c in range(4) if c != col] for r in range(1, 4)]
        md = det3(*minor[0], *minor[1], *minor[2])
        d += (1 if col % 2 == 0 else -1) * m[0][col] * md
    return d == 0


def build_completion() -> dict[tuple[int, int, int], set[int]]:
    completion: dict[tuple[int, int, int], set[int]] = defaultdict(set)
    for quad in itertools.combinations(range(V), 4):
        if not forbidden4(quad):
            continue
        for omitted in range(4):
            triple = tuple(quad[i] for i in range(4) if i != omitted)
            completion[triple].add(quad[omitted])
    return completion


def legal_move_count(state: tuple[int, ...], completion: dict[tuple[int, int, int], set[int]]) -> int:
    occupied = set(state)
    banned: set[int] = set()
    for triple in itertools.combinations(sorted(state), 3):
        banned.update(completion.get(triple, ()))
    return sum(v not in occupied and v not in banned for v in range(V))


def median(xs: list[int]) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    n = len(ys)
    return float(ys[n // 2]) if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2


def main() -> None:
    completion = build_completion()
    with RANKINGS.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if int(r["stones"]) == 3]

    by_parent: dict[str, list[dict[str, object]]] = defaultdict(list)
    loss_counts: list[int] = []
    win_counts: list[int] = []

    for r0 in rows:
        r: dict[str, object] = dict(r0)
        state = tuple(sorted(map(int, str(r["child_state"]).split("-"))))
        lc = legal_move_count(state, completion)
        r["legal_move_count"] = lc
        by_parent[str(r["parent"])].append(r)
        (loss_counts if r["outcome"] == "LOSS" else win_counts).append(lc)

    print("parent,n,losses,distinct_legal_counts,tied_rows,first_loss_solver,first_loss_legal_best,first_loss_legal_worst")
    legal_best_all: list[int] = []
    legal_worst_all: list[int] = []
    solver_all: list[int] = []

    for parent, rs in by_parent.items():
        rs.sort(key=lambda r: int(str(r["solver_default_rank"])))
        groups: dict[int, list[dict[str, object]]] = defaultdict(list)
        for r in rs:
            groups[int(r["legal_move_count"])].append(r)

        tied_rows = sum(len(g) for g in groups.values() if len(g) > 1)
        losses = [r for r in rs if r["outcome"] == "LOSS"]
        if not losses:
            continue

        solver_first = min(int(str(r["solver_default_rank"])) for r in losses)
        before = 0
        best = worst = None
        for lc in sorted(groups):
            g = groups[lc]
            gl = sum(r["outcome"] == "LOSS" for r in g)
            if gl:
                best = before + 1
                worst = before + (len(g) - gl) + 1
                break
            before += len(g)
        assert best is not None and worst is not None
        solver_all.append(solver_first)
        legal_best_all.append(best)
        legal_worst_all.append(worst)
        print(f"{parent},{len(rs)},{len(losses)},{len(groups)},{tied_rows},{solver_first},{best},{worst}")

    # Pairwise AUC-like probability: a random LOSS has fewer legal moves than a
    # random WIN; ties contribute 1/2.  This is descriptive, not an independent
    # hypothesis test because children within a parent are dependent.
    wins = 0.0
    pairs = 0
    for l in loss_counts:
        for w in win_counts:
            pairs += 1
            wins += 1.0 if l < w else 0.5 if l == w else 0.0
    auc = wins / pairs if pairs else float("nan")

    print()
    print(f"rows={len(rows)}")
    print(f"parents={len(by_parent)}")
    print(f"loss_children={len(loss_counts)}")
    print(f"win_children={len(win_counts)}")
    print(f"median_legal_moves_loss={median(loss_counts)}")
    print(f"median_legal_moves_win={median(win_counts)}")
    print(f"pairwise_P_loss_has_fewer_legal_moves={auc:.6f}")
    print(f"median_first_loss_solver_default={median(solver_all)}")
    print(f"median_first_loss_legal_count_best_ties={median(legal_best_all)}")
    print(f"median_first_loss_legal_count_worst_ties={median(legal_worst_all)}")
    print()
    print("Interpretation: if solver-default first LOSS lies inside the [best,worst] interval, its advantage is explainable by legal_move_count plus tie ordering. A secondary probe feature should therefore be tested only inside equal-count groups before it is allowed to reorder different legal-count groups.")


if __name__ == "__main__":
    main()
