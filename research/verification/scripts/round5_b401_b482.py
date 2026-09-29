#!/usr/bin/env python3
"""Round5 B482: triangle sharing style vs nimber variety on n=5.

For each safe subset S (reachable):
  tri = number of point-triples in S that are collinear-or-cocircular with a 4th
        (i.e. number of forbidden quads Q with |Q ∩ S| = 3)  — 'almost' triangles
  Actually B482 says 三角形: in the kyouen P-graph (points = stones, edges = pairs
  that appear together in some forbidden quad? or residual graph).
  Previous work used "triangle count" on P(S) residual conflict graph.

We use the residual conflict graph G_S: vertices = legal moves (empty points),
edge (u,v) if S∪{u,v} still safe? No — the conflict graph of remaining points:
two empty points conflict if S∪{u,v} completes a forbidden quad? That's a 2-conflict.

Simpler and matching prior scripts: triangles among OCCUPIED points in the
"pair-co-occurrence in a forbidden quad" graph. For each occupied triple, if
some forbidden quad contains all three (then adding the 4th would be illegal),
that's a "triangle" (shared triple).

B482: same triangle count and |L|, compare concentration (some point in many
triangles) vs spread (triangles on distinct points) — spread should have more
nimber kinds.

Output: cells (k, tri, |L|) with n>=8 samples, compare g-variety.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

OUT = REPO_ROOT / "research" / "verification" / "round5_b401_b482.json"


def analyze(n: int) -> dict:
    t0 = time.time()
    bd = board_square(n)
    V = bd.V
    full = (1 << V) - 1
    quads = bd.quads

    # enumerate safe subsets
    levels = [[0]]
    seen = {0}
    for _ in range(V):
        nxt = set()
        for occ in levels[-1]:
            empty = full ^ occ
            v = 0
            e = empty
            while e:
                if e & 1:
                    child = occ | (1 << v)
                    if bd.is_safe(child):
                        nxt.add(child)
                e >>= 1
                v += 1
        if not nxt:
            break
        levels.append(sorted(nxt))
        seen |= nxt

    idx_of = [{s: i for i, s in enumerate(L)} for L in levels]
    children = []
    legal_cnt = []
    for k, L in enumerate(levels):
        ch, lc = [], []
        for occ in L:
            empty = full ^ occ
            kids = []
            v = 0
            e = empty
            while e:
                if e & 1:
                    child = occ | (1 << v)
                    if bd.is_safe(child):
                        kids.append(idx_of[k + 1][child])
                e >>= 1
                v += 1
            ch.append(kids)
            lc.append(len(kids))
        children.append(ch)
        legal_cnt.append(lc)

    g_of = [None] * len(levels)
    for k in range(len(levels) - 1, -1, -1):
        row = [0] * len(levels[k])
        for i in range(len(levels[k])):
            kids = children[k][i]
            if not kids:
                continue
            seen_g = 0
            for j in kids:
                seen_g |= 1 << g_of[k + 1][j]
            mex = 0
            while seen_g & (1 << mex):
                mex += 1
            row[i] = mex
        g_of[k] = row

    # For each state: triangle metrics
    # For each forbidden quad Q, if |Q∩S|=3 then those 3 occupied points form a
    # "shared triple" (triangle that misses exactly one point).
    # tri_count = number of such quads
    # concentration = max over occupied points of #triangles through that point
    # spread = if concentration*3 == tri_count (all triangles disjoint-ish) ...
    # Use: conc_score = max_pt_count / tri_count (1=fully concentrated on one pt)
    #      spread_score = mean pairwise distance among triangle points
    cells = defaultdict(lambda: {"conc_g": set(), "spread_g": set(),
                                 "conc_n": 0, "spread_n": 0,
                                 "conc_examples": [], "spread_examples": []})

    # also global correlation between conc and g among same (k,tri,L)
    for k, L in enumerate(levels):
        for i, occ in enumerate(L):
            g = g_of[k][i]
            m = legal_cnt[k][i]
            # triangles
            pt_tri = [0] * V
            tri = 0
            for q in quads:
                inter = occ & q
                if inter.bit_count() == 3:
                    tri += 1
                    e = inter
                    while e:
                        lsb = e & -e
                        pt_tri[lsb.bit_length() - 1] += 1
                        e ^= lsb
            if tri == 0:
                continue
            max_pt = max(pt_tri)
            conc_ratio = max_pt / tri  # 1.0 = all triangles share one point
            key = (k, tri, m)
            cell = cells[key]
            if conc_ratio >= 0.5:
                cell["conc_g"].add(g)
                cell["conc_n"] += 1
                if len(cell["conc_examples"]) < 2:
                    cell["conc_examples"].append({"occ": occ, "g": g, "conc": conc_ratio})
            else:
                cell["spread_g"].add(g)
                cell["spread_n"] += 1
                if len(cell["spread_examples"]) < 2:
                    cell["spread_examples"].append({"occ": occ, "g": g, "conc": conc_ratio})

    # evaluate cells with both sides >=4 samples
    valid = 0
    spread_more = conc_more = ties = 0
    details = []
    for key, cell in cells.items():
        if cell["conc_n"] >= 4 and cell["spread_n"] >= 4:
            valid += 1
            sk, ck = len(cell["spread_g"]), len(cell["conc_g"])
            if sk > ck:
                spread_more += 1
            elif ck > sk:
                conc_more += 1
            else:
                ties += 1
            if len(details) < 15:
                details.append({
                    "k": key[0], "tri": key[1], "L": key[2],
                    "conc_n": cell["conc_n"], "spread_n": cell["spread_n"],
                    "conc_g_kinds": sorted(cell["conc_g"]),
                    "spread_g_kinds": sorted(cell["spread_g"]),
                })

    # also coarse cell (k, tri) only
    coarse = defaultdict(lambda: {"conc_g": set(), "spread_g": set(),
                                  "conc_n": 0, "spread_n": 0})
    # recompute quickly from fine cells
    for (k, tri, m), cell in cells.items():
        c = coarse[(k, tri)]
        c["conc_g"] |= cell["conc_g"]
        c["spread_g"] |= cell["spread_g"]
        c["conc_n"] += cell["conc_n"]
        c["spread_n"] += cell["spread_n"]
    cvalid = cspread = cconc = ctie = 0
    cdetails = []
    for key, cell in coarse.items():
        if cell["conc_n"] >= 8 and cell["spread_n"] >= 8:
            cvalid += 1
            sk, ck = len(cell["spread_g"]), len(cell["conc_g"])
            if sk > ck:
                cspread += 1
            elif ck > sk:
                cconc += 1
            else:
                ctie += 1
            if len(cdetails) < 15:
                cdetails.append({
                    "k": key[0], "tri": key[1],
                    "conc_n": cell["conc_n"], "spread_n": cell["spread_n"],
                    "conc_g_kinds": sorted(cell["conc_g"]),
                    "spread_g_kinds": sorted(cell["spread_g"]),
                })

    return {
        "n": n,
        "F": len(quads),
        "n_states": sum(len(L) for L in levels),
        "fine_cells": {
            "n_cells_total": len(cells),
            "n_valid": valid,
            "spread_more_kinds": spread_more,
            "conc_more_kinds": conc_more,
            "ties": ties,
            "details": details,
        },
        "coarse_cells": {
            "n_valid": cvalid,
            "spread_more_kinds": cspread,
            "conc_more_kinds": cconc,
            "ties": ctie,
            "details": cdetails,
        },
        "timing_s": round(time.time() - t0, 2),
    }


def main():
    ns = [4, 5]
    if len(sys.argv) > 1:
        ns = [int(x) for x in sys.argv[1].split(",")]
    out = {}
    for n in ns:
        print(f"=== n={n} ===", flush=True)
        r = analyze(n)
        out[f"n{n}"] = r
        print(json.dumps(r, ensure_ascii=False, indent=1)[:2500], flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
