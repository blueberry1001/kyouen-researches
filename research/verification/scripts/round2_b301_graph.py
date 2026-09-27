#!/usr/bin/env python3
"""Round2 B301-B308, B311-B315, B318: graph analysis of J_5 and J_4.

J_n: vertices = board points, edge {p,q} iff g({p,q}) == 0 (2-stone P-position).
Output: research/verification/round2_b301.json (section "graph").
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from itertools import combinations, permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

OUT_JSON = Path(__file__).resolve().parent.parent / "round2_b301.json"


# ---------------- graph helpers ----------------
def adj_from_edges(nverts: int, edges):
    adj = {i: set() for i in range(nverts)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def components(adj):
    seen = set()
    comps = []
    for s in adj:
        if s in seen:
            continue
        q = deque([s])
        seen.add(s)
        comp = []
        while q:
            u = q.popleft()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        comps.append(sorted(comp))
    return comps


def is_bipartite(adj, removed=frozenset()):
    color = {}
    for s in adj:
        if s in removed or s in color:
            continue
        color[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v in removed:
                    continue
                if v not in color:
                    color[v] = 1 - color[u]
                    q.append(v)
                elif color[v] == color[u]:
                    return False
    return True


def bridges_and_articulations(adj, vertices):
    """Return (bridges, articulation_points) on induced subgraph of `vertices`."""
    vs = set(vertices)
    sub = {v: (adj[v] & vs) for v in vs}
    # iterative DFS with lowlink (Hopcroft-Tarjan style)
    disc = {}
    low = {}
    parent = {}
    bridges = []
    arts = set()
    time = [0]

    for root in vs:
        if root in disc:
            continue
        stack = [(root, iter(sorted(sub[root])))]
        disc[root] = low[root] = time[0]
        time[0] += 1
        parent[root] = None
        children = 0
        while stack:
            u, it = stack[-1]
            advanced = False
            for v in it:
                if v not in disc:
                    parent[v] = u
                    disc[v] = low[v] = time[0]
                    time[0] += 1
                    if u == root:
                        children += 1
                    stack.append((v, iter(sorted(sub[v]))))
                    advanced = True
                    break
                elif parent.get(u) != v:
                    low[u] = min(low[u], disc[v])
            if not advanced:
                stack.pop()
                pu = parent[u]
                if pu is not None:
                    low[pu] = min(low[pu], low[u])
                    if low[u] > disc[pu]:
                        bridges.append(tuple(sorted((pu, u))))
                    if low[u] >= disc[pu] and pu != root:
                        arts.add(pu)
                elif children > 1:
                    arts.add(u)
    return bridges, sorted(arts)


def suppress_degree2(adj, vertices):
    """Suppress all degree-2 vertices (in induced subgraph). Return multigraph.

    Result: dict frozenset(u,v) -> multiplicity, on the remaining vertices.
    Paths of degree-2 vertices become single edges (multiplicity counted per path).
    """
    vs = set(vertices)
    sub = {v: (adj[v] & vs) for v in vs}
    deg2 = {v for v in vs if len(sub[v]) == 2}
    remaining = vs - deg2
    multi = defaultdict(int)

    def path_walk(start, mid):
        """Walk maximal path through degree-2 vertices starting at edge start-mid."""
        prev, cur = start, mid
        while cur in deg2:
            nxts = sub[cur] - {prev}
            if len(nxts) != 1:
                break  # unexpected
            prev, cur = cur, next(iter(nxts))
        return cur  # end vertex (degree != 2)

    counted_paths = set()
    for v in deg2:
        for u in sub[v]:
            key = frozenset((v, u))
            if key in counted_paths:
                continue
            # find the two endpoints of the maximal path containing edge (v,u)
            a = path_walk(v, u)
            b = path_walk(u, v)
            # count this path once via frozenset of the two endpoints + a representative
            # better: mark all edges of the path
            # re-walk marking
            prev, cur = v, u
            path_edges = {frozenset((prev, cur))}
            while cur in deg2:
                nxts = sub[cur] - {prev}
                if len(nxts) != 1:
                    break
                nxt = next(iter(nxts))
                path_edges.add(frozenset((cur, nxt)))
                prev, cur = cur, nxt
            end = cur
            prev, cur = u, v
            path_edges.add(frozenset((prev, cur)))
            while cur in deg2:
                nxts = sub[cur] - {prev}
                if len(nxts) != 1:
                    break
                nxt = next(iter(nxts))
                path_edges.add(frozenset((cur, nxt)))
                prev, cur = cur, nxt
            start = cur
            for e in path_edges:
                counted_paths.add(e)
            edge = frozenset((start, end))
            multi[edge] += 1

    # also direct edges between remaining vertices that are not via deg2
    for u in remaining:
        for w in sub[u]:
            if w in remaining and w > u:
                # only if this edge is a "direct" edge not already counted as a path
                # A path through deg2 of length 1 would be just the edge u-w with no deg2.
                # Our walk above only processes edges incident to deg2. Direct edges
                # between remaining vertices must be added if not already present.
                key = frozenset((u, w))
                if multi[key] == 0:
                    multi[key] += 1
                # if a deg2 path collapses to u-w, multi[key] >= 1 already — but a
                # length-1 path (direct edge) and a collapsed longer path can both exist
                # only if there are two distinct u-w edges; in a simple graph that means
                # one direct edge plus one (or more) paths through deg2 vertices.
                # Direct edge is always there as an original simple edge:
                # ensure multiplicity counts the direct edge ONCE in addition to paths
                # that also collapse to u-w. Problem: if the only u-w connection is the
                # direct edge, the walk never visits it (no deg2). multi[key]==0 then
                # we add 1. If a path also collapses to u-w, walk already set multi=1,
                # and the direct edge needs +1.
                # Detect: original graph has simple edge u-w. Count original direct edge
                # as +1 always; paths through deg2 add extra.
                pass

    # Cleaner approach: rebuild from scratch
    multi = defaultdict(int)
    # 1) direct edges among remaining
    for u in remaining:
        for w in sub[u]:
            if w in remaining and w > u:
                multi[frozenset((u, w))] += 1
    # 2) paths through deg2
    visited_edge = set()
    for v in deg2:
        for u in sub[v]:
            e0 = frozenset((v, u))
            if e0 in visited_edge:
                continue
            # walk both directions, collect path edges
            path_edges = set()

            def walk(a, b):
                prev, cur = a, b
                path_edges.add(frozenset((prev, cur)))
                while cur in deg2:
                    nxts = sub[cur] - {prev}
                    if len(nxts) != 1:
                        break
                    nxt = next(iter(nxts))
                    path_edges.add(frozenset((cur, nxt)))
                    prev, cur = cur, nxt
                return cur

            end1 = walk(v, u)
            end2 = walk(u, v)
            for e in path_edges:
                visited_edge.add(e)
            multi[frozenset((end1, end2))] += 1

    return dict(multi), sorted(remaining)


def simple_cycles_upto(adj, vertices, max_len):
    """All simple cycles of length 3..max_len as vertex tuples (canonical)."""
    vs = set(vertices)
    cycles = []
    seen = set()
    verts = sorted(vs)

    def dfs(start, path):
        if len(path) >= 3:
            if start in adj[path[-1]] and start in vs:
                cyc = tuple(path)
                # canonical: rotate so smallest vertex first
                i = cyc.index(min(cyc))
                canon = cyc[i:] + cyc[:i]
                if canon not in seen:
                    seen.add(canon)
                    cycles.append(canon)
        if len(path) >= max_len:
            return
        for w in sorted(adj[path[-1]]):
            if w not in vs or w in path:
                continue
            if w < start:
                continue
            dfs(start, path + [w])

    for s in verts:
        dfs(s, [s])
    return cycles


def cycle_edge_mask(cyc, eids):
    m = 0
    n = len(cyc)
    for i in range(n):
        e = frozenset((cyc[i], cyc[(i + 1) % n]))
        m |= 1 << eids[e]
    return m


def gf2_rank(masks):
    basis = []
    for m in masks:
        x = m
        for b in basis:
            x = min(x, x ^ b)
        if x:
            basis.append(x)
            basis.sort(reverse=True)
    return len(basis), basis


def all_perfect_matchings(adj, vertices, limit=None):
    vs = list(vertices)
    n = len(vs)
    if n % 2:
        return []
    idx = {v: i for i, v in enumerate(vs)}
    nbrs = [set(idx[w] for w in adj[vs[i]] if w in idx) for i in range(n)]
    found = []

    def rec(matched, pairs):
        if limit is not None and len(found) >= limit:
            return
        if matched == (1 << n) - 1:
            found.append(list(pairs))
            return
        # pick first unmatched
        for i in range(n):
            if not (matched >> i) & 1:
                break
        for j in sorted(nbrs[i]):
            if (matched >> j) & 1:
                continue
            rec(matched | (1 << i) | (1 << j), pairs + [(vs[i], vs[j])])

    rec(0, [])
    return found


def total_dominating_sets(adj, vertices, max_k=4):
    """All total dominating sets of size <= max_k (every vertex has neighbor in set)."""
    vs = list(vertices)
    n = len(vs)
    idx = {v: i for i, v in enumerate(vs)}
    nbr_mask = []
    for v in vs:
        m = 0
        for w in adj[v]:
            if w in idx:
                m |= 1 << idx[w]
        nbr_mask.append(m)
    full = (1 << n) - 1
    results = []

    def covers(mask):
        # every vertex has a neighbor in mask
        cov = 0
        i = 0
        m = mask
        while m:
            if m & 1:
                cov |= nbr_mask[i]
            m >>= 1
            i += 1
        return cov == full

    def rec(start, left, sel):
        if left == 0:
            if covers(sel):
                results.append([vs[i] for i in range(n) if (sel >> i) & 1])
            return
        for i in range(start, n - left + 1):
            rec(i + 1, left - 1, sel | (1 << i))

    for k in range(1, max_k + 1):
        rec(0, k, 0)
        if results:
            return k, results
    return None, results


def closed_dom_sets(adj, vertices, max_k=4):
    """All closed-neighborhood dominating sets of size <= max_k."""
    vs = list(vertices)
    n = len(vs)
    idx = {v: i for i, v in enumerate(vs)}
    closed = []
    for v in vs:
        m = 1 << idx[v]
        for w in adj[v]:
            if w in idx:
                m |= 1 << idx[w]
        closed.append(m)
    full = (1 << n) - 1
    results = []

    def covers(mask):
        cov = 0
        i = 0
        m = mask
        while m:
            if m & 1:
                cov |= closed[i]
            m >>= 1
            i += 1
        return cov == full

    def rec(start, left, sel):
        if left == 0:
            if covers(sel):
                results.append([vs[i] for i in range(n) if (sel >> i) & 1])
            return
        for i in range(start, n - left + 1):
            rec(i + 1, left - 1, sel | (1 << i))

    for k in range(1, max_k + 1):
        rec(0, k, 0)
        if results:
            return k, results
    return None, results


def d4_map_ids(n):
    """8 D4 actions as functions id->id on n×n."""
    def pt(x, y):
        return y * n + x

    def inv(i):
        return i % n, i // n

    maps = []
    for f in [
        lambda x, y: (x, y),
        lambda x, y: (y, n - 1 - x),
        lambda x, y: (n - 1 - x, n - 1 - y),
        lambda x, y: (n - 1 - y, x),
        lambda x, y: (n - 1 - x, y),
        lambda x, y: (x, n - 1 - y),
        lambda x, y: (y, x),
        lambda x, y: (n - 1 - y, n - 1 - x),
    ]:
        maps.append(lambda i, f=f: pt(*f(*inv(i))))
    return maps


def d4_orbits_of_edges(n, edges):
    maps = d4_map_ids(n)
    remaining = set(tuple(sorted(e)) for e in edges)
    orbits = []
    while remaining:
        e = remaining.pop()
        orb = {e}
        for mp in maps:
            e2 = tuple(sorted((mp(e[0]), mp(e[1]))))
            orb.add(e2)
        remaining -= orb
        orbits.append(sorted(orb))
    return orbits


def build_j(board: Board, grundy):
    edges = []
    two_g = {}
    for a, b in combinations(range(board.V), 2):
        mask = (1 << a) | (1 << b)
        g = grundy.get(mask)
        two_g[(a, b)] = g
        if g == 0:
            edges.append((a, b))
    return edges, two_g


def analyze_J(n, label):
    print(f"=== solve grundy n={n} ===", flush=True)
    b = board_square(n)
    g = b.solve_grundy()
    print(f"  grundy states={len(g)}", flush=True)
    edges, two_g = build_j(b, g)
    one = {v: g.get(1 << v) for v in range(n * n)}
    W = [v for v in range(n * n) if one[v] == 0]
    adj = adj_from_edges(n * n, edges)
    noniso = sorted([v for v in range(n * n) if adj[v]])
    iso = sorted([v for v in range(n * n) if not adj[v]])
    return {
        "n": n,
        "board": b,
        "grundy": g,
        "edges": edges,
        "two_g": two_g,
        "one": one,
        "W": W,
        "adj": adj,
        "noniso": noniso,
        "iso": iso,
        "K": max(t.bit_count() for t in g),  # not exact K; just max size in memo
    }


def main():
    report = {}
    print("Building J_5 and J_4 ...", flush=True)
    J5 = analyze_J(5, "J5")
    J4 = analyze_J(4, "J4")
    print(f"J5: V_noniso={len(J5['noniso'])} E={len(J5['edges'])} W={len(J5['W'])}", flush=True)
    print(f"J4: V_noniso={len(J4['noniso'])} E={len(J4['edges'])} W={len(J4['W'])}", flush=True)

    # ================= B301 =================
    # Suppress all degree-2 vertices of J_5 non-isolated part.
    adj5 = J5["adj"]
    non5 = J5["noniso"]
    degs = {v: len(adj5[v] & set(non5)) for v in non5}
    multi, remaining = suppress_degree2(adj5, non5)
    b301 = {
        "noniso": non5,
        "degrees": degs,
        "deg2_count": sum(1 for v in non5 if degs[v] == 2),
        "remaining_vertices": remaining,
        "remaining_count": len(remaining),
        "multigraph": {str(sorted(k)): v for k, v in multi.items()},
        "multiplicities": sorted(multi.values()),
    }
    # classify: is it a 4-cycle with doubled edges?
    # remaining should be 4 vertices; multigraph should have 4 pairs each with mult 2
    # forming a 4-cycle
    rem_set = set(remaining)
    # extract adjacency of multigraph
    madj = defaultdict(list)
    for k, m in multi.items():
        a, b = tuple(k)
        madj[a].append((b, m))
        madj[b].append((a, m))
    b301["remaining_degrees"] = {v: len(madj[v]) for v in remaining}
    # check 4-cycle structure
    is_doubled_c4 = False
    if len(remaining) == 4:
        # each remaining vertex should have exactly 2 neighbors, each edge mult 2
        if all(len(madj[v]) == 2 for v in remaining):
            if all(m == 2 for _, mlist in madj.items() for _, m in mlist):
                # check it's a single cycle of 4
                start = remaining[0]
                prev, cur = None, start
                path = []
                for _ in range(5):
                    path.append(cur)
                    nbrs = [w for w, _ in madj[cur] if w != prev]
                    if not nbrs:
                        break
                    prev, cur = cur, nbrs[0]
                is_doubled_c4 = path[:5] == path[:4] + [path[0]] and len(path) == 5
                b301["cycle_order"] = path
    b301["is_doubled_4cycle"] = is_doubled_c4
    report["B301"] = b301
    print("B301", is_doubled_c4, "deg2", b301["deg2_count"], "rem", remaining, flush=True)

    # ================= B302 =================
    # Four 5-cycles (direct side edge + detour path) + corner 4-cycle = cycle basis?
    corners = [0, 4, 20, 24]  # (0,0),(4,0),(0,4),(4,4)
    # find 5-cycles and the perimeter 4-cycle
    eids = {frozenset(e): i for i, e in enumerate(J5["edges"])}
    cyc5 = [c for c in simple_cycles_upto(adj5, non5, 5) if len(c) == 5]
    cyc4 = [c for c in simple_cycles_upto(adj5, non5, 4) if len(c) == 4]
    # cycle space dim
    E = len(J5["edges"])
    V = len(non5)
    C = len(components({v: adj5[v] & set(non5) for v in non5}))
    cdim = E - V + C
    # corner 4-cycle: perimeter
    corner_set = set(corners)
    perimeter = [(0, 4), (4, 24), (24, 20), (20, 0)]
    perimeter_exists = all(frozenset(e) in eids for e in perimeter)
    # four 5-cycles: each is a side edge + alternative path of length 4
    # find all 5-cycles that contain exactly one side edge (perimeter edge) and
    # whose other 4 edges form a path between the same corners
    sides = [frozenset(e) for e in perimeter]
    side5 = []  # (cycle, side_edge)
    for c in cyc5:
        ces = [frozenset((c[i], c[(i + 1) % 5])) for i in range(5)]
        inter = [s for s in ces if s in sides]
        if len(inter) == 1:
            side5.append((c, inter[0]))
    # group by which side
    by_side = defaultdict(list)
    for c, s in side5:
        by_side[tuple(sorted(s))].append(c)
    # candidate basis: 4 side-5-cycles (one per side) + perimeter 4-cycle
    basis_masks = []
    chosen_side5 = []
    if len(by_side) == 4 and all(len(v) >= 1 for v in by_side.values()):
        for s, cands in by_side.items():
            c = cands[0]
            chosen_side5.append(c)
            basis_masks.append(cycle_edge_mask(c, eids))
        basis_masks.append(cycle_edge_mask((0, 4, 24, 20), eids) if perimeter_exists else 0)
    rank, _ = gf2_rank(basis_masks) if basis_masks else (0, [])
    # also span of ALL 5-cycles + 4-cycles
    all_short = [cycle_edge_mask(c, eids) for c in cyc5 + cyc4]
    all_rank, _ = gf2_rank(all_short)
    report["B302"] = {
        "cycle_space_dim": cdim,
        "num_5cycles": len(cyc5),
        "num_4cycles": len(cyc4),
        "perimeter_4cycle_exists": perimeter_exists,
        "side_5cycles_by_side": {str(list(k)): v for k, v in by_side.items()},
        "num_sides_with_5cycle": len(by_side),
        "chosen_basis_cycles": [list(c) for c in chosen_side5] + [[0, 4, 24, 20]],
        "rank_of_these5": rank,
        "is_basis": rank == cdim == 5,
        "span_of_all_4_5cycles": all_rank,
    }
    print("B302", report["B302"]["is_basis"], "rank", rank, "dim", cdim, "n5", len(cyc5), flush=True)

    # ================= B303 =================
    # minimum odd cycle transversal on non-isolated part
    # brute force size 1 then 2
    oct_size = None
    oct_set = None
    for k in (1, 2, 3):
        found = False
        for comb in combinations(non5, k):
            if is_bipartite(adj5, set(comb)):
                oct_size = k
                oct_set = list(comb)
                found = True
                break
        if found:
            break
    # also verify size-0 fails
    bip0 = is_bipartite(adj5, set())
    report["B303"] = {
        "bipartite_without_removal": bip0,
        "min_odd_cycle_transversal": oct_size,
        "witness": oct_set,
        "exhaustive_up_to_size": 2 if oct_size is not None and oct_size <= 2 else 3,
    }
    print("B303", oct_size, oct_set, flush=True)

    # ================= B304 =================
    # every edge belongs to some perfect matching
    non_set = set(non5)
    pms = all_perfect_matchings(adj5, non5)
    report["B304"] = {"num_perfect_matchings": len(pms)}
    edge_in_pm = defaultdict(int)
    for pm in pms:
        for e in pm:
            edge_in_pm[frozenset(e)] += 1
    dead_edges = [sorted(e) for e in eids if edge_in_pm[e] == 0]
    # eids includes only J5 edges among all vertices; restrict to noniso
    dead_edges = [sorted(e) for e, i in eids.items() if e <= non_set and edge_in_pm[e] == 0]
    report["B304"].update({
        "num_edges_noniso": len(J5["edges"]),
        "edges_in_some_pm": sum(1 for e in eids if e <= non_set and edge_in_pm[e] > 0),
        "dead_edges": dead_edges,
        "all_edges_in_some_pm": len(dead_edges) == 0,
    })
    print("B304", report["B304"]["all_edges_in_some_pm"], "PM count", len(pms), "dead", dead_edges, flush=True)

    # ================= B305 =================
    # no D4-invariant perfect matching
    maps5 = d4_map_ids(5)
    # D4 acts on the noniso vertex set (it preserves J_5)
    invariant_pms = []
    for pm in pms:
        pm_set = frozenset(frozenset(e) for e in pm)
        ok = True
        for mp in maps5:
            img = frozenset(frozenset((mp(a), mp(b))) for a, b in pm)
            if img != pm_set:
                ok = False
                break
        if ok:
            invariant_pms.append(pm)
    # also check edge-orbit approach: any union of full edge-orbits of size 8?
    orbits = d4_orbits_of_edges(5, J5["edges"])
    orbit_sizes = [len(o) for o in orbits]
    # which orbits are subsets of some pm
    report["B305"] = {
        "num_perfect_matchings": len(pms),
        "num_d4_invariant_pm": len(invariant_pms),
        "invariant_examples": [[list(e) for e in pm] for pm in invariant_pms[:3]],
        "edge_orbit_sizes": orbit_sizes,
    }
    print("B305", len(invariant_pms), "invariant PMs of", len(pms), flush=True)

    # ================= B306 =================
    # matching graph: vertices = perfect matchings; edges = single alternating
    # cycle flip with cycle length <= 10 (always true on 16 verts if even).
    # Symmetric difference of two PMs is a union of even cycles. An elementary
    # exchange flips one such cycle. We connect M-M' if their symmetric
    # difference is a single cycle of length <= 10.
    pm_index = {frozenset(frozenset(e) for e in pm): i for i, pm in enumerate(pms)}
    n_pm = len(pms)

    def symdiff_cycles(pm_a, pm_b):
        """Return list of cycles (vertex lists) in the symmetric difference."""
        ea = set(frozenset(e) for e in pm_a)
        eb = set(frozenset(e) for e in pm_b)
        diff = ea ^ eb
        dadj = defaultdict(list)
        for e in diff:
            a, b = tuple(e)
            dadj[a].append(b)
            dadj[b].append(a)
        seen = set()
        cycles = []
        for s in dadj:
            if s in seen:
                continue
            # walk the alternating cycle
            cyc = []
            prev, cur = None, s
            while cur not in seen:
                seen.add(cur)
                cyc.append(cur)
                nbrs = [w for w in dadj[cur] if w != prev]
                if not nbrs:
                    break
                prev, cur = cur, nbrs[0]
            if len(cyc) >= 3:
                cycles.append(cyc)
        return cycles

    # Build matching graph adjacency (only single-cycle diffs of len <= 10)
    mg_adj = defaultdict(set)
    max_symdiff_cycle = 0
    single_cycle_pairs = 0
    for i in range(n_pm):
        for j in range(i + 1, n_pm):
            cycles = symdiff_cycles(pms[i], pms[j])
            lens = [len(c) for c in cycles]
            max_symdiff_cycle = max(max_symdiff_cycle, max(lens) if lens else 0)
            if len(cycles) == 1 and lens[0] <= 10:
                mg_adj[i].add(j)
                mg_adj[j].add(i)
                single_cycle_pairs += 1
    # components of matching graph
    seen = set()
    mg_comps = []
    for i in range(n_pm):
        if i in seen:
            continue
        q = deque([i])
        seen.add(i)
        comp = []
        while q:
            u = q.popleft()
            comp.append(u)
            for v in mg_adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        mg_comps.append(sorted(comp))
    # also: connectivity if we allow ANY single alternating cycle (no length cap)
    mg_adj2 = defaultdict(set)
    for i in range(n_pm):
        for j in range(i + 1, n_pm):
            cycles = symdiff_cycles(pms[i], pms[j])
            if len(cycles) == 1:
                mg_adj2[i].add(j)
                mg_adj2[j].add(i)
    seen2 = set()
    mg_comps2 = []
    for i in range(n_pm):
        if i in seen2:
            continue
        q = deque([i])
        seen2.add(i)
        comp = []
        while q:
            u = q.popleft()
            comp.append(u)
            for v in mg_adj2[u]:
                if v not in seen2:
                    seen2.add(v)
                    q.append(v)
        mg_comps2.append(sorted(comp))
    report["B306"] = {
        "num_perfect_matchings": n_pm,
        "matching_graph_edges_len_le_10": single_cycle_pairs,
        "matching_graph_components_len_le_10": [len(c) for c in mg_comps],
        "connected_len_le_10": len(mg_comps) == 1 if n_pm else None,
        "matching_graph_components_any_single_cycle": [len(c) for c in mg_comps2],
        "connected_any_single_cycle": len(mg_comps2) == 1 if n_pm else None,
        "max_symdiff_cycle_len_observed": max_symdiff_cycle,
    }
    print("B306", report["B306"]["connected_len_le_10"], "comps", report["B306"]["matching_graph_components_len_le_10"], flush=True)

    # ================= B307 =================
    # remove 4 corners -> 4 isomorphic paths
    rem = [v for v in non5 if v not in corners]
    radj = {v: adj5[v] & set(rem) for v in rem}
    rcomps = components(radj)
    # path check: each component is a path (all degrees <=2, connected, exactly 2 endpoints or 1 vertex)
    def is_path(comp):
        cset = set(comp)
        degs_c = {v: len(radj[v] & cset) for v in comp}
        if any(d > 2 for d in degs_c.values()):
            return False
        ends = [v for v in comp if degs_c[v] <= 1]
        # connected already (component). Path iff #ends == 2, or single vertex
        return len(comp) == 1 or len(ends) == 2

    def canon_path(comp):
        cset = set(comp)
        degs_c = {v: len(radj[v] & cset) for v in comp}
        ends = [v for v in comp if degs_c[v] <= 1]
        if len(comp) == 1:
            return (0,)
        if len(ends) != 2:
            return None
        # walk
        path = []
        prev, cur = None, ends[0]
        while True:
            path.append(cur)
            nbrs = [w for w in radj[cur] & cset if w != prev]
            if not nbrs:
                break
            prev, cur = cur, nbrs[0]
        return tuple(len(radj[v] & cset) for v in path)  # shape signature

    paths = []
    all_paths = True
    for comp in rcomps:
        ip = is_path(comp)
        all_paths = all_paths and ip
        paths.append({"verts": comp, "is_path": ip, "canon": canon_path(comp)})
    canon_set = set(p["canon"] for p in paths)
    report["B307"] = {
        "corners_removed": corners,
        "num_components": len(rcomps),
        "components": paths,
        "all_are_paths": all_paths,
        "num_isomorphism_types": len(canon_set),
        "all_isomorphic": len(canon_set) == 1 and all_paths,
    }
    print("B307", report["B307"]["all_isomorphic"], [p["verts"] for p in paths], flush=True)

    # ================= B308 =================
    # minimum total dominating set of J_5 noniso; is any minimum a diagonal corner pair?
    td_size, td_sets = total_dominating_sets(adj5, non5, max_k=6)
    diagonal_pairs = [{0, 24}, {4, 20}]
    is_diag = []
    for s in td_sets:
        if set(s) in diagonal_pairs:
            is_diag.append(s)
    # also: do diagonal pairs work at all (even if not minimum)?
    def is_total_dom(s):
        sset = set(s)
        # every vertex has a neighbor in s
        for v in non5:
            if not (adj5[v] & sset):
                return False
        return True

    diag_ok = {str(sorted(d)): is_total_dom(list(d)) for d in diagonal_pairs}
    # corner-only pairs
    corner_pairs = [list(c) for c in combinations(corners, 2)]
    corner_pair_ok = {str(p): is_total_dom(p) for p in corner_pairs}
    report["B308"] = {
        "total_domination_number": td_size,
        "num_min_total_dominating_sets": len(td_sets),
        "min_sets_sample": td_sets[:8],
        "diagonal_corner_pairs": diag_ok,
        "all_corner_pairs": corner_pair_ok,
        "diagonal_is_min": len(is_diag) > 0,
        "min_sets_include_noncorner": any(any(v not in corners for v in s) for s in td_sets) if td_sets else None,
    }
    print("B308", "gamma_t", td_size, "diag_ok", diag_ok, flush=True)

    # ================= B311 =================
    # J_4 total dominating pair exists?
    adj4 = J4["adj"]
    non4 = J4["noniso"]
    td4_size, td4_sets = total_dominating_sets(adj4, non4, max_k=3)
    cd4_size, cd4_sets = closed_dom_sets(adj4, non4, max_k=3)
    report["B311"] = {
        "V": len(non4),
        "E": len(J4["edges"]),
        "total_domination_number": td4_size,
        "num_min_total_dominating_sets": len(td4_sets),
        "sample": td4_sets[:6],
        "closed_domination_number": cd4_size,
    }
    print("B311", td4_size, "TD sets", len(td4_sets), flush=True)

    # ================= B312 =================
    # total dominating pairs on J_4: are they edges of J_4? D4 types?
    j4_edges = set(frozenset(e) for e in J4["edges"])
    if td4_size == 2:
        td_pairs = [tuple(sorted(s)) for s in td4_sets]
        are_edges = [frozenset(s) in j4_edges for s in td_pairs]
        # D4 types of these pairs
        maps4 = d4_map_ids(4)
        remaining_p = set(td_pairs)
        types = []
        while remaining_p:
            p = remaining_p.pop()
            orb = {tuple(sorted((mp(p[0]), mp(p[1])))) for mp in maps4}
            types.append(sorted(orb))
            remaining_p -= orb
        def td_pair_ok(a, b):
            sset = {a, b}
            for v in non4:
                if not (adj4[v] & sset):
                    return False
            return True

        all_td_pairs = [(a, b) for a, b in combinations(non4, 2) if td_pair_ok(a, b)]
        n_edge_td = sum(1 for p in all_td_pairs if frozenset(p) in j4_edges)
        report["B312"] = {
            "num_total_dom_pairs": len(td_pairs),
            "all_are_P_pairs": all(are_edges),
            "num_P_pairs": len(j4_edges),
            "num_td_pairs_that_are_P": sum(are_edges),
            "d4_types_of_td_pairs": len(types),
            "type_orbit_sizes": [len(t) for t in types],
            "sample_types": [[list(p) for p in t[:3]] for t in types[:4]],
            "all_2subset_td_count": len(all_td_pairs),
            "td_pairs_that_are_P_count": n_edge_td,
        }
    else:
        report["B312"] = {"total_domination_number": td4_size, "note": "gamma_t != 2"}
    print("B312", report["B312"], flush=True)

    # ================= B313 =================
    # perfect matching on J_4 (second-player-win even board)
    pms4 = all_perfect_matchings(adj4, non4, limit=5)
    # for odd-second-player-win n=7 cannot compute; check statement structure
    report["B313"] = {
        "n4_second_player_win": True,  # known fact
        "n4_vertices": len(non4),
        "n4_has_perfect_matching": len(pms4) > 0,
        "n4_pm_count_capped": len(pms4),
        "n4_pm_example": [[list(e) for e in pm] for pm in pms4[:1]],
        "n7_J_not_computed": True,
        "n8_n10_J_not_computed": True,
    }
    print("B313 J4 PM", len(pms4) > 0, flush=True)

    # ================= B314 =================
    # no bridges in non-isolated parts of J_5, J_4
    br5, art5 = bridges_and_articulations(adj5, non5)
    br4, art4 = bridges_and_articulations(adj4, non4)
    report["B314"] = {
        "J5_bridges": br5,
        "J5_num_bridges": len(br5),
        "J4_bridges": br4,
        "J4_num_bridges": len(br4),
        "no_bridges_both": len(br5) == 0 and len(br4) == 0,
    }
    print("B314 bridges J5", len(br5), "J4", len(br4), flush=True)

    # ================= B315 =================
    report["B315"] = {
        "J5_articulation_points": art5,
        "J5_num_arts": len(art5),
        "J4_articulation_points": art4,
        "J4_num_arts": len(art4),
        "exists_on_small": len(art5) > 0 or len(art4) > 0,
    }
    print("B315 arts J5", art5, "J4", art4, flush=True)

    # ================= B318 =================
    # J_4 complement graph: pairs that are NOT P-pairs. 2-stone g values.
    two_g4 = J4["two_g"]
    g2_hist = defaultdict(int)
    for k, v in two_g4.items():
        g2_hist[v] += 1
    # complement edges among noniso (all 16 are noniso on n=4)
    all_pairs = set(combinations(non4, 2))
    comp_edges = [tuple(sorted(p)) for p in all_pairs if frozenset(p) not in j4_edges]
    cadj = adj_from_edges(16, comp_edges)
    ccomps = components(cadj)
    # local types: for each component, degree sequence signature
    comp_sig = []
    for comp in ccomps:
        cset = set(comp)
        degs_c = sorted(len(cadj[v] & cset) for v in comp)
        comp_sig.append({"size": len(comp), "deg_seq": degs_c})
    # one-stone g uniform?
    one4 = J4["one"]
    one_hist = defaultdict(int)
    for v, gv in one4.items():
        one_hist[gv] += 1
    # which 2-stone g values appear
    report["B318"] = {
        "one_stone_hist": dict(one_hist),
        "two_stone_g_hist": dict(g2_hist),
        "j4_edges": len(j4_edges),
        "complement_edges": len(comp_edges),
        "complement_components": comp_sig,
        "num_complement_components": len(ccomps),
        "has_g1_two_stone": 1 in g2_hist,
        "has_g0_two_stone": 0 in g2_hist,
    }
    print("B318 2-stone g hist", dict(g2_hist), "comps", comp_sig, flush=True)

    # store shared graph data for the game script
    report["_shared"] = {
        "j5_edges": [list(e) for e in J5["edges"]],
        "j5_noniso": non5,
        "j5_W": J5["W"],
        "j4_edges": [list(e) for e in J4["edges"]],
        "j4_noniso": non4,
        "j5_two_g_keys": [[a, b, two_g] for (a, b), two_g in list(J5["two_g"].items())[:5]],
    }

    OUT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT_JSON, flush=True)
    return report


if __name__ == "__main__":
    main()
