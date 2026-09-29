#!/usr/bin/env python3
"""Round5 geom-stats: extract B457/B464/B467/B468/B469 evidence from existing census.

Reads research/verification/round3_b451_census.json (rows_m_ge5 has pts/ext/d4_orbit/q).
Computes:
  B464: A_sq vs A_rect window spectra, focused on asymmetric ext circles.
  B467: order-pattern (x-rank, y-rank) groups -> do they determine A(C)?
  B468: holes count vs d4_orbit, controlling m and bbox.
  B469: best edge-balance of triples on max-m vs slightly-smaller circles (n=8,9,10).
  B457: window-count variety for q>=3 vs q<=2 (already partially in derived json).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CENSUS = ROOT / "research" / "verification" / "round3_b451_census.json"
OUT = ROOT / "research" / "verification" / "round5_geom_stats.json"


def window_spectra(pts, n):
    """A_sq: set of in-board counts of circle points under square windows side w.
    A_rect: same for rectangular windows (w,h independent).
    Window is the integer box [x0,x0+w) x [y0,y0+h) clipped to board? No:
    standard from prior work: translate an n-window of size w x h over Z^2 and
    count how many circle points land inside; record achievable counts.
    Use all positions where the window intersects the bbox of the circle.
    """
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    m = len(pts)
    max_side = max(n, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) + 2
    A_sq = set()
    A_rect = set()
    # include 0 by placing window away
    A_sq.add(0)
    A_rect.add(0)
    # full m is achievable by a large enough window covering all
    A_sq.add(m)
    A_rect.add(m)
    for w in range(1, max_side + 1):
        for h in range(1, max_side + 1):
            # slide window over a range covering all circle points plus margin
            x_lo = min(xs) - w
            x_hi = max(xs) + 1
            y_lo = min(ys) - h
            y_hi = max(ys) + 1
            # too many positions if max_side large; for m>=5 pts, max_side ~ n+2 <= 14
            # positions: O(n^2 * n^2) = 14^4 = 38k, fine
            for x0 in range(x_lo, x_hi + 1):
                for y0 in range(y_lo, y_hi + 1):
                    cnt = 0
                    for x, y in pts:
                        if x0 <= x < x0 + w and y0 <= y < y0 + h:
                            cnt += 1
                    A_rect.add(cnt)
                    if w == h:
                        A_sq.add(cnt)
    return sorted(A_sq), sorted(A_rect)


def holes_of(A, m):
    """gaps in A between 0 and m inclusive that are missing (interior holes)."""
    s = set(A)
    return [k for k in range(0, m + 1) if k not in s]


def order_pattern(pts):
    xs = sorted(set(p[0] for p in pts))
    ys = sorted(set(p[1] for p in pts))
    xr = {v: i for i, v in enumerate(xs)}
    yr = {v: i for i, v in enumerate(ys)}
    return tuple(sorted((xr[x], yr[y]) for x, y in pts))


def edge_balance(pts, n):
    """counts of points on 4 borders of n x n board; return max-min spread."""
    c = [0, 0, 0, 0]  # left x=0, right x=n-1, bottom y=0, top y=n-1
    for x, y in pts:
        if x == 0:
            c[0] += 1
        if x == n - 1:
            c[1] += 1
        if y == 0:
            c[2] += 1
        if y == n - 1:
            c[3] += 1
    return max(c) - min(c)


def best_triple_balance(pts, n):
    """min spread over all triples of the circle's points (on-board points only)."""
    m = len(pts)
    if m < 3:
        return None
    best = 10**9
    for i in range(m):
        for j in range(i + 1, m):
            for k in range(j + 1, m):
                sp = edge_balance([pts[i], pts[j], pts[k]], n)
                if sp < best:
                    best = sp
    return best


def main():
    print("loading census...", flush=True)
    data = json.loads(CENSUS.read_text(encoding="utf-8"))
    report = {}

    # ---------- B464 / B467 / B468: window spectra on rows_m_ge5 ----------
    b464 = {"circles": 0, "asymmetric": 0, "n_with_extra_rect": 0, "examples": []}
    b467 = {"n_patterns": 0, "n_patterns_multi": 0, "n_patterns_different_A": 0,
            "examples_agree": [], "examples_disagree": []}
    b468 = {"pairs": 0, "higher_orbit_more_holes": 0, "lower_orbit_more_holes": 0,
            "ties": 0, "mean_holes_by_orbit": {}, "by_m": {}}

    pattern_to_A = defaultdict(set)
    pattern_to_m = defaultdict(set)
    orbit_holes = defaultdict(list)
    controlled = []  # (m, side, d4_orbit, n_holes)

    # Only compute full window spectra for a manageable subset:
    # - all asymmetric circles with m<=12
    # - all circles with m>=5 up to n=8 (already rows_m_ge5)
    # Cap total circles processed.
    processed = 0
    CAP = 400

    for n_str, board in data["boards"].items():
        n = int(n_str)
        rows = board.get("rows_m_ge5") or []
        for row in rows:
            pts = [tuple(p) for p in row["pts"]]
            m = row["m"]
            ext = row.get("ext")
            d4 = row.get("d4_orbit")
            q = row.get("q")
            side = row.get("side")
            if processed >= CAP:
                break
            # prioritize asymmetric
            is_asym = isinstance(ext, list) and len(set(ext)) > 1
            if not is_asym and m > 10:
                continue
            if m > 16:
                continue
            A_sq, A_rect = window_spectra(pts, n)
            processed += 1
            b464["circles"] += 1
            if is_asym:
                b464["asymmetric"] += 1
            extra = sorted(set(A_rect) - set(A_sq))
            if extra:
                b464["n_with_extra_rect"] += 1
                if len(b464["examples"]) < 12:
                    b464["examples"].append({
                        "n": n, "m": m, "q": q, "side": side, "ext": ext,
                        "d4_orbit": d4, "A_sq": A_sq, "A_rect": A_rect,
                        "extra_rect": extra, "pts": pts[:8],
                    })

            # B467
            op = order_pattern(pts)
            pattern_to_A[op].add(tuple(A_sq))
            pattern_to_m[op].add(m)

            # B468
            hs = holes_of(A_sq, m)
            orbit_holes[d4].append(len(hs))
            controlled.append((m, side, d4, len(hs), is_asym, q))

        if processed >= CAP:
            break

    # finalize B467
    for op, As in pattern_to_A.items():
        b467["n_patterns"] += 1
        if len(pattern_to_m[op]) > 1 or len(As) > 0:
            pass
        if len(pattern_to_A[op]) > 1:
            b467["n_patterns_different_A"] += 1
            if len(b467["examples_disagree"]) < 5:
                b467["examples_disagree"].append({
                    "pattern_size": len(op),
                    "m_vals": sorted(pattern_to_m[op]),
                    "n_distinct_A": len(As),
                })
        else:
            if len(pattern_to_m[op]) > 1:
                b467["n_patterns_multi"] += 1
                if len(b467["examples_agree"]) < 5:
                    b467["examples_agree"].append({
                        "pattern_size": len(op),
                        "m_vals": sorted(pattern_to_m[op]),
                        "A": list(next(iter(As))),
                    })

    # finalize B468: controlled pairs same (m, side)
    by_ms = defaultdict(list)
    for m, side, d4, nh, is_asym, q in controlled:
        by_ms[(m, side)].append((d4, nh))
    for key, lst in by_ms.items():
        if len(lst) < 2:
            continue
        # compare all pairs
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                d1, h1 = lst[i]
                d2, h2 = lst[j]
                if d1 == d2:
                    continue
                b468["pairs"] += 1
                if d1 > d2:
                    if h1 > h2:
                        b468["higher_orbit_more_holes"] += 1
                    elif h1 < h2:
                        b468["lower_orbit_more_holes"] += 1
                    else:
                        b468["ties"] += 1
                else:
                    if h2 > h1:
                        b468["higher_orbit_more_holes"] += 1
                    elif h2 < h1:
                        b468["lower_orbit_more_holes"] += 1
                    else:
                        b468["ties"] += 1
    for d4, hs in orbit_holes.items():
        b468["mean_holes_by_orbit"][str(d4)] = {
            "n": len(hs), "mean": sum(hs) / len(hs), "min": min(hs), "max": max(hs)
        }
    report["B464"] = b464
    report["B467"] = b467
    report["B468"] = b468
    report["window_processed"] = processed

    # ---------- B469: edge balance of triples ----------
    b469 = {"by_n": {}}
    for n_str, board in data["boards"].items():
        n = int(n_str)
        if n < 8 or n > 10:
            continue
        rows = board.get("rows_m_ge5") or []
        max_m = board.get("M_n")
        tops = [r for r in rows if r["m"] == max_m]
        below = [r for r in rows if r["m"] == max_m - 2 or r["m"] == max_m - 1]
        def mean_best(rs):
            vals = []
            for r in rs[:20]:  # cap
                b = best_triple_balance([tuple(p) for p in r["pts"]], n)
                if b is not None:
                    vals.append(b)
            return (sum(vals) / len(vals) if vals else None, len(vals), vals[:8])
        mt, nt, vt = mean_best(tops)
        mb, nb, vb = mean_best(below)
        b469["by_n"][n_str] = {
            "M_n": max_m,
            "n_top_circles": len(tops),
            "n_below_circles": len(below),
            "mean_best_balance_top": mt,
            "n_top_measured": nt,
            "top_vals": vt,
            "mean_best_balance_below": mb,
            "n_below_measured": nb,
            "below_vals": vb,
        }
    report["B469"] = b469

    # ---------- B457: variety of in-board counts by q ----------
    # From census circles_by_m_q / best_per_m_qclass we already have derived json;
    # add a simple count: for each m, number of distinct (qclass) and distinct side.
    b457 = {"by_n": {}}
    for n_str, board in data["boards"].items():
        rows = board.get("rows_m_ge5") or []
        by_m = defaultdict(lambda: {"q_le2": set(), "q_ge3": set(), "sides": set()})
        for r in rows:
            m = r["m"]
            q = r["q"]
            side = r["side"]
            by_m[m]["sides"].add(side)
            if q <= 2:
                by_m[m]["q_le2"].add(q)
            else:
                by_m[m]["q_ge3"].add(q)
        b457["by_n"][n_str] = {
            str(m): {
                "n_q_le2": len(v["q_le2"]),
                "n_q_ge3": len(v["q_ge3"]),
                "n_distinct_sides": len(v["sides"]),
                "sides": sorted(v["sides"]),
            }
            for m, v in by_m.items()
        }
    report["B457_extra"] = b457

    # ---------- B475/B476 confirmation from census m_hist ----------
    # m_hist is count of circles with m points. C(m,4)*H[m] weights.
    from math import comb
    b475 = {}
    b476 = {}
    for n_str, board in data["boards"].items():
        m_hist = board.get("m_hist") or {}
        Cn = 0
        weighted = 0
        for m_s, cnt in m_hist.items():
            m = int(m_s)
            if m < 4:
                continue
            w = comb(m, 4) * cnt
            Cn += w
            weighted += m * w
        if Cn == 0:
            continue
        f_le = {}
        for m0 in (4, 5, 6, 8):
            s = 0
            for m_s, cnt in m_hist.items():
                m = int(m_s)
                if m < 4:
                    continue
                if m <= m0:
                    s += comb(m, 4) * cnt
            f_le[str(m0)] = s / Cn
        b475[n_str] = {"C_n": Cn, "f_le": f_le, "mean_m": weighted / Cn, "m_hist": m_hist}
        b476[n_str] = {"mean_m": weighted / Cn, "P_le": f_le}
    report["B475_from_census"] = b475
    report["B476_from_census"] = b476

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)
    print("B464", {k: b464[k] for k in ("circles", "asymmetric", "n_with_extra_rect")})
    print("B467", {k: b467[k] for k in b467 if k.startswith("n_")})
    print("B468 pairs", b468["pairs"], "higher", b468["higher_orbit_more_holes"],
          "lower", b468["lower_orbit_more_holes"], "ties", b468["ties"])
    print("B469", json.dumps(b469, ensure_ascii=False)[:800])
    print("B475 n8 f_le", b475.get("8", {}).get("f_le"))
    print("B476 n8 mean", b476.get("8", {}).get("mean_m"))


if __name__ == "__main__":
    main()
