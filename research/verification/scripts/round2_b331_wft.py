#!/usr/bin/env python3
"""Round-2 B331-B337, B340: WFT / T* on n=2..5 exact.

WFT recurrence (as in batch-02):
  terminal: {k}
  P (g=0):  intersection over all legal children
  N (g>0):  union over winning moves (children with g=0)
T*: win-preserving terminal sizes (N->P children only, P->any).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b321.json"


def analyze(n: int) -> dict:
    B = board_square(n)
    print(f"[n={n}] start", flush=True)
    reachable = {0}
    stack = [0]
    while stack:
        occ = stack.pop()
        for u in B.legal_moves(occ):
            nxt = occ | (1 << u)
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)

    g = {}
    Lc = {}

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

    # ---- T* ----
    tstar = {}

    def ev_t(occ: int) -> frozenset[int]:
        hit = tstar.get(occ)
        if hit is not None:
            return hit
        mv = Lc[occ]
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

    # ---- WFT ----
    wft = {}

    def ev_w(occ: int) -> frozenset[int]:
        hit = wft.get(occ)
        if hit is not None:
            return hit
        mv = Lc[occ]
        if not mv:
            wft[occ] = frozenset({occ.bit_count()})
            return wft[occ]
        if g[occ] == 0:
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

    empty_t = sorted(tstar[0])
    empty_w = sorted(wft[0])
    print(f"[n={n}] T*(empty)={empty_t} WFT(empty)={empty_w}", flush=True)

    # ---- B331: |WFT(empty)| <= 1 ----
    b331 = {"WFT_empty": empty_w, "Tstar_empty": empty_t, "abs_WFT_le_1": len(empty_w) <= 1}

    # ---- B332: exists S with |WFT(S)| >= 2 ----
    multi = []
    n_multi = 0
    for occ in reachable:
        if len(wft[occ]) >= 2:
            n_multi += 1
            if len(multi) < 6:
                multi.append(
                    {
                        "occ": occ,
                        "k": occ.bit_count(),
                        "g": g[occ],
                        "WFT": sorted(wft[occ]),
                        "Tstar": sorted(tstar[occ]),
                    }
                )
    b332 = {"n_multi_WFT": n_multi, "examples": multi}

    # ---- B333: same-parity holes in WFT ----
    viol333 = []
    n_checked = 0
    for occ in reachable:
        ws = sorted(wft[occ])
        if len(ws) < 2:
            continue
        n_checked += 1
        found = False
        for i, t in enumerate(ws):
            for u in ws[i + 1 :]:
                if u - t >= 4:
                    for mid in range(t + 2, u, 2):
                        if mid not in wft[occ]:
                            viol333.append(
                                {
                                    "occ": occ,
                                    "k": occ.bit_count(),
                                    "WFT": ws,
                                    "gap": [t, u],
                                    "missing_mid": mid,
                                }
                            )
                            found = True
                            break
                if found:
                    break
            if found:
                break
    b333 = {
        "n_multi_checked": n_checked,
        "violations": len(viol333),
        "examples": viol333[:5],
    }

    # ---- B334: |T*|>=3 but WFT empty ----
    wit334 = []
    n_t3 = 0
    n_t3_we = 0
    for occ in reachable:
        if len(tstar[occ]) >= 3:
            n_t3 += 1
            if len(wft[occ]) == 0:
                n_t3_we += 1
                if len(wit334) < 6:
                    wit334.append(
                        {
                            "occ": occ,
                            "k": occ.bit_count(),
                            "g": g[occ],
                            "Tstar": sorted(tstar[occ]),
                        }
                    )
    b334 = {
        "n_Tstar_ge3": n_t3,
        "n_Tstar_ge3_WFT_empty": n_t3_we,
        "examples": wit334,
    }

    # ---- B335: WFT(empty) singleton equals median of T*(empty) ----
    med_ok = None
    med_val = None
    if len(empty_w) == 1 and empty_t:
        ts = empty_t
        m = len(ts)
        if m % 2 == 1:
            med_val = ts[m // 2]
            med_ok = empty_w[0] == med_val
        else:
            lo, hi = ts[m // 2 - 1], ts[m // 2]
            med_val = [lo, hi]
            med_ok = empty_w[0] in (lo, hi)
    b335 = {
        "WFT_empty": empty_w,
        "Tstar_empty": empty_t,
        "median": med_val,
        "match": med_ok,
    }

    # ---- B337: same (g, T*) but different WFT ----
    groups = defaultdict(list)
    for occ in reachable:
        if not wft[occ]:
            continue
        key = (g[occ], tuple(sorted(tstar[occ])))
        groups[key].append((occ, wft[occ]))
    pairs = []
    n_groups_diff = 0
    for key, lst in groups.items():
        wset = {w for _, w in lst}
        if len(wset) >= 2:
            n_groups_diff += 1
            if len(pairs) < 5:
                by_w = {}
                for occ, w in lst:
                    by_w.setdefault(w, occ)
                ws = list(by_w)
                pairs.append(
                    {
                        "g": key[0],
                        "Tstar": list(key[1]),
                        "occ_A": by_w[ws[0]],
                        "WFT_A": sorted(ws[0]),
                        "occ_B": by_w[ws[1]],
                        "WFT_B": sorted(ws[1]),
                    }
                )
    b337 = {"n_groups_with_diff_WFT": n_groups_diff, "examples": pairs}

    # ---- B340: random average terminal length vs forced length among winning firsts ----
    by_k = defaultdict(list)
    for occ in reachable:
        by_k[occ.bit_count()].append(occ)
    kmax = max(by_k)
    E = {}
    for k in range(kmax, -1, -1):
        for occ in by_k[k]:
            mv = Lc[occ]
            if not mv:
                E[occ] = float(k)
            else:
                E[occ] = sum(E[occ | (1 << u)] for u in mv) / len(mv)

    wins = []
    for u in Lc[0]:
        ch = 1 << u
        if g[ch] == 0:
            wins.append(
                {
                    "first": u,
                    "Tstar_min": min(tstar[ch]),
                    "Tstar_max": max(tstar[ch]),
                    "WFT": sorted(wft[ch]),
                    "WFT_val": sorted(wft[ch])[0] if len(wft[ch]) == 1 else None,
                    "E_term": E[ch],
                }
            )
    b340 = {"winning_firsts": wins}
    if wins and all(w["WFT_val"] is not None for w in wins):
        min_e = min(w["E_term"] for w in wins)
        max_e = max(w["E_term"] for w in wins)
        min_e_set = [w for w in wins if abs(w["E_term"] - min_e) < 1e-12]
        max_e_set = [w for w in wins if abs(w["E_term"] - max_e) < 1e-12]
        wft_vals = [w["WFT_val"] for w in wins]
        min_w, max_w = min(wft_vals), max(wft_vals)
        b340["min_E_firsts"] = [
            {"first": w["first"], "E": w["E_term"], "WFT": w["WFT_val"]} for w in min_e_set
        ]
        b340["max_E_firsts"] = [
            {"first": w["first"], "E": w["E_term"], "WFT": w["WFT_val"]} for w in max_e_set
        ]
        b340["min_E_has_max_WFT"] = bool(
            any(w["WFT_val"] == max_w for w in min_e_set) and max_w > min_w
        )
        b340["max_E_has_min_WFT"] = bool(
            any(w["WFT_val"] == min_w for w in max_e_set) and max_w > min_w
        )
        b340["WFT_range"] = [min_w, max_w]
    else:
        b340["note"] = "not all winning firsts have singleton WFT"

    return {
        "n": n,
        "Tstar_empty": empty_t,
        "WFT_empty": empty_w,
        "B331": b331,
        "B332": b332,
        "B333": b333,
        "B334": b334,
        "B335": b335,
        "B337": b337,
        "B340": b340,
        "n_reachable": len(reachable),
    }


def main() -> None:
    res = {}
    for n in (2, 3, 4, 5):
        print(f"===== WFT n={n} =====", flush=True)
        res[str(n)] = analyze(n)
        r = res[str(n)]
        print(
            json.dumps(
                {
                    "WFT_empty": r["WFT_empty"],
                    "B331": r["B331"]["abs_WFT_le_1"],
                    "B332_n": r["B332"]["n_multi_WFT"],
                    "B333_viol": r["B333"]["violations"],
                    "B334_n": r["B334"]["n_Tstar_ge3_WFT_empty"],
                    "B335": r["B335"]["match"],
                    "B337_n": r["B337"]["n_groups_with_diff_WFT"],
                },
                indent=2,
            ),
            flush=True,
        )

    path = ROOT / "research" / "verification" / "round2_b321.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["wft_stats"] = res
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
