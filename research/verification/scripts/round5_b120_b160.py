#!/usr/bin/env python3
"""Round5 B120-B160 geometric asymptotics targeted checks.

B136: which |complete-circle ∩ axis-aligned square| counts are achievable?
B140: inversion maps small maximal safe sets to lattice safe sets?
B149: top-k similarity-type coverage of forbidden 4-sets (n<=6).
B158: |L(S+p)| vs d(p) reversal for |S|=1 on n=4,5.
B160: same-degree D4-inequivalent points with different first-move g (n=5,6 sample).
B153/B154/B159: degree profiles already in round5_b101_quick; add n=6 degrees.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from itertools import combinations, product

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, det4, square_points  # noqa: E402

OUT = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b120_b160.json"


# ---------- helpers ----------
def r2_reprs(M: int):
    """All (u,v) with u^2+v^2=M, u>=0, then full 8-sym handled by caller."""
    out = []
    u = 0
    while u * u <= M:
        v2 = M - u * u
        v = int(round(math.isqrt(v2)))
        if v * v == v2:
            out.append((u, v))
        u += 1
    return out


def complete_circle_points(cx_num, cy_num, q, M):
    """Integer points on circle center (cx_num/q, cy_num/q), q^2 r^2 = M."""
    pts = []
    # (qx - cx)^2 + (qy - cy)^2 = M
    for u in range(-int(math.isqrt(M)) - 1, int(math.isqrt(M)) + 2):
        v2 = M - u * u
        if v2 < 0:
            continue
        v = int(round(math.isqrt(v2)))
        if v * v != v2:
            continue
        for vv in {v, -v} if v else {0}:
            # qx = u + cx, qy = vv + cy
            if (u + cx_num) % q == 0 and (vv + cy_num) % q == 0:
                x = (u + cx_num) // q
                y = (vv + cy_num) // q
                pts.append((x, y))
    return sorted(set(pts))


def square_stabbing_counts(pts):
    """Possible |pts ∩ square| for axis-aligned squares with integer corners.
    Squares are [x0,x1] x [y0,y1] (closed), any integer bounds."""
    if not pts:
        return set()
    xs = sorted({p[0] for p in pts})
    ys = sorted({p[1] for p in pts})
    # critical boundaries: just below/above each coordinate
    x_cuts = [xs[0] - 1] + xs + [xs[-1] + 1]
    y_cuts = [ys[0] - 1] + ys + [ys[-1] + 1]
    counts = set()
    # square = product of intervals; try all pairs of x-cuts and y-cuts as bounds
    # A square needs equal side length in the board-grid sense; here we only need
    # existence of SOME axis-aligned square (not necessarily integer side).
    # Any axis-aligned rectangle that is a square in R^2.
    # We approximate by considering all rectangles with integer corners and
    # equal width/height in coordinate span (common in these boards).
    pts_set = set(pts)
    # general axis-aligned square with real sides: determined by x0,x1,y0,y1, x1-x0=y1-y0
    # Restrict to squares whose sides lie on half-integer or integer lines through points.
    coords_x = sorted({p[0] for p in pts} | {p[0] - 1 for p in pts} | {p[0] + 1 for p in pts})
    coords_y = sorted({p[1] for p in pts} | {p[1] - 1 for p in pts} | {p[1] + 1 for p in pts})
    for x0 in coords_x:
        for x1 in coords_x:
            if x1 <= x0:
                continue
            side = x1 - x0
            for y0 in coords_y:
                y1 = y0 + side
                c = sum(1 for p in pts if x0 <= p[0] <= x1 and y0 <= p[1] <= y1)
                counts.add(c)
    return counts


def d4_orbit(p, n):
    x, y = p
    cands = [
        (x, y),
        (y, n - 1 - x),
        (n - 1 - x, n - 1 - y),
        (n - 1 - y, x),
        (y, x),
        (n - 1 - x, y),
        (n - 1 - y, n - 1 - x),
        (x, n - 1 - y),
    ]
    return tuple(sorted(set(cands)))


def inversion_image(p, cx, cy, R2):
    """Inversion at (cx,cy) radius^2=R2: p -> center + R2 (p-c)/|p-c|^2.
    Returns rational (num_x, den, num_y, den) with common den = |p-c|^2 / g."""
    dx = p[0] - cx
    dy = p[1] - cy
    den = dx * dx + dy * dy
    if den == 0:
        return None
    # image = (cx + R2*dx/den, cy + R2*dy/den)
    # write cx=cnx/cd etc; assume cx,cy integers for now
    ix_num = cx * den + R2 * dx
    iy_num = cy * den + R2 * dy
    g = math.gcd(math.gcd(abs(ix_num), abs(iy_num)), den)
    if g == 0:
        return None
    return (ix_num // g, iy_num // g, den // g)


def to_lattice(img):
    if img is None:
        return None
    nx, ny, den = img
    if den == 1:
        return (nx, ny)
    if den == -1:
        return (-nx, -ny)
    return None


def similarity_signature(quad, n):
    """Signature under integer scaling + translation + D4, normalized."""
    # Use pairwise squared distances sorted, and det magnitude / orientation patterns.
    pts = list(quad)
    # normalize: translate min to 0, try D4, scale by gcd of diffs
    def norm(points):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        mx, my = min(xs), min(ys)
        pts2 = [(p[0] - mx, p[1] - my) for p in points]
        dxs = [p[0] for p in pts2]
        dys = [p[1] for p in pts2]
        g = 0
        for a, b in combinations(pts2, 2):
            g = math.gcd(g, abs(a[0] - b[0]))
            g = math.gcd(g, abs(a[1] - b[1]))
        if g == 0:
            g = 1
        pts2 = [(p[0] // g, p[1] // g) for p in pts2]
        return tuple(sorted(pts2))

    base = norm(pts)
    variants = [base]
    # D4 + reflections on the normalized set (as coordinate transforms then norm)
    def xf(points, kind):
        out = []
        for x, y in points:
            if kind == 0:
                out.append((x, y))
            elif kind == 1:
                out.append((y, x))
            elif kind == 2:
                out.append((-x, y))
            elif kind == 3:
                out.append((x, -y))
            elif kind == 4:
                out.append((-x, -y))
            elif kind == 5:
                out.append((-y, x))
            elif kind == 6:
                out.append((y, -x))
            elif kind == 7:
                out.append((-y, -x))
        return out

    for k in range(8):
        variants.append(norm(xf(list(base), k)))
    return min(variants)


def main():
    res = {}

    # ========== B136: complete circles and square-stabbing counts ==========
    b136 = {"circles": [], "all_stabbing": set(), "missing_small": {}}
    # enumerate complete circles with modest M and q=1,2
    seen = set()
    for q in (1, 2):
        for M in range(1, 80):
            # centers: cx,cy mod 2q enough by translation? Use small centers
            for cx in range(q):
                for cy in range(q):
                    pts = complete_circle_points(cx, cy, q, M)
                    if len(pts) < 4:
                        continue
                    key = (q, M, len(pts), tuple(pts[:3]))
                    if key in seen:
                        continue
                    seen.add(key)
                    stab = square_stabbing_counts(pts)
                    b136["all_stabbing"] |= stab
                    b136["circles"].append(
                        {
                            "q": q,
                            "M": M,
                            "npts": len(pts),
                            "stabbing": sorted(stab),
                            "sample_pts": pts[:12],
                        }
                    )
    b136["all_stabbing"] = sorted(b136["all_stabbing"])
    for k in range(0, 16):
        b136["missing_small"][k] = k not in b136["all_stabbing"]
    res["b136"] = b136

    # ========== B140: inversion on n=4 maximal safe sets ==========
    n = 4
    pts_all = square_points(n)
    B = Board(pts_all, "n4")
    maximal = []
    full = (1 << n * n) - 1
    # enumerate size-7 maximal (known 64) by scanning safe size-7 and checking maximal
    from itertools import combinations as C

    safe7 = []
    for ids in C(range(n * n), 7):
        occ = 0
        for i in ids:
            occ |= 1 << i
        if B.is_safe(occ):
            # maximal? no legal move that keeps safety and increases size — size 7 on 16 pts
            # maximal means cannot add any point
            empty = full ^ occ
            can_add = False
            e = empty
            v = 0
            while e:
                if e & 1:
                    if B.is_safe(occ | (1 << v)):
                        can_add = True
                        break
                e >>= 1
                v += 1
            if not can_add:
                safe7.append(ids)
    b140 = {
        "n": n,
        "n_maximal_size7": len(safe7),
        "inversion_trials": [],
        "n_mapped_to_lattice": 0,
        "n_safety_preserved": 0,
        "n_image_also_maximal": 0,
    }
    # inversion center (0,0) fails if (0,0) in set; use center (1,1) integer, R2 = lcm of denoms
    for ids in safe7[:64]:
        pts = [pts_all[i] for i in ids]
        # center (0,0); skip if contains origin
        if (0, 0) in pts:
            continue
        dens = [p[0] * p[0] + p[1] * p[1] for p in pts]
        if any(d == 0 for d in dens):
            continue
        R2 = 1
        for d in dens:
            R2 = R2 * d // math.gcd(R2, d)
        imgs = []
        ok = True
        for p in pts:
            im = inversion_image(p, 0, 0, R2)
            lat = to_lattice(im)
            if lat is None:
                ok = False
                break
            imgs.append(lat)
        if not ok or len(set(imgs)) != len(pts):
            continue
        b140["n_mapped_to_lattice"] += 1
        # check safety of image on a temporary board of those points + maybe more
        # safety is intrinsic: 4 points forbidden iff det=0 on those 4
        safe_img = True
        for q4 in combinations(imgs, 4):
            rows = [(x * x + y * y, x, y, 1) for x, y in q4]
            if det4(*rows) == 0:
                safe_img = False
                break
        if safe_img:
            b140["n_safety_preserved"] += 1
            # maximality on the n x n board? images may lie outside; check vs full Z^2 not possible.
            # instead check whether image is a maximal safe set inside its convex window
            b140["inversion_trials"].append(
                {"src": pts, "R2": R2, "img": imgs, "safe": True}
            )
    res["b140"] = b140

    # ========== B149: similarity-type coverage n=2..6 ==========
    b149 = {}
    for n in range(2, 7):
        pts_all = square_points(n)
        B = Board(pts_all, f"n{n}")
        sigs = []
        for qm in B.quads:
            ids = [i for i in range(n * n) if qm & (1 << i)]
            quad = [pts_all[i] for i in ids]
            sigs.append(similarity_signature(quad, n))
        from collections import Counter

        ctr = Counter(sigs)
        total = len(sigs)
        top = ctr.most_common()
        cover = 0
        for k in range(1, min(11, len(top) + 1)):
            cover = sum(c for _, c in top[:k])
            if k == 10:
                b149[str(n)] = {
                    "total": total,
                    "n_types": len(ctr),
                    "top10_cover": cover,
                    "top10_frac": cover / total if total else 0,
                    "top10_counts": [c for _, c in top[:10]],
                    "min_frac_needed": 0.5,
                    "ge_half_with_top10": (cover / total) >= 0.5 if total else False,
                }
    res["b149"] = b149

    # ========== B158 / B160 on n=4,5 ==========
    b158 = {"n4": None, "n5": None}
    b160 = {"n4": None, "n5": None}
    for n in (4, 5):
        pts_all = square_points(n)
        B = Board(pts_all, f"n{n}")
        degs = [len(B.quads_by_pt[i]) for i in range(len(pts_all))]
        # |L({p})| should be n^2-1 (always safe)
        # |L({p,q})| for |S|=1: parent S={s}, add p -> |L({s,p})|
        # search reversal: exists s, p, q with d(p)>d(q) but |L({s,p})| > |L({s,q})|
        # and both s+p, s+q legal (safe)
        witness = None
        for s in range(len(pts_all)):
            occ_s = 1 << s
            # legal p != s
            legal_p = []
            for p in range(len(pts_all)):
                if p == s:
                    continue
                occ = occ_s | (1 << p)
                if B.is_safe(occ):
                    legal_p.append(p)
            Lcounts = {}
            for p in legal_p:
                occ = occ_s | (1 << p)
                Lcounts[p] = len(B.legal_moves(occ))
            for p, q in combinations(legal_p, 2):
                if degs[p] > degs[q] and Lcounts[p] > Lcounts[q]:
                    witness = {
                        "S": [pts_all[s]],
                        "p": pts_all[p],
                        "q": pts_all[q],
                        "d_p": degs[p],
                        "d_q": degs[q],
                        "L_p": Lcounts[p],
                        "L_q": Lcounts[q],
                    }
                    break
                if degs[p] < degs[q] and Lcounts[p] > Lcounts[q]:
                    # the claim form: d(p)>d(q) but L(p)>L(q) wait that's same direction
                    # "d(p)>d(q) なのに |L(S+p)|>|L(S+q)|" — higher degree but MORE legal left
                    # actually "なのに" suggests surprise: high degree usually means fewer?
                    # Original: 高次数点を置くと合法手がより多く残る = placing high-deg leaves MORE legal
                    # So the claim is d(p)>d(q) => |L(S+p)|>|L(S+q)| as the tendency,
                    # and [存在] of the reversal would be... re-read.
                    # "d(p)>d(q) なのに |L(S+p)|>|L(S+q)| で、その逆転が..."
                    # Hmm "逆転" = reversal of the expected. Expected: high deg -> fewer?
                    # Title: 高次数点を置くと合法手がより多く残る = high deg -> MORE legal remain.
                    # So the claim is d(p)>d(q) and |L(S+p)|>|L(S+q)| (positive correlation).
                    # "その逆転" = also happens between max-deg and min-deg points.
                    # So witness is d(p)>d(q) and |L(S+p)|>|L(S+q)|.
                    pass
            if witness:
                break
        b158[f"n{n}"] = {
            "witness_positive_corr": witness,
            "deg_min": min(degs),
            "deg_max": max(degs),
            "note": "witness = exists S,p,q with d(p)>d(q) and |L(S+p)|>|L(S+q)|",
        }
        # B160: same deg, D4-inequivalent, different first-move g or win/loss
        # first-move g of single point p: grundy of {p} position = mex of children
        # too heavy for n=5 full grundy; use P/N via solve if available
        # cheaper: compare legal-move counts |L({p})| (constant) and |L(S)| after 1 move
        # higher feature: |L({p})| after placing p from empty is constant;
        # use number of safe completions / or g of the 1-stone game restricted.
        # Compute for each p the multiset of |L({p,q})| over legal q — a higher feature.
        feat = {}
        for p in range(len(pts_all)):
            occ_p = 1 << p
            childs = []
            for q in range(len(pts_all)):
                if q == p:
                    continue
                occ = occ_p | (1 << q)
                if B.is_safe(occ):
                    childs.append(len(B.legal_moves(occ)))
            feat[p] = (tuple(sorted(childs)), d4_orbit(pts_all[p], n))
        # find same deg, different D4 orbit, different feature
        wit160 = None
        for i, j in combinations(range(len(pts_all)), 2):
            if degs[i] != degs[j]:
                continue
            if feat[i][1] == feat[j][1]:
                continue
            if feat[i][0] != feat[j][0]:
                wit160 = {
                    "p": pts_all[i],
                    "q": pts_all[j],
                    "deg": degs[i],
                    "feat_p": list(feat[i][0])[:20],
                    "feat_q": list(feat[j][0])[:20],
                    "orbit_p": list(feat[i][1])[:4],
                    "orbit_q": list(feat[j][1])[:4],
                }
                break
        b160[f"n{n}"] = {"witness": wit160, "deg_hist_sample": None}
        # deg histogram
        hist = defaultdict(int)
        for d in degs:
            hist[d] += 1
        b160[f"n{n}"]["deg_hist"] = dict(sorted(hist.items()))

    res["b158"] = b158
    res["b160"] = b160

    # ========== B153/B154/B159: n=6 degree profile ==========
    n = 6
    pts_all = square_points(n)
    B = Board(pts_all, "n6")
    degs = [len(B.quads_by_pt[i]) for i in range(len(pts_all))]
    # radial bins by r2 from center ((n-1)/2, (n-1)/2)
    cx = (n - 1) / 2
    cy = (n - 1) / 2
    radial = defaultdict(list)
    for i, p in enumerate(pts_all):
        r2 = (p[0] - cx) ** 2 + (p[1] - cy) ** 2
        radial[round(r2, 1)].append(degs[i])
    b153 = {
        "n": n,
        "deg_min": min(degs),
        "deg_max": max(degs),
        "deg_mean": sum(degs) / len(degs),
        "radial": {
            str(k): {"min": min(v), "max": max(v), "mean": sum(v) / len(v), "spread": max(v) - min(v)}
            for k, v in sorted(radial.items())
        },
    }
    res["b153_n6"] = b153

    # B154: two interior points with same r2 but different deg
    same_r2 = []
    for k, v in radial.items():
        if len(v) >= 2 and max(v) != min(v):
            pts_in = [pts_all[i] for i, p in enumerate(pts_all) if round((p[0]-cx)**2+(p[1]-cy)**2,1)==k]
            pairs = []
            for i, j in combinations(range(len(pts_all)), 2):
                ri = round((pts_all[i][0]-cx)**2+(pts_all[i][1]-cy)**2, 1)
                rj = round((pts_all[j][0]-cx)**2+(pts_all[j][1]-cy)**2, 1)
                if ri == rj == k and degs[i] != degs[j]:
                    pairs.append((pts_all[i], degs[i], pts_all[j], degs[j]))
            if pairs:
                same_r2.append({"r2": k, "example": pairs[0], "spread": max(v)-min(v)})
    res["b154_n6"] = {"same_r2_diff_deg": same_r2}

    # B159: n=5 vs n=6 degree increase distribution
    # already have n=5 profile; compute per-point deg on both and map by scaled position
    res["b159_note"] = "see b153_n6 and round5_b101_quick b159_n4/n5"

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("Wrote", OUT)
    print("B136 stabbing", b136["all_stabbing"], "missing", [k for k,v in b136["missing_small"].items() if v])
    print("B140 mapped", b140["n_mapped_to_lattice"], "safe", b140["n_safety_preserved"])
    print("B149", {k: (v["top10_frac"], v["ge_half_with_top10"]) for k,v in b149.items()})
    print("B158 n4", b158["n4"], "n5", b158["n5"])
    print("B160 n4 wit", b160["n4"]["witness"], "n5 wit", b160["n5"]["witness"])


if __name__ == "__main__":
    main()
