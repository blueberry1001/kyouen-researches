#!/usr/bin/env python3
"""B123-B125 follow-up: aux points in the full safe-set complex on A∪B.

Move set: add or remove one point (size can change). Universe restricted to
A∪B unless aux points are explicitly added.

- B123: does A-B need >=2 points outside A∪B?
- B124: need aux, but no single aux is on every path (we check >=2 aux)
- B125: must we temporarily drop a point of A∩B?
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, deque
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "round5_b101_followup_b123.json"


def load_u64(path: Path) -> list[int]:
    raw = path.read_bytes()
    return list(struct.unpack(f"<{len(raw)//8}Q", raw))


def points_of(n: int, mask: int) -> list[tuple[int, int]]:
    return [(i % n, i // n) for i in range(n * n) if (mask >> i) & 1]


def connected_in_universe(board: Board, n: int, A: int, B: int, uni: int,
                          forbid_touch: int = 0) -> bool:
    """BFS from A to B using add/remove of one point, states ⊆ uni.
    If forbid_touch != 0, states must not contain any bit of forbid_touch
    (used to test whether we must leave A∩B)."""
    V = n * n
    if A & forbid_touch:
        # A itself contains a common point; we test paths that drop it later,
        # so start normally — the constraint is only for intermediate visits
        # of states that miss some common point. Handled by caller.
        pass
    visited = {A}
    q = deque([A])
    while q:
        m = q.popleft()
        if m == B:
            return True
        stones = [i for i in range(V) if (m >> i) & 1]
        for p in stones:
            nb = m ^ (1 << p)
            if nb in visited:
                continue
            if not board.is_safe(nb):
                continue
            if nb & ~uni:
                continue
            if forbid_touch and (nb & forbid_touch) != forbid_touch:
                continue
            visited.add(nb)
            q.append(nb)
        empties = [i for i in range(V) if not (m >> i & 1) and (uni >> i & 1)]
        for p in empties:
            nb = m | (1 << p)
            if nb in visited or not board.is_safe(nb):
                continue
            if forbid_touch and (nb & forbid_touch) != forbid_touch:
                continue
            visited.add(nb)
            q.append(nb)
    return False


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--max-pairs", type=int, default=800)
    args = ap.parse_args()
    n = args.n
    board = Board(square_points(n))
    maximal = load_u64(DATA / f"maximal_n{n}.bin")
    K = max(m.bit_count() for m in maximal)
    max_sets = [m for m in maximal if m.bit_count() == K]
    pairs_stats = Counter()
    examples = []
    b125_checked = 0
    b125_must_drop = 0
    b125_examples = []
    total = 0
    for a, b in combinations(range(len(max_sets)), 2):
        total += 1
        if total > args.max_pairs:
            break
        A, B = max_sets[a], max_sets[b]
        U = A | B
        if connected_in_universe(board, n, A, B, U):
            pairs_stats["aux0"] += 1
        else:
            pairs_stats["need_aux"] += 1
            outside = [i for i in range(n * n) if not (U >> i & 1)]
            found1 = False
            for aux in outside:
                if connected_in_universe(board, n, A, B, U | (1 << aux)):
                    found1 = True
                    break
            if found1:
                pairs_stats["aux1"] += 1
            else:
                pairs_stats["aux2plus"] += 1
                if len(examples) < 8:
                    examples.append({
                        "A": points_of(n, A),
                        "B": points_of(n, B),
                        "AandB": points_of(n, A & B),
                    })
        # B125: for pairs with common points, is every A-B path forced to
        # visit a state that misses some common point?
        I = A & B
        if I:
            b125_checked += 1
            # Path that keeps ALL common points at every step:
            if connected_in_universe(board, n, A, B, U, forbid_touch=I):
                pass  # can keep all common points
            else:
                # must drop some common point
                b125_must_drop += 1
                if len(b125_examples) < 5:
                    b125_examples.append({
                        "A": points_of(n, A),
                        "B": points_of(n, B),
                        "AandB": points_of(n, I),
                    })
        if total % 100 == 0:
            print(f"  ... {total} pairs, stats={dict(pairs_stats)}", flush=True)

    result = {
        "n": n,
        "K": K,
        "n_max_sets": len(max_sets),
        "n_pairs_examined": total - 1 if total > args.max_pairs else total,
        "pairs_stats": dict(pairs_stats),
        "examples_need_aux": examples,
        "b125_checked_with_common": b125_checked,
        "b125_must_drop_common": b125_must_drop,
        "b125_examples": b125_examples,
    }
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=1, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
