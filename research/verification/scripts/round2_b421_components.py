#!/usr/bin/env python3
"""Round2 B421-B430: G_12 components that do NOT contain a max-14 set.

Uses existing data first (maxsafe_n7_K14.bin, discovery 903/250, 5 isolated
12-stones). Adds a bounded DFS search for additional outside-12 states and
local component probes. No full re-enumeration of n>=7.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
sys.path.insert(0, str(ROOT / "research/verification/scripts"))
from kyouen_core import Board, square_points  # noqa: E402

RES = ROOT / "results"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research/verification/round2_b411.json"


def popcount(x: int) -> int:
    return bin(x).count("1")


def bits(x: int) -> list[int]:
    return [i for i in range(49) if (x >> i) & 1]


def load_max14():
    data = (NIGHT / "maxsafe_n7_K14.bin").read_bytes()
    return [int.from_bytes(data[i * 8 : (i + 1) * 8], "little") for i in range(16)]


def load_903_orbit():
    """8 D4 images of the 903 component (7224 states) from the one closed_set."""
    cd = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    closed = cd["closed_set"]
    # D4 on 7x7: id = y*7+x
    def d4(s, k):
        out = 0
        for i in range(49):
            if (s >> i) & 1:
                x, y = i % 7, i // 7
                for _ in range(k % 4):
                    x, y = y, 6 - x  # rot90
                if k >= 4:
                    x = 6 - x  # reflect
                out |= 1 << (y * 7 + x)
        return out

    orbit = set()
    for s in closed:
        for k in range(8):
            orbit.add(d4(s, k))
    return orbit, closed


def is_safe_with(board: Board, occ: int) -> bool:
    for q in board.quads:
        if (occ & q) == q:
            return False
    return True


def legal_adds(board: Board, occ: int) -> list[int]:
    """Cells that can be added keeping safety (any size)."""
    out = []
    empty = board.full ^ occ
    v = 0
    e = empty
    while e:
        if e & 1:
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                out.append(v)
        e >>= 1
        v += 1
    return out


def g12_component(board: Board, seed: int, max_states: int = 20000):
    """G_12 component: states of size>=12, edges = 1-stone add/remove."""
    if popcount(seed) < 12 or not is_safe_with(board, seed):
        return None
    seen = {seed}
    q = deque([seed])
    layers = Counter()
    layers[popcount(seed)] += 1
    edges = 0
    max_size = popcount(seed)
    while q:
        u = q.popleft()
        if len(seen) > max_states:
            return {"truncated": True, "n": len(seen), "layers": dict(layers)}
        cu = popcount(u)
        # removals
        if cu > 12:
            for i in bits(u):
                v = u ^ (1 << i)
                if v not in seen:
                    seen.add(v)
                    layers[popcount(v)] += 1
                    q.append(v)
                    edges += 1
        # additions
        for i in legal_adds(board, u):
            v = u | (1 << i)
            if v not in seen and popcount(v) >= 12:
                if v not in seen:
                    seen.add(v)
                    layers[popcount(v)] += 1
                    q.append(v)
                    edges += 1
        max_size = max(max_size, cu)
    return {
        "truncated": False,
        "n": len(seen),
        "layers": dict(layers),
        "max_size": max(popcount(s) for s in seen),
        "states": seen,
    }


def is_tree_component(board: Board, states: set[int]):
    """Check if G_12 component (as induced 1-add/remove graph) is a forest/tree."""
    # build edges
    sset = states
    adj = defaultdict(list)
    ne = 0
    for s in sset:
        for i in range(49):
            t = s ^ (1 << i)
            if t in sset and t > s:
                adj[s].append(t)
                adj[t].append(s)
                ne += 1
    nv = len(sset)
    # connected?
    start = next(iter(sset))
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    connected = len(seen) == nv
    is_tree = connected and ne == nv - 1
    # find cycles if any: BFS tree + back edges
    # induced cycle length max via DFS for small graphs
    longest_induced = None
    if nv <= 5000 and ne >= nv:
        # count independent cycles = ne - nv + ncomp
        ncomp = 1 if connected else None
        cyclomatic = ne - nv + 1 if connected else None
    else:
        cyclomatic = ne - nv + 1 if connected else None
    return {
        "n_vertices": nv,
        "n_edges": ne,
        "connected": connected,
        "is_tree": is_tree,
        "cyclomatic": cyclomatic,
    }


def longest_induced_cycle(adj, states, limit=15):
    """Exact longest induced cycle for tiny components (nv<=80)."""
    nodes = sorted(states)
    n = len(nodes)
    if n > 80:
        return None
    idx = {u: i for i, u in enumerate(nodes)}
    a = [set() for _ in range(n)]
    for u in nodes:
        for v in adj[u]:
            a[idx[u]].add(idx[v])
    best = 0
    # for each start, DFS for induced cycles
    for s in range(n):
        # BFS layered won't get induced; use DFS with neighbor-of-path check
        stack = [(s, [s], {s})]
        while stack:
            u, path, pset = stack.pop()
            if len(path) > best and len(path) >= 3 and s in a[u]:
                # induced? all consecutive edges exist; non-consecutive non-edges
                ok = True
                for i in range(len(path)):
                    for j in range(i + 2, len(path)):
                        if j == len(path) - 1 and i == 0:
                            continue  # closing edge allowed
                        if path[j] in a[path[i]]:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    best = max(best, len(path))
            if len(path) >= limit:
                continue
            for v in a[u]:
                if v == s and len(path) >= 3:
                    continue
                if v in pset:
                    continue
                # induced: v not adjacent to path except u (unless s)
                bad = False
                for w in path[:-1]:
                    if v in a[w]:
                        bad = True
                        break
                if bad:
                    continue
                stack.append((v, path + [v], pset | {v}))
    return best


def local_freeze_signature(board: Board, s12: int):
    """For each stone removed, the set of cells that can be re-added safely
    (size-12 again). Classify the pattern."""
    sig = []
    for i in bits(s12):
        base = s12 ^ (1 << i)
        adds = legal_adds(board, base)
        # which of those give size 12
        adds12 = [a for a in adds if a != i]
        sig.append((i, tuple(sorted(adds12))))
    return sig


def main():
    board = Board(square_points(7), "n7")
    max14 = load_max14()
    orbit903, closed903 = load_903_orbit()
    max_set = set(max14)

    # known isolated 12-stones from batch06_followups2
    iso_boards = [
        [13, 20, 22, 26, 28, 30, 39, 40, 41, 42, 45, 47],
        [13, 19, 21, 23, 29, 33, 34, 35, 36, 38, 46, 48],
        [13, 19, 21, 22, 33, 34, 36, 38, 39, 42, 44, 48],
        [13, 19, 21, 22, 27, 32, 33, 34, 36, 38, 42, 44],
        [13, 19, 20, 24, 26, 28, 29, 30, 39, 41, 42, 47],
    ]
    iso_masks = [sum(1 << c for c in b) for b in iso_boards]

    out = {}

    # ---- verify the 5 known isolated 12-stones ----
    iso_info = []
    for m in iso_masks:
        adds = legal_adds(board, m)
        adds13 = [a for a in adds if True]  # any safe add -> size 13
        # G_12 neighbors: adds (size 13) and removals only if size>12 (not here)
        iso_info.append(
            {
                "mask": m,
                "board": bits(m),
                "n_safe_13_adds": len(adds13),
                "n_g12_neighbors": len(adds13),
                "in_903_orbit": m in orbit903,
                "in_max14": m in max_set,
            }
        )
    out["known_isolated_12"] = iso_info

    # ---- search for more outside-orbit 12/13 states ----
    # bounded DFS: extend partial safe sets, collect size-12 sets outside orbit
    random.seed(20260927)
    found_out = set()
    found_13_nonmax = set()

    def dfs_collect(occ, start_cell, depth_target, acc):
        if len(acc) > 400:
            return
        k = popcount(occ)
        if k == depth_target:
            if occ not in orbit903:
                acc.add(occ)
            return
        for c in range(start_cell, 49):
            bit = 1 << c
            if occ & bit:
                continue
            ok = True
            for q in board.quads_by_pt[c]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                dfs_collect(occ | bit, c + 1, depth_target, acc)

    # a few random seeds then DFS
    for trial in range(8):
        acc = set()
        # random greedy 12 then perturb
        cells = list(range(49))
        random.shuffle(cells)
        occ = 0
        for c in cells:
            bit = 1 << c
            ok = True
            for q in board.quads_by_pt[c]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                occ |= bit
            if popcount(occ) >= 14:
                break
        if popcount(occ) >= 12:
            # all 12-subsets of occ that are outside orbit
            cl = bits(occ)
            for sub in combinations(cl, 12):
                m = sum(1 << c for c in sub)
                if m not in orbit903 and is_safe_with(board, m):
                    found_out.add(m)
        # targeted DFS from a small safe core
        core = 0
        pick = [0, 1, 5, 8]
        for c in pick:
            core |= 1 << c
        if is_safe_with(board, core):
            dfs_collect(core, 0, 12, found_out)
        if len(found_out) > 80:
            break

    out["search_outside_12"] = {
        "n_found": len(found_out),
        "incomplete": True,
        "examples": [bits(m) for m in sorted(found_out)[:15]],
    }

    # ---- component probes on found_out + known isolated ----
    probes = []
    seeds = list(iso_masks) + sorted(found_out)[:40]
    seen_seed = set()
    for m in seeds:
        if m in seen_seed:
            continue
        seen_seed.add(m)
        if m in orbit903:
            continue
        comp = g12_component(board, m, max_states=5000)
        if comp is None:
            continue
        states = comp.get("states", set())
        treeinfo = is_tree_component(board, states) if states else {}
        has14 = any(popcount(s) == 14 for s in states) if states else False
        n13 = sum(1 for s in states if popcount(s) == 13) if states else 0
        probes.append(
            {
                "seed": bits(m),
                "seed_mask": m,
                "n": comp["n"],
                "layers": comp["layers"],
                "max_size": comp.get("max_size"),
                "has_14": has14,
                "n_13": n13,
                "tree": treeinfo,
                "truncated": comp.get("truncated", False),
            }
        )
        if len(probes) >= 25:
            break

    out["component_probes"] = probes

    # ---- B425/B426/B427: local freeze on isolated 12-stones ----
    freeze = []
    for m in iso_masks:
        sig = local_freeze_signature(board, m)
        # re-add patterns: for each removed stone i, which cells can be added
        only_self = all(adds == (i,) or (i in adds and len(adds) == 1) for i, adds in
                        [(i, adds) for i, adds in sig] ) if False else None
        # actually B426: every 11-child has UNIQUE add-back = the original stone
        b426 = True
        details = []
        for i, adds in sig:
            # adds12 were other cells that give size 12; also original i can always be re-added
            # unique add-back means the only legal add to the 11-set is i itself
            base = m ^ (1 << i)
            all_adds = legal_adds(board, base)
            only_i = all_adds == [i] or set(all_adds) == {i}
            details.append({"removed": i, "legal_adds": all_adds, "only_self": only_i})
            if not only_i:
                b426 = False
        # B427: in G_11 (allow size 11), can reach a 13-set?
        # BFS G_11 from m: can go to size 11 (remove), then to 12/13
        reached13 = False
        # check: any 11-child has an add that reaches size 12 different, then +1 -> 13
        # simpler: search 13-sets at G_11-distance <= 3 (remove, add, add)
        q = deque([(m, 0)])
        seen = {m}
        found13 = None
        while q:
            u, d = q.popleft()
            if d > 4:
                continue
            if popcount(u) == 13 and u != m:
                found13 = u
                reached13 = True
                break
            # remove any one
            for i in bits(u):
                v = u ^ (1 << i)
                if v not in seen and is_safe_with(board, v):
                    seen.add(v)
                    q.append((v, d + 1))
            # add any one
            for i in legal_adds(board, u):
                v = u | (1 << i)
                if v not in seen and popcount(v) >= 11:
                    seen.add(v)
                    q.append((v, d + 1))
        freeze.append(
            {
                "board": bits(m),
                "b426_only_self_all_children": b426,
                "children": details,
                "b427_reaches_13_in_G11": reached13,
                "b427_found13": bits(found13) if found13 else None,
                "g11_visited": len(seen),
            }
        )
    out["freeze_analysis"] = freeze

    # ---- B428: center occupancy rates ----
    CENTER = 24
    iso_center = sum(1 for m in iso_masks if (m >> CENTER) & 1)
    # 12-stone states in 903 component
    c12 = [s for s in closed903 if popcount(s) == 12]
    c12_center = sum(1 for s in c12 if (s >> CENTER) & 1)
    # matched by corner occupancy count + orbit totals
    def corner_count(m):
        return sum(1 for c in (0, 6, 42, 48) if (m >> c) & 1)

    def orbit_profile(m):
        # D4 orbits of cells on 7x7: use (min over D4) as orbit id
        # precompute
        return None  # filled below

    # precompute cell orbits under D4
    def d4_cell(c, k):
        x, y = c % 7, c // 7
        for _ in range(k % 4):
            x, y = y, 6 - x
        if k >= 4:
            x = 6 - x
        return y * 7 + x

    cell_orbit = {}
    for c in range(49):
        orb = frozenset(d4_cell(c, k) for k in range(8))
        cell_orbit[c] = orb
    # orbit representatives
    orbits = sorted({cell_orbit[c] for c in range(49)}, key=lambda o: min(o))
    orb_id = {c: i for i, o in enumerate(orbits) for c in o}

    def occ_vector(m):
        v = [0] * len(orbits)
        for c in bits(m):
            v[orb_id[c]] += 1
        return tuple(v)

    # B428: among 12-stones matched on corner count and orbit profile, compare center rate
    # 903 12-stones
    def bucket_stats(masks):
        # (corner_count, orbit_vector_without_center_orbit) -> (n, n_center)
        d = defaultdict(lambda: [0, 0])
        for m in masks:
            key = (corner_count(m), occ_vector(m))
            d[key][0] += 1
            if (m >> CENTER) & 1:
                d[key][1] += 1
        return d

    iso_buckets = bucket_stats(iso_masks)
    c12_buckets = bucket_stats(c12)
    # compare overall center rate
    out["B428"] = {
        "iso_n": len(iso_masks),
        "iso_center": iso_center,
        "iso_rate": iso_center / len(iso_masks) if iso_masks else None,
        "c903_12_n": len(c12),
        "c903_12_center": c12_center,
        "c903_12_rate": c12_center / len(c12) if c12 else None,
        "same_bucket_overlap": 0,
    }
    # matched comparison
    matched = 0
    iso_only = 0
    for key, (n, nc) in iso_buckets.items():
        if key in c12_buckets:
            matched += n
    out["B428"]["n_iso_matched_bucket_in_903"] = matched

    # ---- B429: (2,2)-type orbit occupancy as axis ----
    # cell (2,2) is id 2*7+2=16. Its orbit.
    c22 = 16
    orb22 = cell_orbit[c22]
    # occupancy of this orbit in iso vs 903 12
    def occ_orb(m, orb):
        return sum(1 for c in bits(m) if c in orb)

    iso_o22 = Counter(occ_orb(m, orb22) for m in iso_masks)
    c12_o22 = Counter(occ_orb(m, orb22) for m in c12)
    out["B429"] = {
        "orbit_of_22": sorted(orb22),
        "iso_occ_hist": dict(iso_o22),
        "c903_12_occ_hist": dict(c12_o22),
    }

    # ---- B430: same orbit-occupancy vector, isolated and 903 both ----
    iso_vecs = {occ_vector(m) for m in iso_masks}
    c12_vecs = {occ_vector(m) for m in c12}
    common_vecs = iso_vecs & c12_vecs
    out["B430"] = {
        "n_iso_vectors": len(iso_vecs),
        "n_c12_vectors": len(c12_vecs),
        "n_common": len(common_vecs),
        "example_common_vectors": [list(v) for v in list(common_vecs)[:5]],
    }

    # ---- B421/B422/B423/B424 summary from probes ----
    nonmax = [p for p in probes if not p["has_14"]]
    noniso = [p for p in nonmax if p["n"] > 1]
    trees = [p for p in noniso if p["tree"].get("is_tree")]
    out["B421_B424"] = {
        "n_probes": len(probes),
        "n_nonmax": len(nonmax),
        "n_nonmax_noniso": len(noniso),
        "n_nonmax_noniso_trees": len(trees),
        "max_nonmax_size": max((p["n"] for p in nonmax), default=0),
        "max_nonmax_n13": max((p["n_13"] for p in nonmax), default=0),
        "all_nonmax_lt_903": all(p["n"] < 903 for p in nonmax),
        "all_nonmax_n13_le_8": all(p["n_13"] <= 8 for p in nonmax),
    }

    # merge into existing json
    data = json.loads(OUT.read_text())
    data.update(out)
    OUT.write_text(json.dumps(data, indent=2, default=str))
    print("iso_info", json.dumps(iso_info, indent=2)[:1500])
    print("search_outside", out["search_outside_12"]["n_found"])
    print("probes", len(probes))
    print("B421_B424", out["B421_B424"])
    print("B428", out["B428"])
    print("B430", out["B430"])


if __name__ == "__main__":
    main()
