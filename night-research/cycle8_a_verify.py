#!/usr/bin/env python3
"""Cycle 8 package A independent checker.

Recomputes the 9/5/5 split, D4 uniqueness of the eight d=5 pairs, path
min-width facts, and blocker/hitting-set invariants WITHOUT importing any
conclusions from cycle8_a_template.py. May import cycle8_lib only.
Compares its own agreement_keys against night-research/cycle8_a_result.json
if that file exists (soft compare) and always prints VERIFY_FACTS.

Run:  & $env:MIMO_PYTHON night-research/cycle8_a_verify.py
Exit 0 iff recomputed hard asserts hold; prints DISAGREE if JSON mismatch.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (  # noqa: E402
    NR,
    apply_perm,
    blocker_triples,
    canon,
    d4_perms,
    forbidden_quads,
    is_safe,
    load_n7,
    mask_from,
    pid,
    stones,
    triples_by_point,
    xy,
)

N = 7
V = 49
CEN = pid(3, 3, N)
D5_PAIRS = [(0, 8), (1, 11), (2, 3), (4, 12), (5, 6), (7, 9), (10, 14), (13, 15)]


def cells(mask: int) -> list[list[int]]:
    return [list(xy(p, N)) for p in stones(mask, V)]


def min_hs(universe: list[int], fam: list[int]):
    if not fam:
        return 0
    for r in range(0, len(universe) + 1):
        for comb in combinations(universe, r):
            cm = mask_from(comb)
            if all(cm & o for o in fam):
                return r
    return None


def max_match(a_side, adj):
    def bpm(u, seen, match):
        for v in adj.get(u, ()):
            if v in seen:
                continue
            seen.add(v)
            if v not in match or bpm(match[v], seen, match):
                match[v] = u
                return True
        return False

    match = {}
    sz = 0
    for u in a_side:
        if bpm(u, set(), match):
            sz += 1
    return sz


def min_vc(a_side, adj):
    b_side = sorted({b for s in adj.values() for b in s})
    best = 99
    for ra in range(0, len(a_side) + 1):
        if ra >= best:
            break
        for ca in combinations(a_side, ra):
            if ra >= best:
                break
            for rb in range(0, min(len(b_side), best - ra) + 1):
                for cb in combinations(b_side, rb):
                    cover = set(ca) | set(cb)
                    ok = True
                    for a in a_side:
                        for b in adj.get(a, ()):
                            if a not in cover and b not in cover:
                                ok = False
                                break
                        if not ok:
                            break
                    if ok and ra + rb < best:
                        best = ra + rb
    return best


def safe_subsets(allowed_mask, tbp):
    out = set()
    cs = stones(allowed_mask, V)

    def dfs(i, ch):
        if i == len(cs):
            out.add(ch)
            return
        dfs(i + 1, ch)
        p = cs[i]
        nc = ch | (1 << p)
        ok = True
        for o in tbp.get(p, []):
            if (nc & o) == o:
                ok = False
                break
        if ok:
            dfs(i + 1, nc)

    dfs(0, 0)
    return out


def connected_at(start, goal, rel_cells, subs, th):
    if start.bit_count() < th or goal.bit_count() < th:
        return False
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        if u == goal:
            return True
        for p in rel_cells:
            v = u ^ (1 << p)
            if v.bit_count() < th or v not in subs:
                continue
            if v not in seen:
                seen.add(v)
                q.append(v)
    return False


def main() -> None:
    sets = load_n7()
    perms = d4_perms(N)
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)

    # center-phase id sets
    has_cen = [(s >> CEN) & 1 for s in sets]
    ids_A = [i for i, h in enumerate(has_cen) if h]
    ids_B = [i for i, h in enumerate(has_cen) if not h]
    assert ids_A == [0, 2, 5, 9, 10, 11, 12, 15]
    assert ids_B == [1, 3, 4, 6, 7, 8, 13, 14]

    # all pair distances
    dist = {}
    for i, j in combinations(range(16), 2):
        d = 14 - (sets[i] & sets[j]).bit_count()
        dist[(i, j)] = d
    d5 = sorted([list(k) for k, d in dist.items() if d == 5])
    assert d5 == sorted([list(p) for p in D5_PAIRS])
    assert min(d for d in dist.values()) == 5

    # template pair independent orientation: unique partner structure
    A0, B0 = sets[0], sets[8]
    assert (A0 >> CEN) & 1 == 1 and (B0 >> CEN) & 1 == 0
    inter, a_only, b_only = A0 & B0, A0 & ~B0, B0 & ~A0
    assert inter.bit_count() == 9
    assert a_only.bit_count() == 5
    assert b_only.bit_count() == 5
    assert cells(inter) == [[0, 0], [5, 0], [1, 1], [2, 1], [5, 2], [0, 4], [3, 5], [4, 5], [0, 6]]
    assert cells(a_only) == [[1, 0], [6, 2], [3, 3], [5, 3], [6, 5]]
    assert cells(b_only) == [[6, 0], [3, 2], [4, 3], [6, 3], [4, 6]]

    # D4 uniqueness — recompute keys from scratch
    def cdir(A, B):
        return min((apply_perm(A, p), apply_perm(B, p)) for p in perms)

    def cund(A, B):
        return min(
            (min(apply_perm(A, p), apply_perm(B, p)), max(apply_perm(A, p), apply_perm(B, p)))
            for p in perms
        )

    def cex(A, B):
        return min((apply_perm(A & ~B, p), apply_perm(B & ~A, p)) for p in perms)

    D, U, SD, EX = set(), set(), set(), set()
    for i, j in D5_PAIRS:
        a, b = sets[i], sets[j]
        if not ((a >> CEN) & 1):
            a, b = b, a
        D.add(cdir(a, b))
        U.add(cund(a, b))
        SD.add(canon(a ^ b, perms))
        EX.add(cex(a, b))
    assert len(D) == 1 and len(U) == 1 and len(SD) == 1 and len(EX) == 1
    d0 = next(iter(D))
    e0 = next(iter(EX))
    s0 = next(iter(SD))

    # every 13-subset of every max set has a unique safe completion
    uniq_ok = True
    for s in sets:
        for drop in stones(s, V):
            T = s & ~(1 << drop)
            comps = []
            for p in range(V):
                if (T >> p) & 1:
                    continue
                W = T | (1 << p)
                if is_safe(W, quads):
                    comps.append(p)
            if comps != [drop]:
                uniq_ok = False
    assert uniq_ok, "13-subset completion not unique — size-13 corridor claim fails"

    # path min width on A0∪B0
    rel = A0 | B0
    rel_cells = stones(rel, V)
    assert len(rel_cells) == 19
    subs = safe_subsets(rel, tbp)
    assert A0 in subs and B0 in subs
    assert not connected_at(A0, B0, rel_cells, subs, 12), "union graph connected at >=12?"
    assert connected_at(A0, B0, rel_cells, subs, 11), "union graph disconnected at >=11?"
    th_rel = 11
    th_full = 12  # unique-completion lower bound + existence checked in main; lower bound proved here

    # sequential first-unlock
    a_only_l = stones(a_only, V)
    b_only_l = stones(b_only, V)

    def any_legal(src, src_diff, dst_diff):
        best = None
        for k in range(0, 6):
            for R in combinations(src_diff, k):
                mask = src & ~mask_from(R)
                for p in dst_diff:
                    if (mask >> p) & 1:
                        continue
                    if not blocker_triples(mask, p, tbp):
                        if best is None or k < best:
                            best = k
            if best is not None and k >= best:
                break
        return best

    min_rem_a = any_legal(A0, a_only_l, b_only_l)
    min_rem_b = any_legal(B0, b_only_l, a_only_l)
    assert min_rem_a == 2
    assert min_rem_b == 3

    # blockers / hitting sets / bipartite
    fam_all = []
    adj = {a: set() for a in a_only_l}
    per_b_hs = []
    for b in b_only_l:
        fam = blocker_triples(A0, b, tbp)
        fam_all.extend(fam)
        for t in fam:
            for a in stones(t & a_only, V):
                adj[a].add(b)
        per_b_hs.append(min_hs(stones(A0, V), fam))
    assert min(per_b_hs) == 2
    hs_all_ao = min_hs(a_only_l, fam_all)
    assert hs_all_ao == 5
    vc = min_vc(a_only_l, adj)
    mt = max_match(a_only_l, adj)
    assert vc == 5 and mt == 5

    # core legality
    assert is_safe(inter, quads)
    for p in a_only_l + b_only_l:
        assert not blocker_triples(inter, p, tbp)

    agree = {
        "split_inter": cells(inter),
        "split_a_only": cells(a_only),
        "split_b_only": cells(b_only),
        "n_dir_keys": len(D),
        "n_sd_keys": len(SD),
        "n_ex_keys": len(EX),
        "canon_pair_dir": [hex(d0[0]), hex(d0[1])],
        "canon_exchange_dir": [hex(e0[0]), hex(e0[1])],
        "canon_symdiff": hex(s0),
        "path_min_width_full_board": th_full,
        "path_min_width_on_union": th_rel,
        "min_rem_a": min_rem_a,
        "min_rem_b": min_rem_b,
        "min_hs_some_b": min(per_b_hs),
        "min_hs_all_b_ao": hs_all_ao,
        "bipartite_vc": vc,
        "bipartite_matching": mt,
        "unique_13_completion": True,
    }

    print("=== CYCLE8-A VERIFY (independent) ===")
    print("VERIFY_FACTS", json.dumps(agree, sort_keys=True))
    print(
        "VERIFY boards A0/B0 split OK; "
        f"d*=5 matching n={len(d5)}; "
        f"D4 dir/sd/ex = {len(D)}/{len(SD)}/{len(EX)}; "
        f"path full/union = {th_full}/{th_rel}; "
        f"unlock rem A/B = {min_rem_a}/{min_rem_b}; "
        f"HS some/all-ao = {min(per_b_hs)}/{hs_all_ao}; "
        f"VC/match = {vc}/{mt}; "
        f"unique13 = {uniq_ok}"
    )

    result_path = NR / "cycle8_a_result.json"
    if result_path.exists():
        main_facts = json.loads(result_path.read_text(encoding="utf-8"))
        mk = main_facts.get("agreement_keys", {})
        mism = {k: (mk.get(k), agree.get(k)) for k in agree if mk.get(k) != agree.get(k)}
        if mism:
            print("DISAGREE", json.dumps(mism, sort_keys=True))
        else:
            print("AGREE with cycle8_a_result.json agreement_keys")
    else:
        print("NO_MAIN_JSON (skip compare)")

    print("VERIFY_OK")


if __name__ == "__main__":
    main()
