#!/usr/bin/env python3
"""Round5 B351-B400 follow-up: settle PARTIAL/INCONCLUSIVE via weak forms.

Reflects the 408 maximal 8-stone structure (rho=1, r_ext=1) into each
proposition and computes finite witnesses / bounds.

Integer-only geometry via kyouen_core.
Output: research/verification/round5_b351_followup.json
"""
from __future__ import annotations

import json
import math
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, det4  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
BIN = ROOT / "research" / "verification" / "round4_b371.bin"
OUT = ROOT / "research" / "verification" / "round5_b351_followup.json"
CHUNK6 = ROOT / "research" / "verification" / "round3_chunk6_cover.json"
EXCH6 = ROOT / "results" / "maxsafe_exchange_n6.csv"
EXCH7 = ROOT / "results" / "maxsafe_exchange_n7.csv"


def load_masks(path: Path):
    data = path.read_bytes()
    (count,) = struct.unpack_from("<Q", data, 0)
    return list(struct.unpack_from(f"<{count}Q", data, 8))


def mask_to_ids(mask: int, n: int = 8) -> list[int]:
    return [i for i in range(n * n) if (mask >> i) & 1]


def xy(i: int, n: int = 8):
    return i % n, i // n


def can_add_xy(b: Board, S_list, x: int, y: int) -> bool:
    row_p = (x * x + y * y, x, y, 1)
    for t in combinations(S_list, 3):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], row_p) == 0:
            return False
    return True


def is_safe_mask(b: Board, S_list) -> bool:
    S = set(S_list)
    for q in b.quads:
        if all((q >> i) & 1 for i in S_list):
            # all 4 of q in S
            pass
    # faster: check every quad
    for q in b.quads:
        bits = q
        cnt = 0
        for i in S_list:
            if (q >> i) & 1:
                cnt += 1
        if cnt == 4:
            return False
    return True


def is_safe_fast(b: Board, S_list) -> bool:
    Sset = set(S_list)
    for q in b.quads:
        if q & (q - 1) == 0:
            continue
        # count how many of q are in S
        m = q
        c = 0
        while m:
            bit = m & -m
            i = bit.bit_length() - 1
            if i in Sset:
                c += 1
                if c == 4:
                    return False
            m ^= bit
    return True


def b_S(b: Board, S_list, p: int) -> int:
    """Number of triples T of S with T u {p} forbidden."""
    row_p = b.rows[p]
    c = 0
    for t in combinations(S_list, 3):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], row_p) == 0:
            c += 1
    return c


def forbidding_triples(b: Board, S_list, p: int) -> list[tuple[int, int, int]]:
    row_p = b.rows[p]
    out = []
    for t in combinations(S_list, 3):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], row_p) == 0:
            out.append(t)
    return out


def tau_of(b: Board, S_list, p: int) -> int:
    """Min stones to remove from S so that p becomes legal.
    = transversal number of the forbidding-triple hypergraph.
    Triples are board ids (same as S_list entries)."""
    fam = forbidding_triples(b, S_list, p)
    if not fam:
        return 0
    k = len(S_list)
    for r in range(1, k + 1):
        for R in combinations(S_list, r):
            Rset = set(R)
            if all(any(i in Rset for i in t) for t in fam):
                return r
    return k


def rho_of(b: Board, S_list) -> int:
    empt = [i for i in range(b.V) if i not in set(S_list)]
    if not empt:
        return 10**9
    taus = [tau_of(b, S_list, p) for p in empt]
    return min(taus)


def bbox(xs, ys):
    return min(xs), max(xs), min(ys), max(ys)


def r_ext_of(S_list, n=8) -> int:
    xs = [i % n for i in S_list]
    ys = [i // n for i in S_list]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    for d in range(1, 32):
        for x in range(minx - d, maxx + d + 1):
            for y in range(miny - d, maxy + d + 1):
                dx = 0
                if x < minx:
                    dx = minx - x
                elif x > maxx:
                    dx = x - maxx
                dy = 0
                if y < miny:
                    dy = miny - y
                elif y > maxy:
                    dy = y - maxy
                if max(dx, dy) != d:
                    continue
                if 0 <= x < n and 0 <= y < n:
                    continue
                if can_add_xy_board(S_list, x, y):
                    return d
    return 99


def can_add_xy_board(S_list, x: int, y: int) -> bool:
    row_p = (x * x + y * y, x, y, 1)
    rows = [(i // 8 % 8 * 0 + (i % 8), (i // 8), 0, 0) for i in S_list]
    # proper rows:
    rows = []
    for i in S_list:
        xx, yy = i % 8, i // 8
        rows.append((xx * xx + yy * yy, xx, yy, 1))
    for t in combinations(range(len(S_list)), 3):
        if det4(rows[t[0]], rows[t[1]], rows[t[2]], row_p) == 0:
            return False
    return True


def first_legal_outer(S_list, n=8):
    """All legal points outside the board at minimal Chebyshev distance from bbox."""
    xs = [i % n for i in S_list]
    ys = [i // n for i in S_list]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    found = []
    for d in range(1, 16):
        cand = []
        for x in range(minx - d - 1, maxx + d + 2):
            for y in range(miny - d - 1, maxy + d + 2):
                dx = 0
                if x < minx:
                    dx = minx - x
                elif x > maxx:
                    dx = x - maxx
                dy = 0
                if y < miny:
                    dy = miny - y
                elif y > maxy:
                    dy = y - maxy
                if max(dx, dy) != d:
                    continue
                if 0 <= x < n and 0 <= y < n:
                    continue
                if can_add_xy_board(S_list, x, y):
                    cand.append((x, y))
        if cand:
            return d, cand
    return None, []


def d4_orbit_types(points, minx, maxx, miny, maxy):
    """D4-normalized type of each outer point.

    Under the board's square symmetry, a first legal outer point at Chebyshev
    distance d from the bbox is either
      edge  (exactly one of dx,dy equals d, the other is 0), or
      corner(both dx=dy=d).
    So the orbit type is just ("edge", d) or ("corner", d).
    """
    types = set()
    for x, y in points:
        dx = 0
        if x < minx:
            dx = minx - x
        elif x > maxx:
            dx = x - maxx
        dy = 0
        if y < miny:
            dy = miny - y
        elif y > maxy:
            dy = y - maxy
        d = max(dx, dy)
        if dx == 0 or dy == 0:
            types.add(("edge", d))
        else:
            types.add(("corner", d))
    return sorted(types)


# ---------------- circle keys / inversion (B355/B358/B359) ----------------
def circle_key(p, a, b):
    """Exact key of the circle through p, a, b (None if collinear).
    Key = (A,B,C,D) normalized for A x^2 + A y^2 + B x + C y + D = 0 with A=1
    for non-collinear; collinear uses line Bx+Cy+D=0 with gcd normalization.
    """
    (x1, y1), (x2, y2), (x3, y3) = p, a, b
    # collinear?
    det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    if det == 0:
        # line through a,b: (y2-y1)x - (x2-x1)y + ... = 0
        A = y2 - y1
        B = x1 - x2
        C = x2 * y1 - x1 * y2
        g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
        if g:
            A, B, C = A // g, B // g, C // g
        if A < 0 or (A == 0 and B < 0) or (A == 0 and B == 0 and C < 0):
            A, B, C = -A, -B, -C
        return ("L", A, B, C)
    # circle: solve for center/radius via perpendicular bisectors — use determinant form
    # Circle: x^2+y^2 + D x + E y + F = 0 through 3 pts
    # Set up 3x3:
    # x_i^2+y_i^2 + D x_i + E y_i + F = 0
    M = []
    rhs = []
    for (x, y) in (p, a, b):
        M.append([x, y, 1])
        rhs.append(-(x * x + y * y))
    # solve 3x3
    D, E, F = solve3(M, rhs)
    # normalize by gcd of integer representation
    # multiply to clear: use integer since rhs is integer and M integer
    return ("C", D, E, F)


def solve3(M, rhs):
    det = (
        M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
        - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
        + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0])
    )
    if det == 0:
        return None
    def col(j):
        N = [row[:] for row in M]
        for i in range(3):
            N[i][j] = rhs[i]
        return (
            N[0][0] * (N[1][1] * N[2][2] - N[1][2] * N[2][1])
            - N[0][1] * (N[1][0] * N[2][2] - N[1][2] * N[2][0])
            + N[0][2] * (N[1][0] * N[2][1] - N[1][1] * N[2][0])
        )
    Dx, Dy, Dz = col(0), col(1), col(2)
    # exact rational
    from fractions import Fraction
    return Fraction(Dx, det), Fraction(Dy, det), Fraction(Dz, det)


def vandermonde_rank(points, max_deg=3):
    """Rank of the matrix [1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3] truncated
    at total degree <= max_deg. Integer Gaussian elimination over Q."""
    from fractions import Fraction
    mons = []
    for d in range(max_deg + 1):
        for i in range(d + 1):
            # x^i y^(d-i)
            mons.append((i, d - i))
    M = []
    for (x, y) in points:
        row = []
        for (i, j) in mons:
            row.append(Fraction((x ** i) * (y ** j)))
        M.append(row)
    if not M:
        return 0
    rows, cols = len(M), len(M[0])
    rank = 0
    used = [False] * rows
    for c in range(cols):
        piv = None
        for r in range(rows):
            if not used[r] and M[r][c] != 0:
                piv = r
                break
        if piv is None:
            continue
        used[piv] = True
        rank += 1
        pv = M[piv][c]
        for r in range(rows):
            if r != piv and M[r][c] != 0:
                fac = M[r][c] / pv
                for cc in range(cols):
                    M[r][cc] -= fac * M[piv][cc]
    return rank


def invert_points(points, center):
    """Inversion (x,y) -> center + (p-center)/|p-center|^2, as Fractions.
    Points at the center are skipped. Collinear-with-center triples become
    lines through the image of infinity — we keep exact rational images."""
    from fractions import Fraction
    cx, cy = center
    out = []
    for (x, y) in points:
        dx, dy = x - cx, y - cy
        n2 = dx * dx + dy * dy
        if n2 == 0:
            continue
        out.append((Fraction(dx, n2), Fraction(dy, n2)))
    return out


def vandermonde_rank_frac(points, max_deg=3):
    from fractions import Fraction
    mons = []
    for d in range(max_deg + 1):
        for i in range(d + 1):
            mons.append((i, d - i))
    M = []
    for (x, y) in points:
        row = []
        for (i, j) in mons:
            row.append((x ** i) * (y ** j))
        M.append(row)
    if not M:
        return 0
    rows, cols = len(M), len(M[0])
    rank = 0
    used = [False] * rows
    for c in range(cols):
        piv = None
        for r in range(rows):
            if not used[r] and M[r][c] != 0:
                piv = r
                break
        if piv is None:
            continue
        used[piv] = True
        rank += 1
        pv = M[piv][c]
        for r in range(rows):
            if r != piv and M[r][c] != 0:
                fac = M[r][c] / pv
                for cc in range(cols):
                    M[r][cc] -= fac * M[piv][cc]
    return rank


def t3(k):
    """Real orchard number floor(k(k-3)/6)+1."""
    return (k * (k - 3)) // 6 + 1


# ---------------- main jobs ----------------
def job_chunk6_summary():
    d = json.loads(CHUNK6.read_text(encoding="utf-8"))
    out = {}
    for nk in ["n2", "n3", "n4", "n5", "n6_safe_n6_k8.bin", "n6_safe_n6_k9.bin", "n6_safe_n6_k10.bin"]:
        v = d[nk]
        out[nk] = {
            "n_sets": v["n_sets"],
            "min_delta_by_k": v["min_delta_by_k"],
            "max_b_by_k": v["max_b_by_k"],
            "max_b_second_by_k": v["max_b_second_by_k"],
            "violation_k": v["violation_k"],
            "n_delta_lt_half_k_by_k": v["n_delta_lt_half_k_by_k"],
            "max_b_over_k2": v["max_b_over_k2"],
            "max_b_second_over_k2": v["max_b_second_over_k2"],
        }
    return out


def job_b351_b352_b353_b354(chunk):
    """Weak forms from existing min_delta / max_b tables + 408."""
    # Collect min_delta(k) across n<=6
    min_delta = {}
    max_b = {}
    max_b2 = {}
    for nk, v in chunk.items():
        for k, val in v["min_delta_by_k"].items():
            k = int(k)
            if k not in min_delta or val < min_delta[k]:
                min_delta[k] = val
        for k, val in v["max_b_by_k"].items():
            k = int(k)
            if k not in max_b or val > max_b[k]:
                max_b[k] = val
        for k, val in v["max_b_second_by_k"].items():
            k = int(k)
            if k not in max_b2 or val > max_b2[k]:
                max_b2[k] = val

    # 408: delta_min = C(8,2)-3*max_b ; from multi.json max_b_hist {3:56,4:256,5:88,6:8}
    k8_delta_min_408 = 28 - 3 * 6  # = 10
    if 8 not in min_delta or k8_delta_min_408 < min_delta[8]:
        pass  # keep both

    # B351 weak: k>=4 => delta >= k/2
    viol = []
    for k, dlt in sorted(min_delta.items()):
        if k >= 4 and dlt * 2 < k:
            viol.append((k, dlt))
    # stage exponents for B352
    exponents = {}
    ks = sorted(min_delta.keys())
    for a, b in zip(ks, ks[1:]):
        if min_delta[a] > 0 and min_delta[b] > 0 and a > 0:
            exponents[f"{a}->{b}"] = math.log(min_delta[b] / min_delta[a]) / math.log(b / a)
    # B353: delta/k <= 1
    linear_ok = {k: (min_delta[k] / k) for k in ks}
    # B354: gap t3(k)-max_b
    gaps = {}
    for k, mb in sorted(max_b.items()):
        gaps[k] = {"max_b": mb, "t3": t3(k), "gap": t3(k) - mb}
    return {
        "min_delta_by_k_nle6": min_delta,
        "max_b_by_k_nle6": max_b,
        "max_b_second_by_k_nle6": max_b2,
        "b351_violations_k_ge_4": viol,
        "b351_weak_ok": len(viol) == 0,
        "k8_delta_min_408": k8_delta_min_408,
        "b352_stage_exponents": exponents,
        "b352_all_gt_1": all(e > 1 for e in exponents.values()),
        "b353_delta_over_k": linear_ok,
        "b353_max_k_with_delta_over_k_le_1": max([k for k, r in linear_ok.items() if r <= 1], default=None),
        "b354_gap_table": gaps,
    }


def job_408_structure():
    masks = load_masks(BIN)
    b = board_square(8)
    assert len(masks) == 408
    n = 8
    recs = []
    for idx, m in enumerate(masks):
        S = mask_to_ids(m, n)
        xs = [i % n for i in S]
        ys = [i // n for i in S]
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        # coverage / max_b / second
        empt = [i for i in range(b.V) if i not in set(S)]
        cov = []
        for e in empt:
            cov.append(b_S(b, S, e))
        cov_sorted = sorted(cov, reverse=True)
        max_b = cov_sorted[0] if cov_sorted else 0
        second_b = cov_sorted[1] if len(cov_sorted) > 1 else 0
        argmax = empt[cov.index(max_b)] if cov else None
        # r_ext
        d_ext, outer = first_legal_outer(S, n)
        # rho (may be slow for 408; do for all — k=8, tau small)
        # sample first 8 for rho to keep runtime OK; full rho later if fast
        recs.append({
            "idx": idx,
            "S": S,
            "minx": minx, "maxx": maxx, "miny": miny, "maxy": maxy,
            "max_b": max_b,
            "second_b": second_b,
            "argmax": argmax,
            "sum_b": sum(cov),
            "r_ext": d_ext,
            "outer": outer,
        })
    return recs


def job_b382(recs):
    """D4-normalized types of first legal outer points, full 408."""
    type_counter = Counter()
    n_first = []
    all_types = set()
    for r in recs:
        outer = r["outer"]
        n_first.append(len(outer))
        ts = d4_orbit_types(outer, r["minx"], r["maxx"], r["miny"], r["maxy"])
        for t in ts:
            all_types.add(t)
        type_counter[tuple(ts)] += 1
    return {
        "n_total": len(recs),
        "n_first_hist": dict(Counter(n_first)),
        "d4_types": sorted(list(all_types)),
        "n_d4_types": len(all_types),
        "type_set_hist_size": len(type_counter),
    }


def job_b359(recs, b):
    """For each set, at argmax-b empty point p: how many distinct circles through p
    are determined by triples of S? Compare with b_S(p)."""
    out = []
    for r in recs[:408]:
        S = r["S"]
        p = r["argmax"]
        if p is None:
            continue
        pp = (p % 8, p // 8)
        # distinct circle keys through p from pairs of S
        keys = set()
        circle_ids = []  # which triples map to which key
        triples = forbidding_triples(b, S, p)
        for t in triples:
            a = (S[t[0]] % 8, S[t[0]] // 8) if False else (t[0] % 8, t[0] // 8)
            # t is a tuple of ids (board ids)
            a = (t[0] % 8, t[0] // 8)
            bb = (t[1] % 8, t[1] // 8)
            ck = circle_key(pp, a, bb)
            keys.add(ck)
            circle_ids.append(ck)
        # also all pairs of S give circles through p (may be empty completion)
        pair_keys = set()
        for a_id, b_id in combinations(S, 2):
            a = (a_id % 8, a_id // 8)
            bb = (b_id % 8, b_id // 8)
            pair_keys.add(circle_key(pp, a, bb))
        out.append({
            "idx": r["idx"],
            "p": [pp[0], pp[1]],
            "max_b": r["max_b"],
            "second_b": r["second_b"],
            "n_distinct_circles_from_forbidding_triples": len(keys),
            "n_distinct_circles_from_all_pairs": len(pair_keys),
            "n_forbidding_triples": len(triples),
        })
    # correlation summary
    import statistics
    xs = [o["max_b"] for o in out]
    ys = [o["n_distinct_circles_from_forbidding_triples"] for o in out]
    ys2 = [o["n_distinct_circles_from_all_pairs"] for o in out]
    def corr(a, b_):
        n = len(a)
        if n == 0:
            return None
        ma, mb = sum(a) / n, sum(b_) / n
        num = sum((a[i] - ma) * (b_[i] - mb) for i in range(n))
        da = math.sqrt(sum((x - ma) ** 2 for x in a))
        db = math.sqrt(sum((x - mb) ** 2 for x in b_))
        return num / (da * db) if da and db else None
    return {
        "n": len(out),
        "corr_max_b_vs_n_circles_forbidding": corr(xs, ys),
        "corr_max_b_vs_n_circles_allpairs": corr(xs, ys2),
        "mean_n_circles_forbidding": sum(ys) / len(ys) if ys else None,
        "mean_n_circles_allpairs": sum(ys2) / len(ys2) if ys2 else None,
        "high_b_ge_5": [o for o in out if o["max_b"] >= 5][:12],
    }


def job_b355(recs):
    """Inversion of S about the argmax-b empty point p; Vandermonde rank of the
    inverted stone images at degree <= 3. High-b sets should have low rank."""
    results = []
    for r in recs[:120]:
        S = r["S"]
        p = r["argmax"]
        if p is None:
            continue
        pp = (p % 8, p // 8)
        stones = [(i % 8, i // 8) for i in S]
        inv = invert_points(stones, pp)
        if len(inv) < 3:
            continue
        rank = vandermonde_rank_frac(inv, max_deg=3)
        results.append({
            "idx": r["idx"],
            "max_b": r["max_b"],
            "rank_deg3": rank,
            "n_inv": len(inv),
        })
    # summarize by max_b
    by_b = defaultdict(list)
    for o in results:
        by_b[o["max_b"]].append(o["rank_deg3"])
    summary = {}
    for bval, ranks in sorted(by_b.items()):
        summary[str(bval)] = {
            "n": len(ranks),
            "rank_hist": dict(Counter(ranks)),
            "mean_rank": sum(ranks) / len(ranks),
        }
    return {"by_max_b": summary, "n": len(results)}


def job_b358(recs):
    """After inversion about argmax p, count ordinary lines (exactly 3 inverted
    points collinear, no 4th) and check whether each ordinary line's endpoint-pair
    identifies a distinct circle of the original configuration.

    Operational definition of 'identify': the map ordinary_line -> original circle
    (the circle through p and the two endpoints' preimages) is injective on the
    set of ordinary lines that have both endpoints among inverted stones.
    """
    out = []
    for r in recs[:40]:
        S = r["S"]
        p = r["argmax"]
        if p is None:
            continue
        pp = (p % 8, p // 8)
        stones = [(i % 8, i // 8) for i in S]
        inv = invert_points(stones, pp)
        if len(inv) < 3:
            continue
        # find collinear triples in inverted set
        coll = []
        m = len(inv)
        for i, j, k in combinations(range(m), 3):
            a, b_, c = inv[i], inv[j], inv[k]
            det = (b_[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b_[1] - a[1])
            if det == 0:
                coll.append((i, j, k))
        # ordinary lines: collinear triples that are not contained in a larger collinear set
        ord_lines = []
        for t in coll:
            i, j, k = t
            # any 4th?
            extra = False
            for w in range(m):
                if w in t:
                    continue
                a, b_, c = inv[i], inv[j], inv[w]
                det = (b_[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b_[1] - a[1])
                if det == 0:
                    extra = True
                    break
            if not extra:
                ord_lines.append(t)
        # map each ordinary line to the circle through p and the two endpoints
        # (the third point of the triple is the "middle" — use the two extreme endpoints)
        def endpoints(t):
            # pick the two farthest inverted points
            best = None
            best_d = None
            for i, j in combinations(t, 2):
                d = (inv[i][0] - inv[j][0]) ** 2 + (inv[i][1] - inv[j][1]) ** 2
                if best_d is None or d > best_d:
                    best_d = d
                    best = (i, j)
            return best

        keys = []
        for t in ord_lines:
            i, j = endpoints(t)
            a = stones[i]
            b_ = stones[j]
            keys.append(circle_key(pp, a, b_))
        uniq = set(keys)
        out.append({
            "idx": r["idx"],
            "max_b": r["max_b"],
            "n_collinear_triples": len(coll),
            "n_ordinary": len(ord_lines),
            "n_distinct_circles_from_ordinary": len(uniq),
            "injective": len(uniq) == len(keys),
        })
    n_inj = sum(1 for o in out if o["injective"])
    return {"n_sampled": len(out), "n_injective": n_inj, "all_injective": n_inj == len(out), "rows": out[:20]}


def job_b363_b384_b385_b390(recs, b):
    """rho / r_ext / one-stone-move Delta r for 408."""
    # rho on a sample of 40 sets (tau is O(2^k * b)); full r_ext is cheap.
    sample = recs[:15]
    rhos = [rho_of(b, r["S"]) for r in sample]
    r_exts = [r["r_ext"] for r in recs]
    swap_dr = []
    max_r_after_swap = 0
    for r in recs[:15]:
        S = r["S"]
        Smask = 0
        for i in S:
            Smask |= 1 << i
        for out_i in S:
            rest_mask = Smask & ~(1 << out_i)
            for in_i in range(64):
                if (Smask >> in_i) & 1:
                    continue
                Tmask = rest_mask | (1 << in_i)
                if not is_safe_maskint(b, Tmask):
                    continue
                T = [i for i in range(64) if (Tmask >> i) & 1]
                rT = r_ext_of(T, 8)
                swap_dr.append(rT - r["r_ext"])
                if rT > max_r_after_swap:
                    max_r_after_swap = rT
    return {
        "rho_sample_n": 15,
        "rho_hist_sample": dict(Counter(rhos)),
        "rho_max_sample": max(rhos),
        "r_ext_hist_408": dict(Counter(r_exts)),
        "swap_delta_r_hist_sample15": dict(Counter(swap_dr)),
        "max_r_ext_after_1swap_sample15": max_r_after_swap,
    }


def is_safe_maskint(b: Board, Smask: int) -> bool:
    for q in b.quads:
        if (Smask & q) == q:
            return False
    return True


def can_add_maskint(b: Board, Smask: int, p: int) -> bool:
    for q in b.quads_by_pt[p]:
        rest = q & ~(1 << p)
        if rest and (Smask & rest) == rest:
            return False
    return True


def job_b370_fast(recs, b, n_sets=8):
    """1-out 2-in shrink on a sample of 408 using bitmask legality."""
    total = fail_unsafe = fail_uncovered = success = 0
    for r in recs[:n_sets]:
        S = r["S"]
        Smask = 0
        for i in S:
            Smask |= 1 << i
        cands = [i for i in range(64) if not (Smask >> i) & 1]
        for out_i in S:
            rest_mask = Smask & ~(1 << out_i)
            for in_a, in_b in combinations(cands, 2):
                Tmask = rest_mask | (1 << in_a) | (1 << in_b)
                total += 1
                if not is_safe_maskint(b, Tmask):
                    fail_unsafe += 1
                    continue
                ok = True
                for p in range(64):
                    if (Tmask >> p) & 1:
                        continue
                    if can_add_maskint(b, Tmask, p):
                        ok = False
                        break
                if ok:
                    success += 1
                else:
                    fail_uncovered += 1
    return {
        "sample_sets": n_sets,
        "total_1out2in": total,
        "fail_unsafe": fail_unsafe,
        "fail_uncovered": fail_uncovered,
        "success_maximal": success,
        "unsafe_share": fail_unsafe / total if total else None,
    }


def can_add_fast(b, S_list, p):
    row_p = b.rows[p]
    for t in combinations(S_list, 3):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], row_p) == 0:
            return False
    return True


def job_b376(recs, b):
    """Covering: for each empty point, which triples forbid it. Lower bound on
    the number of curves (triples) needed to cover all empty points.
    Also max empty-points covered by a single triple (gives a set-cover LB)."""
    out = []
    for r in recs[:40]:
        S = r["S"]
        empt = [i for i in range(b.V) if i not in set(S)]
        # for each triple, the set of empty points it forbids
        triple_cov = {}
        for t in combinations(S, 3):
            r0, r1, r2 = b.rows[t[0]], b.rows[t[1]], b.rows[t[2]]
            cover = set()
            for e in empt:
                if det4(r0, r1, r2, b.rows[e]) == 0:
                    cover.add(e)
            triple_cov[t] = cover
        sizes = [len(v) for v in triple_cov.values()]
        max_cov = max(sizes) if sizes else 0
        # greedy set cover
        uncovered = set(empt)
        used = 0
        while uncovered:
            best = max(triple_cov.values(), key=lambda s: len(s & uncovered), default=set())
            gain = len(best & uncovered)
            if gain == 0:
                break
            uncovered -= best
            used += 1
        # exact cover for small: ILP-less branch on first few
        out.append({
            "idx": r["idx"],
            "n_empty": len(empt),
            "max_single_triple_cover": max_cov,
            "greedy_cover": used,
            "lb_from_max_cov": (len(empt) + max_cov - 1) // max_cov if max_cov else None,
        })
    return {"rows": out}


def job_b379():
    """Search 9x9 9-stone maximals by random greedy + check whether any 8-stone
    maximal embeds into one with <=2 relocations. Also try offsets."""
    b9 = board_square(9)
    # random greedy maximals on 9x9
    import random
    rng = random.Random(20260929)
    found = []
    for trial in range(400):
        S = []
        order = list(range(81))
        rng.shuffle(order)
        for p in order:
            if can_add_fast(b9, S, p):
                S.append(p)
        if len(S) == 9:
            found.append(S)
    uniq = {tuple(sorted(s)) for s in found}
    masks = load_masks(BIN)
    hits = 0
    best_common = 0
    for nine in list(uniq)[:80]:
        nine_set = set(nine)
        for m in masks:
            S8 = mask_to_ids(m, 8)
            # try offset (1,1): (x,y) -> (x+1,y+1)
            for off in [(1, 1), (0, 0), (1, 0), (0, 1)]:
                emb = [ (y + off[1]) * 9 + (x + off[0]) for (x, y) in [(i % 8, i // 8) for i in S8] ]
                if any(x < 0 or x > 8 or y < 0 or y > 8 for (x, y) in [(i % 9, i // 9) for i in emb]):
                    continue
                common = len(set(emb) & nine_set)
                if common > best_common:
                    best_common = common
                # need >= 8-2 = 6 common for 2 relocations to reach 9 stones
                if common >= 6:
                    # check exact: remove 8-common, add 9-common = 2 relocations and +1 size
                    # 9-stone from 8-stone: +1 net, so r_out + 1 = r_in, with r_out<=2 => r_in<=3
                    # 2 relocations means r_out<=2 and r_in = r_out+1
                    r_out = 8 - common
                    r_in = 9 - common
                    if r_out <= 2 and r_in == r_out + 1:
                        hits += 1
    return {
        "n_random_9stone_maximals": len(uniq),
        "best_common_with_408": best_common,
        "hits_r_le_2": hits,
    }


def job_b366(b):
    """For a sample of geometric forbidding-triple hypergraphs, compute tau and
    compare with an abstract linear 3-uniform hypergraph bound.
    Abstract bound used: for a linear 3-uniform hypergraph with v vertices and e
    edges, tau <= ceil(e / floor(v/3)) is a crude bound; a better one is
    tau <= v - alpha where alpha is matching number. We compute the max tau over
    ALL linear 3-uniform hypergraphs with small (v,e) by exhaustive generation for
    v<=6 and compare with geometric tau from n=5."""
    # geometric: use n=5 all safe k=6..8 empty points would be heavy; instead use
    # the 408 sample we already have tau for (rho) and also compute tau histogram
    masks = load_masks(BIN)
    b8 = board_square(8)
    taus = []
    fams = []
    for m in masks[:30]:
        S = mask_to_ids(m, 8)
        empt = [i for i in range(64) if i not in set(S)]
        for e in empt[:3]:
            fam = forbidding_triples(b8, S, e)
            if not fam:
                continue
            t = tau_of(b8, S, e)
            taus.append(t)
            fams.append({"v": len(S), "e": len(fam), "tau": t, "linear": is_linear(fam)})

    # abstract exhaustive for v=5, e=2..4 linear 3-uniform
    abstract = abstract_max_tau(vmax=5, emax=5)
    return {
        "geom_tau_hist_sample": dict(Counter(taus)),
        "geom_fams_linear_share": sum(1 for f in fams if f["linear"]) / len(fams) if fams else None,
        "abstract_max_tau": abstract,
    }


def is_linear(fam):
    for a, b_ in combinations(fam, 2):
        if len(set(a) & set(b_)) >= 2:
            return False
    return True


def abstract_max_tau(vmax=6, emax=5):
    """Max tau over all linear 3-uniform hypergraphs with v<=vmax, e<=emax.
    Exhaustive over edge subsets of C(v,3) filtered by linearity."""
    out = {}
    for v in range(3, vmax + 1):
        all_edges = list(combinations(range(v), 3))
        # enumerate edge sets up to emax, check linear, compute tau
        best = {}
        m = len(all_edges)
        # 2^m too big for v=6 (20 edges); cap by generating greedily / all subsets of size<=emax
        from itertools import combinations as C
        for e in range(1, emax + 1):
            best_tau = 0
            best_fam = None
            count = 0
            for fam in C(all_edges, e):
                if not is_linear(list(fam)):
                    continue
                count += 1
                t = abs_tau(v, fam)
                if t > best_tau:
                    best_tau = t
                    best_fam = fam
            best[str(e)] = {"max_tau": best_tau, "n_linear_fams": count, "example": best_fam}
        out[str(v)] = best
    return out


def abs_tau(v, fam):
    """fam: triples of vertex labels 0..v-1."""
    for r in range(1, v + 1):
        for R in combinations(range(v), r):
            Rset = set(R)
            if all(any(i in Rset for i in t) for t in fam):
                return r
    return v


def main():
    out = {}
    def save():
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("chunk6...", flush=True)
    chunk = job_chunk6_summary()
    out["chunk6"] = chunk
    print("b351-354...", flush=True)
    out["b351_b354"] = job_b351_b352_b353_b354(chunk)
    save()
    print("408 structure...", flush=True)
    recs = job_408_structure()
    out["n_masks"] = len(recs)
    save()
    print("b382...", flush=True)
    out["b382"] = job_b382(recs)
    save()
    b = board_square(8)
    print("b359...", flush=True)
    out["b359"] = job_b359(recs, b)
    save()
    print("b355...", flush=True)
    out["b355"] = job_b355(recs)
    save()
    print("b358...", flush=True)
    out["b358"] = job_b358(recs)
    save()
    print("b363/384/385/390...", flush=True)
    out["b363_b390"] = job_b363_b384_b385_b390(recs, b)
    save()
    print("b370 1out2in...", flush=True)
    out["b370"] = job_b370_fast(recs, b, n_sets=6)
    save()
    print("b376...", flush=True)
    out["b376"] = job_b376(recs, b)
    save()
    print("b379...", flush=True)
    out["b379"] = job_b379()
    save()
    print("b366...", flush=True)
    out["b366"] = job_b366(b)
    save()
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
