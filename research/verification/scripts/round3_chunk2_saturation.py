#!/usr/bin/env python3
"""round3 chunk2 / B092-B100 : s_n, spectrum, saturation, in fast stages.

Stage A (fast, < 1 min): per-n completion statistics, random maximal census.
Stage B (fast): maximal size spectrum for n=4..8 by constructive search.
Stage C: B099 line/circle capacity attribution.
Writes incremental JSON after every stage so partial results survive.
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round3_chunk2_geom import bitl, legal_moves, quad_masks, triples_by_point  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk2_saturation.json"


def save(rep):
    OUT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")


def census(n, rng, tries):
    tbp = triples_by_point(n)
    hist = Counter()
    allm = []
    for _ in range(tries):
        m = 0
        while True:
            mv = legal_moves(m, n, tbp)
            if not mv:
                break
            m |= 1 << rng.choice(mv)
        hist[m.bit_count()] += 1
        allm.append(m)
    return allm, hist


def stage_a(rep):
    print("=== Stage A: s_n random maximal census ===", flush=True)
    rng = random.Random(20260927)
    rep["A_census"] = {}
    for n in (5, 6, 7, 8, 9, 10, 11):
        t0 = time.time()
        allm, hist = census(n, rng, 1200)
        allm = sorted(set(allm), key=int.bit_count)
        d = {"n_tries": 1200, "size_hist": dict(sorted(hist.items())),
             "min": allm[0].bit_count(), "min_witness": bitl(allm[0]),
             "distinct": len(allm), "secs": round(time.time() - t0, 1)}
        rep["A_census"][n] = d
        print(f"  n={n}: min={d['min']} hist={d['size_hist']} "
              f"({d['secs']}s)", flush=True)
        save(rep)
    return allm


def stage_b(rep):
    print("\n=== Stage B: maximal size spectrum (constructive) ===", flush=True)
    rng = random.Random(777)
    rep["B_spectrum"] = {}
    for n in (4, 5, 6, 7, 8):
        t0 = time.time()
        tbp = triples_by_point(n)
        qm = quad_masks(n)
        have = {}

        def shrink(m):
            improved = True
            while improved:
                improved = False
                order = bitl(m)
                rng.shuffle(order)
                for p in order:
                    t = m & ~(1 << p)
                    if not legal_moves(t, n, tbp):
                        m = t
                        improved = True
                        break
            return m

        def add(m):
            if m.bit_count() not in have:
                have[m.bit_count()] = m
            for v in legal_moves(m, n, tbp):
                add(shrink(m | (1 << v)))
            for p in bitl(m):
                t = m & ~(1 << p)
                if not any((t & q) == q for q in qm):
                    add(shrink(t))

        for _ in range(400):
            m = 0
            while True:
                mv = legal_moves(m, n, tbp)
                if not mv:
                    break
                m |= 1 << rng.choice(mv)
            add(m)
        lo, hi = min(have), max(have)
        miss = [k for k in range(lo, hi + 1) if k not in have]
        rep["B_spectrum"][n] = {
            "sizes": sorted(have), "min": lo, "max": hi,
            "missing_inside_range": miss,
            "examples": {str(k): bitl(v) for k, v in sorted(have.items())},
            "secs": round(time.time() - t0, 1),
        }
        print(f"  n={n}: sizes {sorted(have)} missing={miss} "
              f"({rep['B_spectrum'][n]['secs']}s)", flush=True)
        save(rep)


def stage_c(rep):
    print("\n=== Stage C: B099 line/circle capacity attribution ===", flush=True)
    rng = random.Random(31337)
    rep["C_b099"] = {}
    for n in (5, 6, 7, 8):
        tbp = triples_by_point(n)
        # c(T): exact number of board points blocked by triple T
        cT = Counter()
        for v in range(n * n):
            for o in tbp[v]:
                cT[o] += 1
        allm, hist = census(n, rng, 1500)
        allm = sorted(set(allm), key=int.bit_count)
        small = allm[:60]
        rows = []
        for m in small:
            pts = bitl(m)
            L = Cn = Lcap = Ccap = 0
            for T in combinations(pts, 3):
                tm = (1 << T[0]) | (1 << T[1]) | (1 << T[2])
                c = cT.get(tm, 0)
                if c == 0:
                    continue
                x1, y1 = T[0] % n, T[0] // n
                x2, y2 = T[1] % n, T[1] // n
                x3, y3 = T[2] % n, T[2] // n
                if (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0:
                    L += 1
                    Lcap += c
                else:
                    Cn += 1
                    Ccap += c
            rows.append({"k": m.bit_count(), "pts": pts, "L": L, "C": Cn,
                         "Lcap": Lcap, "Ccap": Ccap})
        nsmall = len(small)
        lshare = sum(r["Lcap"] for r in small) / max(1, sum(r["Lcap"] + r["Ccap"] for r in small))
        rep["C_b099"][n] = {
            "n_small": nsmall,
            "mean_Lcap": sum(r["Lcap"] for r in small) / nsmall,
            "mean_Ccap": sum(r["Ccap"] for r in small) / nsmall,
            "line_capacity_share": lshare,
            "mean_L": sum(r["L"] for r in small) / nsmall,
            "mean_C": sum(r["C"] for r in small) / nsmall,
            "examples": small[:12],
        }
        print(f"  n={n}: line cap share={lshare:.4f} "
              f"meanL={rep['C_b099'][n]['mean_L']:.1f} "
              f"meanC={rep['C_b099'][n]['mean_C']:.1f}", flush=True)
        save(rep)


def stage_d(rep):
    print("\n=== Stage D: cover bound (exact per-triple) ===", flush=True)
    rep["D_cover"] = {}
    for n in (7, 8, 9, 10, 11, 12):
        qm = quad_masks(n)
        cT = Counter()
        for q in qm:
            for T in combinations(bitl(q), 3):
                cT[(1 << T[0]) | (1 << T[1]) | (1 << T[2])] += 1
        V = n * n
        srt = sorted(cT.values(), reverse=True)
        # upper bound on coverage of any k-set: sum of the C(k,3) largest c(T)
        rows = []
        for k in range(1, 25):
            need = V - k
            ntri = k * (k - 1) * (k - 2) // 6
            cap = sum(srt[:ntri])
            rows.append({"k": k, "need": need, "C(k,3)": ntri,
                         "max_coverage": cap, "excluded": cap < need})
        lb = next((r["k"] for r in rows if not r["excluded"]), None)
        rep["D_cover"][n] = {"V": V, "max_cT": srt[0], "table": rows,
                             "s_n_lower_bound": lb}
        print(f"  n={n}: V={V} max c(T)={srt[0]} -> s_n >= {lb}; "
              f"excluded k<=24: "
              f"{[r['k'] for r in rows if r['excluded']]}", flush=True)
        save(rep)


def main():
    rep = {}
    stage_a(rep)
    stage_b(rep)
    stage_c(rep)
    stage_d(rep)
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()
