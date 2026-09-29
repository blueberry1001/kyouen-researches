#!/usr/bin/env python3
"""Round5 B079: compute max |compl(T)| on 10x10 for triple completion counts.
compl(T) = {q not in T : T∪{q} is a forbidden 4-set (concyclic or collinear)}.
Also compute for n=5..9 for comparison."""
import sys, time, json
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points
from itertools import combinations

results = {}
for n in [5, 6, 7, 8, 9, 10]:
    t0 = time.time()
    b = Board(square_points(n), f"n{n}")
    V = b.V
    # Build map from triple (sorted tuple) -> list of completion points
    # For each forbidden quad, extract its 4 triples and record the 4th point
    from collections import defaultdict
    triple_compl = defaultdict(list)
    for q in b.quads:
        pts = [i for i in range(V) if q & (1 << i)]
        for omit in range(4):
            tri = tuple(pts[j] for j in range(4) if j != omit)
            triple_compl[tri].append(pts[omit])
    # Now compute max |compl(T)| over all triples that have at least one completion
    max_compl = 0
    max_tri = None
    count_ge2 = 0
    compl_sizes = defaultdict(int)
    for tri, compls in triple_compl.items():
        sz = len(compls)
        compl_sizes[sz] += 1
        if sz > max_compl:
            max_compl = sz
            max_tri = tri
        if sz >= 2:
            count_ge2 += 1
    # Also count ALL triples (including those with 0 completions)
    total_triples = V * (V-1) * (V-2) // 6
    results[n] = {
        "V": V,
        "F_n": len(b.quads),
        "total_triples": total_triples,
        "triples_with_completion": len(triple_compl),
        "triples_multi_completion": count_ge2,
        "max_compl": max_compl,
        "max_tri": max_tri,
        "compl_size_hist": dict(sorted(compl_sizes.items())),
    }
    print(f"n={n}: V={V} F={len(b.quads)} triples_with_compl={len(triple_compl)} "
          f"multi={count_ge2} max_compl={max_compl} time={time.time()-t0:.1f}s", flush=True)

with open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_b079.json", "w") as f:
    json.dump(results, f, indent=2)
print("Done.")
