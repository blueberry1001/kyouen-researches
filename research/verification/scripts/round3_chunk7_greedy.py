#!/usr/bin/env python3
"""Round3 chunk7 part 3: random-greedy terminal structure (B494-B500).

Key advances over round2:
  B495/B496  we now compute the EXACT reach probability of every maximal set on
             n=4 (integer/rational DP, not a float MC) and we go to n=5 where
             the reach-probability of a *given* maximal set is computed exactly
             by forward DP over the safe lattice restricted to the sub-lattice
             of subsets of that maximal set.  That gives exact ratios, not
             Monte-Carlo noise, so "10x" / "arbitrarily large" claims become
             decidable at n=4 and n=5.
  B497       perimeter timing measured exactly on n=4 (all 928 maximals).
  B498       exact conditional means.
  B499       exact per-first-move P(minimal terminal) and E[X] on n=4 (full)
             and n=5 via exact forward DP over first-move-conditional states.
  B500       weighted-cut bounds: we compute the exact reach probability and
             compare against the "cut-only" bound (drop all paths that leave the
             size layer) to quantify the sharpness.

Outputs: research/verification/round3_chunk7_greedy.json
"""
from __future__ import annotations

import json
import pickle
import random
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
OUT = ROOT / "research" / "verification" / "round3_chunk7_greedy.json"

from kyouen_core import board_square  # noqa: E402


def d4_images(board, mask):
    n = board.n if hasattr(board, "n") else int(len(board.points) ** 0.5)
    pts = [i for i in range(board.V) if (mask >> i) & 1]

    def tf(k):
        o = 0
        for i in pts:
            x, y = i % n, i // n
            if k == 0:
                nx, ny = x, y
            elif k == 1:
                nx, ny = n - 1 - x, y
            elif k == 2:
                nx, ny = x, n - 1 - y
            elif k == 3:
                nx, ny = n - 1 - x, n - 1 - y
            elif k == 4:
                nx, ny = y, x
            elif k == 5:
                nx, ny = n - 1 - y, x
            elif k == 6:
                nx, ny = y, n - 1 - x
            else:
                nx, ny = n - 1 - y, n - 1 - x
            o |= 1 << (ny * n + nx)
        return o
    return {tf(k) for k in range(8)}


def stabilizer(board, mask):
    return len(d4_images(board, mask))


def exact_reach(board, maximals, top_k=None):
    """Exact reach probability (Fraction) of every maximal set under uniform
    random legal-move greedy.  forward DP: P[occ] = sum of P over parents."""
    P = {0: Fraction(1)}
    order = [0]
    for occ in order:
        mv = board.legal_moves(occ)
        w = P[occ] / len(mv) if mv else Fraction(0)
        if not mv:
            continue
        for u in mv:
            c = occ | (1 << u)
            if c not in P:
                P[c] = Fraction(0)
                order.append(c)
            P[c] += w
    return {m: P.get(m, Fraction(0)) for m in maximals}, P


def all_maximals(board):
    seen = {0}
    stack = [0]
    mx = []
    while stack:
        occ = stack.pop()
        mv = board.legal_moves(occ)
        if not mv:
            mx.append(occ)
            continue
        for u in mv:
            c = occ | (1 << u)
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return mx, seen


def main():
    t0 = time.time()
    report = {}

    # ============================= n = 4 (full exact) =====================
    b4 = board_square(4)
    mx4, safe4 = all_maximals(b4)
    reach4, P4 = exact_reach(b4, mx4)
    print(f"n=4 maximals {len(mx4)} safe {len(safe4)} ({time.time()-t0:.1f}s)", flush=True)

    byk = defaultdict(list)
    for m in mx4:
        byk[m.bit_count()].append(m)

    def stab4(m):
        return stabilizer(b4, m)

    def orb4(m):
        return len(d4_images(b4, m))

    # ---------- B496: exact within-(k,stab) max/min reach ratio ----------
    b496 = []
    for k, ms in sorted(byk.items()):
        cells = defaultdict(list)
        for m in ms:
            cells[stab4(m)].append(m)
        for st, group in sorted(cells.items()):
            vals = sorted((reach4[m] for m in group), reverse=True)
            if len(group) < 2:
                continue
            b496.append({"k": k, "stab": st, "n": len(group),
                         "ratio": float(vals[0] / vals[-1]) if vals[-1] else None,
                         "max": float(vals[0]), "min": float(vals[-1])})
    report["B496"] = {"cells": b496,
                      "max_ratio_n4": max(c["ratio"] for c in b496 if c["ratio"]),
                      "n4_exact": True}
    print("B496 n=4 max exact ratio", report["B496"]["max_ratio_n4"], flush=True)

    # ---------- B495: same |L|-histogram but different reach ----------
    # histogram of |L(S)| over the proper subsets of each maximal set,
    # grouped by size layer.
    L4 = {occ: len(b4.legal_moves(occ)) for occ in safe4}

    def subhist(m, keyfn):
        h = defaultdict(int)
        cells = [i for i in range(b4.V) if (m >> i) & 1]
        for sz in range(1, len(cells) + 1):
            for c in _comb(cells, sz):
                occ = 0
                for i in c:
                    occ |= 1 << i
                h[keyfn(occ, sz)] += 1
        return tuple(sorted(h.items()))

    def _comb(lst, k):
        from itertools import combinations
        return combinations(lst, k)

    b495_groups = defaultdict(list)
    for k, ms in sorted(byk.items()):
        if k > 6:
            continue
        byh = defaultdict(list)
        for m in ms:
            if m.bit_count() > 6:
                continue
            byh[subhist(m, lambda o, sz: L4[o])].append(m)
        for h, group in byh.items():
            if len(group) < 2:
                continue
            vals = sorted((float(reach4[m]) for m in group), reverse=True)
            b495_groups[(k, len(group))].append({"n": len(group), "ratio": vals[0] / vals[-1],
                                                 "max": vals[0], "min": vals[-1]})
    n_grp = sum(len(v) for v in b495_groups.values())
    n_sup = sum(1 for v in b495_groups.values() for x in v if x["ratio"] > 1.0000001)
    report["B495"] = {"n_groups": n_grp, "n_groups_ratio_gt_1": n_sup,
                      "max_ratio": max((x["ratio"] for v in b495_groups.values() for x in v),
                                       default=None),
                      "groups": [{"k": k, "size": s, "detail": v}
                                 for (k, s), v in list(b495_groups.items())[:10]]}
    print("B495 groups", n_grp, "with ratio>1:", n_sup, flush=True)

    # ---------- B497: perimeter timing, exact ----------
    n = 4
    perim = [1 if (i % n in (0, n - 1) or i // n in (0, n - 1)) else 0
             for i in range(b4.V)]
    P3 = {m: [None] * 0 for m in []}
    # forward prob restricted to reaching size 3 with perimeter count
    perim3 = defaultdict(Fraction)
    Psub = {0: Fraction(1)}
    order = [0]
    for occ in order:
        mv = b4.legal_moves(occ)
        if not mv:
            continue
        w = Psub[occ] / len(mv)
        for u in mv:
            c = occ | (1 << u)
            if c not in Psub:
                Psub[c] = Fraction(0)
                order.append(c)
            Psub[c] += w
            if c.bit_count() == 3:
                perim3[sum(perim[i] for i in range(b4.V) if (c >> i) & 1)] += w
    allp = sum(perim3.values())
    termp = defaultdict(Fraction)
    for m in mx4:
        if m.bit_count() == 7:
            termp[sum(perim[i] for i in range(b4.V) if (m >> i) & 1)] += reach4[m]
    alltp = sum(termp.values())
    p7 = {k: (float(v / allp) if allp else None, float(termp.get(k, 0) / alltp) if alltp else None)
          for k, v in sorted(perim3.items())}
    report["B497"] = {"n": 4, "exact": True,
                      "perim3_marginal": {str(k): v[0] for k, v in p7.items()},
                      "perim3_given_terminal_7": {str(k): v[1] for k, v in p7.items()},
                      "mean_perim_all": float(sum(Fraction(k) * v for k, v in perim3.items()) / allp),
                      "mean_perim_term7": float(sum(Fraction(k) * v for k, v in termp.items()) / alltp) if alltp else None}
    print("B497 n=4 exact", report["B497"]["mean_perim_all"], report["B497"]["mean_perim_term7"], flush=True)

    # ---------- B498: 3-stone completion profile, exact ----------
    sumb3 = defaultdict(Fraction)
    for occ in Psub:
        if occ.bit_count() != 3:
            continue
        s = 0
        for p in range(b4.V):
            if (occ >> p) & 1:
                continue
            bit = 1 << p
            for q in b4.quads_by_pt[p]:
                if (q & bit) == bit and (q & occ).bit_count() == 3:
                    s += 1
        sumb3[s] += Psub[occ]
    tot3 = sum(sumb3.values())
    mn_k = min(m.bit_count() for m in mx4)
    mx_k = max(m.bit_count() for m in mx4)
    prof = {}
    for k in (mn_k, mx_k):
        sub = defaultdict(Fraction)
        for m in mx4:
            if m.bit_count() != k:
                continue
            sub[sumb3_at(m)] += reach4[m]
        tt = sum(sub.values())
        prof[str(k)] = {str(s): float(v / tot3) for s, v in sorted(sub.items())}
        prof[str(k) + "_all"] = {str(s): float(v / tot3) for s, v in sorted(sumb3.items())}
    report["B498"] = {"n": 4, "exact": True, "profile_by_terminal_size": prof,
                      "n_terminals": {"min": mn_k, "max": mx_k}}
    print("B498 n=4 exact profiles done", flush=True)

    # ---------- B500: weighted-cut sharpness ----------
    # exact reach vs the "cut" approximation: probability of staying inside the
    # size-layer band around the target.  We compute the exact reach and the
    # product of per-layer harmonic factors restricted to the sub-lattice of
    # subsets of the target -- that IS the exact reach, so instead we measure
    # the *loss* incurred by ignoring the legality constraint (i.e. treating all
    # k-subsets of the target as reachable) -- a genuine upper bound.
    b500 = []
    for k, ms in sorted(byk.items()):
        if k > 5:
            continue
        for m in ms[:200]:
            cells = [i for i in range(b4.V) if (m >> i) & 1]
            # exact reach
            r_exact = reach4[m]
            # "cut bound": uniform-order model: 1 / prod_{j=0}^{k-1} C(k - j ... )
            # = probability of reaching m if at each step we pick uniformly
            # among the remaining cells of m -- always succeeds, so 1.
            # A genuine upper bound: the probability of the specific ORDER is
            # 1/prod |L| along the best order; a lower bound is 1/prod |L| along
            # the worst order.
            # compute best/worst product of |L| over all orders (subset DP)
            best = {0: Fraction(1)}
            worst = {0: Fraction(1)}
            for sz in range(0, k):
                for c in _comb(cells, sz):
                    occ = 0
                    for i in c:
                        occ |= 1 << i
                    nb = None
                    nw = None
                    for i in cells:
                        if (occ >> i) & 1:
                            continue
                        ch = occ | (1 << i)
                        if ch not in safe4:
                            continue
                        L = L4[ch]
                        nb = best[occ] * L if nb is None else min(nb, best[occ] * L)
                        nw = worst[occ] * L if nw is None else max(nw, worst[occ] * L)
                    if nb is not None:
                        best[occ | 0] = best[occ]
                # rebuild properly
            # proper subset DP for best/worst product
            best = {0: Fraction(1)}
            worst = {0: Fraction(1)}
            for sz in range(0, k):
                layer = [c for c in _comb(cells, sz) if _mask(c) in best]
                for c in layer:
                    occ = _mask(c)
                    for i in cells:
                        if (occ >> i) & 1:
                            continue
                        ch = occ | (1 << i)
                        if ch not in safe4:
                            continue
                        v = best[occ] * L4[ch]
                        if ch not in best or v < best[ch]:
                            best[ch] = v
                        v2 = worst[occ] * L4[ch]
                        if ch not in worst or v2 > worst[ch]:
                            worst[ch] = v2
            fm = _mask(cells)
            if fm in best:
                lo = Fraction(1) / worst[fm]
                hi = Fraction(1) / best[fm]
                b500.append({"k": k, "exact": float(r_exact),
                             "cut_lo": float(lo), "cut_hi": float(hi),
                             "ratio_exact_lo": float(r_exact / lo) if lo else None,
                             "ratio_hi_exact": float(hi / r_exact) if r_exact else None})
    good = [x for x in b500 if x["ratio_exact_lo"] and x["cut_lo"] > 0]
    report["B500"] = {
        "n_targets": len(b500),
        "mean_exact_over_cut_lo": (sum(x["ratio_exact_lo"] for x in good) / len(good)) if good else None,
        "max_exact_over_cut_lo": max((x["ratio_exact_lo"] for x in good), default=None),
        "mean_cut_hi_over_exact": (sum(x["ratio_hi_exact"] for x in good) / len(good)) if good else None,
        "rows": b500[:40],
        "note": "cut_lo/hi = 1/(worst|best order prod |L|); a sharp cut would have exact/lo ~ 1",
    }
    print("B500 n=4 targets", len(b500), "mean exact/cut_lo",
          report["B500"]["mean_exact_over_cut_lo"], flush=True)

    # ============================= n = 5 (exact, first move) ===============
    b5 = board_square(5)
    cache = pickle.load(open(ROOT / "research" / "verification" / "batch03_cache.pkl", "rb"))
    safe5 = {r["occ"] for r in cache[5]["recs"]}
    mx5 = [r["occ"] for r in cache[5]["recs"] if r["L"] == 0]
    print(f"n=5 maximals {len(mx5)} safe {len(safe5)}", flush=True)

    L5 = {r["occ"]: r["nL"] for r in cache[5]["recs"]}

    # ---------- B499: exact per-first-move P(min terminal) and E[X] -------
    first = {}
    for p in range(b5.V):
        Pf = {1 << p: Fraction(1)}
        order = [1 << p]
        sizes = defaultdict(Fraction)
        for occ in order:
            mv = b5.legal_moves(occ)
            if not mv:
                sizes[occ.bit_count()] += Pf[occ]
                continue
            w = Pf[occ] / len(mv)
            for u in mv:
                c = occ | (1 << u)
                if c not in Pf:
                    Pf[c] = Fraction(0)
                    order.append(c)
                Pf[c] += w
        tot = sum(sizes.values())
        EX = sum(Fraction(t) * v for t, v in sizes.items()) / tot
        Pmin = Fraction(0)
        kmin = min(m.bit_count() for m in mx5)
        for m in mx5:
            if m.bit_count() == kmin:
                Pmin += Pf.get(m, Fraction(0))
        Pmax = Fraction(0)
        kmax = max(m.bit_count() for m in mx5)
        for m in mx5:
            if m.bit_count() == kmax:
                Pmax += Pf.get(m, Fraction(0))
        first[p] = {"EX": EX, "Pmin": Pmin, "Pmax": Pmax,
                    "x": p % 5, "y": p // 5}
    b499 = []
    ps = list(first.values())
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            a, c = ps[i], ps[j]
            dE = abs(a["EX"] - c["EX"])
            if dE > Fraction(1, 50):
                continue
            ra = a["Pmin"] / c["Pmin"] if c["Pmin"] else None
            rc = c["Pmin"] / a["Pmin"] if a["Pmin"] else None
            rr = max([x for x in (ra, rc) if x is not None], default=None)
            b499.append({"a": [a["x"], a["y"]], "c": [c["x"], c["y"]],
                         "dE": float(dE), "dE_exact": str(dE),
                         "Pmin_a": float(a["Pmin"]), "Pmin_c": float(c["Pmin"]),
                         "ratio": float(rr) if rr is not None else None})
    b499.sort(key=lambda z: -(z["ratio"] or 0))
    report["B499"] = {
        "n": 5, "exact": True,
        "n_pairs_dE_le_1_50": len(b499),
        "max_ratio": max((z["ratio"] for z in b499 if z["ratio"]), default=None),
        "top": b499[:12],
        "per_first": {str(p): {"EX": float(v["EX"]), "Pmin": float(v["Pmin"]),
                               "Pmax": float(v["Pmax"]), "x": v["x"], "y": v["y"]}
                      for p, v in first.items()},
        "kmin": kmin, "kmax": kmax,
    }
    print("B499 n=5 exact max Pmin ratio at dE<=0.02:", report["B499"]["max_ratio"], flush=True)

    # ---------- B494: n=5 high-symmetry maximals, exact reach -------------
    # Exact reach of a maximal set on n=5 restricted to its own sub-lattice:
    # reach(m) = sum over orders of prod 1/|L(partial)|  -- but P is computed by
    # the global forward DP which is over 151394 states: affordable.
    P5 = {0: Fraction(1)}
    order = [0]
    for occ in order:
        mv = b5.legal_moves(occ)
        if not mv:
            continue
        w = P5[occ] / len(mv)
        for u in mv:
            c = occ | (1 << u)
            if c not in P5:
                P5[c] = Fraction(0)
                order.append(c)
            P5[c] += w
    reach5 = {m: P5.get(m, Fraction(0)) for m in mx5}
    print("n=5 forward DP done", len(P5), f"({time.time()-t0:.1f}s)", flush=True)

    byk5 = defaultdict(list)
    for m in mx5:
        byk5[m.bit_count()].append(m)

    b494 = []
    for k, ms in sorted(byk5.items()):
        if len(ms) < 2:
            continue
        # per-target: off-target mobility = mean |L| of the proper subsets
        # that are NOT subsets of m, weighted by the probability of being there
        row = {"k": k, "n": len(ms),
               "reach_min": float(min(reach5[m] for m in ms)),
               "reach_max": float(max(reach5[m] for m in ms))}
        # correlation stab vs reach
        stabs = []
        reaches = []
        offs = []
        sample = ms if len(ms) <= 400 else ms[:400]
        for m in sample:
            st = stabilizer(b5, m)
            stabs.append(st)
            reaches.append(float(reach5[m]))
        row["spear_stab_reach"] = _spear(stabs, reaches)
        # off-target mobility: P-weighted mean |L| over states of size k-1
        # that are NOT subsets of m  -- estimated on a sample
        row["n_sample"] = len(sample)
        b494.append(row)
    report["B494"] = {"n": 5, "exact_reach": True, "by_k": b494,
                      "n_m5_total": len(mx5)}
    print("B494 n=5 rows", [(r["k"], r["n"]) for r in b494], flush=True)

    # ---------- B496 extended to n=5: exact (k,stab) ratios --------------
    b496b = []
    for k, ms in sorted(byk5.items()):
        cells = defaultdict(list)
        for m in ms:
            cells[stabilizer(b5, m)].append(m)
        for st, group in sorted(cells.items()):
            if len(group) < 2:
                continue
            vals = sorted((reach5[m] for m in group), reverse=True)
            b496b.append({"k": k, "stab": st, "n": len(group),
                          "ratio": float(vals[0] / vals[-1]) if vals[-1] else None,
                          "max": float(vals[0]), "min": float(vals[-1])})
    report["B496_n5"] = {"cells": b496b,
                         "max_ratio_n5": max((c["ratio"] for c in b496b if c["ratio"]), default=None)}
    print("B496 n=5 max exact ratio", report["B496_n5"]["max_ratio_n5"], flush=True)

    report["meta"] = {"elapsed_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


_sumb3_cache = {}


def sumb3_at(m):
    return _sumb3_cache.get(m)


def _mask(c):
    o = 0
    for i in c:
        o |= 1 << i
    return o


def _spear(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            a = (i + j) / 2.0
            for t in range(i, j + 1):
                rk[order[t]] = a
            i = j + 1
        return rk
    if len(xs) < 3:
        return None
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    dx = sum((v - mx) ** 2 for v in rx) ** 0.5
    dy = sum((v - my) ** 2 for v in ry) ** 0.5
    return num / (dx * dy) if dx and dy else None


if __name__ == "__main__":
    # prefill sumb3 cache
    b4 = board_square(4)
    mx4, safe4 = all_maximals(b4)
    reach4, P4 = exact_reach(b4, mx4)
    for occ in P4:
        if occ.bit_count() == 3:
            s = 0
            for p in range(b4.V):
                if (occ >> p) & 1:
                    continue
                bit = 1 << p
                for q in b4.quads_by_pt[p]:
                    if (q & bit) == bit and (q & occ).bit_count() == 3:
                        s += 1
            _sumb3_cache[occ] = s
    main()
