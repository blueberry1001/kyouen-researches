#!/usr/bin/env python3
"""B471-B473: collinear-quad counting by primitive direction height.

D(a,b;n) = sum of C(run,4) over maximal runs in primitive direction (a,b).
H(a,b) = max(|a|,|b|).  Integer arithmetic only.

Checks:
  B471  tail sum_{H>h} D_H <= C * n^5 / h  (uniformity in n,h)
  B472  D(a,b;n) * H^3 / n^5 ~ bounded function of reduced ratio
  B473  finite-size residual after c n^5 log n main term
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b471.json"


def dir_contribution(n: int, dx: int, dy: int) -> int:
    """C(run,4) total for one primitive direction. Canonical: dx>0 or (dx==0,dy==1)."""
    if dx < 0 or (dx == 0 and dy <= 0):
        dx, dy = -dx, -dy
    if dx == 0 and dy != 1:
        return 0
    if dx > 0 and math.gcd(dx, abs(dy)) != 1:
        return 0
    pts = [(x, y) for y in range(n) for x in range(n)]
    S = set(pts)
    seen = set()
    total = 0
    for x, y in pts:
        if (x, y) in seen:
            continue
        sx, sy = x, y
        while (sx - dx, sy - dy) in S:
            sx, sy = sx - dx, sy - dy
        L = 0
        cx, cy = sx, sy
        while (cx, cy) in S:
            seen.add((cx, cy))
            L += 1
            cx, cy = cx + dx, cy + dy
        if L >= 4:
            total += math.comb(L, 4)
    return total


def all_dirs(n: int) -> list[tuple[int, int]]:
    out = []
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy <= 0:
                continue
            if dx > 0 and math.gcd(dx, abs(dy)) != 1:
                continue
            if dx == 0 and dy != 1:
                continue
            out.append((dx, dy))
    return out


def by_height(n: int) -> dict[int, int]:
    """Total D contributed by each height H = max(|dx|,|dy|)."""
    acc: dict[int, int] = defaultdict(int)
    for dx, dy in all_dirs(n):
        H = max(abs(dx), abs(dy))
        c = dir_contribution(n, dx, dy)
        if c:
            acc[H] += c
    return dict(acc)


def main() -> None:
    report: dict = {"B471": {}, "B472": {}, "B473": {}}

    # ---------- B471 / B472: height decomposition ----------
    ns = [8, 12, 16, 20, 24, 28, 32]
    height_tables = {}
    for n in ns:
        bh = by_height(n)
        height_tables[n] = bh
        D = sum(bh.values())
        print(f"n={n} D={D} heights={ {h: bh[h] for h in sorted(bh)}}", flush=True)

    # Tail check: for each n and several h, compute tail = sum_{H>h} D_H
    # and the scaled value h * tail / n^5.  B471 claims this stays O(1).
    tail_rows = []
    for n in ns:
        bh = height_tables[n]
        maxH = max(bh) if bh else 0
        D = sum(bh.values())
        for h in [1, 2, 3, 4, 6, 8, max(1, maxH // 2)]:
            tail = sum(v for H, v in bh.items() if H > h)
            # also the cumulative-from-below for reference
            head = sum(v for H, v in bh.items() if H <= h)
            row = {
                "n": n,
                "h": h,
                "tail": tail,
                "head": head,
                "D": D,
                "tail_over_n5h": (tail * h) / n ** 5 if h else None,
                "tail_over_n5": tail / n ** 5,
                "frac_tail": tail / D if D else None,
            }
            tail_rows.append(row)
    # uniformity: max over (n,h) of h*tail/n^5
    scaled = [r["tail_over_n5h"] for r in tail_rows if r["tail_over_n5h"] is not None]
    report["B471"] = {
        "claim": "sum_{H>h} D_H = O(n^5/h) uniformly",
        "rows": tail_rows,
        "max_h_tail_over_n5": max(scaled) if scaled else None,
        "min_h_tail_over_n5": min(scaled) if scaled else None,
        "by_h": {},
    }
    # group by h to see if h*tail/n^5 decreases like 1/h * const or stays flat
    by_h_map: dict[int, list[float]] = defaultdict(list)
    for r in tail_rows:
        if r["tail_over_n5h"] is not None:
            by_h_map[r["h"]].append(r["tail_over_n5h"])
    for h, vs in sorted(by_h_map.items()):
        report["B471"]["by_h"][str(h)] = {
            "mean_h_tail_over_n5": sum(vs) / len(vs),
            "max": max(vs),
            "min": min(vs),
            "count": len(vs),
        }
    print("B471 scaled tail h*tail/n^5 by h:", report["B471"]["by_h"], flush=True)

    # ---------- B472: H^3 scaling of per-direction coefficients ----------
    # For fixed ratio a:b (primitive), look at D(a,b;n)*H^3/n^5 across n.
    ratios_of_interest = []
    for dx, dy in all_dirs(max(ns)):
        ratios_of_interest.append((dx, dy))
    # measure at the largest few n
    measure_ns = [16, 20, 24, 28, 32]
    per_dir = {}
    for n in measure_ns:
        rows = []
        for dx, dy in all_dirs(n):
            c = dir_contribution(n, dx, dy)
            if c == 0:
                continue
            H = max(abs(dx), abs(dy))
            rows.append({
                "dir": f"{dx},{dy}",
                "H": H,
                "D": c,
                "D_over_n5": c / n ** 5,
                "H3_D_over_n5": (H ** 3) * c / n ** 5,
            })
        per_dir[n] = rows
        # summary: spread of H3-scaled coeff within each H
        byH = defaultdict(list)
        for r in rows:
            byH[r["H"]].append(r["H3_D_over_n5"])
        print(f"n={n} H3-scaled by H:", {h: (min(v), max(v), sum(v)/len(v)) for h, v in sorted(byH.items())}, flush=True)

    # For a fixed direction (dx,dy), track H3*D/n^5 across n (stability)
    stab = {}
    for dx, dy in [(1, 0), (1, 1), (2, 1), (3, 1), (3, 2), (4, 1), (4, 3), (5, 1), (5, 2), (5, 3), (5, 4)]:
        key = f"{dx},{dy}"
        series = []
        for n in measure_ns:
            c = dir_contribution(n, dx, dy)
            H = max(abs(dx), abs(dy))
            series.append({"n": n, "D": c, "H3_D_over_n5": (H ** 3) * c / n ** 5 if n else 0})
        stab[key] = {"H": max(abs(dx), abs(dy)), "series": series}
        print(f"  dir {key} H={max(abs(dx),abs(dy))} series H3D/n5:", [round(s['H3_D_over_n5'], 6) for s in series], flush=True)

    # Bounded-function-of-ratio check: for each n, does H3*D/n^5 depend mostly on H or on angle?
    # Compute variance decomposition: range within same H vs across H.
    n0 = 32
    rows = per_dir[n0]
    byH = defaultdict(list)
    for r in rows:
        byH[r["H"]].append(r)
    within_H_ranges = {}
    for H, rs in sorted(byH.items()):
        vals = [r["H3_D_over_n5"] for r in rs]
        within_H_ranges[str(H)] = {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "ratio_max_min": (max(vals) / min(vals)) if min(vals) > 0 else None,
            "mean": sum(vals) / len(vals),
        }
    report["B472"] = {
        "claim": "D(a,b;n)/n^5 ~ f(a:b)/H^3",
        "within_H_ranges_n32": within_H_ranges,
        "fixed_dir_series": stab,
        "per_dir_n32_topH": [r for r in rows if r["H"] >= 4][:40],
    }

    # ---------- B473: finite-size residual ----------
    # Fit D_n = c * n^5 * log(n) using exact rational-ish estimate at n=28..40,
    # then look at residual vs n^4 and divisor sums.
    from batch08_verify import collinear_c4  # local import

    Dns = {}
    for n in range(2, 41):
        t, _ = collinear_c4(n)
        Dns[n] = t
    # least-squares-free: c_hat = D_n / (n^5 log n) at large n
    c_series = [{"n": n, "D": Dns[n], "c": Dns[n] / (n ** 5 * math.log(n))} for n in range(4, 41)]
    c_large = [r["c"] for r in c_series if r["n"] >= 28]
    c_hat = sum(c_large) / len(c_large)
    residuals = []
    for n in range(4, 41):
        main = c_hat * (n ** 5) * math.log(n)
        resid = Dns[n] - main
        # divisor-sum proxy: sigma_0(n) = number of divisors; also sum_{d|n} d
        sig0 = sum(1 for d in range(1, n + 1) if n % d == 0)
        sig1 = sum(d for d in range(1, n + 1) if n % d == 0)
        # number of primitive dirs with 4+ points ~ phi-ish; use n^4 and n^4 * sig0/n as candidates
        residuals.append({
            "n": n,
            "D": Dns[n],
            "main": main,
            "resid": resid,
            "resid_over_n4": resid / n ** 4,
            "resid_over_n5": resid / n ** 5,
            "sig0": sig0,
            "sig1": sig1,
            "resid_over_n4sig0": resid / (n ** 4 * sig0) if sig0 else None,
        })
    # correlation-ish: does resid/n^4 track sig0 or a constant?
    r_n4 = [r["resid_over_n4"] for r in residuals if r["n"] >= 10]
    report["B473"] = {
        "claim": "residual after c n^5 log n splits into n^4 boundary + gcd-sum terms",
        "c_hat": c_hat,
        "residuals": residuals,
        "resid_over_n4_n>=10": {
            "min": min(r_n4),
            "max": max(r_n4),
            "mean": sum(r_n4) / len(r_n4),
            "first": r_n4[0],
            "last": r_n4[-1],
        },
        "note": "raw residual after fixed c_hat; sign drift indicates higher-order/log terms remain",
    }
    print(f"B473 c_hat={c_hat:.6f} resid/n4 n>=10: min={min(r_n4):.4f} max={max(r_n4):.4f}", flush=True)

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
