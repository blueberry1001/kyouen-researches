#!/usr/bin/env python3
"""Round5 B101-B200 multi-job computation.

Jobs:
  b129  - 1-swap mobility: min-maximal vs max-maximal (n=4,5)
  b130  - P/N vs deformation components at k=3,4 (n=4,5)
  b157  - two-point degree matrix features vs P/N (n=4,5 k=2)
  b158  - degree vs |L| reversal search (n=4,5)
  b159  - boundary effect reach (n=4,5,6 point degrees)
  b160  - same-degree D4-inequivalent points with different outcome (n=5,6)
  b165  - mod-p determinant nonzero construction check
  b166  - single-prime safety certificate failure
  b167  - small prime set covering all quad dets
  b133  - circle hierarchy by center denominator
  b149  - similarity-type coverage extended (top-k for k=1..20)
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points, is_forbidden_quad

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "round5_b101_multi.json"


def load_maximal(n: int) -> list[int]:
    p = DATA / f"maximal_n{n}.bin"
    raw = p.read_bytes()
    cnt = len(raw) // 8
    return list(struct.unpack(f"<{cnt}Q", raw))


def load_safe(n: int) -> list[int]:
    p = DATA / f"safe_n{n}.bin"
    raw = p.read_bytes()
    cnt = len(raw) // 8
    return list(struct.unpack(f"<{cnt}Q", raw))


def points_of(n: int, mask: int) -> list[tuple[int, int]]:
    pts = []
    for i in range(n * n):
        if mask >> i & 1:
            pts.append((i % n, i // n))
    return pts


def job_b129(n: int) -> dict:
    """1-swap mobility: for each maximal set S, count p in S, q not in S
    with S-p+q maximal. Compare min-size vs max-size maximal sets."""
    maximal = load_maximal(n)
    sizes = [bin(m).count("1") for m in maximal]
    smin, smax = min(sizes), max(sizes)
    board = Board(square_points(n))
    # Build set of maximal masks for O(1) lookup
    mset = set(maximal)

    def swap_count(mask: int) -> int:
        """Count 1-swap neighbors that are also maximal."""
        c = 0
        occupied = [i for i in range(n * n) if mask >> i & 1]
        empty = [i for i in range(n * n) if not (mask >> i & 1)]
        for p in occupied:
            base = mask ^ (1 << p)
            for q in empty:
                if base | (1 << q) in mset:
                    c += 1
        return c

    # Sample: for min-size, take all if few, else first 50
    min_sets = [m for m, s in zip(maximal, sizes) if s == smin]
    max_sets = [m for m, s in zip(maximal, sizes) if s == smax]
    # For n=5 max sets=100, min sets=4; for n=4 min=176 max=64
    # Compute all for min, all for max if <=100 else sample 50
    min_sample = min_sets if len(min_sets) <= 100 else min_sets[:50]
    max_sample = max_sets if len(max_sets) <= 100 else max_sets[:50]
    min_swaps = [swap_count(m) for m in min_sample]
    max_swaps = [swap_count(m) for m in max_sample]
    return {
        "n": n,
        "n_maximal": len(maximal),
        "smin": smin,
        "smax": smax,
        "n_min_sets": len(min_sets),
        "n_max_sets": len(max_sets),
        "min_swap_total": sum(min_swaps),
        "min_swap_mean": sum(min_swaps) / max(1, len(min_swaps)),
        "min_swap_norm": (sum(min_swaps) / max(1, len(min_swaps))) / smin,
        "max_swap_total": sum(max_swaps),
        "max_swap_mean": sum(max_swaps) / max(1, len(max_swaps)),
        "max_swap_norm": (sum(max_swaps) / max(1, len(max_swaps))) / smax,
        "min_sample_size": len(min_sample),
        "max_sample_size": len(max_sample),
    }


def job_b130(n: int, k: int) -> dict:
    """At layer k, build 1-point-swap graph components and check if P/N
    is constant on each component."""
    board = Board(square_points(n))
    V = n * n
    # Enumerate all safe k-sets
    safe_k = []
    for mask in range(1 << V):
        if bin(mask).count("1") != k:
            continue
        if board.is_safe(mask):
            safe_k.append(mask)
    # Build adjacency: 1-point swap (remove one, add one)
    index = {m: i for i, m in enumerate(safe_k)}
    parent = list(range(len(safe_k)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for m in safe_k:
        occupied = [i for i in range(V) if m >> i & 1]
        empty = [i for i in range(V) if not (m >> i & 1)]
        for p in occupied:
            base = m ^ (1 << p)
            for q in empty:
                nb = base | (1 << q)
                if nb in index:
                    union(index[m], index[nb])

    # Compute P/N for each safe k-set using Grundy of the full game from that state
    # g(S) = mex of g(S+p) for legal p; P iff g=0
    # For small n,k this is feasible via memoized recursion
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def grundy(mask: int) -> int:
        moves = []
        empty = board.full ^ mask
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                if board.is_safe(mask | bit):
                    moves.append(grundy(mask | bit))
            empty >>= 1
            v += 1
        if not moves:
            return 0
        s = set(moves)
        g = 0
        while g in s:
            g += 1
        return g

    # Component-wise P/N
    comp_pn = defaultdict(set)
    comp_size = Counter()
    for m in safe_k:
        g = grundy(m)
        r = find(index[m])
        comp_pn[r].add(g == 0)
        comp_size[r] += 1

    mixed = sum(1 for s in comp_pn.values() if len(s) > 1)
    pure = sum(1 for s in comp_pn.values() if len(s) == 1)
    return {
        "n": n,
        "k": k,
        "n_safe_k": len(safe_k),
        "n_components": len(comp_size),
        "n_pure_components": pure,
        "n_mixed_components": mixed,
        "largest_component": max(comp_size.values()) if comp_size else 0,
        "grundy_lru_info": grundy.cache_info()._asdict(),
    }


def job_b157_b158_b160(n: int) -> dict:
    """Degree features and game outcomes for 1-stone and 2-stone positions."""
    board = Board(square_points(n))
    V = n * n
    # Point degree d(p) = number of forbidden quads containing p
    deg = [0] * V
    for q in board.quads:
        for i in range(V):
            if q >> i & 1:
                deg[i] += 1

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def grundy(mask: int) -> int:
        moves = []
        empty = board.full ^ mask
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                if board.is_safe(mask | bit):
                    moves.append(grundy(mask | bit))
            empty >>= 1
            v += 1
        if not moves:
            return 0
        s = set(moves)
        g = 0
        while g in s:
            g += 1
        return g

    # B160: same-degree D4-inequivalent points with different first-move outcome
    # D4 action on (x,y) in [0,n-1]^2
    def d4_orbit(x, y):
        n1 = n - 1
        cands = [
            (x, y), (y, n1 - x), (n1 - x, n1 - y), (n1 - y, x),
            (n1 - x, y), (n1 - y, n1 - x), (x, n1 - y), (y, x),
        ]
        return set(cands)

    # Classify points by (degree, D4-orbit-rep)
    pt_info = []
    for i in range(V):
        x, y = i % n, i // n
        g = grundy(1 << i)
        pt_info.append({"i": i, "xy": (x, y), "deg": deg[i], "g": g, "pn": "P" if g == 0 else "N"})

    # Group by degree
    by_deg = defaultdict(list)
    for p in pt_info:
        by_deg[p["deg"]].append(p)

    b160_witness = None
    for d, pts in by_deg.items():
        # Check if any two D4-inequivalent points have different g
        seen_orbits = []
        for p in pts:
            orb = d4_orbit(*p["xy"])
            placed = False
            for orb2, g2 in seen_orbits:
                if orb == orb2:
                    if g2 != p["g"] and b160_witness is None:
                        b160_witness = {
                            "deg": d,
                            "p1": p["xy"], "g1": p["g"],
                            "p2_xy_in_orbit": list(orb)[:2],
                        }
                    placed = True
                    break
            if not placed:
                seen_orbits.append((orb, p["g"]))
        # Different orbits with same degree but different g
        orbit_gs = {}
        for p in pts:
            orb = frozenset(d4_orbit(*p["xy"]))
            orbit_gs.setdefault(orb, set()).add(p["g"])
        g_vals = set()
        for gs in orbit_gs.values():
            g_vals |= gs
        if len(g_vals) > 1 and b160_witness is None:
            # find two points with same degree, different orbits, different g
            pts_by_orbit = defaultdict(list)
            for p in pts:
                pts_by_orbit[frozenset(d4_orbit(*p["xy"]))].append(p)
            orbits = list(pts_by_orbit.keys())
            for o1, o2 in combinations(orbits, 2):
                g1 = pts_by_orbit[o1][0]["g"]
                g2 = pts_by_orbit[o2][0]["g"]
                if g1 != g2:
                    b160_witness = {
                        "deg": d,
                        "p1": pts_by_orbit[o1][0]["xy"], "g1": g1,
                        "p2": pts_by_orbit[o2][0]["xy"], "g2": g2,
                    }
                    break

    # B158: high-degree point gives fewer legal moves than low-degree
    # For empty board, compare |L({p})| vs deg(p)
    L_sizes = []
    for i in range(V):
        mask = 1 << i
        # count legal moves from this 1-stone position
        legal = 0
        empty = board.full ^ mask
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                if board.is_safe(mask | bit):
                    legal += 1
            empty >>= 1
            v += 1
        L_sizes.append(legal)

    # Check reversal: deg(p) > deg(q) but L(p) > L(q)
    reversal_found = None
    max_reversal = 0
    for i in range(V):
        for j in range(V):
            if deg[i] > deg[j] and L_sizes[i] > L_sizes[j]:
                gap = L_sizes[i] - L_sizes[j]
                if gap > max_reversal:
                    max_reversal = gap
                    reversal_found = {
                        "p": (i % n, i // n), "deg_p": deg[i], "L_p": L_sizes[i],
                        "q": (j % n, j // n), "deg_q": deg[j], "L_q": L_sizes[j],
                    }
            if deg[i] < deg[j] and L_sizes[i] > L_sizes[j]:
                pass  # same as above, symmetric

    # Also check inverse: high deg -> more L (hypothesis direction)
    # B158 claims: d(p)>d(q) but |L(S+p)|>|L(S+q)| (reversal of "high degree -> constrained")
    # Actually re-read: "高次数点を置くと合法手がより多く残る" = placing high-degree point
    # leaves MORE legal moves. So the claim is d(p)>d(q) implies |L(S+p)|>|L(S+q)| sometimes.
    # And "その逆転が最大次数点と最小次数点の間でも起こる"
    claim_witness = None
    for i in range(V):
        for j in range(V):
            if deg[i] > deg[j] and L_sizes[i] > L_sizes[j]:
                claim_witness = {
                    "p": (i % n, i // n), "deg_p": deg[i], "L_p": L_sizes[i],
                    "q": (j % n, j // n), "deg_q": deg[j], "L_q": L_sizes[j],
                }
                break
        if claim_witness:
            break

    # B159: boundary effect - compare degree of boundary vs interior
    # and how degree changes with n (do it as radial profile)
    rad_prof = defaultdict(list)
    for i in range(V):
        x, y = i % n, i // n
        cx, cy = (n - 1) / 2, (n - 1) / 2
        r2 = (x - cx) ** 2 + (y - cy) ** 2
        rad_prof[r2].append(deg[i])

    return {
        "n": n,
        "deg_min": min(deg), "deg_max": max(deg), "deg_mean": sum(deg) / V,
        "deg_hist": dict(Counter(deg)),
        "L_min": min(L_sizes), "L_max": max(L_sizes),
        "b160_witness": b160_witness,
        "b158_reversal": reversal_found,
        "b158_max_reversal_gap": max_reversal,
        "b158_claim_witness": claim_witness,
        "b159_radial": {str(k): {"min": min(v), "max": max(v), "mean": sum(v)/len(v), "n": len(v)}
                        for k, v in sorted(rad_prof.items())},
        "first_move_g": {str(p["xy"]): p["g"] for p in pt_info},
    }


def job_b165_b166_b167(n: int) -> dict:
    """mod-p determinant analysis on maximal safe sets."""
    maximal = load_maximal(n)
    board = Board(square_points(n))
    V = n * n

    # For each maximal set S, compute all 4-point dets (which are nonzero since safe)
    # Then check mod p = 0 for small primes
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]

    # B166: exists safe S such that for every p in range, some det is 0 mod p
    # B167: min size of prime set P such that for every quad det in S, some p in P has det != 0 mod p

    # Sample: take all max-size maximal sets, or up to 100
    sizes = [bin(m).count("1") for m in maximal]
    smax = max(sizes)
    max_sets = [m for m, s in zip(maximal, sizes) if s == smax]
    sample = max_sets if len(max_sets) <= 80 else max_sets[:80]

    b166_witness = None
    b167_stats = []
    prime_hit_counts = {p: 0 for p in primes}  # how many quads are nonzero mod p

    for mask in sample:
        pts_idx = [i for i in range(V) if mask >> i & 1]
        pts = [(i % n, i // n) for i in pts_idx]
        # All 4-subsets have nonzero det (safe set)
        dets = []
        for ids in combinations(range(len(pts)), 4):
            rows = [(pts[j][0]**2 + pts[j][1]**2, pts[j][0], pts[j][1], 1) for j in ids]
            d = det4(*rows)
            assert d != 0
            dets.append(d)

        # B167: for each det, find primes where it's nonzero
        covering_primes = set()
        for d in dets:
            for p in primes:
                if d % p != 0:
                    covering_primes.add(p)
        b167_stats.append(len(covering_primes))

        # B166: check if some single prime certifies all dets (all nonzero mod p)
        for p in primes:
            if all(d % p != 0 for d in dets):
                prime_hit_counts[p] += 1
                break

    # B165: can we construct a linear-size safe set via mod-p nonzero?
    # Simple test: points (i, i^2 mod p) on a p x p board, check safety
    b165_trials = {}
    for p in [3, 5, 7]:
        # Try the parabola construction: {(i, i^2 mod p) : i in 0..p-1}
        # But we need integer board. Try on a board of side >= p.
        side = max(n, p)
        # Actually let's just check: on board of side p, is the set of p points
        # {(i, i^2 % p)} safe? The det condition mod p...
        pts = [(i, (i * i) % p) for i in range(p)]
        # Check if any 4 are concyclic/collinear (integer det = 0)
        safe = True
        for ids in combinations(range(p), 4):
            rows = [(pts[j][0]**2 + pts[j][1]**2, pts[j][0], pts[j][1], 1) for j in ids]
            if det4(*rows) == 0:
                safe = False
                break
        b165_trials[f"parabola_p{p}"] = {"points": pts, "safe": safe}

    return {
        "n": n,
        "n_sample": len(sample),
        "n_max_sets": len(max_sets),
        "b166_prime_coverage": prime_hit_counts,
        "b166_witness": b166_witness,
        "b167_covering_set_sizes": {
            "min": min(b167_stats) if b167_stats else None,
            "max": max(b167_stats) if b167_stats else None,
            "mean": sum(b167_stats) / max(1, len(b167_stats)),
            "hist": dict(Counter(b167_stats)),
        },
        "b165_trials": b165_trials,
    }


def job_b133(n_max: int = 8) -> dict:
    """Circle hierarchy by center denominator q."""
    results = {}
    for n in range(2, n_max + 1):
        pts = square_points(n)
        # Enumerate all circles through >=3 points via circumcircles of triangles
        seen = set()
        by_q = Counter()
        max_pts_by_q = defaultdict(int)
        for tri in combinations(range(len(pts)), 3):
            p0, p1, p2 = pts[tri[0]], pts[tri[1]], pts[tri[2]]
            # Circumcenter as rational
            ax, ay = p0
            bx, by = p1
            cx, cy = p2
            d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
            if d == 0:
                continue  # collinear
            ux_num = ((ax*ax+ay*ay) * (by-cy) + (bx*bx+by*by) * (cy-ay) + (cx*cx+cy*cy) * (ay-by))
            uy_num = ((ax*ax+ay*ay) * (cx-bx) + (bx*bx+by*by) * (ax-cx) + (cx*cx+cy*cy) * (bx-ax))
            # center = (ux_num/d, uy_num/d)
            from math import gcd
            g1 = gcd(abs(ux_num), abs(d))
            g2 = gcd(abs(uy_num), abs(d))
            # denominator of center: d / gcd(ux_num, d) for x, etc.
            # A common denominator is d / gcd(d, ux_num, uy_num)... actually
            # the denom of the reduced fraction ux_num/d is d/gcd(ux_num,d)
            dx = abs(d) // g1 if g1 else abs(d)
            dy = abs(d) // g2 if g2 else abs(d)
            # The "center denominator" q = lcm of the two denoms, or just |d|/gcd(|d|,|ux|,|uy|)
            g_all = gcd(gcd(abs(ux_num), abs(uy_num)), abs(d))
            q = abs(d) // g_all if g_all else abs(d)
            key = (ux_num, uy_num, d)
            if key in seen:
                continue
            seen.add(key)
            # Count lattice points on this circle
            # r^2 = ((ax*d-ux)^2 + (ay*d-uy)^2) / d^2
            # point (x,y) on circle iff (x*d-ux)^2 + (y*d-uy)^2 == r2_num
            r2_num = (ax * d - ux_num)**2 + (ay * d - uy_num)**2
            cnt = 0
            for (x, y) in pts:
                if (x * d - ux_num)**2 + (y * d - uy_num)**2 == r2_num:
                    cnt += 1
            if cnt >= 3:
                by_q[q] += 1
                max_pts_by_q[q] = max(max_pts_by_q[q], cnt)

        results[n] = {
            "n_circles_ge3": sum(by_q.values()),
            "by_q_count": dict(sorted(by_q.items())),
            "max_pts_by_q": dict(sorted(max_pts_by_q.items())),
            "global_max_pts": max(max_pts_by_q.values()) if max_pts_by_q else 0,
            "q_at_max": [q for q, m in max_pts_by_q.items() if m == (max(max_pts_by_q.values()) if max_pts_by_q else 0)],
        }
    return results


def job_b177(n: int = 4) -> dict:
    """Search for two subboards (point subsets) with same f-vector but different
    empty-board game outcome / nimber."""
    board = Board(square_points(n))
    V = n * n
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def grundy(mask: int) -> int:
        moves = []
        empty = board.full ^ mask
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                if board.is_safe(mask | bit):
                    moves.append(grundy(mask | bit))
            empty >>= 1
            v += 1
        if not moves:
            return 0
        s = set(moves)
        g = 0
        while g in s:
            g += 1
        return g

    # For subboards, we need to restrict to a subset of points.
    # f-vector = number of safe k-sets for each k, on the subboard.
    # Sample: take subboards of size V-1 (remove one point) and V-2.
    # Compare f-vectors and game values.

    def f_vector_and_g(keep_mask: int) -> tuple:
        """f-vector of safe subsets of the kept points, and grundy of empty on subboard."""
        kept = [i for i in range(V) if keep_mask >> i & 1]
        # Build sub-board
        sub_pts = [(i % n, i // n) for i in kept]
        sub = Board(sub_pts)
        # f-vector
        fv = Counter()
        for m in range(1 << sub.V):
            if sub.is_safe(m):
                fv[bin(m).count("1")] += 1
        # Grundy on subboard: need to solve on sub-board
        @lru_cache(maxsize=None)
        def sg(mask: int) -> int:
            moves = []
            empty = ((1 << sub.V) - 1) ^ mask
            v = 0
            while empty:
                if empty & 1:
                    bit = 1 << v
                    if sub.is_safe(mask | bit):
                        moves.append(sg(mask | bit))
                empty >>= 1
                v += 1
            if not moves:
                return 0
            s = set(moves)
            g = 0
            while g in s:
                g += 1
            return g
        g0 = sg(0)
        return (tuple(sorted(fv.items())), g0)

    # Remove-one-point subboards
    results = []
    seen_fv = {}
    for rm in range(V):
        keep = board.full ^ (1 << rm)
        fv, g0 = f_vector_and_g(keep)
        results.append({"removed": (rm % n, rm // n), "fv": fv, "g": g0})
        if fv in seen_fv:
            prev = seen_fv[fv]
            if prev["g"] != g0:
                return {
                    "n": n,
                    "witness": {
                        "sub1_removed": prev["removed"], "g1": prev["g"],
                        "sub2_removed": (rm % n, rm // n), "g2": g0,
                        "f_vector": str(fv)[:200],
                    },
                    "n_subboards": len(results),
                }
        else:
            seen_fv[fv] = {"removed": (rm % n, rm // n), "g": g0}

    # If no witness with remove-one, try remove-two
    n_found = 0
    for rm1, rm2 in combinations(range(V), 2):
        keep = board.full ^ (1 << rm1) ^ (1 << rm2)
        fv, g0 = f_vector_and_g(keep)
        if fv in seen_fv:
            prev = seen_fv[fv]
            if prev["g"] != g0:
                return {
                    "n": n,
                    "witness": {
                        "sub1_removed": prev["removed"], "g1": prev["g"],
                        "sub2_removed": [(rm1 % n, rm1 // n), (rm2 % n, rm2 // n)], "g2": g0,
                        "f_vector": str(fv)[:200],
                    },
                    "n_subboards": len(results) + n_found,
                }
        else:
            seen_fv[fv] = {"removed": [(rm1 % n, rm1 // n), (rm2 % n, rm2 // n)], "g": g0}
        n_found += 1

    return {
        "n": n,
        "witness": None,
        "n_subboards_examined": len(results) + n_found,
        "n_distinct_fv": len(seen_fv),
    }


def main():
    out = {}
    print("=== B129 ===")
    for n in [4, 5]:
        print(f"  n={n}...")
        out[f"b129_n{n}"] = job_b129(n)
        print(f"    {out[f'b129_n{n}']}")

    print("=== B130 ===")
    for n, k in [(4, 3), (4, 4), (5, 3), (5, 4)]:
        print(f"  n={n} k={k}...")
        out[f"b130_n{n}k{k}"] = job_b130(n, k)
        print(f"    n_safe={out[f'b130_n{n}k{k}']['n_safe_k']}, "
              f"comps={out[f'b130_n{n}k{k}']['n_components']}, "
              f"mixed={out[f'b130_n{n}k{k}']['n_mixed_components']}")

    print("=== B157/158/160 ===")
    for n in [4, 5]:
        print(f"  n={n}...")
        out[f"b157_158_160_n{n}"] = job_b157_b158_b160(n)
        r = out[f"b157_158_160_n{n}"]
        print(f"    deg[{r['deg_min']},{r['deg_max']}], "
              f"b160={r['b160_witness'] is not None}, "
              f"b158_claim={r['b158_claim_witness'] is not None}")

    print("=== B165/166/167 ===")
    for n in [4, 5]:
        print(f"  n={n}...")
        out[f"b165_166_167_n{n}"] = job_b165_b166_b167(n)
        r = out[f"b165_166_167_n{n}"]
        print(f"    b167 sizes: {r['b167_covering_set_sizes']}")
        print(f"    b165: {r['b165_trials']}")

    print("=== B133 (circles) ===")
    out["b133"] = job_b133(7)
    for n, v in out["b133"].items():
        print(f"  n={n}: max={v['global_max_pts']}, q_at_max={v['q_at_max']}, "
              f"n_circles={v['n_circles_ge3']}")

    print("=== B177 ===")
    out["b177_n4"] = job_b177(4)
    print(f"  {out['b177_n4']}")
    out["b177_n5"] = job_b177(5)
    print(f"  {out['b177_n5']}")

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
