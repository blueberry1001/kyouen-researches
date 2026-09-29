#!/usr/bin/env python3
"""B263: count ties and >= variants; also mean-of-u metric."""
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
    cmp_n = 0
    ge_min = gt_min = eq_min = 0
    ge_max = gt_max = eq_max = 0
    ge_mean = gt_mean = 0
    # opponent mean-u of child
    gt_meanu = ge_meanu = 0
    gt_minu_pair = 0
    pair_n = 0
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

        def child_meanu(p):
            sp = occ | (1 << p)
            Lsp = b.legal_moves(sp)
            if not Lsp:
                return 0.0
            return sum(u_gain(b, sp, q) for q in Lsp) / len(Lsp)

        wm = [child_min(p) for p in win_i]
        lm = [child_min(p) for p in lose_i]
        if min(wm) > min(lm):
            gt_min += 1
        if min(wm) == min(lm):
            eq_min += 1
        if min(wm) >= min(lm):
            ge_min += 1
        if max(wm) > max(lm):
            gt_max += 1
        if max(wm) == max(lm):
            eq_max += 1
        if max(wm) >= max(lm):
            ge_max += 1
        if sum(wm)/len(wm) > sum(lm)/len(lm):
            gt_mean += 1
        if sum(wm)/len(wm) >= sum(lm)/len(lm):
            ge_mean += 1

        wmu = [child_meanu(p) for p in win_i]
        lmu = [child_meanu(p) for p in lose_i]
        if sum(wmu)/len(wmu) > sum(lmu)/len(lmu):
            gt_meanu += 1
        if sum(wmu)/len(wmu) >= sum(lmu)/len(lmu):
            ge_meanu += 1

        # pairwise: fraction of (win,lose) pairs with wm>lm
        for a in wm:
            for c in lm:
                pair_n += 1
                if a > c:
                    gt_minu_pair += 1

    print(f"cmp={cmp_n}")
    print(f"min>min: {gt_min} ({100*gt_min/cmp_n:.1f}%)  min==min: {eq_min}  min>=min: {ge_min} ({100*ge_min/cmp_n:.1f}%)")
    print(f"max>max: {gt_max} ({100*gt_max/cmp_n:.1f}%)  max==max: {eq_max}  max>=max: {ge_max} ({100*ge_max/cmp_n:.1f}%)")
    print(f"mean>mean: {gt_mean} ({100*gt_mean/cmp_n:.1f}%)  mean>=mean: {ge_mean} ({100*ge_mean/cmp_n:.1f}%)")
    print(f"mean_u>mean_u: {gt_meanu} ({100*gt_meanu/cmp_n:.1f}%)  >=: {ge_meanu} ({100*ge_meanu/cmp_n:.1f}%)")
    print(f"pairwise wm>lm: {gt_minu_pair}/{pair_n} ({100*gt_minu_pair/pair_n:.1f}%)")

if __name__ == "__main__":
    main()
