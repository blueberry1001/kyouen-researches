#!/usr/bin/env python3
"""Round2 follow-ups: B308 gamma_t exact, B316 orbit-size-matched comparison,
B320 non-trivial rule check, B301 multigraph detail, B302 cycle listing.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

OUT_JSON = Path(__file__).resolve().parent.parent / "round2_b301.json"


def load() -> dict:
    return json.loads(OUT_JSON.read_text(encoding="utf-8"))


def save(rep: dict):
    OUT_JSON.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")


def main():
    rep = load()
    print("n=5 grundy ...", flush=True)
    b5 = board_square(5)
    g5 = b5.solve_grundy()
    print(f"  states={len(g5)}", flush=True)

    # ---- B308 exact gamma_t via bit DP over subsets is 2^16=65536 — trivial ----
    edges = [(a, b) for a, b in combinations(range(25), 2) if g5[(1 << a) | (1 << b)] == 0]
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    non = sorted([v for v in range(25) if adj[v]])
    n = len(non)
    idx = {v: i for i, v in enumerate(non)}
    nbr = []
    for v in non:
        m = 0
        for w in adj[v]:
            if w in idx:
                m |= 1 << idx[w]
        nbr.append(m)
    full = (1 << n) - 1

    def covers(sel: int) -> bool:
        cov = 0
        i = 0
        m = sel
        while m:
            if m & 1:
                cov |= nbr[i]
            m >>= 1
            i += 1
        return cov == full

    # enumerate all total dominating sets of size <= 10, find minimum
    min_k = None
    min_sets = []
    for k in range(1, 11):
        found = []
        for combi in combinations(range(n), k):
            sel = 0
            for i in combi:
                sel |= 1 << i
            if covers(sel):
                found.append([non[i] for i in combi])
        if found:
            min_k = k
            min_sets = found
            break
        print(f"  k={k}: none", flush=True)
    corners = [0, 4, 20, 24]
    all_min_have_noncorner = any(any(v not in corners for v in s) for s in min_sets)
    any_min_corner_only = any(all(v in corners for v in s) for s in min_sets)
    rep["B308"] = {
        "total_domination_number": min_k,
        "num_min_sets": len(min_sets),
        "sample": min_sets[:6],
        "all_min_include_noncorner": all_min_have_noncorner,
        "any_min_is_corner_only": any_min_corner_only,
        "diagonal_pairs_total_dom": {"[0,24]": covers((1 << idx[0]) | (1 << idx[24])),
                                      "[4,20]": covers((1 << idx[4]) | (1 << idx[20]))},
    }
    print(f"B308 gamma_t={min_k} num={len(min_sets)} noncorner={all_min_have_noncorner}", flush=True)

    # ---- B301 multigraph detail ----
    # corners + paths
    path_comps = [[1, 3, 17], [5, 13, 15], [7, 21, 23], [9, 11, 19]]
    # which corners each path endpoint touches
    detours = []
    for comp in path_comps:
        ends = []
        for v in comp:
            cs = [c for c in corners if c in adj[v]]
            ends.append((v, cs))
        detours.append({"path": comp, "endpoints": ends})
    # suppress degree-2
    deg2 = [v for v in non if len(adj[v] & set(non)) == 2]
    rem = [v for v in non if v not in deg2]
    multi = defaultdict(int)
    # direct
    for u in rem:
        for w in adj[u]:
            if w in rem and w > u:
                multi[frozenset((u, w))] += 1
    # paths through deg2
    sub = {v: adj[v] & set(non) for v in non}
    visited_edge = set()
    for v in deg2:
        for u in sub[v]:
            e0 = frozenset((v, u))
            if e0 in visited_edge:
                continue
            path_edges = set()
            def walk(a, b):
                prev, cur = a, b
                path_edges.add(frozenset((prev, cur)))
                while cur in deg2:
                    nxts = sub[cur] - {prev}
                    if len(nxts) != 1:
                        break
                    nxt = next(iter(nxts))
                    path_edges.add(frozenset((cur, nxt)))
                    prev, cur = cur, nxt
                return cur
            end1 = walk(v, u)
            end2 = walk(u, v)
            for e in path_edges:
                visited_edge.add(e)
            multi[frozenset((end1, end2))] += 1
    rep["B301"]["detours"] = detours
    rep["B301"]["multigraph_detail"] = {str(sorted(k)): v for k, v in multi.items()}
    rep["B301"]["is_doubled_4cycle"] = (
        len(rem) == 4 and all(v == 2 for v in multi.values()) and len(multi) == 4
    )
    print("B301", rep["B301"]["is_doubled_4cycle"], "multi", dict(multi), flush=True)

    # ---- B302 listing of 5-cycles ----
    def simple_cycles(adj, verts, length):
        vs = set(verts)
        cycles = []
        seen = set()
        def dfs(start, path):
            if len(path) == length:
                if start in adj[path[-1]]:
                    cyc = tuple(path)
                    i = cyc.index(min(cyc))
                    canon = cyc[i:] + cyc[:i]
                    if canon not in seen:
                        seen.add(canon)
                        cycles.append(canon)
                return
            for w in sorted(adj[path[-1]]):
                if w not in vs or w in path:
                    continue
                if w < start:
                    continue
                dfs(start, path + [w])
        for s in sorted(vs):
            dfs(s, [s])
        return cycles

    cyc5 = simple_cycles(adj, non, 5)
    cyc4 = simple_cycles(adj, non, 4)
    rep["B302"]["five_cycles"] = cyc5
    rep["B302"]["four_cycles"] = cyc4
    print("B302 5cyc", cyc5, flush=True)

    # ---- B316 same-orbit-size comparison: corners (orb4,deg4) vs interior-odd (orb4,deg2) ----
    # interior odd cells: 7,11,13,17  (x+y odd, interior)
    # boundary odd: 1,3,5,9,15,19,21,23
    corners = [0, 4, 20, 24]
    interior_odd = [7, 11, 13, 17]
    boundary_odd = [1, 3, 5, 9, 15, 19, 21, 23]
    two_P = [(a, b) for a, b in combinations(range(25), 2) if g5[(1 << a) | (1 << b)] == 0]

    def wft(occ):
        memo = {}
        def W(o):
            if o in memo:
                return memo[o]
            mv = b5.legal_moves(o)
            if not mv:
                memo[o] = frozenset({o.bit_count()})
                return memo[o]
            if g5[o] == 0:
                acc = None
                for u in mv:
                    s = W(o | (1 << u))
                    acc = s if acc is None else (acc & s)
                    if not acc:
                        break
                memo[o] = frozenset(acc or set())
            else:
                accs = set()
                for u in mv:
                    ch = o | (1 << u)
                    if g5[ch] == 0:
                        accs |= W(ch)
                memo[o] = frozenset(accs)
            return memo[o]
        return W(occ)

    def tstar(occ):
        memo = {}
        def T(o):
            if o in memo:
                return memo[o]
            mv = b5.legal_moves(o)
            if not mv:
                memo[o] = frozenset({o.bit_count()})
                return memo[o]
            acc = set()
            if g5[o] == 0:
                for u in mv:
                    acc |= T(o | (1 << u))
            else:
                for u in mv:
                    ch = o | (1 << u)
                    if g5[ch] == 0:
                        acc |= T(ch)
            memo[o] = frozenset(acc)
            return memo[o]
        return T(occ)

    def analyze_points(pts):
        rows = []
        for p in pts:
            ch = []
            for a, b in two_P:
                if p == a or p == b:
                    q = b if p == a else a
                    m = (1 << a) | (1 << b)
                    ch.append({"partner": q, "wft": sorted(wft(m)), "tstar": sorted(tstar(m))})
            tstar_types = set(tuple(c["tstar"]) for c in ch)
            wft_mins = [min(c["wft"]) for c in ch if c["wft"]]
            rows.append({
                "point": p,
                "deg": len(adj[p]),
                "num_children": len(ch),
                "num_tstar_types": len(tstar_types),
                "tstar_types": [list(t) for t in tstar_types],
                "min_wft_value": min(wft_mins) if wft_mins else None,
                "min_wft_card": min(len(c["wft"]) for c in ch) if ch else None,
                "wft_by_child": [(c["partner"], c["wft"]) for c in ch],
            })
        return rows

    corners_rows = analyze_points(corners)
    interior_rows = analyze_points(interior_odd)
    boundary_rows = analyze_points(boundary_odd)
    rep.setdefault("game", {})
    rep["game"].setdefault("B316", {})
    rep["game"]["B316"]["same_orbit4_comparison"] = {
        "corners_deg4": corners_rows,
        "interior_odd_deg2": interior_rows,
        "boundary_odd_deg8": boundary_rows,
        "note": "corners and interior-odd share orbit size 4 but degrees 4 vs 2",
    }
    # reading: high-deg (corners) vs low-deg (interior) on same orbit size
    c_types = [r["num_tstar_types"] for r in corners_rows]
    i_types = [r["num_tstar_types"] for r in interior_rows]
    rep["game"]["B316"]["high_vs_low_same_orbit"] = {
        "corners_tstar_types": c_types,
        "interior_tstar_types": i_types,
        "high_has_more_tstar_types": (min(c_types) > max(i_types)) if c_types and i_types else None,
        "readingA_all_tstar_types_gt_min_wft_card": all(
            r["num_tstar_types"] > (r["min_wft_card"] or 0) for r in corners_rows + interior_rows + boundary_rows
        ),
        "readingB_all_tstar_types_gt_min_wft_value": all(
            r["num_tstar_types"] > r["min_wft_value"]
            for r in corners_rows + interior_rows + boundary_rows if r["min_wft_value"] is not None
        ),
    }
    print("B316", rep["game"]["B316"]["high_vs_low_same_orbit"], flush=True)

    # ---- B320 non-trivial rule: is "1 in 3-hist" a separator? ----
    def three_hist(a, b):
        m2 = (1 << a) | (1 << b)
        hist = defaultdict(int)
        for u in range(25):
            if m2 >> u & 1:
                continue
            if u not in b5.legal_moves(m2):
                continue
            hist[g5[m2 | (1 << u)]] += 1
        return dict(hist)

    P_all = [(a, b) for a, b in combinations(range(25), 2) if g5[(1 << a) | (1 << b)] == 0]
    N_all = [(a, b) for a, b in combinations(range(25), 2) if g5[(1 << a) | (1 << b)] != 0]
    # check features
    feats = {}
    for name, fn in [
        ("has0", lambda h: 0 in h),
        ("has1", lambda h: 1 in h),
        ("has2", lambda h: 2 in h),
        ("max_ge5", lambda h: max(h) >= 5 if h else False),
        ("n_keys_ge3", lambda h: len(h) >= 3),
    ]:
        p_yes = sum(1 for p in P_all if fn(three_hist(*p)))
        n_yes = sum(1 for p in N_all[:60] if fn(three_hist(*p)))
        feats[name] = {"P_yes": p_yes, "P_n": len(P_all), "N_yes": n_yes, "N_n": min(60, len(N_all))}
    rep["game"].setdefault("B320", {})
    rep["game"]["B320"]["feature_rules"] = feats
    print("B320 features", feats, flush=True)

    save(rep)
    print("saved", flush=True)


if __name__ == "__main__":
    main()
