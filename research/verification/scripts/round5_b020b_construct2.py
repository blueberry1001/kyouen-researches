#!/usr/bin/env python3
"""B088 follow-up: maximize two-curve (and multi-curve) safe sets inside 10x10."""
from __future__ import annotations
import json, sys, itertools
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import det4

OUT = ROOT / "research" / "verification" / "round5_b020b_construct2.json"

def is_safe(pts):
    k = len(pts)
    if k < 4:
        return True
    S = set(pts)
    if len(S) != k:
        return False  # duplicates
    for comb in itertools.combinations(pts, 4):
        a, b, c, d = comb
        if not all(0 <= p[0] <= 9 and 0 <= p[1] <= 9 for p in comb):
            return False
        r0 = (a[0]*a[0]+a[1]*a[1], a[0], a[1], 1)
        r1 = (b[0]*b[0]+b[1]*b[1], b[0], b[1], 1)
        r2 = (c[0]*c[0]+c[1]*c[1], c[0], c[1], 1)
        r3 = (d[0]*d[0]+d[1]*b[1] if False else d[0]*d[0]+d[1]*d[1], d[0], d[1], 1)
        if det4(r0, r1, r2, r3) == 0:
            return False
    return True

def max_keep(pts):
    best = []
    def rec(i, kept):
        nonlocal best
        if len(kept) + (len(pts) - i) <= len(best):
            return
        if i == len(pts):
            if len(kept) > len(best) and is_safe(kept):
                best = list(kept)
            return
        # try include
        cand = kept + [pts[i]]
        if is_safe(cand):
            rec(i+1, cand)
        # exclude
        rec(i+1, kept)
    rec(0, [])
    return best

def main():
    results = {}

    # Two parabolas y=x^2 and y=x^2+c, in-bounds
    for c in range(0, 5):
        pts = []
        for x in range(0, 10):
            for yoff in (0, c):
                y = x*x + yoff
                if 0 <= y <= 9:
                    pts.append((x, y))
        # dedup preserve order
        seen = set(); pts2 = []
        for p in pts:
            if p not in seen:
                seen.add(p); pts2.append(p)
        kept = max_keep(pts2) if len(pts2) <= 14 else pts2[:14]
        # greedy if large
        if len(pts2) > 14:
            g = []
            for p in pts2:
                if is_safe(g + [p]):
                    g.append(p)
            kept = g
        results[f"parabolas_c{c}"] = {
            "raw": pts2, "raw_k": len(pts2),
            "kept": kept, "k": len(kept),
            "all_safe": is_safe(pts2),
        }
        print(f"parabolas c={c}: raw={len(pts2)} kept={len(kept)} all_safe={is_safe(pts2)}")

    # Two cubics x^3 and x^3+d
    for d in (1, 2, 3, 4):
        pts = []
        for x in range(0, 10):
            for yoff in (0, d):
                y = x**3 + yoff
                if 0 <= y <= 9:
                    pts.append((x, y))
        seen = set(); pts2 = []
        for p in pts:
            if p not in seen:
                seen.add(p); pts2.append(p)
        g = []
        for p in pts2:
            if is_safe(g + [p]):
                g.append(p)
        results[f"cubics_d{d}"] = {"raw_k": len(pts2), "kept": g, "k": len(g),
                                   "all_safe": is_safe(pts2)}
        print(f"cubics d={d}: raw={len(pts2)} kept={len(g)} all_safe={is_safe(pts2)}")

    # Three parallel parabolas y=x^2, x^2+c1, x^2+c2
    pts = []
    for x in range(0, 4):
        for yoff in (0, 1, 2):
            y = x*x + yoff
            if 0 <= y <= 9:
                pts.append((x, y))
    seen = set(); pts2 = []
    for p in pts:
        if p not in seen:
            seen.add(p); pts2.append(p)
    kept = max_keep(pts2)
    results["three_parabolas"] = {"raw": pts2, "raw_k": len(pts2),
                                  "kept": kept, "k": len(kept),
                                  "all_safe": is_safe(pts2)}
    print(f"three_parabolas: raw={len(pts2)} kept={len(kept)} all_safe={is_safe(pts2)}")

    # Lines with 3 pts each, various slopes, greedy packing
    # generate all 3-point collinear triples inside 10x10, greedy set cover style
    triples = []
    for x0 in range(10):
        for y0 in range(10):
            for dx in range(-9, 10):
                for dy in range(-9, 10):
                    if dx == 0 and dy == 0:
                        continue
                    pts = []
                    x, y = x0, y0
                    for _ in range(3):
                        if 0 <= x <= 9 and 0 <= y <= 9:
                            pts.append((x, y))
                        x += dx; y += dy
                    if len(pts) == 3 and pts[0] == (x0, y0):
                        triples.append(tuple(pts))
    # unique triples
    triples = sorted(set(triples))
    print(f"triples={len(triples)}", flush=True)
    # greedy: keep triple if union stays safe
    chosen = []
    used = set()
    for t in triples:
        cand = list(used) + [p for p in t if p not in used]
        if is_safe(cand):
            for p in t:
                used.add(p)
            chosen.append(t)
    results["greedy_triples"] = {
        "n_triples": len(triples),
        "n_chosen": len(chosen),
        "k": len(used),
        "points": sorted(used),
    }
    print(f"greedy_triples: chose {len(chosen)} lines, k={len(used)}")

    best = max(r.get("k", 0) for r in results.values() if isinstance(r, dict))
    results["best_k"] = best
    OUT.write_text(json.dumps(results, indent=2, default=str))
    print("best_k", best)

if __name__ == "__main__":
    main()
