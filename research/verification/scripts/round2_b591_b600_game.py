"""round2_b591_b600_game.py — B600 game-theoretic check on n=5 candidates.

For each structural candidate S (dmax=1, h=3, size=5):
  compute g(S), winning moves, and whether every winning move lies outside
  the shortest-modification candidate set.
Also test whether any win-preserving line can reach a max set.

Merges key "b600_game" into round2_b591.json.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b591.json"

N = 5
V = N * N
K = 9


def det4_rows(r0, r1, r2, r3):
    def det3(m):
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    m = [r1, r2, r3]
    total = 0
    for i in range(4):
        minor = [[m[a][b] for b in range(4) if b != i] for a in range(3)]
        total += (1 if i % 2 == 0 else -1) * r0[i] * det3(minor)
    return total


def pt_row(x, y):
    return [x * x + y * y, x, y, 1]


def forbidden_quads(n: int):
    pts = [(i % n, i // n) for i in range(n * n)]
    rows = [pt_row(x, y) for x, y in pts]
    quads = []
    for a, b, c, d in combinations(range(n * n), 4):
        if det4_rows(rows[a], rows[b], rows[c], rows[d]) == 0:
            quads.append((a, b, c, d))
    return quads


def build_inc(n, quads):
    v = n * n
    inc = [[] for _ in range(v)]
    for a, b, c, d in quads:
        for p, others in (
            (a, (1 << b) | (1 << c) | (1 << d)),
            (b, (1 << a) | (1 << c) | (1 << d)),
            (c, (1 << a) | (1 << b) | (1 << d)),
            (d, (1 << a) | (1 << b) | (1 << c)),
        ):
            inc[p].append(others)
    return inc


def addable(mask, inc):
    out = []
    for p in range(V):
        if (mask >> p) & 1:
            continue
        ok = True
        for others in inc[p]:
            if mask & others == others:
                ok = False
                break
        if ok:
            out.append(p)
    return out


def grundy(mask, inc, memo):
    if mask in memo:
        return memo[mask]
    moves = addable(mask, inc)
    if not moves:
        memo[mask] = 0
        return 0
    seen = set()
    for p in moves:
        seen.add(grundy(mask | (1 << p), inc, memo))
    g = 0
    while g in seen:
        g += 1
    memo[mask] = g
    return g


def enum_safe(n, k, inc):
    v = n * n
    out = []

    def dfs(start, chosen, count):
        if count == k:
            out.append(chosen)
            return
        if count + (v - start) < k:
            return
        for p in range(start, v):
            ok = True
            for others in inc[p]:
                if chosen & others == others:
                    ok = False
                    break
            if ok:
                dfs(p + 1, chosen | (1 << p), count + 1)

    dfs(0, 0, 0)
    return out


def main():
    t0 = time.time()
    quads = forbidden_quads(N)
    inc = build_inc(N, quads)
    max_sets = enum_safe(N, K, inc)
    max_set = set(max_sets)
    safe8 = enum_safe(N, 8, inc)
    size5 = enum_safe(N, 5, inc)
    print(f"max={len(max_sets)} safe8={len(safe8)} size5={len(size5)}", flush=True)

    contains = set()
    for t in safe8:
        pts = [i for i in range(V) if (t >> i) & 1]
        for comb in combinations(pts, 5):
            m = 0
            for p in comb:
                m |= 1 << p
            contains.add(m)

    # structural candidates
    struct = []
    for s in size5:
        if s not in contains:
            continue
        dmax = min((s & ~m).bit_count() for m in max_sets)
        if dmax != 1:
            continue
        cands = set()
        for m in max_sets:
            diff = s & ~m
            if diff.bit_count() == 1:
                addpts = m & ~s
                for p in range(V):
                    if (addpts >> p) & 1:
                        cands.add(p)
        struct.append((s, sorted(cands)))
    print(f"structural candidates: {len(struct)}", flush=True)

    # game check
    memo: dict[int, int] = {}
    # precompute grundy of all safe sets size>=5 (small)
    for k in range(8, 4, -1):
        for s in enum_safe(N, k, inc):
            grundy(s, inc, memo)
    print(f"grundy memo size: {len(memo)}", flush=True)

    n_npos = 0
    n_wins_outside = 0
    witnesses = []
    no_win_reaches_max_count = 0
    g_hist = Counter()
    for s, shortc in struct:
        g = grundy(s, inc, memo)
        g_hist[g] += 1
        if g == 0:
            continue  # P-position, not N
        n_npos += 1
        moves = addable(s, inc)
        win = [p for p in moves if grundy(s | (1 << p), inc, memo) == 0]
        if not win:
            continue
        shortc_set = set(shortc)
        # condition: ALL winning moves outside shortmod candidates
        if any(p in shortc_set for p in win):
            continue
        n_wins_outside += 1

        # condition: no win-preserving play reaches a max set
        # explore all replies from winning moves where opponent plays any move,
        # and we again play winning moves (g=0 for opponent)
        def reaches_max(state, player_is_us, depth=0):
            """Return True if some win-preserving line reaches a max set.
            player_is_us: True if it is our turn (we must move to keep win).
            """
            if state in max_set:
                return True
            moves = addable(state, inc)
            if not moves:
                return False
            if player_is_us:
                for p in moves:
                    child = state | (1 << p)
                    if grundy(child, inc, memo) == 0:
                        if reaches_max(child, False, depth + 1):
                            return True
                return False
            else:
                # opponent moves; win-preserving means we still win after any reply,
                # i.e. we consider all opponent moves (they try to not help us, but
                # the claim is that NO win-preserving line reaches max).
                for p in moves:
                    child = state | (1 << p)
                    if reaches_max(child, True, depth + 1):
                        return True
                return False

        # actually "勝敗維持対局" = play that maintains our win.
        # We only continue lines where we keep g(child)=0 after our moves.
        # Opponent can play anything; if ANY such line reaches max, condition fails.
        any_reach = False
        for p in win:
            child = s | (1 << p)
            # BFS/DFS over win-preserving lines
            stack = [(child, False)]  # (state, our_turn)
            seen = set()
            while stack:
                st, our_turn = stack.pop()
                if st in max_set:
                    any_reach = True
                    break
                if (st, our_turn) in seen:
                    continue
                seen.add((st, our_turn))
                mv = addable(st, inc)
                if our_turn:
                    for q in mv:
                        ch = st | (1 << q)
                        if grundy(ch, inc, memo) == 0:
                            stack.append((ch, False))
                else:
                    for q in mv:
                        stack.append((st | (1 << q), True))
            if any_reach:
                break
        if not any_reach:
            no_win_reaches_max_count += 1
            if len(witnesses) < 6:
                witnesses.append({
                    "mask": s,
                    "pts": [i for i in range(V) if (s >> i) & 1],
                    "coords": [[i % N, i // N] for i in range(V) if (s >> i) & 1],
                    "g": g,
                    "winning_moves": win,
                    "winning_coords": [[p % N, p // N] for p in win],
                    "shortmod_cands": shortc,
                    "shortmod_coords": [[p % N, p // N] for p in shortc],
                    "shortmod_addable": sorted(set(addable(s, inc)) & set(shortc)),
                    "dmax": 1,
                    "h": 3,
                })

    result = {
        "n": N,
        "structural_candidates": len(struct),
        "g_hist": {str(k): v for k, v in sorted(g_hist.items())},
        "N_position_count": n_npos,
        "all_wins_outside_shortmod": n_wins_outside,
        "no_win_reaches_max": no_win_reaches_max_count,
        "witnesses": witnesses,
        "note": (
            "勝敗維持 = 自分の手で常に g=0 に落とす線。"
            "相手は全応手を列挙。最大配置到達があれば条件5は偽。"
        ),
    }
    print(json.dumps({k: v for k, v in result.items() if k != "witnesses"}, indent=2), flush=True)
    print(f"witnesses: {len(witnesses)}", flush=True)

    if OUT.exists():
        data = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        data = {}
    data["b600_game"] = result
    data.setdefault("_meta", {})["b600_game_elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"merged b600_game into {OUT}", flush=True)


if __name__ == "__main__":
    main()
