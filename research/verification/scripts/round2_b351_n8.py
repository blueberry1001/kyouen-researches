#!/usr/bin/env python3
"""Round2 B371-B380: 8-stone maximal sets on 8x8.

Known witness W = [0,1,6,20,24,32,34,60].
Search additional 8-stone maximal sets (backtrack sample + random greedy),
then test structural claims on the sample.
"""
from __future__ import annotations

import json
import random
import struct
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square  # noqa: E402

DATA = ROOT / "research" / "verification" / "data"
OUT = ROOT / "research" / "verification" / "round2_b351.json"
NR = ROOT / "night-research"


def mask_ids(m: int):
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def build_triple_comp(board):
    tc = {}
    for q in board.quads:
        ids = mask_ids(q)
        for p in ids:
            t = q & ~(1 << p)
            tc.setdefault(t, []).append(p)
    return tc


def b_vector_fast(S, tc, V):
    bvec = [0] * V
    ids = mask_ids(S)
    for a, b, c in combinations(ids, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for p in tc.get(tm, ()):
            bvec[p] += 1
    return bvec


def is_safe(board, S):
    return board.is_safe(S)


def is_maximal_tc(S, tc, V):
    bvec = b_vector_fast(S, tc, V)
    for p in range(V):
        if not ((S >> p) & 1) and bvec[p] == 0:
            return False
    return True


def collinear_triples(board, S_ids):
    """Triples of S that are collinear (det4 with any 4th? use slope/det2)."""
    out = []
    for a, b, c in combinations(S_ids, 3):
        xa, ya = a % 8, a // 8
        xb, yb = b % 8, b // 8
        xc, yc = c % 8, c // 8
        det = (xb - xa) * (yc - ya) - (xc - xa) * (yb - ya)
        if det == 0:
            out.append((a, b, c))
    return out


def line_direction(triple):
    a, b, c = triple
    xa, ya = a % 8, a // 8
    xb, yb = b % 8, b // 8
    dx, dy = xb - xa, yb - ya
    g = abs(__import__("math").gcd(dx, dy)) or 1
    dx, dy = dx // g, dy // g
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return (dx, dy)


def side_touch(S_ids):
    """Which sides of 8x8 the set touches: top y=0, bottom y=7, left x=0, right x=7."""
    sides = set()
    for i in S_ids:
        x, y = i % 8, i // 8
        if y == 0:
            sides.add("T")
        if y == 7:
            sides.add("B")
        if x == 0:
            sides.add("L")
        if x == 7:
            sides.add("R")
    return sides


def corners_used(S_ids):
    corners = {0, 7, 56, 63}
    return [i for i in S_ids if i in corners]


def d4_orbit_counts(S_ids):
    """Orbit sizes under D4 for an 8x8 board. Orbit of a point is its D4 image set."""
    def orb(i):
        x, y = i % 8, i // 8
        pts = set()
        for sx, sy in ((x, y), (y, x), (7 - x, y), (x, 7 - y), (7 - x, 7 - y), (y, 7 - x), (7 - y, x), (7 - y, 7 - x)):
            pts.add(sy * 8 + sx)
        return frozenset(pts)

    orbits = {}
    for i in S_ids:
        o = orb(i)
        orbits.setdefault(o, 0)
        orbits[o] += 1
    # return sorted occupancy signature
    sig = tuple(sorted((len(o), c) for o, c in orbits.items()))
    return sig, {tuple(sorted(o)): c for o, c in orbits.items()}


def covering_lines_circles(board, tc, S_ids, V):
    """List of covering structures: each triple T of S that forbids some empty p.
    Group by the circle/line (the forbidden-quad class). Return number of distinct
    circles/lines that cover at least one empty point, and a greedy compression count.
    """
    # Each forbidden quad q with |q∩S|=3 covers its missing point.
    # Distinct circles: group quads by their 4-point set? A circle can host many points.
    # Better: two triples T1,T2 lie on same circle with p if T1∪{p} and T2∪{p} share 3 concyclic.
    # For compression: the set of empty points covered by a given circle through 3 points of S.
    # A circle through a triple T (noncollinear) is unique; collinear T has a line.
    # So each triple T defines one circle/line L(T). An empty p is covered by L(T) if T∪{p} forbidden.
    # Greedy: choose triples to cover all empty points; count min circles needed (set cover).
    empties = [p for p in range(V) if not ((sum(1 << i for i in S_ids)) >> p) & 1]
    S = sum(1 << i for i in S_ids)
    # map triple -> list of empties it covers
    trip_cov = {}
    for a, b, c in combinations(S_ids, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        ps = [p for p in tc.get(tm, ())]
        ps = [p for p in ps if not ((S >> p) & 1)]
        if ps:
            trip_cov[(a, b, c)] = ps
    need = set(empties)
    # greedy set cover
    chosen = []
    remaining = set(need)
    trips = list(trip_cov.items())
    while remaining:
        best = max(trips, key=lambda tv: len(set(tv[1]) & remaining), default=None)
        if best is None:
            break
        cover = set(best[1]) & remaining
        if not cover:
            break
        chosen.append(best[0])
        remaining -= cover
    # exact cover count via ILP-ish DFS for small
    def exact_cover(trips, remaining, depth):
        if not remaining:
            return depth
        if depth >= 12:
            return 99
        best = 99
        # pick uncovered point with fewest covering triples
        p = min(remaining, key=lambda pt: sum(1 for _, ps in trips if pt in ps))
        for t, ps in trips:
            if p in ps:
                best = min(best, exact_cover(trips, remaining - set(ps), depth + 1))
        return best

    exact = exact_cover(trips, set(need), 0)
    return {
        "n_empty": len(empties),
        "n_triples_covering": len(trip_cov),
        "greedy_circles": len(chosen),
        "exact_circles_upper": exact,
        "n_collinear_triples": len(collinear_triples(board, S_ids)),
    }


def analyze_witness(board, tc, S_ids, name):
    V = board.V
    S = sum(1 << i for i in S_ids)
    k = len(S_ids)
    assert is_safe(board, S)
    assert is_maximal_tc(S, tc, V)
    cols = collinear_triples(board, S_ids)
    dirs = [line_direction(t) for t in cols]
    sides = side_touch(S_ids)
    corners = corners_used(S_ids)
    sig, orbmap = d4_orbit_counts(S_ids)
    # B378: one-stone deletion -> number of newly legal empty points
    bvec = b_vector_fast(S, tc, V)
    empties = [p for p in range(V) if not ((S >> p) & 1)]
    del_stats = []
    for a in S_ids:
        S2 = S & ~(1 << a)
        # empty points of original that become legal: originally empty p with b_S(p)>0
        # becomes legal in S2 iff all triples of S2 that forbid p are gone
        # = all triples of S forbidding p contain a
        newly = []
        for p in empties:
            # recompute b in S2
            b2 = 0
            ids2 = mask_ids(S2)
            for x, y, z in combinations(ids2, 3):
                tm = (1 << x) | (1 << y) | (1 << z)
                if p in tc.get(tm, ()):
                    b2 += 1
                    break
            if b2 == 0:
                newly.append(p)
        del_stats.append({"removed": a, "newly_legal": newly, "count": len(newly)})
    # B376 compression
    cov = covering_lines_circles(board, tc, S_ids, V)
    return {
        "name": name,
        "S": S_ids,
        "mask": S,
        "k": k,
        "n_collinear_triples": len(cols),
        "collinear_triples": cols,
        "line_directions": dirs,
        "n_distinct_directions": len(set(dirs)),
        "sides": sorted(sides),
        "n_sides": len(sides),
        "corners_used": corners,
        "n_corners": len(corners),
        "d4_orbit_sig": sig,
        "d4_orbit_map": {",".join(map(str, k)): v for k, v in orbmap.items()},
        "deletion": del_stats,
        "n_newly_by_del": [d["count"] for d in del_stats],
        "covering": cov,
    }


def random_maximal_8(board, tc, rng):
    """Random greedy until maximal; if size==8 return, else None. Restart inside."""
    V = board.V
    for _ in range(1):
        S = 0
        order = list(range(V))
        rng.shuffle(order)
        for v in order:
            bit = 1 << v
            if not board.is_safe(S | bit):
                continue
            S |= bit
        if S.bit_count() == 8 and is_maximal_tc(S, tc, V):
            return mask_ids(S)
    return None


def backtrack_8_maximal(board, tc, limit_nodes=2_000_000):
    """DFS by id order: build safe 8-sets; prune when remaining can't cover empties.
    Yield distinct maximal 8-sets (up to limit).
    """
    V = board.V
    found = []
    nodes = 0
    quads_by = board.quads_by_pt

    def legal_ok(occ, v):
        bit = 1 << v
        for q in quads_by[v]:
            if (q & occ) == (q & ~bit):
                return False
        return True

    def dfs(start, occ, depth):
        nonlocal nodes
        nodes += 1
        if nodes > limit_nodes:
            return
        if depth == 8:
            if is_maximal_tc(occ, tc, V):
                found.append(mask_ids(occ))
            return
        for v in range(start, V):
            if legal_ok(occ, v):
                dfs(v + 1, occ | (1 << v), depth + 1)
                if nodes > limit_nodes:
                    return

    dfs(0, 0, 0)
    return found, nodes


def main():
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    board = board_square(8)
    tc = build_triple_comp(board)
    V = 64

    # 1. known witness
    W = [0, 1, 6, 20, 24, 32, 34, 60]
    wit = analyze_witness(board, tc, W, "W1_batch05")
    data["n8_witnesses"] = [wit]

    # 2. 15-stone for contrast
    w15 = json.loads((NR / "cycle6-maxsafeset-n8-15.json").read_text())
    S15 = [(int(xy[1]) * 8 + int(xy[0])) for xy in w15["witness"]]
    # not 8-stone; skip full analyze, just rho already done

    # 3. random search for more 8-stone maximal
    rng = random.Random(20260927)
    seen = {tuple(W)}
    extra = []
    trials = 8000
    hit = 0
    for i in range(trials):
        S = 0
        order = list(range(V))
        rng.shuffle(order)
        for v in order:
            bit = 1 << v
            if board.is_safe(S | bit):
                S |= bit
        if S.bit_count() == 8:
            ids = mask_ids(S)
            if is_maximal_tc(S, tc, V):
                hit += 1
                t = tuple(ids)
                if t not in seen:
                    seen.add(t)
                    extra.append(ids)
        elif S.bit_count() == 7:
            # try to see if any single extension makes 8-stone maximal
            for v in range(V):
                if (S >> v) & 1:
                    continue
                if board.is_safe(S | (1 << v)) and is_maximal_tc(S | (1 << v), tc, V):
                    ids = mask_ids(S | (1 << v))
                    hit += 1
                    t = tuple(ids)
                    if t not in seen:
                        seen.add(t)
                        extra.append(ids)
    data["n8_random_trials"] = trials
    data["n8_random_hits"] = hit
    data["n8_random_unique"] = len(extra)

    # 4. backtrack limited search
    found, nodes = backtrack_8_maximal(board, tc, limit_nodes=3_000_000)
    data["n8_backtrack_nodes"] = nodes
    data["n8_backtrack_found"] = len(found)
    for ids in found:
        t = tuple(ids)
        if t not in seen:
            seen.add(t)
            extra.append(ids)

    # analyze up to 30 sets
    analyses = [wit]
    for ids in extra[:30]:
        try:
            analyses.append(analyze_witness(board, tc, ids, f"extra_{ids}"))
        except AssertionError:
            pass
    data["n8_witnesses"] = analyses

    # summary claims
    def claim_summary(analyses):
        n = len(analyses)
        has_col = sum(1 for a in analyses if a["n_collinear_triples"] >= 1)
        has_2dir = sum(1 for a in analyses if a["n_distinct_directions"] >= 2)
        has_2sides = sum(1 for a in analyses if a["n_sides"] >= 2)
        no_corner = sum(1 for a in analyses if a["n_corners"] == 0)
        del_exactly1 = sum(1 for a in analyses if a["n_newly_by_del"].count(1) >= 1)
        cov_le12 = sum(1 for a in analyses if a["covering"]["exact_circles_upper"] <= 12)
        orsigs = {str(a["d4_orbit_sig"]) for a in analyses}
        return {
            "n": n,
            "B371_have_collinear": has_col,
            "B372_have_2dirs": has_2dir,
            "B373_touch_2sides": has_2sides,
            "B374_no_corner": no_corner,
            "B378_del_gives_exactly1": del_exactly1,
            "B376_cov_le12": cov_le12,
            "B375_distinct_orbit_sigs": len(orsigs),
            "orbit_sigs": list(orsigs)[:10],
        }

    data["n8_claim_summary"] = claim_summary(analyses)

    # B377 probe: search 7-stone safe sets with <=1 legal move (random + local)
    b7_le1 = []
    rng2 = random.Random(99)
    for i in range(20000):
        S = 0
        order = list(range(V))
        rng2.shuffle(order)
        for v in order:
            if board.is_safe(S | (1 << v)):
                S |= (1 << v)
        if S.bit_count() > 7:
            # shrink randomly to 7
            ids = mask_ids(S)
            rng2.shuffle(ids)
            S = sum(1 << x for x in ids[:7])
        if S.bit_count() == 7:
            bvec = b_vector_fast(S, tc, V)
            legal = [p for p in range(V) if not ((S >> p) & 1) and bvec[p] == 0]
            if len(legal) <= 1:
                b7_le1.append({"S": mask_ids(S), "legal": legal})
    data["b377_probe"] = {
        "trials": 20000,
        "n_le1_legal": len(b7_le1),
        "sample": b7_le1[:5],
    }

    # B379: embed W in 9x9, try remove<=2 + add to get 9-stone maximal on 9x9
    b9 = board_square(9)
    tc9 = build_triple_comp(b9)
    # embed 8x8 ids -> 9x9 ids: x,y -> y*9+x
    def embed(ids8):
        return [((i % 8) + (i // 8) * 9) for i in ids8]

    W9 = embed(W)
    S9 = sum(1 << i for i in W9)
    # is it safe on 9x9? (fewer quads restriction? 9x9 has more points so more quads)
    safe9 = b9.is_safe(S9)
    # try remove r stones, add stones to reach 9-stone maximal
    b379 = {"embed_safe": safe9, "attempts": []}
    if safe9:
        from itertools import combinations as comb

        # search: remove 0..2 of W9, then greedily/exactly add up to 9 stones
        found379 = None
        for r in range(0, 3):
            for rem in comb(W9, r):
                base = S9
                for x in rem:
                    base &= ~(1 << x)
                # add up to 9 - (8-r) stones
                need = 9 - (8 - r)
                # DFS add
                def dfs_add(start, occ, left):
                    nonlocal found379
                    if found379:
                        return
                    if left == 0:
                        if b9.is_safe(occ) and is_maximal_tc(occ, tc9, 81):
                            found379 = {"removed": list(rem), "final": mask_ids(occ)}
                        return
                    for v in range(start, 81):
                        if (occ >> v) & 1:
                            continue
                        if b9.is_safe(occ | (1 << v)):
                            dfs_add(v + 1, occ | (1 << v), left - 1)
                            if found379:
                                return

                # limited nodes
                # just try one greedy path
                occ = base
                cands = [v for v in range(81) if not ((occ >> v) & 1) and b9.is_safe(occ | (1 << v))]
                # greedy fill
                cur = occ
                added = []
                for _ in range(need):
                    moved = False
                    for v in cands:
                        if (cur >> v) & 1:
                            continue
                        if b9.is_safe(cur | (1 << v)):
                            cur |= 1 << v
                            added.append(v)
                            moved = True
                            break
                    if not moved:
                        break
                if cur.bit_count() == 9 and is_maximal_tc(cur, tc9, 81):
                    found379 = {"removed": list(rem), "added": added, "final": mask_ids(cur)}
                    break
            if found379:
                break
        b379["result"] = found379
    data["b379"] = b379

    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print("n8 done, unique", len(seen), "claim", data["n8_claim_summary"])
    print("b377", data["b377_probe"]["n_le1_legal"])
    print("b379", data["b379"])


if __name__ == "__main__":
    main()
