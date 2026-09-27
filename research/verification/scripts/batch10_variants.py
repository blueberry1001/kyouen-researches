"""Batch-10 priority 1: rule-variant winners on n<=5.

Variants (forbidden-quad filter):
  standard     : det4==0  (collinear OR concyclic)
  circles-only : det4==0 AND not collinear   (allow 4 collinear)
  lines-only   : collinear only              (allow 4 concyclic)

Computes empty-board g(0)/winner and first-move win sets.
Supports B221, B222, B223 (partial), B224, B226 (misère compare).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch10_core import (  # noqa: E402
    Game,
    classify_quads,
    first_move_labels,
    grundy_map,
    winner_from_grundy,
)

OUT = Path(__file__).resolve().parents[1] / "batch10_variants.json"


def misère_winner(game: Game, occ: int, memo_pn: dict) -> bool:
    """True if current player wins under misère (last move loses).
    Terminal (no legal move) => current player wins (opponent cannot move? no):
    normal: no move => lose. misère: the player who made the last move loses,
    so if current has no move, the previous player made the last move and
    therefore lost => current wins. So terminal is a WIN in misère.
    """
    if occ in memo_pn:
        return memo_pn[occ]
    moves = game.legal(occ)
    if not moves:
        memo_pn[occ] = True  # current wins (opponent just took last move)
        return True
    # if every child is a win for the next player (i.e. we eventually take last),
    # careful: player wins if there EXISTS a move leading to opponent losing.
    # opponent losing at child means opponent-to-move eventually loses misère.
    val = False
    for m in moves:
        child = occ | (1 << m)
        child_win_for_next = misère_winner(game, child, memo_pn)
        if not child_win_for_next:
            val = True
            break
    memo_pn[occ] = val
    return val


def run_board(n: int) -> dict:
    t0 = time.time()
    coll, circ = classify_quads(n)
    fams = {
        "standard": coll + circ,
        "circles_only": circ,
        "lines_only": coll,
    }
    row = {
        "n": n,
        "n_collinear": len(coll),
        "n_circles": len(circ),
        "variants": {},
    }
    for name, quads in fams.items():
        t1 = time.time()
        game = Game(n, quads)
        gm = grundy_map(game, 0)
        g0 = gm[0]
        winner = winner_from_grundy(g0)
        fm = first_move_labels(game, gm)
        win_pts = sorted(p for p, lab in fm.items() if lab == "Win")
        lose_pts = sorted(p for p, lab in fm.items() if lab == "Lose")
        # misère empty-board winner
        memo_mis = {}
        mis_first_wins = misère_winner(game, 0, memo_mis)
        row["variants"][name] = {
            "n_quads": len(quads),
            "g0": g0,
            "winner": winner,
            "n_positions": len(gm),
            "max_g": max(gm.values()),
            "winning_first_moves": win_pts,
            "losing_first_moves": lose_pts,
            "misere_first_wins": mis_first_wins,
            "misere_winner": "First" if mis_first_wins else "Second",
            "seconds": round(time.time() - t1, 2),
        }
        print(
            f"  n={n} {name:13s} quads={len(quads):5d} g0={g0} "
            f"winner={winner:6s} |W|={len(win_pts)} pos={len(gm)} "
            f"misere_first={mis_first_wins} ({time.time()-t1:.1f}s)",
            flush=True,
        )
    row["seconds"] = round(time.time() - t0, 2)
    return row


def main():
    ns = [int(a) for a in sys.argv[1:]] or [2, 3, 4, 5]
    results = []
    for n in ns:
        print(f"[batch10 variants] n={n}", flush=True)
        results.append(run_board(n))
    OUT.write_text(json.dumps(results, indent=2))
    print(f"wrote {OUT}")

    # summary comparison for B221/B222
    print("\n=== comparison ===")
    for r in results:
        n = r["n"]
        s = r["variants"]["standard"]
        c = r["variants"]["circles_only"]
        l = r["variants"]["lines_only"]
        print(
            f"n={n}: std={s['winner']}(g={s['g0']}) "
            f"circ={c['winner']}(g={c['g0']}) "
            f"lines={l['winner']}(g={l['g0']}) "
            f"Wstd==Wcirc:{s['winning_first_moves']==c['winning_first_moves']} "
            f"Wstd==Wlines:{s['winning_first_moves']==l['winning_first_moves']}"
        )


if __name__ == "__main__":
    main()
