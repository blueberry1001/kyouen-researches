#!/usr/bin/env python3
"""Round3 chunk-4 A1: rule variants + nimber range (B228, B229, B230, B231).

n=4 is exhaustive (5811 states, ~0.3 s per full solve).  Outputs
research/verification/round3_chunk4_A1.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from round3_chunk4_core import (  # noqa: E402
    Solve, quad_masks, square_points, is_collinear4, d4_perms, apply_perm_mask,
    det4, pt,
)

OUT = Path(__file__).resolve().parents[1] / "round3_chunk4_A1.json"
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


_REP: dict = {}


def save(rep):
    """Write the report so far; a crash or timeout never loses finished work."""
    _REP.update(rep)
    OUT.write_text(json.dumps(_REP, indent=1, ensure_ascii=False, default=str))


def bits(mask):
    out, v, m = [], 0, mask
    while m:
        if m & 1:
            out.append(v)
        m >>= 1
        v += 1
    return out


def conic_family(mask, pts):
    """('circle'|'line', sorted board-point ids on that conic)"""
    ids = bits(mask)
    P = [pts[i] for i in ids]
    if is_collinear4(P):
        (x0, y0), (x1, y1) = P[0], P[1]
        A, B = y1 - y0, x0 - x1
        C = -(A * x0 + B * y0)
        return ("line", tuple(i for i, (x, y) in enumerate(pts)
                              if A * x + B * y + C == 0))
    (x0, y0), (x1, y1), (x2, y2) = P[0], P[1], P[2]
    a1, b1 = x1 - x0, y1 - y0
    a2, b2 = x2 - x0, y2 - y0
    det = a1 * b2 - a2 * b1
    s1 = x1 * x1 + y1 * y1 - x0 * x0 - y0 * y0
    s2 = x2 * x2 + y2 * y2 - x0 * x0 - y0 * y0
    A = (s1 * b2 - s2 * b1) / det
    B = (a1 * s2 - a2 * s1) / det
    C = (x0 * x0 + y0 * y0 - A * x0 - B * y0) / 2.0
    K = A * A + B * B + 4 * C
    return ("circle", tuple(i for i, (x, y) in enumerate(pts)
                            if abs((2 * x - A) ** 2 + (2 * y - B) ** 2 - K) < 1e-9))


def main():
    rep = {}
    N = 4
    V = N * N
    pts = square_points(N)
    quads = quad_masks(N, pts)
    log(f"n=4 |Q|={len(quads)}")
    base = Solve(quads, V)
    base_pn = base.pn()
    pn0 = bool(base_pn[0])
    log(f"base winner = {'First' if pn0 else 'Second'}")

    fam = {q: conic_family(q, pts) for q in quads}
    fam_size = {q: len(v[1]) for q, v in fam.items()}
    kinds = Counter(v[0] for v in fam.values())
    log(f"conics: {dict(kinds)}, point-counts {sorted(set(fam_size.values()))}")

    # ================= B228 ==========================================
    # Order by DECREASING number of board points on the conic and ADD the
    # forbidden quads in that order (smallest conics first) starting from the
    # empty family.  Equivalent to the RELEASE order used before, but
    # expressed in the hypothesis' own words ("círculos con muchos puntos
    # primero").
    order = sorted(quads, key=lambda q: (-fam_size[q], q))
    t0 = time.time()
    seq, keep = [], []
    seq.append(("Second", "empty family"))
    for j, q in enumerate(order):
        keep.append(q)
        s = Solve(keep, V)
        seq.append(("First" if s.pn()[0] else "Second", f"added conic with "
                    f"{fam_size[q]} board pts"))
    flips = [i for i in range(1, len(seq)) if seq[i][0] != seq[i - 1][0]]
    rep["B228"] = {
        "n": N, "n_quads": len(quads),
        "order_rule": "add forbidden quads by DECREASING conic board-point count",
        "conic_kind_counts": dict(kinds),
        "conic_point_counts_present": sorted(set(fam_size.values())),
        "n_winner_flips": len(flips),
        "first_flip_after_adding": flips[0] if flips else None,
        "second_flip_after_adding": flips[1] if len(flips) > 1 else None,
        "winners_along_sequence": [w for w, _ in seq[:40]],
        "n_distinct_winners": len({w for w, _ in seq}),
        "seconds": round(time.time() - t0, 1),
    }
    log(f"B228: {len(flips)} flips, first at step {flips[0] if flips else None}")
    save(rep)

    # ================= B229 ==========================================
    near = []
    for ids in combinations(range(V), 4):
        d = abs(det4(*[pt(*pts[i]) for i in ids]))
        if d:
            near.append((d, sum(1 << i for i in ids)))
    near.sort()
    log(f"B229: {len(near)} non-degenerate 4-sets, min|det|={near[0][0]}, "
        f"det hist {dict(sorted(Counter(d for d,_ in near).items())[:5])}")
    perms = d4_perms(N)
    rows = []
    for t in (0, 1, 2, 3, 4, 6, 8, 12):
        famq = list(quads) + [m for d, m in near if d <= t]
        s = Solve(famq, V)
        K = max(m.bit_count() for m in s.states)
        maximals = [m for m in s.states
                    if m.bit_count() == K and s.legal_mask(m) == 0]
        orbkey = {min(apply_perm_mask(m, p) for p in perms) for m in maximals}
        fixed = sum(1 for m in maximals
                    if all(apply_perm_mask(m, p) == m for p in perms))
        rows.append({
            "t": t, "n_quads": len(famq), "n_new_quads": len(famq) - len(quads),
            "winner": "First" if s.pn()[0] else "Second",
            "max_safe_K": K, "n_maximal_at_K": len(maximals),
            "n_D4_orbits": len(orbkey),
            "n_D4_fixed_maximals": fixed,
            "orbit_size_multiset": sorted(Counter(
                sum(1 for m in maximals
                    if min(apply_perm_mask(m, p) for p in perms) == ok)
                for ok in orbkey).values(), reverse=True),
            "maximal_sets": [sorted((i % N, i // N) for i in bits(m))
                             for m in sorted(maximals)[:6]],
        })
        log(f"B229 t={t}: {orbit_data}" if False else
            f"B229 t={t}: win={rows[-1]['winner']} K={K} "
            f"max={len(maximals)} orbits={len(orbkey)} fixed={fixed}")
    rep["B229"] = {
        "n": N, "min_abs_det_nonzero": near[0][0],
        "abs_det_histogram": {str(k): v for k, v in
                              sorted(Counter(d for d, _ in near).items())},
        "by_threshold": rows,
    }
    save(rep)

    # ================= B230 ==========================================
    t0 = time.time()
    b230 = {"n": N, "variants": {}}
    base_pn_by_mask = {m: bool(base_pn[base.idx[m]]) for m in base.states}
    for k in sorted(set(fam_size.values())):
        dropped = [q for q in quads if fam_size[q] <= k]
        s = Solve([q for q in quads if fam_size[q] > k], V)
        pn = s.pn()
        layers = {}
        for lev, lv in enumerate(s.levels):
            if len(lv) == 0:
                continue
            same = sum(1 for i in lv
                       if base_pn_by_mask.get(s.states[int(i)]) ==
                       bool(pn[int(i)]))
            layers[lev] = {"n_states": int(len(lv)), "preserved": same,
                           "frac": round(same / len(lv), 4)}
        b230["variants"][f"drop_all_conics_with_at_most_{k}_board_points"] = {
            "n_dropped": len(dropped), "n_kept": len(quads) - len(dropped),
            "winner": "First" if pn[0] else "Second",
            "fully_preserved_layers": [lv for lv, r in layers.items()
                                       if r["frac"] == 1.0],
            "per_layer": layers,
        }
        log(f"B230 k<={k}: drop {len(dropped)} keep {len(quads)-len(dropped)} "
            f"win={b230['variants'][f'drop_all_conics_with_at_most_{k}_board_points']['winner']} "
            f"perfect layers={b230['variants'][f'drop_all_conics_with_at_most_{k}_board_points']['fully_preserved_layers']}")
    b230["seconds"] = round(time.time() - t0, 1)
    rep["B230"] = b230
    save(rep)

    # ================= B231 ==========================================
    b231 = {"squares": {}}
    for n in (2, 3, 4, 5):
        s = Solve(quad_masks(n), n * n)
        g = s.grundy()
        b231["squares"][f"{n}x{n}"] = {
            "max_g": int(g.max()), "n_states": s.N,
            "values_present": sorted({int(x) for x in g}),
            "g1_positions_count": int((g == 1).sum()),
        }
        log(f"B231 {n}x{n}: max g={int(g.max())} states={s.N}")
    b231["rects"] = {}
    for (w, h) in ((3, 4), (4, 3), (3, 5), (5, 3), (4, 5), (5, 4), (2, 6), (6, 2)):
        pts2 = [(x, y) for y in range(h) for x in range(w)]
        qq = quad_masks(None, pts2)
        t0 = time.time()
        s = Solve(qq, w * h)
        g = s.grundy()
        b231["rects"][f"{w}x{h}"] = {
            "V": w * h, "n_quads": len(qq), "n_states": s.N,
            "max_g": int(g.max()),
            "values_present": sorted({int(x) for x in g}),
            "K_max": max(m.bit_count() for m in s.states),
            "seconds": round(time.time() - t0, 1),
        }
        log(f"B231 {w}x{h}: max g={int(g.max())} states={s.N} "
            f"({time.time()-t0:.0f}s)")
    b231["note"] = ("max g over all boards tried; the quantifier 'for every m' "
                    "needs boards with unbounded number of points and is not "
                    "reachable by brute force here.")
    rep["B231"] = b231
    save(rep)

    log("wrote", OUT)


if __name__ == "__main__":
    main()
