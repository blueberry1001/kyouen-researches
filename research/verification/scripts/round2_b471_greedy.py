#!/usr/bin/env python3
"""B491-B500: random greedy terminal sizes and maximal-set reachability.

Reuses batch09 exact n<=5 terminal distributions and recomputes n=4 maximal
reach structure for B493-B500.  Integer arithmetic for combinatorics; floats
only for reported means/probabilities.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b471.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, board_square  # noqa: E402


def load_batch09() -> dict:
    p = ROOT / "research" / "verification" / "batch09_random_greedy.json"
    return json.loads(p.read_text(encoding="utf-8"))


def d4_images(mask: int, pts: list[tuple[int, int]], n: int) -> set[int]:
    coord_to_id = {pts[i]: i for i in range(len(pts))}
    imgs = set()
    for flipx in (False, True):
        for flipy in (False, True):
            for swap in (False, True):
                nm = 0
                for i in range(len(pts)):
                    if mask >> i & 1:
                        x, y = pts[i]
                        if flipx:
                            x = n - 1 - x
                        if flipy:
                            y = n - 1 - y
                        if swap:
                            x, y = y, x
                        nm |= 1 << coord_to_id[(x, y)]
                imgs.add(nm)
    return imgs


def stabilizer_size(mask: int, pts: list[tuple[int, int]], n: int) -> int:
    """Number of D4 elements fixing this set (not pointwise)."""
    s = 0
    for flipx in (False, True):
        for flipy in (False, True):
            for swap in (False, True):
                nm = 0
                coord_to_id = {pts[i]: i for i in range(len(pts))}
                for i in range(len(pts)):
                    if mask >> i & 1:
                        x, y = pts[i]
                        if flipx:
                            x = n - 1 - x
                        if flipy:
                            y = n - 1 - y
                        if swap:
                            x, y = y, x
                        nm |= 1 << coord_to_id[(x, y)]
                if nm == mask:
                    s += 1
    return s


def all_safe_subsets_of(board: Board, mask: int) -> list[int]:
    """All safe subsets of the occupied mask (including empty), as bitmasks."""
    bits = [i for i in range(board.V) if mask >> i & 1]
    out = []
    m = len(bits)
    for sub in range(1 << m):
        occ = 0
        for j in range(m):
            if sub >> j & 1:
                occ |= 1 << bits[j]
        if board.is_safe(occ):
            out.append(occ)
    return out


def analyze_maximals_n4() -> dict:
    n = 4
    b = board_square(n)
    pts = b.points

    # enumerate all reachable safe sets, collect maximal
    maximals = []
    seen = {0}
    stack = [0]
    while stack:
        occ = stack.pop()
        mv = b.legal_moves(occ)
        if not mv:
            maximals.append(occ)
        for u in mv:
            c = occ | (1 << u)
            if c not in seen:
                seen.add(c)
                stack.append(c)

    # exact reach probability of each maximal
    reach_memo: dict[int, dict[int, float]] = {}

    def reach_from(occ: int) -> dict[int, float]:
        hit = reach_memo.get(occ)
        if hit is not None:
            return hit
        mv = b.legal_moves(occ)
        if not mv:
            d = {occ: 1.0}
            reach_memo[occ] = d
            return d
        acc: dict[int, float] = defaultdict(float)
        w = 1.0 / len(mv)
        for u in mv:
            for t, p in reach_from(occ | (1 << u)).items():
                acc[t] += p * w
        d = dict(acc)
        reach_memo[occ] = d
        return d

    reach_exact = reach_from(0)

    # per-maximal features
    rows = []
    for m in maximals:
        sz = m.bit_count()
        # subsets and |L| histogram by subset size
        subs = all_safe_subsets_of(b, m)
        by_k_l: dict[int, list[int]] = defaultdict(list)  # k -> list of |L(S)|
        by_k_off: dict[int, list[int]] = defaultdict(list)  # k -> list of off-target |L|
        for s in subs:
            k = s.bit_count()
            if k == 0 or k == sz:
                continue
            L = b.legal_moves(s)
            by_k_l[k].append(len(L))
            off = 0
            for u in L:
                if not (m >> u & 1):
                    off += 1
            by_k_off[k].append(off)
        # mid-layer average log|L| (k between 1 and sz-1)
        all_L = []
        all_off = []
        mid_L = []
        for k, vs in by_k_l.items():
            all_L.extend(vs)
            mid_L.extend(vs)
        for k, vs in by_k_off.items():
            all_off.extend(vs)
        mean_logL = sum(math.log(v) for v in mid_L) / len(mid_L) if mid_L else None
        mean_L = sum(mid_L) / len(mid_L) if mid_L else None
        mean_off = sum(all_off) / len(all_off) if all_off else None
        mean_off_rate = (
            sum(all_off) / sum(all_L) if all_L and sum(all_L) > 0 else None
        )
        # histogram of |L| by k (for B495)
        hist = {str(k): sorted(vs) for k, vs in sorted(by_k_l.items())}
        stab = stabilizer_size(m, pts, n)
        rows.append({
            "mask": m,
            "k": sz,
            "reach": reach_exact.get(m, 0.0),
            "mean_logL_mid": mean_logL,
            "mean_L_mid": mean_L,
            "mean_off_mid": mean_off,
            "off_rate_mid": mean_off_rate,
            "stab": stab,
            "orbit_size": len(d4_images(m, pts, n)),
            "n_subsets": len(subs),
            "hist_L_by_k": hist,
        })

    # B493: correlation of reach with mean_logL_mid within same size
    b493 = {}
    for sz in sorted({r["k"] for r in rows}):
        rs = [r for r in rows if r["k"] == sz]
        pairs = [(r["mean_logL_mid"], r["reach"], r["mean_L_mid"]) for r in rs if r["mean_logL_mid"] is not None]
        if len(pairs) < 3:
            continue
        # Spearman
        def rank(xs):
            order = sorted(range(len(xs)), key=lambda i: xs[i])
            rk = [0] * len(xs)
            for r, i in enumerate(order):
                rk[i] = r
            return rk

        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        rx, ry = rank(xs), rank(ys)
        mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
        num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
        denx = math.sqrt(sum((v - mx) ** 2 for v in rx))
        deny = math.sqrt(sum((v - my) ** 2 for v in ry))
        rho = num / (denx * deny) if denx and deny else None
        b493[str(sz)] = {
            "n": len(pairs),
            "spearman_logL_vs_reach": rho,
            "reach_min": min(p[1] for p in pairs),
            "reach_max": max(p[1] for p in pairs),
        }

    # B494: off-target option count vs stab
    b494_pairs = []
    for sz in sorted({r["k"] for r in rows}):
        rs = [r for r in rows if r["k"] == sz and r["mean_off_mid"] is not None]
        if len(rs) < 4:
            continue
        stabs = [r["stab"] for r in rs]
        offs = [r["mean_off_mid"] for r in rs]
        reaches = [r["reach"] for r in rs]
        # does higher stab => higher off => lower reach?
        def rank(xs):
            order = sorted(range(len(xs)), key=lambda i: xs[i])
            rk = [0] * len(xs)
            for r, i in enumerate(order):
                rk[i] = r
            return rk

        def spear(a, c):
            ra, rc = rank(a), rank(c)
            ma, mc = sum(ra) / len(ra), sum(rc) / len(rc)
            num = sum((ra[i] - ma) * (rc[i] - mc) for i in range(len(ra)))
            da = math.sqrt(sum((v - ma) ** 2 for v in ra))
            dc = math.sqrt(sum((v - mc) ** 2 for v in rc))
            return num / (da * dc) if da and dc else None

        b494_pairs.append({
            "k": sz,
            "n": len(rs),
            "spear_stab_off": spear(stabs, offs),
            "spear_off_reach": spear(offs, reaches),
            "spear_stab_reach": spear(stabs, reaches),
        })

    # B495: same hist_L_by_k, different reach
    b495_hits = []
    hist_map: dict = defaultdict(list)
    for r in rows:
        key = json.dumps(r["hist_L_by_k"], sort_keys=True)
        hist_map[key].append(r)
    for key, group in hist_map.items():
        if len(group) < 2:
            continue
        reaches = [g["reach"] for g in group]
        if max(reaches) > 1.5 * min(reaches) and min(reaches) > 0:
            b495_hits.append({
                "k": group[0]["k"],
                "n_group": len(group),
                "reach_min": min(reaches),
                "reach_max": max(reaches),
                "ratio": max(reaches) / min(reaches),
                "masks": [g["mask"] for g in group[:6]],
            })
    b495_hits.sort(key=lambda h: -h["ratio"])

    # B496: same size + same stab, reach ratio
    b496_cells = []
    cell: dict = defaultdict(list)
    for r in rows:
        cell[(r["k"], r["stab"])].append(r)
    for (sz, st), group in sorted(cell.items()):
        if len(group) < 2:
            continue
        reaches = [g["reach"] for g in group]
        if min(reaches) <= 0:
            continue
        b496_cells.append({
            "k": sz,
            "stab": st,
            "n": len(group),
            "ratio": max(reaches) / min(reaches),
            "reach_min": min(reaches),
            "reach_max": max(reaches),
        })
    b496_cells.sort(key=lambda h: -h["ratio"])

    # distribution summary
    by_sz = defaultdict(list)
    for r in rows:
        by_sz[r["k"]].append(r["reach"])
    spread = {}
    for sz, ps in sorted(by_sz.items()):
        ps = sorted(ps)
        spread[str(sz)] = {
            "count": len(ps),
            "min": ps[0],
            "max": ps[-1],
            "ratio": ps[-1] / ps[0] if ps[0] > 0 else None,
        }

    return {
        "n": n,
        "n_maximal": len(maximals),
        "n_reachable_safe": len(seen),
        "size_spread_reach": spread,
        "B493": b493,
        "B494": b494_pairs,
        "B495_hits": b495_hits[:10],
        "B496_cells": b496_cells[:10],
        "rows_lite": [
            {k: r[k] for k in ("mask", "k", "reach", "mean_logL_mid", "mean_off_mid",
                               "off_rate_mid", "stab", "orbit_size")}
            for r in rows
        ],
    }


def mc_conditional(n: int, trials: int, seed: int) -> dict:
    """B497/B498/B499: conditional random-greedy statistics."""
    b = board_square(n)
    rng = random.Random(seed)

    # record first-3 perimeter occupancy, terminal size, 3-stone completion count
    perim_ok = 0
    perim_tot = 0
    max_term_perim = []
    all_term_perim = []
    # b at 3 stones: number of triples in S that forbid an empty point (= sum b_S(p))
    # actually "三石時点の補完数" = max/mean b_S(p) or number of p with b>0
    max_term_comp = []
    all_term_comp = []
    min_term_comp = []
    term_sizes = []
    # per first-move: E[X] and P(minimal)
    first_stats = defaultdict(lambda: {"X": [], "minflag": [], "maxflag": []})
    # global min/max terminal size
    global_min = n * n
    global_max = 0
    samples = []
    for _ in range(trials):
        occ = 0
        first = None
        trace_perim = 0
        trace_comp3 = None
        for step in range(n * n):
            mv = b.legal_moves(occ)
            if not mv:
                break
            u = mv[rng.randrange(len(mv))]
            if step == 0:
                first = u
            occ |= 1 << u
            if step == 2:  # 3 stones placed
                # perimeter = stones on boundary
                st = [i for i in range(b.V) if occ >> i & 1]
                per = 0
                for i in st:
                    x, y = b.points[i]
                    if x in (0, n - 1) or y in (0, n - 1):
                        per += 1
                trace_perim = per
                # completion counts b(p) for empty p
                comps = []
                empty = [i for i in range(b.V) if not (occ >> i & 1)]
                for p in empty:
                    bit = 1 << p
                    bp = 0
                    for q in b.quads_by_pt[p]:
                        # b_S(p) = # quads containing p with 3 other points already in S
                        if (q & bit) == bit and (q & occ).bit_count() == 3:
                            bp += 1
                    comps.append(bp)
                trace_comp3 = {
                    "max_b": max(comps) if comps else 0,
                    "sum_b": sum(comps),
                    "n_pos": sum(1 for c in comps if c > 0),
                }
        sz = occ.bit_count()
        term_sizes.append(sz)
        global_min = min(global_min, sz)
        global_max = max(global_max, sz)
        samples.append({"first": first, "sz": sz, "perim": trace_perim, "comp3": trace_comp3})

    # classify
    for s in samples:
        is_max = s["sz"] == global_max
        is_min = s["sz"] == global_min
        if s["comp3"]:
            all_term_comp.append(s["comp3"])
            if is_max:
                max_term_comp.append(s["comp3"])
            if is_min:
                min_term_comp.append(s["comp3"])
        all_term_perim.append(s["perim"])
        if is_max:
            max_term_perim.append(s["perim"])
        fs = first_stats[s["first"]]
        fs["X"].append(s["sz"])
        fs["minflag"].append(1 if is_min else 0)
        fs["maxflag"].append(1 if is_max else 0)

    def avg(xs):
        return sum(xs) / len(xs) if xs else None

    # B497: perimeter of first 3 stones, conditioned on max terminal, within first move
    by_first_perim = defaultdict(lambda: {"all": [], "maxterm": []})
    for s in samples:
        by_first_perim[s["first"]]["all"].append(s["perim"])
        if s["sz"] == global_max:
            by_first_perim[s["first"]]["maxterm"].append(s["perim"])
    within_deltas = []
    for p, st in by_first_perim.items():
        if not st["all"] or not st["maxterm"]:
            continue
        within_deltas.append(avg(st["maxterm"]) - avg(st["all"]))
    b497 = {
        "global_min": global_min,
        "global_max": global_max,
        "mean_perim_all": avg(all_term_perim),
        "mean_perim_maxterm": avg(max_term_perim),
        "n_maxterm": len(max_term_perim),
        "n_minterm": len([s for s in samples if s["sz"] == global_min]),
        "within_first_delta_mean": avg(within_deltas),
        "within_first_delta_min": min(within_deltas) if within_deltas else None,
        "within_first_delta_max": max(within_deltas) if within_deltas else None,
        "n_first_with_maxterm": len(within_deltas),
    }
    # B498: 3-stone completion, conditioned on min terminal
    def comp_key(cs):
        return {
            "mean_max_b": avg([c["max_b"] for c in cs]),
            "mean_sum_b": avg([c["sum_b"] for c in cs]),
            "mean_n_pos": avg([c["n_pos"] for c in cs]),
            "n": len(cs),
        }

    b498 = {
        "all": comp_key(all_term_comp),
        "min_term": comp_key(min_term_comp),
        "max_term": comp_key(max_term_comp),
    }
    # B499: first moves with close E[X] but very different P(min)
    fs_rows = []
    for p, st in first_stats.items():
        if not st["X"]:
            continue
        fs_rows.append({
            "first": p,
            "E_X": avg(st["X"]),
            "P_min": avg(st["minflag"]),
            "P_max": avg(st["maxflag"]),
            "n": len(st["X"]),
        })
    # find pairs
    b499_pairs = []
    for i in range(len(fs_rows)):
        for j in range(i + 1, len(fs_rows)):
            a, c = fs_rows[i], fs_rows[j]
            if abs(a["E_X"] - c["E_X"]) <= 0.05:
                if a["P_min"] > 0 and c["P_min"] > 0:
                    ratio = max(a["P_min"], c["P_min"]) / min(a["P_min"], c["P_min"])
                    if ratio >= 3:
                        b499_pairs.append({
                            "a": a, "c": c,
                            "dE": abs(a["E_X"] - c["E_X"]),
                            "Pmin_ratio": ratio,
                        })
                elif a["P_min"] == 0 and c["P_min"] > 0 and c["P_min"] >= 0.02:
                    b499_pairs.append({
                        "a": a, "c": c,
                        "dE": abs(a["E_X"] - c["E_X"]),
                        "Pmin_ratio": "inf",
                    })
                elif c["P_min"] == 0 and a["P_min"] > 0 and a["P_min"] >= 0.02:
                    b499_pairs.append({
                        "a": a, "c": c,
                        "dE": abs(a["E_X"] - c["E_X"]),
                        "Pmin_ratio": "inf",
                    })
    b499_pairs.sort(key=lambda h: -h["dE"] if False else (
        h["Pmin_ratio"] if isinstance(h["Pmin_ratio"], float) else 1e9))

    return {
        "n": n,
        "trials": trials,
        "B497": b497,
        "B498": b498,
        "B499_pairs": b499_pairs[:8],
        "first_move_rows": fs_rows,
        "term_size_hist": {str(s): term_sizes.count(s) for s in sorted(set(term_sizes))},
    }


def bottleneck_n4(analysis: dict) -> dict:
    """B500: can a single size-layer cut give sharp reach bounds?

    For each maximal, reach = sum over construction orders of prod 1/|L|.
    A bottleneck layer: among all intermediate safe subsets of a maximal,
    the layer where |L| is smallest forces a large penalty.
    We compare the actual reach with a lower bound obtained by using only
    the worst-layer harmonic mean.
    """
    # Use rows_lite: reach vs mean_logL.  A crude bound:
    # reach(M) <= (max over paths of prod 1/|L|) and >= (min over paths).
    # Without enumerating paths we use the layer-average product as a proxy.
    rows = analysis["rows_lite"]
    # product of layer-mean 1/|L|  (requires hist; we only have mean_logL)
    # Instead report correlation of log(reach) with mean_logL as the "cut" quality.
    pairs = [(r["mean_logL_mid"], r["reach"], r["k"]) for r in rows if r["mean_logL_mid"] is not None and r["reach"] > 0]
    # residual spread after predicting reach by exp(mean_logL * c)
    # fit log(reach) = a + b * mean_logL  (least squares, floats ok for reporting)
    if len(pairs) >= 5:
        xs = [p[0] for p in pairs]
        ys = [math.log(p[1]) for p in pairs]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
        b = sxy / sxx if sxx else 0.0
        a = my - b * mx
        resid = [ys[i] - (a + b * xs[i]) for i in range(n)]
        ss_res = sum(r * r for r in resid)
        ss_tot = sum((y - my) ** 2 for y in ys)
        r2 = 1 - ss_res / ss_tot if ss_tot else None
    else:
        a = b = r2 = None
        resid = []
    return {
        "n_pairs": len(pairs),
        "fit_log_reach_on_mean_logL": {"a": a, "b": b, "R2": r2},
        "resid_sd": (math.sqrt(sum(r * r for r in resid) / len(resid))) if resid else None,
        "note": "R2 of log-reach vs mid-layer mean log|L|; high R2 would support B500's cut view",
    }


def main() -> None:
    try:
        report = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        report = {}

    old = load_batch09()
    # B491 / B492 from existing exact + MC
    b491_rows = []
    for n_str, s in old["exact"].items():
        n = int(n_str)
        b491_rows.append({
            "n": n,
            "E_X": s["mean"],
            "E_over_n": s["mean"] / n,
            "Var": s["var"],
            "Var_over_n": s["var"] / n,
            "src": "exact",
        })
    for n_str, s in old["mc"].items():
        n = int(n_str)
        if n <= 5:
            continue
        b491_rows.append({
            "n": n,
            "E_X": s["mean"],
            "E_over_n": s["mean"] / n,
            "Var": s["std"] ** 2,
            "Var_over_n": s["std"] ** 2 / n,
            "src": "mc",
        })
    b491_rows.sort(key=lambda r: r["n"])
    print("B491 rows:", [(r["n"], round(r["E_over_n"], 4), round(r["Var_over_n"], 4)) for r in b491_rows], flush=True)

    # n=4 maximal analysis
    print("analyzing n=4 maximals...", flush=True)
    analysis = analyze_maximals_n4()
    print("n_maximal", analysis["n_maximal"], "B493", analysis["B493"], flush=True)
    print("B494", analysis["B494"], flush=True)
    print("B495 hits", len(analysis["B495_hits"]), "top", analysis["B495_hits"][:2], flush=True)
    print("B496 top", analysis["B496_cells"][:3], flush=True)

    # MC conditional n=5 (moderate) and n=6
    print("MC conditional n=5...", flush=True)
    mc5 = mc_conditional(5, trials=4000, seed=20260928)
    print("B497", mc5["B497"], flush=True)
    print("B498", mc5["B498"], flush=True)
    print("B499 pairs", len(mc5["B499_pairs"]), mc5["B499_pairs"][:2], flush=True)

    print("MC conditional n=6...", flush=True)
    mc6 = mc_conditional(6, trials=2500, seed=20260929)

    bn = bottleneck_n4(analysis)
    print("B500", bn, flush=True)

    report["B491"] = {
        "claim": "E[X_n]/n -> 3/2",
        "rows": b491_rows,
    }
    report["B492"] = {
        "claim": "Var(X_n)=O(n)",
        "rows": b491_rows,
        "Var_over_n_range": [
            min(r["Var_over_n"] for r in b491_rows if r["n"] >= 4),
            max(r["Var_over_n"] for r in b491_rows if r["n"] >= 4),
        ],
    }
    report["B493"] = analysis["B493"]
    report["B494"] = analysis["B494"]
    report["B495"] = analysis["B495_hits"]
    report["B496"] = analysis["B496_cells"]
    report["B497"] = {"n5": mc5["B497"], "n6": mc6["B497"]}
    report["B498"] = {"n5": mc5["B498"], "n6": mc6["B498"]}
    report["B499"] = {"n5_pairs": mc5["B499_pairs"], "n6_pairs": mc6["B499_pairs"],
                      "n5_first": mc5["first_move_rows"], "n6_first": mc6["first_move_rows"]}
    report["B500"] = bn
    report["n4_maximal_analysis"] = {
        "n_maximal": analysis["n_maximal"],
        "size_spread_reach": analysis["size_spread_reach"],
        "rows_lite": analysis["rows_lite"][:30],
    }
    report["mc_cond"] = {
        "n5_term_hist": mc5["term_size_hist"],
        "n6_term_hist": mc6["term_size_hist"],
    }

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
