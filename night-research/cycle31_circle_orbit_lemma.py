#!/usr/bin/env python3
"""Cycle 31 — D4-orbit circle lemma + occupancy-cap search on skeleton M.

Lemma (first principles): every D4-orbit on an odd n×n grid lies on a
circle centered at the board center (D4 preserves radius). Hence any
orbit with ≥4 cells is concyclic, hence occupancy ≤ 3 in a safe set.

Then: which occupancy vectors on M that satisfy local ceilings and
COMPLETE subset maxima still cannot reach 14?
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (
    NR,
    RES,
    forbidden_quads,
    mask_from,
    orbit_members,
    stones,
    triples_by_point,
    cell_key,
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


def orbit_radius_info(n: int):
    """For each D4 orbit key, members and r^2 from board center."""
    members = orbit_members(n)
    c = n // 2
    out = {}
    for k, pts in sorted(members.items()):
        r2s = set()
        coords = []
        for p in pts:
            x, y = p % n, p // n
            coords.append((x, y))
            r2s.add((x - c) ** 2 + (y - c) ** 2)
        out[f"{k[0]},{k[1]}"] = {
            "size": len(pts),
            "pts": coords,
            "r2_set": sorted(r2s),
            "on_one_circle": len(r2s) == 1,
        }
    return out


def all_orbits_circle(n: int) -> dict:
    return orbit_radius_info(n)


def search_occ_cap(
    m_cells: list[int],
    quads: list,
    tbp: dict,
    orbit_of: dict[int, tuple],
    caps: dict[tuple, int],
    target: int,
    max_nodes: int = 2_000_000,
) -> dict:
    """Max safe subset of m_cells with occ[orbit] ≤ caps[orbit]."""
    mset = set(m_cells)
    # order cells: high-degree first for earlier pruning? Actually take
    # cells in orbit order matching caps to fill cheap orbits first.
    order = sorted(m_cells, key=lambda p: (orbit_of[p], -len(tbp.get(p, ()))))
    cap_of = {p: caps[orbit_of[p]] for p in m_cells}
    used = defaultdict(int)
    best = {"size": 0, "count": 0, "first": None}
    nodes = [0]
    # remaining count per orbit for bound
    rem_orb = defaultdict(int)
    for p in m_cells:
        rem_orb[orbit_of[p]] += 1

    def dfs(i: int, mask: int, size: int) -> None:
        nodes[0] += 1
        if nodes[0] > max_nodes:
            return
        if size > best["size"]:
            best["size"] = size
            best["count"] = 1
            best["first"] = mask
        elif size == best["size"] and mask:
            best["count"] += 1
        if i >= len(order):
            return
        # optimistic bound
        room = size
        # cells left
        left = order[i:]
        # cap-limited room
        occ_left = defaultdict(int)
        for p in left:
            o = orbit_of[p]
            if used[o] + occ_left[o] < cap_of[p]:
                occ_left[o] += 1
        room += sum(occ_left.values())
        if room <= best["size"] and best["size"] >= target:
            return
        if room < best["size"]:
            return

        p = order[i]
        o = orbit_of[p]
        # skip p
        dfs(i + 1, mask, size)
        # take p if cap and safe (no triple in mask completing a quad)
        if used[o] < cap_of[p]:
            ok = True
            for tr in tbp.get(p, ()):
                if (mask & tr) == tr:
                    ok = False
                    break
            if ok:
                used[o] += 1
                dfs(i + 1, mask | (1 << p), size + 1)
                used[o] -= 1

    dfs(0, 0, 0)
    return {
        "max": best["size"],
        "count_at_max": best["count"],
        "nodes": nodes[0],
        "complete": nodes[0] <= max_nodes and best["size"] >= 0,
        "first_hex": hex(best["first"]) if best["first"] else None,
        "target": target,
        "reached_target": best["size"] >= target,
        "caps": {f"{a},{b}": c for (a, b), c in caps.items()},
    }


def main() -> None:
    # --- circle lemma for n=5,6,7,8 ---
    circle = {n: all_orbits_circle(n) for n in (5, 6, 7, 8)}
    summary = {}
    for n, info in circle.items():
        on_circle = sum(1 for v in info.values() if v["on_one_circle"])
        multi = sum(1 for v in info.values() if not v["on_one_circle"] and v["size"] >= 2)
        size_ge4_one_circle = sum(
            1 for v in info.values() if v["size"] >= 4 and v["on_one_circle"]
        )
        summary[n] = {
            "n_orbits": len(info),
            "on_single_circle": on_circle,
            "multi_radius_or_size_lt2": multi,
            "size>=4_on_circle": size_ge4_one_circle,
        }

    members = orbit_members(N)
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)
    m_mask = 0
    for k in MANDATORY:
        for p in members[k]:
            m_mask |= 1 << p
    m_cells = stones(m_mask, V)
    orbit_of = {}
    for k in ORBIT_ORDER:
        for p in members[k]:
            orbit_of[p] = k

    # LP attainer from 30c that reaches 14 under local+4-orbit caps
    attainer = {(0, 0): 2, (0, 1): 2, (0, 2): 3, (1, 1): 1, (1, 2): 3, (1, 3): 3}
    # also try A-m and B-m patterns and a few near-miss 14-vectors
    trials = {
        "lp14_attainer": attainer,
        "A_on_M": {(0, 0): 2, (0, 1): 3, (0, 2): 2, (1, 1): 1, (1, 2): 3, (1, 3): 2},
        "B_on_M": {(0, 0): 3, (0, 1): 1, (0, 2): 2, (1, 1): 1, (1, 2): 3, (1, 3): 1},
        "all3_except_11_1": {(0, 0): 3, (0, 1): 3, (0, 2): 3, (1, 1): 1, (1, 2): 3, (1, 3): 3},
        "all3_except_11_0": {(0, 0): 3, (0, 1): 3, (0, 2): 3, (1, 1): 0, (1, 2): 3, (1, 3): 3},
        "cycle15_dom": {(0, 0): 2, (0, 1): 3, (0, 2): 3, (1, 1): 1, (1, 2): 3, (1, 3): 1},
    }

    occ_results = {}
    for name, caps in trials.items():
        # search max under these caps (target 14)
        r = search_occ_cap(m_cells, quads, tbp, orbit_of, caps, target=14, max_nodes=1_500_000)
        occ_results[name] = r
        print(name, r["max"], r["nodes"], r["caps"], flush=True)

    # Also: max under local ceiling 3 only (no finer caps) — should be 13
    ceil3 = {k: 3 for k in MANDATORY}
    r3 = search_occ_cap(m_cells, quads, tbp, orbit_of, ceil3, target=14, max_nodes=2_000_000)
    occ_results["local_ceiling_3_only"] = r3
    print("ceil3", r3["max"], r3["nodes"], flush=True)

    results = {
        "circle_summary": summary,
        "n7_orbit_radii": circle[7],
        "occ_cap_search": occ_results,
        "m_cell_count": len(m_cells),
    }
    outp = RES / "cycle31_circle_lemma_occ.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Cycle 31 — D4 orbit circle lemma + occupancy-cap search",
        "",
        "## Lemma (first principles, all odd n)",
        "",
        "> The dihedral group D4 acting on an odd n×n board preserves",
        "> Euclidean distance from the board center. Therefore **every D4-orbit",
        "> lies on a single circle centered at the board center**.",
        "> Any 4 points on a circle are concyclic, hence form a forbidden",
        "> kyouen 4-set. Consequently **every orbit with ≥4 cells has",
        "> occupancy ≤ 3 in any safe set**.",
        "",
        "This is a geometric proof of the local ceiling used in Cycle 30 —",
        "it does not require census data.",
        "",
        "## Orbit radii (COMPLETE)",
        "",
    ]
    for n, info in circle.items():
        lines.append(f"### n={n} ({summary[n]})")
        lines.append("| orbit | size | r² from center | on one circle |")
        lines.append("|---|---:|---|---|")
        for k, v in info.items():
            lines.append(
                f"| ({k}) | {v['size']} | {v['r2_set']} | {v['on_one_circle']} |"
            )
        lines.append("")

    lines += [
        "## n=7 skeleton M occupancy-cap search",
        "",
        "Caps are per-orbit maxima. COMPLETE when nodes finished.",
        "",
        "| trial | caps | max seen | nodes | reached 14? |",
        "|---|---|---:|---:|---|",
    ]
    for name, r in occ_results.items():
        lines.append(
            f"| {name} | {r['caps']} | {r['max']} | {r['nodes']} | {r['reached_target']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Circle lemma ⇒ local occ≤3 on every multi-cell orbit (why n-boards",
        "  cannot pack more than ~3 per radial shell).",
        "- COMPLETE solver: α(M)=13 despite local ceilings summing to 18.",
        "- 4-orbit COMPLETE maxima still allow an integer occupancy vector",
        "  summing to 14 (Cycle 30c LP). Occupancy-cap search tests whether",
        "  that vector is geometrically realizable on M.",
        "",
        "## Artifacts",
        "- `results/cycle31_circle_lemma_occ.json`",
        "- `night-research/CYCLE30B_ORBIT_CONCYCLICITY.md`",
        "- `night-research/CYCLE30C_MULTI_ORBIT_CAPACITY.md`",
    ]
    md = NR / "CYCLE31_CIRCLE_ORBIT_LEMMA.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
