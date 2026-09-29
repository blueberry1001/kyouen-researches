#!/usr/bin/env python3
"""Verify B495 witnesses with exact Fraction reach; B489 top cells; B499 inf pair."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round5_b482b500_verify.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_rect, board_square_minus, board_square  # noqa: E402

CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
FEAT_CACHE = ROOT / "research" / "verification" / "round5_b482b500_feats.pkl"
import pickle


def enumerate_states(board):
    seen = {0}
    stack = [0]
    states = []
    while stack:
        occ = stack.pop()
        states.append(occ)
        for u in board.legal_moves(occ):
            ch = occ | (1 << u)
            if ch not in seen:
                seen.add(ch)
                stack.append(ch)
    recs = []
    for occ in states:
        mv = board.legal_moves(occ)
        recs.append({"occ": occ, "k": occ.bit_count(), "nL": len(mv),
                     "L": sum(1 << u for u in mv)})
    return recs


def exact_reach(board, recs, targets):
    """Fraction reach for all states, return reach of targets."""
    by_occ = {r["occ"]: r for r in recs}
    rows_asc = sorted(recs, key=lambda r: r["k"])
    reach = {0: Fraction(1)}
    for r in rows_asc:
        occ = r["occ"]
        if occ == 0:
            continue
        p = Fraction(0)
        for i in range(board.V):
            if (occ >> i) & 1:
                par = occ ^ (1 << i)
                pr = by_occ.get(par)
                if pr is not None and par in reach:
                    p += reach[par] / pr["nL"]
        reach[occ] = p
    return {t: reach.get(t, Fraction(0)) for t in targets}


def main():
    out = {}

    # ---- B495 exact verify ----
    print("B495 exact", flush=True)
    cases = [
        ("3x5", board_rect(3, 5), [
            [(0, 0), (0, 1), (1, 1), (1, 3), (1, 4), (2, 4)],
            [(1, 0), (2, 0), (2, 1), (1, 3), (0, 4), (1, 4)],
        ]),
        ("4x4-1pt", board_square_minus(4, [(0, 0)]), [
            [(3, 1), (0, 2), (1, 2), (0, 3), (2, 3), (3, 3)],
            [(3, 0), (2, 1), (0, 2), (1, 3), (2, 3), (3, 3)],
        ]),
    ]
    out["B495_exact"] = {}
    for label, brd, pair in cases:
        print(" ", label, flush=True)
        recs = enumerate_states(brd)
        # map coords to occ
        pt_index = {p: i for i, p in enumerate(brd.points)}
        occs = []
        for coords in pair:
            m = 0
            for c in coords:
                m |= 1 << pt_index[tuple(c)]
            occs.append(m)
        # also verify they are maximal and hist matches
        by_occ = {r["occ"]: r for r in recs}

        def full_hist(m):
            bits = [i for i in range(brd.V) if (m >> i) & 1]
            sz = len(bits)
            byk = defaultdict(list)
            for sub in range(1, (1 << sz) - 1):
                occ = 0
                bb = sub
                j = 0
                while bb:
                    if bb & 1:
                        occ |= 1 << bits[j]
                    bb >>= 1
                    j += 1
                pr = by_occ.get(occ)
                if pr is None:
                    continue
                byk[pr["k"]].append(pr["nL"])
            return tuple(sorted((k, nL) for k, vs in byk.items() for nL in vs))

        h0, h1 = full_hist(occs[0]), full_hist(occs[1])
        rs = exact_reach(brd, recs, occs)
        r0, r1 = rs[occs[0]], rs[occs[1]]
        ratio = (r0 / r1) if r1 != 0 else None
        out["B495_exact"][label] = {
            "n_states": len(recs),
            "occ": occs,
            "is_maximal": [by_occ[m]["nL"] == 0 for m in occs],
            "hist_equal": h0 == h1,
            "hist_len": len(h0),
            "reach_frac": [str(r0), str(r1)],
            "reach_float": [float(r0), float(r1)],
            "ratio_frac": str(ratio) if ratio is not None else None,
            "ratio_float": float(ratio) if ratio is not None else None,
            "coords": pair,
        }
        print("   hist_equal", h0 == h1, "ratio", ratio, flush=True)

    # ---- B489 top gap cells ----
    print("B489 cells", flush=True)
    with open(FEAT_CACHE, "rb") as f:
        feats_all = pickle.load(f)
    with open(CACHE, "rb") as f:
        cache = pickle.load(f)
    # recompute T*/WFT for n=5 quickly using the same DP
    recs5 = cache[5]["recs"]
    by_occ = {r["occ"]: r for r in recs5}
    rows_desc = sorted(recs5, key=lambda r: -r["k"])
    T = {}
    W = {}
    for r in rows_desc:
        occ = r["occ"]
        L = r["L"]
        if L == 0:
            T[occ] = frozenset({r["k"]})
            W[occ] = frozenset({r["k"]})
            continue
        g = r["g"]
        ch_list = []
        v = 0
        Lm = L
        while Lm:
            if Lm & 1:
                ch_list.append(occ | (1 << v))
            Lm >>= 1
            v += 1
        if g == 0:
            acc_t = set()
            acc_w = None
            for ch in ch_list:
                acc_t |= T[ch]
                s = W[ch]
                acc_w = set(s) if acc_w is None else (acc_w & set(s))
            T[occ] = frozenset(acc_t)
            W[occ] = frozenset(acc_w or set())
        else:
            acc_t = set()
            acc_w = set()
            for ch in ch_list:
                if by_occ[ch]["g"] == 0:
                    acc_t |= T[ch]
                    acc_w |= W[ch]
            if not acc_t:
                for ch in ch_list:
                    acc_t |= T[ch]
                    acc_w |= W[ch]
            T[occ] = frozenset(acc_t)
            W[occ] = frozenset(acc_w)

    feats = feats_all[5]
    by = defaultdict(list)
    for occ, f in feats.items():
        if f["nL"] == 0:
            continue
        ts = T[occ]
        ws = W[occ]
        span_t = (max(ts) - min(ts)) if ts else 0
        min_w = min(ws) if ws else 0
        wft_short = min_w - f["k"] if ws else 0
        by[(f["k"], f["nL"])].append({
            "span_t": span_t, "min_w": min_w, "wft_short": wft_short,
            "illusion": f["illusion"], "g": f["g"], "occ": occ,
        })
    cells = []
    for key, rs in sorted(by.items()):
        if len(rs) < 8:
            continue
        if len(set(r["span_t"] for r in rs)) < 2:
            continue
        med = sorted(r["span_t"] for r in rs)[len(rs) // 2]
        hi = [r for r in rs if r["span_t"] >= med]
        lo = [r for r in rs if r["span_t"] < med]
        if not hi or not lo:
            continue
        mi = sum(r["illusion"] for r in hi) / len(hi)
        ml = sum(r["illusion"] for r in lo) / len(lo)
        # also min_w split
        medw = sorted(r["min_w"] for r in rs)[len(rs) // 2]
        hiw = [r for r in rs if r["min_w"] <= medw]  # small WFT
        low = [r for r in rs if r["min_w"] > medw]
        miw = sum(r["illusion"] for r in hiw) / len(hiw) if hiw else None
        mlw = sum(r["illusion"] for r in low) / len(low) if low else None
        cells.append({
            "k": key[0], "nL": key[1], "n": len(rs),
            "gap_span": mi - ml,
            "gap_smallwft": (miw - mlw) if (miw is not None and mlw is not None) else None,
        })
    cells.sort(key=lambda z: -abs(z["gap_span"]))
    out["B489_cells"] = {
        "n_cells": len(cells),
        "gap_span_pos": sum(1 for c in cells if c["gap_span"] > 0),
        "gap_span_neg": sum(1 for c in cells if c["gap_span"] < 0),
        "gap_wft_pos": sum(1 for c in cells if c["gap_smallwft"] is not None and c["gap_smallwft"] > 0),
        "gap_wft_neg": sum(1 for c in cells if c["gap_smallwft"] is not None and c["gap_smallwft"] < 0),
        "top": cells[:12],
    }
    print("  cells", out["B489_cells"]["n_cells"],
          "span_pos", out["B489_cells"]["gap_span_pos"],
          "wft_pos", out["B489_cells"]["gap_wft_pos"], flush=True)

    # ---- B499 inf pair details ----
    print("B499 pair", flush=True)
    with open(ROOT / "research" / "verification" / "round5_b482b500_followup.json") as f:
        prev = json.load(f)
    b499 = prev["B499"]["5"]
    out["B499_pair"] = {
        "closest_zero_pos": b499["closest_zero_pos"],
        "inf_pairs_w005": b499["w0.05"]["inf_pairs"],
        "n_zero": b499["n_zero_pmin"],
        "n_pos": b499["n_pos_pmin"],
        "E_range": b499["E_range"],
        "Pmin_range": b499["Pmin_range"],
    }
    # also best finite pair
    out["B499_pair"]["best_finite"] = b499["w0.05"]["best_pair"]

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
