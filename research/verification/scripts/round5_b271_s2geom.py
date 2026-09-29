#!/usr/bin/env python3
"""Stage 2a: B281/B283 Q-hypergraph collisions. Optimized.

Writes round5_b271_s2geom.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import combinations, permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import is_forbidden_quad

OUT = Path(__file__).resolve().parents[1] / "round5_b271_s2geom.json"


def collinear(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def q_signature(points):
    k = len(points)
    quads = []
    n_col = 0
    n_cyc = 0
    for ids in combinations(range(k), 4):
        pts4 = [points[i] for i in ids]
        if is_forbidden_quad(pts4):
            quads.append(ids)
            a, b, c, d = pts4
            if collinear(a, b, c) and collinear(a, b, d):
                n_col += 1
            else:
                n_cyc += 1
    return quads, n_col, n_cyc


def hypergraph_iso(q1, q2, k):
    s1 = set(q1)
    s2 = set(q2)
    if len(s1) != len(s2):
        return False
    for perm in permutations(range(k)):
        img = set(tuple(sorted(perm[v] for v in q)) for q in s1)
        if img == s2:
            return True
    return False


def are_similar(A, B):
    """Translate + uniform scale + D4 of Z^2."""
    A = list(A)
    B = list(B)
    k = len(A)
    if k != len(B):
        return False
    Bset = set(B)

    def apply_d4(p, op):
        x, y = p
        return [
            (x, y), (y, -x), (-x, -y), (-y, x),
            (y, x), (x, -y), (-x, y), (-y, -x),
        ][op]

    for i0 in range(k):
        for i1 in range(k):
            if i0 == i1:
                continue
            va = (A[i1][0] - A[i0][0], A[i1][1] - A[i0][1])
            if va == (0, 0):
                continue
            for j0 in range(k):
                for j1 in range(k):
                    if j0 == j1:
                        continue
                    vb = (B[j1][0] - B[j0][0], B[j1][1] - B[j0][1])
                    if vb == (0, 0):
                        continue
                    for op in range(8):
                        rot = apply_d4(va, op)
                        ok = True
                        s = None
                        for u, v in zip(rot, vb):
                            if u == 0:
                                if v != 0:
                                    ok = False
                                    break
                            else:
                                if v % u != 0:
                                    ok = False
                                    break
                                si = v // u
                                if si <= 0:
                                    ok = False
                                    break
                                if s is None:
                                    s = si
                                elif s != si:
                                    ok = False
                                    break
                        if not ok or s is None:
                            continue
                        img = []
                        for p in A:
                            rp = apply_d4((p[0] - A[i0][0], p[1] - A[i0][1]), op)
                            img.append((B[j0][0] + s * rp[0], B[j0][1] + s * rp[1]))
                        if set(img) == Bset:
                            return True
    return False


def search(box, k, max_pair_iso=20000):
    pts_grid = [(x, y) for y in range(box) for x in range(box)]
    subsets = list(combinations(range(box * box), k))
    # Group by cheap invariant: (nq, sorted deg, sorted col_deg, sorted cyc_deg)
    # For B283 we also need a second grouping without split.
    recs = []
    buckets_split = defaultdict(list)
    buckets_hyper = defaultdict(list)
    for idxs in subsets:
        pts = tuple(pts_grid[i] for i in idxs)
        quads, n_col, n_cyc = q_signature(pts)
        deg = [0] * k
        col_deg = [0] * k
        cyc_deg = [0] * k
        for q in quads:
            pts4 = [pts[i] for i in q]
            a, b, c, d = pts4
            is_col = collinear(a, b, c) and collinear(a, b, d)
            for v in q:
                deg[v] += 1
                if is_col:
                    col_deg[v] += 1
                else:
                    cyc_deg[v] += 1
        rec = {
            "pts": pts,
            "quads": quads,
            "n_col": n_col,
            "n_cyc": n_cyc,
            "deg": deg,
        }
        recs.append(rec)
        inv_h = (len(quads), tuple(sorted(deg)))
        inv_s = (len(quads), n_col, n_cyc, tuple(sorted(deg)), tuple(sorted(col_deg)), tuple(sorted(cyc_deg)))
        buckets_hyper[inv_h].append(len(recs) - 1)
        if len(quads) > 0:
            buckets_split[inv_s].append(len(recs) - 1)

    # B281: same hypergraph, not similar
    b281 = None
    n_iso_tests = 0
    for inv, members in buckets_hyper.items():
        if inv[0] == 0:
            continue
        if len(members) < 2:
            continue
        for ia in range(len(members)):
            for ib in range(ia + 1, len(members)):
                if n_iso_tests >= max_pair_iso:
                    break
                ra, rb = recs[members[ia]], recs[members[ib]]
                n_iso_tests += 1
                if not hypergraph_iso(ra["quads"], rb["quads"], k):
                    continue
                if not are_similar(ra["pts"], rb["pts"]):
                    b281 = {
                        "A": [list(p) for p in ra["pts"]],
                        "B": [list(p) for p in rb["pts"]],
                        "quads_A": ra["quads"],
                        "n_col": ra["n_col"],
                        "n_cyc": ra["n_cyc"],
                    }
                    break
            if b281:
                break
        if b281:
            break

    # B283: same hypergraph, different (n_col, n_cyc)
    b283 = None
    for inv, members in buckets_hyper.items():
        if inv[0] == 0 or len(members) < 2:
            continue
        for ia in range(len(members)):
            for ib in range(ia + 1, len(members)):
                ra, rb = recs[members[ia]], recs[members[ib]]
                if (ra["n_col"], ra["n_cyc"]) == (rb["n_col"], rb["n_cyc"]):
                    continue
                if hypergraph_iso(ra["quads"], rb["quads"], k):
                    b283 = {
                        "A": [list(p) for p in ra["pts"]],
                        "B": [list(p) for p in rb["pts"]],
                        "quads_A": ra["quads"],
                        "quads_B": rb["quads"],
                        "split_A": {"collinear": ra["n_col"], "concyclic": ra["n_cyc"]},
                        "split_B": {"collinear": rb["n_col"], "concyclic": rb["n_cyc"]},
                    }
                    break
            if b283:
                break
        if b283:
            break

    # also: different hypergraph-only? already handled
    # count nonempty Q subsets
    n_nonempty = sum(1 for r in recs if r["quads"])
    n_multi_bucket = sum(1 for inv, mem in buckets_hyper.items() if inv[0] > 0 and len(mem) > 1)

    return {
        "box": box,
        "k": k,
        "n_subsets": len(subsets),
        "n_nonempty_Q": n_nonempty,
        "n_collision_buckets": n_multi_bucket,
        "n_iso_tests": n_iso_tests,
        "B281_witness": b281,
        "B283_witness": b283,
    }


def main():
    result = {}
    print("box=3 k=5 ...", flush=True)
    result["b3k5"] = search(3, 5)
    print("  B281", result["b3k5"]["B281_witness"] is not None,
          "B283", result["b3k5"]["B283_witness"] is not None, flush=True)
    print("box=3 k=6 ...", flush=True)
    result["b3k6"] = search(3, 6)
    print("  B281", result["b3k6"]["B281_witness"] is not None,
          "B283", result["b3k6"]["B283_witness"] is not None, flush=True)
    print("box=4 k=5 ...", flush=True)
    result["b4k5"] = search(4, 5)
    print("  B281", result["b4k5"]["B281_witness"] is not None,
          "B283", result["b4k5"]["B283_witness"] is not None, flush=True)
    print("box=4 k=6 (may be slow) ...", flush=True)
    result["b4k6"] = search(4, 6, max_pair_iso=8000)
    print("  B281", result["b4k6"]["B281_witness"] is not None,
          "B283", result["b4k6"]["B283_witness"] is not None, flush=True)
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
