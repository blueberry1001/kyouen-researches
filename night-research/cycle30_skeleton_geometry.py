#!/usr/bin/env python3
"""Cycle 30 — geometric certificates for skeleton-M capacity 13 on n=7.

Goal: recover a first-principles reason that the six mandatory orbits M
support at most 13 safe stones, and that +1 requires exclusive phase
extensions. Does NOT re-enumerate full K=14; uses census bins + local
forbidden-quad incidence + packing/cover certificates.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (
    NR,
    RES,
    board_str,
    cell_key,
    load_n7,
    mask_from,
    occupancy_vector,
    orbit_members,
    stones,
    forbidden_quads,
    det4,
    pid,
    xy,
)

N = 7
V = N * N
CENTER = pid(3, 3, N)
ORBIT_ORDER = [
    (0, 0),
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 1),
    (1, 2),
    (1, 3),
    (2, 2),
    (2, 3),
    (3, 3),
]
MANDATORY = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 3)]
M_KEYS = set(MANDATORY)
PHASE_A = (3, 3)  # center
PHASE_B = {(0, 3), (2, 3)}
F_KEY = (2, 2)


def members_mask(members: dict, keys) -> int:
    m = 0
    for k in keys:
        for p in members[k]:
            m |= 1 << p
    return m


def occ_on(mask: int, members: dict, keys) -> tuple:
    out = []
    for k in keys:
        out.append(sum(1 for p in members[k] if (mask >> p) & 1))
    return tuple(out)


def main() -> None:
    members = orbit_members(N)
    sizes = {k: len(members[k]) for k in ORBIT_ORDER}
    m_mask = members_mask(members, M_KEYS)
    m_cells = stones(m_mask, V)
    quads = forbidden_quads(N)

    # --- quads by orbit-key signature ---
    def qkey(q):
        return tuple(sorted(cell_key(N, *xy(p, N)) for p in q))

    inside_M = []
    touch_M = 0
    phase_inc = Counter()  # (keyA, keyB) pairs in quads with center / B
    for q in quads:
        ks = [cell_key(N, *xy(p, N)) for p in q]
        if all(k in M_KEYS for k in ks):
            inside_M.append(q)
        if any(k in M_KEYS for k in ks):
            touch_M += 1
        if CENTER in q:
            for k in ks:
                if k != (3, 3):
                    phase_inc[("C", k)] += 1
        b_in = [p for p in q if cell_key(N, *xy(p, N)) in PHASE_B]
        if b_in:
            for k in set(ks):
                if k not in PHASE_B:
                    phase_inc[("B", k)] += 1

    # incidence of each orbit key among all quads
    touch = Counter()
    for q in quads:
        for k in {cell_key(N, *xy(p, N)) for p in q}:
            touch[k] += 1

    # --- fractional matching on quads fully inside M ---
    # capacity 1 per vertex; greedy packing + local improvement
    cap = {p: 1.0 for p in m_cells}
    # index quads by vertices
    mset = set(m_cells)
    quads_M = [q for q in inside_M if all(p in mset for p in q)]
    # sort by tightness heuristic: smaller orbit-span first
    def q_span(q):
        ks = {cell_key(N, *xy(p, N)) for p in q}
        return (len(ks), sum(1 for p in q if p == CENTER))

    quads_M_sorted = sorted(quads_M, key=q_span)

    w = [0.0] * len(quads_M_sorted)
    load = {p: 0.0 for p in m_cells}
    # multi-pass greedy: try each edge with weight = min residual on verts
    improved = True
    rounds = 0
    while improved and rounds < 8:
        improved = False
        rounds += 1
        order = sorted(range(len(quads_M_sorted)), key=lambda i: -w[i])
        for i in order:
            q = quads_M_sorted[i]
            residual = min(1.0 - load[p] for p in q)
            if residual > 1e-9:
                w[i] += residual
                for p in q:
                    load[p] += residual
                improved = True
    fm_weight = sum(w)
    used_edges = sum(1 for x in w if x > 1e-9)
    # max load check
    max_load = max(load[p] for p in m_cells)

    # --- census skeleton 13-sets from known A-core pattern ---
    n7 = load_n7()
    # A-core = A sets without center
    a_sets = [s for s in n7 if (s >> CENTER) & 1]
    b_sets = [s for s in n7 if not (s >> CENTER) & 1]
    a_cores = [s & m_mask for s in a_sets]  # should be pop 13
    # B cores: remove (0,3)∪(2,3) stones
    b_bundle = members_mask(members, PHASE_B)
    b_cores = [s & m_mask for s in b_sets]

    # empty-cell blocker analysis on A0 and B0
    from cycle8_lib import triples_by_point

    tbp, _ = triples_by_point(N, quads)

    def blocker_profile(mask: int, label: str) -> dict:
        empty_M = [p for p in m_cells if not (mask >> p) & 1]
        empty_phase = [p for p in stones(members_mask(members, {PHASE_A}) | members_mask(members, PHASE_B) | members_mask(members, {F_KEY}), V) if not (mask >> p) & 1]
        # also all empty board cells
        empty_all = [p for p in range(V) if not (mask >> p) & 1]
        prof = {}
        for p in empty_all:
            fam = [o for o in tbp.get(p, []) if (mask & o) == o]
            k = cell_key(N, *xy(p, N))
            prof[p] = {
                "orbit": k,
                "n_blockers": len(fam),
                "in_M": p in mset,
            }
        return prof

    # --- orbit-pair simultaneous-full incompatibility ---
    # For pairs of M-orbits, can both be fully occupied in some safe set
    # that also contains high occupancy? Use census of max sets + skeleton
    # occ table from Cycle 15 (hardcoded 6 patterns) + probe via is_safe
    # on full-orbit samples.
    from cycle8_lib import is_safe

    pair_full = {}
    for i, ki in enumerate(MANDATORY):
        for kj in MANDATORY[i:]:
            mi = members_mask(members, {ki})
            mj = members_mask(members, {kj})
            pair_full[(ki, kj)] = is_safe(mi | mj, quads)

    # triple full
    triple_full = {}
    for i, ki in enumerate(MANDATORY):
        for j, kj in enumerate(MANDATORY[i + 1 :], start=i + 1):
            for kj2 in MANDATORY[j + 1 :]:
                m = members_mask(members, {ki, kj, kj2})
                triple_full[(ki, kj, kj2)] = is_safe(m, quads)

    # max safe if we try to fill ALL of a single orbit plus greedily?
    # Instead: max occupancy vector search on M via C++ already said 13.
    # Local: for each orbit, how many cells of that orbit appear across
    # all 8 A-cores / B-cores / any known skeleton 13.
    a_core_occ = Counter(occ_on(s, members, MANDATORY) for s in a_cores)
    b_core_occ = Counter(occ_on(s, members, MANDATORY) for s in b_cores)

    # --- incompatibility: center vs B-bundle via named quads ---
    # count quads that use center + >=1 B-bundle cell + >=2 M cells
    c_incompat = []
    for q in quads:
        ks = [cell_key(N, *xy(p, N)) for p in q]
        if (3, 3) in ks and (set(ks) & PHASE_B):
            c_incompat.append(q)

    # quads that use (2,2) + M
    f_quads = [q for q in quads if any(cell_key(N, *xy(p, N)) == F_KEY for p in q)]

    # --- packing certificate refinement ---
    # Try to cover M cells with quads_M using integer hitting via greedy
    # set-cover on the dual: min cells to hit all quads_M (lower bound 23 needed)
    # Actually we need UPPER bound on independent = LOWER bound on transversal.
    # Fractional matching weight W gives α ≤ |M| - W. Report W.
    # Also: count how many quads_M each cell is in (degree in hypergraph)
    deg = Counter()
    for q in quads_M:
        for p in q:
            deg[p] += 1

    # --- why only one skeleton 13-pattern extends by center ---
    # A-core occupancy (2,3,2,1,3,2); test other Cycle15 skeleton patterns
    # by reconstructing *existence* via solver max with force/forbid — skip
    # full search; instead blocker of center on A-core vs a representative
    # of the dominant (2,3,3,1,3,1) class if we can get one from census.
    # We only have max-14 census; skeleton 13 patterns come from C++ occ.
    # Probe: take A0, remove center → A-core; blockers of center = 0.
    # Take a random safe 13 on M if we can build from A-core mutations.

    a0 = a_sets[0]
    a_core = a0 & m_mask
    b0 = b_sets[0]
    b_core = b0 & m_mask

    def blockers_of(mask: int, p: int) -> list:
        return [o for o in tbp.get(p, []) if (mask & o) == o]

    # For every empty cell on A0 / B0, blocker count
    def empty_blockers(mask: int) -> list[tuple]:
        out = []
        for p in range(V):
            if (mask >> p) & 1:
                continue
            fam = blockers_of(mask, p)
            out.append((p, cell_key(N, *xy(p, N)), len(fam)))
        return sorted(out, key=lambda t: -t[2])

    # --- orbit capacity: max stones from each orbit that appear in ANY
    # known safe set at size 13 on M. We don't have the 88 bin; approximate
    # via A-cores (8) and B-cores (8) and note Cycle15 occ table.
    # --- LP-style orbit upper bounds: if orbit O fully occupied together
    # with some other full orbits is unsafe, occupancy of O is limited
    # when others are high.

    # incidence between orbit pairs: # quads that meet both orbits
    pair_inc = Counter()
    for q in quads:
        ks = {cell_key(N, *xy(p, N)) for p in q}
        ks = list(ks)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = sorted((ks[i], ks[j]))
                pair_inc[(a, b)] += 1

    # How many quads_M use only 2 distinct orbits (pure pair pollution)
    pure_pair = Counter()
    pure_one = Counter()
    multi = 0
    for q in quads_M:
        ks = {cell_key(N, *xy(p, N)) for p in q}
        if len(ks) == 1:
            pure_one[list(ks)[0]] += 1
        elif len(ks) == 2:
            pure_pair[tuple(sorted(ks))] += 1
        else:
            multi += 1

    # n=6 analog skeleton: mandatory-like hard orbits from Cycle24
    # forbid (0,2)=0 @11, (0,1)/corners/(1,2) cost 1, (1,1) optional.
    # Compute n=6 orbit sizes + quads inside "hard set" H = orbits that
    # cannot be fully omitted... not the same as n=7 M. For contrast:
    # on n=6, no orbit is empty at max; independence structure differs.
    # We'll record n=6 orbit sizes + quads count for documentation.

    # ---------- write results ----------
    results = {
        "n": N,
        "orbit_sizes": {f"{a},{b}": sizes[(a, b)] for a, b in ORBIT_ORDER},
        "M_cell_count": len(m_cells),
        "n_forbidden_quads_total": len(quads),
        "n_quads_inside_M": len(inside_M),
        "n_quads_touch_M": touch_M,
        "touch_pct_by_orbit": {
            f"{a},{b}": round(100 * touch[(a, b)] / len(quads), 2) for a, b in ORBIT_ORDER
        },
        "phase_inc_center": {
            f"{a},{b}": phase_inc[("C", (a, b))]
            for a, b in ORBIT_ORDER
            if phase_inc[("C", (a, b))]
        },
        "phase_inc_B": {
            f"{a},{b}": phase_inc[("B", (a, b))]
            for a, b in ORBIT_ORDER
            if phase_inc[("B", (a, b))]
        },
        "fractional_matching_weight": round(fm_weight, 4),
        "fractional_matching_edges_used": used_edges,
        "max_vertex_load": round(max_load, 6),
        "implied_alpha_upper": round(len(m_cells) - fm_weight, 4),
        "pair_full_orbit_safe": {f"{a}+{b}": pair_full[(a, b)] for a, b in pair_full},
        "triple_full_orbit_safe_count_ok": sum(1 for v in triple_full.values() if v),
        "triple_full_orbit_unsafe": [
            "+".join(f"{x},{y}" for x, y in k) for k, v in triple_full.items() if not v
        ],
        "a_core_occ_patterns": {str(k): v for k, v in a_core_occ.items()},
        "b_core_occ_patterns": {str(k): v for k, v in b_core_occ.items()},
        "quads_M_pure_pair_top": {
            f"{a}+{b}": c for (a, b), c in pure_pair.most_common(15)
        },
        "quads_M_pure_one": {f"{a},{b}": pure_one[(a, b)] for a, b in pure_one},
        "quads_M_multi_orbit": multi,
        "center_B_incompat_quads": len(c_incompat),
        "quads_touching_22": len(f_quads),
        "a0_empty_blockers_top": empty_blockers(a0)[:12],
        "b0_empty_blockers_top": empty_blockers(b0)[:12],
        "a_core_center_blockers": len(blockers_of(a_core, CENTER)),
        "b_core_center_blockers": len(blockers_of(b_core, CENTER)),
        "hypergraph_deg_min": min(deg[p] for p in m_cells),
        "hypergraph_deg_max": max(deg[p] for p in m_cells),
        "hypergraph_deg_mean": round(sum(deg[p] for p in m_cells) / len(m_cells), 2),
        "pair_inc_M_top": {
            f"{a}+{b}": c
            for (a, b), c in pair_inc.most_common(20)
            if a in M_KEYS or b in M_KEYS
        },
    }

    # named quads for center+B incompat
    named = []
    for q in c_incompat[:8]:
        named.append([xy(p, N) for p in q])
    results["center_B_example_quads_xy"] = named

    out = RES / "cycle30_skeleton_geometry.json"
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    # human summary
    lines = []
    lines.append("# Cycle 30 — skeleton-M geometry certificate (draft)")
    lines.append("")
    lines.append(f"| orbit | size | touch% of {len(quads)} quads |")
    lines.append("|---|---:|---:|")
    for a, b in ORBIT_ORDER:
        lines.append(
            f"| ({a},{b}) | {sizes[(a,b)]} | {results['touch_pct_by_orbit'][f'{a},{b}']} |"
        )
    lines.append("")
    lines.append(f"- |M| = {len(m_cells)} cells; quads fully inside M = {len(inside_M)}")
    lines.append(
        f"- fractional matching on quads_M: weight={fm_weight:.4f}, "
        f"edges_used={used_edges}, max_load={max_load:.4f}"
    )
    lines.append(
        f"- **implied α(M) ≤ {len(m_cells) - fm_weight:.4f}** "
        f"(COMPLETE census says α=13; need weight ≥ 23 for tight bound)"
    )
    lines.append(f"- pure 1-orbit quads in M: {dict(pure_one)}")
    lines.append(f"- pure 2-orbit quads in M (top): {results['quads_M_pure_pair_top']}")
    lines.append(f"- multi-orbit quads in M: {multi}")
    lines.append(
        f"- orbits that can be fully occupied pairwise (is_safe of two full orbits):"
    )
    for k, v in results["pair_full_orbit_safe"].items():
        lines.append(f"  - {k}: {'SAFE' if v else 'UNSAFE'}")
    lines.append(
        f"- triples of full M-orbits that are UNSAFE: {len(results['triple_full_orbit_unsafe'])} / {len(triple_full)}"
    )
    if results["triple_full_orbit_unsafe"]:
        lines.append("  - " + "; ".join(results["triple_full_orbit_unsafe"][:20]))
    lines.append(
        f"- center ∧ B-bundle co-occurring quads: {len(c_incompat)}; examples xy={named[:4]}"
    )
    lines.append(
        f"- A-core center blockers = {results['a_core_center_blockers']} "
        f"(phase A lifts free); B-core center blockers = {results['b_core_center_blockers']}"
    )
    lines.append(f"- A-core M-occupancy patterns: {results['a_core_occ_patterns']}")
    lines.append(f"- B-core M-occupancy patterns: {results['b_core_occ_patterns']}")
    md = NR / "CYCLE30_SKELETON_GEOMETRY.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {out} and {md}")


if __name__ == "__main__":
    main()
