#!/usr/bin/env python3
"""round5_b101a_ident_inv — B106/B107（識別点数）と B140（反転変換）と B104（未使用軌道）。

出力: research/verification/round5_b101a_ident_inv.json
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points, is_forbidden_quad  # noqa: E402

OUT = ROOT / "research" / "verification" / "round5_b101a_ident_inv.json"


def load_masks(path: Path) -> list[int]:
    raw = path.read_bytes()
    cnt = len(raw) // 8
    return list(struct.unpack(f"<{cnt}Q", raw)) if cnt else []


def b106_ident(n: int, max_c: int = 6) -> dict:
    board = Board(square_points(n))
    max_sets = load_masks(DATA / f"maximal_n{n}.bin")
    sizes = [m.bit_count() for m in max_sets]
    K = max(sizes) if sizes else 0
    M = [m for m in max_sets if m.bit_count() == K]
    ident_needed = []
    for S in M:
        stones = [i for i in range(board.V) if (S >> i) & 1]
        found = -1
        for c in range(1, min(max_c, len(stones)) + 1):
            ok = False
            for sub in combinations(stones, c):
                cmask = sum(1 << i for i in sub)
                covers = 0
                for T in M:
                    if (T & cmask) == cmask:
                        covers += 1
                        if covers > 1:
                            break
                if covers == 1:
                    ok = True
                    break
            if ok:
                found = c
                break
        ident_needed.append(found)
    valid = [x for x in ident_needed if x > 0]
    curve = {str(c): sum(1 for x in valid if x <= c) for c in range(1, max_c + 1)}
    return {
        "n": n,
        "K": K,
        "n_max": len(M),
        "min_det": min(valid) if valid else -1,
        "max_det": max(valid) if valid else -1,
        "mean_det": (sum(valid) / len(valid)) if valid else None,
        "ident_curve": curve,
        "n_unidentified_within_c": sum(1 for x in ident_needed if x < 0),
        "log2_nmax": (len(M).bit_length() - 1) if M else 0,
        "min_det_vs_log": (min(valid) / max(1, (len(M).bit_length() - 1))) if valid else None,
    }


def b107_correlation() -> dict:
    """Compare n_max and min_det across n=4,5,6,7 (7 from existing data)."""
    rows = []
    for n in (4, 5, 6):
        r = b106_ident(n, max_c=5)
        rows.append(r)
    # n=7 from round4_b092.json shape data: min_det=2, n_max=16
    rows.append({
        "n": 7, "K": 14, "n_max": 16, "min_det": 2,
        "max_det": 2, "ident_curve": {"1": 0, "2": 16, "3": 16, "4": 16, "5": 16},
        "n_unidentified_within_c": 0,
    })
    # correlation: does smaller n_max imply smaller min_det?
    # log2(n_max) vs min_det
    pairs = [(r["n"], r["n_max"], r["min_det"]) for r in rows]
    # Spearman-like: sort by n_max and see if min_det is monotone
    by_nmax = sorted(pairs, key=lambda t: t[1])
    min_dets = [p[2] for p in by_nmax]
    monotone_inc = all(min_dets[i] <= min_dets[i + 1] for i in range(len(min_dets) - 1))
    return {
        "pairs_n_nmax_mindet": pairs,
        "sorted_by_nmax": by_nmax,
        "min_det_monotone_nondecreasing_in_nmax": monotone_inc,
    }


def b140_inversion(n: int) -> dict:
    """Apply integer-friendly inversion to small maximal configs and test safety/maximality.

    Inversion about origin with radius R: (x,y) -> (R^2 x / (x^2+y^2), R^2 y / (x^2+y^2)).
    For lattice->lattice we need R^2 divisible appropriately. Try R^2 = r2_num such that
    for each point (x,y) with d=x^2+y^2, R^2*x/d and R^2*y/d are integers.
    """
    board = Board(square_points(n))
    max_sets = load_masks(DATA / f"maximal_n{n}.bin")
    sizes = [m.bit_count() for m in max_sets]
    smin = min(sizes) if sizes else 0
    small_sets = [m for m in max_sets if m.bit_count() == smin][:20]
    pts = square_points(n)
    results = []
    for m in small_sets:
        chosen = [pts[i] for i in range(board.V) if (m >> i) & 1]
        # find R^2 such that inversion maps all chosen points to integers
        # R^2 must be a common multiple of d/gcd(d, ...) — simply R^2 = lcm of all d
        import math
        ds = [x * x + y * y for x, y in chosen]
        ds = [d for d in ds if d > 0]
        if not ds:
            continue
        R2 = 1
        for d in ds:
            R2 = R2 * d // math.gcd(R2, d)
        # try inversion of each point
        inv = []
        ok = True
        for x, y in chosen:
            d = x * x + y * y
            if d == 0:
                # (0,0) maps to infinity — fail
                ok = False
                break
            ix = R2 * x // d
            iy = R2 * y // d
            if R2 * x % d != 0 or R2 * y % d != 0:
                ok = False
                break
            inv.append((ix, iy))
        if not ok:
            results.append({"chosen": chosen, "inversion_ok": False, "R2": R2})
            continue
        # check if inverted points are a subset of some board (translate to fit)
        xs = [p[0] for p in inv]
        ys = [p[1] for p in inv]
        # translate so min is 0
        inv_t = [(x - min(xs), y - min(ys)) for x, y in inv]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        # safety of inverted set on a board that fits
        n2 = max(w, h) + 1
        if n2 > 8:
            results.append({"chosen": chosen, "inversion_ok": True, "R2": R2,
                            "inv_pts": inv_t, "board_n": n2, "safe_on_board": False,
                            "note": "board too large"})
            continue
        board2 = Board(square_points(n2))
        # map inv_t to indices
        pt_to_idx = {(x, y): i for i, (x, y) in enumerate(square_points(n2))}
        mask2 = 0
        in_board = True
        for p in inv_t:
            if p not in pt_to_idx:
                in_board = False
                break
            mask2 |= 1 << pt_to_idx[p]
        safe2 = in_board and board2.is_safe(mask2)
        maximal2 = safe2 and not board2.legal_moves(mask2)
        results.append({
            "chosen": chosen,
            "inversion_ok": True,
            "R2": R2,
            "inv_pts": inv_t,
            "board_n": n2,
            "in_board": in_board,
            "safe_on_board": safe2,
            "is_maximal": maximal2,
        })
    n_ok = sum(1 for r in results if r.get("inversion_ok"))
    n_safe = sum(1 for r in results if r.get("safe_on_board"))
    n_max = sum(1 for r in results if r.get("is_maximal"))
    return {
        "n": n,
        "n_trials": len(results),
        "n_inversion_ok": n_ok,
        "n_safe": n_safe,
        "n_maximal": n_max,
        "examples": results[:5],
    }


def b104_orbits(n: int) -> dict:
    """D4 orbits of points and how often each is used by max sets."""
    board = Board(square_points(n))
    max_sets = load_masks(DATA / f"maximal_n{n}.bin")
    pts = square_points(n)
    V = n * n

    def d4_orbit(x, y):
        orb = set()
        for k in range(8):
            a, b = x, y
            if k & 1:
                a, b = b, a
            if k & 2:
                a = -a
            if k & 4:
                b = -b
            orb.add((a % n, b % n))  # fold back? better: keep canonical
        return frozenset((px, py) for px, py in orb if 0 <= px < n and 0 <= py < n)

    # build orbits properly (D4 of the board)
    def d4_orbit_board(x, y):
        orb = set()
        for k in range(8):
            a, b = x, y
            if k & 1:
                a, b = b, a
            if k & 2:
                a = n - 1 - a
            if k & 4:
                b = n - 1 - b
            orb.add((a, b))
        return frozenset(orb)

    orbit_of = {}
    orbits = []
    for y in range(n):
        for x in range(n):
            o = d4_orbit_board(x, y)
            if o not in orbit_of:
                orbit_of[o] = len(orbits)
                orbits.append(o)
    # point usage
    usage = Counter()
    for m in max_sets:
        for i in range(V):
            if (m >> i) & 1:
                usage[i] += 1
    orbit_usage = []
    for o in orbits:
        idxs = [pt_to_idx := (py * n + px) for (px, py) in o]
        total = sum(usage.get(i, 0) for i in idxs)
        orbit_usage.append({"orbit": sorted(o), "size": len(o), "total_usage": total,
                            "never_used": total == 0})
    never = [ou for ou in orbit_usage if ou["never_used"]]
    return {
        "n": n,
        "n_orbits": len(orbits),
        "n_never_used_orbits": len(never),
        "n_never_used_points": sum(ou["size"] for ou in never),
        "never_used_orbits": never,
        "usage_min": min(ou["total_usage"] for ou in orbit_usage) if orbit_usage else None,
    }


def main():
    out = {}
    print("=== B106/B107 ident", flush=True)
    for n in (4, 5, 6):
        print(f"n={n} ...", flush=True)
        r = b106_ident(n)
        out[f"b106_n{n}"] = r
        print(" ", {k: r[k] for k in ("n_max", "min_det", "max_det", "mean_det", "ident_curve")}, flush=True)
    out["b107_correlation"] = b107_correlation()
    print("b107", out["b107_correlation"]["pairs_n_nmax_mindet"],
          "monotone", out["b107_correlation"]["min_det_monotone_nondecreasing_in_nmax"], flush=True)

    print("=== B140 inversion", flush=True)
    for n in (4, 5):
        print(f"n={n} ...", flush=True)
        r = b140_inversion(n)
        out[f"b140_n{n}"] = r
        print(" ", {k: r[k] for k in ("n_trials", "n_inversion_ok", "n_safe", "n_maximal")}, flush=True)

    print("=== B104 orbits", flush=True)
    for n in (4, 5, 6):
        print(f"n={n} ...", flush=True)
        r = b104_orbits(n)
        out[f"b104_n{n}"] = r
        print(" ", {k: r[k] for k in ("n_orbits", "n_never_used_orbits", "n_never_used_points", "usage_min")}, flush=True)

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
