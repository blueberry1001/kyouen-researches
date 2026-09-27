#!/usr/bin/env python3
"""Round-2 B324-B328: ceiling-achievement statistics (n=4,5 exact).

Computes for every reachable safe S:
  g, k, K(S)=max terminal size, h=K-k, |L|,
  maximal-extension size histogram (via increasing-id DP),
  entropy of that histogram,
  D4-stabilizer orbits of legal moves / winning moves,
  and for k=3 the collinear vs non-collinear nimber split.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square
from residual_core import apply_perm_mask, d4_perms

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b321.json"


def analyze(n: int) -> dict:
    B = board_square(n)
    V = B.V
    print(f"[n={n}] quads={len(B.quads)}", flush=True)

    reachable = {0}
    stack = [0]
    while stack:
        occ = stack.pop()
        for u in B.legal_moves(occ):
            nxt = occ | (1 << u)
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)
    print(f"[n={n}] reachable={len(reachable)}", flush=True)

    g: dict[int, int] = {}
    Lc: dict[int, list[int]] = {}

    def ev(occ: int) -> int:
        hit = g.get(occ)
        if hit is not None:
            return hit
        mv = B.legal_moves(occ)
        Lc[occ] = mv
        if not mv:
            g[occ] = 0
            return 0
        seen = {ev(occ | (1 << u)) for u in mv}
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        return x

    ev(0)
    for occ in reachable:
        if occ not in Lc:
            Lc[occ] = B.legal_moves(occ)
    print(f"[n={n}] grundy max={max(g.values())}", flush=True)

    # K(S) = max terminal size among descendants (and self if terminal)
    by_k: dict[int, list[int]] = defaultdict(list)
    for occ in reachable:
        by_k[occ.bit_count()].append(occ)
    kmax = max(by_k)
    Klocal: dict[int, int] = {}
    for k in range(kmax, -1, -1):
        for occ in by_k[k]:
            mv = Lc[occ]
            if not mv:
                Klocal[occ] = k
            else:
                Klocal[occ] = max(Klocal[occ | (1 << u)] for u in mv)

    # maximal-extension size histogram: add new points in increasing id order
    # so each maximal superset of S is counted exactly once.
    memo: dict[tuple[int, int], dict[int, int]] = {}

    def _eh(key: tuple[int, int]) -> dict[int, int]:
        hit = memo.get(key)
        if hit is not None:
            return hit
        occ, min_next = key
        mv = Lc[occ]
        legal_new = [u for u in mv if u >= min_next]
        if not legal_new:
            # terminal under the restriction; this is a maximal extension
            # only if occ itself has no legal moves at all.
            res = {occ.bit_count(): 1} if not mv else {}
            memo[key] = res
            return res
        acc: dict[int, int] = {}
        for u in legal_new:
            sub = _eh((occ | (1 << u), u + 1))
            for t, c in sub.items():
                acc[t] = acc.get(t, 0) + c
        memo[key] = acc
        return acc

    top_hist: dict[int, dict[int, int]] = {}
    for occ in reachable:
        top_hist[occ] = dict(_eh((occ, 0)))

    def entropy(hd: dict[int, int]) -> float:
        tot = sum(hd.values())
        if tot <= 0:
            return 0.0
        h = 0.0
        for c in hd.values():
            if c:
                p = c / tot
                h -= p * math.log(p)
        return h

    # D4 perms
    perms = d4_perms(n)
    ident = list(range(V))

    def stab_and_orbits(occ: int):
        stabs = [p for p in perms if apply_perm_mask(occ, p) == occ]
        # orbits of legal points under stabs
        pts = list(range(V))
        seen = [False] * V
        orbits = {}
        for v in pts:
            if seen[v]:
                continue
            orb = {v}
            for p in stabs:
                orb.add(p[v])
            for w in orb:
                seen[w] = True
            orbits[v] = frozenset(orb)
        return len(stabs), orbits

    # ---- B324/B325/B326/B327 ----
    cells: dict[tuple, dict] = {}
    ceiling_records = []  # g == h
    b325_pairs = []
    b326 = {"n_g_h_ge3": 0, "n_with_small_orbit_win": 0, "n_violation": 0, "violations": []}
    b327_cands = []

    for occ in reachable:
        k = occ.bit_count()
        gv = g[occ]
        K = Klocal[occ]
        h = K - k
        nL = len(Lc[occ])
        hd = top_hist[occ]
        ent = entropy(hd)
        is_ceil = gv == h and (not Lc[occ] or True)
        # ceiling achievement: g equals local ceiling h (non-terminal or terminal)
        key = (n, k, h, nL)
        cell = cells.setdefault(key, {"ceil_ent": [], "other_ent": [], "ceil_n": 0, "other_n": 0})
        if gv == h:
            cell["ceil_ent"].append(ent)
            cell["ceil_n"] += 1
            ceiling_records.append((occ, k, h, nL, ent, hd))
            b325_pairs.append((nL - h, n, k, h, occ))
        else:
            cell["other_ent"].append(ent)
            cell["other_n"] += 1

        # B326
        if gv == h and h >= 3 and gv > 0:
            b326["n_g_h_ge3"] += 1
            _, orbits = stab_and_orbits(occ)
            win = [u for u in Lc[occ] if g[occ | (1 << u)] == 0]
            ok = False
            for u in win:
                if len(orbits[u]) <= 2:
                    ok = True
                    break
            if ok:
                b326["n_with_small_orbit_win"] += 1
            else:
                b326["n_violation"] += 1
                if len(b326["violations"]) < 8:
                    b326["violations"].append(
                        {
                            "occ": occ,
                            "k": k,
                            "g": gv,
                            "h": h,
                            "win_orbit_sizes": sorted({len(orbits[u]) for u in win}),
                            "n_win": len(win),
                        }
                    )

        # B327: h-g large and some child reaches 0 deficit
        if Lc[occ] and h - gv >= 2:
            for u in Lc[occ]:
                ch = occ | (1 << u)
                h2 = Klocal[ch] - ch.bit_count()
                if h2 - g[ch] == 0:
                    b327_cands.append((h - gv, n, k, h, gv, occ, u))
                    break

    # B324: cells with both ceil and other, compare mean entropy
    b324 = {"cells_both": 0, "ceil_higher": 0, "other_higher": 0, "tie": 0, "examples": []}
    for key, cell in cells.items():
        if cell["ceil_n"] == 0 or cell["other_n"] == 0:
            continue
        b324["cells_both"] += 1
        me = sum(cell["ceil_ent"]) / len(cell["ceil_ent"])
        mo = sum(cell["other_ent"]) / len(cell["other_ent"])
        if me > mo + 1e-12:
            b324["ceil_higher"] += 1
        elif mo > me + 1e-12:
            b324["other_higher"] += 1
        else:
            b324["tie"] += 1
        if len(b324["examples"]) < 6:
            b324["examples"].append(
                {
                    "cell": list(key),
                    "ceil_n": cell["ceil_n"],
                    "other_n": cell["other_n"],
                    "mean_ent_ceil": me,
                    "mean_ent_other": mo,
                }
            )

    # B325: minimal |L|-h among ceiling positions
    b325_pairs.sort()
    b325 = {
        "min_L_minus_h": b325_pairs[0][0] if b325_pairs else None,
        "top5": [
            {"L_minus_h": t[0], "n": t[1], "k": t[2], "h": t[3], "occ": t[4]}
            for t in b325_pairs[:5]
        ],
        "n_ceiling": len(b325_pairs),
    }

    # B327
    b327_cands.sort(reverse=True)
    b327 = {
        "max_deficit_with_zero_child": b327_cands[0][0] if b327_cands else None,
        "top5": [
            {"deficit": t[0], "n": t[1], "k": t[2], "h": t[3], "g": t[4], "occ": t[5], "child": t[6]}
            for t in b327_cands[:5]
        ],
        "count": len(b327_cands),
    }

    # B328: k=3 collinear vs not, same |L|, top nimbers
    def is_collinear3(occ: int) -> bool:
        pts = [(p % n, p // n) for p in range(V) if (occ >> p) & 1]
        assert len(pts) == 3
        (x1, y1), (x2, y2), (x3, y3) = pts
        return (x2 - x1) * (y3 - y1) == (y2 - y1) * (x3 - x1)

    buckets: dict[tuple, dict] = defaultdict(
        lambda: {
            "coll_g": defaultdict(int),
            "non_g": defaultdict(int),
            "coll": 0,
            "non": 0,
        }
    )
    for occ in by_k[3]:
        if not Lc[occ]:
            continue
        nL = len(Lc[occ])
        gv = g[occ]
        b = buckets[nL]
        if is_collinear3(occ):
            b["coll"] += 1
            b["coll_g"][gv] += 1
        else:
            b["non"] += 1
            b["non_g"][gv] += 1

    # top-tier = g >= max_g_in_bucket - 0 (top value) or upper half
    b328_buckets = []
    n_coll_top_excess = 0
    n_non_top_excess = 0
    n_comparable = 0
    for nL in sorted(buckets):
        b = buckets[nL]
        if b["coll"] < 3 or b["non"] < 3:
            continue
        allmax = max(list(b["coll_g"]) + list(b["non_g"]))
        # top tier = g == allmax
        ct = b["coll_g"].get(allmax, 0)
        nt = b["non_g"].get(allmax, 0)
        cr = ct / b["coll"]
        nr = nt / b["non"]
        n_comparable += 1
        if cr > nr:
            n_coll_top_excess += 1
        elif nr > cr:
            n_non_top_excess += 1
        b328_buckets.append(
            {
                "nL": nL,
                "coll": b["coll"],
                "non": b["non"],
                "coll_hist": dict(sorted(b["coll_g"].items())),
                "non_hist": dict(sorted(b["non_g"].items())),
                "top_g": allmax,
                "coll_top_rate": cr,
                "non_top_rate": nr,
            }
        )

    b328 = {
        "comparable_buckets": n_comparable,
        "collinear_top_excess": n_coll_top_excess,
        "noncollinear_top_excess": n_non_top_excess,
        "buckets": b328_buckets,
    }

    return {
        "n": n,
        "K_global": Klocal[0],
        "max_g": max(g.values()),
        "n_ceiling_g_eq_h": sum(1 for occ in reachable if g[occ] == Klocal[occ] - occ.bit_count()),
        "B324": b324,
        "B325": b325,
        "B326": b326,
        "B327": b327,
        "B328": b328,
    }


def main() -> None:
    results = {}
    for n in (4, 5):
        print(f"===== n={n} =====", flush=True)
        results[str(n)] = analyze(n)
        print(json.dumps({k: results[str(n)][k] for k in ("B324", "B325", "B326", "B327")}, indent=2)[:3000], flush=True)

    # merge into existing json
    path = ROOT / "research" / "verification" / "round2_b321.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}
    data["ceiling_stats"] = results
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
