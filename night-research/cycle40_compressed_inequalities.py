#!/usr/bin/env python3
"""Cycle 40 — compress the 120 sum-14 occupancy rejections on skeleton M.

Goal: replace "reject all 120 by search" with a short list of dominant
inequalities / case families. Classify each unrealizable vector by which
COMPLETE subset-max inequality it violates; residual LP-feasible vectors
become an explicit exceptional list.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES

MANDATORY = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 3)]
IDX = {k: i for i, k in enumerate(MANDATORY)}


def key_of(sub) -> str:
    return "+".join(f"{a},{b}" for a, b in sub)


def main() -> None:
    cert = json.loads((RES / "cycle34_occupancy_lattice_certificate.json").read_text(encoding="utf-8"))
    cap = json.loads((RES / "cycle30c_multi_orbit_capacity.json").read_text(encoding="utf-8"))
    un = cert["unrealizable_occ"]
    known13 = {
        "A": (2, 3, 2, 1, 3, 2),
        "dom": (2, 3, 3, 1, 3, 1),
        "Bcore": (3, 1, 2, 1, 3, 1),
        "c1": (2, 2, 3, 1, 3, 2),
        "c2": (3, 2, 2, 1, 3, 2),
        "c3": (3, 2, 3, 1, 3, 1),
        "c4": (3, 3, 3, 1, 0, 1),
    }

    # COMPLETE subset maxima from cycle30c + cycle30b pairs/triples
    # EXCLUDE the full M-set (bound 13) — that is the statement to prove.
    subset_max = {}  # frozenset of indices -> max
    for group in ("4", "5", "6"):
        for k, v in cap.get(group, {}).items():
            if not v.get("complete") or v.get("max") is None:
                continue
            parts = k.split("+")
            idxs = frozenset(IDX[tuple(map(int, p.split(",")))] for p in parts)
            if len(idxs) >= 6:
                continue  # skip full M
            subset_max[idxs] = v["max"]

    # pairs/triples from cycle30b if present
    bpath = RES / "cycle30b_orbit_concyclicity.json"
    if bpath.exists():
        b = json.loads(bpath.read_text(encoding="utf-8"))
        for k, v in b.get("pair_max_M", {}).items():
            if not v.get("complete") or v.get("max") is None:
                continue
            parts = k.split("+")
            idxs = frozenset(IDX[tuple(map(int, p.split(",")))] for p in parts)
            # keep tightest
            subset_max[idxs] = min(subset_max.get(idxs, 99), v["max"])
        for k, v in b.get("triple_max_M", {}).items():
            if not v.get("complete") or v.get("max") is None:
                continue
            parts = k.split("+")
            idxs = frozenset(IDX[tuple(map(int, p.split(",")))] for p in parts)
            subset_max[idxs] = min(subset_max.get(idxs, 99), v["max"])

    # local ceilings
    local = {i: 3 for i in range(6)}

    def violators(occ):
        """List subset-max inequalities violated by occ."""
        out = []
        for S, mx in subset_max.items():
            s = sum(occ[i] for i in S)
            if s > mx:
                out.append((tuple(sorted(S)), s, mx))
        for i, c in local.items():
            if occ[i] > c:
                out.append(((i,), occ[i], c))
        return out

    # sanity: known realizable 13-patterns must violate nothing
    for name, occ in known13.items():
        v = violators(occ)
        if v:
            print("WARNING known13", name, occ, "violates", v, flush=True)

    killed_by_subset = []
    residual = []
    kill_stats = {}
    for occ in un:
        v = violators(occ)
        if v:
            killed_by_subset.append({"occ": occ, "violations": v})
            # attribute to the tightest/most specific
            for S, s, mx in v:
                kill_stats.setdefault((S, mx), []).append(tuple(occ))
        else:
            residual.append(occ)

    # which subset inequalities kill the most
    ranked = sorted(kill_stats.items(), key=lambda kv: -len(kv[1]))
    # greedy cover: which residual would need extra constraints
    # try additional candidate inequalities: all pairs/triples with b = max over known13
    extra_candidates = []
    for r in (2, 3):
        for S in combinations(range(6), r):
            b_known = max(sum(occ[i] for i in S) for occ in known13.values())
            # also try b_known (must hold on known realizable max patterns)
            extra_candidates.append((frozenset(S), b_known, "known13max"))
            # solver-based if we have subset_max
            if frozenset(S) in subset_max:
                extra_candidates.append((frozenset(S), subset_max[frozenset(S)], "solver"))

    # greedy: pick extra ineq that kill residual vectors
    residual_set = [tuple(r) for r in residual]
    chosen = []
    remaining = set(residual_set)
    # prefer inequalities valid on all known13 and killing many residual
    cands = []
    for S, b, src in extra_candidates:
        if any(sum(occ[i] for i in S) > b for occ in known13.values()):
            continue  # invalid on known realizable
        kills = {occ for occ in remaining if sum(occ[i] for i in S) > b}
        if kills:
            cands.append((len(kills), S, b, src, kills))
    cands.sort(reverse=True, key=lambda t: t[0])
    while remaining and cands:
        # recompute best
        best = None
        for i, (nk, S, b, src, kills) in enumerate(cands):
            kills = {occ for occ in remaining if sum(occ[i] for i in S) > b}
            if kills and (best is None or len(kills) > best[0]):
                best = (len(kills), i, S, b, src, kills)
        if best is None:
            break
        nk, i, S, b, src, kills = best
        chosen.append(
            {
                "orbits": [MANDATORY[j] for j in sorted(S)],
                "bound": b,
                "source": src,
                "kills_now": len(kills),
            }
        )
        remaining -= kills
        cands = [c for c in cands if c[1] != S or c[2] != b]

    # integer LP: local + chosen + subset_max → max sum
    from itertools import product

    def feasible(occ) -> bool:
        for i, c in local.items():
            if occ[i] > c:
                return False
        for S, mx in subset_max.items():
            if sum(occ[i] for i in S) > mx:
                return False
        for ch in chosen:
            S = frozenset(IDX[tuple(k)] if False else IDX[(k[0], k[1])] for k in ch["orbits"])
            # orbits stored as lists [x,y]
            S = frozenset(IDX[tuple(o)] for o in ch["orbits"])
            if sum(occ[i] for i in S) > ch["bound"]:
                return False
        return True

    best = 0
    best_occ = None
    n_feas = 0
    n_feas_ge14 = 0
    for occ in product(range(4), repeat=6):
        if not feasible(occ):
            continue
        n_feas += 1
        s = sum(occ)
        if s > best:
            best = s
            best_occ = occ
        if s >= 14:
            n_feas_ge14 += 1

    # classification counts
    n_viol_local = sum(1 for occ in un if any(occ[i] > 3 for i in range(6)))
    results = {
        "n_unrealizable": len(un),
        "n_killed_by_COMPLETE_subset_maxima": len(killed_by_subset),
        "n_residual_LP_feasible": len(residual),
        "residual_occ": residual,
        "top_killing_inequalities": [
            {
                "orbits": [MANDATORY[i] for i in S],
                "bound": mx,
                "n_killed": len(lst),
            }
            for (S, mx), lst in ranked[:20]
        ],
        "extra_chosen": chosen,
        "remaining_after_extra": [list(x) for x in remaining],
        "integer_LP_with_local_plus_subset_plus_extra": {
            "max_sum": best,
            "attainer": best_occ,
            "n_feasible": n_feas,
            "n_feasible_ge14": n_feas_ge14,
        },
        "known13_controls": known13,
        "n_subset_max_inequalities": len(subset_max),
    }
    outp = RES / "cycle40_compressed_inequalities.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Cycle 40 — compress 120 occupancy rejections on M",
        "",
        f"- unrealizable sum-14 vectors: **{len(un)}**",
        f"- killed by COMPLETE subset-max inequalities alone: **{len(killed_by_subset)}**",
        f"- residual (satisfy all known subset maxima + local ceilings): **{len(residual)}**",
        f"- COMPLETE subset-max inequalities available: {len(subset_max)}",
        "",
        "## Top killing inequalities (COMPLETE solver subset maxima)",
        "",
        "| orbits | bound | # of 120 killed |",
        "|---|---:|---:|",
    ]
    for row in results["top_killing_inequalities"][:15]:
        o = ",".join(f"({a},{b})" for a, b in row["orbits"])
        lines.append(f"| {o} | {row['bound']} | {row['n_killed']} |")
    lines += [
        "",
        "## Extra inequalities chosen by greedy cover of residuals",
        "",
        "| orbits | bound | source | kills at pick |",
        "|---|---:|---|---:|",
    ]
    for ch in chosen:
        o = ",".join(f"({a},{b})" for a, b in ch["orbits"])
        lines.append(f"| {o} | {ch['bound']} | {ch['source']} | {ch['kills_now']} |")
    lp = results["integer_LP_with_local_plus_subset_plus_extra"]
    lines += [
        "",
        f"## Integer LP after local + subset-max + extra",
        f"- max sum = **{lp['max_sum']}**, attainer = {lp['attainer']}",
        f"- feasible vectors: {lp['n_feasible']}; with sum≥14: {lp['n_feasible_ge14']}",
        "",
        "## Residual LP-feasible sum-14 vectors (need joint lemmas)",
        "",
    ]
    for occ in residual:
        lines.append(f"- `{occ}` sum={sum(occ)}")
    lines += [
        "",
        "## Lemma draft (Cycle 40)",
        "",
        "> Local ceilings x_i≤3 plus COMPLETE orbit-subset maxima already kill",
        f"> **{len(killed_by_subset)}/{len(un)}** of the sum-14 occupancy vectors.",
        f"> A short extra inequality list covers most residuals; remaining",
        f"> **{len(remaining)}** vectors satisfy every known proper-subset maximum",
        "> yet are COMPLETE-unrealizable on M — these are *emergent* joint",
        "> obstructions and form the compressed exceptional set for a",
        "> human-readable certificate.",
        "",
        f"Artifact: `{outp.name}`",
    ]
    md = NR / "CYCLE40_COMPRESSED_INEQUALITIES.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: results[k] for k in results if k != "residual_occ"}, indent=2)[:3000])
    print("n_residual", len(residual), "remaining_after_extra", len(remaining), "LP max", best)
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
