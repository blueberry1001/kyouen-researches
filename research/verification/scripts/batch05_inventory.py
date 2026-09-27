#!/usr/bin/env python3
"""Batch 05 inventory: K_n / s_n table checks, witness safety, B099 probe."""
from __future__ import annotations

import itertools
import json
import random
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification"


def det4(p, q, r, s):
    pts = [p, q, r, s]
    A = [[pts[i][0] ** 2 + pts[i][1] ** 2, pts[i][0], pts[i][1], 1] for i in range(4)]

    def d3(rows):
        return (
            rows[0][0] * (rows[1][1] * rows[2][2] - rows[1][2] * rows[2][1])
            - rows[0][1] * (rows[1][0] * rows[2][2] - rows[1][2] * rows[2][0])
            + rows[0][2] * (rows[1][0] * rows[2][1] - rows[1][1] * rows[2][0])
        )

    det = 0
    for j in range(4):
        minor = [[A[i][c] for c in range(4) if c != j] for i in range(1, 4)]
        cof = d3(minor)
        if j % 2 == 0:
            det += A[0][j] * cof
        else:
            det -= A[0][j] * cof
    return det


def xy(pid, n):
    return (pid % n, pid // n)


def is_safe(points, n):
    pts = [xy(p, n) for p in points]
    for quad in itertools.combinations(pts, 4):
        if det4(*quad) == 0:
            return False, quad
    return True, None


def build_forbidden(n):
    pts = n * n
    coords = [(i % n, i // n) for i in range(pts)]
    quads = []
    for i, j, k, l in itertools.combinations(range(pts), 4):
        if det4(coords[i], coords[j], coords[k], coords[l]) == 0:
            quads.append((i, j, k, l))
    return quads


def is_maximal_safe(points, n):
    ok, _ = is_safe(points, n)
    if not ok:
        return False, "unsafe"
    s = set(points)
    free = []
    for p in range(n * n):
        if p in s:
            continue
        if is_safe(list(s | {p}), n)[0]:
            free.append(p)
    return (len(free) == 0), free


def count_line_triples(points, n):
    pts = [xy(p, n) for p in points]
    collinear_triples = 0
    total_triples = 0
    for tri in itertools.combinations(range(len(pts)), 3):
        total_triples += 1
        (x1, y1), (x2, y2), (x3, y3) = [pts[i] for i in tri]
        if (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0:
            collinear_triples += 1
    return total_triples, collinear_triples


def analyze_minimal_examples():
    examples = {
        "n5_s5": (5, [2, 6, 7, 8, 22]),
        "n6_s6": (6, [1, 2, 18, 19, 23, 31]),
        "n7_s7": (7, [1, 9, 22, 23, 27, 44, 45]),
        "n10_s11": (10, [11, 20, 23, 32, 43, 50, 59, 63, 68, 81, 98]),
        "n10_s11b": (10, [3, 38, 41, 42, 53, 54, 59, 64, 65, 93, 95]),
        "n8_greedy10": (8, [1, 4, 7, 14, 20, 22, 38, 42, 53, 59]),
        "n9_greedy11": (9, [1, 4, 22, 29, 36, 40, 56, 62, 64, 70, 71]),
    }
    out = {}
    for name, (n, S) in examples.items():
        ok, _ = is_safe(S, n)
        maximal, free = is_maximal_safe(S, n)
        t, c = count_line_triples(S, n)
        out[name] = {
            "n": n,
            "size": len(S),
            "safe": ok,
            "maximal": maximal,
            "n_free_if_not": len(free) if isinstance(free, list) else free,
            "triples": t,
            "collinear_triples": c,
            "noncollinear_triples": t - c,
        }
    return out


def kn_table_checks():
    kn = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15}
    kn_lb = {9: 17}
    rows = []
    for n in sorted(kn):
        k = kn[n]
        rows.append({
            "n": n,
            "K_n": k,
            "K_n_minus_2n": k - 2 * n,
            "K_over_n": k / n,
            "delta": None if n == 1 else k - kn[n - 1],
            "delta_le_3": None if n == 1 else (k - kn[n - 1]) <= 3,
        })
    n = 9
    k = kn_lb[n]
    rows.append({
        "n": n,
        "K_n_lb": k,
        "K_n_minus_2n_lb": k - 2 * n,
        "K_over_n_lb": k / n,
        "delta_lb": k - kn[8],
        "delta_le_3_possible": (k - kn[8]) <= 3,
    })
    return {
        "K_n_table": rows,
        "monotone_so_far": all(kn[i] <= kn[i + 1] for i in kn if i + 1 in kn),
        "max_observed_delta": max(kn[i + 1] - kn[i] for i in kn if i + 1 in kn),
        "max_observed_abs_K_minus_2n": max(abs(v - 2 * n) for n, v in kn.items()),
    }


def sn_inventory():
    return {
        "confirmed": {3: 5, 4: 5, 5: 5, 6: 6, 7: 7},
        "brackets": {
            8: {"lower": 7, "upper": 10, "witness": [1, 4, 7, 14, 20, 22, 38, 42, 53, 59], "source": "F-AS greedy + complete k<=6 nonexist"},
            9: {"lower": None, "upper": 11, "witness": [1, 4, 22, 29, 36, 40, 56, 62, 64, 70, 71], "source": "F-AS greedy"},
            10: {"lower": 7, "upper": 11, "witness": [11, 20, 23, 32, 43, 50, 59, 63, 68, 81, 98], "source": "F-BE complete k=6 nonexist + F-AK 11-witness"},
        },
        "sequence_so_far": [5, 5, 5, 6, 7],
        "deltas": [0, 0, 1, 1],
    }


def try_s8_targeted(seed=1, trials=6000, target=9):
    n = 8
    forbidden = build_forbidden(n)
    by_point = [[] for _ in range(n * n)]
    for q in forbidden:
        for p in q:
            by_point[p].append(q)
    rng = random.Random(seed)
    best = 999
    best_set = None
    hits = {}
    t0 = time.time()
    for trial in range(trials):
        order = list(range(n * n))
        rng.shuffle(order)
        occ = []
        occ_set = set()
        for p in order:
            ok = True
            for q in by_point[p]:
                others = [x for x in q if x != p]
                if all(x in occ_set for x in others):
                    ok = False
                    break
            if ok:
                occ.append(p)
                occ_set.add(p)
        changed = True
        while changed:
            changed = False
            for p in range(n * n):
                if p in occ_set:
                    continue
                ok = True
                for q in by_point[p]:
                    others = [x for x in q if x != p]
                    if all(x in occ_set for x in others):
                        ok = False
                        break
                if ok:
                    occ.append(p)
                    occ_set.add(p)
                    changed = True
                    break
        sz = len(occ)
        hits[sz] = hits.get(sz, 0) + 1
        if sz < best:
            best = sz
            best_set = occ[:]
            if best <= target:
                return {
                    "found_size": best,
                    "set": best_set,
                    "trials_done": trial + 1,
                    "seconds": time.time() - t0,
                    "hist": hits,
                }
    return {
        "found_size": best,
        "set": best_set,
        "trials_done": trials,
        "seconds": time.time() - t0,
        "hist": hits,
    }


def spectrum_known():
    return {
        3: {5: 56},
        4: {5: 176, 6: 688, 7: 64},
        5: {5: 4, 6: 1136, 7: 11280, 8: 4340, 9: 100},
        6: {6: 8, 7: 3952, 8: 115496, 9: 199184, 10: 30492, 11: 464},
        "interval_so_far": True,
        "n7_incomplete": True,
        "n8_incomplete": True,
    }


def main():
    print("=== K_n table ===")
    kn = kn_table_checks()
    print(json.dumps(kn, indent=2))
    print("=== s_n inventory ===")
    print(json.dumps(sn_inventory(), indent=2))
    print("=== witness verification ===")
    ex = analyze_minimal_examples()
    print(json.dumps(ex, indent=2))
    print("=== spectrum ===")
    print(json.dumps(spectrum_known(), indent=2))
    print("=== s8 targeted greedy ===")
    s8 = try_s8_targeted()
    print(json.dumps(s8, indent=2))
    payload = {
        "kn": kn,
        "sn": sn_inventory(),
        "witnesses": ex,
        "spectrum": spectrum_known(),
        "s8_greedy": s8,
    }
    (OUT / "batch05_inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("wrote", OUT / "batch05_inventory.json")


if __name__ == "__main__":
    main()

