#!/usr/bin/env python3
"""Batch 02 verification: Grundy size/gaps/saturation (B021-B030) and
winning-length sets T* (B031-B040), exact on n=4 and n=5.

Computes per reachable safe position S:
  g(S), |L(S)|, AllTermSizes(S) = sizes of maximal safe supersets,
  T*(S) = win-preserving terminal sizes (N->P only, P->any),
  WinForceT(S) = terminal sizes the winner can force exactly.

Outputs research/verification/scripts/batch02_out.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square

OUT = Path(__file__).resolve().parent / "batch02_out.json"


def analyze_board(n: int) -> dict:
    t0 = time.time()
    B = board_square(n)
    V = B.V
    print(f"[n={n}] forbidden quads: {len(B.quads)}", flush=True)

    # ---- all reachable safe sets via BFS from empty ----
    from collections import deque

    reachable: set[int] = {0}
    dq = deque([0])
    parent_check = 0
    while dq:
        occ = dq.popleft()
        for u in B.legal_moves(occ):
            nxt = occ | (1 << u)
            if nxt not in reachable:
                reachable.add(nxt)
                dq.append(nxt)
        parent_check += 1
    print(f"[n={n}] reachable={len(reachable)} in {time.time()-t0:.1f}s", flush=True)

    # ---- grundy ----
    g: dict[int, int] = {}

    def ev(occ: int) -> int:
        hit = g.get(occ)
        if hit is not None:
            return hit
        mv = B.legal_moves(occ)
        if not mv:
            g[occ] = 0
            return 0
        seen = set()
        for u in mv:
            seen.add(ev(occ | (1 << u)))
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        return x

    ev(0)
    assert len(g) == len(reachable)
    print(f"[n={n}] grundy done {time.time()-t0:.1f}s max={max(g.values())}", flush=True)

    # ---- legal-move lists cached ----
    Lcache: dict[int, list[int]] = {}
    for occ in reachable:
        Lcache[occ] = B.legal_moves(occ)

    # ---- AllTermSizes: sizes of maximal safe supersets ----
    # bottom-up from terminals
    term_sizes: dict[int, set[int]] = {}
    # process by decreasing popcount so children (more stones) done first
    by_k: dict[int, list[int]] = defaultdict(list)
    for occ in reachable:
        by_k[occ.bit_count()].append(occ)

    Kmax = max(by_k)
    for k in range(Kmax, -1, -1):
        for occ in by_k[k]:
            mv = Lcache[occ]
            if not mv:
                term_sizes[occ] = {k}
            else:
                s: set[int] = set()
                for u in mv:
                    s |= term_sizes[occ | (1 << u)]
                term_sizes[occ] = s
    print(f"[n={n}] term_sizes done {time.time()-t0:.1f}s", flush=True)

    # ---- T*: N only to P-children; P any legal move ----
    tstar: dict[int, frozenset[int]] = {}

    def ev_t(occ: int) -> frozenset[int]:
        hit = tstar.get(occ)
        if hit is not None:
            return hit
        mv = Lcache[occ]
        if not mv:
            tstar[occ] = frozenset({occ.bit_count()})
            return tstar[occ]
        s: set[int] = set()
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

    for occ in reachable:
        ev_t(occ)
    print(f"[n={n}] tstar done {time.time()-t0:.1f}s T*(empty)={sorted(tstar[0])}", flush=True)

    # ---- WinForceT: winner can force exactly t ----
    # N: union over winning moves (to g=0); P: intersection over legal moves.
    wft: dict[int, frozenset[int]] = {}

    def ev_w(occ: int) -> frozenset[int]:
        hit = wft.get(occ)
        if hit is not None:
            return hit
        mv = Lcache[occ]
        if not mv:
            wft[occ] = frozenset({occ.bit_count()})
            return wft[occ]
        if g[occ] == 0:
            # intersection over all legal children
            acc = None
            for u in mv:
                ch = occ | (1 << u)
                s = ev_w(ch)
                acc = s if acc is None else (acc & s)
                if not acc:
                    break
            wft[occ] = frozenset(acc or set())
        else:
            acc_set: set[int] = set()
            for u in mv:
                ch = occ | (1 << u)
                if g[ch] == 0:
                    acc_set |= ev_w(ch)
            wft[occ] = frozenset(acc_set)
        return wft[occ]

    for occ in reachable:
        ev_w(occ)
    print(f"[n={n}] winforceT done {time.time()-t0:.1f}s WFT(empty)={sorted(wft[0])}", flush=True)

    # ---- K_n = global max safe size = max term_sizes[0] ----
    Kn = max(term_sizes[0])

    # ---- B025: saturation-layer completeness ----
    # sigma = min k with max_g(k)=K-k
    layer_max: dict[int, int] = {}
    layer_hist: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for occ, gv in g.items():
        k = occ.bit_count()
        layer_hist[k][gv] += 1
        if gv > layer_max.get(k, -1):
            layer_max[k] = gv
    sigma = None
    for k in sorted(layer_max):
        if layer_max[k] == Kn - k:
            sigma = k
            break
    b025_gaps = {}
    for k in sorted(layer_max):
        if sigma is not None and k >= sigma:
            present = set(layer_hist[k])
            missing = sorted(set(range(Kn - k + 1)) - present)
            if missing:
                b025_gaps[k] = missing

    # ---- B026: local ceiling attained, global not ----
    b026_witnesses = []
    for occ, gv in g.items():
        k = occ.bit_count()
        ks = max(term_sizes[occ])
        if k == ks:
            continue  # terminal
        if gv == ks - k and ks < Kn:
            b026_witnesses.append({
                "occ": occ,
                "k": k,
                "g": gv,
                "K_S": ks,
                "local_ceiling": ks - k,
                "global_ceiling": Kn - k,
                "cells": [f"({i % n},{i // n})" for i in range(V) if occ >> i & 1],
            })
            if len(b026_witnesses) >= 5:
                break

    # ---- B027: high g vs spread of terminal sizes (same n,k,|L|) ----
    # collect (k, |L|) -> list of (g, spread)
    groups: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for occ, gv in g.items():
        k = occ.bit_count()
        if not Lcache[occ]:
            continue
        sizes = term_sizes[occ]
        spread = max(sizes) - min(sizes)
        groups[(k, len(Lcache[occ]))].append((gv, spread))

    b027_cells = []
    n_pos_corr = n_neg_corr = n_tie = 0
    for key, lst in groups.items():
        if len(lst) < 8:
            continue
        # split into high-g (top third) vs low-g (bottom third) and compare mean spread
        lst_sorted = sorted(lst, key=lambda x: x[0])
        t = len(lst_sorted) // 3
        if t < 2:
            continue
        low = lst_sorted[:t]
        high = lst_sorted[-t:]
        mean_low = sum(s for _, s in low) / len(low)
        mean_high = sum(s for _, s in high) / len(high)
        b027_cells.append({
            "k": key[0], "L": key[1], "count": len(lst),
            "mean_spread_low_g": round(mean_low, 3),
            "mean_spread_high_g": round(mean_high, 3),
            "low_g_range": [low[0][0], low[-1][0]],
            "high_g_range": [high[0][0], high[-1][0]],
        })
        if mean_high > mean_low + 1e-9:
            n_pos_corr += 1
        elif mean_high < mean_low - 1e-9:
            n_neg_corr += 1
        else:
            n_tie += 1

    # ---- B028: child with g-1 among max-mobility moves ----
    b028_total = b028_ok = 0
    b028_fail_example = None
    for occ, gv in g.items():
        if gv <= 1:
            continue
        mv = Lcache[occ]
        if not mv:
            continue
        b028_total += 1
        # mobility of each child
        child_mob = []
        for u in mv:
            ch = occ | (1 << u)
            child_mob.append((len(Lcache[ch]), g[ch], u, ch))
        max_mob = max(m for m, _, _, _ in child_mob)
        ok = any(m == max_mob and cgv == gv - 1 for m, cgv, _, _ in child_mob)
        if ok:
            b028_ok += 1
        elif b028_fail_example is None:
            b028_fail_example = {
                "occ": occ,
                "g": gv,
                "k": occ.bit_count(),
                "cells": [f"({i % n},{i // n})" for i in range(V) if occ >> i & 1],
                "children": [
                    {"mob": m, "g": cgv, "add": f"({u % n},{u // n})"}
                    for m, cgv, u, _ in sorted(child_mob, key=lambda x: -x[0])[:8]
                ],
            }

    # ---- B030: same term-size-set, different g ----
    by_sig: dict[tuple[int, frozenset], list[tuple[int, int, int]]] = defaultdict(list)
    for occ, gv in g.items():
        k = occ.bit_count()
        sig = (k, frozenset(term_sizes[occ]))
        by_sig[sig].append((gv, occ, len(Lcache[occ])))
    b030_witness = None
    for sig, lst in by_sig.items():
        gs = {gv for gv, _, _ in lst}
        if len(gs) >= 2:
            # pick two with different g
            lst_sorted = sorted(lst, key=lambda x: x[0])
            a, b = lst_sorted[0], lst_sorted[-1]
            b030_witness = {
                "k": sig[0],
                "term_sizes": sorted(sig[1]),
                "S": {
                    "g": a[0],
                    "cells": [f"({i % n},{i // n})" for i in range(V) if a[1] >> i & 1],
                    "L": a[2],
                },
                "T_pos": {
                    "g": b[0],
                    "cells": [f"({i % n},{i // n})" for i in range(V) if b[1] >> i & 1],
                    "L": b[2],
                },
                "group_count": len(lst),
                "distinct_g": sorted(gs),
            }
            break

    # ---- B031: T* same-parity holes ----
    b031_violations = []
    b031_checked = 0
    for occ, ts in tstar.items():
        if len(ts) < 3:
            continue
        b031_checked += 1
        srt = sorted(ts)
        for parity in (0, 1):
            evens = [x for x in srt if x % 2 == parity]
            if len(evens) >= 3:
                for i in range(len(evens) - 2):
                    if evens[i + 1] - evens[i] > 2:
                        b031_violations.append({
                            "occ": occ,
                            "k": occ.bit_count(),
                            "g": g[occ],
                            "Tstar": srt,
                            "gap_parity": parity,
                            "gap": [evens[i], evens[i + 1]],
                            "cells": [f"({i % n},{i // n})" for i in range(V) if occ >> i & 1],
                        })
                        break
                if b031_violations and b031_violations[-1]["occ"] == occ:
                    break
        if len(b031_violations) >= 5:
            break

    # ---- B032/B033: first-move T* analysis ----
    first_moves = []
    for u in range(V):
        occ = 1 << u
        ts = sorted(tstar[occ])
        wf = sorted(wft[occ])
        first_moves.append({
            "cell": f"({u % n},{u // n})",
            "g": g[occ],
            "winning_first": g[occ] == 0,
            "Tstar": ts,
            "Tstar_min": min(ts) if ts else None,
            "Tstar_max": max(ts) if ts else None,
            "WFT": wf,
            "WFT_min": min(wf) if wf else None,
            "WFT_max": max(wf) if wf else None,
        })
    # B032: argmin of WFT_min vs argmax of WFT_max (among winning first moves)
    wins = [f for f in first_moves if f["winning_first"]]
    b032 = None
    if wins:
        # shortest win (against delay) = min WFT_min? actually WFT is forced-exact.
        # Use Tstar_min / Tstar_max for reachable extremes; and WFT for forced.
        min_tm = min(f["Tstar_min"] for f in wins)
        max_tm = max(f["Tstar_max"] for f in wins)
        shortest_set = {f["cell"] for f in wins if f["Tstar_min"] == min_tm}
        longest_set = {f["cell"] for f in wins if f["Tstar_max"] == max_tm}
        # also forced-length based
        wmin = min(f["WFT_min"] for f in wins)
        wmax = max(f["WFT_max"] for f in wins)
        shortest_w = {f["cell"] for f in wins if f["WFT_min"] == wmin}
        longest_w = {f["cell"] for f in wins if f["WFT_max"] == wmax}
        b032 = {
            "min_Tstar_min": min_tm,
            "max_Tstar_max": max_tm,
            "shortest_first_moves": sorted(shortest_set),
            "longest_first_moves": sorted(longest_set),
            "disjoint_Tstar_extremes": shortest_set.isdisjoint(longest_set),
            "WFT_min_min": wmin,
            "WFT_max_max": wmax,
            "shortest_WFT": sorted(shortest_w),
            "longest_WFT": sorted(longest_w),
            "disjoint_WFT_extremes": shortest_w.isdisjoint(longest_w),
        }

    # B033 (n=5 specific): center (2,2) vs others — compare WFT_min (worst-case short)
    b033 = None
    if n == 5:
        center = [f for f in wins if f["cell"] == "(2,2)"]
        if center:
            c = center[0]
            others = [f for f in wins if f["cell"] != "(2,2)"]
            b033 = {
                "center": c,
                "others_same_WFT_min": [
                    f["cell"] for f in others if f["WFT_min"] == c["WFT_min"]
                ],
                "others_Tstar_min": [
                    (f["cell"], f["Tstar_min"], f["WFT_min"]) for f in others
                ],
                "center_Tstar_min": c["Tstar_min"],
                "center_WFT_min": c["WFT_min"],
            }

    # ---- B034: K_n in T*(empty)? ----
    b034 = {
        "Kn": Kn,
        "Tstar_empty": sorted(tstar[0]),
        "Kn_in_Tstar": Kn in tstar[0],
        "WFT_empty": sorted(wft[0]),
        "parity_Kn": Kn % 2,
        "parity_empty_g0": g[0] == 0,
        "note": "parity explanation: all cert outcomes are parity-locked by format; "
                "here T*(empty) is game-theoretic (win-preserving).",
    }

    # ---- B035: fewer P-children -> narrower T* ----
    b035_groups: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for occ, gv in g.items():
        if gv == 0:
            continue  # N positions only
        mv = Lcache[occ]
        p_count = sum(1 for u in mv if g[occ | (1 << u)] == 0)
        if p_count == 0:
            continue
        ts = tstar[occ]
        width = max(ts) - min(ts) if ts else 0
        b035_groups[(occ.bit_count(), gv, p_count)].append(width)
    b035_rows = []
    for key, widths in sorted(b035_groups.items()):
        if len(widths) < 5:
            continue
        mean_w = sum(widths) / len(widths)
        b035_rows.append({
            "k": key[0], "g": key[1], "p_children": key[2],
            "count": len(widths), "mean_Tstar_width": round(mean_w, 3),
        })

    # ---- B036: N-position where losing moves get closer to terminal ----
    # K(S+p) > K(S+q) for all winning p and some losing q
    b036_witness = None
    b036_count = 0
    for occ, gv in g.items():
        if gv == 0:
            continue
        mv = Lcache[occ]
        wins_c, loss_c = [], []
        for u in mv:
            ch = occ | (1 << u)
            ks = max(term_sizes[ch])
            (wins_c if g[ch] == 0 else loss_c).append((ks, u, ch))
        if not wins_c or not loss_c:
            continue
        min_win_K = min(k for k, _, _ in wins_c)
        max_loss_K = max(k for k, _, _ in loss_c)
        if max_loss_K < min_win_K:
            b036_count += 1
            if b036_witness is None:
                b036_witness = {
                    "occ": occ,
                    "g": gv,
                    "k": occ.bit_count(),
                    "cells": [f"({i % n},{i // n})" for i in range(V) if occ >> i & 1],
                    "min_win_K": min_win_K,
                    "max_loss_K": max_loss_K,
                    "example_loss_move": f"({loss_c[0][1] % n},{loss_c[0][1] // n})"
                    if False else f"({[u for k,u,_ in loss_c if k==max_loss_K][0] % n},{[u for k,u,_ in loss_c if k==max_loss_K][0] // n})",
                }

    # ---- B038: two winning moves to P-children, D4-non-isomorphic, disjoint T* ----
    def d4_orbit(occ: int) -> list[int]:
        pts = [(i % n, i // n) for i in range(V) if occ >> i & 1]

        def to_occ(transform):
            o = 0
            for (x, y) in pts:
                nx, ny = transform(x, y)
                o |= 1 << (ny * n + nx)
            return o

        ts_ = [
            lambda x, y: (x, y),
            lambda x, y: (n - 1 - x, y),
            lambda x, y: (x, n - 1 - y),
            lambda x, y: (n - 1 - x, n - 1 - y),
            lambda x, y: (y, x),
            lambda x, y: (n - 1 - y, x),
            lambda x, y: (y, n - 1 - x),
            lambda x, y: (n - 1 - y, n - 1 - x),
        ]
        return sorted(set(to_occ(t) for t in ts_))

    b038_witness = None
    for occ, gv in g.items():
        if gv == 0:
            continue
        mv = Lcache[occ]
        p_children = [(u, occ | (1 << u)) for u in mv if g[occ | (1 << u)] == 0]
        # find two with disjoint T* and D4-non-isomorphic
        for i in range(len(p_children)):
            for j in range(i + 1, len(p_children)):
                u1, c1 = p_children[i]
                u2, c2 = p_children[j]
                t1, t2 = tstar[c1], tstar[c2]
                if t1 & t2:
                    continue
                orb1 = set(d4_orbit(c1))
                if c2 in orb1:
                    continue
                b038_witness = {
                    "parent_occ": occ,
                    "parent_g": gv,
                    "parent_k": occ.bit_count(),
                    "parent_cells": [f"({i2 % n},{i2 // n})" for i2 in range(V) if occ >> i2 & 1],
                    "child1": {
                        "add": f"({u1 % n},{u1 // n})",
                        "Tstar": sorted(t1),
                        "cells": [f"({i2 % n},{i2 // n})" for i2 in range(V) if c1 >> i2 & 1],
                    },
                    "child2": {
                        "add": f"({u2 % n},{u2 // n})",
                        "Tstar": sorted(t2),
                        "cells": [f"({i2 % n},{i2 // n})" for i2 in range(V) if c2 >> i2 & 1],
                    },
                }
                break
            if b038_witness:
                break

    # ---- B039: P/N flip rate under single-stone relocation ----
    # For safe S with |S|=k, consider S' = S - {a} + {b} safe, |S'|=k.
    # Flip if (g(S)==0) != (g(S')==0).  Group by k; also by "distance to max" = Kn - k.
    flip_by_k: dict[int, list[int]] = defaultdict(list)  # k -> [0/1 flips]
    # sample up to 400 sets per layer to keep cost down for n=5
    import random

    rng = random.Random(42)
    for k in sorted(by_k):
        pool = by_k[k]
        if not pool:
            continue
        sample = pool if len(pool) <= 400 else rng.sample(pool, 400)
        for occ in sample:
            # remove each stone, try adding each other empty
            stones = [i for i in range(V) if occ >> i & 1]
            empties = [i for i in range(V) if not (occ >> i & 1)]
            flips = 0
            total = 0
            base_p = g[occ] == 0
            for a in stones:
                mid = occ ^ (1 << a)
                for b in empties:
                    if b == a:
                        continue
                    nxt = mid | (1 << b)
                    if nxt not in reachable:
                        continue
                    total += 1
                    if (g[nxt] == 0) != base_p:
                        flips += 1
            if total > 0:
                flip_by_k[k].append(flips / total)
    b039_rows = []
    for k in sorted(flip_by_k):
        rates = flip_by_k[k]
        if not rates:
            continue
        b039_rows.append({
            "k": k,
            "Kn_minus_k": Kn - k,
            "mean_flip_rate": round(sum(rates) / len(rates), 4),
            "samples": len(rates),
        })

    # ---- B040: WFT(empty) nonempty ----
    b040 = {
        "WFT_empty": sorted(wft[0]),
        "holds_on_this_board": len(wft[0]) > 0,
    }

    # ---- M_n(k) profile summary (B021/B025 evidence) ----
    profile = {
        str(k): {
            "max_g": layer_max[k],
            "ceiling": Kn - k,
            "deficit": Kn - k - layer_max[k],
            "hist": dict(layer_hist[k]),
            "missing_below_ceiling": sorted(set(range(Kn - k + 1)) - set(layer_hist[k])),
        }
        for k in sorted(layer_max)
    }

    result = {
        "n": n,
        "V": V,
        "K_n": Kn,
        "reachable": len(reachable),
        "sigma": sigma,
        "empty_g": g[0],
        "max_g": max(g.values()),
        "profile": profile,
        "B025_gaps_after_sigma": b025_gaps,
        "B026_witnesses": b026_witnesses,
        "B026_count_total": sum(
            1
            for occ, gv in g.items()
            if Lcache[occ]
            and gv == max(term_sizes[occ]) - occ.bit_count()
            and max(term_sizes[occ]) < Kn
        ),
        "B027_cells": b027_cells[:30],
        "B027_pos_corr": n_pos_corr,
        "B027_neg_corr": n_neg_corr,
        "B027_tie": n_tie,
        "B028_total": b028_total,
        "B028_ok": b028_ok,
        "B028_fail_example": b028_fail_example,
        "B030_witness": b030_witness,
        "B031_checked": b031_checked,
        "B031_violations": b031_violations,
        "B032": b032,
        "B033": b033,
        "B034": b034,
        "B035_rows": b035_rows[:40],
        "B036_count": b036_count,
        "B036_witness": b036_witness,
        "B038_witness": b038_witness,
        "B039_rows": b039_rows,
        "B040": b040,
        "first_moves": first_moves,
        "seconds": round(time.time() - t0, 1),
    }
    print(f"[n={n}] DONE in {result['seconds']}s sigma={sigma} Kn={Kn}", flush=True)
    return result


def main() -> None:
    out = {}
    for n in (4, 5):
        out[str(n)] = analyze_board(n)
        # write incrementally
        OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
