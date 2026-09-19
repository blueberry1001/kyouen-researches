#!/usr/bin/env python3
"""Cycle 33 — decision search: can occupancy vector sum-14 be realized on M?

Uses orbit-by-orbit exact occupancy with early quad pruning.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, forbidden_quads, mask_from, orbit_members, stones, triples_by_point

N = 7
V = N * N
MANDATORY = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 3)]


def realize(caps: dict, members, quads, max_partial: int = 50_000_000) -> dict:
    """Exact occupancy caps on M-orbits; return whether a safe set exists."""
    tbp, _ = triples_by_point(N, quads)
    # order orbits: smallest choose-count first
    orbs = sorted(MANDATORY, key=lambda k: (caps[k], len(members[k])))
    # precompute cells
    orb_cells = {k: members[k] for k in MANDATORY}
    stats = {"partial": 0, "complete_sets": 0, "first": None, "aborted": False}

    def safe_add(mask: int, p: int) -> bool:
        for tr in tbp.get(p, ()):
            if (mask & tr) == tr:
                return False
        return True

    def dfs(i: int, mask: int) -> bool:
        stats["partial"] += 1
        if stats["partial"] > max_partial:
            stats["aborted"] = True
            return False
        if i >= len(orbs):
            stats["complete_sets"] += 1
            stats["first"] = mask
            return True
        k = orbs[i]
        need = caps[k]
        cells = orb_cells[k]
        if need == 0:
            return dfs(i + 1, mask)
        if need > len(cells):
            return False
        for comb in combinations(cells, need):
            m2 = mask
            ok = True
            for p in comb:
                if not safe_add(m2, p):
                    ok = False
                    break
                m2 |= 1 << p
            if ok and dfs(i + 1, m2):
                return True
        return False

    found = dfs(0, 0)
    return {
        "caps": {f"{a},{b}": caps[(a, b)] for a, b in MANDATORY},
        "sum": sum(caps[k] for k in MANDATORY),
        "found_safe": found,
        "partial_nodes": stats["partial"],
        "aborted": stats["aborted"],
        "first_hex": hex(stats["first"]) if stats["first"] else None,
    }


def main() -> None:
    members = orbit_members(N)
    # restrict members to M orbits only (they already are)
    quads = forbidden_quads(N)
    trials = {
        "lp14_attainer": {(0, 0): 2, (0, 1): 2, (0, 2): 3, (1, 1): 1, (1, 2): 3, (1, 3): 3},
        "A_on_M": {(0, 0): 2, (0, 1): 3, (0, 2): 2, (1, 1): 1, (1, 2): 3, (1, 3): 2},
        "B_on_M": {(0, 0): 3, (0, 1): 1, (0, 2): 2, (1, 1): 1, (1, 2): 3, (1, 3): 1},
        "dom32": {(0, 0): 2, (0, 1): 3, (0, 2): 3, (1, 1): 1, (1, 2): 3, (1, 3): 1},
        "alt14_a": {(0, 0): 3, (0, 1): 3, (0, 2): 2, (1, 1): 1, (1, 2): 3, (1, 3): 2},
        "alt14_b": {(0, 0): 3, (0, 1): 2, (0, 2): 3, (1, 1): 1, (1, 2): 3, (1, 3): 2},
        "alt14_c": {(0, 0): 2, (0, 1): 3, (0, 2): 3, (1, 1): 0, (1, 2): 3, (1, 3): 3},
        "alt14_d": {(0, 0): 3, (0, 1): 2, (0, 2): 2, (1, 1): 1, (1, 2): 3, (1, 3): 3},
    }
    results = {}
    for name, caps in trials.items():
        r = realize(caps, members, quads)
        results[name] = r
        print(name, "sum", r["sum"], "found", r["found_safe"], "nodes", r["partial_nodes"], "aborted", r["aborted"], flush=True)

    outp = RES / "cycle33_spurious_occ_decision.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Cycle 33 — exact-occupancy decision on skeleton M",
        "",
        "Orbit-by-orbit combination search (COMPLETE if not aborted).",
        "",
        "| trial | occ sum | safe set exists? | nodes | aborted |",
        "|---|---:|---|---:|---|",
    ]
    for name, r in results.items():
        lines.append(
            f"| {name} | {r['sum']} | {r['found_safe']} | {r['partial_nodes']} | {r['aborted']} |"
        )
    lines += [
        "",
        "Known COMPLETE: A_on_M and dom32 realize size-13 skeleton patterns",
        "(must be found). Sum-14 vectors that are never realized document the",
        "cross-shell obstruction beyond local ceilings and 4-orbit maxima.",
        "",
        f"Artifact: `{outp}`",
    ]
    md = NR / "CYCLE33_SPURIOUS_OCC_DECISION.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
