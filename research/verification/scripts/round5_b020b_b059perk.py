#!/usr/bin/env python3
"""B059 per-k: D4 orbits vs R abstract types for each stone count (n=4)."""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square

OUT = ROOT / "research" / "verification" / "round5_b020b_b059perk.json"

def d4_images(S):
    pts = [(i % 4, i // 4) for i in S]
    ims = set()
    for fx in (0, 1):
        for fy in (0, 1):
            for sw in (0, 1):
                out = []
                for x, y in pts:
                    if fx: x = 3 - x
                    if fy: y = 3 - y
                    if sw: x, y = y, x
                    out.append(y * 4 + x)
                ims.add(tuple(sorted(out)))
    return ims

def main():
    b = board_square(4)
    seen = set()
    # per-k: list of (size_seq_sig, abs_sig)
    by_k = defaultdict(list)
    for occ in range(1, 1 << 16):
        k = occ.bit_count()
        if k < 2:
            continue
        if not b.is_safe(occ):
            continue
        key = tuple(i for i in range(16) if (occ >> i) & 1)
        if key in seen:
            continue
        for im in d4_images(key):
            seen.add(im)
        edges = []
        for q in b.quads:
            rem = q & ~occ & b.full
            if (q & occ).bit_count() >= 2 and rem.bit_count() > 0:
                edges.append(tuple(sorted(i for i in range(16) if (rem >> i) & 1)))
        size_seq = tuple(sorted(len(e) for e in edges))
        esz = Counter(len(e) for e in edges)
        deg = Counter()
        for e in edges:
            for u in e:
                deg[u] += 1
        abs_sig = (tuple(sorted(esz.items())), tuple(sorted(deg.values())))
        by_k[k].append((size_seq, abs_sig))

    rows = []
    for k in sorted(by_k):
        items = by_k[k]
        n_d4 = len(items)
        n_size = len(set(s for s, _ in items))
        n_abs = len(set(a for _, a in items))
        rows.append({
            "k": k,
            "d4_orbits": n_d4,
            "size_seq_types": n_size,
            "abstract_types": n_abs,
            "reduction_vs_d4": (n_d4 / n_abs) if n_abs else None,
        })
        print(f"k={k}: D4={n_d4} size={n_size} abs={n_abs} ratio={n_d4/n_abs if n_abs else 0:.2f}")
    OUT.write_text(json.dumps({"n": 4, "per_k": rows}, indent=2))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
