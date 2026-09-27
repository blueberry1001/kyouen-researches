#!/usr/bin/env python3
"""B121-B126,B128: deformation graph G_t on safe sets (size>=t, 1-point add/remove).

Uses pre-enumerated layers from night-research/maxsafe_enum.exe:
  safe_n6_k8.bin (1459292), safe_n6_k9.bin (438952), safe_n6_k10.bin (35316),
  maxsafe_n6_K11.bin (464), safe_n7_k12.bin (177760), safe_n7_k13.bin (2176),
  maxsafe_n7_K14.bin (16).

G_t vertices = safe sets with size >= t; edges = add/remove one point (still safe,
still size >= t).  Optimal width w(A,B) = max{t : A,B in same component of G_t}.
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "data"


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


def det4_rows(n: int):
    rows = []
    for y in range(n):
        for x in range(n):
            rows.append((x * x + y * y, x, y, 1))
    return rows


def build_triples(n: int):
    """per-point list of 3-point masks that complete a forbidden quad."""
    rows = det4_rows(n)
    V = n * n
    triples_by_pt = [[] for _ in range(V)]
    quads = []
    for a in range(V - 3):
        for b in range(a + 1, V - 2):
            for c in range(b + 1, V - 1):
                for d in range(c + 1, V):
                    ids = (a, b, c, d)
                    det = 0
                    for i in range(4):
                        mm = []
                        for r2 in range(4):
                            if r2 == i:
                                continue
                            mm.append([rows[ids[r2]][c2] for c2 in range(1, 4)])
                        det3 = (
                            mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
                            - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
                            + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0])
                        )
                        det += (1 if i % 2 == 0 else -1) * rows[ids[i]][0] * det3
                    if det != 0:
                        continue
                    quads.append(ids)
                    for t in range(4):
                        o = 0
                        for s in range(4):
                            if s != t:
                                o |= 1 << ids[s]
                        triples_by_pt[ids[t]].append(o)
    return triples_by_pt, quads


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        if x not in p:
            p[x] = x
            return x
        root = x
        while p[root] != root:
            root = p[root]
        while p[x] != root:
            p[x], x = root, p[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def layer_masks(layers: dict[int, list[int]], k: int) -> dict[int, int]:
    return {m: m for m in layers[k]}


def union_find_gt(layers: dict[int, list[int]], floor_t: int, ks: list[int]):
    """Union-find on all safe sets of size in ks (all >= floor_t).

    Every add-edge is the reverse of a remove-edge from the larger endpoint, so
    iterating single-bit removals covers the whole G_t edge set.
    """
    dsu = DSU()
    index = {}
    for k in ks:
        if k not in layers:
            continue
        for m in layers[k]:
            index[m] = k
            dsu.find(m)
    for m in index:
        mm = m
        while mm:
            bit = mm & -mm
            mm ^= bit
            nb = m ^ bit
            if nb in index:
                dsu.union(m, nb)
    comp = {}
    for m in index:
        comp.setdefault(dsu.find(m), []).append(m)
    return dsu, index, comp


def components_among_max(comp, max_sets):
    """Map each max set to its component id; group max sets by component."""
    root_of = {}
    for root, members in comp.items():
        for m in members:
            root_of[m] = root
    groups = defaultdict(list)
    missing = []
    for m in max_sets:
        if m not in root_of:
            missing.append(m)
        else:
            groups[root_of[m]].append(m)
    return groups, missing


def width_classes(max_sets, layers, n, ks_desc):
    """w(A,B) via components of G_t for t = max ks down to min ks.

    Returns dict pair->width for a sample, and component counts per t.
    """
    # We compute connectivity among max sets for each floor t.
    result = {}
    max_set = set(max_sets)
    for t in ks_desc:
        use_ks = [k for k in ks_desc if k >= t]
        # restrict layers
        sub = {k: layers[k] for k in use_ks if k in layers}
        dsu, index, comp = union_find_gt(sub, t, sorted(sub))
        groups, missing = components_among_max(comp, max_sets)
        result[t] = {
            "n_max_connected": len(max_set),
            "n_components_touching_max": len(groups),
            "component_sizes_of_max": sorted((len(v) for v in groups.values()), reverse=True),
            "missing_max_in_index": len(missing),
            "largest_component_total": max((len(v) for v in comp.values()), default=0),
            "n_total_vertices": len(index),
        }
    return result


def pair_widths_n6(max_sets, layers, sample_pairs):
    """Compute w(A,B) for sampled pairs using precomputed union-find per t."""
    # Build DSU for t=10,9,8 once and remember root maps.
    root_maps = {}
    for t, use_ks in ((10, [10, 11]), (9, [9, 10, 11]), (8, [8, 9, 10, 11])):
        sub = {k: layers[k] for k in use_ks if k in layers}
        dsu, index, comp = union_find_gt(sub, t, sorted(sub))
        root_maps[t] = {m: dsu.find(m) for m in max_sets}
    out = []
    for a, b in sample_pairs:
        w = None
        for t in (10, 9, 8):
            if root_maps[t].get(a) is not None and root_maps[t][a] == root_maps[t].get(b):
                w = t
                break
        out.append((a, b, w))
    return out


def analyze_n6():
    print("=== n=6 layers ===", flush=True)
    layers = {
        8: load_bin(DATA / "safe_n6_k8.bin"),
        9: load_bin(DATA / "safe_n6_k9.bin"),
        10: load_bin(DATA / "safe_n6_k10.bin"),
        11: load_bin(NIGHT / "maxsafe_n6_K11.bin"),
    }
    for k, v in layers.items():
        print(f"  size {k}: {len(v)}", flush=True)
    max_sets = layers[11]
    print("union-find per floor t ...", flush=True)
    wc = width_classes(max_sets, layers, 6, [11, 10, 9, 8])
    for t, info in wc.items():
        print(f"  G_{t}: {info}", flush=True)

    # B126: sample pairs with same |A\B| and see width spread
    # Also record |A&B| and a residual forbidden-quad overlap density.
    triples_by_pt, quads = build_triples(6)
    print(f"  forbidden quads n=6: {len(quads)}", flush=True)

    # sample up to 400 pairs stratified by |A\B|
    import random

    rng = random.Random(20260927)
    pairs_by_diff = defaultdict(list)
    idx = list(range(len(max_sets)))
    for _ in range(8000):
        i, j = rng.sample(idx, 2)
        a, b = max_sets[i], max_sets[j]
        d = bin(a ^ b).count("1") // 2  # |A\B| = |B\A|
        if len(pairs_by_diff[d]) < 80:
            pairs_by_diff[d].append((i, j, a, b))
    sample = []
    for d, lst in sorted(pairs_by_diff.items()):
        sample.extend(lst)
    print(f"  pair sample: {len(sample)} pairs, diffs={ {d: len(v) for d, v in pairs_by_diff.items()} }", flush=True)

    # widths
    root_maps = {}
    for t, use_ks in ((10, [10, 11]), (9, [9, 10, 11]), (8, [8, 9, 10, 11])):
        sub = {k: layers[k] for k in use_ks if k in layers}
        dsu, index, comp = union_find_gt(sub, t, sorted(sub))
        root_maps[t] = dsu

    def width(a, b):
        for t in (10, 9, 8):
            if root_maps[t].find(a) == root_maps[t].find(b):
                return t
        return None  # not even in G_8 together (or below)

    # residual forbidden-quad density: quads that meet both A\\B and B\\A
    # (i.e. quads that are "stretched" across the pair), normalized.
    def pair_stats(a, b):
        A, B = a, b
        P = A & ~B  # A-only
        Q = B & ~A  # B-only
        inter = A & B
        # quads with at least one point in P and at least one in Q
        cross = 0
        total = len(quads)
        for q in quads:
            qm = (1 << q[0]) | (1 << q[1]) | (1 << q[2]) | (1 << q[3])
            if (qm & P) and (qm & Q):
                cross += 1
        return {
            "diff": bin(A ^ B).count("1") // 2,
            "inter": bin(inter).count("1"),
            "cross_quads": cross,
            "cross_density": cross / total if total else 0,
        }

    rows = []
    for i, j, a, b in sample:
        w = width(a, b)
        st = pair_stats(a, b)
        st["i"], st["j"], st["width"] = i, j, w
        rows.append(st)

    # B126 check: among same (diff, inter), does width vary with cross_quads?
    by_key = defaultdict(list)
    for r in rows:
        by_key[(r["diff"], r["inter"])].append(r)
    b126_ev = []
    for key, lst in sorted(by_key.items()):
        widths = [r["width"] for r in lst]
        crosses = [r["cross_quads"] for r in lst]
        wset = set(widths)
        b126_ev.append({
            "diff_inter": key,
            "n": len(lst),
            "width_set": sorted([w for w in wset if w is not None]) + ([None] if None in wset else []),
            "cross_min": min(crosses),
            "cross_max": max(crosses),
            "widths_by_cross": sorted([(r["cross_quads"], r["width"]) for r in lst])[:20],
        })
    print("  B126 groups:", flush=True)
    for g in b126_ev:
        print(f"    {g}", flush=True)

    # B128: pairs with diff=2. Sequential path through A∩B has drop=2 (subset-closed).
    diff2 = [r for r in rows if r["diff"] == 2]
    print(f"  B128-related diff=2 pairs in sample: {len(diff2)}", flush=True)

    return {
        "n": 6,
        "layers": {k: len(v) for k, v in layers.items()},
        "width_classes": wc,
        "pair_sample": rows,
        "b126_groups": b126_ev,
    }


def bfs_gt(start_masks, floor_t, n, triples_by_pt, max_visit=5_000_000):
    """BFS in G_floor_t from start_masks. Returns visited set and parent map."""
    Vbits = n * n
    full = (1 << Vbits) - 1
    visited = set(start_masks)
    q = deque(start_masks)
    parent = {m: None for m in start_masks}
    steps = 0
    while q:
        m = q.popleft()
        steps += 1
        if steps % 100000 == 0:
            print(f"    BFS visited {len(visited)} frontier {len(q)}", flush=True)
        if len(visited) > max_visit:
            print(f"    BFS aborted at {len(visited)}", flush=True)
            break
        sz = m.bit_count()
        # removals
        if sz > floor_t:
            mm = m
            while mm:
                bit = mm & -mm
                mm ^= bit
                nb = m ^ bit
                if nb not in visited:
                    visited.add(nb)
                    parent[nb] = m
                    q.append(nb)
        # additions
        missing = full ^ m
        mm = missing
        while mm:
            bit = mm & -mm
            mm ^= bit
            v = bit.bit_length() - 1
            # safe to add v iff no triple of v is inside m
            ok = True
            for tmask in triples_by_pt[v]:
                if (m & tmask) == tmask:
                    ok = False
                    break
            if not ok:
                continue
            nb = m | bit
            if nb not in visited:
                visited.add(nb)
                parent[nb] = m
                q.append(nb)
    return visited, parent


def analyze_n7():
    print("=== n=7 layers ===", flush=True)
    layers = {
        12: load_bin(DATA / "safe_n7_k12.bin"),
        13: load_bin(DATA / "safe_n7_k13.bin"),
        14: load_bin(NIGHT / "maxsafe_n7_K14.bin"),
    }
    for k, v in layers.items():
        print(f"  size {k}: {len(v)}", flush=True)
    max_sets = layers[14]
    triples_by_pt, quads = build_triples(7)
    print(f"  forbidden quads n=7: {len(quads)}", flush=True)

    # G_12 components touching max sets (known: 8 comps of 903)
    dsu12, index12, comp12 = union_find_gt(layers, 12, [12, 13, 14])
    groups12, missing12 = components_among_max(comp12, max_sets)
    print(f"  G_12: total vertices {len(index12)}, comps {len(comp12)}, max-touching {len(groups12)}, missing {len(missing12)}", flush=True)
    sizes = sorted((len(v) for v in groups12.values()), reverse=True)
    print(f"  G_12 max-group sizes: {sizes}", flush=True)
    print(f"  G_12 component size hist (all): {Counter(len(v) for v in comp12.values())}", flush=True)

    # G_11 via BFS from the 16 max sets (do not need full layer 11)
    print("  BFS G_11 from 16 max sets ...", flush=True)
    visited, parent = bfs_gt(max_sets, 11, 7, triples_by_pt, max_visit=8_000_000)
    reached_max = [m for m in max_sets if m in visited]
    print(f"  G_11 BFS: visited {len(visited)}, max sets reached {len(reached_max)}/{len(max_sets)}", flush=True)
    by_size = Counter(m.bit_count() for m in visited)
    print(f"  G_11 BFS size hist: {dict(by_size)}", flush=True)

    # B126 n=7: widths among max pairs via G_12 (width 12) vs G_11 (width 11)
    root12 = {m: dsu12.find(m) for m in max_sets}
    pairs = []
    for i in range(len(max_sets)):
        for j in range(i + 1, len(max_sets)):
            a, b = max_sets[i], max_sets[j]
            w12 = root12[a] == root12[b]
            w11 = (a in visited and b in visited)  # all should be if connected
            pairs.append({
                "i": i,
                "j": j,
                "diff": bin(a ^ b).count("1") // 2,
                "inter": bin(a & b).count("1"),
                "same_G12": w12,
                "width": 12 if w12 else (11 if w11 else None),
            })
    print(f"  n=7 pair widths: {Counter((p['diff'], p['width']) for p in pairs)}", flush=True)

    return {
        "n": 7,
        "layers": {k: len(v) for k, v in layers.items()},
        "G12": {
            "n_vertices": len(index12),
            "n_components": len(comp12),
            "max_touching": len(groups12),
            "max_group_sizes": sizes,
            "comp_size_hist": dict(Counter(len(v) for v in comp12.values())),
        },
        "G11_bfs": {
            "visited": len(visited),
            "max_reached": len(reached_max),
            "size_hist": dict(by_size),
        },
        "pairs": pairs,
    }


def main():
    out = {}
    out["n6"] = analyze_n6()
    out["n7"] = analyze_n7()
    path = OUT / "deform_b121_b126.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
