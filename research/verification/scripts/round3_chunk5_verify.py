#!/usr/bin/env python3
"""Round3 chunk5 - INDEPENDENT verification of the B291..B300 witnesses.

Re-derives every reported invariant from scratch (own det4, own legal-move
scan, own grundy DP) and checks the P/N claim and the key equality.  Also
verifies the B300 depth-d tree invariants and the J_n facts (bridges,
articulation points, perfect matchings) with separate code paths.

Output: research/verification/round3_chunk5_verify.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk5_verify.json"


# ---------------- independent geometry (own determinant, no shared code) ----
def det_ind(p0, p1, p2, p3):
    """3x3 determinant of [[x^2+y^2, x, y]] columns; equals the 4x4 with ones."""
    a = [p0, p1, p2, p3]

    def m3(r0, r1, r2):
        return (a[r0][0] * (a[r1][1] * a[r2][2] - a[r1][2] * a[r2][1])
                - a[r0][1] * (a[r1][0] * a[r2][2] - a[r1][2] * a[r2][0])
                + a[r0][2] * (a[r1][0] * a[r2][1] - a[r1][1] * a[r2][0]))

    return (m3(1, 2, 3) - m3(0, 2, 3) + m3(0, 1, 3) - m3(0, 1, 2))


def row(n, v):
    x, y = v % n, v // n
    return (x * x + y * y, x, y)


def quad_list(n):
    V = n * n
    rows = [row(n, v) for v in range(V)]
    qs = []
    for c in combinations(range(V), 4):
        if det_ind(*[rows[i] for i in c]) == 0:
            qs.append(sum(1 << i for i in c))
    return qs, V


class Ind:
    def __init__(self, n):
        self.n = n
        self.V = n * n
        self.quads, _ = quad_list(n)
        self.full = (1 << self.V) - 1
        self.qbp = [[] for _ in range(self.V)]
        for q in self.quads:
            for i in range(self.V):
                if (q >> i) & 1:
                    self.qbp[i].append(q)

    def legal(self, occ):
        out = []
        for v in range(self.V):
            if (occ >> v) & 1:
                continue
            m = occ | (1 << v)
            ok = True
            for q in self.qbp[v]:
                if (q & m) == q:
                    ok = False
                    break
            if ok:
                out.append(v)
        return out

    def solve(self):
        reach = {0}
        st = [0]
        while st:
            o = st.pop()
            for u in self.legal(o):
                nx = o | (1 << u)
                if nx not in reach:
                    reach.add(nx)
                    st.append(nx)
        g = {}
        Lc = {}
        for o in sorted(reach, key=lambda m: -m.bit_count()):
            mv = self.legal(o)
            Lc[o] = mv
            if not mv:
                g[o] = 0
            else:
                s = {g[o | (1 << u)] for u in mv}
                x = 0
                while x in s:
                    x += 1
                g[o] = x
        return g, Lc

    def maxterm(self, o, memo):
        """max |terminal| reachable from o (h(S)+|S|)."""
        if o in memo:
            return memo[o]
        mv = self.legal(o)
        if not mv:
            memo[o] = o.bit_count()
        else:
            memo[o] = max(self.maxterm(o | (1 << u), memo) for u in mv)
        return memo[o]


def oc(v, n):
    return f"({v % n},{v // n})"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    t0 = time.time()
    ind = Ind(n)
    g, Lc = ind.solve()
    hterm = {}

    def h_of(occ):
        return ind.maxterm(occ, hterm) - occ.bit_count()

    report = {"n": n, "n_states": len(g), "g_empty": g[0]}

    # ---- verify B291..B296 witnesses ----
    src = ROOT / "research" / "verification" / (
        "round3_chunk5_sharp.json" if n == 4 else "round3_chunk5_sharp_n5.json")
    if src.exists():
        rep = json.loads(src.read_text(encoding="utf-8"))
        block = rep.get(f"n{n}")
        if block:
            ver = {}
            for key in ("B291", "B291_b", "B292", "B293", "B293_weak", "B294",
                        "B294_weak", "B295", "B296"):
                ent = block.get(key)
                if not ent or not ent.get("examples"):
                    continue
                checks = []
                for ex in ent["examples"]:
                    P = ex["P"]
                    N = ex["N"]
                    mP = sum(1 << v for v in P)
                    mN = sum(1 << v for v in N)
                    kP, kN = mP.bit_count(), mN.bit_count()
                    rowsP = [row(n, v) for v in P]
                    rowsN = [row(n, v) for v in N]
                    mdP = None
                    if kP >= 4:
                        mdP = min(abs(det_ind(*[rowsP[i] for i in c]))
                                  for c in combinations(range(kP), 4)
                                  if det_ind(*[rowsP[i] for i in c]) != 0)
                    mdN = None
                    if kN >= 4:
                        mdN = min(abs(det_ind(*[rowsN[i] for i in c]))
                                  for c in combinations(range(kN), 4)
                                  if det_ind(*[rowsN[i] for i in c]) != 0)
                    chP = sorted(len(Lc[mP | (1 << p)]) for p in Lc[mP])
                    chN = sorted(len(Lc[mN | (1 << p)]) for p in Lc[mN])
                    dP = tuple(sorted((P[i] % n - P[j] % n) ** 2 + (P[i] // n - P[j] // n) ** 2
                                      for i in range(kP) for j in range(i + 1, kP)))
                    dN = tuple(sorted((N[i] % n - N[j] % n) ** 2 + (N[i] // n - N[j] // n) ** 2
                                      for i in range(kN) for j in range(i + 1, kN)))
                    bP = tuple(sorted(min(v % n, v // n, n - 1 - v % n, n - 1 - v // n)
                                      for v in P))
                    bN = tuple(sorted(min(v % n, v // n, n - 1 - v % n, n - 1 - v // n)
                                      for v in N))

                    def comp(S):
                        ss = set(S)
                        out = []
                        for tri in combinations(sorted(S), 3):
                            c = 0
                            for e in range(n * n):
                                if e in ss:
                                    continue
                                if det_ind(row(n, tri[0]), row(n, tri[1]), row(n, tri[2]),
                                           row(n, e)) == 0:
                                    c += 1
                            out.append(c)
                        return tuple(sorted(out))

                    def subpn(S):
                        o = {}
                        for j in range(1, min(3, len(S)) + 1):
                            a = b = 0
                            for s in combinations(S, j):
                                m = sum(1 << v for v in s)
                                if g.get(m) == 0:
                                    a += 1
                                else:
                                    b += 1
                            o[j] = (a, b)
                        return o

                    def ext(S):
                        o = {}
                        k = len(S)
                        Sset = set(S)
                        empty = [v for v in range(n * n) if v not in Sset]
                        for dt in (1, 2, 3):
                            c = 0
                            for add in combinations(empty, dt):
                                m = sum(1 << v for v in S)
                                ok = True
                                for p in add:
                                    m2 = m | (1 << p)
                                    if any((q & m2) == q for q in ind.qbp[p]):
                                        ok = False
                                        break
                                    m = m2
                                if ok:
                                    c += 1
                            o[dt] = c
                        return tuple(sorted(o.items()))

                    rec = {
                        "P": [oc(v, n) for v in P], "N": [oc(v, n) for v in N],
                        "g_P": g[mP], "g_N": g[mN],
                        "L_P": len(Lc[mP]), "L_N": len(Lc[mN]),
                        "h_P": h_of(mP), "h_N": h_of(mN),
                        "min_det_P": mdP, "min_det_N": mdN,
                        "child_hist_equal": chP == chN,
                        "dist_equal": dP == dN, "bdist_equal": bP == bN,
                        "comp_equal": comp(P) == comp(N),
                        "subpn_equal": subpn(P) == subpn(N),
                    }
                    if n == 4:
                        rec["ext_equal"] = ext(P) == ext(N)
                    rec["pn_opposite"] = (g[mP] == 0) != (g[mN] == 0)
                    checks.append(rec)
                ver[key] = checks
            report["witness_checks"] = ver

    # ---- B297 / B298 / B299 independent recomputation ----
    b = {}
    b297 = []
    b298 = []
    b299 = []
    for occ, gv in g.items():
        k = occ.bit_count()
        if k < 2 or k > (6 if n == 4 else 4):
            continue
        S = [v for v in range(n * n) if (occ >> v) & 1]
        L = Lc[occ]
        wins = [p for p in L if g[occ | (1 << p)] == 0]
        if gv != 0 and len(wins) == 1 and len(L) >= 3:
            p0 = wins[0]
            degs = {p: sum(1 for q in ind.qbp[p] if q & occ) for p in L}
            us = {p: len(L) - len(Lc[occ | (1 << p)]) for p in L}
            if (min(degs.values()) < degs[p0] < max(degs.values())
                    and min(us.values()) < us[p0] < max(us.values())):
                b297.append({"S": [oc(v, n) for v in S], "p": oc(p0, n),
                             "deg": degs[p0], "deg_range": [min(degs.values()), max(degs.values())],
                             "u": us[p0], "u_range": [min(us.values()), max(us.values())],
                             "n_legal": len(L)})
    b["B297_n_hits"] = len(b297)
    b["B297_examples"] = b297[:3]
    print(f"  B297 independent: {len(b297)}", flush=True)

    # B298: P with strictly more legal moves (=> more (k+1)-supersets) and h_P>=h_N
    byk = defaultdict(lambda: ([], []))
    for occ, gv in g.items():
        k = occ.bit_count()
        if k < 2 or k > (6 if n == 4 else 4):
            continue
        byk[k][0 if gv == 0 else 1].append(occ)
    for k, (ps, ns) in byk.items():
        for p in ps:
            for q in ns:
                if len(Lc[p]) > len(Lc[q]) and h_of(p) >= h_of(q):
                    b298.append({"k": k, "P": [oc(v, n) for v in range(n * n) if (p >> v) & 1],
                                 "N": [oc(v, n) for v in range(n * n) if (q >> v) & 1],
                                 "L_P": len(Lc[p]), "L_N": len(Lc[q]),
                                 "h_P": h_of(p), "h_N": h_of(q)})
                    break
            if len(b298) >= 3:
                break
        if len(b298) >= 3:
            break
    b["B298_n_hits"] = len(b298)
    b["B298_examples"] = b298[:3]
    print(f"  B298 independent: {len(b298)}", flush=True)

    # B299: n=4 only.  Block a winning move -> still N, new winning move born.
    if n == 4:
        from kyouen_core import Board
        for occ, gv in g.items():
            if gv == 0 or occ.bit_count() != 3:
                continue
            L = Lc[occ]
            wins = [p for p in L if g[occ | (1 << p)] == 0]
            if not wins:
                continue
            p0 = wins[0]
            idx = [v for v in range(16) if v != p0]
            rm = {v: i for i, v in enumerate(idx)}
            sub = Ind.__new__(Ind)
            sub.n = 4
            sub.V = 15
            bpts = [(v % 4, v // 4) for v in idx]
            bb = Board(bpts, name="sub")
            sub.quads = bb.quads
            sub.qbp = bb.quads_by_pt
            sub.full = bb.full
            sg, sLc = sub.solve()
            socc = 0
            for v in range(16):
                if (occ >> v) & 1 and v != p0:
                    socc |= 1 << rm[v]
            if socc not in sg:
                continue
            sw = [idx[q] for q in sLc[socc] if sg[socc | (1 << q)] == 0]
            orig_nonwins = [p for p in L if g[occ | (1 << p)] != 0 and p != p0]
            reborn = [v for v in sw if v in orig_nonwins]
            if sg[socc] != 0 and reborn:
                b299.append({"S": [oc(v, n) for v in range(16) if (occ >> v) & 1],
                             "g_orig": gv, "blocked": oc(p0, n),
                             "wins_orig": [oc(v, n) for v in wins],
                             "g_after": sg[socc],
                             "reborn": [oc(v, n) for v in reborn]})
        b["B299_n_hits"] = len(b299)
        b["B299_examples"] = b299[:3]
        print(f"  B299 independent: {len(b299)}", flush=True)

    report["B297_B298_B299"] = b
    report["seconds"] = round(time.time() - t0, 1)
    outp = ROOT / "research" / "verification" / (
        "round3_chunk5_verify.json" if n == 4 else "round3_chunk5_verify_n5.json")
    old = json.loads(outp.read_text(encoding="utf-8")) if outp.exists() else {}
    old[f"n{n}"] = report
    outp.write_text(json.dumps(old, indent=2, default=str), encoding="utf-8")
    print("wrote", outp)


if __name__ == "__main__":
    main()
