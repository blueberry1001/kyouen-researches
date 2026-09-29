#!/usr/bin/env python3
"""B032: search more small boards for disjoint shortest/longest first-move sets."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_rect, board_square

OUT = ROOT / "research" / "verification" / "round5_b020b_b032more.json"

def analyze(b):
    g = b.solve_outcomes()
    if g.get(0, 0) != 1:
        return {"board": b.name, "first_wins": False, "g_empty": g.get(0)}
    memo_T = {}
    def Tstar(occ):
        if occ in memo_T:
            return memo_T[occ]
        mv = b.legal_moves(occ)
        if not mv:
            memo_T[occ] = frozenset([occ.bit_count()])
            return memo_T[occ]
        is_n = g[occ] == 1
        acc = set()
        for u in mv:
            ch = occ | (1 << u)
            if is_n:
                if g.get(ch, 0) == 0:
                    acc |= Tstar(ch)
            else:
                acc |= Tstar(ch)
        memo_T[occ] = frozenset(acc)
        return memo_T[occ]
    win_moves = []
    for u in b.legal_moves(0):
        ch = 1 << u
        if g.get(ch, 0) == 0:
            t = Tstar(ch)
            win_moves.append((u, min(t), max(t), sorted(t)))
    if not win_moves:
        return {"board": b.name, "first_wins": True, "n_win_first": 0}
    mins = [m for _, m, _, _ in win_moves]
    maxs = [M for _, _, M, _ in win_moves]
    shortest = {u for u, m, M, _ in win_moves if m == min(mins)}
    longest = {u for u, m, M, _ in win_moves if M == max(maxs)}
    # also: "strict" shortest = only achieve min, "strict" longest = only achieve max
    strict_short = {u for u, m, M, _ in win_moves if m == min(mins) and M < max(maxs)}
    strict_long = {u for u, m, M, _ in win_moves if M == max(maxs) and m > min(mins)}
    return {
        "board": b.name, "first_wins": True,
        "n_win_first": len(win_moves),
        "min_t": min(mins), "max_t": max(maxs),
        "shortest": sorted(shortest), "longest": sorted(longest),
        "disjoint": len(shortest & longest) == 0,
        "strict_short": sorted(strict_short), "strict_long": sorted(strict_long),
        "strict_disjoint": len(strict_short & strict_long) == 0 and (strict_short or strict_long),
        "first_move_T": {str(u): sorted(t) for u, m, M, t in win_moves},
        "K": None,
    }

def main():
    boards = []
    for w, h in [(2,3),(2,4),(2,5),(2,6),(2,7),(2,8),(3,3),(3,4),(3,5),(3,6),(3,7),(4,4),(4,5),(4,6),(5,5),(5,6),(6,6),(1,5),(1,6),(1,7),(1,8)]:
        if w * h > 36:
            continue
        boards.append(board_rect(w, h))
    rows = []
    for b in boards:
        print(f"  {b.name} V={b.V}", flush=True)
        rows.append(analyze(b))
    OUT.write_text(json.dumps(rows, indent=2, default=str))
    # summary
    for r in rows:
        if r.get("first_wins"):
            flag = "DISJOINT" if r.get("disjoint") else ("strict?" if r.get("strict_disjoint") else "overlap")
            print(f"{r['board']}: wins={r.get('n_win_first')} min={r.get('min_t')} max={r.get('max_t')} {flag}")
            if r.get("strict_short") or r.get("strict_long"):
                print(f"   strict_short={r.get('strict_short')} strict_long={r.get('strict_long')}")
    print("wrote", OUT)

if __name__ == "__main__":
    main()
