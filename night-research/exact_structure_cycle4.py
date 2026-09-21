#!/usr/bin/env python3
"""Cycle 4: exact safe-set outcomes, depth profiles, first-move mobility.

Deterministic integer-geometry kyouen analysis for small boards.
Point id = y * n + x. Forbidden 4-set iff det[x^2+y^2, x, y, 1] rows == 0.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "night-research"


def det4(p0, p1, p2, p3) -> int:
    """4x4 determinant of rows [x^2+y^2, x, y, 1]."""
    a0, a1, a2, a3 = p0, p1, p2, p3
    # Bareiss-free direct expansion via 3x3 minors on last row pattern is messy;
    # use explicit 4x4 expansion (Leibniz) — only 24 terms, exact ints.
    rows = [a0, a1, a2, a3]

    def minor3(r, cols):
        m = [[rows[i][c] for c in cols] for i in r]
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    det = 0
    for c0 in range(4):
        sign = 1 if c0 % 2 == 0 else -1
        cols = [c for c in range(4) if c != c0]
        det += sign * rows[0][c0] * minor3([1, 2, 3], cols)
    return det


def point_rows(n: int):
    rows = []
    for y in range(n):
        for x in range(n):
            rows.append((x * x + y * y, x, y, 1))
    return rows


def forbidden_quads(n: int):
    rows = point_rows(n)
    V = n * n
    quads = []
    for ids in combinations(range(V), 4):
        p = [rows[i] for i in ids]
        if det4(*p) == 0:
            quads.append(ids)
    return quads


def build_index(n: int, quads):
    """Return (quads_by_pt as bitmask list, list of quad bitmasks)."""
    V = n * n
    quads_by_pt = [[] for _ in range(V)]
    quad_masks = []
    for ids in quads:
        m = 0
        for i in ids:
            m |= 1 << i
        quad_masks.append(m)
        for i in ids:
            quads_by_pt[i].append(m)
    return quads_by_pt, quad_masks


def legal_moves(occ: int, V: int, quads_by_pt):
    moves = []
    empty = ((1 << V) - 1) ^ occ
    v = 0
    while empty:
        if empty & 1:
            mask = occ | (1 << v)
            ok = True
            for q in quads_by_pt[v]:
                if (q & mask) == q:
                    ok = False
                    break
            if ok:
                moves.append(v)
        empty >>= 1
        v += 1
    return moves


def solve_all_reachable(n: int, quads_by_pt):
    """Retrograde via DFS memo from empty. Returns outcomes dict and stats."""
    V = n * n
    memo: dict[int, int] = {}  # 1=WIN (player to move), 0=LOSS
    legal_cache: dict[int, list[int]] = {}
    visited_order = []

    def moves_of(occ: int) -> list[int]:
        mv = legal_cache.get(occ)
        if mv is None:
            mv = legal_moves(occ, V, quads_by_pt)
            legal_cache[occ] = mv
        return mv

    def outcome(occ: int) -> int:
        if occ in memo:
            return memo[occ]
        # detect recursion via explicit stack would be better; depth <= V
        mv = moves_of(occ)
        if not mv:
            memo[occ] = 0
            return 0
        # assume WIN until proven all children WIN
        memo[occ] = 1  # optimistic; children will overwrite if needed
        result = 0
        for u in mv:
            child = occ | (1 << u)
            if outcome(child) == 0:
                result = 1
                break
        memo[occ] = result
        return result

    t0 = time.time()
    empty = 0
    root = outcome(empty)
    # force full DAG evaluation: re-walk all memoized keys' children not computed
    # Actually outcome() only computes nodes on path to first WIN child + terminals.
    # For a complete depth profile we must evaluate EVERY reachable safe set.
    # Do a full explicit DFS that computes outcome for every node.
    memo.clear()
    legal_cache.clear()

    sys.setrecursionlimit(100000)

    def evaluate_complete(occ: int) -> int:
        if occ in memo:
            return memo[occ]
        mv = moves_of(occ)
        if not mv:
            memo[occ] = 0
            return 0
        any_loss_child = False
        for u in mv:
            child = occ | (1 << u)
            if evaluate_complete(child) == 0:
                any_loss_child = True
                # must still evaluate remaining children for complete profile
        # complete evaluation of all children
        # recompute properly
        results = []
        for u in mv:
            child = occ | (1 << u)
            results.append(evaluate_complete(child))
        memo[occ] = 1 if any(r == 0 for r in results) else 0
        return memo[occ]

    # The nested complete eval double-walks; simplify to single pass:
    memo.clear()

    def eval_full(occ: int) -> int:
        if occ in memo:
            return memo[occ]
        mv = moves_of(occ)
        if not mv:
            memo[occ] = 0
            return 0
        win = False
        for u in mv:
            if eval_full(occ | (1 << u)) == 0:
                win = True
                # continue to fill memo for siblings' subtrees
        memo[occ] = 1 if win else 0
        return memo[occ]

    # Fill entire reachable game DAG by iterating all recorded occ after DFS.
    # eval_full from empty visits all nodes reachable via ANY legal play path
    # because it recurses into every legal child.
    root = eval_full(0)
    elapsed = time.time() - t0

    # Depth profile
    by_k = defaultdict(lambda: {"safe": 0, "loss": 0, "win": 0})
    for occ, res in memo.items():
        k = occ.bit_count()
        by_k[k]["safe"] += 1
        if res == 0:
            by_k[k]["loss"] += 1
        else:
            by_k[k]["win"] += 1

    profile = []
    for k in sorted(by_k):
        safe = by_k[k]["safe"]
        loss = by_k[k]["loss"]
        profile.append(
            {
                "k": k,
                "safe": safe,
                "loss": loss,
                "win": safe - loss,
                "loss_rate": (loss / safe) if safe else None,
            }
        )

    return {
        "n": n,
        "empty_outcome": "WIN" if root == 1 else "LOSS",
        "empty_is_first_win": root == 1,
        "reachable_safe_sets": len(memo),
        "legal_cache_size": len(legal_cache),
        "elapsed_sec": elapsed,
        "depth_profile": profile,
        "peak_loss_rate": max(profile, key=lambda r: r["loss_rate"] or -1)
        if profile
        else None,
    }


def first_move_mobility(n: int, quads_by_pt, outcomes: dict[int, int]):
    V = n * n
    rows = []
    for first in range(V):
        occ = 1 << first
        # first move is always legal on empty board
        replies = legal_moves(occ, V, quads_by_pt)
        child_outcomes = []
        for r in replies:
            child = occ | (1 << r)
            child_outcomes.append(outcomes.get(child))
        # Position after first move: outcome from player-to-move (second player)
        pos_out = outcomes.get(occ)
        if pos_out == 0:
            result_first = "WIN"  # second player loses => first wins
        elif pos_out == 1:
            result_first = "LOSS"
        else:
            result_first = "UNKNOWN"
        # winning replies for second player (moves to LOSS for first = child outcome 0 means child is LOSS for player to move = first player after reply)
        # child outcome is for player to move after the reply (first player again).
        # Second player wants child_outcome == 0 (LOSS for first player).
        win_replies = [replies[i] for i, o in enumerate(child_outcomes) if o == 0]
        x, y = first % n, first // n
        rows.append(
            {
                "id": first,
                "x": x,
                "y": y,
                "result_for_first_player": result_first,
                "legal_reply_count": len(replies),
                "second_player_winning_reply_count": len(win_replies),
                "winning_reply_ids": win_replies[:8],
            }
        )
    return rows


def known_winner(n: int) -> str:
    # From repo certificates / README, including n=10 from 10x10 probes
    table = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F", 10: "S"}
    return table.get(n, "?")


def main(argv: list[str]) -> int:
    sizes = [int(a) for a in argv[1:]] or [2, 3, 4, 5]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # T1 hygiene: density table updated with Cycle 3 complete 9x9
    density = {
        "table": [
            {"n": 1, "winner": "F", "winning_first_moves": 1, "cells": 1, "density": 1.0, "status": "complete"},
            {"n": 2, "winner": "F", "winning_first_moves": 4, "cells": 4, "density": 1.0, "status": "complete"},
            {"n": 3, "winner": "F", "winning_first_moves": 9, "cells": 9, "density": 1.0, "status": "complete"},
            {"n": 4, "winner": "S", "winning_first_moves": 0, "cells": 16, "density": 0.0, "status": "complete"},
            {"n": 5, "winner": "F", "winning_first_moves": 9, "cells": 25, "density": 0.36, "status": "complete"},
            {"n": 6, "winner": "F", "winning_first_moves": 36, "cells": 36, "density": 1.0, "status": "complete"},
            {"n": 7, "winner": "S", "winning_first_moves": 0, "cells": 49, "density": 0.0, "status": "complete"},
            {"n": 8, "winner": "S", "winning_first_moves": 0, "cells": 64, "density": 0.0, "status": "complete"},
            {
                "n": 9,
                "winner": "F",
                "winning_first_moves": 81,
                "cells": 81,
                "density": 1.0,
                "status": "complete",
                "orbits_done": 15,
                "orbits_total": 15,
                "source": "night-research/first-moves-9x9.csv + CYCLE3_RESULTS.md",
            },
            {"n": 10, "winner": "S", "winning_first_moves": 0, "cells": 100, "density": 0.0, "status": "complete"},
        ],
        "h_dense": {
            "statement": "Among F-win boards n<=10, only n=5 has any losing first move.",
            "known_F_win": [1, 2, 3, 5, 6, 9],
            "status": "SUPPORTED on complete n<=10 data (exploratory; 9x9 completed after hypothesis)",
            "falsified": False,
        },
        "h_embed": {
            "statement": "Center-relative D4 orbit outcome transfers from 5x5 to 9x9.",
            "status": "REJECTED (3 MATCH / 3 FLIP on complete transfer table)",
        },
        "github_origin_note": {
            "local_head_example": "db50e40 Complete 9x9 first-move classification (replicate-8x8-o-stratum)",
            "origin_main_latest_known": "4152c1a Document factorial Holm reachability criterion",
            "origin_replicate_lag": "origin/replicate-8x8-o-stratum missing Cycle 3 commit",
        },
    }
    dens_path = OUT_DIR / "cycle4-density-table.json"
    dens_path.write_text(json.dumps(density, indent=2), encoding="utf-8")

    all_results = {"density": density, "boards": []}
    mobility_all = {}

    for n in sizes:
        print(f"=== n={n} forbidden quads ===", flush=True)
        t0 = time.time()
        quads = forbidden_quads(n)
        print(f"forbidden={len(quads)} in {time.time()-t0:.3f}s", flush=True)
        quads_by_pt, _ = build_index(n, quads)

        print(f"=== n={n} exact depth profile ===", flush=True)
        board = solve_all_reachable(n, quads_by_pt)
        board["forbidden_quadruples"] = len(quads)
        board["expected_winner"] = known_winner(n)
        board["winner_match"] = board["empty_is_first_win"] == (known_winner(n) == "F")
        print(
            f"empty={board['empty_outcome']} reachable={board['reachable_safe_sets']} "
            f"match={board['winner_match']} peak={board['peak_loss_rate']}",
            flush=True,
        )

        # rebuild outcomes memo by re-running solve internals — solve_all_reachable
        # doesn't return memo; recompute mobility via a second pass that returns memo.
        print(f"=== n={n} re-solve for mobility outcomes ===", flush=True)
        outcomes = outcomes_table(n, quads_by_pt)
        mob = first_move_mobility(n, quads_by_pt, outcomes)
        mobility_all[str(n)] = mob

        win_moves = sum(1 for r in mob if r["result_for_first_player"] == "WIN")
        board["mobility_winning_first_moves"] = win_moves
        board["mobility_density"] = win_moves / (n * n)
        # mobility mean replies for winning first moves (opponent forced into LOSS)
        win_rep = [r["legal_reply_count"] for r in mob if r["result_for_first_player"] == "WIN"]
        loss_rep = [r["legal_reply_count"] for r in mob if r["result_for_first_player"] == "LOSS"]
        board["mean_replies_if_first_win"] = (sum(win_rep) / len(win_rep)) if win_rep else None
        board["mean_replies_if_first_loss"] = (sum(loss_rep) / len(loss_rep)) if loss_rep else None

        all_results["boards"].append(board)
        (OUT_DIR / f"cycle4-exact-n{n}.json").write_text(
            json.dumps({"board": board, "first_move_mobility": mob}, indent=2),
            encoding="utf-8",
        )

    (OUT_DIR / "cycle4-exact-structure.json").write_text(
        json.dumps(all_results, indent=2), encoding="utf-8"
    )
    print(f"wrote {dens_path}", flush=True)
    print(f"wrote {OUT_DIR / 'cycle4-exact-structure.json'}", flush=True)
    return 0


def outcomes_table(n: int, quads_by_pt):
    V = n * n
    memo: dict[int, int] = {}
    sys.setrecursionlimit(100000)

    def moves_of(occ: int) -> list[int]:
        return legal_moves(occ, V, quads_by_pt)

    def eval_full(occ: int) -> int:
        if occ in memo:
            return memo[occ]
        mv = moves_of(occ)
        if not mv:
            memo[occ] = 0
            return 0
        win = False
        for u in mv:
            if eval_full(occ | (1 << u)) == 0:
                win = True
        memo[occ] = 1 if win else 0
        return memo[occ]

    eval_full(0)
    return memo


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
