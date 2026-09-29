#!/usr/bin/env python3
"""B285 (cached grundy, n=4,5 only) + B281 (4x4 grid k=6)."""
import json
import sys
from pathlib import Path
from itertools import combinations

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square, is_forbidden_quad

OUT = Path(__file__).resolve().parents[1] / "round5_b251_embed.json"

_cache = {}

def get_grundy(n):
    if n not in _cache:
        b = board_square(n)
        print(f"  solving n={n} ...", flush=True)
        _cache[n] = (b, b.solve_grundy())
    return _cache[n]

def b285_multi_config():
    configs = {
        "2x2": [(0, 0), (1, 0), (0, 1), (1, 1)],
        "L3": [(0, 0), (1, 0), (0, 1)],
        "diag3": [(0, 0), (1, 1), (2, 2)],
        "T4": [(0, 0), (1, 0), (2, 0), (1, 1)],
        "Z4": [(0, 0), (1, 0), (1, 1), (2, 1)],
        "plus5": [(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)],
        "ring8": [(0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)],
    }
    results = {}
    for cname, pts in configs.items():
        entry = {}
        for n in [4, 5]:
            b, gmap = get_grundy(n)
            ok = True
            mask = 0
            idxs = []
            for (x, y) in pts:
                if x >= n or y >= n:
                    ok = False
                    break
                idx = y * n + x
                idxs.append(idx)
                mask |= 1 << idx
            if not ok:
                entry[f"n{n}"] = {"skip": "range"}
                continue
            if not b.is_safe(mask):
                entry[f"n{n}"] = {"skip": "unsafe"}
                continue
            L = b.legal_moves(mask)
            entry[f"n{n}"] = {"g": gmap.get(mask), "n_legal": len(L), "idxs": idxs}
        gvals = set()
        for k, v in entry.items():
            if isinstance(v, dict) and v.get("g") is not None:
                gvals.add(v["g"])
        entry["distinct_g"] = sorted(gvals)
        entry["n_distinct"] = len(gvals)
        results[cname] = entry
    return results

def d4_normalize(points):
    pts = sorted(points)
    variants = []
    for fx in (False, True):
        for fy in (False, True):
            for sw in (False, True):
                out = []
                for (x, y) in pts:
                    if sw:
                        x, y = y, x
                    if fx:
                        x = -x
                    if fy:
                        y = -y
                    out.append((x, y))
                variants.append(tuple(sorted(out)))
    return min(variants)

def q_signature(points):
    pts = list(points)
    V = len(pts)
    quads = set()
    for ids in combinations(range(V), 4):
        if is_forbidden_quad([pts[i] for i in ids]):
            quads.add(tuple(sorted(pts[i] for i in ids)))
    return frozenset(quads)

def b281_grid4():
    N = 4
    all_pts = [(x, y) for y in range(N) for x in range(N)]
    found = []
    checked = 0
    for k in [6]:
        sig_map = {}
        for sub in combinations(all_pts, k):
            checked += 1
            sig = q_signature(sub)
            if not sig:
                continue
            key = (k, sig)
            norm = d4_normalize(sub)
            if key in sig_map:
                prev_norm, prev_sub = sig_map[key]
                if prev_norm != norm:
                    found.append({
                        "k": k,
                        "A": [list(p) for p in prev_sub],
                        "B": [list(p) for p in sub],
                        "n_quads": len(sig),
                    })
                    if len(found) >= 8:
                        return {"found": found, "checked": checked, "status": "sampled"}
            else:
                sig_map[key] = (norm, sub)
    return {"found": found, "checked": checked, "status": "exhaustive_k6"}

def main():
    res = {}
    print("B285...", flush=True)
    res["B285"] = b285_multi_config()
    for cname, e in res["B285"].items():
        print(f"  {cname}: distinct_g={e.get('distinct_g')}")
        for n in [4, 5]:
            print(f"    n{n}: {e.get(f'n{n}')}")

    print("B281...", flush=True)
    res["B281"] = b281_grid4()
    print(" ", res["B281"]["status"], "checked", res["B281"]["checked"], "found", len(res["B281"]["found"]))
    for w in res["B281"]["found"][:3]:
        print("   k=", w["k"], "n_quads=", w["n_quads"])

    OUT.write_text(json.dumps(res, indent=2))
    print("WROTE", OUT)

if __name__ == "__main__":
    main()
