#!/usr/bin/env python3
"""B541-B550: 2-row pair-sum game on {0..m-1} x {0,1}.

Exact characterization (B214): forbidden 4-sets are
  (1) four points in one row (collinear), i.e. |A|>=4 or |B|>=4;
  (2) 2+2 split with a+b = c+d (concyclic).
3+1 splits are never concyclic. 2+2 splits are never collinear.

So a state is (A, B) with A,B subsets of {0..m-1}, |A|,|B| <= 3,
and Sigma2(A) cap Sigma2(B) = empty, where
  Sigma2(S) = {s_i + s_j : i < j}.

Outputs research/verification/round2_b531.json (merged later) or its own
section under key "b541".
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from itertools import combinations
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "round2_b531.json"


def sigma2(t: tuple[int, ...]) -> frozenset[int]:
    return frozenset(t[i] + t[j] for i in range(len(t)) for j in range(i + 1, len(t)))


def pairsum_game(m: int):
    """Return (states, grundy, legal_moves_fn) for 2-row pair-sum game."""

    def legal_children(A: tuple[int, ...], B: tuple[int, ...]):
        sA = sigma2(A)
        sB = sigma2(B)
        out = []
        if len(A) < 3:
            for x in range(m):
                if x in A:
                    continue
                ok = True
                for a in A:
                    if (x + a) in sB:
                        ok = False
                        break
                if ok:
                    nA = tuple(sorted(A + (x,)))
                    out.append((nA, B))
        if len(B) < 3:
            for x in range(m):
                if x in B:
                    continue
                ok = True
                for b in B:
                    if (x + b) in sA:
                        ok = False
                        break
                if ok:
                    nB = tuple(sorted(B + (x,)))
                    out.append((A, nB))
        return out

    memo: dict[tuple, int] = {}

    def g(A: tuple[int, ...], B: tuple[int, ...]) -> int:
        key = (A, B)
        if key in memo:
            return memo[key]
        # iterative-safe: depth <= 6
        ch = legal_children(A, B)
        if not ch:
            memo[key] = 0
            return 0
        seen = {g(a, b) for a, b in ch}
        v = 0
        while v in seen:
            v += 1
        memo[key] = v
        return v

    g((), ())
    return memo, legal_children


def all_safe_states(m: int, memo, legal_children):
    """Enumerate every safe (A,B) (not only reachable-from-empty; all are)."""
    states = []
    for i in range(4):
        for j in range(4):
            for A in combinations(range(m), i):
                for B in combinations(range(m), j):
                    if not (sigma2(A) & sigma2(B)):
                        states.append((A, B))
    return states


def analyze_m(m: int) -> dict:
    memo, legal_children = pairsum_game(m)
    states = all_safe_states(m, memo, legal_children)
    gvals = {}
    for A, B in states:
        gvals[(A, B)] = memo[(A, B)]

    empty_g = memo[((), ())]
    # winning first moves: g({p}) == 0 means after first move opponent is at P
    # first player wins iff empty_g != 0; W = {p : g({p}) == 0}
    win_first = []
    lose_first = []
    for r in (0, 1):
        for x in range(m):
            st = ((x,), ()) if r == 0 else ((), (x,))
            gg = gvals.get(st, memo.get(st))
            if gg == 0:
                win_first.append((r, x))
            else:
                lose_first.append((r, x))

    # maximal states
    maximals = []
    max_sizes = {}
    for A, B in states:
        if not legal_children(A, B):
            sz = len(A) + len(B)
            maximals.append((A, B, sz))
            max_sizes[sz] = max_sizes.get(sz, 0) + 1

    # B541: after any first move, is there a winning reply in the OPPOSITE row?
    # empty is P for m>=6 => every first move is losing for P1; P2 wins by
    # moving to a P-position (g=0). Check opposite-row reply exists with g=0.
    b541_fail = []
    b541_detail = {}
    for r in (0, 1):
        for x in range(m):
            if r == 0:
                A0, B0 = (x,), ()
            else:
                A0, B0 = (), (x,)
            wins_same = []
            wins_opp = []
            for nA, nB in legal_children(A0, B0):
                gg = memo[(nA, nB)]
                if gg == 0:
                    # which row was played?
                    if r == 0:
                        played_opp = nB != B0
                    else:
                        played_opp = nA != A0
                    if played_opp:
                        wins_opp.append((nA, nB))
                    else:
                        wins_same.append((nA, nB))
            key = f"{r}:{x}"
            b541_detail[key] = {
                "n_win_opp": len(wins_opp),
                "n_win_same": len(wins_same),
            }
            if empty_g == 0 and not wins_opp:
                b541_fail.append(key)

    # B543: from any (A,B) with |A|=3,|B|=0 (or sym), game always reaches 6
    # stones. Equiv: every safe (3,k) with k<3 has a child, AND some child path
    # reaches (3,3). Stronger claim in bank: "残り3手で必ず終わる" = cannot get
    # stuck before 6, i.e. every safe (3,k), k<3, has a legal move in the empty row.
    b543_stuck = []
    b543_checked = 0
    for A in combinations(range(m), 3):
        sA = sigma2(A)
        # build all safe B of size 0,1,2
        for k in range(3):
            for B in combinations(range(m), k):
                if sigma2(B) & sA:
                    continue
                b543_checked += 1
                # any legal move in row 1?
                has = False
                for x in range(m):
                    if x in B:
                        continue
                    ok = True
                    for b in B:
                        if (x + b) in sA:
                            ok = False
                            break
                    if ok:
                        has = True
                        break
                if not has:
                    b543_stuck.append((A, B))

    # B545: 2x5 (m=5) 3v3 safe: complete pair-sum separation
    b545 = None
    if m == 5:
        sep = mixed = 0
        mixed_examples = []
        for A in combinations(range(5), 3):
            sA = sigma2(A)
            for B in combinations(range(5), 3):
                if sigma2(B) & sA:
                    continue
                sB = sigma2(B)
                if max(sA) < min(sB) or max(sB) < min(sA):
                    sep += 1
                else:
                    mixed += 1
                    if len(mixed_examples) < 5:
                        mixed_examples.append((list(A), list(B), sorted(sA), sorted(sB)))
        b545 = {
            "n_3v3_safe": sep + mixed,
            "n_separated": sep,
            "n_mixed": mixed,
            "mixed_examples": mixed_examples,
        }

    # B546: for 3v3 safe (A,B), allowed integer shifts t of A (A+t stays in board)
    # such that (A+t, B) still safe. Count connected components of allowed t.
    b546 = None
    if m >= 5:
        comps_list = []
        examples = []
        for A in combinations(range(m), 3):
            sA = sigma2(A)
            for B in combinations(range(m), 3):
                if sigma2(B) & sA:
                    continue
                sB = sigma2(B)
                tmin = -min(A)
                tmax = (m - 1) - max(A)
                allowed = []
                for t in range(tmin, tmax + 1):
                    nA = tuple(sorted(a + t for a in A))
                    if sigma2(nA) & sB:
                        continue
                    allowed.append(t)
                # components of consecutive integers
                comps = 0
                prev = None
                for t in allowed:
                    if prev is None or t != prev + 1:
                        comps += 1
                    prev = t
                comps_list.append(comps)
                if comps >= 3 and len(examples) < 5:
                    examples.append((list(A), list(B), allowed, comps))
        from collections import Counter

        b546 = {
            "n_3v3_safe": len(comps_list),
            "comps_hist": dict(Counter(comps_list)),
            "n_ge3_comps": sum(1 for c in comps_list if c >= 3),
            "examples_ge3": examples,
        }

    # B547: minimal maximal = no legal move AND every proper subset is non-maximal
    # (i.e. has a legal move). Classify by covering condition.
    # For 2-row: maximal iff for every empty cell x in either row, adding x
    # creates a collision or fills to 4. With |A|,|B|<=3 the only way is
    #   |A|=3,|B|=3 (full), or
    #   |A|=3,|B|<3 and every x in empty-row is forbidden by reflections s-b.
    b547 = {
        "minimal_maximal_by_size": {},
        "reflection_cover_ok": 0,
        "reflection_cover_fail": [],
    }
    min_max = []
    for A, B, sz in maximals:
        # check subset-minimal among maximals
        pass
    # subset-minimal maximal: no proper subset (remove one stone) is still maximal
    maxset = set((A, B) for A, B, _ in maximals)
    for A, B, sz in maximals:
        minimal = True
        for i in range(len(A)):
            sub = (A[:i] + A[i + 1 :], B)
            if sub in maxset:
                minimal = False
                break
        if minimal:
            for j in range(len(B)):
                sub = (A, B[:j] + B[j + 1 :])
                if sub in maxset:
                    minimal = False
                    break
        if not minimal:
            continue
        min_max.append((A, B, sz))
        b547["minimal_maximal_by_size"][sz] = (
            b547["minimal_maximal_by_size"].get(sz, 0) + 1
        )
        # reflection-cover characterization:
        # empty cells in row0 forbidden if exists b in B, s in Sigma2(B) with x+b = s
        #   or |A|>=3 (row full)
        # empty cells in row1 similarly.
        # Maximal => every x in 0..m-1 is either in A (occupied) or forbidden.
        sA, sB = sigma2(A), sigma2(B)
        row0_covered = True
        for x in range(m):
            if x in A:
                continue
            if len(A) >= 3:
                break
            # x forbidden in row0 iff exists a in A with x+a in sB
            if not any((x + a) in sB for a in A):
                row0_covered = False
                break
        row1_covered = True
        for x in range(m):
            if x in B:
                continue
            if len(B) >= 3:
                break
            if not any((x + b) in sA for b in B):
                row1_covered = False
                break
        if row0_covered and row1_covered:
            b547["reflection_cover_ok"] += 1
        else:
            if len(b547["reflection_cover_fail"]) < 5:
                b547["reflection_cover_fail"].append((list(A), list(B)))

    # B548/B549: existence of 5-stone maximals, and whether all maximals are 6
    five = [s for s in maximals if s[2] == 5]
    other = [s for s in maximals if s[2] != 6]
    b548 = {
        "n_maximal": len(maximals),
        "size_hist": max_sizes,
        "n_5stone_maximal": len(five),
        "n_non6_maximal": len(other),
        "all_maximal_6": all(s[2] == 6 for s in maximals),
        "example_5": [ (list(a), list(b)) for a, b, _ in five[:8] ],
    }

    # max grundy among all safe states (B544)
    max_g = max(gvals.values()) if gvals else 0
    argmax = [ (list(a), list(b), v) for (a, b), v in gvals.items() if v == max_g ][:5]
    g_hist = {}
    for v in gvals.values():
        g_hist[v] = g_hist.get(v, 0) + 1

    return {
        "m": m,
        "n_states": len(states),
        "empty_g": empty_g,
        "win_first": win_first,
        "lose_first": lose_first,
        "max_g_all_states": max_g,
        "max_g_args": argmax,
        "g_hist": g_hist,
        "b541_fail": b541_fail,
        "b541_detail_sample": {
            k: b541_detail[k] for k in list(b541_detail)[:8]
        },
        "b541_n_fail": len(b541_fail),
        "b543_stuck": [(list(a), list(b)) for a, b in b543_stuck[:10]],
        "b543_n_stuck": len(b543_stuck),
        "b543_checked": b543_checked,
        "b545": b545,
        "b546": b546,
        "b547": b547,
        "b548": b548,
        "n_minimal_maximal": len(min_max),
    }


def b550_probe(m: int, memo, legal_children) -> dict:
    """B550: heuristic probe — do two far-apart columns behave equivalently?
    Compare residual game type after committing one stone at x=0 vs x=m-1
    under translation, via grundy of {p} vs reflected.
    """
    # g({(0,0)}) vs g({(m-1,0)}) — if only endpoints matter these should match
    # after the map x -> m-1-x (board reflection) the game is isomorphic, so
    # this is automatic. A stronger probe: g of (A,B) vs (A+d, B+d) when both
    # fit — interior translation invariance.
    trans_ok = 0
    trans_fail = 0
    fail_ex = []
    for A, B in list(memo.keys()):
        if not A and not B:
            continue
        if max(A + B) < m - 1:
            nA = tuple(a + 1 for a in A)
            nB = tuple(b + 1 for b in B)
            if (nA, nB) in memo and memo[(A, B)] != memo[(nA, nB)]:
                trans_fail += 1
                if len(fail_ex) < 5:
                    fail_ex.append((list(A), list(B), memo[(A, B)], list(nA), list(nB), memo[(nA, nB)]))
            elif (nA, nB) in memo:
                trans_ok += 1
    return {
        "translation_g_invariance_ok": trans_ok,
        "translation_g_invariance_fail": trans_fail,
        "fail_examples": fail_ex,
    }


def main():
    results = {}
    ms = [5, 6, 7, 8, 9, 10, 11, 12]
    if len(sys.argv) > 1:
        ms = [int(a) for a in sys.argv[1:]]
    for m in ms:
        print(f"[pairsum] m={m} ...", flush=True)
        r = analyze_m(m)
        print(
            f"  states={r['n_states']} g0={r['empty_g']} maxg={r['max_g_all_states']} "
            f"maxsizes={r['b548']['size_hist']} b541_fail={r['b541_n_fail']} "
            f"b543_stuck={r['b543_n_stuck']}",
            flush=True,
        )
        results[f"m{m}"] = r

    # translation probe on computed m only
    for m in ms:
        if f"m{m}" not in results:
            continue
        memo, lc = pairsum_game(m)
        results[f"m{m}"]["b550_probe"] = b550_probe(m, memo, lc)
        print(f"  b550 m={m}", results[f"m{m}"]["b550_probe"], flush=True)

    # merge / write
    path = OUT
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("b541_pairsum", {}).update(results)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
