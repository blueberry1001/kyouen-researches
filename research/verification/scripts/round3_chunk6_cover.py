#!/usr/bin/env python3
"""Round3 chunk6 group C: B351, B352, B353, B354, B355, B356, B358, B359, B360.

Integer / exact rational arithmetic only.

  b_S(p) = #{T c S, |T|=3 : T u {p} is a forbidden quad}
  delta(S,p) = C(k,2) - 3 b_S(p)

  B351  min delta/k per k over the whole eligible population; the exact k from
        which delta >= k/2 holds with no exception.
  B352  power-law fit of min delta(k); is the exponent > 1?
  B353  unbounded-lattice hill climb maximising b at k = 2..14: is delta = O(k)
        achievable?  (Uses the exact circle-key identity below.)
  B354  gap to the real-valued orchard optimum t_3(k) = floor(k(k-3)/6)+1
        for every k, on the lattice.
  B355  inversion x -> x/|x|^2 of the argmax-b witnesses + EXACT rank test:
        how many inverted points lie on a degree <= d curve (d=1,2,3)?
  B356  is there any k with TWO empty points both at c*k^2?  Exact scan of
        min(b_1,b_2)/k^2.
  B358  the "ordinary lines" of the inverted point set (3 collinear, no 4th)
        and their endpoints: does each one identify a distinct circle of the
        original configuration?
  B359  number of distinct circles through p at the argmax-b empty point vs b.
  B360  two safe sets with the same max b but maximally different |union of
        forbidden empty points|.

Circle-key identity (exact, used everywhere):
  b_S(p) = sum over circles C through p of binom(|S n C|, 3)
so grouping the C(k,2) pairs of S by their circle-through-p key gives b.

Output: research/verification/round3_chunk6_cover.json
"""
from __future__ import annotations

import json
import math
import random
import struct
import sys
import time
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, square_points  # noqa: E402

sys.setrecursionlimit(300000)
OUT = ROOT / "research" / "verification" / "round3_chunk6_cover.json"
DATA = ROOT / "research" / "verification" / "data"


# ---------------------------------------------------------------- utilities
def load_u64(path: Path) -> list[int]:
    d = path.read_bytes()
    return list(struct.unpack(f"<{len(d)//8}Q", d))


def mask_ids(m: int) -> list[int]:
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def build_triple_comp(board: Board):
    tc: dict[int, list[int]] = {}
    for q in board.quads:
        for p in mask_ids(q):
            t = q & ~(1 << p)
            tc.setdefault(t, []).append(p)
    return tc


def circle_key(p, a, b):
    """Exact key of the circle through p, a, b (None if collinear)."""
    px, py = p
    ax, ay = a
    bx, by = b
    d = 2 * (ax * (by - py) + bx * (py - ay) + px * (ay - by))
    if d == 0:
        return None
    ux = ((ax * ax + ay * ay) * (by - py) + (bx * bx + by * by) * (py - ay)
          + (px * px + py * py) * (ay - by))
    uy = ((ax * ax + ay * ay) * (px - bx) + (bx * bx + by * by) * (ax - px)
          + (px * px + py * py) * (bx - ax))
    # normalise uy/d : ux/d by a common factor
    g = math.gcd(math.gcd(abs(ux), abs(uy)), abs(d)) or 1
    return (ux // g, uy // g, d // g)


def b_from_pairs(p, S):
    """b_S(p) via the circle-key identity.  S is a list of lattice points."""
    groups: dict[tuple, set] = defaultdict(set)
    for a, b in combinations(S, 2):
        kk = circle_key(p, a, b)
        if kk is None:
            continue
        groups[kk].add(a)
        groups[kk].add(b)
    tot = 0
    for st in groups.values():
        if len(st) >= 3:
            tot += len(st) * (len(st) - 1) * (len(st) - 2) // 6
    return tot, groups


# ---------------------------------------------------------------- scanning
def scan_masks(board: Board, tc, masks, name):
    V = board.V
    st = {
        "name": name, "n_sets": 0,
        "min_delta_by_k": {}, "min_delta_arg": {},
        "max_b_by_k": {}, "max_b_arg": {},
        "max_b_second_by_k": {},
        "violation_k": {},
        "n_delta_lt_half_k_by_k": {},
    }
    by_maxb: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for S in masks:
        k = S.bit_count()
        if k < 2:
            continue
        st["n_sets"] += 1
        ids = mask_ids(S)
        bvec = [0] * V
        for a, b, c in combinations(ids, 3):
            tm = (1 << a) | (1 << b) | (1 << c)
            for p in tc.get(tm, ()):
                bvec[p] += 1
        Ck2 = k * (k - 1) // 2
        empties = [p for p in range(V) if not (S >> p) & 1]
        if not empties:
            continue
        dmin = min(Ck2 - 3 * bvec[p] for p in empties)
        mb = max(bvec[p] for p in empties)
        pa = max(empties, key=lambda q: bvec[q])
        key = st["min_delta_by_k"].get(k)
        if key is None or dmin < key:
            st["min_delta_by_k"][k] = dmin
            st["min_delta_arg"][k] = {"S": ids, "delta": dmin, "k": k}
        key = st["max_b_by_k"].get(k)
        if key is None or mb > key:
            st["max_b_by_k"][k] = mb
            st["max_b_arg"][k] = {"S": ids, "p": pa, "b": mb, "k": k}
        top2 = sorted((bvec[p] for p in empties), reverse=True)[:2]
        if len(top2) >= 2:
            c = st["max_b_second_by_k"].get(k)
            if c is None or top2[1] > c:
                st["max_b_second_by_k"][k] = top2[1]
        if 2 * dmin < k:
            st["n_delta_lt_half_k_by_k"][k] = st["n_delta_lt_half_k_by_k"].get(k, 0) + 1
            st["violation_k"][k] = {"S": ids, "delta": dmin, "k": k}
        forb = sum(1 for p in empties if bvec[p] > 0)
        by_maxb[mb].append((forb, sum(bvec[p] for p in empties)))
    ok = None
    for k in sorted(st["min_delta_by_k"]):
        if 2 * st["min_delta_by_k"][k] >= k and k not in st["n_delta_lt_half_k_by_k"]:
            ok = k
            break
    st["smallest_k_all_satisfy_delta_ge_half_k"] = ok
    st["violations_k_ge_8"] = {str(k): v for k, v in
                               sorted(st["violation_k"].items()) if k >= 8}
    st["max_b_over_k2"] = {str(k): (v / (k * k)) for k, v in
                           sorted(st["max_b_by_k"].items())}
    st["max_b_second_over_k2"] = {str(k): (v / (k * k)) for k, v in
                                  sorted(st["max_b_second_by_k"].items())
                                  if k in st["max_b_by_k"]}
    b360 = []
    for mb, lst in by_maxb.items():
        if len(lst) < 2:
            continue
        fs = [f for f, _ in lst]
        b360.append({"max_b": mb, "n": len(lst), "min_forb": min(fs),
                     "max_forb": max(fs),
                     "ratio": (max(fs) / min(fs)) if min(fs) else None})
    b360.sort(key=lambda r: -(r["ratio"] or 0))
    st["B360_same_maxb_spread_top"] = b360[:15]
    st["B360_global_best_ratio"] = max((r["ratio"] or 0) for r in b360) if b360 else None
    st["B360_n_maxb_classes_with_ge2_sets"] = len(b360)
    return st


# ------------------------------------------------------- unbounded lattice
def unbounded_b_max(k: int, restarts: int, box: int, seed: int = 20260927):
    rng = random.Random(seed + k)
    p = (0, 0)
    best = (-1, None)
    for _ in range(restarts):
        S = set(rng.sample([(x, y) for x in range(-box, box + 1)
                            for y in range(-box, box + 1)], k))
        S.discard(p)
        while len(S) < k:
            S.add((rng.randint(-box, box), rng.randint(-box, box)))
            S.discard(p)
        cur, _ = b_from_pairs(p, sorted(S))
        improved = True
        while improved:
            improved = False
            for s in list(S):
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if dx == 0 and dy == 0:
                            continue
                        new = set(S)
                        new.discard(s)
                        cand = (s[0] + dx, s[1] + dy)
                        if cand == p or cand in new:
                            continue
                        new.add(cand)
                        v, _ = b_from_pairs(p, sorted(new))
                        if v > cur:
                            S, cur, improved = new, v, True
        if cur > best[0]:
            best = (cur, sorted(S))
    return best[0], best[1]


# -------------------------------------------------- inversion & curve rank
def invert(pts):
    out = []
    for (x, y) in pts:
        d = x * x + y * y
        out.append(None if d == 0 else (Fraction(x, d), Fraction(y, d)))
    return out


def monomials(deg):
    return [(a, deg - a) for a in range(deg + 1)]


def vandermonde_rank(pts, deg):
    """Exact rank over Q of the matrix [x^a y^b]_{(a,b) in monomials(deg)}."""
    monos = monomials(deg)
    rows = [[(x ** a) * (y ** b) for (a, b) in monos] for (x, y) in pts]
    m, N = len(rows), len(monos)
    rank = 0
    A = [list(r) for r in rows]
    for col in range(N):
        sel = None
        for r in range(rank, m):
            if A[r][col] != 0:
                sel = r
                break
        if sel is None:
            continue
        A[rank], A[sel] = A[sel], A[rank]
        pv = A[rank][col]
        A[rank] = [v / pv for v in A[rank]]
        for r in range(m):
            if r != rank and A[r][col] != 0:
                f = A[r][col]
                A[r] = [a - f * b for a, b in zip(A[r], A[rank])]
        rank += 1
        if rank == m:
            break
    return rank, N


def curve_block(pts, label):
    """How many of the inverted points lie on a degree<=d curve for d=1,2,3."""
    inv = [q for q in invert(pts) if q is not None]
    res = {"label": label, "n_points_inverted": len(inv),
           "n_points_at_infinity": len(pts) - len(inv)}
    for d in (1, 2, 3):
        if len(inv) < 1:
            res[f"deg{d}"] = None
            continue
        r, N = vandermonde_rank(inv, d)
        # a nonzero degree<=d curve through ALL inv points exists iff r < N
        res[f"deg{d}"] = {
            "n_monomials": N, "rank": r,
            "curve_through_all_exists": r < N,
            "n_on_some_curve": len(inv) if r < N else None,
        }
    return res


# ------------------------------------------------------------------- B358
def ordinary_lines(inv_pts):
    """Lines containing exactly 3 of the inverted points, with endpoints."""
    n = len(inv_pts)
    lines: dict[tuple, set] = defaultdict(set)
    for i, j in combinations(range(n), 2):
        (x1, y1), (x2, y2) = inv_pts[i], inv_pts[j]
        a = y2 - y1
        b = x1 - x2
        c = -(a * x1 + b * y1)
        g = math.gcd(math.gcd(abs(a.numerator), abs(b.numerator)),
                      abs(c.numerator))
        if g == 0:
            g = 1
        key = (a / g, b / g, c / g)
        # canonical sign
        if (key[0], key[1], key[2]) < (-key[0], -key[1], -key[2]):
            key = (-key[0], -key[1], -key[2])
        lines[key].update((i, j))
    out = []
    for key, mem in lines.items():
        if len(mem) == 3:
            out.append({"line": [str(x) for x in key], "members": sorted(mem)})
    return out, {k: sorted(v) for k, v in lines.items()}


# ------------------------------------------------------------------- B359
def bundle_stats(S, p):
    _, groups = b_from_pairs(p, sorted(S))
    sizes = [len(v) for v in groups.values() if len(v) >= 2]
    return {
        "n_circles_through_p_with_2plus_S_points": len(sizes),
        "circle_size_hist": dict(Counter(sizes)),
        "b": sum(t * (t - 1) * (t - 2) // 6 for t in sizes),
    }


def main() -> None:
    res: dict = {}
    t0 = time.time()
    for n in (2, 3, 4, 5):
        B = Board(square_points(n), name=f"{n}x{n}")
        tc = build_triple_comp(B)
        masks = load_u64(DATA / f"safe_n{n}.bin")
        print(f"[n={n}] scanning {len(masks)} safe sets", flush=True)
        res[f"n{n}"] = scan_masks(B, tc, masks, f"{n}x{n} all safe")
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                       encoding="utf-8")
        print(f"[n={n}] done {time.time()-t0:.0f}s", flush=True)

    B6 = Board(square_points(6), name="6x6")
    tc6 = build_triple_comp(B6)
    for tag in ("safe_n6_k8.bin", "safe_n6_k9.bin", "safe_n6_k10.bin"):
        pth = DATA / tag
        if not pth.exists():
            continue
        masks = load_u64(pth)
        print(f"[n=6 {tag}] {len(masks)} sets", flush=True)
        res[f"n6_{tag}"] = scan_masks(B6, tc6, masks, tag)
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                       encoding="utf-8")

    print("== B352 power-law fit ==", flush=True)
    res["B352_fit"] = power_law_fit(res)

    print("== B353/B354 unbounded lattice ==", flush=True)
    res["B353_B354_lattice_search"] = lattice_search()
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                   encoding="utf-8")

    print("== B355/B358 inversion ==", flush=True)
    res["B355_B358_inversion"] = inversion_block(res)
    res["B359_bundle"] = bundle_block(res)
    res["elapsed_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                   encoding="utf-8")
    print("wrote", OUT, "in", res["elapsed_s"], "s", flush=True)


def power_law_fit(res):
    tab: dict[int, int] = {}
    for key in list(res):
        if not (key.startswith("n") and "_" not in key):
            continue
        for k, d in (res[key].get("min_delta_by_k") or {}).items():
            k = int(k)
            if k not in tab or d < tab[k]:
                tab[k] = d
    ks = sorted(tab)
    steps = []
    alphas = []
    for i in range(1, len(ks)):
        k0, k1 = ks[i - 1], ks[i]
        d0, d1 = tab[k0], tab[k1]
        steps.append({"k": k1, "delta": d1, "delta_over_k": round(d1 / k1, 4),
                      "delta_over_k2": round(d1 / (k1 * k1), 4),
                      "ratio": (d1 / d0) if d0 else None})
        if d1 > 0 and d0 > 0 and k1 > k0:
            alphas.append(math.log(d1 / d0) / math.log(k1 / k0))
    return {
        "min_delta_by_k": {str(k): tab[k] for k in ks},
        "per_step": steps,
        "mean_alpha": (sum(alphas) / len(alphas)) if alphas else None,
        "n_steps": len(alphas),
        "n_steps_alpha_ge_1": sum(1 for a in alphas if a >= 1.0),
        "n_steps_alpha_gt_1": sum(1 for a in alphas if a > 1.0),
    }


def lattice_search():
    out = []
    for k in range(2, 16):
        restarts = 120 if k <= 8 else (50 if k <= 11 else 20)
        box = 4 + k // 2
        b, S = unbounded_b_max(k, restarts, box)
        Ck2 = k * (k - 1) // 2
        delta = Ck2 - 3 * b
        t3 = (k * (k - 3)) // 6 + 1
        out.append({
            "k": k, "b_max_found": b, "S": S, "delta": delta,
            "delta_over_k": round(delta / k, 4) if k else None,
            "delta_over_k2": round(delta / (k * k), 4),
            "real_orchard_t3": t3, "gap_to_real": t3 - b,
            "b_over_k": round(b / k, 4), "b_over_k2": round(b / (k * k), 4),
            "b_over_Ck2_over_3": round(b / (Ck2 / 3), 4) if Ck2 else None,
            "upper_bound_Ck2_over_3": round(Ck2 / 3, 4),
        })
        print(f"  k={k}: b={b} delta={delta} delta/k={delta/k:.3f} t3={t3} "
              f"gap={t3-b}", flush=True)
    return out


def inversion_block(res):
    out = []
    for key in list(res):
        if not key.startswith("n") or not isinstance(res[key], dict):
            continue
        st = res[key]
        if "max_b_arg" not in st:
            continue
        n = 6 if "_" in key else int(key[1:])
        for k, arg in st["max_b_arg"].items():
            S = [(v % n, v // n) for v in arg["S"]]
            p = (arg["p"] % n, arg["p"] // n)
            inv = [q for q in invert([p] + S) if q is not None]
            cb = curve_block([p] + S, f"{key}:k={k}")
            ol, all_lines = ordinary_lines(inv)
            out.append({
                "board": key, "k": int(k), "b": arg["b"], "p_xy": p, "S_xy": S,
                "n_collinear_triples_in_original": count_collinear(S),
                "curve_rank": cb,
                "n_ordinary_lines_in_inverted": len(ol),
                "ordinary_lines": ol[:10],
                "bundle": bundle_stats(S, p),
            })
    return out


def count_collinear(pts):
    c = 0
    for a, b, d in combinations(pts, 3):
        if (b[0] - a[0]) * (d[1] - a[1]) == (b[1] - a[1]) * (d[0] - a[0]):
            c += 1
    return c


def bundle_block(res):
    out = []
    for key in list(res):
        if not key.startswith("n") or not isinstance(res[key], dict):
            continue
        st = res[key]
        for k, arg in (st.get("max_b_arg") or {}).items():
            n = 6 if "_" in key else int(key[1:])
            S = [(v % n, v // n) for v in arg["S"]]
            p = (arg["p"] % n, arg["p"] // n)
            out.append({"board": key, "k": int(k), "b": arg["b"], "p_xy": p,
                        "Chebyshev_dist_p_to_S": max(
                            max(abs(px - qx), abs(py - qy)) for qx, qy in S),
                        **bundle_stats(S, p)})
    return out


if __name__ == "__main__":
    main()
