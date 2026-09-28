#!/usr/bin/env python3
"""Round3 chunk5 - shared fast helpers + B291..B300 sharp counterexample pairs.

B291 min|det| equal but P/N differ
B292 distance multiset (+ boundary distance multiset) equal but P/N differ
B293 completion histogram over all 3-subsets equal but P/N differ
B294 child |L| histogram equal but P/N differ
B295 maximal-extension count profile equal but P/N differ
B296 j<=3 subset P/N count vector equal but P/N differ
B297 unique winning move non-extremal in degree AND u AND stabilizer
B298 more (k+1)-supersets (and no larger local h) but P  -> exists
B299 blocking one winning move keeps N, a previously non-winning move becomes winning
B300 depth-d move trees isomorphic but P/N differ (d=1 here; d=2 in B300 script)

Output: research/verification/round3_chunk5_sharp.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square, det4  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk5_sharp.json"


# ----------------------------------------------------------------- game core
class Game:
    def __init__(self, n: int):
        self.n = n
        self.b = board_square(n)
        self.V = n * n
        self.quads = self.b.quads
        self.qbp = self.b.quads_by_pt
        self.full = self.b.full
        self.rows = [self._row(v) for v in range(self.V)]

    def _row(self, v):
        x, y = v % self.n, v // self.n
        return (x * x + y * y, x, y, 1)

    def legal(self, occ):
        out = []
        empty = self.full ^ occ
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                ok = True
                for q in self.qbp[v]:
                    if (q & (occ | bit)) == q:
                        ok = False
                        break
                if ok:
                    out.append(v)
            empty >>= 1
            v += 1
        return out

    def grundy_all(self, reachable):
        g = {}
        Lc = {}
        order = sorted(reachable, key=lambda m: -m.bit_count())
        for occ in order:
            mv = self.legal(occ)
            Lc[occ] = mv
            if not mv:
                g[occ] = 0
                continue
            seen = {g[occ | (1 << u)] for u in mv}
            x = 0
            while x in seen:
                x += 1
            g[occ] = x
        return g, Lc

    def reachable(self):
        reach = {0}
        st = [0]
        while st:
            occ = st.pop()
            for u in self.legal(occ):
                nxt = occ | (1 << u)
                if nxt not in reach:
                    reach.add(nxt)
                    st.append(nxt)
        return reach

    def u_gain(self, occ, p):
        return len(self.legal(occ)) - len(self.legal(occ | (1 << p)))

    def threat_deg(self, occ, p):
        """# forbidden quads through p that already contain another point of occ."""
        m = occ | (1 << p)
        c = 0
        for q in self.qbp[p]:
            if (q & occ) and (q & m) != (1 << p) or ((q & occ) and (q & m) == (1 << p)):
                c += 1
        return c

    def threat_deg_fast(self, occ, p):
        """fast: # quads through p that have >=1 other point in occ."""
        c = 0
        for q in self.qbp[p]:
            if q & occ:
                c += 1
        return c


def h_all(game, g, reach, cap=12):
    """h(S) = max over completions of |S'| - |S| ; computed by DP descending in k."""
    h = {}
    order = sorted(reach, key=lambda m: -m.bit_count())
    for occ in order:
        if not game.legal(occ):
            h[occ] = 0
        else:
            best = 0
            for u in game.legal(occ):
                v = 1 + h[occ | (1 << u)]
                if v > best:
                    best = v
            h[occ] = best
    return h


def bits(mask):
    while mask:
        b = mask & -mask
        yield b.bit_length() - 1
        mask ^= b


def det_table(game):
    rows = game.rows
    return {c: det4(*[rows[i] for i in c]) for c in combinations(range(game.V), 4)}


# ------------------------------------------------------------------ features
def min_abs_det(game, S):
    S = sorted(S)
    if len(S) < 4:
        return -1
    best = None
    for c in combinations(S, 4):
        d = abs(det4(*[game.rows[i] for i in c]))
        if d and (best is None or d < best):
            best = d
    return -1 if best is None else best


def dist_multiset(n, S):
    out = []
    for a, b in combinations(sorted(S), 2):
        dx = (a % n) - (b % n)
        dy = (a // n) - (b // n)
        out.append(dx * dx + dy * dy)
    return tuple(sorted(out))


def boundary_dist_multiset(n, S):
    out = []
    for v in S:
        x, y = v % n, v // n
        out.append(min(x, y, n - 1 - x, n - 1 - y))
    return tuple(sorted(out))


def completion_hist(game, S, tab):
    """multiset of c(T) over 3-subsets T of S; c(T)=#board pts completing a quad."""
    S = sorted(S)
    Sset = set(S)
    out = []
    for tri in combinations(S, 3):
        key = tuple(sorted(tri))
        c = 0
        for extra in range(game.V):
            if extra in Sset:
                continue
            k4 = tuple(sorted(key + (extra,)))
            if tab[k4] == 0:
                c += 1
        out.append(c)
    return tuple(sorted(out))


def ext_profile(game, occ, k, dmax=3):
    """# safe supersets of size k+dt (dt=1..dmax) containing occ."""
    empty = [p for p in range(game.V) if not (occ >> p) & 1]
    prof = {}
    for dt in range(1, dmax + 1):
        c = 0
        for add in combinations(empty, dt):
            m = occ
            ok = True
            for p in add:
                if m | (1 << p) in game.qbp[p]:
                    # fast check: any quad fully inside new mask
                    bad = False
                    for q in game.qbp[p]:
                        if (q & (m | (1 << p))) == q:
                            bad = True
                            break
                    if bad:
                        ok = False
                        break
                m |= 1 << p
            if ok:
                c += 1
        prof[dt] = c
    return prof


def subpn_vec(g, S, jmax=3):
    res = {}
    for j in range(1, min(jmax, len(S)) + 1):
        np_ = 0
        nn = 0
        for sub in combinations(S, j):
            m = 0
            for p in sub:
                m |= 1 << p
            v = g.get(m)
            if v is None:
                continue
            if v == 0:
                np_ += 1
            else:
                nn += 1
        res[j] = (np_, nn)
    return res


# ------------------------------------------------------------------ analysis
def split_search(stats, keyfn, name, cap=3):
    groups = defaultdict(list)
    for st in stats:
        groups[keyfn(st)].append(st)
    nsplit = 0
    ex = []
    for key, lst in groups.items():
        ps = [x for x in lst if x["g"] == 0]
        ns = [x for x in lst if x["g"] != 0]
        if ps and ns:
            nsplit += 1
            if len(ex) < cap:
                ex.append({
                    "key": repr(key)[:180],
                    "P": ps[0]["S"], "g_P": ps[0]["g"], "L_P": ps[0]["L"],
                    "N": ns[0]["S"], "g_N": ns[0]["g"], "L_N": ns[0]["L"],
                    "group_size": len(lst),
                })
    print(f"  {name}: groups={len(groups)} pn_split={nsplit}", flush=True)
    return {"n_groups": len(groups), "n_pn_split_groups": nsplit, "examples": ex,
            "verdict": "FOUND" if nsplit else "none_in_range"}


def analyze(n, kmax=6, cap=3, kmin=2):
    t0 = time.time()
    game = Game(n)
    reach = game.reachable()
    g, Lc = game.grundy_all(reach)
    print(f"[n={n}] states={len(reach)} g0={g[0]} maxg={max(g.values())} "
          f"({time.time()-t0:.1f}s)", flush=True)
    tab = det_table(game)
    h = h_all(game, g, reach)

    stats = []
    for occ in reach:
        k = occ.bit_count()
        if k < kmin or k > kmax:
            continue
        S = list(bits(occ))
        L = len(Lc[occ])
        stats.append({
            "occ": occ, "S": S, "k": k, "g": g[occ], "L": L, "h": h[occ],
            "child_h": tuple(sorted(len(Lc[occ | (1 << p)]) for p in Lc[occ])),
            "min_det": min_abs_det(game, S),
            "dist": dist_multiset(n, S),
            "bdist": boundary_dist_multiset(n, S),
            "comp": completion_hist(game, S, tab),
            "subpn": subpn_vec(g, S),
        })
    print(f"[n={n}] analyzed={len(stats)} ({time.time()-t0:.1f}s)", flush=True)

    res = {"n": n, "n_states": len(reach), "kmax": kmax, "n_analyzed": len(stats)}

    def split_where(where, keyfn, name, cap=3):
        sub = [s for s in stats if where(s)]
        r = split_search(sub, keyfn, name, cap)
        r["n_positions"] = len(sub)
        return r

    res["B291"] = split_where(lambda s: s["k"] >= 4, lambda s: (s["k"], s["min_det"], s["L"]),
                               "B291 (k>=4: k,min|det|,|L|)", cap)
    res["B291_b"] = split_where(lambda s: s["k"] >= 4,
                                lambda s: (s["k"], s["min_det"], s["L"], sum(s["comp"])),
                                "B291 (k>=4: +sum c)", cap)
    res["B292"] = split_where(lambda s: s["k"] >= 3, lambda s: (s["k"], s["dist"], s["bdist"]),
                               "B292 (k>=3: dist,bdist)", cap)
    res["B293_weak"] = split_where(lambda s: s["k"] >= 3, lambda s: (s["k"], s["comp"]),
                                    "B293 (k>=3: comp)", cap)
    res["B293"] = split_where(lambda s: s["k"] >= 4, lambda s: (s["k"], s["comp"], s["L"]),
                               "B293 (k>=4: comp,|L|)", cap)
    res["B294_weak"] = split_where(lambda s: s["k"] >= 3, lambda s: (s["child_h"],),
                                    "B294w (k>=3: child hist only)", cap)
    res["B294"] = split_where(lambda s: s["k"] >= 3, lambda s: (s["k"], s["L"], s["child_h"]),
                               "B294 (k>=3: |L|,child hist)", cap)

    # --- B295: maximal-extension count profile
    if n <= 4:
        for st in stats:
            st["ext"] = ext_profile(game, st["occ"], st["k"], dmax=3)
        res["B295"] = split_where(lambda s: s["k"] >= 3,
                                  lambda s: (s["k"], tuple(sorted(s["ext"].items()))),
                                  "B295 (k>=3: ext profile k+1..k+3)", cap)
        res["B296"] = split_where(lambda s: s["k"] >= 3,
                                  lambda s: (s["k"], tuple(sorted(s["subpn"].items()))),
                                  "B296 (k>=3: j<=3 subset P/N counts)", cap)
    else:
        res["B296"] = split_where(lambda s: s["k"] >= 3,
                                  lambda s: (s["k"], tuple(sorted(s["subpn"].items()))),
                                  "B296 (k>=3: j<=3 subset P/N counts)", cap)

    # --- B298: P with strictly more (k+1)-supersets than some N, h_P >= h_N
    b298 = []
    by_k = defaultdict(list)
    for st in stats:
        by_k[st["k"]].append(st)
    for k, lst in by_k.items():
        ps = [x for x in lst if x["g"] == 0]
        ns = [x for x in lst if x["g"] != 0]
        for p in ps:
            for q in ns:
                if p["L"] > q["L"] and p["h"] >= q["h"]:
                    b298.append({"k": k, "P": p["S"], "N": q["S"],
                                 "L_P": p["L"], "L_N": q["L"],
                                 "h_P": p["h"], "h_N": q["h"],
                                 "g_P": p["g"], "g_N": q["g"]})
                    break
            if len(b298) >= 3:
                break
        if len(b298) >= 3:
            break
    res["B298"] = {"n_hits": len(b298), "examples": b298,
                   "verdict": "FOUND" if b298 else "none_in_range"}
    print(f"  B298 hits={len(b298)}", flush=True)

    # --- B297: unique winning move, non-extremal in (threat-deg, u, stabilizer)
    b297 = []
    for st in stats:
        occ, k, gv = st["occ"], st["k"], st["g"]
        if gv == 0 or len(Lc[occ]) < 3:
            continue
        wins = [p for p in Lc[occ] if g[occ | (1 << p)] == 0]
        if len(wins) != 1:
            continue
        p0 = wins[0]
        moves = Lc[occ]
        degs = {p: game.threat_deg_fast(occ, p) for p in moves}
        us = {p: game.u_gain(occ, p) for p in moves}
        # stabilizer of the position: D4 orbit size of the set S (square boards)
        orbit = d4_orbit_size(n, st["S"])
        d0, u0 = degs[p0], us[p0]
        if (min(degs.values()) < d0 < max(degs.values())
                and min(us.values()) < u0 < max(us.values())
                and len(b297) < 3):
            b297.append({"S": st["S"], "k": k, "g": gv, "p": p0,
                         "deg": d0, "deg_min": min(degs.values()), "deg_max": max(degs.values()),
                         "u": u0, "u_min": min(us.values()), "u_max": max(us.values()),
                         "d4_orbit_size": orbit, "n_legal": len(moves)})
    res["B297"] = {"n_hits": len(b297), "examples": b297,
                   "verdict": "FOUND" if b297 else "none_in_range"}
    print(f"  B297 hits={len(b297)}", flush=True)

    # --- B299: block a winning move point (remove from board entirely)
    b299 = []
    for st in stats:
        occ, gv = st["occ"], st["g"]
        if gv == 0 or st["k"] != 3 or n != 4:
            continue
        wins = [p for p in Lc[occ] if g[occ | (1 << p)] == 0]
        if not wins:
            continue
        p0 = wins[0]
        # sub-board with p0 deleted
        idx = [v for v in range(game.V) if v != p0]
        remap = {v: i for i, v in enumerate(idx)}
        sub = Game.__new__(Game)
        sub.n = 1
        # rebuild a Game over the reduced point set with the same quad structure
        from kyouen_core import Board
        bpts = [(v % n, v // n) for v in idx]
        sub.b = Board(bpts, name=f"n{n}-del{p0}")
        sub.V = len(bpts)
        sub.quads = sub.b.quads
        sub.qbp = sub.b.quads_by_pt
        sub.full = sub.b.full
        sub.rows = [sub.b.rows[i] for i in range(sub.V)]
        sreach = sub.reachable()
        sg, sLc = sub.grundy_all(sreach)
        socc = 0
        for v in st["S"]:
            if v != p0:
                socc |= 1 << remap[v]
        if socc not in sg:
            continue
        newsg = sg[socc]
        swins = [q for q in sLc[socc] if sg[socc | (1 << q)] == 0]
        newnames = [idx[q] for q in swins]
        # original non-winning legal moves
        orig_nonwins = [p for p in Lc[occ] if g[occ | (1 << p)] != 0 and p != p0]
        reborn = [v for v in newnames if v in orig_nonwins]
        if newsg != 0 and reborn:
            b299.append({"S": st["S"], "g_orig": gv, "blocked": p0,
                         "wins_orig": wins, "g_after": newsg,
                         "new_wins": newnames, "reborn_wins": reborn})
    res["B299"] = {"n_hits": len(b299), "examples": b299[:5],
                   "verdict": "FOUND" if b299 else "none_in_range"}
    print(f"  B299 hits={len(b299)}", flush=True)

    # --- B300 d=1: |L| and child |L| histogram identical but P/N differ
    res["B300_d1"] = res["B294"]
    # d=1 tree = child |L| multiset  (i.e. {|L(S+p)|}) -> B294_weak
    res["B300_d1_note"] = "depth-1 move tree = multiset {|L(S+p)|}; identical to B294_weak"

    return res, stats, game, g, Lc, h, tab


def d4_orbit_size(n, S):
    S = set(S)
    def pt(x, y):
        return y * n + x
    def inv(i):
        return i % n, i // n
    maps = [lambda x, y: (x, y), lambda x, y: (y, n - 1 - x),
            lambda x, y: (n - 1 - x, n - 1 - y), lambda x, y: (n - 1 - y, x),
            lambda x, y: (n - 1 - x, y), lambda x, y: (x, n - 1 - y),
            lambda x, y: (y, x), lambda x, y: (n - 1 - y, n - 1 - x)]
    orb = {frozenset(S)}
    for f in maps:
        orb.add(frozenset(pt(*f(*inv(v))) for v in S))
    return len(orb)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, nargs="*", default=[4, 5])
    ap.add_argument("--kmax", type=int, default=6)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    outp = Path(a.out)
    report = json.loads(outp.read_text(encoding="utf-8")) if outp.exists() else {}
    for n in a.n:
        res, *_ = analyze(n, kmax=a.kmax)
        report[f"n{n}"] = res
        outp.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print("checkpoint written", outp, flush=True)
    print("wrote", outp)


if __name__ == "__main__":
    main()
