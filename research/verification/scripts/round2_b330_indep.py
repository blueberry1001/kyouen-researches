#!/usr/bin/env python3
"""Independent checks: B342 counterexample, B345 clique counterexample,
B333 WFT gap histogram, B330 same-(h,mu) pairs with far g.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b321.json"


def bits(mask: int) -> list[int]:
    out = []
    while mask:
        b = mask & -mask
        out.append(b.bit_length() - 1)
        mask ^= b
    return out


def occ_str(occ: int, n: int) -> str:
    return "{" + ",".join(f"({p % n},{p // n})" for p in bits(occ)) + "}"


def residual_game(Lmask: int, residuals: list[int], drop: set[int] | None = None):
    """Return (g0, win_moves_ids_on_board, g_map_abs) for residual game."""
    pts = bits(Lmask)
    idx = {p: i for i, p in enumerate(pts)}
    m = len(pts)
    rs_abs = []
    for i, r in enumerate(residuals):
        if drop and i in drop:
            continue
        rm = 0
        for p in bits(r):
            rm |= 1 << idx[p]
        if rm:
            rs_abs.append(rm)

    def legal(occ: int) -> list[int]:
        moves = []
        for i in range(m):
            if (occ >> i) & 1:
                continue
            nxt = occ | (1 << i)
            if any((nxt & r) == r for r in rs_abs):
                continue
            moves.append(i)
        return moves

    g = {}

    def ev(occ: int) -> int:
        hit = g.get(occ)
        if hit is not None:
            return hit
        mv = legal(occ)
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
    win = [pts[u] for u in legal(0) if g.get(1 << u) == 0]
    return g[0], win, g, legal, pts


def check_b342_b345() -> dict:
    """Recompute the specific n=4 occ=5 forest case and n=5 triangle case."""
    import pickle

    cache = pickle.loads((ROOT / "research" / "verification" / "batch03_cache.pkl").read_bytes())
    out = {}

    # --- B342: n=4, occ=5 ---
    recs4 = {r["occ"]: r for r in cache[4]["recs"]}
    r = recs4[5]
    R = r["R"]
    Lmask = r["L"]
    threes = [i for i, e in enumerate(R) if e.bit_count() == 3]
    print("B342 target: occ=5 n=4", "nL", Lmask.bit_count(), "n3", len(threes), "cache_g", r["g"])
    g_full, win_full, _, _, pts = residual_game(Lmask, R)
    print("  recomputed g_full", g_full, "win", win_full)
    best = None
    for ti in threes:
        g_m, win_m, _, _, _ = residual_game(Lmask, R, drop={ti})
        diff = abs(g_full - g_m)
        if best is None or diff > best[0]:
            best = (diff, ti, g_m, win_m, list(R[ti]) if False else bits(R[ti]))
    print("  best single-drop", best)
    # forest check
    idx = {p: i for i, p in enumerate(pts)}
    edges = []
    for e in R:
        if e.bit_count() == 2:
            b = bits(e)
            edges.append((idx[b[0]], idx[b[1]]))
    parent = list(range(Lmask.bit_count()))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    is_forest = True
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            is_forest = False
            break
        parent[ra] = rb
    print("  P edges", edges, "is_forest", is_forest, "nvert", Lmask.bit_count())
    out["B342_n4_occ5"] = {
        "g_full": g_full,
        "cache_g": r["g"],
        "best_diff": best[0],
        "dropped_residual_points": best[4],
        "g_minus": best[2],
        "is_forest": is_forest,
        "edges": edges,
        "n3": len(threes),
        "occ_str": occ_str(5, 4),
    }

    # --- B345: n=5 occ=391 (triangle P) ---
    recs5 = {r["occ"]: r for r in cache[5]["recs"]}
    r = recs5[391]
    R = r["R"]
    Lmask = r["L"]
    pts = bits(Lmask)
    idx = {p: i for i, p in enumerate(pts)}
    edges = []
    for e in R:
        if e.bit_count() == 2:
            b = bits(e)
            edges.append((idx[b[0]], idx[b[1]]))
    g_full, win_full, _, _, _ = residual_game(Lmask, R)
    # drop all 3+ residuals
    drop = {i for i, e in enumerate(R) if e.bit_count() >= 3}
    g2, win2, _, _, _ = residual_game(Lmask, R, drop=drop)
    print("B345 target: occ=391 n=5", "nL", Lmask.bit_count(), "g_full", g_full, "g_2pt", g2)
    print("  edges", edges, "drop_count", len(drop), "cache_g", r["g"])
    out["B345_n5_occ391"] = {
        "g_full": g_full,
        "g_2pt": g2,
        "cache_g": r["g"],
        "edges": edges,
        "n_drop_3plus": len(drop),
        "win_full": win_full,
        "win_2pt": win2,
        "occ_str": occ_str(391, 5),
    }
    return out


def b333_gap_hist() -> dict:
    """WFT gap structure on n=4,5."""
    res = {}
    for n in (4, 5):
        B = board_square(n)
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
        wft = {}

        def ev_w(occ: int) -> frozenset[int]:
            hit = wft.get(occ)
            if hit is not None:
                return hit
            mv = Lc[occ]
            if not mv:
                wft[occ] = frozenset({occ.bit_count()})
                return wft[occ]
            if g[occ] == 0:
                acc = None
                for u in mv:
                    s = ev_w(occ | (1 << u))
                    acc = s if acc is None else (acc & s)
                    if not acc:
                        break
                wft[occ] = frozenset(acc or set())
            else:
                acc_set: set[int] = set()
                for u in mv:
                    ch = occ | (1 << u)
                    if g[ch] == 0:
                        acc_set |= ev_w(ch)
                wft[occ] = frozenset(acc_set)
            return wft[occ]

        for occ in reachable:
            ev_w(occ)
        gap_hist = defaultdict(int)
        width_hist = defaultdict(int)
        n_multi = 0
        max_gap = 0
        for occ in reachable:
            ws = sorted(wft[occ])
            if len(ws) < 2:
                continue
            n_multi += 1
            width_hist[len(ws)] += 1
            gaps = [ws[i + 1] - ws[i] for i in range(len(ws) - 1)]
            for gp in gaps:
                gap_hist[gp] += 1
                if gp > max_gap:
                    max_gap = gp
        res[str(n)] = {
            "n_multi": n_multi,
            "width_hist": dict(width_hist),
            "gap_hist": dict(gap_hist),
            "max_gap": max_gap,
            "antecedent_gap_ge4": sum(v for k, v in gap_hist.items() if k >= 4),
        }
        print("B333 gaps n", n, res[str(n)])
    return res


def b330_pairs() -> dict:
    """Same (h, mu) with far g on n=4,5. mu = min remaining moves = min term size - k."""
    out = {}
    for n in (4, 5):
        B = board_square(n)
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
        minT = {}
        for k in range(kmax, -1, -1):
            for occ in by_k[k]:
                mv = Lc[occ]
                if not mv:
                    Klocal[occ] = k
                    minT[occ] = k
                else:
                    Klocal[occ] = max(Klocal[occ | (1 << u)] for u in mv)
                    minT[occ] = min(minT[occ | (1 << u)] for u in mv)
        buckets = defaultdict(list)
        for occ in reachable:
            k = occ.bit_count()
            h = Klocal[occ] - k
            mu = minT[occ] - k
            buckets[(h, mu)].append((g[occ], occ, k))
        best = (0, None)
        n_pairs_far = 0
        for key, arr in buckets.items():
            gs = [x[0] for x in arr]
            spread = max(gs) - min(gs)
            if spread > best[0]:
                lo = min(arr, key=lambda t: t[0])
                hi = max(arr, key=lambda t: t[0])
                best = (spread, key, lo, hi)
            if spread >= 3:
                n_pairs_far += 1
        out[str(n)] = {
            "max_g_spread_same_h_mu": best[0],
            "cell": list(best[1]) if best[1] else None,
            "low": {"g": best[2][0], "occ": best[2][1], "k": best[2][2]} if best[1] else None,
            "high": {"g": best[3][0], "occ": best[3][1], "k": best[3][2]} if best[1] else None,
            "n_cells_spread_ge3": n_pairs_far,
        }
        print("B330 n", n, out[str(n)])
    return out


def main() -> None:
    verify = check_b342_b345()
    gaps = b333_gap_hist()
    b330 = b330_pairs()
    path = ROOT / "research" / "verification" / "round2_b321.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["independent_checks"] = {"B342_B345": verify, "B333_gaps": gaps, "B330": b330}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
