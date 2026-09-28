#!/usr/bin/env python3
"""Round3 chunk6 group A: B336, B338, B339, B340.

B336  5x5 "7-stone forcing needs only local rules": restricted winning
      policies (win-preservation + one avoidance class) and the exact set of
      terminal sizes each policy can still reach.
B338  WFT-nonempty vs the opponent's T*-intersection, inside several cell
      definitions; also a decision-tree depth test.
B339  the two-label recursion (Force_T) equals "T in WFT"; the *content* of
      the hypothesis is the size of a closed set of D4 local move-types that
      still certifies the forcing (minimum set cover over (S,move) orbits).
B340  first-move order inversion, E(random) vs forced length, on squares
      n=2..5 and the 2xm family m=2..8.

Output: research/verification/round3_chunk6_wft.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_rect, board_square  # noqa: E402

sys.setrecursionlimit(300000)

OUT = ROOT / "research" / "verification" / "round3_chunk6_wft.json"


# --------------------------------------------------------------------------
def bits(mask: int) -> list[int]:
    out = []
    while mask:
        b = mask & -mask
        out.append(b.bit_length() - 1)
        mask ^= b
    return out


def d4_perms(w: int, h: int):
    def pid(x, y):
        return y * w + x

    def gen(fn):
        return [pid(*fn(x, y)) for y in range(h) for x in range(w)]

    return [
        gen(lambda x, y: (x, y)),
        gen(lambda x, y: (w - 1 - y, x)),
        gen(lambda x, y: (w - 1 - x, h - 1 - y)),
        gen(lambda x, y: (y, w - 1 - x)),
        gen(lambda x, y: (w - 1 - x, y)),
        gen(lambda x, y: (x, h - 1 - y)),
        gen(lambda x, y: (y, x)),
        gen(lambda x, y: (w - 1 - y, h - 1 - x)),
    ]


def apply_p(occ: int, p) -> int:
    m = occ
    img = 0
    while m:
        b = m & -m
        img |= 1 << p[b.bit_length() - 1]
        m ^= b
    return img


def solve(B):
    reachable = {0}
    stack = [0]
    while stack:
        occ = stack.pop()
        for u in B.legal_moves(occ):
            nxt = occ | (1 << u)
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)

    g: dict[int, int] = {}
    Lc: dict[int, list[int]] = {}

    def ev(occ):
        if occ in g:
            return g[occ]
        mv = B.legal_moves(occ)
        Lc[occ] = mv
        if not mv:
            g[occ] = 0
            return g[occ]
        seen = {ev(occ | (1 << u)) for u in mv}
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        return x

    ev(0)
    for occ in reachable:
        Lc.setdefault(occ, B.legal_moves(occ))

    tstar: dict[int, frozenset] = {}
    wft: dict[int, frozenset] = {}
    Fr: dict[int, Fraction] = {}

    def ev_t(occ):
        if occ in tstar:
            return tstar[occ]
        mv = Lc[occ]
        if not mv:
            tstar[occ] = frozenset({occ.bit_count()})
            return tstar[occ]
        s: set = set()
        if g[occ] == 0:
            for u in mv:
                s |= ev_t(occ | (1 << u))
        else:
            for u in mv:
                ch = occ | (1 << u)
                if g[ch] == 0:
                    s |= ev_t(ch)
        tstar[occ] = frozenset(s)
        return tstar[occ]

    def ev_w(occ):
        if occ in wft:
            return wft[occ]
        mv = Lc[occ]
        if not mv:
            wft[occ] = frozenset({occ.bit_count()})
            return wft[occ]
        if g[occ] == 0:
            acc = None
            for u in mv:
                s = ev_w(occ | (1 << u))
                acc = s if acc is None else (acc & s)
            wft[occ] = frozenset(acc or set())
        else:
            a: set = set()
            for u in mv:
                ch = occ | (1 << u)
                if g[ch] == 0:
                    a |= ev_w(ch)
            wft[occ] = frozenset(a)
        return wft[occ]

    def ev_f(occ):
        if occ in Fr:
            return Fr[occ]
        mv = Lc[occ]
        if not mv:
            Fr[occ] = Fraction(occ.bit_count())
            return Fr[occ]
        s = Fraction(0)
        for u in mv:
            s += ev_f(occ | (1 << u))
        Fr[occ] = s / len(mv)
        return Fr[occ]

    for occ in reachable:
        ev_t(occ)
        ev_w(occ)
        ev_f(occ)
    return reachable, g, Lc, tstar, wft, Fr


# --------------------------------------------------------------------------
def restricted_policy(B, g, Lc, T, allowed_type=None, forbid=None):
    """Winner plays only moves that (a) keep the win (child is P) and
    (b) pass `forbid`, and (c) if allowed_type is given, whose
    (S,move) D4-orbit type is in allowed_type.

    Returns (forces_T, sorted terminal sizes still reachable, perm_cache)."""
    if forbid is None:
        forbid = lambda occ: False  # noqa: E731
    forced: dict[int, bool] = {}
    poss: dict[int, set] = {}
    perms = d4_perms(*_dims(B))
    stab_cache: dict[int, list] = {}

    def stab(occ):
        if occ not in stab_cache:
            stab_cache[occ] = [p for p in perms if apply_p(occ, p) == occ]
        return stab_cache[occ]

    def typ(occ, u):
        if allowed_type is None:
            return 0
        return min(frozenset((apply_p(occ, p), p[u]) for p in stab(occ)))

    def ev(occ):
        if occ in forced:
            return forced[occ]
        mv = Lc[occ]
        if not mv:
            forced[occ] = (occ.bit_count() == T)
            poss[occ] = {occ.bit_count()}
            return forced[occ]
        kids = [occ | (1 << u) for u in mv]
        fvals = [ev(c) for c in kids]
        s: set = set()
        if g[occ] == 0:
            forced[occ] = all(fvals)
            for c in kids:
                s |= poss[c]
        else:
            ach = []
            for u in mv:
                c = occ | (1 << u)
                if g[c] != 0:
                    continue
                if forbid(c):
                    continue
                if allowed_type is not None and typ(occ, u) not in allowed_type:
                    continue
                ach.append(c)
            fv2 = [ev(c) for c in ach]
            forced[occ] = any(fv2) if fv2 else False
            for c in ach:
                s |= poss[c]
        poss[occ] = s
        return forced[occ]

    ev(0)
    return forced[0], sorted(poss[0]), stab_cache


def _dims(B):
    xs = [p[0] for p in B.points]
    ys = [p[1] for p in B.points]
    return max(xs) + 1, max(ys) + 1


# --------------------------------------------------------------------------
def B336_block(B, g, Lc, wft, hfun) -> dict:
    tgt = sorted(wft[0])
    res: dict = {"WFT_empty": tgt,
                 "claim": "win-preservation + 'avoid entering a size-4 minimax' "
                          "+ 'avoid the entry to a 5-stone terminal' suffices for the 7-forcing"}
    if len(tgt) != 1:
        res["note"] = "WFT(empty) not singleton"
        return res
    T = tgt[0]
    res["T"] = T

    def f_none(occ):
        return False

    def f_minimax4(occ):
        return occ.bit_count() == 4 and hfun(occ) == 0

    def f_minimax4or5(occ):
        return occ.bit_count() in (4, 5) and hfun(occ) == 0

    def f_allminimax(occ):
        return hfun(occ) == 0

    def f_k4(occ):
        return occ.bit_count() == 4

    def f_k4or5(occ):
        return occ.bit_count() in (4, 5)

    rules = {
        "R0_win_preservation_only": f_none,
        "R1_avoid_minimax_4__literal_B336": f_minimax4,
        "R2_avoid_any_4stone": f_k4,
        "R3_avoid_minimax_4_and_minimax_5": f_minimax4or5,
        "R4_avoid_any_4stone_and_any_5stone": f_k4or5,
        "R5_avoid_all_minimax": f_allminimax,
    }
    res["policies"] = {}
    for name, fn in rules.items():
        t0 = time.time()
        force, terms, _ = restricted_policy(B, g, Lc, T, forbid=fn)
        res["policies"][name] = {
            "forces_exactly_T": force,
            "terminal_sizes_still_reachable": terms,
            "seconds": round(time.time() - t0, 1),
        }
        print(f"    {name}: force={force} terms={terms}", flush=True)
    base = res["policies"]["R0_win_preservation_only"]["forces_exactly_T"]
    res["conclusion"] = (
        "win-preservation alone already forces the target length" if base else
        "win-preservation alone does NOT force the target; an extra rule is needed")
    return res


# --------------------------------------------------------------------------
def B338_block(reachable, g, Lc, tstar, wft) -> dict:
    cellfns = {
        "(k,g,|L|)": lambda o: (o.bit_count(), g[o], o.bit_count() + len(Lc[o])),
        "(k,|L|)": lambda o: (o.bit_count(), o.bit_count() + len(Lc[o])),
        "(k,)": lambda o: (o.bit_count(),),
        "(k,g)": lambda o: (o.bit_count(), g[o]),
    }
    feats = {
        "Tstar_intersection_all_children": lambda o: _inter(Lc, tstar, o),
        "Tstar_intersection_of_P_children": lambda o: _inter(Lc, tstar, o, True),
        "Tstar_union_all_children": lambda o: _uni(Lc, tstar, o),
        "g_of_state": lambda o: g[o],
    }
    res = {"cell_definitions": {}, "features": {}}
    for cname, cfn in cellfns.items():
        cells = defaultdict(list)
        for o in reachable:
            cells[cfn(o)].append(o)
        mixed = sum(1 for occs in cells.values()
                    if 0 < sum(1 for o in occs if wft[o]) < len(occs))
        res["cell_definitions"][cname] = {
            "n_cells": len(cells),
            "n_mixed_cells": mixed,
        }
        # score every feature inside this cell definition
        res["features"][cname] = {}
        for fname, ffn in feats.items():
            seps = []
            covered = 0
            undecided = 0
            for key, occs in cells.items():
                lab = [1 if wft[o] else 0 for o in occs]
                if all(lab) or not any(lab):
                    continue
                vals = [ffn(o) for o in occs]
                pos = [v for v, l in zip(vals, lab) if l]
                neg = [v for v, l in zip(vals, lab) if not l]
                pairs = [(a, b) for a in pos for b in neg]
                if not pairs:
                    continue
                good = sum(1 for a, b in pairs if a > b)
                bad = sum(1 for a, b in pairs if a < b)
                if good + bad == 0:
                    undecided += 1
                    continue
                seps.append(good / (good + bad))
                if good + bad == len(pairs):
                    covered += 1
            res["features"][cname][fname] = {
                "n_mixed_cells_scored": len(seps) + undecided,
                "n_mixed_cells_undecided": undecided,
                "mean_pairwise_separation": (sum(seps) / len(seps)) if seps else None,
                "n_cells_perfectly_separated": covered,
            }
        best = max(
            ((f, v) for f, v in res["features"][cname].items()
             if v["mean_pairwise_separation"] is not None),
            key=lambda kv: kv[1]["mean_pairwise_separation"], default=None)
        print(f"    cells {cname} mixed={mixed}: best={best[0] if best else None} "
              f"sep={best[1]['mean_pairwise_separation'] if best else None}", flush=True)
    # depth-2 decision table on the two T* features inside (k,g,|L|) cells
    cfn = cellfns["(k,g,|L|)"]
    cells = defaultdict(list)
    for o in reachable:
        cells[cfn(o)].append(o)
    featA = feats["Tstar_intersection_all_children"]
    featB = feats["Tstar_union_all_children"]
    depth_ok = 0
    n_cells = 0
    for key, occs in cells.items():
        lab = [1 if wft[o] else 0 for o in occs]
        if all(lab) or not any(lab):
            continue
        n_cells += 1
        rows = sorted({(featA(o), featB(o), lab[i])
                       for i, o in enumerate(occs)})
        mapping = {}
        ok = True
        for a, b, l in rows:
            if mapping.setdefault((a, b), l) != l:
                ok = False
                break
        if ok:
            depth_ok += 1
    res["two_Tstar_feature_table_is_consistent_cells"] = depth_ok
    res["n_mixed_cells_for_table_test"] = n_cells
    return res


def _inter(Lc, tstar, o, only_p=False):
    mv = Lc[o]
    if not mv:
        return 0
    acc = None
    for u in mv:
        ch = o | (1 << u)
        s = tstar[ch]
        acc = s if acc is None else (acc & s)
        if not acc:
            return 0
    return len(acc) if acc else 0


def _uni(Lc, tstar, o):
    mv = Lc[o]
    acc: set = set()
    for u in mv:
        acc |= tstar[o | (1 << u)]
    return len(acc)


# --------------------------------------------------------------------------
def B339_block(B, g, Lc, wft, reachable) -> dict:
    tgt = sorted(wft[0])
    res: dict = {"WFT_empty": tgt}
    if len(tgt) != 1:
        res["note"] = "not singleton"
        return res
    T = tgt[0]
    res["T"] = T
    # exact WFT-style 2-label recursion: force(occ) = (T in WFT(occ))
    force: dict[int, bool] = {}

    def ev_f(occ):
        if occ in force:
            return force[occ]
        mv = Lc[occ]
        if not mv:
            force[occ] = (occ.bit_count() == T)
            return force[occ]
        if g[occ] == 0:
            vals = [ev_f(occ | (1 << u)) for u in mv]
            force[occ] = all(vals)
        else:
            vals = [ev_f(occ | (1 << u)) for u in mv if g[occ | (1 << u)] == 0]
            force[occ] = any(vals) if vals else False
        return force[occ]

    for o in reachable:
        ev_f(o)
    res["n_states"] = len(reachable)
    res["force0"] = force[0]
    res["n_distinct_g_values"] = len({g[o] for o in reachable})
    res["n_distinct_force_labels"] = 2
    res["compression_ratio_g_table_over_2_labels"] = (
        res["n_distinct_g_values"] / 2.0)
    by_force = defaultdict(set)
    for o in reachable:
        by_force[force[o]].add(g[o])
    res["nimbers_merged_by_force"] = {str(k): sorted(v) for k, v in by_force.items()}
    res["force_equals_WFT_membership_all"] = all(
        force[o] == (T in wft[o]) for o in reachable)

    # ---- the real content: minimum number of D4 (S,move) local types ----
    t0 = time.time()
    w, h = _dims(B)
    perms = d4_perms(w, h)
    force_moves: dict[int, list[int]] = {}

    def win_moves(o):
        if o not in force_moves:
            force_moves[o] = [u for u in Lc[o]
                              if g[o | (1 << u)] == 0 and force[o | (1 << u)]]
        return force_moves[o]

    forced_N = [o for o in reachable if g[o] > 0 and force[o]]
    cover: dict[frozenset, set] = defaultdict(set)   # type -> states it can handle
    need = set()
    for o in forced_N:
        if not win_moves(o):
            continue
        sts = [p for p in perms if apply_p(o, p) == o]
        typs = {min(frozenset((apply_p(o, p), p[u]) for p in sts))
                for u in win_moves(o)}
        need.add(o)
        for t in typs:
            cover[t].add(o)
    res["n_force_N_states"] = len(forced_N)
    res["n_rule_types_total"] = len(cover)
    res["n_states_needing_a_rule"] = len(need)
    res["mean_types_per_state"] = (
        sum(len(win_moves(o)) for o in need) / max(1, len(need)))
    # greedy minimum set cover
    chosen: list = []
    uncovered = set(need)
    guard = 0
    while uncovered and guard < 5000:
        guard += 1
        best = max(cover, key=lambda t: len(cover[t] & uncovered))
        gain = len(cover[best] & uncovered)
        if gain == 0:
            break
        chosen.append(best)
        uncovered -= cover[best]
    res["greedy_min_rule_set_size"] = len(chosen)
    res["greedy_covers_all"] = not uncovered
    res["types_covered"] = len(need) - len(uncovered)
    res["greedy_seconds"] = round(time.time() - t0, 1)
    res["compression_ratio_moves_over_types"] = (
        res["n_force_N_states"] / max(1, len(cover)))
    res["verdict"] = (
        "a closed rule set of D4 move-types of size %d covers all %d forcing "
        "states (vs %d forcing states themselves)"
        % (len(chosen), len(need), len(forced_N)))
    print(f"    B339 orbit-types: types={len(cover)} greedy={len(chosen)} "
          f"states={len(need)} ({res['greedy_seconds']}s)", flush=True)

    # ---- alternative reading: state-independent local descriptors ----
    # A rule = "from any state whose local descriptor is D, play a move whose
    # (descriptor of the move) is M".  We test whether a *small* number of
    # descriptor classes suffices, i.e. how many (D, M) pairs are needed.
    # Move descriptor: (resulting k, #legal after, is P, WFT child size).
    def mdesc(o, u):
        c = o | (1 << u)
        return (o.bit_count(), len(Lc[o]), c.bit_count(), len(Lc[c]),
                0 if g[c] == 0 else 1, tuple(sorted(wft[c])))

    st_desc = {}
    for o in reachable:
        st_desc[o] = (o.bit_count(), len(Lc[o]), g[o], tuple(sorted(wft[o])))
    rules2: dict[tuple, set] = defaultdict(set)
    need2 = set()
    for o in forced_N:
        if not win_moves(o):
            continue
        need2.add(o)
        for u in win_moves(o):
            rules2[(st_desc[o], mdesc(o, u))].add(o)
    chosen2: list = []
    unc = set(need2)
    while unc:
        best = max(rules2, key=lambda t: len(rules2[t] & unc))
        if not (rules2[best] & unc):
            break
        chosen2.append(best)
        unc -= rules2[best]
    res["descriptor_rule_set_size"] = len(chosen2)
    res["descriptor_rules_total"] = len(rules2)
    res["descriptor_covers_all"] = not unc
    res["n_states_needing_a_descriptor_rule"] = len(need2)
    res["descriptor_compression"] = len(need2) / max(1, len(chosen2))
    print(f"    B339 descriptor-rules: rules={len(chosen2)}/{len(rules2)} "
          f"states={len(need2)} compression={res['descriptor_compression']:.2f}", flush=True)
    return res


# --------------------------------------------------------------------------
def B340_block(B, g, Lc, wft, Fr, w, h, label) -> dict:
    rows = []
    for u in Lc[0]:
        ch = 1 << u
        rows.append({
            "first": u, "xy": [u % w, u // w], "g": g[ch],
            "winning": g[ch] == 0, "E": str(Fr[ch]), "WFT": sorted(wft[ch]),
        })
    wins = [r for r in rows if r["winning"]]
    res = {
        "board": label,
        "n_first_moves": len(rows),
        "n_winning_firsts": len(wins),
        "n_losing_firsts": len(rows) - len(wins),
    }
    if not wins:
        res["note"] = "empty board is P: no winning first move, antecedent void"
        return res
    if any(not r["WFT"] for r in wins):
        res["note"] = "some winning first move has empty WFT"
        res["n_empty_wft"] = sum(1 for r in wins if not r["WFT"])
        return res
    fmin = [min(r["WFT"]) for r in wins]
    fmax = [max(r["WFT"]) for r in wins]
    res["forced_min_range"] = [min(fmin), max(fmin)]
    res["forced_max_range"] = [min(fmax), max(fmax)]
    res["forced_is_constant"] = (min(fmin) == max(fmin) and min(fmax) == max(fmax))
    res["E_range"] = [str(min(Fr[1 << r["first"]] for r in wins)),
                      str(max(Fr[1 << r["first"]] for r in wins))]
    res["E_is_constant"] = res["E_range"][0] == res["E_range"][1]
    res["all_firsts"] = rows
    if res["forced_is_constant"]:
        res["note"] = ("forced length identical for every winning first move; "
                       "the order is a point mass so an inversion is impossible")
        return res
    Es = [Fr[1 << r["first"]] for r in wins]
    res["spearman_E_vs_forcedmin"] = _spear(Es, fmin)
    res["spearman_E_vs_forcedmax"] = _spear(Es, fmax)
    inv = None
    for i in range(len(wins)):
        for j in range(len(wins)):
            if i == j:
                continue
            Ei, Ej = Es[i], Es[j]
            if Ei < Ej and (fmax[i] > fmax[j] or fmin[i] < fmin[j]):
                cand = {"metric": "max(WFT)" if fmax[i] > fmax[j] else "min(WFT)",
                        "shorter_random_avg": wins[i], "longer_random_avg": wins[j]}
                inv = inv or cand
    res["inversion_witness"] = inv
    res["inversion_found"] = inv is not None
    return res


def _spear(a, b):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for t in range(i, j + 1):
                r[order[t]] = avg
            i = j + 1
        return r
    return _ptcor(ranks(a), ranks(b))


def _ptcor(xs, ys):
    m = len(xs)
    mx = sum(xs) / m
    my = sum(ys) / m
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return 0.0 if dx == 0 or dy == 0 else num / (dx * dy)


# --------------------------------------------------------------------------
def local_ceiling_h(B):
    cache: dict[int, int] = {}

    def h_of(occ):
        if occ in cache:
            return cache[occ]
        mv = B.legal_moves(occ)
        v = 0 if not mv else max(h_of(occ | (1 << u)) for u in mv)
        cache[occ] = v
        return v

    h_of(0)
    return h_of


def analyze_square(n: int) -> dict:
    t0 = time.time()
    B = board_square(n)
    print(f"[{n}x{n}] solving...", flush=True)
    reachable, g, Lc, tstar, wft, Fr = solve(B)
    print(f"[{n}x{n}] states={len(reachable)} solved in {time.time()-t0:.1f}s", flush=True)
    hfun = local_ceiling_h(B)
    out = {
        "board": f"{n}x{n}", "n_states": len(reachable),
        "Tstar_empty": sorted(tstar[0]), "WFT_empty": sorted(wft[0]),
        "K_global": max(o.bit_count() for o in reachable),
    }
    print("  B336...", flush=True)
    out["B336"] = B336_block(B, g, Lc, wft, hfun)
    print("  B338...", flush=True)
    out["B338"] = B338_block(reachable, g, Lc, tstar, wft)
    print("  B339...", flush=True)
    out["B339"] = B339_block(B, g, Lc, wft, reachable)
    print("  B340...", flush=True)
    out["B340"] = B340_block(B, g, Lc, wft, Fr, n, n, f"{n}x{n}")
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def analyze_rect(w: int, h: int) -> dict:
    t0 = time.time()
    B = board_rect(w, h)
    print(f"[{w}x{h}] solving...", flush=True)
    reachable, g, Lc, tstar, wft, Fr = solve(B)
    out = {
        "board": f"{w}x{h}", "n_states": len(reachable),
        "Tstar_empty": sorted(tstar[0]), "WFT_empty": sorted(wft[0]),
        "max_g": max(g.values()),
        "K": max(o.bit_count() for o in reachable),
        "B340": B340_block(B, g, Lc, wft, Fr, w, h, f"{w}x{h}"),
    }
    out["elapsed_s"] = round(time.time() - t0, 1)
    print(f"[{w}x{h}] states={len(reachable)} maxg={out['max_g']} "
          f"{out['elapsed_s']}s", flush=True)
    return out


def main() -> None:
    res: dict = {}
    if OUT.exists():
        try:
            res = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            res = {}
    for n in (2, 3, 4, 5):
        print(f"===== chunk6-A square n={n} =====", flush=True)
        res[f"n{n}"] = analyze_square(n)
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                       encoding="utf-8")
        print("  wrote", OUT, flush=True)
    print("===== chunk6-A 2xm family =====", flush=True)
    for m in range(2, 11):
        try:
            res[f"r2x{m}"] = analyze_rect(m, 2)
        except Exception as e:  # noqa: BLE001
            res[f"r2x{m}"] = {"error": repr(e)}
            print("  error", m, e, flush=True)
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                       encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
