#!/usr/bin/env python3
"""Cycle 34 — COMPLETE occupancy-lattice certificate for α(M)=13.

Enumerate every occupancy vector on the six M-orbits with
0 ≤ o_i ≤ 3 (orbit-circle local ceiling) and sum = 14,
and decide realizability on M by exact-orbit combination search.
If none is realizable, α(M) ≤ 13 without invoking the full K=14 census.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations, product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, forbidden_quads, orbit_members, triples_by_point

N = 7
MANDATORY = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 3)]


def realize(caps: dict, members, tbp, max_partial: int = 5_000_000) -> dict:
    orbs = sorted(MANDATORY, key=lambda k: (caps[k], len(members[k])))
    orb_cells = {k: members[k] for k in MANDATORY}
    stats = {"partial": 0, "first": None, "aborted": False}

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
        "found": found,
        "nodes": stats["partial"],
        "aborted": stats["aborted"],
        "first_hex": hex(stats["first"]) if stats["first"] else None,
    }


def main() -> None:
    members = orbit_members(N)
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)

    vectors = []
    for vals in product(range(4), repeat=6):
        if sum(vals) == 14:
            vectors.append(vals)
    print(f"sum=14 vectors with o<=3: {len(vectors)}", flush=True)

    realizable = []
    unrealizable = []
    aborted = []
    for vals in vectors:
        caps = {MANDATORY[i]: vals[i] for i in range(6)}
        r = realize(caps, members, tbp)
        rec = {
            "occ": list(vals),
            "occ_str": ",".join(str(v) for v in vals),
            "nodes": r["nodes"],
            "aborted": r["aborted"],
            "found": r["found"],
            "first_hex": r["first_hex"],
        }
        if r["aborted"]:
            aborted.append(rec)
        elif r["found"]:
            realizable.append(rec)
        else:
            unrealizable.append(rec)
        print(
            f"occ={rec['occ_str']} found={r['found']} nodes={r['nodes']} aborted={r['aborted']}",
            flush=True,
        )

    # also confirm known sum-13 patterns exist
    known13 = {
        "A": (2, 3, 2, 1, 3, 2),
        "dom": (2, 3, 3, 1, 3, 1),
        "Bcore": (3, 1, 2, 1, 3, 1),
    }
    known = {}
    for name, vals in known13.items():
        caps = {MANDATORY[i]: vals[i] for i in range(6)}
        r = realize(caps, members, tbp)
        known[name] = {"occ": list(vals), **r}
        print("known13", name, r["found"], r["nodes"], flush=True)

    results = {
        "n_sum14_vectors": len(vectors),
        "n_realizable": len(realizable),
        "n_unrealizable": len(unrealizable),
        "n_aborted": len(aborted),
        "realizable": realizable,
        "unrealizable_occ": [r["occ"] for r in unrealizable],
        "aborted": aborted,
        "known_sum13": known,
        "conclusion": (
            "COMPLETE occupancy-lattice certificate: α(M)≤13"
            if len(realizable) == 0 and len(aborted) == 0
            else "incomplete" if aborted or realizable else "unexpected"
        ),
    }
    outp = RES / "cycle34_occupancy_lattice_certificate.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Cycle 34 — COMPLETE occupancy-lattice certificate for α(M)=13",
        "",
        "Local orbit–circle ceiling: each M-orbit occupancy o_i ∈ {0,1,2,3}.",
        f"There are **{len(vectors)}** occupancy vectors with Σ o_i = 14.",
        "Each is decided by exact-orbit combination search on M (COMPLETE if not aborted).",
        "",
        f"- realizable sum-14 vectors: **{len(realizable)}**",
        f"- unrealizable: **{len(unrealizable)}**",
        f"- aborted: **{len(aborted)}**",
        "",
        "### Known sum-13 controls",
        "",
    ]
    for name, r in known.items():
        lines.append(f"- {name} occ={r['occ']}: found={r['found']} nodes={r['nodes']}")
    lines += [
        "",
        "### Lemma",
        "",
        "> **Cycle 34 occupancy-lattice lemma (COMPLETE if aborted=0 and realizable=0).**",
        "> On the six-orbit skeleton M of the 7×7 board, every safe set satisfies",
        "> o_i ≤ 3 by the orbit–circle lemma. No occupancy vector with Σ o_i = 14",
        "> and o_i ≤ 3 is realizable. Hence **α(M) ≤ 13**. Together with the COMPLETE",
        "> witness α(M)=13 (solver max / Cycle 15), α(M)=13 is explained by",
        "> *local circle ceilings + cross-shell incompatibility of high occupancies*,",
        "> not by the full-board K=14 census.",
        "",
        f"Artifact: `{outp.name}`",
    ]
    md = NR / "CYCLE34_OCCUPANCY_LATTICE_CERTIFICATE.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(results["conclusion"])
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
