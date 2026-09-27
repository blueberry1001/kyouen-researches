#!/usr/bin/env python3
"""Batch 06 follow-ups v2: fix cover analysis; analyze outside-12 components."""
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
)

RES = ROOT / "results"
OUT = ROOT / "research" / "verification" / "batch06_followups2.json"


def popcount(x: int) -> int:
    return bin(x).count("1")


def load_quads7():
    cache_q = ROOT / "research" / "verification" / "batch06_quads_cache.json"
    return [tuple(q) for q in json.loads(cache_q.read_text())["n7"]]


def quads_to_masks(quads):
    out = []
    for q in quads:
        m = 0
        for p in q:
            m |= 1 << p
        out.append(m)
    return out


def is_safe_mask(m, quad_masks):
    for qm in quad_masks:
        if (m & qm) == qm:
            return False
    return True


def fix_cover():
    sc = json.loads((RES / "discovery_corridor_static_certificate.json").read_text())
    a_mask, b_mask = sc["a"], sc["b"]
    cells = sc["cells"]  # 19 board point ids
    p_pts = set(stones(a_mask & ~b_mask, 49))
    q_pts = set(stones(b_mask & ~a_mask, 49))
    u_pts = cells  # list of 19
    quads7 = load_quads7()
    u_set = set(u_pts)
    u_quads = [q for q in quads7 if all(p in u_set for p in q)]
    u_quad_masks = quads_to_masks(u_quads)

    # candidates: ALL S⊆U, |S|>=13, d(S) in {2,3}  (not necessarily safe)
    candidates = []
    for sz in range(13, 20):
        for comb in combinations(u_pts, sz):
            d = sum(1 for p in comb if p in q_pts) - sum(1 for p in comb if p in p_pts)
            if d in (2, 3):
                m = 0
                for p in comb:
                    m |= 1 << p
                candidates.append(m)

    # interpret covering_quads as bitmasks over the 19-cell index
    cover_board_masks = []
    for cq in sc["covering_quads"]:
        m = 0
        bits = stones(cq, 19)
        for b in bits:
            m |= 1 << cells[b]
        cover_board_masks.append(m)
    # also try direct board-point interpretation
    cover_direct = list(sc["covering_quads"])

    def hits(cm, cand):
        return (cand & cm) == cm

    def covers_all(subset):
        return all(any(hits(qm, c) for qm in subset) for c in candidates)

    ok_index = covers_all(cover_board_masks) if candidates else None
    ok_direct = covers_all(cover_direct) if candidates else None

    # verify each cover quad is an actual U-forbidden quad
    u_qset = set(u_quad_masks)
    index_are_real = set(cover_board_masks) <= u_qset
    direct_are_real = set(cover_direct) <= u_qset

    # 1-minimal shrink on whichever interpretation works
    result = {
        "n_candidates": len(candidates),
        "n_candidates_certificate": sc["candidate_count"],
        "n_u_quads": len(u_quads),
        "cover_index_interp_ok": ok_index,
        "cover_direct_interp_ok": ok_direct,
        "index_are_real_U_quads": index_are_real,
        "direct_are_real_U_quads": direct_are_real,
    }

    working = None
    if ok_index:
        working = cover_board_masks
    elif ok_direct:
        working = cover_direct
    if working is not None:
        current = list(working)
        changed = True
        while changed:
            changed = False
            for i in range(len(current)):
                sub = current[:i] + current[i + 1 :]
                if covers_all(sub):
                    current = sub
                    changed = True
                    break
        result["min_1minimal_size"] = len(current)
        # single removals from original
        single_ok = any(
            covers_all(working[:i] + working[i + 1 :]) for i in range(len(working))
        )
        result["single_removal_suffices"] = single_ok
        # pair removals
        pair = None
        for i, j in combinations(range(len(working)), 2):
            sub = [working[k] for k in range(len(working)) if k not in (i, j)]
            if covers_all(sub):
                pair = [i, j]
                break
        result["pair_removal"] = pair
    return result


def analyze_outside_components(n_max=5, max_component_size=20000):
    """Grow G_12 components from safe 12-sets outside the 903 D4-orbit."""
    quads7 = load_quads7()
    quad_masks = quads_to_masks(quads7)
    perms = d4_perms(7)

    d_full = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    closed903 = d_full["closed_set"]
    orbit = set()
    for m in closed903:
        for p in perms:
            orbit.add(apply_perm(m, p))

    # find outside 12-sets
    v = 49
    tbp = defaultdict(list)
    for qm in quad_masks:
        qpts = stones(qm, v)
        for t in qpts:
            tbp[t].append(qm & ~(1 << t))

    found = []

    def dfs(start, chosen, count, cand, ccount):
        if len(found) >= n_max:
            return
        if count == 12:
            if chosen not in orbit:
                found.append(chosen)
            return
        if not cand or count + cand.bit_count() < 12:
            return
        cand2 = cand & ~((1 << start) - 1)
        if not cand2:
            return
        u = (cand2 & -cand2).bit_length() - 1
        dfs(start, chosen, count, cand2 & ~(1 << u), ccount)
        newcand = cand2 & ~(1 << u)
        undo = []
        ok = True
        for o in tbp.get(u, []):
            if bin(o & chosen).count("1") == 2:
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

    dfs(0, 0, 0, (1 << v) - 1, [0] * v)
    print(f"found {len(found)} outside 12-sets", flush=True)

    # BFS each seed's G_12 component (bounded)
    results = []
    for seed in found[:n_max]:
        if seed in orbit:
            continue
        seen = {seed}
        q = deque([seed])
        while q and len(seen) < max_component_size:
            m = q.popleft()
            # removals
            for r in stones(m, v):
                t = m & ~(1 << r)
                if popcount(t) >= 12 and t not in seen:
                    if is_safe_mask(t, quad_masks):
                        seen.add(t)
                        q.append(t)
            # adds
            for a in range(v):
                if (m >> a) & 1:
                    continue
                t = m | (1 << a)
                if t not in seen:
                    if is_safe_mask(t, quad_masks):
                        seen.add(t)
                        q.append(t)
        layers = Counter(popcount(m) for m in seen)
        has14 = any(popcount(m) == 14 for m in seen)
        results.append(
            {
                "seed": seed,
                "seed_board": stones(seed, 49),
                "component_size": len(seen),
                "layers": dict(sorted(layers.items())),
                "reaches_14": has14,
                "reaches_13": any(popcount(m) == 13 for m in seen),
                "max_size_in_component": max(layers) if layers else None,
                "overlaps_903_orbit": any(m in orbit for m in seen),
            }
        )
        print("component:", results[-1], flush=True)
    return {"n_seeds": len(found), "components": results}


def main():
    cover = fix_cover()
    print("cover:", json.dumps(cover, indent=2), flush=True)
    other = analyze_outside_components()
    print("other:", json.dumps(other, indent=2, default=str), flush=True)
    OUT.write_text(
        json.dumps({"B116_cover": cover, "B112_B119": other}, indent=2, default=str)
    )
    print("wrote", OUT)


if __name__ == "__main__":
    main()
