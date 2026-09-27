#!/usr/bin/env python3
"""Round-2 follow-up: B325 (|L|-h on high ceiling) and B326 (nontrivial stabilizer)."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square
from residual_core import apply_perm_mask, d4_perms

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b321.json"


def analyze(n: int) -> dict:
    B = board_square(n)
    V = B.V
    reachable = {0}
    stack = [0]
    while stack:
        occ = stack.pop()
        for u in B.legal_moves(occ):
            nxt = occ | (1 << u)
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)
    g = {}
    Lc = {}

    def ev(occ: int) -> int:
        hit = g.get(occ)
        if hit is not None:
            return hit
        mv = B.legal_moves(occ)
        Lc[occ] = mv
        if not mv:
            g[occ] = 0
            return 0
        seen = {ev(occ | (1 << u)) for u in mv}
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        return x

    ev(0)
    for occ in reachable:
        if occ not in Lc:
            Lc[occ] = B.legal_moves(occ)

    by_k = defaultdict(list)
    for occ in reachable:
        by_k[occ.bit_count()].append(occ)
    kmax = max(by_k)
    Klocal = {}
    for k in range(kmax, -1, -1):
        for occ in by_k[k]:
            mv = Lc[occ]
            Klocal[occ] = k if not mv else max(Klocal[occ | (1 << u)] for u in mv)

    perms = d4_perms(n)

    # B325 by height
    by_h = defaultdict(list)  # h -> list of (L-h, occ, k, g, nL)
    for occ in reachable:
        k = occ.bit_count()
        h = Klocal[occ] - k
        if g[occ] != h:
            continue
        nL = len(Lc[occ])
        by_h[h].append((nL - h, occ, k, g[occ], nL))

    b325 = {}
    for h in sorted(by_h):
        arr = sorted(by_h[h])
        b325[str(h)] = {
            "count": len(arr),
            "min_L_minus_h": arr[0][0],
            "p10_L_minus_h": arr[max(0, len(arr) // 10)][0],
            "median_L_minus_h": arr[len(arr) // 2][0],
            "best_examples": [
                {"L_minus_h": t[0], "occ": t[1], "k": t[2], "g": t[3], "nL": t[4]}
                for t in arr[:3]
            ],
        }

    # B326 restricted to nontrivial stabilizer
    n_nt = 0
    n_ok = 0
    viol = []
    orbit_sizes_seen = defaultdict(int)
    for occ in reachable:
        k = occ.bit_count()
        h = Klocal[occ] - k
        if not (g[occ] == h and h >= 3 and g[occ] > 0):
            continue
        stabs = [p for p in perms if apply_perm_mask(occ, p) == occ]
        if len(stabs) <= 1:
            continue
        n_nt += 1
        # orbits under stabilizer
        seen = [False] * V
        orbits = {}
        for v in range(V):
            if seen[v]:
                continue
            orb = {v}
            for p in stabs:
                orb.add(p[v])
            fs = frozenset(orb)
            for w in orb:
                seen[w] = True
                orbits[w] = fs
        win = [u for u in Lc[occ] if g[occ | (1 << u)] == 0]
        ok = any(len(orbits[u]) <= 2 for u in win)
        for u in win:
            orbit_sizes_seen[len(orbits[u])] += 1
        if ok:
            n_ok += 1
        else:
            if len(viol) < 5:
                viol.append(
                    {
                        "occ": occ,
                        "k": k,
                        "g": g[occ],
                        "h": h,
                        "stab": len(stabs),
                        "win_orbit_sizes": sorted({len(orbits[u]) for u in win}),
                    }
                )

    return {
        "n": n,
        "B325_by_h": b325,
        "B326_nontrivial_stab": {
            "n_candidates": n_nt,
            "n_ok": n_ok,
            "n_violation": n_nt - n_ok,
            "violations": viol,
            "winning_move_orbit_size_hist": dict(orbit_sizes_seen),
        },
    }


def main() -> None:
    res = {}
    for n in (4, 5):
        print(f"===== followup n={n} =====", flush=True)
        res[str(n)] = analyze(n)
        print(json.dumps(res[str(n)], indent=2)[:2500], flush=True)

    path = ROOT / "research" / "verification" / "round2_b321.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["ceiling_followup"] = res
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
