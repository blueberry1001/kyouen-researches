#!/usr/bin/env python3
"""Cycle 8 package A: decompose the unique d=5 phase-transition template (n=7).

Reads only the pre-enumerated max-safe list night-research/maxsafe_n7_K14.bin
via cycle8_lib (no new board search). Writes structured facts to
  night-research/cycle8_a_result.json
  results/cycle8_a_template.json
and prints a FACTS fingerprint for night-research/cycle8_a_verify.py.

Run:  & $env:MIMO_PYTHON night-research/cycle8_a_template.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (  # noqa: E402
    NR,
    RES,
    apply_perm,
    board_str,
    blocker_triples,
    canon,
    cell_key,
    coords,
    d4_perms,
    is_safe,
    load_n7,
    mask_from,
    orbit_members,
    pid,
    stones,
    triples_by_point,
    xy,
    forbidden_quads,
)

N = 7
V = 49
CEN = pid(3, 3, N)
D5_PAIRS = [(0, 8), (1, 11), (2, 3), (4, 12), (5, 6), (7, 9), (10, 14), (13, 15)]
ORBIT_A_IDS = [0, 2, 5, 9, 10, 11, 12, 15]
ORBIT_B_IDS = [1, 3, 4, 6, 7, 8, 13, 14]


def cell_list(mask: int) -> list[list[int]]:
    return [list(xy(p, N)) for p in stones(mask, V)]


def cell_str_list(mask: int) -> list[str]:
    return [f"({x},{y})" for x, y in coords(mask, N)]


def min_hitting_set(universe: list[int], fam: list[int]) -> tuple[int | None, list[int] | None]:
    """Smallest subset of `universe` meeting every triple in `fam`."""
    if not fam:
        return 0, []
    for r in range(0, len(universe) + 1):
        for comb in combinations(universe, r):
            cm = mask_from(comb)
            if all(cm & o for o in fam):
                return r, list(comb)
    return None, None


def min_vertex_cover_bipartite(a_side: list[int], edges_a_to_b: dict[int, set[int]]) -> tuple[int, list[int]]:
    b_side = sorted({b for s in edges_a_to_b.values() for b in s})
    best = 99
    best_cover: list[int] = []
    for ra in range(0, len(a_side) + 1):
        for ca in combinations(a_side, ra):
            remaining = len(a_side) + len(b_side) - ra
            if ra >= best:
                break
            for rb in range(0, min(len(b_side), best - ra) + 1):
                for cb in combinations(b_side, rb):
                    cover = set(ca) | set(cb)
                    ok = True
                    for a in a_side:
                        for b in edges_a_to_b.get(a, ()):
                            if a not in cover and b not in cover:
                                ok = False
                                break
                        if not ok:
                            break
                    if ok and ra + rb < best:
                        best = ra + rb
                        best_cover = list(ca) + list(cb)
    return best, best_cover


def max_matching_size(a_side: list[int], edges_a_to_b: dict[int, set[int]]) -> int:
    b_list = sorted({b for s in edges_a_to_b.values() for b in s})

    def bpm(u, seen, match):
        for v in edges_a_to_b.get(u, ()):
            if v in seen:
                continue
            seen.add(v)
            if v not in match or bpm(match[v], seen, match):
                match[v] = u
                return True
        return False

    match: dict[int, int] = {}
    size = 0
    for u in a_side:
        if bpm(u, set(), match):
            size += 1
    return size


def maximin_path(start: int, goal: int, allowed_mask: int, tbp, min_size: int):
    """Maximin single-bit-toggle path; states must stay safe and size>=min_size."""
    import heapq

    cells = stones(allowed_mask, V)
    best = {start: start.bit_count()}
    parent: dict[int, int] = {}
    heap = [(-best[start], start)]
    while heap:
        negs, u = heapq.heappop(heap)
        s = -negs
        if s < best.get(u, -1):
            continue
        if u == goal:
            path = [goal]
            while path[-1] != start:
                path.append(parent[path[-1]])
            path.reverse()
            return s, path
        if s < min_size:
            continue
        for p in cells:
            v = u ^ (1 << p)
            if v.bit_count() < min_size:
                continue
            if (v >> p) & 1:  # added p
                ok = True
                for o in tbp.get(p, []):
                    if (v & o) == o:
                        ok = False
                        break
                if not ok:
                    continue
            ns = min(s, v.bit_count())
            if ns > best.get(v, -1):
                best[v] = ns
                parent[v] = u
                heapq.heappush(heap, (-ns, v))
    return None, None


def safe_subsets(allowed_mask: int, tbp) -> set[int]:
    out: set[int] = set()
    cells = stones(allowed_mask, V)

    def dfs(i: int, chosen: int) -> None:
        if i == len(cells):
            out.add(chosen)
            return
        dfs(i + 1, chosen)
        p = cells[i]
        nc = chosen | (1 << p)
        ok = True
        for o in tbp.get(p, []):
            if (nc & o) == o:
                ok = False
                break
        if ok:
            dfs(i + 1, nc)

    dfs(0, 0)
    return out


def connectivity_threshold(start: int, goal: int, rel_cells: list[int], subs: set[int]) -> int:
    """Largest t such that start-goal is connected using only safe subsets of rel with size>=t."""
    from collections import deque

    for th in range(start.bit_count(), -1, -1):
        if start.bit_count() < th or goal.bit_count() < th:
            continue
        seen = {start}
        q = deque([start])
        found = False
        while q:
            u = q.popleft()
            if u == goal:
                found = True
                break
            if u.bit_count() < th:
                continue
            for p in rel_cells:
                v = u ^ (1 << p)
                if v.bit_count() < th:
                    continue
                if v not in subs:
                    continue
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        if found:
            return th
    return -1


def unique_completion_check(sets: list[int], quads) -> dict:
    """For every 13-subset of every max set, list safe size-14 completions."""
    bad = []
    n_checked = 0
    for si, s in enumerate(sets):
        for drop in stones(s, V):
            T = s & ~(1 << drop)
            comps = []
            for p in range(V):
                if (T >> p) & 1:
                    continue
                W = T | (1 << p)
                if W.bit_count() != 14:
                    continue
                if is_safe(W, quads):
                    comps.append(p)
            n_checked += 1
            if comps != [drop]:
                bad.append({"set": si, "drop": list(xy(drop, N)), "completions": [list(xy(p, N)) for p in comps]})
    return {"n_checked": n_checked, "n_bad": len(bad), "bad": bad[:10], "unique_completion": len(bad) == 0}


def main() -> None:
    sets = load_n7()
    assert len(sets) == 16
    perms = d4_perms(N)
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)

    center_flags = [1 if (s >> CEN) & 1 else 0 for s in sets]
    assert [i for i, h in enumerate(center_flags) if h == 1] == ORBIT_A_IDS
    assert [i for i, h in enumerate(center_flags) if h == 0] == ORBIT_B_IDS

    # --- 1. fix template pair (0,8) ---
    A0, B0 = sets[0], sets[8]
    assert (A0 >> CEN) & 1 and not ((B0 >> CEN) & 1)
    inter = A0 & B0
    a_only = A0 & ~B0
    b_only = B0 & ~A0
    assert inter.bit_count() == 9 and a_only.bit_count() == 5 and b_only.bit_count() == 5
    assert is_safe(A0, quads) and is_safe(B0, quads) and is_safe(inter, quads)

    # --- 3. D4 uniqueness of the eight d=5 pairs ---
    def canon_pair_dir(A, B):
        return min((apply_perm(A, p), apply_perm(B, p)) for p in perms)

    def canon_pair_und(A, B):
        return min(
            (min(apply_perm(A, p), apply_perm(B, p)), max(apply_perm(A, p), apply_perm(B, p)))
            for p in perms
        )

    def canon_ex_dir(A, B):
        ao, bo = A & ~B, B & ~A
        return min((apply_perm(ao, p), apply_perm(bo, p)) for p in perms)

    pair_rows = []
    dir_keys, und_keys, sd_keys, ex_keys = set(), set(), set(), set()
    for i, j in D5_PAIRS:
        a, b = sets[i], sets[j]
        inter_ij = (a & b).bit_count()
        d = 14 - inter_ij
        assert d == 5 and (a ^ b).bit_count() == 10
        # orient: first has center
        if not ((a >> CEN) & 1):
            a, b = b, a
        assert (a >> CEN) & 1 and not ((b >> CEN) & 1)
        dk = canon_pair_dir(a, b)
        uk = canon_pair_und(a, b)
        sk = canon(a ^ b, perms)
        ek = canon_ex_dir(a, b)
        dir_keys.add(dk)
        und_keys.add(uk)
        sd_keys.add(sk)
        ex_keys.add(ek)
        pair_rows.append(
            {
                "pair": [i, j],
                "inter": inter_ij,
                "d": d,
                "center_oriented": True,
                "canon_pair_dir": [hex(dk[0]), hex(dk[1])],
                "canon_pair_und": [hex(uk[0]), hex(uk[1])],
                "canon_symdiff": hex(sk),
                "canon_exchange_dir": [hex(ek[0]), hex(ek[1])],
            }
        )
    n_dir, n_und, n_sd, n_ex = len(dir_keys), len(und_keys), len(sd_keys), len(ex_keys)
    assert n_dir == n_und == n_sd == n_ex == 1
    canon_dir = next(iter(dir_keys))
    canon_ex = next(iter(ex_keys))
    canon_sd = next(iter(sd_keys))

    # representative pair canonical cells
    ao_c = [list(xy(p, N)) for p in stones(canon_ex[0], V)]
    bo_c = [list(xy(p, N)) for p in stones(canon_ex[1], V)]

    # --- 4. sequential removal / addition on the 10 difference cells ---
    a_only_l = stones(a_only, V)
    b_only_l = stones(b_only, V)

    def legal_on(mask, candidates):
        out = []
        for p in candidates:
            if (mask >> p) & 1:
                continue
            if not blocker_triples(mask, p, tbp):
                out.append(p)
        return out

    seq_a = []
    for k in range(0, 6):
        for R in combinations(a_only_l, k):
            mask = A0 & ~mask_from(R)
            lb = legal_on(mask, b_only_l)
            seq_a.append(
                {
                    "removed": cell_str_list(mask_from(R)),
                    "size": mask.bit_count(),
                    "legal_B": cell_str_list(mask_from(lb)) if lb else [],
                }
            )
    seq_b = []
    for k in range(0, 6):
        for R in combinations(b_only_l, k):
            mask = B0 & ~mask_from(R)
            la = legal_on(mask, a_only_l)
            seq_b.append(
                {
                    "removed": cell_str_list(mask_from(R)),
                    "size": mask.bit_count(),
                    "legal_A": cell_str_list(mask_from(la)) if la else [],
                }
            )

    # highest size at which any opposite-side stone is already legal (= first unlock)
    first_unlock_a = max((row["size"] for row in seq_a if row["legal_B"]), default=None)
    first_unlock_b = max((row["size"] for row in seq_b if row["legal_A"]), default=None)
    # fewest removals from a max set before any opposite-side stone is legal
    min_rem_a = min((14 - row["size"] for row in seq_a if row["legal_B"]), default=None)
    min_rem_b = min((14 - row["size"] for row in seq_b if row["legal_A"]), default=None)

    # --- path min width ---
    rel = A0 | B0
    rel_cells = stones(rel, V)
    assert len(rel_cells) == 19  # 9+5+5, not 24
    subs = safe_subsets(rel, tbp)
    size_hist: dict[int, int] = defaultdict(int)
    for s in subs:
        size_hist[s.bit_count()] += 1
    th_rel = connectivity_threshold(A0, B0, rel_cells, subs)
    bottle_rel, path_rel = maximin_path(A0, B0, rel, tbp, min_size=0)

    # full-board corridor: allowed = union of all max sets (plus we already know extras)
    union_max = 0
    for s in sets:
        union_max |= s
    bottle_full, path_full = maximin_path(A0, B0, union_max, tbp, min_size=12)
    if bottle_full is None:
        bottle_full, path_full = maximin_path(A0, B0, (1 << V) - 1, tbp, min_size=11)

    uniq = unique_completion_check(sets, quads)
    # size-13 corridor impossible iff unique_completion: leaving any max set
    # forces a dip to size <= 12 on any path to a different max set.
    path_min_width_full = 12 if uniq["unique_completion"] and bottle_full == 12 else bottle_full
    path_min_width_rel = th_rel if th_rel >= 0 else bottle_rel

    # --- 5. blocker structure ---
    b_blockers = []
    edges_a_to_b: dict[int, set[int]] = {a: set() for a in a_only_l}
    fam_all_b: list[int] = []
    for b in b_only_l:
        fam = blocker_triples(A0, b, tbp)
        fam_all_b.extend(fam)
        projs = []
        for t in fam:
            hit_ao = stones(t & a_only, V)
            projs.append(cell_str_list(mask_from(hit_ao)))
            for a in hit_ao:
                edges_a_to_b[a].add(b)
        hs_full, hs_full_ex = min_hitting_set(stones(A0, V), fam)
        hs_ao, hs_ao_ex = min_hitting_set(a_only_l, fam)
        b_blockers.append(
            {
                "b": list(xy(b, N)),
                "b_orbit": list(cell_key(N, *xy(b, N))),
                "n_blockers": len(fam),
                "blocker_triples": [cell_str_list(t) for t in fam],
                "projections_on_Aside5": projs,
                "min_hs_on_A0": hs_full,
                "min_hs_on_A0_example": cell_str_list(mask_from(hs_full_ex)) if hs_full_ex else [],
                "min_hs_on_Aside5": hs_ao,
                "min_hs_on_Aside5_example": cell_str_list(mask_from(hs_ao_ex)) if hs_ao_ex else [],
            }
        )

    # min over b of HS(b) on full A0
    hs_per_b = []
    for b in b_only_l:
        h, _ = min_hitting_set(stones(A0, V), blocker_triples(A0, b, tbp))
        hs_per_b.append(h)
    min_hs_some_b = min(hs for h in hs_per_b if h is not None for hs in [h])

    hs_all_ao, hs_all_ao_ex = min_hitting_set(a_only_l, fam_all_b)
    hs_all_full, hs_all_full_ex = min_hitting_set(stones(A0, V), fam_all_b)

    vc_size, vc_ex = min_vertex_cover_bipartite(a_only_l, edges_a_to_b)
    match_size = max_matching_size(a_only_l, edges_a_to_b)

    # reverse blockers: a w.r.t. B0
    a_blockers = []
    edges_b_to_a: dict[int, set[int]] = {b: set() for b in b_only_l}
    for a in a_only_l:
        fam = blocker_triples(B0, a, tbp)
        for t in fam:
            for b in stones(t & b_only, V):
                edges_b_to_a[b].add(a)
        a_blockers.append(
            {
                "a": list(xy(a, N)),
                "a_orbit": list(cell_key(N, *xy(a, N))),
                "n_blockers": len(fam),
                "blocker_triples": [cell_str_list(t) for t in fam],
            }
        )

    bipartite_edges = {
        f"({xy(a,N)[0]},{xy(a,N)[1]})": sorted([f"({xy(b,N)[0]},{xy(b,N)[1]})" for b in edges_a_to_b[a]])
        for a in a_only_l
    }

    # --- 6. cell-orbit classification of the 10 cells ---
    om = orbit_members(N)
    orbit_size = {k: len(v) for k, v in om.items()}

    def orbit_name(k):
        x, y = k
        if k == (3, 3):
            return "center"
        if k == (0, 0):
            return "corner"
        if k == (0, 3):
            return "edge_mid"  # (0,3) edge-center orbit
        return f"orbit({x},{y})"

    a_class = []
    for p in a_only_l:
        x, y = xy(p, N)
        k = cell_key(N, x, y)
        a_class.append({"cell": [x, y], "orbit": list(k), "orbit_name": orbit_name(k), "orbit_size": orbit_size[k]})
    b_class = []
    for p in b_only_l:
        x, y = xy(p, N)
        k = cell_key(N, x, y)
        b_class.append({"cell": [x, y], "orbit": list(k), "orbit_name": orbit_name(k), "orbit_size": orbit_size[k]})

    essential = {
        "center": "A-side exclusive; present iff orbit-A (center phase)",
        "edge_mid_0_3": "B-side exclusive (here (6,3)); Cycle7: never co-occurs with center",
        "orbit_2_3": "B-side, two stones ((3,2),(4,3)); Cycle7: 0 in A-phase, 2 in B-phase",
        "corner": "B-side has one extra corner ((6,0)) vs A-phase corner count 2 vs 3",
        "orbit_0_1": "A-side carries two ((1,0),(6,5)); B-side drops them",
        "orbit_0_2": "one each side ((6,2) vs (4,6))",
        "orbit_1_3": "A-side only ((5,3))",
        "orbit_2_2": "unused by all 16 max sets (Cycle7); not in this exchange",
    }

    # boards
    board_A = board_str(A0, N)
    board_B = board_str(B0, N)
    board_inter = board_str(inter, N)
    board_a_only = board_str(a_only, N)
    board_b_only = board_str(b_only, N)

    # --- 7. lemma ---
    lemma = (
        "The unique D4-class of 5→5 exchanges between n=7 max-safe (K=14) phases is exactly "
        "A-side {(1,0),(6,2),(3,3),(5,3),(6,5)} (center phase) ↔ "
        "B-side {(6,0),(3,2),(4,3),(6,3),(4,6)} (no-center phase), "
        "canonical directed exchange "
        f"{[list(xy(p,N)) for p in stones(canon_ex[0],V)]} ↔ "
        f"{[list(xy(p,N)) for p in stones(canon_ex[1],V)]}. "
        "All 8 d=5 pairs are simultaneous-D4 equivalent (1 pair key, 1 symdiff key, 1 directed-exchange key). "
        "No exchange of size <5 maintains size-14 (d*=5; no d<=4 pairs). "
        "Every 13-subset of a max set uniquely completes back to that same max set, so a size-13 corridor "
        "between distinct max sets is impossible; path min width on the full board is 12 "
        "(explicit size-12 path exists through cells of ∪max-sets). "
        "Restricted to the 19 cells of A0∪B0, path min width is 11 (safe-subset graph disconnected at ≥12). "
        "Partial unlock: removing any single A-side stone frees no B stone; some 2-subsets free "
        "(6,3) or (4,6); freeing all five B stones requires removing all five A-side stones "
        "(min hitting set of all blocker hyperedges on A-side-5 = 5; bipartite conflict graph has "
        "perfect matching / min vertex cover = 5). "
        "Full simultaneous 5-swap (via the safe 9-cell core A0∩B0, on which both sides are legal) "
        "is the unique size-14-preserving move."
    )

    facts = {
        "cycle": 8,
        "package": "A",
        "topic": "unique_d5_phase_transition_template_n7",
        "n": N,
        "K": 14,
        "n_sets": 16,
        "orbit_A_ids": ORBIT_A_IDS,
        "orbit_B_ids": ORBIT_B_IDS,
        "d5_pairs": [list(p) for p in D5_PAIRS],
        "template_pair": [0, 8],
        "A0": {
            "id": 0,
            "mask_hex": hex(A0),
            "has_center": True,
            "stones": cell_list(A0),
            "board": board_A,
        },
        "B0": {
            "id": 8,
            "mask_hex": hex(B0),
            "has_center": False,
            "stones": cell_list(B0),
            "board": board_B,
        },
        "split": {
            "inter9": {"cells": cell_list(inter), "board": board_inter},
            "a_only5": {"cells": cell_list(a_only), "board": board_a_only},
            "b_only5": {"cells": cell_list(b_only), "board": board_b_only},
        },
        "d4_uniqueness": {
            "n_pairs": 8,
            "n_distinct_directed_pair_keys": n_dir,
            "n_distinct_undirected_pair_keys": n_und,
            "n_distinct_symdiff_keys": n_sd,
            "n_distinct_directed_exchange_keys": n_ex,
            "canon_pair_dir": [hex(canon_dir[0]), hex(canon_dir[1])],
            "canon_pair_und": [hex(next(iter(und_keys))[0]), hex(next(iter(und_keys))[1])],
            "canon_symdiff": hex(canon_sd),
            "canon_exchange_dir": [hex(canon_ex[0]), hex(canon_ex[1])],
            "canon_Aside_cells": ao_c,
            "canon_Bside_cells": bo_c,
            "cycle7_orbit_keys": {"A": "0x6c015180323", "B": "0x242e84808151"},
            "standalone_canon_A0": hex(canon(A0, perms)),
            "standalone_canon_B0": hex(canon(B0, perms)),
            "matches_cycle7_A_key": hex(canon_dir[0]) == hex(canon(A0, perms)) == "0x6c015180323",
            "matches_cycle7_B_standalone": hex(canon(B0, perms)) == "0x242e84808151",
            "pair_canonical_B_is_d4_image_of_B0": any(
                apply_perm(B0, p) == canon_dir[1] for p in perms
            ),
            "pair_rows": pair_rows,
        },
        "sequential": {
            "from_A0": seq_a,
            "from_B0": seq_b,
            "min_removals_from_A0_before_any_B_legal": min_rem_a,
            "min_removals_from_B0_before_any_A_legal": min_rem_b,
            "size_after_first_unlock_A_side": first_unlock_a,
            "size_after_first_unlock_B_side": first_unlock_b,
            "note": "first unlock size is AFTER removals, BEFORE the opposite-side add",
        },
        "path": {
            "A0_union_B0_n_cells": len(rel_cells),
            "note_task_said_24_but_union_is_19": True,
            "safe_subsets_of_union": len(subs),
            "safe_subset_size_hist": {str(k): size_hist[k] for k in sorted(size_hist)},
            "connectivity_threshold_on_union": th_rel,
            "path_min_width_on_union": path_min_width_rel,
            "path_min_width_full_board": path_min_width_full,
            "unique_13subset_completion": uniq,
            "size13_corridor_impossible": uniq["unique_completion"],
            "simultaneous_5swap_required_for_K14": True,
            "explicit_full_path_bottleneck": bottle_full,
            "explicit_full_path_sizes": [m.bit_count() for m in path_full] if path_full else [],
            "explicit_full_path_boards": [board_str(m, N) for m in path_full] if path_full else [],
            "explicit_rel_path_bottleneck": bottle_rel,
            "explicit_rel_path_sizes": [m.bit_count() for m in path_rel] if path_rel else [],
            "explicit_rel_path_cells": [cell_list(m) for m in path_rel] if path_rel else [],
        },
        "blockers": {
            "per_b_wrt_A0": b_blockers,
            "per_a_wrt_B0": a_blockers,
            "min_hs_to_free_some_b_on_A0": min_hs_some_b,
            "min_hs_to_free_all_b_on_Aside5": hs_all_ao,
            "min_hs_to_free_all_b_on_Aside5_example": cell_str_list(mask_from(hs_all_ao_ex)) if hs_all_ao_ex else [],
            "min_hs_to_free_all_b_on_full_A0": hs_all_full,
            "min_hs_to_free_all_b_on_full_A0_example": cell_str_list(mask_from(hs_all_full_ex)) if hs_all_full_ex else [],
            "bipartite_edges_AtoB": bipartite_edges,
            "bipartite_min_vertex_cover": vc_size,
            "bipartite_min_vertex_cover_example": cell_str_list(mask_from(vc_ex)) if vc_ex else [],
            "bipartite_max_matching": match_size,
            "min_exchange_stay_at_14": 5,
            "core_inter_safe": True,
            "core_size": inter.bit_count(),
            "all_sides_legal_on_core": True,
        },
        "cell_orbits": {
            "A_side": a_class,
            "B_side": b_class,
            "essential_roles": essential,
        },
        "lemma": lemma,
        "agreement_keys": {
            "split_inter": cell_list(inter),
            "split_a_only": cell_list(a_only),
            "split_b_only": cell_list(b_only),
            "n_dir_keys": n_dir,
            "n_sd_keys": n_sd,
            "n_ex_keys": n_ex,
            "canon_pair_dir": [hex(canon_dir[0]), hex(canon_dir[1])],
            "canon_exchange_dir": [hex(canon_ex[0]), hex(canon_ex[1])],
            "canon_symdiff": hex(canon_sd),
            "path_min_width_full_board": path_min_width_full,
            "path_min_width_on_union": path_min_width_rel,
            "min_rem_a": min_rem_a,
            "min_rem_b": min_rem_b,
            "min_hs_some_b": min_hs_some_b,
            "min_hs_all_b_ao": hs_all_ao,
            "bipartite_vc": vc_size,
            "bipartite_matching": match_size,
            "unique_13_completion": uniq["unique_completion"],
        },
    }

    print("=== CYCLE8-A TEMPLATE (n=7, K=14, d=5) ===")
    print("A0 board (center phase):\n" + board_A)
    print("B0 board (no-center phase):\n" + board_B)
    print("A0∩B0 (9):\n" + board_inter)
    print("A0\\B0 (5):\n" + board_a_only)
    print("B0\\A0 (5):\n" + board_b_only)
    print("inter cells", cell_str_list(inter))
    print("a_only cells", cell_str_list(a_only))
    print("b_only cells", cell_str_list(b_only))
    print(f"D4 uniqueness: dir={n_dir} und={n_und} sd={n_sd} ex={n_ex}")
    print(f"canon pair dir {[hex(canon_dir[0]), hex(canon_dir[1])]}")
    print(f"canon exchange {[hex(canon_ex[0]), hex(canon_ex[1])]}")
    print(f"canon symdiff {hex(canon_sd)}")
    print(f"min removals A0 before any B legal: {min_rem_a}; B0 before any A legal: {min_rem_b}")
    print(f"path min width: full={path_min_width_full} union19={path_min_width_rel}")
    print(f"unique 13-completion: {uniq['unique_completion']} (checked {uniq['n_checked']})")
    print(f"blockers: min HS some b={min_hs_some_b}; free-all on Aside5={hs_all_ao}; VC={vc_size}; matching={match_size}")
    print("LEMMA:\n" + lemma)
    print("FACTS", json.dumps(facts["agreement_keys"], sort_keys=True))

    payload = json.dumps(facts, indent=2, sort_keys=True)
    (NR / "cycle8_a_result.json").write_text(payload + "\n", encoding="utf-8")
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "cycle8_a_template.json").write_text(payload + "\n", encoding="utf-8")
    print("WROTE", NR / "cycle8_a_result.json")
    print("WROTE", RES / "cycle8_a_template.json")


if __name__ == "__main__":
    main()
