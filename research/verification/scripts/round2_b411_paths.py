#!/usr/bin/env python3
"""Round2 B411-B420: internal structure of the 14-op / 8-path A-B shortest corridors.

Uses the existing 903-state G_12 component
(results/discovery_full_board_forbid_-1.json). No re-enumeration of n>=7.
Integer bitmasks only.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
sys.path.insert(0, str(ROOT / "research/verification/scripts"))
from kyouen_core import Board, square_points  # noqa: E402

RES = ROOT / "results"
OUT = ROOT / "research/verification/round2_b411.json"

N = 7
CENTER = 24  # (3,3)
CORNER = 48  # (6,6)


def popcount(x: int) -> int:
    return bin(x).count("1")


def bits(x: int) -> list[int]:
    return [i for i in range(49) if (x >> i) & 1]


def load_component():
    d = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    closed = d["closed_set"]
    A, B = d["reachable_14_sets"]
    return closed, A, B


def build_adj(closed: list[int]):
    cset = set(closed)
    adj = defaultdict(list)
    for s in closed:
        for i in range(49):
            t = s ^ (1 << i)
            if t in cset:
                adj[s].append(t)
    return adj


def ops_along(path: list[int]) -> list[tuple[str, int]]:
    """Return add/remove events between consecutive states."""
    ev = []
    for a, b in zip(path, path[1:]):
        diff = a ^ b
        assert bin(diff).count("1") == 1
        i = diff.bit_length() - 1
        if (b >> i) & 1:
            ev.append(("+", i))
        else:
            ev.append(("-", i))
    return ev


def all_shortest_paths(adj, src, dst):
    """BFS layers + DAG DP counting + DFS enumeration of ALL shortest paths."""
    dist = {src: 0}
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    if dst not in dist:
        return dist, []
    L = dist[dst]
    # DP count of shortest paths
    cnt = defaultdict(int)
    cnt[src] = 1
    for u in sorted(dist, key=lambda x: dist[x]):
        for v in adj[u]:
            if dist.get(v) == dist[u] + 1:
                cnt[v] += cnt[u]
    # DFS enumerate
    paths = []

    def dfs(u, acc):
        if u == dst:
            paths.append(list(acc))
            return
        for v in adj[u]:
            if dist.get(v) == dist[u] + 1 and cnt[v] > 0:
                acc.append(v)
                dfs(v, acc)
                acc.pop()

    dfs(src, [src])
    return dist, paths


def det4_rows(pts):
    from kyouen_core import det4

    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    return det4(*rows)


def main():
    board = Board(square_points(N), "n7")
    closed, A, B = load_component()
    adj = build_adj(closed)
    dist, paths = all_shortest_paths(adj, A, B)

    A_set, B_set = set(bits(A)), set(bits(B))
    inter = A_set & B_set
    onlyA = A_set - B_set
    onlyB = B_set - A_set
    union = A_set | B_set

    path_ops = [ops_along(p) for p in paths]
    path_cells_used = [set(i for _, i in ev) for ev in path_ops]
    aux_cells = sorted(set().union(*path_cells_used) - union)

    out = {}
    out["basic"] = {
        "n_states": len(closed),
        "layers": dict(Counter(popcount(s) for s in closed)),
        "distance": dist[B],
        "n_shortest_paths": len(paths),
        "A": sorted(A_set),
        "B": sorted(B_set),
        "A_intersect_B": sorted(inter),
        "only_A": sorted(onlyA),
        "only_B": sorted(onlyB),
        "union_size": len(union),
        "aux_cells_on_paths": aux_cells,
    }

    # ---- B413 / B414: temporary removal of common stones + corner in/out ----
    path_tmp_common = []
    path_corner_window = []
    path_event_multiset = []
    for ev in path_ops:
        removed_then_added = []
        for i in inter:
            # appears as '-' then later '+'
            seq = [op for op, c in ev if c == i]
            if seq == ["-", "+"] or ("-" in seq and "+" in seq and seq.index("-") < seq.index("+")):
                removed_then_added.append(i)
        # any cell that is removed then added
        tmp_any = []
        for i in set(c for _, c in ev):
            seq = [op for op, c in ev if c == i]
            if "-" in seq and "+" in seq and seq.index("-") < seq.index("+"):
                tmp_any.append(i)
        path_tmp_common.append(sorted(removed_then_added))
        # corner window: index of +48 and -48
        cw = None
        if CORNER in path_cells_used[path_ops.index(ev)]:
            ops_idx = [(k, op, c) for k, (op, c) in enumerate(ev) if c == CORNER]
            if len(ops_idx) == 2:
                k0, op0, _ = ops_idx[0]
                k1, op1, _ = ops_idx[1]
                cw = {
                    "add_at": k0 if op0 == "+" else k1,
                    "del_at": k1 if op1 == "-" else k0,
                    "window_ops": abs(k1 - k0),
                    "internal_ops": abs(k1 - k0) - 1,
                    "size_seq": [popcount(p) for p in paths[path_ops.index(ev)]],
                }
        path_corner_window.append(cw)
        path_event_multiset.append(tuple(sorted(ev)))

    out["B413_B414"] = {
        "tmp_common_per_path": path_tmp_common,
        "all_exactly_one_common": all(len(x) == 1 for x in path_tmp_common),
        "distinct_tmp_common": sorted({tuple(x) for x in path_tmp_common}),
        "same_tmp_common_all_paths": len({tuple(x) for x in path_tmp_common}) == 1,
        "tmp_any_per_path": None,  # filled below
    }
    # tmp_any
    tmp_any_all = []
    for ev in path_ops:
        tmp_any = []
        for i in set(c for _, c in ev):
            seq = [op for op, c in ev if c == i]
            if "-" in seq and "+" in seq and seq.index("-") < seq.index("+"):
                tmp_any.append(i)
        tmp_any_all.append(sorted(tmp_any))
    out["B413_B414"]["tmp_any_per_path"] = tmp_any_all

    out["B415"] = {
        "corner_windows": path_corner_window,
        "all_have_corner": all(cw is not None for cw in path_corner_window),
        "add_at_set": sorted({cw["add_at"] for cw in path_corner_window if cw}),
        "del_at_set": sorted({cw["del_at"] for cw in path_corner_window if cw}),
        "window_ops_set": sorted({cw["window_ops"] for cw in path_corner_window if cw}),
        "internal_ops_set": sorted({cw["internal_ops"] for cw in path_corner_window if cw}),
        "identical_window": len({(cw["add_at"], cw["del_at"], cw["window_ops"], cw["internal_ops"]) for cw in path_corner_window if cw})
        == 1,
    }

    # ---- B411: adjacency-transposition graph on the 8 paths ----
    # two paths are adjacent if their event sequences differ by swapping
    # exactly one pair of adjacent independent operations.
    def seq_of(ev):
        return list(ev)

    def independent(e1, e2):
        # different cells, and not add-then-remove of same / remove-then-add of same
        if e1[1] == e2[1]:
            return False
        return True

    def swap_adjacent(seq, k):
        # swap positions k, k+1 if independent and resulting states stay safe
        # (we only compare event sequences first; legality checked via path set)
        s = list(seq)
        if not independent(s[k], s[k + 1]):
            return None
        s[k], s[k + 1] = s[k + 1], s[k]
        return tuple(s)

    path_index = {tuple(ev): i for i, ev in enumerate(path_ops)}
    # also map by state-sequence
    g8 = defaultdict(set)
    for i, ev in enumerate(path_ops):
        for k in range(len(ev) - 1):
            sw = swap_adjacent(ev, k)
            if sw is not None and sw in path_index:
                j = path_index[sw]
                g8[i].add(j)
                g8[j].add(i)
    g8_edges = sorted({tuple(sorted((i, j))) for i in g8 for j in g8[i]})
    # degrees
    deg8 = {i: len(g8[i]) for i in range(len(path_ops))}
    # is it a 3-cube? 8 vertices, 12 edges, all deg 3
    out["B411"] = {
        "n_paths": len(path_ops),
        "edges": g8_edges,
        "n_edges": len(g8_edges),
        "degrees": deg8,
        "is_3cube_skeleton": len(path_ops) == 8
        and len(g8_edges) == 12
        and all(deg8[i] == 3 for i in range(8)),
    }

    # ---- B412: common partial order of 14 events ----
    # events labeled by (op, cell). Check all paths are linear extensions of
    # one poset: intersection of all pairwise orderings that appear in ALL paths.
    # First, do all paths use the same multiset of events?
    same_multiset = len(set(path_event_multiset)) == 1
    # Build union poset: (e1 < e2) if e1 precedes e2 in EVERY path
    # Use event identity (op,cell); note same event appears once per path.
    events = path_ops[0]
    if same_multiset:
        event_ids = events  # 14 tuples
        order_pairs = set()
        first = True
        for ev in path_ops:
            pos = {e: k for k, e in enumerate(ev)}
            pairs = set()
            for a, b in combinations(event_ids, 2):
                if pos[a] < pos[b]:
                    pairs.add((a, b))
                else:
                    pairs.add((b, a))
            order_pairs = pairs if first else (order_pairs & pairs)
            first = False
        # check linear extension: every path's total order extends order_pairs
        all_linear = True
        for ev in path_ops:
            pos = {e: k for k, e in enumerate(ev)}
            for a, b in order_pairs:
                if pos[a] > pos[b]:
                    all_linear = False
        # transitive closure size
        # represent events as indices
        idx = {e: i for i, e in enumerate(event_ids)}
        rel = {(idx[a], idx[b]) for a, b in order_pairs}
        # transitive closure
        changed = True
        while changed:
            changed = False
            add = set()
            for a, b in rel:
                for c, d in rel:
                    if b == c and (a, d) not in rel:
                        add.add((a, d))
            if add:
                rel |= add
                changed = True
        out["B412"] = {
            "same_event_multiset": True,
            "n_events": len(event_ids),
            "n_common_order_pairs": len(order_pairs),
            "n_transitive_closure": len(rel),
            "all_paths_are_linear_extensions": all_linear,
            "poset_is_total": len(rel) == len(event_ids) * (len(event_ids) - 1) // 2,
            "incomparable_pairs": len(event_ids) * (len(event_ids) - 1) // 2 - len(rel),
            "events": [[op, c] for op, c in event_ids],
        }
    else:
        out["B412"] = {"same_event_multiset": False, "multisets": [list(map(list, m)) for m in set(path_event_multiset)]}

    # ---- B416: structure of the 21-vertex shortest-path graph ----
    on_path = set()
    for p in paths:
        on_path |= set(p)
    # induced subgraph
    ind = {u: [v for v in adj[u] if v in on_path] for u in on_path}
    # find diamonds: 4-cycles a-b-c-d-a where the two middle vertices have
    # two common neighbors (a and c)
    # simpler: count undirected edges, components, and 4-cycles
    edges_ind = set()
    for u in on_path:
        for v in ind[u]:
            edges_ind.add(tuple(sorted((u, v))))
    # connected components of induced subgraph
    seen = set()
    comps = []
    for u in on_path:
        if u in seen:
            continue
        q = deque([u])
        seen.add(u)
        comp = []
        while q:
            x = q.popleft()
            comp.append(x)
            for y in ind[x]:
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        comps.append(sorted(comp))
    # diamond = two vertices with exactly 2 common neighbors, or 4-cycle count
    n4cycles = 0
    diamonds = []
    for a, b in combinations(sorted(on_path), 2):
        na, nb = set(ind[a]), set(ind[b])
        common = na & nb
        if len(common) >= 2:
            for u, v in combinations(sorted(common), 2):
                n4cycles += 1
                diamonds.append((a, b, u, v))
    # branching vertices: degree >= 3 in induced graph
    branch = [u for u in on_path if len(ind[u]) >= 3]
    # do branches differ only by order of two independent ops?
    # For each path, record the set of branch-adjacent decision points
    out["B416"] = {
        "n_vertices_on_shortest": len(on_path),
        "n_edges_induced": len(edges_ind),
        "components": [len(c) for c in comps],
        "degree_hist_induced": dict(Counter(len(ind[u]) for u in on_path)),
        "n_4cycles_as_common2": n4cycles,
        "diamonds_count": len(diamonds),
        "branch_vertices_deg_ge3": len(branch),
        "layer_of_vertices": dict(Counter(popcount(u) for u in on_path)),
    }

    # ---- B417: shortest detour using a point outside union∪{48} ----
    # BFS on full component with cost; find shortest A-B path whose used cells
    # include some cell not in union∪{48}.
    allowed_aux = set(range(49)) - union - {CORNER}
    # BFS tracking whether aux used: state = (node, used_aux_flag)
    # distance
    start = (A, 0)
    dq = deque([start])
    d2 = {start: 0}
    parent = {start: None}
    found = None
    while dq:
        u, used = dq.popleft()
        if u == B and used:
            found = (u, used)
            break
        for v in adj[u]:
            nused = used
            diff = u ^ v
            i = diff.bit_length() - 1
            if i in allowed_aux:
                nused = 1
            st = (v, nused)
            if st not in d2:
                d2[st] = d2[(u, used)] + 1
                parent[st] = (u, used)
                dq.append(st)
    detour_len = None
    detour_cells = None
    if found is not None:
        detour_len = d2[found]
        # reconstruct
        seq = []
        cur = found
        while cur is not None:
            seq.append(cur[0])
            cur = parent[cur]
        seq = seq[::-1]
        detour_cells = sorted({i for p in seq for i in bits(p)} - union)
    # also: shortest path that uses ONLY union∪{48} is 14 (known).
    # shortest path using any cell outside union (including 48) is still 14.
    # shortest path using cell outside union∪{48}:
    out["B417"] = {
        "auxiliary_non_corner_exists_at_len": detour_len,
        "excess_vs_14": (detour_len - 14) if detour_len else None,
        "aux_cells_on_detour": detour_cells,
    }

    # ---- B418: paths using the corner more than once ----
    # On the component, count shortest paths that touch 48 k times (add/del pairs).
    # General: BFS A->B with constraint on number of 48-presence windows.
    # Presence windows = number of maximal intervals where 48 is occupied.
    # Equivalently: number of (+48) events.
    def n_corner_enters(path_states):
        n = 0
        prev = 0
        for s in path_states:
            cur = (s >> CORNER) & 1
            if cur == 1 and prev == 0:
                n += 1
            prev = cur
        return n

    enters_dist = {}
    # BFS with state (node, enters, has48)
    st0 = (A, n_corner_enters([A]), (A >> CORNER) & 1)
    dq = deque([st0])
    dd = {st0: 0}
    while dq:
        u, e, has = dq.popleft()
        for v in adj[u]:
            nh = (v >> CORNER) & 1
            ne = e + (1 if nh == 1 and has == 0 else 0)
            st = (v, ne, nh)
            if st not in dd and ne <= 4:
                dd[st] = dd[(u, e, has)] + 1
                dq.append(st)
    # min distance to B with each enters count
    min_by_enters = {}
    for (u, e, has), dval in dd.items():
        if u == B:
            if e not in min_by_enters or dval < min_by_enters[e]:
                min_by_enters[e] = dval
    out["B418"] = {
        "min_len_by_corner_enters": {str(k): v for k, v in sorted(min_by_enters.items())},
        "enter_1_len": min_by_enters.get(1),
        "enter_2_len": min_by_enters.get(2),
        "enter_0_len": min_by_enters.get(0),
        "excess_enter2_vs_enter1": (min_by_enters.get(2) - min_by_enters.get(1))
        if (2 in min_by_enters and 1 in min_by_enters)
        else None,
    }

    # ---- B419: non-swappable op pairs and their forbidden-quad causes ----
    # For each pair of paths, find adjacent swaps that are NOT legal (cannot
    # swap because intermediate state is unsafe). Collect the blocking quad.
    board_quads = board.quads
    # map each quad to the 4 cells
    quad_cells = [bits(q) for q in board_quads]

    def state_after_prefix(ev, k, cells0):
        s = set(cells0)
        for op, c in ev[:k]:
            if op == "+":
                s.add(c)
            else:
                s.discard(c)
        return s

    blocking = []  # (path_i, k, e1, e2, blocking_quad_cells)
    for i, ev in enumerate(path_ops):
        cells0 = A_set if True else None
        # states along path
        states = [set(bits(p)) for p in paths[i]]
        for k in range(len(ev) - 1):
            e1, e2 = ev[k], ev[k + 1]
            if e1[1] == e2[1]:
                continue  # same cell, not a transposition candidate
            # try swap: apply e2 then e1 from states[k]
            s = set(states[k])
            # apply e2
            if e2[0] == "+":
                s.add(e2[1])
            else:
                s.discard(e2[1])
            mid_ok = board.is_safe(sum(1 << x for x in s)) if False else True
            # check safety via quads
            mask = 0
            for x in s:
                mask |= 1 << x
            safe_mid = True
            blocking_quad = None
            for q, cells in zip(board_quads, quad_cells):
                if all((mask >> c) & 1 for c in cells):
                    safe_mid = False
                    blocking_quad = cells
                    break
            if not safe_mid:
                blocking.append(
                    {
                        "path": i,
                        "k": k,
                        "e1": list(e1),
                        "e2": list(e2),
                        "blocking_quad": blocking_quad,
                    }
                )
    # classify blocking quads by D4 geometry type: sorted edge-length^2 multiset
    def d4_type(cells):
        pts = [(c % 7, c // 7) for c in cells]
        # side length^2 multiset of the 4-cycle in sorted order (poor man's)
        # better: sorted pairwise squared distances
        ds = []
        for a, b in combinations(pts, 2):
            ds.append((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
        return tuple(sorted(ds))

    type_hist = Counter()
    for b in blocking:
        type_hist[d4_type(b["blocking_quad"])] += 1
    out["B419"] = {
        "n_illegal_swaps": len(blocking),
        "distinct_blocking_quads": sorted({tuple(b["blocking_quad"]) for b in blocking}),
        "n_distinct_blocking_quads": len({tuple(b["blocking_quad"]) for b in blocking}),
        "d4_type_hist": {str(k): v for k, v in type_hist.items()},
        "n_d4_types": len(type_hist),
        "examples": blocking[:6],
    }

    # ---- B420: A->B vs B->A prep before first corner use ----
    # min ops before first time 48 becomes occupied, starting from A and from B.
    def min_ops_before_corner(src):
        # BFS until first state with 48 occupied (or including src)
        if (src >> CORNER) & 1:
            return 0
        dq = deque([src])
        dd = {src: 0}
        while dq:
            u = dq.popleft()
            for v in adj[u]:
                if v not in dd:
                    dd[v] = dd[u] + 1
                    if (v >> CORNER) & 1:
                        return dd[v]
                    dq.append(v)
        return None

    prep_A = min_ops_before_corner(A)
    prep_B = min_ops_before_corner(B)
    # also: min ops before first corner use ON A SHORTEST PATH
    prep_A_sp = None
    prep_B_sp = None
    for p in paths:
        # forward A->B
        for k, s in enumerate(p):
            if (s >> CORNER) & 1:
                if prep_A_sp is None or k < prep_A_sp:
                    prep_A_sp = k
                break
        pr = p[::-1]
        for k, s in enumerate(pr):
            if (s >> CORNER) & 1:
                if prep_B_sp is None or k < prep_B_sp:
                    prep_B_sp = k
                break
    out["B420"] = {
        "min_ops_before_corner_from_A": prep_A,
        "min_ops_before_corner_from_B": prep_B,
        "asymmetric": prep_A != prep_B,
        "min_corner_appear_index_on_shortest_A2B": prep_A_sp,
        "min_corner_appear_index_on_shortest_B2A": prep_B_sp,
    }

    # ---- path event listings (for notes) ----
    out["paths"] = [
        {
            "i": i,
            "len": len(paths[i]) - 1,
            "states": paths[i],
            "ops": [[op, c] for op, c in path_ops[i]],
            "size_seq": [popcount(s) for s in paths[i]],
            "tmp_common": path_tmp_common[i],
            "corner_window": path_corner_window[i],
        }
        for i in range(len(paths))
    ]

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("wrote", OUT)
    print(json.dumps({k: out[k] for k in ["basic", "B411", "B412", "B413_B414", "B415", "B416", "B417", "B418", "B420"]}, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
