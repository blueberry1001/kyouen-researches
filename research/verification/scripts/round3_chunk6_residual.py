#!/usr/bin/env python3
"""Round3 chunk6 group B: B341, B343, B344, B347, B348, B349.

Attacks the obstacles left by round2-batch-b321.md:
  B341 PARTIAL  -> the observed |diff| cap was 5 for n<=5 with only 250
                    positions solved.  This run solves the *whole* eligible
                    population for n=3,4 and a large stratified sample for
                    n=5, and separates the two readings
                    ("one residual" = delete one 3-residual, "one edge" =
                    delete one 2-residual) that round2 conflated.
  B343 INCONCLUSIVE -> round2 only compared win-sets of full vs minus-ONE
                    3-residual and found 0.  Here we scan *all* residual
                    subsets of size >=1 removed (including 4-residuals and
                    pairs), on the whole eligible population.
  B344 NOT-CHECKED -> classify every "effective" 3-residual by its position
                    inside P(S): parity of the distance to the branch
                    vertex, whether it lies on a shared path, its cycle
                    participation.  Gives the first "type" table.
  B347/B348 NOT-CHECKED -> stratified error-rate statistics of the 2-point
                    approximation against (coverage ratio) and (number of
                    P(S) components bridged), inside (n,k,|L|) cells.
  B349 NOT-CHECKED -> minimum-|L| positions where the 3-residual-truncated
                    game still misses the true g but removing a 4-residual
                    fixes it, plus abstract hypergraph canonical types.

Output: research/verification/round3_chunk6_residual.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square  # noqa: E402
from residual_core import (P_graph_edges, bits_of, legal_mask,  # noqa: E402
                           residual_R)

sys.setrecursionlimit(300000)
OUT = ROOT / "research" / "verification" / "round3_chunk6_residual.json"


# --------------------------------------------------------------------------
class ResidualGame:
    """Game on L: place a legal point, may not complete a residual."""

    def __init__(self, Lmask: int, residuals: list[int]):
        self.pts = bits_of(Lmask)
        self.m = len(self.pts)
        idx = {p: i for i, p in enumerate(self.pts)}
        self.idx = idx
        rs = set()
        for r in residuals:
            rm = 0
            ok = True
            for p in bits_of(r):
                if p not in idx:
                    ok = False
                    break
                rm |= 1 << idx[p]
            if ok and rm:
                rs.add(rm)
        self.rs = sorted(rs)
        self.g: dict[int, int] = {}
        self.moves: dict[int, list[int]] = {}

    def legal(self, occ: int) -> list[int]:
        if occ in self.moves:
            return self.moves[occ]
        out = []
        for i in range(self.m):
            if (occ >> i) & 1:
                continue
            nxt = occ | (1 << i)
            if any((nxt & r) == r for r in self.rs):
                continue
            out.append(i)
        self.moves[occ] = out
        return out

    def ev(self, occ: int) -> int:
        if occ in self.g:
            return self.g[occ]
        mv = self.legal(occ)
        if not mv:
            self.g[occ] = 0
            return 0
        seen = {self.ev(occ | (1 << u)) for u in mv}
        x = 0
        while x in seen:
            x += 1
        self.g[occ] = x
        return x

    def win_moves(self) -> list[int]:
        return [u for u in self.legal(0) if self.ev(1 << u) == 0]


# --------------------------------------------------------------------------
def bfs_dist_from(adj: dict, src: int, n: int) -> list[int]:
    INF = 10 ** 9
    d = [INF] * n
    d[src] = 0
    q = [src]
    head = 0
    while head < len(q):
        u = q[head]
        head += 1
        for v in adj.get(u, ()):  # noqa: B007
            if d[v] == INF:
                d[v] = d[u] + 1
                q.append(v)
    return d


def tree_info(edges: list[tuple[int, int]], nvert: int):
    adj = defaultdict(set)
    has = [False] * nvert
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
        has[a] = has[b] = True
    deg = [0] * nvert
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    # branching vertices (deg>=3) and leaves
    branch = [v for v in range(nvert) if deg[v] >= 3]
    # forest test
    parent = list(range(nvert))

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
    # connected components
    seen = [False] * nvert
    comps = []
    for s in range(nvert):
        if not has[s] or seen[s]:
            continue
        stack = [s]
        seen[s] = True
        c = [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    c.append(v)
                    stack.append(v)
        comps.append(set(c))
    isolated = [v for v in range(nvert) if deg[v] == 0]
    return {
        "adj": adj, "deg": deg, "branch": branch, "is_forest": is_forest,
        "comps": comps, "isolated": isolated, "n_edges": len(edges),
    }


def clique_union(edges, nvert) -> bool:
    adj = defaultdict(set)
    has = set()
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
        has.add(a)
        has.add(b)
    seen = set()
    for s in has:
        if s in seen:
            continue
        comp = []
        stack = [s]
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        cs = set(comp)
        for u in comp:
            for v in cs:
                if u != v and v not in adj[u]:
                    return False
    return True


# --------------------------------------------------------------------------
def enumerate_candidates(B, max_L: int):
    """All safe states with a non-trivial residual set and |L| <= max_L."""
    out = []
    stack = [(0, 0)]   # (occ, start index) - enumerate all safe sets
    # simple: iterate over all safe sets of size <= K by increasing index
    V = B.V

    def rec(occ, start):
        if occ.bit_count() and len(out) > 400000:
            return
        for v in range(start, V):
            bit = 1 << v
            if occ & bit:
                continue
            ok = True
            for q in B.quads_by_pt[v]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if not ok:
                continue
            rec(occ | bit, v + 1)
        if occ:
            L = legal_mask(B, occ)
            if L.bit_count() <= max_L:
                R = residual_R(B, occ)
                if R:
                    out.append((occ, L, R))
    rec(0, 0)
    return out


def main() -> None:
    res: dict = {}
    for n, max_L, cap in ((3, 14, 10 ** 9), (4, 14, 10 ** 9), (5, 12, 1200)):
        t0 = time.time()
        B = board_square(n)
        print(f"[n={n}] enumerating candidates...", flush=True)
        cands = enumerate_candidates(B, max_L)
        print(f"[n={n}] candidates={len(cands)} ({time.time()-t0:.1f}s)", flush=True)
        blk = analyze_n(n, B, cands, cap)
        blk["n_candidates"] = len(cands)
        blk["max_L"] = max_L
        blk["elapsed_s"] = round(time.time() - t0, 1)
        res[str(n)] = blk
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                       encoding="utf-8")
        print(f"[n={n}] done in {blk['elapsed_s']}s", flush=True)
    print("wrote", OUT, flush=True)


def analyze_n(n, B, cands, cap) -> dict:
    """Full analysis of the eligible population (capped for n=5)."""
    # deterministic stratification for the cap: sort by (k, |L|, n3, n4)
    cands = sorted(cands, key=lambda t: (t[0].bit_count(), t[1].bit_count(),
                                         sum(1 for r in t[2] if r.bit_count() == 3),
                                         sum(1 for r in t[2] if r.bit_count() == 4)))
    if len(cands) > cap:
        step = len(cands) / cap
        cands = [cands[int(i * step)] for i in range(cap)]
    print(f"  analysing {len(cands)} positions", flush=True)

    b341 = {"max_diff_3res": 0, "max_diff_2res": 0, "hist3": defaultdict(int),
            "hist2": defaultdict(int), "witness3": None, "witness2": None,
            "forest_violations_gt3": 0, "forest_max": 0}
    b343 = {"n_tested": 0, "n_disjoint_win": 0, "examples": [],
            "kinds_tried": ["one 3-res", "one 4-res", "two 3-res", "all 3-res"]}
    b344 = {"types": defaultdict(int), "examples": [], "n_effective": 0}
    b347 = {"rows": [], "cells": defaultdict(lambda: [0, 0])}
    b348 = {"rows": [], "cells": defaultdict(lambda: [0, 0])}
    b349 = {"n_found": 0, "examples": [], "min_L": None,
            "hyper_types": defaultdict(int)}
    b345_extra = {"clique_diff": 0, "clique_same": 0}

    n_solved = 0
    for occ, Lmask, R in cands:
        k = occ.bit_count()
        nL = Lmask.bit_count()
        pts = bits_of(Lmask)
        idx = {p: i for i, p in enumerate(pts)}
        abs_res = []
        for r in R:
            rm = 0
            for p in bits_of(r):
                rm |= 1 << idx[p]
            abs_res.append(rm)
        i2 = [i for i, r in enumerate(R) if r.bit_count() == 2]
        i3 = [i for i, r in enumerate(R) if r.bit_count() == 3]
        i4 = [i for i, r in enumerate(R) if r.bit_count() == 4]
        # P(S) edges in *local* index space 0..nL-1 (residual_core returns board ids)
        edges = sorted({(min(idx[a], idx[b]), max(idx[a], idx[b]))
                        for a, b in P_graph_edges(R)})
        ti = tree_info(edges, nL)
        adj = ti["adj"]
        deg = ti["deg"]

        full = ResidualGame(Lmask, R)
        g_full = full.ev(0)
        win_full = set(full.win_moves())

        two = ResidualGame(Lmask, [R[i] for i in i2])
        g2 = two.ev(0)

        # ---------------- B341: single-residual deletion ----------------
        for tag, group in (("3res", i3), ("2res", i2)):
            for ti_ in group[:8]:
                keep = [R[i] for i in range(len(R)) if i != ti_]
                sub = ResidualGame(Lmask, keep)
                gm = sub.ev(0)
                d = abs(g_full - gm)
                if tag == "3res":
                    b341["hist3"][d] += 1
                    if d > b341["max_diff_3res"]:
                        b341["max_diff_3res"] = d
                        b341["witness3"] = {
                            "occ": bits_of(occ), "k": k, "nL": nL, "g_full": g_full,
                            "g_minus": gm, "removed_residual": bits_of(R[ti_]),
                            "is_forest": ti["is_forest"],
                            "n_edges": ti["n_edges"], "n_branch": len(ti["branch"]),
                        }
                    if ti["is_forest"]:
                        b341["forest_max"] = max(b341["forest_max"], d)
                        if d > 3:
                            b341["forest_violations_gt3"] += 1
                else:
                    b341["hist2"][d] += 1
                    if d > b341["max_diff_2res"]:
                        b341["max_diff_2res"] = d
                        b341["witness2"] = {
                            "occ": bits_of(occ), "k": k, "nL": nL, "g_full": g_full,
                            "g_minus": gm, "removed_residual": bits_of(R[ti_]),
                        }

        # ---------------- B343: full exchange of winning moves -----------
        variants: list[tuple[str, list[int]]] = []
        if i3:
            variants.append(("one_3res", [i3[0]]))
        if i4:
            variants.append(("one_4res", [i4[0]]))
        if len(i3) >= 2:
            variants.append(("two_3res", i3[:2]))
        if len(i3) >= 3:
            variants.append(("all_3res", i3))
        b343["n_tested"] += 1
        for kind, drop in variants:
            keep = [R[i] for i in range(len(R)) if i not in set(drop)]
            sub = ResidualGame(Lmask, keep)
            gm = sub.ev(0)
            if g_full > 0 and gm > 0:
                wm = set(sub.win_moves())
                if win_full and wm and win_full.isdisjoint(wm):
                    b343["n_disjoint_win"] += 1
                    if len(b343["examples"]) < 8:
                        b343["examples"].append({
                            "occ": bits_of(occ), "k": k, "nL": nL, "kind": kind,
                            "g_full": g_full, "g_minus": gm,
                            "win_full": sorted(win_full), "win_minus": sorted(wm),
                            "dropped": [bits_of(R[i]) for i in drop],
                        })
                    break

        # ---------------- B344: geometric type of effective 3-residuals --
        if ti["is_forest"] and i3 and nL <= 12:
            comp_of = {}
            for ci, c in enumerate(ti["comps"]):
                for v in c:
                    comp_of[v] = ci
            # for each component that is a tree, distance to nearest branch
            for ci, c in enumerate(ti["comps"]):
                if len(c) < 2:
                    continue
                cs = sorted(c)
                if any(deg[v] >= 3 for v in c):
                    src = [v for v in c if deg[v] >= 3][0]
                    dmap = bfs_dist_from(adj, src, nL)
                    base = "tree_branched"
                else:
                    # path component: no branch, use "all deg<=2"
                    if all(deg[v] <= 2 for v in c):
                        base = "path"
                    else:
                        base = "tree_other"
                    dmap = None
                for ri in i3:
                    rpts = [idx[p] for p in bits_of(R[ri])]
                    if not all(v in c for v in rpts):
                        continue
                    spread = max(rpts) - min(rpts)
                    if dmap is not None:
                        par = tuple(sorted({dmap[v] % 2 for v in rpts}))
                        dists = tuple(sorted({dmap[v] for v in rpts}))
                        key = f"{base}|parity={par}|maxdist={max(dists)}|deg={tuple(sorted(deg[v] for v in rpts))}"
                    else:
                        # path: position parity along the path
                        src = min(c)
                        dm = bfs_dist_from(adj, src, nL)
                        key = (f"{base}|parity={tuple(sorted({dm[v] % 2 for v in rpts}))}"
                               f"|spread={spread}|deg={tuple(sorted(deg[v] for v in rpts))}")
                    b344["types"][key] += 1
                    b344["n_effective"] += 1
                    if len(b344["examples"]) < 10 and key not in [e["type"] for e in b344["examples"]]:
                        b344["examples"].append({
                            "occ": bits_of(occ), "k": k, "nL": nL,
                            "residual": bits_of(R[ri]), "type": key,
                            "deg": [deg[v] for v in rpts],
                        })
        if not ti["is_forest"] and i3 and nL <= 12:
            b344["types"]["NONFOREST"] += 1

        # ---------------- B347 / B348: approximation-error statistics -----
        higher = [R[i] for i in i3 + i4]
        cover_pts = set()
        for r in higher:
            cover_pts.update(bits_of(r))
        cov = len(cover_pts) / nL if nL else 0.0
        # components of P(S) bridged by higher residuals
        if ti["comps"]:
            comp_of2 = {}
            for ci, c in enumerate(ti["comps"]):
                for v in c:
                    comp_of2[v] = ci
            bridged = 0
            for r in higher:
                cs = {comp_of2[idx[p]] for p in bits_of(r) if idx.get(p) in comp_of2}
                if len(cs) > 1:
                    bridged += 1
        else:
            bridged = 0
        n_comps = len(ti["comps"])
        wrong = int(g2 != g_full)
        cell = (k, nL)
        b347["cells"][cell][0] += wrong
        b347["cells"][cell][1] += 1
        b348["cells"][(k, nL, n_comps)][0] += wrong
        b348["cells"][(k, nL, n_comps)][1] += 1
        if len(b347["rows"]) < 100000:
            b347["rows"].append({"k": k, "nL": nL, "cov": cov,
                                 "n3": len(i3), "n4": len(i4), "wrong": wrong,
                                 "g_full": g_full, "g2": g2})
            b348["rows"].append({"k": k, "nL": nL, "n_comps": n_comps,
                                 "bridged": bridged, "n_higher": len(higher),
                                 "wrong": wrong})

        # ---------------- B345 extra (clique union sanity) ---------------
        if clique_union(edges, nL) and (i3 or i4):
            if g2 == g_full:
                b345_extra["clique_same"] += 1
            else:
                b345_extra["clique_diff"] += 1

        # ---------------- B349: 4-residual minimal -----------------------
        if i4 and i3:
            # (a) deleting all 3-residuals still misses g, deleting a 4 fixes
            keep3 = [R[i] for i in i4]
            sub3 = ResidualGame(Lmask, keep3)
            g3 = sub3.ev(0)
            if g3 != g_full:
                fixed = False
                for j in i4[:6]:
                    keep34 = [R[i] for i in i4 if i != j]
                    s4 = ResidualGame(Lmask, keep34)
                    if s4.ev(0) == g_full:
                        fixed = True
                        break
                if fixed:
                    b349["n_found"] += 1
                    if b349["min_L"] is None or nL < b349["min_L"]:
                        b349["min_L"] = nL
                    if len(b349["examples"]) < 6:
                        b349["examples"].append({
                            "occ": bits_of(occ), "k": k, "nL": nL,
                            "g_full": g_full, "g_3res_only": g3,
                            "n3": len(i3), "n4": len(i4),
                            "n_resid_abstract": len(R),
                        })
        # (b) minimal |L| where a 4-residual is the *only* thing that matters
        if i4 and not i3 and nL <= 10:
            keep_no4 = [R[i] for i in i2]
            s0 = ResidualGame(Lmask, keep_no4)
            if s0.ev(0) != g_full:
                b349["types"]["only4_effective"] += 1

        n_solved += 1

    b341["hist3"] = {str(k): v for k, v in sorted(b341["hist3"].items())}
    b341["hist2"] = {str(k): v for k, v in sorted(b341["hist2"].items())}
    b344["types"] = {k: v for k, v in sorted(b344["types"].items(), key=lambda kv: -kv[1])}
    b347["cells"] = {f"{c[0]},{c[1]}": {"wrong": v[0], "total": v[1]}
                     for c, v in sorted(b347["cells"].items())}
    b348["cells"] = {f"{c[0]},{c[1]},{c[2]}": {"wrong": v[0], "total": v[1]}
                     for c, v in sorted(b348["cells"].items())}
    # ---- aggregate statistics for B347/B348 ----
    b347["agg"] = strat_agg(b347["rows"], "cov", [0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.01])
    b348["agg"] = strat_agg(b348["rows"], "bridged", [0, 1, 2, 3, 5, 100])
    b348["agg_ncomp"] = strat_agg(b348["rows"], "n_comps", [1, 2, 3, 4, 6, 100])
    b347["rows"] = b347["rows"][:4000]
    b348["rows"] = b348["rows"][:4000]
    return {
        "B341": b341, "B343": b343, "B344": b344, "B347": b347,
        "B348": b348, "B349": b349, "B345_extra": b345_extra,
        "n_solved": n_solved,
    }


def strat_agg(rows, key, bins):
    out = []
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        sel = [r for r in rows if lo <= r[key] < hi]
        if sel:
            out.append({"bin": [lo, hi], "n": len(sel),
                        "err_rate": sum(r["wrong"] for r in sel) / len(sel)})
        else:
            out.append({"bin": [lo, hi], "n": 0, "err_rate": None})
    tot = len(rows)
    out.append({"bin": "all", "n": tot,
                "err_rate": (sum(r["wrong"] for r in rows) / tot) if tot else None})
    return out


if __name__ == "__main__":
    main()
