#!/usr/bin/env python3
"""B564 follow-up + D4 orbit of B561 witnesses + controlled B565.

Deep-dive residual hypergraphs of the 4 n=5 log-concavity failures.
Classify the failures by residual type.  Also compute Spearman of
peak/Eterm/g controlling for (k, |L|) bins.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b561.json"


def mask_of(pts, n):
    m = 0
    for x, y in pts:
        m |= 1 << (y * n + x)
    return m


def pts_of(mask, n):
    return [(i % n, i // n) for i in range(n * n) if (mask >> i) & 1]


def d4_images(mask, n):
    def pid(x, y):
        return y * n + x

    gens = [
        lambda x, y: (x, y),
        lambda x, y: (n - 1 - y, x),
        lambda x, y: (n - 1 - x, n - 1 - y),
        lambda x, y: (y, n - 1 - x),
        lambda x, y: (n - 1 - x, y),
        lambda x, y: (x, n - 1 - y),
        lambda x, y: (y, x),
        lambda x, y: (n - 1 - y, n - 1 - x),
    ]
    imgs = set()
    for fn in gens:
        m = 0
        for x, y in pts_of(mask, n):
            m |= 1 << pid(*fn(x, y))
        imgs.add(m)
    return imgs


def legal_mask(board, occ):
    out = 0
    for v in board.legal_moves(occ):
        out |= 1 << v
    return out


def residual_R(board, occ):
    empties = board.full ^ occ
    L = legal_mask(board, occ)
    seen = set()
    for q in board.quads:
        rest = q & empties
        if rest and (rest & ~L) == 0:
            seen.add(rest)
    minimal = []
    for r in seen:
        ok = True
        x = r
        while x:
            x = (x - 1) & r
            if x == 0:
                break
            if x in seen:
                ok = False
                break
        if ok:
            minimal.append(r)
    return sorted(minimal)


def independent_set_counts(R, umask):
    """counts[t] = # t-subsets of umask avoiding every r in R."""
    ulist = [i for i in range(umask.bit_length()) if (umask >> i) & 1]
    Ru = [r for r in R if (r & ~umask) == 0]
    counts = [0] * (len(ulist) + 1)

    def dfs(occ, idx, sz):
        counts[sz] += 1
        for j in range(idx, len(ulist)):
            bit = 1 << ulist[j]
            ok = True
            for r in Ru:
                if (r & (occ | bit)) == r:
                    ok = False
                    break
            if ok:
                dfs(occ | bit, j + 1, sz + 1)

    dfs(0, 0, 0)
    return counts, Ru


def is_log_concave(f):
    a = list(f)
    while a and a[0] == 0:
        a.pop(0)
    while a and a[-1] == 0:
        a.pop()
    if len(a) < 3:
        return True, None
    for k in range(1, len(a) - 1):
        if a[k] * a[k] < a[k - 1] * a[k + 1]:
            return False, k
    return True, None


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for i, idx in enumerate(order):
            r[idx] = i
        return r
    if len(xs) < 3:
        return 0.0
    rx, ry = rank(xs), rank(ys)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    denx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(len(rx))))
    deny = math.sqrt(sum((ry[i] - my) ** 2 for i in range(len(ry))))
    return num / (denx * deny) if denx * deny else 0.0


def main():
    n = 5
    board = board_square(n)
    report = json.loads(OUT.read_text(encoding="utf-8"))

    # witnesses from previous run
    fails = report["n5"]["b561_logc_failures"]
    masks = [mask_of(rec["pts"], n) for rec in fails]

    # D4 orbits
    orbits = []
    used = set()
    for m in masks:
        if m in used:
            continue
        orb = d4_images(m, n)
        used |= orb
        orbits.append(sorted(orb))

    # residual dump
    details = []
    for rec, m in zip(fails, masks):
        R = residual_R(board, m)
        L = legal_mask(board, m)
        r2 = [r for r in R if r.bit_count() == 2]
        r3 = [r for r in R if r.bit_count() == 3]
        r4 = [r for r in R if r.bit_count() == 4]
        # counts on full L
        cnt_L, _ = independent_set_counts(R, L)
        # search minimal U with |U|<=10 whose residual-induced counts break logc
        pts_l = [i for i in range(board.V) if (L >> i) & 1]
        min_u = None
        for usz in range(3, min(11, len(pts_l) + 1)):
            found = False
            for combo in combinations(pts_l, usz):
                um = 0
                for i in combo:
                    um |= 1 << i
                counts, Ru = independent_set_counts(R, um)
                ok, fk = is_log_concave(counts)
                if not ok:
                    min_u = {
                        "U_pts": pts_of(um, n),
                        "U_size": usz,
                        "counts": counts,
                        "fail_k": fk,
                        "R_U": [pts_of(r, n) for r in Ru],
                        "R_U_sizes": [r.bit_count() for r in Ru],
                    }
                    found = True
                    break
            if found:
                break
        # also: the unique max extension (f has 1 four-point extension)
        # find it
        max_ext = None
        empties = [i for i in range(board.V) if not (m >> i) & 1]
        for combo in combinations(empties, 4):
            t = m
            for i in combo:
                t |= 1 << i
            if board.is_safe(t):
                max_ext = t
                break
        details.append({
            "S_pts": rec["pts"],
            "S_mask": m,
            "f": [x for x in rec["f"] if x != 0 or True][:6],
            "L_pts": pts_of(L, n),
            "L_size": L.bit_count(),
            "counts_on_L": cnt_L,
            "n_R2": len(r2),
            "n_R3": len(r3),
            "n_R4": len(r4),
            "R3_pts": [pts_of(r, n) for r in r3],
            "R4_pts": [pts_of(r, n) for r in r4],
            "max_ext_pts": pts_of(max_ext, n) if max_ext else None,
            "min_U": min_u,
        })

    # B565 controlled: reload rows-like sample using stored rows_sample is too small.
    # Recompute small sample with bins (k, L) and within-bin spearman.
    # Use n=4 all + n=5 sample of 200.
    import random
    rng = random.Random(42)

    def peak_index(f):
        nz = [(i, x) for i, x in enumerate(f) if x > 0]
        return max(nz, key=lambda t: (t[1], -t[0]))[0] if nz else None

    def exact_term(board, occ, memo=None):
        if memo is None:
            memo = {}
        if occ in memo:
            return memo[occ]
        mv = board.legal_moves(occ)
        if not mv:
            d = {occ.bit_count(): 1.0}
            memo[occ] = d
            return d
        acc = defaultdict(float)
        w = 1.0 / len(mv)
        for u in mv:
            for t, p in exact_term(board, occ | (1 << u), memo).items():
                acc[t] += p * w
        d = dict(acc)
        memo[occ] = d
        return d

    def grundy_all(board):
        memo = {}

        def ev(occ):
            if occ in memo:
                return memo[occ]
            mv = board.legal_moves(occ)
            if not mv:
                memo[occ] = 0
                return 0
            seen = set()
            for u in mv:
                seen.add(ev(occ | (1 << u)))
            g = 0
            while g in seen:
                g += 1
            memo[occ] = g
            return g
        ev(0)
        return memo

    # fvecs via quick subset-zeta on n=4 (small)
    def enum_safe(board):
        V = board.V
        by = [[] for _ in range(V + 1)]

        def dfs(occ, start, size):
            by[size].append(occ)
            for v in range(start, V):
                bit = 1 << v
                ok = True
                for q in board.quads_by_pt[v]:
                    if (q & (occ | bit)) == q:
                        ok = False
                        break
                if ok:
                    dfs(occ | bit, v + 1, size + 1)

        dfs(0, 0, 0)
        return by

    def all_fvecs(by):
        safe_set = set()
        for g in by:
            safe_set.update(g)
        fvec = {m: [0] * 20 for m in safe_set}
        for g in by:
            for T in g:
                kT = T.bit_count()
                sub = T
                while True:
                    fs = fvec.get(sub)
                    if fs is not None:
                        fs[kT - sub.bit_count()] += 1
                    if sub == 0:
                        break
                    sub = (sub - 1) & T
        return fvec

    b565_ctrl = {}
    for nn in (4, 5):
        b = board_square(nn)
        by = enum_safe(b)
        fvec = all_fvecs(by)
        gm = grundy_all(b)
        # sample S with 4<=|L|<=10
        cand = []
        for m in fvec:
            Lsz = legal_mask(b, m).bit_count()
            if 4 <= Lsz <= 10:
                cand.append(m)
        rng.shuffle(cand)
        cand = cand[: min(300 if nn == 5 else 800, len(cand))]
        rows = []
        for m in cand:
            Lsz = legal_mask(b, m).bit_count()
            dist = exact_term(b, m)
            eterm = sum(t * p for t, p in dist.items())
            rows.append({
                "k": m.bit_count(),
                "L": Lsz,
                "peak": peak_index(fvec[m]),
                "g": gm[m],
                "Eterm": eterm,
            })
        # within-bin spearman for bins (k,L) with >=6 members
        bins = defaultdict(list)
        for r in rows:
            bins[(r["k"], r["L"])].append(r)
        peak_sp = []
        g_sp = []
        for key, grp in bins.items():
            if len(grp) < 6:
                continue
            xs_p = [r["peak"] if r["peak"] is not None else 0 for r in grp]
            xs_g = [r["g"] for r in grp]
            ys = [r["Eterm"] for r in grp]
            peak_sp.append((key, len(grp), spearman(xs_p, ys)))
            g_sp.append((key, len(grp), spearman(xs_g, ys)))
        # overall
        xs_p = [r["peak"] if r["peak"] is not None else 0 for r in rows]
        xs_g = [r["g"] for r in rows]
        ys = [r["Eterm"] for r in rows]
        b565_ctrl[f"n{nn}"] = {
            "n_rows": len(rows),
            "overall_spearman_peak": spearman(xs_p, ys),
            "overall_spearman_g": spearman(xs_g, ys),
            "within_bin_peak": peak_sp[:12],
            "within_bin_g": g_sp[:12],
            "mean_abs_peak": (
                sum(abs(s) for _, _, s in peak_sp) / len(peak_sp) if peak_sp else None
            ),
            "mean_abs_g": (
                sum(abs(s) for _, _, s in g_sp) / len(g_sp) if g_sp else None
            ),
            "n_bins": len(peak_sp),
        }

    report["n5"]["b561_orbits"] = orbits
    report["n5"]["b564_detail"] = details
    report["b565_controlled"] = b565_ctrl
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("orbits", [[pts_of(m, n) for m in orb] for orb in orbits])
    for d in details:
        print("S", d["S_pts"], "L", d["L_size"], "R3", d["n_R3"], "R4", d["n_R4"])
        print("  max_ext", d["max_ext_pts"], "minU", None if not d["min_U"] else d["min_U"]["U_size"])
    print("b565", json.dumps(b565_ctrl, indent=2)[:2000])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
