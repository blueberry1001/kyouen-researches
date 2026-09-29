#!/usr/bin/env python3
"""B286 / B287: coordinate compression / large-coordinate necessity.

Given a combinatorial point set with forbidden 4-sets (collinear/cocircular
dependencies), find the smallest integer-grid embedding that preserves the
dependency structure (which 4-subsets are cocircular/collinear).

Method: start from the B281 witness pairs (same Q, non-D4-congruent on 4x4),
then search integer embeddings with small coordinate bounds and measure
min max-abs-coordinate for k-point configurations with a given Q signature.

Also: for k-point subsets of the n x n grid, measure the smallest side length
m such that the same Q-signature can be realized inside an m x m grid.
"""
import json
from itertools import combinations
from pathlib import Path

OUT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b286_coord.json")


def det4(rows):
    a = [[int(rows[i][j]) for j in range(4)] for i in range(4)]
    total = 0
    for i in range(4):
        mm = [[a[r2][c2] for c2 in range(1, 4)] for r2 in range(4) if r2 != i]
        d3 = (mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
              - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
              + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]))
        total += (1 if i % 2 == 0 else -1) * a[i][0] * d3
    return total


def q_signature(pts):
    """Return frozenset of 4-subsets (indices) that are cocircular/collinear."""
    k = len(pts)
    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    quads = []
    for a, b, c, d in combinations(range(k), 4):
        if det4([rows[a], rows[b], rows[c], rows[d]]) == 0:
            quads.append((a, b, c, d))
    return frozenset(quads)


def normalize(pts):
    """Translate so minx,miny = 0,0. Return sorted tuple."""
    minx = min(p[0] for p in pts)
    miny = min(p[1] for p in pts)
    return tuple(sorted((x - minx, y - miny) for x, y in pts))


def max_abs(pts):
    return max(max(abs(x), abs(y)) for x, y in pts)


def embed_search(target_sig, k, max_coord=8, max_solutions=50):
    """Search integer embeddings of k points with the given Q signature.
    Points are distinct integer pairs in [-max_coord, max_coord]^2.
    Heuristic: fix first 3 points to break similarity (not done fully),
    brute-force is too big; instead sample structured families.
    """
    # Brute force is C((2M+1)^2, k) which explodes. Use incremental:
    # place points one at a time, pruning by partial signature consistency
    # is hard. Instead: enumerate all k-subsets of a small grid and match.
    solutions = []
    grid = [(x, y) for x in range(0, max_coord + 1) for y in range(0, max_coord + 1)]
    # too many for k>=5 on 9x9=81 pts. Limit.
    if len(grid) > 36:
        grid = [(x, y) for x in range(0, min(max_coord, 5) + 1)
                for y in range(0, min(max_coord, 5) + 1)]
    from itertools import combinations as comb
    for subset in comb(range(len(grid)), k):
        pts = [grid[i] for i in subset]
        # quick reject: |Q| must match
        sig = q_signature(pts)
        if len(sig) != len(target_sig):
            continue
        # full match up to renumbering: compare sorted degree sequences of
        # the 4-uniform hypergraph — cheap necessary condition
        degs = sorted(sum(1 for q in sig if i in q) for i in range(k))
        tdegs = sorted(sum(1 for q in target_sig if i in q) for i in range(k))
        if degs != tdegs:
            continue
        # exact: there must exist a bijection
        # for small k try all bijections? k! = 120 for k=5, 720 for 6.
        # Compare canonical form: sort points, then signature under identity
        # is not enough. Use: signature as sorted tuple of sorted quads
        # relative to sorted point order — not invariant under perm.
        # Do exact matching via backtracking for small k.
        if k <= 6:
            if match_sig(target_sig, sig, k):
                solutions.append(pts)
                if len(solutions) >= max_solutions:
                    break
        else:
            solutions.append(pts)
            if len(solutions) >= max_solutions:
                break
    return solutions


def match_sig(sigA, sigB, k):
    """Check if hypergraphs are isomorphic (k small)."""
    from itertools import permutations
    # map indices of A to B
    for perm in permutations(range(k)):
        mapped = set()
        for q in sigA:
            mapped.add(tuple(sorted(perm[i] for i in q)))
        if mapped == set(sigB):
            return True
    return False


def min_side_for_sig(sig, k, current_side):
    """Find the smallest side length m such that some m x m grid contains
    a k-point set with this Q signature. Search m = 2, 3, ... """
    for m in range(2, current_side + 1):
        grid = [(x, y) for x in range(m) for y in range(m)]
        if len(grid) < k:
            continue
        from itertools import combinations as comb
        for subset in comb(range(len(grid)), k):
            pts = [grid[i] for i in subset]
            s2 = q_signature(pts)
            if len(s2) != len(sig):
                continue
            if match_sig(sig, s2, k):
                return m
    return None


def main():
    out = {}
    # --- B281 witnesses on 4x4, measure min side ---
    # A = {(0,0),(1,0),(2,0),(3,0),(0,1),(3,3)}
    # B = {(0,0),(1,0),(2,0),(3,0),(1,1),(0,2)}
    witA = [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (3, 3)]
    witB = [(0, 0), (1, 0), (2, 0), (3, 0), (1, 1), (0, 2)]
    sigA = q_signature(witA)
    sigB = q_signature(witB)
    out["B281_witA_sig_size"] = len(sigA)
    out["B281_witB_sig_size"] = len(sigB)

    # min side for these signatures
    mA = min_side_for_sig(sigA, 6, 4)
    mB = min_side_for_sig(sigB, 6, 4)
    out["B286_min_side_witA"] = mA
    out["B286_min_side_witB"] = mB

    # --- systematic: k=4..6 on 3x3 and 4x4 ---
    results = []
    for m in (3, 4):
        grid = [(x, y) for x in range(m) for y in range(m)]
        for k in (4, 5, 6):
            if len(grid) < k:
                continue
            sigs = {}
            from itertools import combinations as comb
            for subset in comb(range(len(grid)), k):
                pts = [grid[i] for i in subset]
                sig = q_signature(pts)
                sigs.setdefault(sig, []).append(pts)
            # count signatures and their min max-coord after normalize
            n_sig = len(sigs)
            min_maxabs = {}
            for sig, plist in sigs.items():
                best = min(max_abs(p) for p in plist)
                min_maxabs[sig] = best
            results.append({
                "m": m, "k": k, "n_points": len(grid),
                "n_subsets": sum(len(v) for v in sigs.values()),
                "n_distinct_Q": n_sig,
                "empty_Q_count": sum(1 for s in sigs if len(s) == 0),
                "min_maxabs_dist": {
                    str(a): sum(1 for s, v in min_maxabs.items() if v == a)
                    for a in sorted(set(min_maxabs.values()))
                },
            })
    out["B286_grid_scan"] = results

    # --- B287: do any k-point configs need coords outside the k-1 square? ---
    # A k-point set with non-empty Q: is it always embeddable in (k-1) x (k-1)?
    # Empirical: take all 5-point and 6-point sets on 4x4 with |Q|>=1,
    # check if any requires a coord >= 4 (i.e., cannot fit in 3x3).
    need = {}
    for m in (4,):
        grid = [(x, y) for x in range(m) for y in range(m)]
        for k in (5, 6):
            from itertools import combinations as comb
            stuck = 0
            total = 0
            max_needed = 0
            examples = []
            for subset in comb(range(len(grid)), k):
                pts = [grid[i] for i in subset]
                sig = q_signature(pts)
                if len(sig) == 0:
                    continue
                total += 1
                # min max-abs among embeddings with same sig
                # (already in this grid; check smaller grids)
                mm = max_abs(normalize(pts))
                # try to find embedding in smaller square
                found_small = False
                for m2 in range(2, m):
                    g2 = [(x, y) for x in range(m2) for y in range(m2)]
                    if len(g2) < k:
                        continue
                    for s2 in comb(range(len(g2)), k):
                        p2 = [g2[i] for i in s2]
                        if len(q_signature(p2)) != len(sig):
                            continue
                        if match_sig(sig, q_signature(p2), k):
                            found_small = True
                            break
                    if found_small:
                        break
                if not found_small:
                    stuck += 1
                    if len(examples) < 3:
                        examples.append(normalize(pts))
                    if mm > max_needed:
                        max_needed = mm
            need[f"m4_k{k}"] = {
                "nonempty_Q_total": total,
                "need_full_4x4": stuck,
                "max_needed_maxabs": max_needed,
                "examples": examples,
            }
    out["B287_need_large"] = need

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("WROTE", OUT)
    for k, v in out.items():
        if k != "B286_grid_scan":
            print(k, v)


if __name__ == "__main__":
    main()
