#!/usr/bin/env python3
"""n=4 B263 metric cross-check with the same definition as round5_b251a_weak b263n5."""
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
    cmp_n = hi_min = hi_q25 = 0
    sum_w = sum_l = 0
    nw = nl = 0
    byS = {}
    for occ, w in win.items():
        L = b.legal_moves(occ)
        if not L:
            continue
        win_i, lose_i = [], []
        for p in L:
            c = occ | (1 << p)
            if win.get(c, 0) == 0:
                win_i.append(p)
            else:
                lose_i.append(p)
        if not win_i or not lose_i:
            continue

        def child_min(p):
            sp = occ | (1 << p)
            Lsp = b.legal_moves(sp)
            if not Lsp:
                return 0
            return min(u_gain(b, sp, q) for q in Lsp)

        def child_q(p):
            sp = occ | (1 << p)
            Lsp = b.legal_moves(sp)
            if not Lsp:
                return 0
            v = sorted(u_gain(b, sp, q) for q in Lsp)
            return v[len(v) // 4]

        bwm = min(child_min(p) for p in win_i)
        blm = min(child_min(p) for p in lose_i)
        cmp_n += 1
        sum_w += bwm; nw += 1
        sum_l += blm; nl += 1
        if bwm > blm:
            hi_min += 1
        wq = min(child_q(p) for p in win_i)
        lq = min(child_q(p) for p in lose_i)
        if wq > lq:
            hi_q25 += 1
        nsz = bin(occ).count("1")
        byS.setdefault(nsz, [0, 0])
        byS[nsz][0] += 1
        if bwm > blm:
            byS[nsz][1] += 1

    print("n=4 B263 same-metric")
    print(f"cmp={cmp_n} hi_min={hi_min} ({100*hi_min/cmp_n:.1f}%) hi_q25={hi_q25} ({100*hi_q25/cmp_n:.1f}%)")
    print(f"avg_win_min={sum_w/nw:.4f} avg_lose_min={sum_l/nl:.4f}")
    for k in sorted(byS):
        c, h = byS[k]
        print(f"  |S|={k}: {h}/{c} = {100*h/c:.1f}%")

if __name__ == "__main__":
    main()
