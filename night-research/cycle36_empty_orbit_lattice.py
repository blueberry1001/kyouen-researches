#!/usr/bin/env python3
"""Cycle 36 — occupancy-lattice: empty orbit (2,2) at n=7 K=14.

Decision on all 10-orbit occupancy vectors with:
  o_i ≤ 3 for multi-cell orbits, center o∈{0,1}, o_(2,2) ≥ 1, Σ = 14.
If none realizable, (2,2) empty at max is an occupancy-lattice fact.
Also confirm some Σ=13 vectors with o_(2,2)=1 are realizable (controls
from known size-13 witnesses).
"""
from __future__ import annotations

import json
import sys
from itertools import combinations, product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, forbidden_quads, orbit_members, triples_by_point

N = 7
ORDER = [
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
F = (2, 2)
CENTER = (3, 3)


def decide(caps, members, tbp, max_partial=4_000_000):
    keys = [k for k in ORDER if caps.get(k, 0) > 0]
    # include zero-cap keys implicitly skipped
    orbs = sorted(keys, key=lambda k: (caps[k], len(members[k])))
    stats = {"partial": 0, "first": None, "aborted": False}

    def safe_add(mask, p):
        for tr in tbp.get(p, ()):
            if (mask & tr) == tr:
                return False
        return True

    def dfs(i, mask):
        stats["partial"] += 1
        if stats["partial"] > max_partial:
            stats["aborted"] = True
            return False
        if i >= len(orbs):
            stats["first"] = mask
            return True
        k = orbs[i]
        need = caps[k]
        cells = members[k]
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
        "found": found,
        "nodes": stats["partial"],
        "aborted": stats["aborted"],
        "first_hex": hex(stats["first"]) if stats["first"] else None,
        "sum": sum(caps[k] for k in ORDER),
        "caps": {f"{a},{b}": caps.get((a, b), 0) for a, b in ORDER},
    }


def main() -> None:
    members = orbit_members(N)
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)

    # ceilings
    ceil = {}
    for k in ORDER:
        sz = len(members[k])
        ceil[k] = 1 if k == CENTER else min(3, sz)

    # enumerate sum=14 with o_F>=1
    vectors_14 = []
    for vals in product(range(4), repeat=9):  # all but center
        # map: first 7 are 00..13, then 22, 23 — wait ORDER without center
        pass
    # explicit: iterate all 10 with product of ranges
    ranges = []
    for k in ORDER:
        if k == CENTER:
            ranges.append(range(2))  # 0 or 1
        else:
            ranges.append(range(4))  # 0..3
    n14 = n14_found = n14_abort = 0
    unreal14 = []
    for vals in product(*ranges):
        if sum(vals) != 14:
            continue
        if vals[ORDER.index(F)] < 1:
            continue
        n14 += 1
        caps = {ORDER[i]: vals[i] for i in range(10)}
        r = decide(caps, members, tbp)
        if r["aborted"]:
            n14_abort += 1
        elif r["found"]:
            n14_found += 1
            print("sum14 with (2,2) FOUND", vals, r["nodes"], flush=True)
        else:
            unreal14.append(list(vals))
        if n14 % 20 == 0:
            print(f"... tested {n14} sum14-with-F vectors", flush=True)

    # controls: sum=13 with o_F=1, sample a few (not exhaustive)
    controls = []
    # A phase does not use (2,2); try vector = drop one stone from a known 13-with-F
    # Use: fill many orbits at ceiling but o_F=1, sum=13
    sample_caps_list = []
    # all ceiling except reduce to sum 13 with F=1
    base = dict(ceil)
    base[F] = 1
    # reduce others to sum 13
    s = sum(base.values())
    # trim from largest orbits
    while s > 13:
        for k in [(0, 1), (0, 2), (1, 2), (0, 0), (0, 3), (1, 1), (1, 3), (2, 3)]:
            if s <= 13:
                break
            if base[k] > 0:
                base[k] -= 1
                s -= 1
    sample_caps_list.append(base)
    # another: B-like but with F=1 instead of some B stones
    b_like = {
        (0, 0): 3,
        (0, 1): 1,
        (0, 2): 2,
        (0, 3): 1,
        (1, 1): 1,
        (1, 2): 3,
        (1, 3): 1,
        F: 1,
        (2, 3): 0,
        CENTER: 0,
    }
    sample_caps_list.append(b_like)
    for caps in sample_caps_list:
        r = decide(caps, members, tbp)
        controls.append({"caps": r["caps"], "sum": r["sum"], **{k: r[k] for k in ("found", "nodes", "aborted")}})
        print("control sum", r["sum"], "F", caps[F], "found", r["found"], r["nodes"], flush=True)

    results = {
        "n_sum14_with_22_ge1": n14,
        "n_found": n14_found,
        "n_aborted": n14_abort,
        "n_unrealizable": len(unreal14),
        "unrealizable_sample": unreal14[:30],
        "controls_sum13_with_22": controls,
        "conclusion": (
            "COMPLETE: no sum-14 occupancy with (2,2)≥1 is realizable on 7×7"
            if n14_found == 0 and n14_abort == 0 and n14 > 0
            else "incomplete"
        ),
    }
    outp = RES / "cycle36_empty_orbit_lattice.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Cycle 36 — empty (2,2) via occupancy lattice (n=7)",
        "",
        f"- sum=14 vectors with o_(2,2)≥1 and o_i≤ceil: **{n14}**",
        f"- realizable: **{n14_found}**; aborted: **{n14_abort}**; unrealizable: **{len(unreal14)}**",
        f"- conclusion: {results['conclusion']}",
        "",
        "Controls (sum=13 with o_(2,2)=1):",
    ]
    for c in controls:
        lines.append(f"  - sum={c['sum']} found={c['found']} nodes={c['nodes']} aborted={c['aborted']}")
    lines += ["", f"Artifact: `{outp.name}`"]
    md = NR / "CYCLE36_EMPTY_ORBIT_LATTICE.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(results["conclusion"])
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
