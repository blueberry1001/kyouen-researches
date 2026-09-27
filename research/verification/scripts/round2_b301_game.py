#!/usr/bin/env python3
"""Round2 B309-B310, B316-B320: game-theoretic analysis on n=4,5.

Outputs research/verification/round2_b301.json (section "game").
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, det4, is_forbidden_quad  # noqa: E402

OUT_JSON = Path(__file__).resolve().parent.parent / "round2_b301.json"


def load_or_empty(p: Path) -> dict:
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_merge(section: str, data: dict):
    rep = load_or_empty(OUT_JSON)
    rep[section] = data
    OUT_JSON.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"saved section {section}", flush=True)


def compute_outcomes_and_grundy(board: Board):
    import sys as _sys
    _sys.setrecursionlimit(200000)
    g: dict[int, int] = {}
    out: dict[int, int] = {}

    def ev(occ: int) -> int:
        if occ in g:
            return g[occ]
        mv = board.legal_moves(occ)
        if not mv:
            g[occ] = 0
            out[occ] = 0
            return 0
        seen = set()
        win = False
        for u in mv:
            cg = ev(occ | (1 << u))
            seen.add(cg)
            if cg == 0:
                win = True
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        out[occ] = 1 if win else 0
        return x

    ev(0)
    return g, out


def compute_tstar(board: Board, g: dict, occ: int) -> frozenset:
    """N: only to P children; P: any legal move."""
    memo: dict[int, frozenset] = {}

    def T(o: int) -> frozenset:
        if o in memo:
            return memo[o]
        mv = board.legal_moves(o)
        if not mv:
            memo[o] = frozenset({o.bit_count()})
            return memo[o]
        acc = set()
        if g[o] == 0:
            for u in mv:
                acc |= T(o | (1 << u))
        else:
            for u in mv:
                ch = o | (1 << u)
                if g[ch] == 0:
                    acc |= T(ch)
        if not acc:
            for u in mv:
                acc |= T(o | (1 << u))
        memo[o] = frozenset(acc)
        return memo[o]

    return T(occ)


def compute_wft(board: Board, g: dict, occ: int) -> frozenset:
    """Winner forces exactly t. N: union over winning moves; P: intersection over all moves."""
    memo: dict[int, frozenset] = {}

    def W(o: int) -> frozenset:
        if o in memo:
            return memo[o]
        mv = board.legal_moves(o)
        if not mv:
            memo[o] = frozenset({o.bit_count()})
            return memo[o]
        if g[o] == 0:
            acc = None
            for u in mv:
                s = W(o | (1 << u))
                acc = s if acc is None else (acc & s)
                if not acc:
                    break
            memo[o] = frozenset(acc or set())
        else:
            acc_set = set()
            for u in mv:
                ch = o | (1 << u)
                if g[ch] == 0:
                    acc_set |= W(ch)
            memo[o] = frozenset(acc_set)
        return memo[o]

    return W(occ)


# ---------------- B309 / B316 on n=5 ----------------
def b309_b316():
    print("n=5 solve grundy ...", flush=True)
    b5 = board_square(5)
    g5, _ = compute_outcomes_and_grundy(b5)
    print(f"  states={len(g5)}", flush=True)

    # two-stone P-positions
    two_P = []
    two_all = {}
    for a, b in combinations(range(25), 2):
        m = (1 << a) | (1 << b)
        gv = g5[m]
        two_all[(a, b)] = gv
        if gv == 0:
            two_P.append((a, b))

    # one-stone g and degree in J_5
    one = {v: g5[1 << v] for v in range(25)}
    adj = defaultdict(set)
    for a, b in two_P:
        adj[a].add(b)
        adj[b].add(a)
    deg = {v: len(adj[v]) for v in range(25)}

    # D4 orbits of losing first moves (noniso)
    noniso = [v for v in range(25) if adj[v]]
    def d4_maps(n):
        def pt(x, y):
            return y * n + x
        def inv(i):
            return i % n, i // n
        fs = [
            lambda x, y: (x, y),
            lambda x, y: (y, n - 1 - x),
            lambda x, y: (n - 1 - x, n - 1 - y),
            lambda x, y: (n - 1 - y, x),
            lambda x, y: (n - 1 - x, y),
            lambda x, y: (x, n - 1 - y),
            lambda x, y: (y, x),
            lambda x, y: (n - 1 - y, n - 1 - x),
        ]
        return [lambda i, f=f: pt(*f(*inv(i))) for f in fs]

    maps = d4_maps(5)
    remaining = set(noniso)
    orbits = []
    while remaining:
        v = remaining.pop()
        orb = {mp(v) for mp in maps}
        # keep only noniso images
        orb &= set(noniso) | {v}
        orb = {mp(v) for mp in maps} & set(noniso)
        orb.add(v)
        remaining -= orb
        orbits.append(sorted(orb))

    print(f"  two-P={len(two_P)} losing-first orbits={[len(o) for o in orbits]}", flush=True)

    # WFT and T* for each 2-stone P-position
    recs = []
    for a, b in two_P:
        m = (1 << a) | (1 << b)
        wft = sorted(compute_wft(b5, g5, m))
        tstar = sorted(compute_tstar(b5, g5, m))
        recs.append({
            "pair": [a, b],
            "coords": [(a % 5, a // 5), (b % 5, b // 5)],
            "deg_a": deg[a],
            "deg_b": deg[b],
            "wft": wft,
            "tstar": tstar,
            "g_children_3": None,  # filled later if needed
        })
        print(f"  pair {a},{b} WFT={wft} T*={tstar}", flush=True)

    # B309: from same first move, two edges both winning, WFT differ
    by_first = defaultdict(list)
    for r in recs:
        a, b = r["pair"]
        by_first[a].append(r)
        by_first[b].append(r)
    b309_witnesses = []
    for p, lst in by_first.items():
        wfts = set(tuple(r["wft"]) for r in lst)
        if len(lst) >= 2 and len(wfts) >= 2:
            b309_witnesses.append({
                "first_move": p,
                "coords": (p % 5, p // 5),
                "deg": deg[p],
                "edges": [{"partner": r["pair"][1] if r["pair"][0] == p else r["pair"][0],
                           "wft": r["wft"], "tstar": r["tstar"]} for r in lst],
                "distinct_wft": [list(w) for w in wfts],
            })
    b309 = {
        "n": 5,
        "num_two_stone_P": len(two_P),
        "first_moves_with_multiple_edges": {p: len(lst) for p, lst in by_first.items() if len(lst) >= 2},
        "wft_split_witnesses": b309_witnesses,
        "exists_split": len(b309_witnesses) > 0,
    }

    # B316: within same orbit size, high-degree points' 2-P children have
    # |T* types| > min(WFT values)?  Compare WFT-min vs |distinct T*| across
    # high-deg vs low-deg first moves.
    # Group first moves by D4 orbit (orbit size) and by degree.
    orbit_of = {}
    for oi, o in enumerate(orbits):
        for v in o:
            orbit_of[v] = oi

    groups = []  # per first-move: deg, orbit_size, list of (wft, tstar) of its P-children
    for p, lst in by_first.items():
        tstar_types = set(tuple(r["tstar"]) for r in lst)
        wft_mins = [min(r["wft"]) if r["wft"] else None for r in lst]
        wft_sets = [tuple(r["wft"]) for r in lst]
        valid_mins = [w for w in wft_mins if w is not None]
        groups.append({
            "point": p,
            "deg": deg[p],
            "orbit_size": len(orbits[orbit_of[p]]),
            "num_P_children": len(lst),
            "num_tstar_types": len(tstar_types),
            "tstar_types": [list(t) for t in tstar_types],
            "wft_sets": [list(w) for w in wft_sets],
            "wft_min_over_children": min(valid_mins) if valid_mins else None,
            "min_wft_size": min(len(r["wft"]) for r in lst) if lst else None,
            "num_empty_wft": sum(1 for r in lst if not r["wft"]),
        })

    # Statistical: among same orbit_size, is high-deg associated with larger num_tstar_types
    # relative to min WFT cardinality?
    # Hypothesis wording: "WFTの最小値よりT*の集合の種類数が大きい"
    # interpret as: |distinct T*| > min{|WFT|} or |distinct T*| > min(WFT values)?
    # Use both readings.
    by_orbit = defaultdict(list)
    for gr in groups:
        by_orbit[gr["orbit_size"]].append(gr)
    stat = {}
    for osz, lst in by_orbit.items():
        lst2 = sorted(lst, key=lambda z: z["deg"])
        stat[osz] = {
            "points": [(z["point"], z["deg"], z["num_tstar_types"], z["min_wft_size"], z["wft_min_over_children"]) for z in lst2],
            "deg_range": [lst2[0]["deg"], lst2[-1]["deg"]] if lst2 else None,
        }
    # reading A: num_tstar_types > min_wft_size  (cardinality comparison)
    readingA = all(
        gr["num_tstar_types"] > (gr["min_wft_size"] or 0)
        for gr in groups if gr["num_P_children"] >= 2
    )
    # reading B: num_tstar_types > min over children of min(WFT values) — skip empty WFT
    readingB_vals = []
    for gr in groups:
        if gr["num_P_children"] < 2:
            continue
        if gr["wft_min_over_children"] is None:
            continue
        readingB_vals.append(gr["num_tstar_types"] > gr["wft_min_over_children"])
    readingB = all(readingB_vals) if readingB_vals else None
    # correlation: high deg -> larger tstar types?
    import statistics
    degs = [gr["deg"] for gr in groups]
    nts = [gr["num_tstar_types"] for gr in groups]
    b316 = {
        "groups": groups,
        "by_orbit_size": stat,
        "readingA_num_tstar_types_gt_min_wft_card": readingA,
        "readingB_num_tstar_types_gt_min_wft_value": readingB,
        "all_first_moves_have_same_num_P_children": len(set(gr["num_P_children"] for gr in groups)) == 1,
    }

    # B319: one-stone nimber kinds on n=5 (not all-losing) and n=4
    one_hist5 = defaultdict(int)
    for v, gv in one.items():
        one_hist5[gv] += 1
    # n=4
    b4 = board_square(4)
    g4, _ = compute_outcomes_and_grundy(b4)
    one4 = {v: g4[1 << v] for v in range(16)}
    one_hist4 = defaultdict(int)
    for v, gv in one4.items():
        one_hist4[gv] += 1
    b319 = {
        "n4_all_first_losing": all(v == 0 for v in one4.values()) is False,
        "n4_one_stone_hist": dict(one_hist4),
        "n4_num_kinds": len(one_hist4),
        "n5_one_stone_hist": dict(one_hist5),
        "n5_num_kinds": len(one_hist5),
        "n5_all_first_losing": all(g5[1 << v] == 0 for v in range(25)),
        "n7_n8_n10_not_computed": True,
    }

    # B320: among pairs with same (g(p), g(q)) and same L-inf/Euclidean distance,
    # P vs non-P distinguished by 3-stone child nimber histogram.
    # Collect pairs of losing first moves (or all pairs) grouped by
    # (one_g_a, one_g_b, dist) — then see if P/non-P coexist in a group,
    # and if 3-stone histograms differ.
    def dist(a, b):
        ax, ay = a % 5, a // 5
        bx, by = b % 5, b // 5
        return (ax - bx) ** 2 + (ay - by) ** 2  # squared Euclidean

    def linf(a, b):
        ax, ay = a % 5, a // 5
        bx, by = b % 5, b // 5
        return max(abs(ax - bx), abs(ay - by))

    pair_groups = defaultdict(list)
    for a, b in combinations(range(25), 2):
        key = (one[a], one[b], dist(a, b), linf(a, b))
        pair_groups[key].append((a, b))

    mixed = {k: v for k, v in pair_groups.items() if len(v) >= 2 and
             len(set(two_all[p] == 0 for p in v)) > 1}
    print(f"  B320 mixed groups: {len(mixed)}", flush=True)

    def three_hist(a, b):
        """nimber histogram of 3-stone children of {a,b}."""
        m2 = (1 << a) | (1 << b)
        hist = defaultdict(int)
        for u in range(25):
            if m2 >> u & 1:
                continue
            if u not in b5.legal_moves(m2):
                continue
            hist[g5[m2 | (1 << u)]] += 1
        return dict(sorted(hist.items()))

    b320_groups = []
    for k, v in mixed.items():
        # compute 3-stone histograms for P and non-P members
        P_mems = [p for p in v if two_all[p] == 0]
        N_mems = [p for p in v if two_all[p] != 0]
        rec = {
            "key_one_g_dist_linf": list(k),
            "P_pairs": [list(p) for p in P_mems[:4]],
            "N_pairs": [list(p) for p in N_mems[:4]],
            "num_P": len(P_mems),
            "num_N": len(N_mems),
        }
        # sample histograms
        if P_mems and N_mems:
            hp = three_hist(*P_mems[0])
            hn = three_hist(*N_mems[0])
            rec["P_3hist_sample"] = hp
            rec["N_3hist_sample"] = hn
            rec["hists_differ"] = hp != hn
            # check if a short rule exists: e.g. presence of nimber 0 among 3-children
            # or count of nimber 0
            rec["P_has_g0_child"] = 0 in hp
            rec["N_has_g0_child"] = 0 in hn
        b320_groups.append(rec)
        if len(b320_groups) >= 6:
            break

    # broader: do all P pairs have g0 in 3-hist and all non-P lack it? (or vice versa)
    # sample 30 P and 30 N
    P_all = [(a, b) for (a, b), gv in two_all.items() if gv == 0]
    N_all = [(a, b) for (a, b), gv in two_all.items() if gv != 0]
    def rule_stats(pairs):
        has0 = 0
        n = 0
        for p in pairs[:40]:
            h = three_hist(*p)
            if 0 in h:
                has0 += 1
            n += 1
        return has0, n
    p_has0, p_n = rule_stats(P_all)
    n_has0, n_n = rule_stats(N_all)

    b320 = {
        "num_mixed_key_groups": len(mixed),
        "groups": b320_groups,
        "rule_g0_among_3children": {"P_sample_has0": p_has0, "P_sample_n": p_n,
                                     "N_sample_has0": n_has0, "N_sample_n": n_n},
        "n4_note": "n=4 all pairs among 16: check separately below",
    }

    # Also n=4 quick: one-stone all g=1; pairs grouped by dist
    pair_groups4 = defaultdict(list)
    for a, b in combinations(range(16), 2):
        key = (one4[a], one4[b], (a % 4 - b % 4) ** 2 + (a // 4 - b // 4) ** 2,
               max(abs(a % 4 - b % 4), abs(a // 4 - b // 4)))
        pair_groups4[key].append((a, b))
    two_all4 = {}
    for a, b in combinations(range(16), 2):
        two_all4[(a, b)] = g4[(1 << a) | (1 << b)]
    mixed4 = {k: v for k, v in pair_groups4.items()
              if len(set(two_all4[p] == 0 for p in v)) > 1}
    b320["n4_mixed_groups"] = len(mixed4)
    b320["n4_two_g_hist"] = dict(defaultdict(int, {str(k): sum(1 for p, gv in two_all4.items() if gv == k)
                                                     for k in set(two_all4.values())}))

    return {
        "B309": b309,
        "B316": b316,
        "B319": b319,
        "B320": b320,
    }


# ---------------- B310: line-constraint sensitivity of 5-cycles ----------------
def b310():
    print("B310: classifying forbidden quads line vs circle ...", flush=True)
    n = 5
    b = board_square(n)
    pts = b.points

    def is_collinear4(p0, p1, p2, p3):
        # area of triangles: (x1-x0)(y2-y0)-(x2-x0)(y1-y0) etc — all triples collinear
        def col(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]) == 0
        return col(p0, p1, p2) and col(p0, p1, p3)

    line_quads = []
    circle_quads = []
    for q in b.quads:
        ids = [i for i in range(b.V) if q >> i & 1]
        ps = [pts[i] for i in ids]
        if is_collinear4(*ps):
            line_quads.append((tuple(ids), q))
        else:
            circle_quads.append((tuple(ids), q))
    print(f"  total quads={len(b.quads)} line={len(line_quads)} circle={len(circle_quads)}", flush=True)

    # group line quads by the line they span; then D4-orbits of lines
    # represent a line by sorted set of ALL points on that line within board
    def line_key(ids):
        ps = [pts[i] for i in ids]
        # find all board points collinear with these
        on = []
        for j, p in enumerate(pts):
            if is_collinear4(ps[0], ps[1], ps[2], p) or all(
                (ps[0][0] - p[0]) * (ps[1][1] - p[1]) == (ps[1][0] - p[0]) * (ps[0][1] - p[1])
                for _ in [0]
            ):
                # proper: all 4 collinear check with p replacing — simpler:
                pass
        # direct: p is on line through ps[0], ps[1]
        x0, y0 = ps[0]
        x1, y1 = ps[1]
        dx, dy = x1 - x0, y1 - y0
        on = []
        for j, p in enumerate(pts):
            if (p[0] - x0) * dy == (p[1] - y0) * dx:
                on.append(j)
        return tuple(sorted(on))

    line_groups = defaultdict(list)
    for ids, q in line_quads:
        line_groups[line_key(ids)].append((ids, q))
    print(f"  distinct lines with >=4 pts: {len(line_groups)}", flush=True)

    # D4 orbits of these lines
    def d4_maps(n):
        def pt(x, y):
            return y * n + x
        def inv(i):
            return i % n, i // n
        fs = [
            lambda x, y: (x, y),
            lambda x, y: (y, n - 1 - x),
            lambda x, y: (n - 1 - x, n - 1 - y),
            lambda x, y: (n - 1 - y, x),
            lambda x, y: (n - 1 - x, y),
            lambda x, y: (x, n - 1 - y),
            lambda x, y: (y, x),
            lambda x, y: (n - 1 - y, n - 1 - x),
        ]
        return [lambda i, f=f: pt(*f(*inv(i))) for f in fs]

    maps = d4_maps(n)
    remaining = set(line_groups.keys())
    line_orbits = []
    while remaining:
        lk = remaining.pop()
        orb = {lk}
        for mp in maps:
            orb.add(tuple(sorted(mp(i) for i in lk)))
        remaining -= orb
        line_orbits.append(sorted(orb))

    print(f"  D4 orbits of lines: {len(line_orbits)} sizes={[len(o) for o in line_orbits]}", flush=True)

    # Original J_5 5-cycles
    g, _ = compute_outcomes_and_grundy(b)
    edges = []
    for a, bb in combinations(range(25), 2):
        if g[(1 << a) | (1 << bb)] == 0:
            edges.append((a, bb))
    adj = defaultdict(set)
    for a, bb in edges:
        adj[a].add(bb)
        adj[bb].add(a)
    noniso = sorted([v for v in range(25) if adj[v]])

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

    cyc5 = simple_cycles(adj, noniso, 5)
    print(f"  original 5-cycles: {len(cyc5)} -> {cyc5}", flush=True)

    # For each D4 line-orbit, rebuild board without those line-forbidden quads,
    # recompute J_5, see which original 5-cycles survive.
    results = []
    for oi, orb in enumerate(line_orbits):
        # collect all forbidden quad masks belonging to lines in this orbit
        drop_quads = set()
        for lk in orb:
            for ids, q in line_groups[lk]:
                drop_quads.add(q)
        # custom board: same points, quads = all except dropped
        bmod = Board(pts, name=f"5x5-nolines-orbit{oi}")
        bmod.quads = [q for q in bmod.quads if q not in drop_quads]
        bmod.quads_by_pt = [[] for _ in range(bmod.V)]
        for q in bmod.quads:
            for i in range(bmod.V):
                if q >> i & 1:
                    bmod.quads_by_pt[i].append(q)
        g2, _ = compute_outcomes_and_grundy(bmod)
        e2 = set()
        for a, bb in combinations(range(25), 2):
            if g2[(1 << a) | (1 << bb)] == 0:
                e2.add(frozenset((a, bb)))
        # which original 5-cycles survive (all 5 edges still P-pairs)?
        surv = []
        dead = []
        for c in cyc5:
            ok = all(frozenset((c[i], c[(i + 1) % 5])) in e2 for i in range(5))
            (surv if ok else dead).append(c)
        results.append({
            "orbit_index": oi,
            "orbit_size": len(orb),
            "lines_sample": [list(lk) for lk in orb[:3]],
            "dropped_quads": len(drop_quads),
            "num_edges_mod": len(e2),
            "num_5cycles_surviving": len(surv),
            "surviving": surv,
            "dying": dead,
        })
        print(f"  orbit {oi} size={len(orb)} droppedQ={len(drop_quads)} edges={len(e2)} 5cyc surv={len(surv)} dead={len(dead)}", flush=True)

    # distinguishability: map each 5-cycle to the set of orbit-indices where it dies
    # if the death-set uniquely identifies the orbit, the sensitivity distinguishes orbits
    death_of_cycle = defaultdict(set)  # cycle -> set of orbit indices where it dies
    for r in results:
        for c in r["dying"]:
            death_of_cycle[c].add(r["orbit_index"])
    # for each orbit, the set of cycles that die under it
    death_of_orbit = {r["orbit_index"]: set(tuple(c) for c in r["dying"]) for r in results}
    # unique signature per orbit?
    sigs = {}
    for oi, s in death_of_orbit.items():
        sigs[oi] = frozenset(s)
    unique = len(set(sigs.values())) == len(sigs)
    # injective: different orbits kill different cycle-sets
    b310 = {
        "num_line_quads": len(line_quads),
        "num_circle_quads": len(circle_quads),
        "num_lines": len(line_groups),
        "num_line_D4_orbits": len(line_orbits),
        "orbit_sizes": [len(o) for o in line_orbits],
        "original_5cycles": cyc5,
        "per_orbit": results,
        "death_signature_unique_per_orbit": unique,
        "orbit_signatures": {oi: sorted(s) for oi, s in sigs.items()},
    }
    return {"B310": b310}


# ---------------- B317: fixed matching is breakable ----------------
def b317():
    print("B317: matching strategy breakability on n=4 ...", flush=True)
    b4 = board_square(4)
    g4, out4 = compute_outcomes_and_grundy(b4)
    # J_4 perfect matchings
    edges = [(a, b) for a, b in combinations(range(16), 2) if g4[(1 << a) | (1 << b)] == 0]
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    # enumerate perfect matchings
    vs = list(range(16))
    idx = {v: i for i, v in enumerate(vs)}
    nbrs = [set(idx[w] for w in adj[vs[i]]) for i in range(16)]
    pms = []

    def rec(matched, pairs):
        if len(pms) >= 20:
            return
        if matched == (1 << 16) - 1:
            pms.append(list(pairs))
            return
        for i in range(16):
            if not (matched >> i) & 1:
                break
        for j in sorted(nbrs[i]):
            if (matched >> j) & 1:
                continue
            rec(matched | (1 << i) | (1 << j), pairs + [(vs[i], vs[j])])

    rec(0, [])
    print(f"  found {len(pms)} PMs (capped)", flush=True)

    # For each PM: after first move p and response M(p), can the opponent (P1)
    # play a legal q such that M(q) is not a legal reply (occupied or illegal)?
    def legal_after(occ):
        return b4.legal_moves(occ)

    breakable = []
    for pi, pm in enumerate(pms):
        M = {}
        for a, b in pm:
            M[a] = b
            M[b] = a
        breaks = []
        for p in range(16):
            m = M[p]
            occ2 = (1 << p) | (1 << m)
            # P1 to move (this is a P-position by construction, so P1 loses with perfect play,
            # but P1 can still choose among legal moves — looking for a move that breaks pairing)
            for q in legal_after(occ2):
                mq = M[q]
                # fixed response mq fails if mq occupied or illegal
                if (occ2 >> mq) & 1:
                    breaks.append({"first": p, "response": m, "break_move": q, "fail": "occupied"})
                elif mq not in legal_after(occ2 | (1 << q)):
                    breaks.append({"first": p, "response": m, "break_move": q, "fail": "illegal",
                                   "pair_state": [p, m, q, mq]})
        breakable.append({"pm_index": pi, "num_breaks": len(breaks), "sample": breaks[:3]})
        print(f"  PM{pi} breaks={len(breaks)}", flush=True)

    all_breakable = all(r["num_breaks"] > 0 for r in breakable)
    # also: is there a PM with zero breaks (strategy never fails)?
    b317 = {
        "n": 4,
        "num_pms_examined": len(pms),
        "all_pms_breakable": all_breakable,
        "per_pm": breakable,
        "note": "after first pair (p,M(p)), opponent plays q; pairing fails if M(q) illegal/occupied",
    }
    return {"B317": b317}


def main():
    data = {}
    data.update(b309_b316())
    save_merge("game", data)
    data2 = b310()
    save_merge("b310", data2)
    data3 = b317()
    save_merge("b317", data3)
    print("done", flush=True)


if __name__ == "__main__":
    main()
