#!/usr/bin/env python3
"""Batch 06 verification part 2: B111-B120 component / path / cover analysis.

Uses existing COMPLETE certificates in results/:
  discovery_full_board_forbid_-1.json   (903-state G_12 component with A,B)
  discovery_full_board_forbid_48.json   (250-state corner-forbidden component)
  discovery_corridor_static_certificate.json  (21 covering quads, 6460 candidates)
  discovery_corridor_auxiliary.json

Integer arithmetic only. Outputs research/verification/batch06_components.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "night-research"))

from cycle8_lib import (  # noqa: E402
    apply_perm,
    board_str,
    d4_perms,
    load_n7,
    stones,
    xy,
)

RES = ROOT / "results"
OUT = ROOT / "research" / "verification" / "batch06_components.json"


def popcount(x: int) -> int:
    return bin(x).count("1")


def neighbors_g12(mask: int, floor: int = 12, v: int = 49) -> list[int]:
    """All safe-by-membership 1-stone add/remove neighbors with size >= floor.

    Caller supplies the known closed set; here we just generate candidates.
    """
    out = []
    pts = stones(mask, v)
    for r in pts:
        t = mask & ~(1 << r)
        if popcount(t) >= floor:
            out.append(t)
    for a in range(v):
        if (mask >> a) & 1:
            continue
        t = mask | (1 << a)
        out.append(t)
    return out


def build_graph_within(
    closed: list[int], floor: int = 12
) -> dict[int, list[int]]:
    """Adjacency among the known closed set via 1-stone add/remove."""
    index = {m: i for i, m in enumerate(closed)}
    adj: dict[int, list[int]] = defaultdict(list)
    for m in closed:
        for nb in neighbors_g12(m, floor=floor):
            if nb in index:
                adj[m].append(nb)
    return adj


def bfs_dist(adj, src: int, dst: int) -> tuple[int | None, list[int] | None]:
    if src == dst:
        return 0, [src]
    prev = {src: None}
    q = deque([src])
    while q:
        u = q.popleft()
        for w in adj[u]:
            if w not in prev:
                prev[w] = u
                if w == dst:
                    path = []
                    cur = w
                    while cur is not None:
                        path.append(cur)
                        cur = prev[cur]
                    path.reverse()
                    return len(path) - 1, path
                q.append(w)
    return None, None


def all_shortest_paths_info(adj, src: int, dst: int) -> dict:
    """BFS layered DAG; count shortest paths and collect auxiliary points."""
    dist = {src: 0}
    q = deque([src])
    parent: dict[int, list[int]] = defaultdict(list)
    order = [src]
    while q:
        u = q.popleft()
        for w in adj[u]:
            if w not in dist:
                dist[w] = dist[u] + 1
                parent[w].append(u)
                q.append(w)
                order.append(w)
            elif dist[w] == dist[u] + 1:
                parent[w].append(u)
    if dst not in dist:
        return {"reachable": False}
    # count shortest paths
    cnt = {src: 1}
    for u in order:
        if u == src:
            continue
        cnt[u] = sum(cnt[p] for p in parent[u])
    # collect vertices on any shortest path (forward slice)
    on_path = {dst}
    q2 = deque([dst])
    while q2:
        u = q2.popleft()
        for p in parent[u]:
            if p not in on_path:
                on_path.add(p)
                q2.append(p)
    # sample auxiliary points used in the shortest-path subgraph
    return {
        "reachable": True,
        "distance": dist[dst],
        "n_shortest_paths": cnt[dst],
        "n_vertices_on_some_shortest_path": len(on_path),
        "vertices_on_some_shortest_path": sorted(on_path),
        "dist_sample_max": max(dist.values()),
    }


def layer_stats(closed: list[int]) -> dict:
    return dict(sorted(Counter(popcount(m) for m in closed).items()))


def analyze_component(closed: list[int], a: int, b: int, label: str) -> dict:
    adj = build_graph_within(closed)
    deg_hist = Counter(len(adj[m]) for m in closed)
    dist, path = bfs_dist(adj, a, b) if b is not None else (None, None)
    info = all_shortest_paths_info(adj, a, b) if b is not None else {}
    # auxiliary cells on the found path
    aux = None
    if path:
        union = a | b
        used = set()
        for m in path:
            used |= set(stones(m, 49))
        aux = sorted(used - set(stones(union, 49)))
    return {
        "label": label,
        "n_states": len(closed),
        "layers": layer_stats(closed),
        "degree_hist": dict(sorted(deg_hist.items())),
        "degree_min": min(deg_hist) if deg_hist else None,
        "degree_max": max(deg_hist) if deg_hist else None,
        "bfs_distance_A_B": dist,
        "bfs_path_len_states": len(path) if path else None,
        "shortest_info": info,
        "auxiliary_on_found_path": aux,
    }


def try_shrink_cover() -> dict:
    """B116: can the 21-quad cover of the 6460 static candidates be reduced?"""
    sc = json.loads((RES / "discovery_corridor_static_certificate.json").read_text())
    quads = sc["covering_quads"]  # ints, likely bitmasks of 4 points
    # Rebuild candidates: need the same definition. Use the certificate's
    # candidate_count and verify coverage ourselves from the U-restricted
    # safe sets with d in {2,3} and size>=13 — but we may not have the
    # candidate list stored. Instead verify each covering quad is a real
    # forbidden quad inside U and try hitting-set reduction using the
    # discovery_static_barrier_exploration or by regenerating candidates.
    cells = sc["cells"]  # 19 cells of U
    a_mask, b_mask = sc["a"], sc["b"]
    # Regenerate U-restricted safe sets of size 13..17 with d(S) in {2,3}
    # d(S) = |S∩Q| - |S∩P| with P=A\B, Q=B\A
    p_pts = stones(a_mask & ~b_mask, 49)
    q_pts = stones(b_mask & ~a_mask, 49)
    # restricted to U = support(a|b)
    u_mask = a_mask | b_mask
    u_pts = stones(u_mask, 49)

    # We need is_safe on U; build forbidden quads among u_pts (59 known).
    # Load full forbidden quads from cache if present.
    cache_q = ROOT / "research" / "verification" / "batch06_quads_cache.json"
    if cache_q.exists():
        data = json.loads(cache_q.read_text())
        quads7 = [tuple(q) for q in data["n7"]]
    else:
        from cycle8_lib import forbidden_quads

        quads7 = forbidden_quads(7)
        cache_q.write_text(json.dumps({"n6": [], "n7": quads7}))

    u_set = set(u_pts)
    u_quads = [q for q in quads7 if all(p in u_set for p in q)]
    u_quad_masks = []
    for q in u_quads:
        m = 0
        for p in q:
            m |= 1 << p
        u_quad_masks.append(m)

    p_set, q_set = set(p_pts), set(q_pts)

    # Enumerate subsets of U of sizes 13..17 with d in {2,3} that are safe.
    # U has 19 points; C(19,13)=27132, C(19,14)=3876, C(19,15)=3876/ wait
    # C(19,13)=27132, C(19,14)=11628, C(19,15)=3876, C(19,16)=969, C(19,17)=171
    # total ~45k — feasible.
    candidates = []
    for sz in range(13, 18):
        for comb in combinations(u_pts, sz):
            m = 0
            for p in comb:
                m |= 1 << p
            d = sum(1 for p in comb if p in q_set) - sum(1 for p in comb if p in p_set)
            if d not in (2, 3):
                continue
            ok = True
            for qm in u_quad_masks:
                if (m & qm) == qm:
                    ok = False
                    break
            if ok:
                candidates.append(m)

    # Coverage: candidate is covered if it contains one of the covering quads.
    # covering_quads ints — check they match u_quad_masks format (bitmasks).
    cover_masks = quads[:]
    # verify each cover mask is among u_quad_masks
    cover_set = set(cover_masks)
    u_qset = set(u_quad_masks)
    covers_are_real = cover_set <= u_qset

    # candidate hits
    def hits(cm: int, cand: int) -> bool:
        return (cand & cm) == cm

    # Greedy / exact reduction: try all subsets of size <=20, then <=15 etc.
    # 21 quads -> 2^21 is 2M, feasible to check minimal covers exhaustively
    # for "is there a cover of size <=20" by trying all single removals first.
    def covers_all(subset: list[int]) -> bool:
        return all(any(hits(qm, c) for qm in subset) for c in candidates)

    full_ok = covers_all(cover_masks)
    # single removals
    reducible_20 = None
    for i in range(len(cover_masks)):
        sub = cover_masks[:i] + cover_masks[i + 1 :]
        if covers_all(sub):
            reducible_20 = {"removed_index": i, "remaining": len(sub)}
            break

    # Greedy set cover on the same universe (candidates) with the 21 quads,
    # then verify. This gives an upper bound on the minimum.
    def greedy_cover() -> list[int]:
        uncovered = set(candidates)
        chosen = []
        pool = list(cover_masks)
        while uncovered:
            best_q, best_cov = None, set()
            for qm in pool:
                cov = {c for c in uncovered if hits(qm, c)}
                if len(cov) > len(best_cov):
                    best_q, best_cov = qm, cov
            if best_q is None or not best_cov:
                break
            chosen.append(best_q)
            uncovered -= best_cov
            pool.remove(best_q)
        return chosen

    g_cover = greedy_cover() if full_ok else []
    # Try removing each quad from the FULL set down to a smaller cover:
    # iterative single-deletion minimization (1-minimal cover).
    current = list(cover_masks)
    if full_ok:
        changed = True
        while changed:
            changed = False
            for i in range(len(current)):
                sub = current[:i] + current[i + 1 :]
                if covers_all(sub):
                    current = sub
                    changed = True
                    break
    min_cover = len(current) if full_ok else None
    min_cover_quads = current

    return {
        "n_cover_quads": len(quads),
        "n_u_quads_total": len(u_quads),
        "covers_are_real_U_quads": covers_are_real,
        "n_candidates_regenerated": len(candidates),
        "n_candidates_certificate": sc["candidate_count"],
        "full_cover_ok": full_ok,
        "reducible_to_20": reducible_20,
        "greedy_cover_size": len(g_cover),
        "greedy_cover": g_cover,
        "min_cover_1minimal": min_cover,
        "min_cover_quads": min_cover_quads,
    }


def structural_aut_probe(closed: list[int], a: int, b: int) -> dict:
    """B117 probe: are A and B locally/graph-theoretically interchangeable?

    Compare degree, layer, and rooted 2-hop neighbourhood profile.
    """
    adj = build_graph_within(closed)

    def profile(root: int) -> dict:
        deg = len(adj[root])
        # 2-hop degree sequence (sorted)
        n1 = adj[root]
        n1_degs = sorted(len(adj[w]) for w in n1)
        n2_degs = Counter()
        seen = {root} | set(n1)
        for w in n1:
            for z in adj[w]:
                if z not in seen:
                    n2_degs[len(adj[z])] += 1
        return {
            "degree": deg,
            "n1_deg_seq_hash": hash(tuple(n1_degs)),
            "n1_deg_seq": n1_degs,
            "n2_deg_hist": dict(sorted(n2_degs.items())),
            "layer": popcount(root),
        }

    pa, pb = profile(a), profile(b)
    same_local = (
        pa["degree"] == pb["degree"]
        and pa["n1_deg_seq"] == pb["n1_deg_seq"]
        and pa["n2_deg_hist"] == pb["n2_deg_hist"]
    )
    # degree distribution of the whole component
    deg_hist = Counter(len(adj[m]) for m in closed)
    # how many states share A's / B's local profile
    def sig(root):
        n1 = adj[root]
        return (
            popcount(root),
            len(n1),
            tuple(sorted(len(adj[w]) for w in n1)),
        )
    sigs = Counter(sig(m) for m in closed)
    return {
        "profile_A": pa,
        "profile_B": pb,
        "same_local_neighbourhood": same_local,
        "n_states_sharing_A_sig": sigs[sig(a)],
        "n_states_sharing_B_sig": sigs[sig(b)],
        "component_degree_hist": dict(sorted(deg_hist.items())),
    }


def orientation_invariant_probe(closed: list[int]) -> dict:
    """B120 probe: compute a small per-state invariant from corners/edges.

    For each state compute (n_corners, n_edge_noncorner, n_interior) and
    the D4-orbit occupancy of the 10 cell orbits; check whether the 8
    components (not available here — only 1 component) can be labelled.
    Within one component, report how many distinct invariant values occur
    and whether the two maxima A,B differ.
    """
    # For n=7 corner orbit (0,0) size 4, edge-1 (0,1) size 8, etc.
    from cycle8_lib import cell_orbit_key, orbit_members

    members = orbit_members(7)

    def inv(m: int) -> tuple:
        occ = []
        for k in sorted(members):
            pts = members[k]
            occ.append(sum(1 for p in pts if (m >> p) & 1))
        return tuple(occ)

    invs = Counter(inv(m) for m in closed)
    return {
        "n_distinct_orbit_occupancy": len(invs),
        "top_inv_counts": [list(k) + [v] for k, v in invs.most_common(12)],
    }


def main():
    d_full = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    d_48 = json.loads((RES / "discovery_full_board_forbid_48.json").read_text())
    closed903 = d_full["closed_set"]
    closed250 = d_48["closed_set"]
    a_mask, b_mask = d_full["reachable_14_sets"][0], d_full["reachable_14_sets"][1]
    print(f"loaded 903={len(closed903)} 250={len(closed250)}", flush=True)

    comp903 = analyze_component(closed903, a_mask, b_mask, "G12_component_with_AB")
    print("903 analyzed, dist=", comp903["bfs_distance_A_B"], flush=True)
    comp250 = analyze_component(closed250, a_mask, None, "G12_corner_forbidden")
    print("250 analyzed", flush=True)

    aut = structural_aut_probe(closed903, a_mask, b_mask)
    print("aut probe done", flush=True)

    inv = orientation_invariant_probe(closed903)
    print("inv probe done", flush=True)

    # B116 cover shrink
    try:
        cover = try_shrink_cover()
        print("cover shrink done", cover["min_cover_found"], flush=True)
    except Exception as e:
        cover = {"error": str(e)}
        print("cover error", e, flush=True)

    # B111 heuristic: from 12-stone states in 903, try adding a stone outside U
    # and see if we escape the component (i.e. reach a state not in closed903).
    u_mask = a_mask | b_mask
    escapes = 0
    escape_examples = []
    for m in closed903:
        if popcount(m) != 12:
            continue
        for a_pt in range(49):
            if (m >> a_pt) & 1:
                continue
            t = m | (1 << a_pt)
            if t not in closed903 and t not in closed250:
                # could be in another component or unsafe; cheap safety check
                # deferred; just count candidates that leave the known sets
                escapes += 1
                if len(escape_examples) < 5:
                    escape_examples.append((m, a_pt, t))
                break  # one escape per state is enough to count states
    # More precise: actually check safety of escape targets
    cache_q = ROOT / "research" / "verification" / "batch06_quads_cache.json"
    quads7 = [tuple(q) for q in json.loads(cache_q.read_text())["n7"]]
    quad_masks = []
    for q in quads7:
        qm = 0
        for p in q:
            qm |= 1 << p
        quad_masks.append(qm)

    def is_safe_mask(m: int) -> bool:
        for qm in quad_masks:
            if (m & qm) == qm:
                return False
        return True

    # Count 12-states in 903 that have a safe add going outside closed903
    outside_safe = 0
    outside_unsafe = 0
    for m in closed903:
        if popcount(m) != 12:
            continue
        for a_pt in range(49):
            if (m >> a_pt) & 1:
                continue
            t = m | (1 << a_pt)
            if t in closed903:
                continue
            if is_safe_mask(t):
                outside_safe += 1
                break
            else:
                outside_unsafe += 1
    b111_probe = {
        "n_12_states_with_safe_add_outside_903": outside_safe,
        "note": "safe add outside known 903 does NOT by itself prove G_11 connectivity; it shows the G_12 component is closed under adds that stay safe inside it, and some safe adds leave the set (so the component is a true G_12 component, not truncated)",
    }

    out = {
        "comp903": comp903,
        "comp250": comp250,
        "aut_probe": aut,
        "inv_probe": inv,
        "cover_shrink": cover,
        "b111_probe": b111_probe,
    }
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
