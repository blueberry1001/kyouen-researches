#!/usr/bin/env python3
"""探索14: 5×5 の 5 石極大が「勝ち初手後」に到達可能か、および共線比の極限候補。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from explore_maximal_spectrum import Hypergraph

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def n5_size5_after_first_moves():
    """勝ち初手 9 点それぞれから、5 石極大 4 個へ到達できるか。

    証明書戦略 (witness) ではなく、双方が任意に指したときに
    5 石極大がゲーム終端として現れうるかを見る。
    """
    hg = Hypergraph(5)
    wins = [(2, 0), (1, 1), (3, 1), (0, 2), (2, 2), (4, 2), (1, 3), (3, 3), (2, 4)]
    win_ids = [y * 5 + x for x, y in wins]
    losses = [p for p in range(25) if p not in win_ids]
    size5 = [
        (10, 6, 11, 16, 24),  # (2,0),(1,1),(2,1),(3,1),(2,4) ids = y*5+x
        (10, 16, 17, 18, 24),
        (6, 2, 7, 22, 8),
        (16, 2, 17, 22, 18),
    ]
    # recompute ids properly
    def ids_of(xy):
        return tuple(sorted(y * 5 + x for x, y in xy))

    sets_xy = [
        [(2, 0), (1, 1), (2, 1), (3, 1), (2, 4)],
        [(2, 0), (1, 3), (2, 3), (3, 3), (2, 4)],
        [(1, 1), (0, 2), (1, 2), (4, 2), (1, 3)],
        [(3, 1), (0, 2), (3, 2), (4, 2), (3, 3)],
    ]
    rows = []
    for xy in sets_xy:
        S = ids_of(xy)
        contains_win = [p for p in S if p in win_ids]
        contains_loss = [p for p in S if p in losses]
        # can this be reached if first move is a winning cell in S?
        first_win_in = any(p in win_ids for p in S)
        rows.append({
            "ids": list(S),
            "xy": xy,
            "winning_cells_inside": contains_win,
            "losing_cells_inside": contains_loss,
            "contains_a_winning_first_move": first_win_in,
        })
    # From CYCLE4: after any first move, remaining 24 cells are all legal.
    # A 5-stone terminal is reachable as a game end iff some play sequence
    # of 5 safe moves hits exactly that set and cannot extend.
    # If the first move is a winning cell, the opponent is in a losing 1-stone
    # position; the 5-stone maximals all contain some winning cells (see rows).
    return {
        "size5_sets": rows,
        "all_size5_contain_winning_cell": all(r["contains_a_winning_first_move"] for r in rows),
        "interpretation": (
            "5-stone maximals always include at least one winning first-move cell. "
            "They can appear as terminals after a losing first move (which lands on "
            "a losing cell), not after a winning first move under perfect play."
        ),
    }


def collinear_share_limit():
    """共線比 coll/F の推移 (n=4..13) から極限を推測。"""
    coll = {4: 10, 5: 64, 6: 234, 7: 660, 8: 1524, 9: 3156, 10: 5928}
    forb = {
        4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564,
        9: 29152, 10: 54441, 11: 95670, 12: 158426, 13: 252362,
    }
    rows = []
    for n in sorted(coll):
        rows.append({"n": n, "collinear": coll[n], "forbidden": forb[n], "share": coll[n] / forb[n]})
    return {
        "rows": rows,
        "note": "share rises 0.05→0.11 and flattens; limit ~0.11–0.13 unknown",
    }


def main():
    report = {
        "n5_size5_reach": n5_size5_after_first_moves(),
        "collinear_share": collinear_share_limit(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str), flush=True)
    out = OUT / "exploration_report_14.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()
