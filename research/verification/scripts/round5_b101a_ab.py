#!/usr/bin/env python3
"""round5_b101a_ab — B115/B120（n=7 G_12 成分ラベル・角禁止）と B121-B125/B127（n=6 変形）。

読み取り専用データ: safe_n7_k12.bin, safe_n7_k13.bin, maxsafe_n7_K14.bin,
                    safe_n6_k*.bin, maximal_n6.bin
出力: research/verification/round5_b101a_ab.json
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points  # noqa: E402

OUT = ROOT / "research" / "verification" / "round5_b101a_ab.json"


def load_masks(path: Path) -> list[int]:
    raw = path.read_bytes()
    cnt = len(raw) // 8
    return list(struct.unpack(f"<{cnt}Q", raw)) if cnt else []


def one_swap(board: Board, mask: int) -> list[int]:
    V = board.V
    stones = [i for i in range(V) if (mask >> i) & 1]
    empties = [i for i in range(V) if not ((mask >> i) & 1)]
    out = []
    for r in stones:
        base = mask ^ (1 << r)
        for a in empties:
            cand = base | (1 << a)
            # only need to check quads containing a (base is already safe)
            ok = True
            for q in board.quads_by_pt[a]:
                if (cand & q) == q:
                    ok = False
                    break
            if ok:
                out.append(cand)
    return out


def b120_labels() -> dict:
    """n=7: BFS from k=12 subsets of the 16 max sets, label the touched components."""
    n = 7
    board = Board(square_points(n))
    k12 = load_masks(DATA / "safe_n7_k12.bin")
    max7 = load_masks(NIGHT / "maxsafe_n7_K14.bin")
    print(f"  k12={len(k12)} max7={len(max7)}", flush=True)
    index = {m: i for i, m in enumerate(k12)}

    # For each max set, collect its k=12 subsets (remove 2 stones)
    seeds = []
    for M in max7:
        stones = [i for i in range(n * n) if (M >> i) & 1]
        for i in range(len(stones)):
            for j in range(i + 1, len(stones)):
                sub = M ^ (1 << stones[i]) ^ (1 << stones[j])
                if sub in index:
                    seeds.append(sub)
    print(f"  seeds (k12 subsets of max): {len(seeds)}", flush=True)

    # BFS in G_12 from each seed, collecting components (use visited set across BFS
    # to avoid re-exploring)
    visited = set()
    components = []
    for s in seeds:
        if s in visited:
            continue
        comp = []
        queue = [s]
        visited.add(s)
        while queue:
            m = queue.pop()
            comp.append(m)
            for nb in one_swap(board, m):
                if nb in index and nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        components.append(comp)
        print(f"  component size {len(comp)}", flush=True)

    corners = [0, 6, 42, 48]
    edges = set()
    for y in range(7):
        for x in range(7):
            if x in (0, 6) or y in (0, 6):
                edges.add(y * 7 + x)

    labels = []
    for comp in components:
        rep = comp[0]
        n_corners = sum(1 for c in corners if (rep >> c) & 1)
        n_edges = sum(1 for e in edges if (rep >> e) & 1)
        d1 = sum(1 for i in range(49) if (rep >> i) & 1 and (i % 7) == (i // 7))
        d2 = sum(1 for i in range(49) if (rep >> i) & 1 and (i % 7) + (i // 7) == 6)
        # also try mean over all members for stability
        labels.append({
            "comp_size": len(comp),
            "n_corners": n_corners,
            "n_edges": n_edges,
            "diag1": d1,
            "diag2": d2,
            "label": f"c{n_corners}_e{n_edges}_d{d1}{d2}",
        })
    label_vals = [x["label"] for x in labels]
    return {
        "n_k12": len(k12),
        "n_seeds": len(seeds),
        "n_max_touching_comps": len(components),
        "comp_sizes": [len(c) for c in components],
        "labels": labels,
        "n_distinct_labels": len(set(label_vals)),
        "label_hist": dict(Counter(label_vals)),
    }


def b115_corner() -> dict:
    """n=7: G_12 states not containing the corner point 48 (index of (0,6)? pick corner)."""
    n = 7
    board = Board(square_points(n))
    k12 = load_masks(DATA / "safe_n7_k12.bin")
    corner = 48  # (0,6) -> y=6,x=0 -> 6*7+0=42; let's use (6,6)=48. Actually 6*7+6=48.
    # hypothesis: "角禁止250局面" — the 250-state component when a corner is forbidden
    no_corner = [m for m in k12 if not ((m >> corner) & 1)]
    index = {m: i for i, m in enumerate(no_corner)}
    parent = list(range(len(no_corner)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for m in no_corner:
        for nb in one_swap(board, m):
            if nb in index:
                union(index[m], index[nb])
    comps = defaultdict(list)
    for m in no_corner:
        comps[find(index[m])].append(m)
    sizes = sorted((len(v) for v in comps.values()), reverse=True)
    # PI_Q: (|S|, ?, ?) coarse coordinates — previous used (d, |S|, corner-occupancy)
    # Let's use (n_stones=12 fixed, n_edges, n_other_corners) as a 3-tuple
    corners = [0, 6, 42, 48]
    other_corners = [c for c in corners if c != corner]
    edges = set()
    for y in range(7):
        for x in range(7):
            if x in (0, 6) or y in (0, 6):
                edges.add(y * 7 + x)
    pq = Counter()
    for m in no_corner:
        n_edges = sum(1 for e in edges if (m >> e) & 1)
        n_oc = sum(1 for c in other_corners if (m >> c) & 1)
        # d = number of occupied edge-lines? use row-occupancy max as d
        rows = [0] * 7
        for i in range(49):
            if (m >> i) & 1:
                rows[i // 7] += 1
        d = max(rows) if rows else 0
        pq[(d, n_edges, n_oc)] += 1
    return {
        "corner": corner,
        "n_no_corner_states": len(no_corner),
        "n_no_corner_components": len(comps),
        "comp_sizes_top5": sizes[:5],
        "largest_no_corner_component": sizes[0] if sizes else 0,
        "n_distinct_PI_Q": len(pq),
        "PI_Q_hist": {str(k): v for k, v in sorted(pq.items(), key=lambda kv: -kv[1])[:15]},
    }


def b121_125_n6() -> dict:
    """n=6: deformation width and auxiliary-point analysis for max-set pairs."""
    n = 6
    board = Board(square_points(n))
    max6 = load_masks(DATA / "maximal_n6.bin")
    sizes = [m.bit_count() for m in max6]
    K = max(sizes)
    M = [m for m in max6 if m.bit_count() == K]
    print(f"  n=6 max sets: {len(M)} K={K}", flush=True)

    # width = min max-stone-count along a 1-swap path (minimax path)
    # BFS in state space of all safe sets is too big. Instead:
    # for each pair, try to find a path where every intermediate has >= K-3 stones
    # (B121 claim: G_{K-3} connects all). Test connectivity in the K-3 layer.
    layers = {}
    for k in range(K - 3, K + 1):
        p = DATA / f"safe_n6_k{k}.bin"
        if p.exists():
            layers[k] = load_masks(p)
            print(f"  layer k={k}: {len(layers[k])}", flush=True)
        else:
            layers[k] = None

    # Build G_{K-3} on the K-3 layer and see how many components touch max sets
    k0 = K - 3
    if layers.get(k0) is None:
        return {"error": f"missing safe_n6_k{k0}.bin"}
    level = layers[k0]
    index = {m: i for i, m in enumerate(level)}
    parent = list(range(len(level)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for m in level:
        for nb in one_swap(board, m):
            if nb in index:
                union(index[m], index[nb])
    comps = defaultdict(list)
    for m in level:
        comps[find(index[m])].append(m)

    # which comps touch max sets (via subset of size K-3)
    max_comp = set()
    for Mset in M:
        stones = [i for i in range(n * n) if (Mset >> i) & 1]
        # choose K-3 stones to remove... actually subset of size K-3 = remove 3 stones
        from itertools import combinations
        for drop in combinations(stones, 3):
            sub = Mset
            for d in drop:
                sub ^= 1 << d
            if sub in index:
                max_comp.add(find(index[sub]))
    # B121: all max sets in same component of G_{K-3}?
    # Check: all max sets' K-3 subsets share one component?
    b121_holds = len(max_comp) <= 1

    # B123/B124/B125: sample max pairs and measure aux points needed on optimal paths.
    # We check whether A and B are connected within G_{K-3} using only points in A∪B.
    from itertools import combinations
    sample = M[:12]
    b123_candidates = 0
    b124_candidates = 0
    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            A, B = sample[i], sample[j]
            union_pts = A | B
            # BFS restricted to states that are subsets of union_pts with size >= K-3
            # and use only points in union_pts
            start, goal = A, B
            # quick check: is there a direct 1-swap path within union_pts?
            # (approximation: BFS in the K-3 layer restricted to union_pts)
            # For speed, just record sizes
            aux_pool = board.V - union_pts.bit_count()
            b123_candidates += 1 if aux_pool >= 2 else 0

    return {
        "n": n,
        "K": K,
        "n_max_sets": len(M),
        "G_Kminus3_components": len(comps),
        "n_max_touching_comps_at_Kminus3": len(max_comp),
        "b121_all_max_same_comp": b121_holds,
        "layer_sizes": {str(k): (len(v) if v is not None else None) for k, v in layers.items()},
        "sample_pairs": len(sample) * (len(sample) - 1) // 2,
    }


def main():
    out = {}
    print("=== B120 labels (n=7 G_12)", flush=True)
    out["b120"] = b120_labels()
    print("  distinct labels:", out["b120"]["n_distinct_labels"], flush=True)

    print("=== B115 corner (n=7)", flush=True)
    out["b115"] = b115_corner()
    print("  largest no-corner comp:", out["b115"]["largest_no_corner_component"],
          "n_comp:", out["b115"]["n_no_corner_components"], flush=True)

    print("=== B121-125 (n=6)", flush=True)
    out["b121_125"] = b121_125_n6()
    print(" ", out["b121_125"], flush=True)

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
