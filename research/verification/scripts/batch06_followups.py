#!/usr/bin/env python3
"""Batch 06 follow-ups: B114 auxiliaries, B116 cover shrink, B112/B119 other components."""
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
    d4_perms,
    load_n7,
    stones,
    xy,
)

RES = ROOT / "results"
OUT = ROOT / "research" / "verification" / "batch06_followups.json"


def popcount(x: int) -> int:
    return bin(x).count("1")


def load_quads7() -> list[tuple[int, ...]]:
    cache_q = ROOT / "research" / "verification" / "batch06_quads_cache.json"
    if cache_q.exists():
        return [tuple(q) for q in json.loads(cache_q.read_text())["n7"]]
    from cycle8_lib import forbidden_quads

    q = forbidden_quads(7)
    cache_q.write_text(json.dumps({"n6": [], "n7": q}))
    return q


def quads_to_masks(quads):
    out = []
    for q in quads:
        m = 0
        for p in q:
            m |= 1 << p
        out.append(m)
    return out


def is_safe_mask(m: int, quad_masks: list[int]) -> bool:
    for qm in quad_masks:
        if (m & qm) == qm:
            return False
    return True


def neighbors_g12(mask: int, floor: int = 12, v: int = 49):
    pts = stones(mask, v)
    for r in pts:
        t = mask & ~(1 << r)
        if popcount(t) >= floor:
            yield t
    for a in range(v):
        if (mask >> a) & 1:
            continue
        yield mask | (1 << a)


def build_graph_within(closed: list[int], floor: int = 12):
    index = set(closed)
    adj = defaultdict(list)
    for m in closed:
        for nb in neighbors_g12(m, floor=floor):
            if nb in index:
                adj[m].append(nb)
    return adj


def enumerate_shortest_path_aux(closed, a, b):
    adj = build_graph_within(closed)
    dist = {a: 0}
    parent = defaultdict(list)
    q = deque([a])
    order = [a]
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
    assert b in dist
    # enumerate all shortest paths (there are few)
    union = a | b
    union_pts = set(stones(union, 49))
    paths = []

    def dfs(cur, path):
        if cur == a:
            paths.append(list(reversed(path)))
            return
        for p in parent[cur]:
            dfs(p, path + [p])

    dfs(b, [b])
    aux_sets = []
    for pth in paths:
        used = set()
        for m in pth:
            used |= set(stones(m, 49))
        aux_sets.append(sorted(used - union_pts))
    return {
        "n_shortest_paths": len(paths),
        "auxiliary_sets_per_path": aux_sets,
        "distinct_aux_sets": [list(s) for s in {tuple(x) for x in aux_sets}],
        "all_use_only_48": all(s == [48] for s in aux_sets),
    }


def try_shrink_cover():
    sc = json.loads((RES / "discovery_corridor_static_certificate.json").read_text())
    quads = sc["covering_quads"]
    a_mask, b_mask = sc["a"], sc["b"]
    p_pts = stones(a_mask & ~b_mask, 49)
    q_pts = stones(b_mask & ~a_mask, 49)
    u_pts = stones(a_mask | b_mask, 49)
    quads7 = load_quads7()
    u_set = set(u_pts)
    u_quads = [q for q in quads7 if all(p in u_set for p in q)]
    u_quad_masks = quads_to_masks(u_quads)
    p_set, q_set = set(p_pts), set(q_pts)

    candidates = []
    for sz in range(13, 18):
        for comb in combinations(u_pts, sz):
            m = 0
            for p in comb:
                m |= 1 << p
            d = sum(1 for p in comb if p in q_set) - sum(1 for p in comb if p in p_set)
            if d not in (2, 3):
                continue
            if is_safe_mask(m, u_quad_masks):
                candidates.append(m)

    cover_masks = list(quads)
    cover_set = set(cover_masks)
    u_qset = set(u_quad_masks)

    def hits(cm, cand):
        return (cand & cm) == cm

    def covers_all(subset):
        return all(any(hits(qm, c) for qm in subset) for c in candidates)

    full_ok = covers_all(cover_masks)
    # iterative 1-minimal
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
    # try all pairs removal to see if 19 works from the original 21
    pair_removal_ok = None
    if full_ok and len(cover_masks) == 21:
        for i, j in combinations(range(21), 2):
            sub = [cover_masks[k] for k in range(21) if k != i and k != j]
            if covers_all(sub):
                pair_removal_ok = {"removed": [i, j], "remaining": 19}
                break
    # greedy
    def greedy_cover():
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

    g = greedy_cover() if full_ok else []
    return {
        "n_cover_quads": len(quads),
        "n_u_quads_total": len(u_quads),
        "covers_are_real_U_quads": cover_set <= u_qset,
        "n_candidates_regenerated": len(candidates),
        "n_candidates_certificate": sc["candidate_count"],
        "full_cover_ok": full_ok,
        "min_1minimal_cover_size": len(current) if full_ok else None,
        "pair_removal_19": pair_removal_ok,
        "greedy_cover_size": len(g),
    }


def probe_other_g12_components(closed903: list[int], closed250: list[int]):
    """Look for safe 12-sets outside the 8 D4 images of the 903 component.

    Cheap approach: enumerate all safe 12-sets with a bounded DFS and test
    membership in the D4 orbit of closed903. If the number is too large,
    sample instead.
    """
    quads7 = load_quads7()
    quad_masks = quads_to_masks(quads7)
    # Build D4 orbit of closed903
    perms = d4_perms(7)
    orbit = set()
    for m in closed903:
        for p in perms:
            orbit.add(apply_perm(m, p))
    print(f"D4 orbit of 903-component has {len(orbit)} states", flush=True)

    # Also orbit of 250
    orbit250 = set()
    for m in closed250:
        for p in perms:
            orbit250.add(apply_perm(m, p))
    print(f"D4 orbit of 250-component has {len(orbit250)} states", flush=True)

    # Enumerate safe 12-sets via DFS with incremental blocking.
    # We only need to find whether any safe 12-set is outside `orbit`.
    v = 49
    tbp = defaultdict(list)  # point -> list of triple-masks that complete a quad
    for qm in quad_masks:
        qpts = stones(qm, v)
        for t in qpts:
            others = qm & ~(1 << t)
            tbp[t].append(others)

    found_outside = []
    n_safe12 = 0
    nodes = 0

    def dfs(start: int, chosen: int, count: int, cand: int, ccount: list[int]):
        nonlocal n_safe12, nodes
        nodes += 1
        if count == 12:
            n_safe12 += 1
            if chosen not in orbit:
                found_outside.append(chosen)
            return
        if not cand or count + cand.bit_count() < 12:
            return
        # pick next cell >= start
        u = (cand & -cand).bit_length() - 1
        if u < start:
            # mask out bits below start
            cand &= ~((1 << start) - 1)
            if not cand:
                return
            u = (cand & -cand).bit_length() - 1
        # option: skip u permanently
        dfs(start, chosen, count, cand & ~(1 << u), ccount)
        # option: take u
        newcand = cand & ~(1 << u)
        undo = []
        ok = True
        for o in tbp.get(u, []):
            pc = bin(o & chosen).count("1")
            if pc == 2:
                wmask = o & ~chosen
                if wmask == 0:
                    ok = False
                    break
                w = (wmask & -wmask).bit_length() - 1
                if ccount[w] == 0:
                    newcand &= ~(1 << w)
                ccount[w] += 1
                undo.append(w)
        if ok:
            dfs(u + 1, chosen | (1 << u), count + 1, newcand, ccount)
        for w in undo:
            ccount[w] -= 1

    ccount = [0] * v
    # Stop early if we find 20 outside states
    class Early(Exception):
        pass

    def dfs_limited(start, chosen, count, cand, ccount):
        nonlocal n_safe12, nodes
        if len(found_outside) >= 20:
            raise Early()
        nodes += 1
        if count == 12:
            n_safe12 += 1
            if chosen not in orbit:
                found_outside.append(chosen)
            return
        if not cand or count + cand.bit_count() < 12:
            return
        cand2 = cand & ~((1 << start) - 1)
        if not cand2:
            return
        u = (cand2 & -cand2).bit_length() - 1
        dfs_limited(start, chosen, count, cand2 & ~(1 << u), ccount)
        newcand = cand2 & ~(1 << u)
        undo = []
        ok = True
        for o in tbp.get(u, []):
            pc = bin(o & chosen).count("1")
            if pc == 2:
                wmask = o & ~chosen
                if wmask == 0:
                    ok = False
                    break
                w = (wmask & -wmask).bit_length() - 1
                if ccount[w] == 0:
                    newcand &= ~(1 << w)
                ccount[w] += 1
                undo.append(w)
        if ok:
            dfs_limited(u + 1, chosen | (1 << u), count + 1, newcand, ccount)
        for w in undo:
            ccount[w] -= 1

    try:
        dfs_limited(0, 0, 0, (1 << v) - 1, [0] * v)
        complete = True
    except Early:
        complete = False

    return {
        "d4_orbit_of_903_size": len(orbit),
        "d4_orbit_of_250_size": len(orbit250),
        "n_safe12_seen": n_safe12,
        "n_outside_orbit_found": len(found_outside),
        "outside_examples": found_outside[:5],
        "enumeration_complete": complete,
        "nodes": nodes,
    }


def main():
    d_full = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    d_48 = json.loads((RES / "discovery_full_board_forbid_48.json").read_text())
    closed903 = d_full["closed_set"]
    closed250 = d_48["closed_set"]
    a_mask = d_full["reachable_14_sets"][0]
    b_mask = d_full["reachable_14_sets"][1]

    aux = enumerate_shortest_path_aux(closed903, a_mask, b_mask)
    print("aux:", aux, flush=True)

    cover = try_shrink_cover()
    print("cover:", cover, flush=True)

    other = probe_other_g12_components(closed903, closed250)
    print("other:", other, flush=True)

    OUT.write_text(
        json.dumps(
            {"B114_aux": aux, "B116_cover": cover, "B112_B119_other": other},
            indent=2,
            default=str,
        )
    )
    print("wrote", OUT)


if __name__ == "__main__":
    main()
