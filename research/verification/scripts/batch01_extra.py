#!/usr/bin/env python3
"""Batch 01 extras: T* game-length split (B010), refined B017 metrics, B018 punctured boards."""
from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from itertools import combinations, permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, board_square_minus  # noqa: E402

OUT = Path(__file__).resolve().parent.parent


# ---------------- T* (B010) ----------------
def compute_tstar(board: Board, outcomes: dict[int, int], root: int) -> frozenset[int]:
    """Terminal stone counts under outcome-preserving play.
    N (outcome=1): move only to P children. P (outcome=0): any legal move.
    """
    sys.setrecursionlimit(100000)
    memo: dict[int, frozenset[int]] = {}

    def T(occ: int) -> frozenset[int]:
        hit = memo.get(occ)
        if hit is not None:
            return hit
        mv = board.legal_moves(occ)
        if not mv:
            memo[occ] = frozenset({occ.bit_count()})
            return memo[occ]
        acc = set()
        if outcomes[occ] == 1:
            for u in mv:
                ch = occ | (1 << u)
                if outcomes[ch] == 0:
                    acc |= T(ch)
        else:
            for u in mv:
                acc |= T(occ | (1 << u))
        # if N but no P child (shouldn't happen), fall back to all
        if not acc:
            for u in mv:
                acc |= T(occ | (1 << u))
        memo[occ] = frozenset(acc)
        return memo[occ]

    return T(root)


def b010_n5():
    b = board_square(5)
    out = b.solve_outcomes()
    print("n=5 outcomes done", len(out), flush=True)
    results = {}
    for p in range(25):
        if out.get(1 << p, -1) != 0:
            continue  # only winning first moves (P after first stone)
        ts = compute_tstar(b, out, 1 << p)
        results[p] = sorted(ts)
    # group by T* set
    groups = defaultdict(list)
    for p, ts in results.items():
        groups[tuple(ts)].append(p)
    return {
        "n": 5,
        "winning_first_moves": len(results),
        "tstar_by_point": results,
        "distinct_tstar_sets": {str(list(k)): v for k, v in groups.items()},
        "split": len(groups) > 1,
    }


def b010_n6(max_points: int = 36):
    b = board_square(6)
    print("n=6 building outcomes...", flush=True)
    out = b.solve_outcomes()
    print("n=6 outcomes", len(out), flush=True)
    results = {}
    for p in range(36):
        if out.get(1 << p, -1) != 0:
            continue
        ts = compute_tstar(b, out, 1 << p)
        results[p] = sorted(ts)
        print(f"  p={p} T*={sorted(ts)}", flush=True)
    groups = defaultdict(list)
    for p, ts in results.items():
        groups[tuple(ts)].append(p)
    return {
        "n": 6,
        "winning_first_moves": len(results),
        "tstar_by_point": results,
        "distinct_tstar_sets": {str(list(k)): v for k, v in groups.items()},
        "split": len(groups) > 1,
    }


# ---------------- B017 refined ----------------
def b017_refined():
    b = board_square(5)
    quads = b.quads
    V = 25
    # Q[p] = set of quad-masks containing p
    Q = [set() for _ in range(V)]
    for q in quads:
        for i in range(V):
            if (q >> i) & 1:
                Q[i].add(q)
    # coquad[p][q] = number of quads containing both
    coquad = [[0] * V for _ in range(V)]
    for q in quads:
        pts = [i for i in range(V) if (q >> i) & 1]
        for i, j in combinations(pts, 2):
            coquad[i][j] += 1
            coquad[j][i] += 1

    # Threat set: points z such that some 2-set completes a quad with p
    # (i.e. z shares a quad with p) — already degenerate.
    # Alternative "completion-role" measure:
    # For point p, the set of unordered pairs {x,y} such that {p,x,y} is contained
    # in some forbidden quad (p with a pair nearly completing).
    # Overlap of pair-families of a and b.
    pairs_of = [set() for _ in range(V)]
    for q in quads:
        pts = [i for i in range(V) if (q >> i) & 1]
        for i in pts:
            others = [j for j in pts if j != i]
            for pr in combinations(others, 2):
                pairs_of[i].add(pr)

    # grid-neighborhood (king-move)
    def coords(i):
        return i % 5, i // 5

    def king_nbrs(i):
        x, y = coords(i)
        out = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                xx, yy = x + dx, y + dy
                if 0 <= xx < 5 and 0 <= yy < 5:
                    out.add(yy * 5 + xx)
        return out

    king = [king_nbrs(i) for i in range(V)]

    def rowcol(i):
        x, y = coords(i)
        # same row or col points
        return {y * 5 + xx for xx in range(5)} | {yy * 5 + x for yy in range(5)} - {i}

    rc = [rowcol(i) for i in range(V)]

    # Load P pairs
    known = json.loads((ROOT / "night-research/cycle4-n5-two-stone-geometry.json").read_text(encoding="utf-8"))
    p_pairs = [tuple(p["ids"]) for p in known["loss_pairs"]]
    p_set = set(tuple(sorted(e)) for e in p_pairs)
    losing = sorted(set([a for e in p_pairs for a in e]))

    def stats(pairs, fn):
        vals = [fn(a, b) for a, b in pairs]
        return {
            "mean": round(sum(vals) / len(vals), 3),
            "min": min(vals),
            "max": max(vals),
            "values": sorted(vals),
        }

    def jac_pair_family(a, b):
        A, B = pairs_of[a], pairs_of[b]
        if not A and not B:
            return 0.0
        return len(A & B) / len(A | B)

    measures = {
        "coquad_count": lambda a, b: coquad[a][b],
        "jacard_pair_completion_family": jac_pair_family,
        "king_common": lambda a, b: len(king[a] & king[b]),
        "rowcol_common": lambda a, b: len(rc[a] & rc[b]),
    }

    all_pairs = list(combinations(losing, 2))
    nonP = [(a, b) for a, b in all_pairs if (a, b) not in p_set]
    out = {}
    for name, fn in measures.items():
        out[name] = {
            "P_pairs": stats([(a, b) for a, b in p_pairs], fn),
            "nonP_among_losing": stats(nonP, fn),
        }
    # also degrees
    out["note"] = (
        "pairs_of[i] = 2-subsets {x,y} with {i,x,y} inside some forbidden quad. "
        "Overlap measures complementarity of geometric completion roles."
    )
    return out


# ---------------- B018 punctured / small boards ----------------
def graph_canon(nverts, edges):
    """Canonical form of simple graph: sorted sorted-adjacency tuple under min over perms
    of same degree sequence (small n)."""
    if nverts > 8:
        raise ValueError("too big")
    adj = [0] * nverts
    for a, b in edges:
        adj[a] |= 1 << b
        adj[b] |= 1 << a
    deg = [bin(adj[i]).count("1") for i in range(nverts)]
    # group vertices by degree for permutation pruning
    order = sorted(range(nverts), key=lambda i: (deg[i], adj[i]))

    def apply_perm(perm):
        # perm[i] = image of vertex i
        new_adj = [0] * nverts
        for i in range(nverts):
            a = adj[i]
            m = 0
            while a:
                b = a & -a
                j = b.bit_length() - 1
                m |= 1 << perm[j]
                a ^= b
            new_adj[perm[i]] = m
        return tuple(new_adj)

    best = None
    # only permute within degree classes
    classes = defaultdict(list)
    for i in range(nverts):
        classes[deg[i]].append(i)

    def rec(keys, mapping):
        nonlocal best
        if not keys:
            val = apply_perm(mapping)
            if best is None or val < best:
                best = val
            return
        cls = keys[0]
        members = classes[cls]
        for images in permutations(range(nverts)):
            # images assigned to members in order; must be unused and same degree
            used = set(mapping.values())
            ok = True
            mp = dict(mapping)
            for m, im in zip(members, images):
                if im in used or deg[im] != cls:
                    ok = False
                    break
                mp[m] = im
            if not ok:
                continue
            # too many perms; instead iterate combinations of remaining
            rec(keys[1:], mp)

    # simpler brute force for n<=7: all perms of same degree multiset
    from itertools import permutations as P

    def all_same_deg_perms():
        # generate all perms pi with deg[pi(i)]=deg[i]
        lists = [classes[deg[i]] for i in range(nverts)]
        # cartesian with distinctness
        def rec2(i, used, mp):
            if i == nverts:
                yield dict(mp)
                return
            for j in lists[i]:
                if j in used:
                    continue
                used.add(j)
                mp[i] = j
                yield from rec2(i + 1, used, mp)
                used.pop()
                del mp[i]
        yield from rec2(0, set(), {})

    for mp in all_same_deg_perms():
        val = apply_perm([mp[i] for i in range(nverts)])
        if best is None or val < best:
            best = val
    return best


def three_stone_signature(board: Board, grundy):
    """Abstract 3-stone P structure: sorted g-values of 3-subsets that are safe."""
    V = board.V
    vals = []
    for comb in combinations(range(V), 3):
        mask = (1 << comb[0]) | (1 << comb[1]) | (1 << comb[2])
        g = grundy.get(mask)
        if g is not None:
            vals.append(g)
    return {
        "safe_3sets": len(vals),
        "P_3sets": sum(1 for v in vals if v == 0),
        "grundy_hist": {str(k): vals.count(k) for k in sorted(set(vals))},
    }


def board_from_points(pts, name):
    return Board(pts, name=name)


def b018_search():
    """Search small point-sets (punctured grids / rects) for isomorphic J, different 3-stone."""
    candidates = []
    # full 3x3
    candidates.append(("3x3", [(x, y) for y in range(3) for x in range(3)]))
    # 3x3 minus 1
    for hole in range(9):
        pts = [(x, y) for y in range(3) for x in range(3) if y * 3 + x != hole]
        candidates.append((f"3x3-1_{hole}", pts))
    # 3x3 minus 2
    for h1, h2 in combinations(range(9), 2):
        pts = [(x, y) for y in range(3) for x in range(3) if y * 3 + x not in (h1, h2)]
        candidates.append((f"3x3-2_{h1}_{h2}", pts))
    # rectangles
    for w, h in [(2, 3), (2, 4), (3, 4), (2, 5), (3, 5)]:
        if w * h <= 12:
            candidates.append((f"{w}x{h}", [(x, y) for y in range(h) for x in range(w)]))
    # 4x4 minus 3 in a corner pattern? keep V<=10 for full grundy
    for hole_set in [
        [(0, 0)],
        [(0, 0), (1, 0)],
        [(0, 0), (3, 3)],
        [(0, 0), (3, 0)],
        [(1, 1)],
    ]:
        pts = [(x, y) for y in range(4) for x in range(4) if (x, y) not in hole_set]
        candidates.append((f"4x4-del{len(hole_set)}_{hole_set}", pts))

    records = []
    for name, pts in candidates:
        if not (4 <= len(pts) <= 11):
            continue
        b = board_from_points(pts, name)
        g = b.solve_grundy()
        # J graph on V vertices
        edges = []
        for a, c in combinations(range(b.V), 2):
            if g.get((1 << a) | (1 << c)) == 0:
                edges.append((a, c))
        # isolated = winning-ish
        try:
            jcanon = graph_canon(b.V, edges)
        except Exception as e:
            jcanon = None
        sig3 = three_stone_signature(b, g)
        # also 2-stone grundy hist
        g2 = [g.get((1 << a) | (1 << c)) for a, c in combinations(range(b.V), 2)]
        g2h = {str(k): g2.count(k) for k in sorted(set(x for x in g2 if x is not None))}
        rec = {
            "name": name,
            "V": b.V,
            "points": pts,
            "forbidden": len(b.quads),
            "j_edges": len(edges),
            "j_canon": jcanon,
            "empty_g": g.get(0),
            "g2_hist": g2h,
            "g3": sig3,
        }
        records.append(rec)
        print(f"  {name} V={b.V} |E_J|={len(edges)} empty_g={rec['empty_g']} P3={sig3['P_3sets']}", flush=True)

    # group by j_canon
    by_j = defaultdict(list)
    for r in records:
        key = r["j_canon"]
        by_j[str(key) if key is not None else f"V{r['V']}_E{r['j_edges']}"].append(r)

    collisions = []
    for k, group in by_j.items():
        if len(group) < 2:
            continue
        # compare 3-stone structure within group
        sigs = set()
        for r in group:
            sigs.add((r["g3"]["P_3sets"], r["g3"]["safe_3sets"], tuple(sorted(r["g3"]["grundy_hist"].items()))))
        if len(sigs) > 1:
            collisions.append(
                {
                    "j_canon_key": k[:200],
                    "boards": [
                        {"name": r["name"], "V": r["V"], "g3": r["g3"], "j_edges": r["j_edges"], "g2_hist": r["g2_hist"]}
                        for r in group
                    ],
                    "distinct_g3_sigs": len(sigs),
                }
            )
    return {
        "num_boards": len(records),
        "records": [
            {k: v for k, v in r.items() if k != "j_canon"} | {"j_canon": None if r["j_canon"] is None else "omitted", "j_canon_key": str(r["j_canon"])[:80]}
            for r in records
        ],
        "isomorphic_J_different_3stone": collisions,
    }


def main():
    report = {}

    print("=== B017 refined ===", flush=True)
    report["b017"] = b017_refined()
    print(json.dumps(report["b017"], indent=1)[:2000], flush=True)

    print("=== B010 n=5 ===", flush=True)
    report["b010_n5"] = b010_n5()
    print(json.dumps(report["b010_n5"], indent=1)[:2000], flush=True)

    print("=== B018 search ===", flush=True)
    report["b018"] = b018_search()
    print("collisions:", len(report["b018"]["isomorphic_J_different_3stone"]), flush=True)
    print(json.dumps(report["b018"]["isomorphic_J_different_3stone"], indent=1)[:3000], flush=True)

    path = OUT / "batch01_extra.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
