#!/usr/bin/env python3
"""B263 metric variants on n=4 to identify which definition matches 61.6%."""
import sys
sys.path.insert(0, "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts")
from kyouen_core import board_square

def u_gain(board, occ, p):
    L = set(board.legal_moves(occ))
    Lp = set(board.legal_moves(occ | (1 << p)))
    return len(L - Lp - {p})

def main():
    b = board_square(4)
    win = b.solve_outcomes()
    stats = {k: 0 for k in ["min>min", "max>max", "mean>mean", "min>max", "any_win_min>all_lose_min", "avg_all"]}
    cmp_n = 0
    for occ, w in win.items():
        L = b.legal_moves(occ)
        if not L:
            continue
        win_i, lose_i = [], []
        for p in L:
            c = occ | (1 << p)
            (win_i if win.get(c, 0) == 0 else lose_i).append(p)
        if not win_i or not lose_i:
            continue
        cmp_n += 1

        def child_min(p):
            sp = occ | (1 << p)
            Lsp = b.legal_moves(sp)
            return 0 if not Lsp else min(u_gain(b, sp, q) for q in Lsp)

        wm = [child_min(p) for p in win_i]
        lm = [child_min(p) for p in lose_i]
        if min(wm) > min(lm):
            stats["min>min"] += 1
        if max(wm) > max(lm):
            stats["max>max"] += 1
        if sum(wm)/len(wm) > sum(lm)/len(lm):
            stats["mean>mean"] += 1
        if min(wm) > max(lm):
            stats["min>max"] += 1
        if max(wm) > min(lm):
            stats["any_win_min>all_lose_min"] += 1
        # average over all moves of each class, compare
        stats["avg_all"] += 0

    print(f"cmp={cmp_n}")
    for k, v in stats.items():
        if k == "avg_all":
            continue
        print(f"  {k}: {v} ({100*v/cmp_n:.1f}%)")

if __name__ == "__main__":
    main()
