#!/usr/bin/env python3
"""B445/B446/B448/B450 detail probes on the n=4 same-R families.

Covers:
- B445: covering-responsibility signature separates components?
- B446: stone-removal resilience differs across components?
- B448: G_{k-1} wandering (descend, 1-swap among safe (k-1)-sets, ascend)
  connects the same-R family components?
- B450: fixed shielding stone-groups (intersection of each component)
  that can be transplanted.
"""
from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
OUT = ROOT / "research" / "verification" / "round2_b441.json"


def bits_of(mask: int) -> list[int]:
    return [i for i in range(mask.bit_length() if mask else 0) if (mask >> i) & 1]


def det4(p0, p1, p2, p3) -> int:
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p0, p1, p2, p3
    rows = [
        (x1 * x1 + y1 * y1, x1, y1, 1),
        (x2 * x2 + y2 * y2, x2, y2, 1),
        (x3 * x3 + y3 * y3, x3, y3, 1),
        (x4 * x4 + y4 * y4, x4, y4, 1),
    ]

    def det(rws):
        if len(rws) == 1:
            return rws[0][0]
        s = 0
        for j in range(len(rws[0])):
            minor = [r[:j] + r[j + 1 :] for r in rws[1:]]
            s += ((-1) ** j) * rws[0][j] * det(minor)
        return s

    return det(rows)


def build_quads(n: int) -> list[int]:
    pts = [(x, y) for y in range(n) for x in range(n)]
    quads = []
    for comb in combinations(range(n * n), 4):
        if det4(pts[comb[0]], pts[comb[1]], pts[comb[2]], pts[comb[3]]) == 0:
            m = 0
            for i in comb:
                m |= 1 << i
            quads.append(m)
    return quads


def is_safe(quads: list[int], occ: int) -> bool:
    for q in quads:
        if (occ & q) == q:
            return False
    return True


def blocking_sig(n: int, quads_by_pt: list[list[int]], occ: int) -> tuple:
    """Covering-responsibility signature.

    For every empty point p, record the multiset of sizes of minimal
    subsets T of occ with T∪{p} forbidden. Also record the union of
    stones that appear in any such blocking set (the 'guards' of p).
    """
    parts = []
    n2 = n * n
    guards_total = set()
    for p in range(n2):
        if (occ >> p) & 1:
            continue
        sizes = []
        guards = set()
        for q in quads_by_pt[p]:
            # q is a forbidden quad containing p
            others = q & ~(1 << p)
            if (occ & others) == others:
                # occ completes the quad with p
                sz = others.bit_count()
                sizes.append(sz)
                for v in bits_of(others):
                    guards.add(v)
        if sizes:
            parts.append((p, tuple(sorted(sizes)), tuple(sorted(guards))))
            guards_total |= guards
    return (tuple(parts), tuple(sorted(guards_total)))


def min_remove_to_legalize(quads: list[int], occ: int, illegal: list[int]):
    stones = bits_of(occ)
    for t in range(1, min(4, len(stones)) + 1):
        for rem in combinations(stones, t):
            red = occ
            for b in rem:
                red ^= 1 << b
            for p in illegal:
                nxt = red | (1 << p)
                if is_safe(quads, nxt):
                    return t
    return None


def min_stones_to_change_L(quads: list[int], occ: int):
    """Min removals that change the legal set L(S) at all (either legalize
    a point or (impossible) illegalize — removal only legalizes)."""
    n2 = 16
    L0 = []
    for p in range(n2):
        if (occ >> p) & 1:
            continue
        if is_safe(quads, occ | (1 << p)):
            L0.append(p)
    illegal = [p for p in range(n2) if not (occ >> p) & 1 and p not in L0]
    if not illegal:
        return {"n_illegal": 0, "min_remove": None, "n_L": len(L0)}
    return {
        "n_illegal": len(illegal),
        "n_L": len(L0),
        "min_remove": min_remove_to_legalize(quads, occ, illegal),
    }


def swap_comps(occs, quads, max_swap, n2=16):
    s = set(occs)
    parent = {o: o for o in occs}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for o in occs:
        stones = [i for i in range(n2) if (o >> i) & 1]
        empties = [i for i in range(n2) if not (o >> i) & 1]
        for t in range(1, max_swap + 1):
            for rem in combinations(stones, t):
                base = o
                for b in rem:
                    base ^= 1 << b
                for add in combinations(empties, t):
                    o2 = base
                    for a in add:
                        o2 |= 1 << a
                    if o2 in s and o2 != o:
                        union(o, o2)
    groups = defaultdict(list)
    for o in occs:
        groups[find(o)].append(o)
    return list(groups.values())


def gkminus1_bridge_comps(fam: list[int], quads: list[int], n2=16):
    """Connect family members if they are linked by a path that may wander
    through ANY safe (k-1)-set via 1-swaps (G_{k-1}), then re-ascend."""
    k = fam[0].bit_count()
    # collect all safe (k-1) sets that appear as a subset of some family member
    # PLUS those reachable by 1-swap from those (bounded BFS)
    seeds = set()
    for o in fam:
        for v in bits_of(o):
            seeds.add(o ^ (1 << v))
    # BFS in G_{k-1}: 1-swap among safe (k-1)-sets
    seen = set(seeds)
    frontier = list(seeds)
    while frontier:
        o = frontier.pop()
        stones = [i for i in range(n2) if (o >> i) & 1]
        empties = [i for i in range(n2) if not (o >> i) & 1]
        for s in stones:
            for e in empties:
                o2 = (o ^ (1 << s)) | (1 << e)
                if o2 in seen:
                    continue
                if o2.bit_count() != k - 1:
                    continue
                if is_safe(quads, o2):
                    seen.add(o2)
                    frontier.append(o2)
    # which family members share a seen (k-1) set as subset
    parent = {o: o for o in fam}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    mid_to_fam = defaultdict(list)
    for o in fam:
        for v in bits_of(o):
            mid = o ^ (1 << v)
            if mid in seen:
                mid_to_fam[mid].append(o)
    for mid, mem in mid_to_fam.items():
        for i in range(1, len(mem)):
            union(mem[0], mem[i])
    groups = defaultdict(list)
    for o in fam:
        groups[find(o)].append(o)
    return len(seen), list(groups.values())


def main():
    data = pickle.loads(CACHE.read_bytes())
    n = 4
    quads = build_quads(n)
    quads_by_pt = [[] for _ in range(n * n)]
    for q in quads:
        for i in bits_of(q):
            quads_by_pt[i].append(q)
    print(f"n={n} quads={len(quads)}", flush=True)

    recs = data[n]["recs"]
    by_kr = defaultdict(list)
    for r in recs:
        by_kr[(r["k"], tuple(r["R"]))].append(r)

    # pick multi families sorted by size desc
    fams = [(len(g), k, g) for k, g in by_kr.items() if len(g) >= 2]
    fams.sort(reverse=True)

    out = {"n": n, "n_quads": len(quads), "families": []}

    # Analyze top 12 multi families + the B057 witness (k=5 size 18)
    selected = []
    wit = None
    for sz, k, g in fams:
        if k == 5 and sz == 18:
            wit = (sz, k, g)
    if wit:
        selected.append(wit)
    for item in fams[:12]:
        if wit and item[1] == wit[1] and item[0] == wit[0] and item[2][0]["occ"] == wit[2][0]["occ"]:
            continue
        selected.append(item)

    for sz, key, group in selected:
        occs = [r["occ"] for r in group]
        comps1 = swap_comps(occs, quads, 1)
        comps2 = swap_comps(occs, quads, 2)
        n_gk, comps_gk = gkminus1_bridge_comps(occs, quads)

        # B445 covering-responsibility: do components have different
        # blocking signatures?
        comp_sigs = []
        for comp in comps1:
            ss = {blocking_sig(n, quads_by_pt, o) for o in comp}
            # signature as sorted first elements (stable digest)
            dig = tuple(sorted(str(s)[:200] for s in ss)[:3])
            comp_sigs.append({"n_distinct_sigs": len(ss), "digest": dig[:1]})
        n_distinct_sig_across = len({tuple(sorted(str(s)[:200] for s in {blocking_sig(n, quads_by_pt, o) for o in comp})) for comp in comps1}) if comps1 else 0
        # simpler: union of digests
        all_sig_hashes = []
        for comp in comps1:
            hs = {hash(str(blocking_sig(n, quads_by_pt, o))[:500]) for o in comp}
            all_sig_hashes.append(sorted(hs))
        sig_sets = [frozenset(h) for h in all_sig_hashes]
        sig_overlap = len(set().union(*sig_sets)) if sig_sets else 0
        sig_disjoint = all(
            sig_sets[i].isdisjoint(sig_sets[j])
            for i in range(len(sig_sets))
            for j in range(i + 1, len(sig_sets))
        ) if len(sig_sets) > 1 else True

        # B446 resilience
        res = []
        for comp in comps1[:6]:
            o = comp[0]
            res.append(min_stones_to_change_L(quads, o))

        # B450 fixed shielding: intersection of each component
        inters = []
        for comp in comps1[:6]:
            inter = comp[0]
            for o in comp[1:]:
                inter &= o
            inters.append({"inter": inter, "inter_bits": bits_of(inter), "comp_size": len(comp)})

        # covering responsibility in a finer sense: for each empty p,
        # the set of (guard-size, guard-set-id) — compare mean guard-size
        def guard_profile(o):
            prof = []
            for p in range(n * n):
                if (o >> p) & 1:
                    continue
                gs = []
                for q in quads_by_pt[p]:
                    others = q & ~(1 << p)
                    if (o & others) == others:
                        gs.append(others.bit_count())
                if gs:
                    prof.append(tuple(sorted(gs)))
            return tuple(sorted(prof))

        profs_by_comp = []
        for comp in comps1:
            ps = {guard_profile(o) for o in comp}
            profs_by_comp.append(len(ps))

        out["families"].append(
            {
                "k": key[0],
                "size": len(group),
                "n_comp_1swap": len(comps1),
                "n_comp_2swap": len(comps2),
                "comp_sizes_1": sorted((len(c) for c in comps1), reverse=True),
                "comp_sizes_2": sorted((len(c) for c in comps2), reverse=True),
                "n_gk1_seen": n_gk,
                "n_comp_gk1_bridge": len(comps_gk),
                "comp_sizes_gk1": sorted((len(c) for c in comps_gk), reverse=True),
                "b445_sig_disjoint": sig_disjoint,
                "b445_sig_union": sig_overlap,
                "b445_prof_counts": profs_by_comp[:8],
                "b446_res": res,
                "b446_min_removes": [r.get("min_remove") for r in res],
                "b446_n_illegal": [r.get("n_illegal") for r in res],
                "b450_inters": inters,
                "rep_occ": occs[0],
            }
        )
        print(
            f"k={key[0]} sz={len(group)} c1={len(comps1)} c2={len(comps2)} "
            f"gk1={len(comps_gk)} sig_disj={sig_disjoint} min_rem={[r.get('min_remove') for r in res]}",
            flush=True,
        )

    # merge into existing json
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    prev.setdefault("sections", {})["detail_families_b445_450"] = out
    OUT.write_text(json.dumps(prev, indent=2, default=str))
    print("saved", OUT)


if __name__ == "__main__":
    main()
