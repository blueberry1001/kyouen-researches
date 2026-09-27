#!/usr/bin/env python3
"""Batch 01: two-stone P-position graphs J_n (B011-B020) and small-n checks.

J_n: vertices = board points, edge {p,q} iff g({p,q}) == 0 (P-position).
Isolated vertices are winning first moves (recursive definition).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

OUT = Path(__file__).resolve().parent.parent  # research/verification/


# ---------- graph helpers ----------
def neighbors_of_edges(nverts: int, edges: list[tuple[int, int]]) -> dict[int, set[int]]:
    adj = {i: set() for i in range(nverts)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def components(nverts: int, adj: dict[int, set[int]]) -> list[list[int]]:
    seen = set()
    comps = []
    for s in range(nverts):
        if s in seen or s not in adj:
            continue
        # include isolates only if they are keys
        if s not in adj:
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
    # isolates that appear as vertices with empty adj already handled if in adj
    return comps


def is_bipartite(nverts: int, adj: dict[int, set[int]]) -> tuple[bool, list[int] | None, list | None]:
    color = {}
    for s in range(nverts):
        if s in color or s not in adj:
            continue
        if not adj[s] and s not in color:
            color[s] = 0
            continue
        if s in color:
            continue
        color[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in color:
                    color[v] = 1 - color[u]
                    q.append(v)
                elif color[v] == color[u]:
                    # find an odd cycle witness (short BFS path)
                    return False, None, find_odd_cycle(adj, u, v)
    return True, [color[i] for i in range(nverts) if i in color], None


def find_odd_cycle(adj, u, v):
    """Return a vertex list of an odd closed walk through edge u-v."""
    # BFS from u to v in adj minus edge (u,v)
    prev = {u: None}
    q = deque([u])
    banned = (u, v)
    while q:
        x = q.popleft()
        for y in adj[x]:
            if (x, y) == banned or (y, x) == banned:
                continue
            if y not in prev:
                prev[y] = x
                q.append(y)
    if v not in prev:
        return [u, v, u]  # just the edge as 2-cycle? shouldn't happen
    path = []
    cur = v
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    # path from u to v, plus edge v-u closes
    return path + [u]


def perfect_matchings(nverts: int, adj: dict[int, set[int]], vertices: list[int], limit: int = 5):
    """Enumerate perfect matchings on the induced subgraph of `vertices`."""
    vs = list(vertices)
    idx = {v: i for i, v in enumerate(vs)}
    n = len(vs)
    if n % 2:
        return []
    nbrs = [set(idx[w] for w in adj[vs[i]] if w in idx) for i in range(n)]
    found = []

    def rec(matched_mask: int, pairs: list[tuple[int, int]]):
        if len(found) >= limit:
            return
        if matched_mask == (1 << n) - 1:
            found.append(list(pairs))
            return
        # first unmatched
        for i in range(n):
            if not (matched_mask >> i) & 1:
                break
        for j in nbrs[i]:
            if (matched_mask >> j) & 1:
                continue
            rec(matched_mask | (1 << i) | (1 << j), pairs + [(vs[i], vs[j])])
                # only need one branch from i

    rec(0, [])
    return found


def domination_number(nverts: int, adj: dict[int, set[int]], vertices: list[int], max_k: int = 10):
    """Exact domination number of induced subgraph (brute force over size k)."""
    vs = list(vertices)
    n = len(vs)
    idx = {v: i for i, v in enumerate(vs)}
    closed = []
    for i, v in enumerate(vs):
        mask = 1 << i
        for w in adj[v]:
            if w in idx:
                mask |= 1 << idx[w]
        closed.append(mask)
    full = (1 << n) - 1

    def covers(mask_sel: int) -> bool:
        cov = 0
        i = 0
        m = mask_sel
        while m:
            if m & 1:
                cov |= closed[i]
            m >>= 1
            i += 1
        return cov == full

    for k in range(1, max_k + 1):
        # iterate combinations of k bits
        if k == 0:
            if full == 0:
                return 0, []
            continue
        # simple recursive combination
        chosen = []

        def rec(start: int, left: int, sel: int):
            if left == 0:
                return covers(sel)
            for i in range(start, n - left + 1):
                if rec(i + 1, left - 1, sel | (1 << i)):
                    chosen.append(sel | (1 << i))
                    return True
            return False

        if rec(0, k, 0):
            sel = chosen[-1]
            dom = [vs[i] for i in range(n) if (sel >> i) & 1]
            return k, dom
    return None, None


def cycle_space_dim(nverts: int, edges: list[tuple[int, int]], vertices: list[int]) -> int:
    """dim = E - V + C on induced subgraph."""
    vs = set(vertices)
    e2 = [(a, b) for a, b in edges if a in vs and b in vs]
    adj = {v: set() for v in vs}
    for a, b in e2:
        adj[a].add(b)
        adj[b].add(a)
    seen = set()
    c = 0
    for s in vs:
        if s in seen:
            continue
        c += 1
        q = deque([s])
        seen.add(s)
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
    return len(e2) - len(vs) + c


def all_short_cycles(edges: list[tuple[int, int]], vertices: list[int], max_len: int = 4):
    """All simple cycles of length <= max_len as frozenset of edge-ids."""
    vs = set(vertices)
    adj = defaultdict(set)
    for a, b in edges:
        if a in vs and b in vs:
            adj[a].add(b)
            adj[b].add(a)
    # edge id map
    eids = {}
    for i, (a, b) in enumerate(edges):
        if a in vs and b in vs:
            eids[frozenset((a, b))] = i
    cycles = []  # list of bitmask of edge ids
    # enumerate via DFS paths
    verts = sorted(vs)

    def dfs(start, path):
        if len(path) >= 3:
            if start in adj[path[-1]]:
                # close if length in [3, max_len]
                if 3 <= len(path) <= max_len:
                    mask = 0
                    seq = path + [start]
                    for i in range(len(seq) - 1):
                        mask |= 1 << eids[frozenset((seq[i], seq[i + 1]))]
                    cycles.append(mask)
        if len(path) >= max_len:
            return
        for w in adj[path[-1]]:
            if w in path:
                continue
            if w < start:
                continue  # canonical: smallest vertex is start
            dfs(start, path + [w])

    for s in verts:
        dfs(s, [s])
    # unique
    return list(set(cycles))


def gf2_span_dim(masks: list[int]) -> int:
    basis = []
    for m in masks:
        x = m
        for b in basis:
            x = min(x, x ^ b)
        if x:
            basis.append(x)
            basis.sort(reverse=True)
    return len(basis)


def automorphisms(nverts: int, adj: dict[int, set[int]], vertices: list[int], max_count: int = 200):
    """Enumerate automorphisms of induced subgraph (small graphs only)."""
    vs = sorted(vertices)
    n = len(vs)
    idx = {v: i for i, v in enumerate(vs)}
    deg = [len(adj[vs[i]] & set(vs)) for i in range(n)]
    nbrs = [set(idx[w] for w in adj[vs[i]] if w in idx) for i in range(n)]

    auts = []
    img = [-1] * n
    used = [False] * n

    def rec(k):
        if len(auts) >= max_count:
            return
        if k == n:
            auts.append(tuple(img))
            return
        # order vertices by degree (most constrained first) — fixed order is fine for n<=16
        for j in range(n):
            if used[j]:
                continue
            if deg[j] != deg[k]:
                continue
            # check edges to already-assigned
            ok = True
            for t in range(k):
                edge_in = (idx[vs[k]] in nbrs[t] or True)
                # adjacency of k-t
                ak = (t in nbrs[k])
                aj = (img[t] in nbrs[j])
                if ak != aj:
                    ok = False
                    break
            if not ok:
                continue
            img[k] = j
            used[j] = True
            rec(k + 1)
            used[j] = False
            img[k] = -1

    rec(0)
    return auts, vs


def d4_pairs_orbits(n: int, edges: list[tuple[int, int]]):
    """Apply D4 to edge set, return number of D4-orbits of edges."""

    def maps(n):
        return [
            lambda x, y: (x, y),
            lambda x, y: (y, n - 1 - x),
            lambda x, y: (n - 1 - x, n - 1 - y),
            lambda x, y: (n - 1 - y, x),
            lambda x, y: (n - 1 - x, y),
            lambda x, y: (x, n - 1 - y),
            lambda x, y: (y, x),
            lambda x, y: (n - 1 - y, n - 1 - x),
        ]

    def pt(x, y):
        return y * n + x

    def inv(i):
        return i % n, i // n

    remaining = set(tuple(sorted(e)) for e in edges)
    orbits = []
    while remaining:
        e = remaining.pop()
        orb = {e}
        for f in maps(n):
            a = inv(e[0])
            b = inv(e[1])
            e2 = tuple(sorted((pt(*f(*a)), pt(*f(*b)))))
            orb.add(e2)
        remaining -= orb
        orbits.append(sorted(orb))
    return orbits


def build_j(board: Board, grundy: dict[int, int] | None = None):
    """Return (edges, one_stone_g, two_stone_g_sample)."""
    if grundy is None:
        grundy = board.solve_grundy()
    one = {v: grundy.get(1 << v, None) for v in range(board.V)}
    edges = []
    two_g = {}
    for a, b in combinations(range(board.V), 2):
        mask = (1 << a) | (1 << b)
        g = grundy.get(mask)
        two_g[(a, b)] = g
        if g == 0:
            edges.append((a, b))
    return edges, one, two_g, grundy


def main():
    report = {}
    boards = {}

    # ---- compute / load J_n for n=3,4,5 ----
    for n in (3, 4, 5):
        print(f"=== n={n} solve grundy ===", flush=True)
        b = board_square(n)
        g = b.solve_grundy()
        edges, one, two_g, _ = build_j(b, g)
        boards[n] = dict(board=b, edges=edges, one=one, two_g=two_g, grundy=g)
        W = [v for v in range(n * n) if one[v] == 0]
        print(f"n={n} |E|={len(edges)} |W|={len(W)} empty_g={g[0]}", flush=True)

        # verify against known n=5 loss pairs
        if n == 5:
            known = json.loads(
                (ROOT / "night-research/cycle4-n5-two-stone-loss.json").read_text(encoding="utf-8")
            )
            known_ids = set(tuple(sorted(p["ids"])) for p in json.loads(
                (ROOT / "night-research/cycle4-n5-two-stone-geometry.json").read_text(encoding="utf-8")
            )["loss_pairs"])
            computed = set(tuple(sorted(e)) for e in edges)
            report["n5_verify_loss_pairs"] = {
                "computed": len(computed),
                "known": len(known_ids),
                "equal": computed == known_ids,
                "only_computed": list(computed - known_ids)[:5],
                "only_known": list(known_ids - computed)[:5],
            }

        # one-stone g hist
        hist = defaultdict(int)
        for v, gv in one.items():
            hist[gv] += 1
        report[f"n{n}_one_stone_g"] = dict(sorted(hist.items(), key=lambda x: (x[0] is None, x[0])))

    # ---- J_5 detailed (B011-B015, B017, B020) ----
    b5 = boards[5]["board"]
    edges5 = boards[5]["edges"]
    one5 = boards[5]["one"]
    V5 = 25
    adj5 = neighbors_of_edges(V5, edges5)
    losing = [v for v in range(V5) if one5[v] != 0]  # non-isolated candidates
    winning = [v for v in range(V5) if one5[v] == 0]
    noniso = [v for v in range(V5) if adj5[v]]
    report["j5_summary"] = {
        "vertices": V5,
        "edges": len(edges5),
        "winning_first_isolated": len(winning),
        "nonisolated": len(noniso),
        "edges_among_noniso": sum(1 for a, b in edges5 if a in noniso and b in noniso),
        "any_edge_touching_isolated": any(one5[a] == 0 or one5[b] == 0 for a, b in edges5),
    }

    # B011 connectivity of non-isolated part
    sub_adj = {v: set(w for w in adj5[v] if w in noniso) for v in noniso}
    comps = components(V5, {**{v: set() for v in range(V5) if v not in noniso}, **sub_adj})
    comps_nontrivial = [c for c in comps if len(c) > 1]
    report["b011_connected"] = {
        "nonisolated": len(noniso),
        "components_on_noniso": [len(c) for c in comps_nontrivial],
        "isolated_not_counted": len(winning),
        "connected": len(comps_nontrivial) == 1 and len(comps_nontrivial[0]) == len(noniso),
        "component_vertices": comps_nontrivial,
    }

    # B014 bipartite
    bip, colors, oddcyc = is_bipartite(V5, sub_adj)
    report["b014_bipartite"] = {
        "bipartite": bip,
        "odd_cycle_witness": oddcyc,
    }

    # B012 cycle space vs short cycles
    cd = cycle_space_dim(V5, edges5, noniso)
    short = all_short_cycles(edges5, noniso, max_len=4)
    span = gf2_span_dim(short)
    # also compute fundamental cycles
    report["b012_cycle_space"] = {
        "cycle_space_dim": cd,
        "num_simple_cycles_len_le_4": len(short),
        "span_dim_of_len_le_4": span,
        "generated_by_len_le_4": span == cd,
    }

    # B013 automorphisms vs D4
    auts, vs = automorphisms(V5, sub_adj, noniso, max_count=500)
    d4_orb = d4_pairs_orbits(5, edges5)
    # D4 acts on the 16 nonisolated; count distinct perms induced
    report["b013_aut"] = {
        "num_automorphisms_noniso": len(auts),
        "vertices_order": vs,
        "d4_edge_orbits": len(d4_orb),
        "d4_edge_orbit_sizes": [len(o) for o in d4_orb],
        "beyond_d4": len(auts) > 8,
    }

    # B015 perfect matching
    pms = perfect_matchings(V5, sub_adj, noniso, limit=3)
    report["b015_perfect_matching"] = {
        "exists": len(pms) > 0,
        "num_found_capped": len(pms),
        "example": pms[0] if pms else None,
    }

    # B017: common neighbors of pair endpoints (geometric danger completions)
    # C(p) = other board points sharing a forbidden 4-set with p
    b = b5
    C = [set() for _ in range(V5)]
    for q in b.quads:
        pts = [i for i in range(V5) if (q >> i) & 1]
        for i in pts:
            for j in pts:
                if i != j:
                    C[i].add(j)
    def overlap(p, q):
        return len(C[p] & C[q])

    p_over = [overlap(a, b_) for a, b_ in edges5]
    # baseline: all pairs among noniso
    all_over = [overlap(a, b_) for a, b_ in combinations(noniso, 2)]
    nonP_over = [overlap(a, b_) for a, b_ in combinations(noniso, 2) if (a, b_) not in set(tuple(sorted(e)) for e in edges5)]
    import statistics as stats
    report["b017_common_neighbors"] = {
        "P_pair_overlap_mean": round(sum(p_over) / len(p_over), 3),
        "P_pair_overlap_values": sorted(p_over),
        "nonP_pair_overlap_mean": round(sum(nonP_over) / len(nonP_over), 3) if nonP_over else None,
        "all_pair_overlap_mean": round(sum(all_over) / len(all_over), 3),
        "P_pair_deg_C_mean": round(sum(len(C[a]) + len(C[b]) for a, b in edges5) / (2 * len(edges5)), 3),
    }

    # B020: classify the 20 pairs by (dx,dy, boundary flags)
    def coords(i, n=5):
        return i % n, i // n

    fam = defaultdict(list)
    for a, b_ in edges5:
        xa, ya = coords(a)
        xb, yb = coords(b_)
        dx, dy = abs(xa - xb), abs(ya - yb)
        a_corner = (xa in (0, 4) and ya in (0, 4))
        b_corner = (xb in (0, 4) and yb in (0, 4))
        same_row = ya == yb
        same_col = xa == xb
        on_bnd = lambda x, y: x in (0, 4) or y in (0, 4)  # noqa: E731
        if a_corner and b_corner and (same_row or same_col):
            key = "corner-corner side (distance 4 axis-aligned)"
        elif a_corner != b_corner and (same_row or same_col):
            key = "corner-boundary-dist3 (axis distance 3)"
        elif {dx, dy} == {1, 3}:
            key = "knight (1,3) among odd-sum losing cells"
        else:
            key = f"OTHER dx={dx} dy={dy} corner={a_corner,b_corner}"
        fam[key].append((a, b_, dx, dy))

    # counterexamples to pure-distance rule among losing cells
    losing = noniso
    pure_dist = set()
    for a, b_ in combinations(losing, 2):
        xa, ya = coords(a)
        xb, yb = coords(b_)
        cheb = max(abs(xa - xb), abs(ya - yb))
        if cheb >= 3:
            pure_dist.add((a, b_))
    edge_set = set(tuple(sorted(e)) for e in edges5)
    report["b020_pair_families"] = {
        "families": {k: len(v) for k, v in fam.items()},
        "family_members": {k: v for k, v in fam.items()},
        "pure_chebyshev_ge3_count": len(pure_dist),
        "pure_chebyshev_extra_not_P": [list(t) for t in sorted(pure_dist - edge_set)[:12]],
        "P_not_in_chebyshev_ge3": [list(t) for t in sorted(edge_set - pure_dist)],
    }

    # ---- J_4 (B016, B019) ----
    n = 4
    edges4 = boards[n]["edges"]
    one4 = boards[n]["one"]
    adj4 = neighbors_of_edges(16, edges4)
    allv = list(range(16))
    comps4 = components(16, adj4)
    report["b016_j4"] = {
        "edges": len(edges4),
        "components": [len(c) for c in comps4],
        "connected": len(comps4) == 1,
        "degrees": sorted((len(adj4[v]) for v in allv)),
    }
    dom_k, dom_set = domination_number(16, adj4, allv, max_k=8)
    report["b019_dom_n4"] = {
        "n2": 16,
        "domination_number": dom_k,
        "dominating_set": dom_set,
        "ratio_to_n2": (dom_k / 16) if dom_k else None,
    }

    # J_5 domination on nonisolated (informational; n=5 is F-win)
    dom5, set5 = domination_number(25, sub_adj, noniso, max_k=10)
    report["b019_dom_j5_noniso"] = {
        "nverts": len(noniso),
        "domination_number": dom5,
        "set": set5,
        "note": "n=5 is F-win; B019 claims S-win boards, so this is informational",
    }

    # ---- B001-B006 table from existing data ----
    report["empty_and_W_table"] = {
        "source": "cycle4-density-table.json + README + cycle5-grundy + 10x10-first-move-classification",
        "n": list(range(1, 11)),
        "winner": ["F", "F", "F", "S", "F", "F", "S", "S", "F", "S"],
        "W_size": [1, 4, 9, 0, 9, 36, 0, 0, 81, 0],
        "partial_only_n5": True,
        "empty_g_known": {1: 1, 2: 1, 3: 1, 4: 0, 5: 1, 6: 1, 7: 0, 8: 0, 9: ">0 unknown", 10: 0},
        "one_stone_nonzero_g": {
            2: [0],
            3: [0],
            4: [1],
            5: [3],
            6: [0],
        },
    }

    # B006 check across computed boards
    odd_ok = True
    nonzero = []
    for n in (3, 4, 5):
        for v, gv in boards[n]["one"].items():
            if gv and gv != 0:
                nonzero.append((n, v, gv))
                if gv % 2 == 0:
                    odd_ok = False
    report["b006_one_stone_nonzero_all_odd"] = {
        "nonzero_values": sorted(set(g for _, _, g in nonzero)),
        "all_odd": odd_ok,
        "range": "n=2..5 computed exact",
    }

    out_path = OUT / "batch01_jgraph.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", out_path)
    # brief print
    for k in ["b011_connected", "b012_cycle_space", "b013_aut", "b014_bipartite", "b015_perfect_matching", "b016_j4", "b019_dom_n4", "b020_pair_families", "n5_verify_loss_pairs"]:
        print("----", k)
        print(json.dumps(report.get(k), indent=2, ensure_ascii=False, default=str)[:1500])


if __name__ == "__main__":
    main()
