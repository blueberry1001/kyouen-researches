#!/usr/bin/env python3
"""B495 witnesses only (fast)."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round5_b482b500_b495wit.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_rect, board_square_minus  # noqa: E402


def reach_all(board, recs):
    by_occ = {r["occ"]: r for r in recs}
    rows_asc = sorted(recs, key=lambda r: r["k"])
    reach = {0: 1.0}
    for r in rows_asc:
        occ = r["occ"]
        if occ == 0:
            continue
        p = 0.0
        for i in range(board.V):
            if (occ >> i) & 1:
                par = occ ^ (1 << i)
                pr = by_occ.get(par)
                if pr is not None and par in reach:
                    p += reach[par] / pr["nL"]
        reach[occ] = p
    return reach


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


def hist_reach_witness(board, recs):
    by_occ = {r["occ"]: r for r in recs}
    reach = reach_all(board, recs)
    maximals = [r for r in recs if r["nL"] == 0]
    mfeat = []
    for r in maximals:
        m = r["occ"]
        bits = [i for i in range(board.V) if (m >> i) & 1]
        sz = len(bits)
        byk_L = defaultdict(list)
        full = 1 << sz
        for sub in range(1, full - 1):
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
            byk_L[pr["k"]].append(pr["nL"])
        hist = tuple(sorted((k, nL) for k, vs in byk_L.items() for nL in vs))
        mfeat.append({
            "occ": m, "sz": sz, "reach": reach.get(m, 0.0),
            "hist_full": hist,
            "coords": [list(board.points[i]) for i in bits],
        })
    by_full = defaultdict(list)
    for m in mfeat:
        by_full[m["hist_full"]].append(m)
    witnesses = []
    for gk, gs in by_full.items():
        if len(gs) < 2:
            continue
        rs = [g["reach"] for g in gs]
        if max(rs) - min(rs) <= 1e-15:
            continue
        ratio = (max(rs) / min(rs)) if min(rs) > 0 else float("inf")
        imax = rs.index(max(rs))
        imin = rs.index(min(rs))
        witnesses.append({
            "group_size": len(gs),
            "ratio": ratio if ratio != float("inf") else "inf",
            "reach_max": max(rs), "reach_min": min(rs),
            "max_coords": gs[imax]["coords"],
            "min_coords": gs[imin]["coords"],
            "sz": gs[imax]["sz"],
            "hist_len": len(gk),
            "hist_sample": [list(x) for x in gk[:10]],
        })
    witnesses.sort(key=lambda z: (
        0 if z["ratio"] == "inf" else -z["ratio"] if isinstance(z["ratio"], (int, float)) else 0))
    return {"n_max": len(mfeat), "n_states": len(recs),
            "n_witness_groups": len(witnesses), "witnesses": witnesses[:8]}


def main():
    out = {}
    for label, brd in [
        ("3x5", board_rect(3, 5)),
        ("4x4-1pt", board_square_minus(4, [(0, 0)])),
        ("3x4", board_rect(3, 4)),
    ]:
        print(label, flush=True)
        recs = enumerate_states(brd)
        print("  states", len(recs), flush=True)
        out[label] = hist_reach_witness(brd, recs)
        print("  witness groups", out[label]["n_witness_groups"],
              "top ratio", out[label]["witnesses"][0]["ratio"] if out[label]["witnesses"] else None,
              flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
