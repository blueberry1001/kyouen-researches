#!/usr/bin/env python3
"""Follow-up details: B495 witnesses on 3x5 / 4x4-1pt, B490 richer keys."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round5_b482b500_followup2.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, board_rect, board_square, board_square_minus  # noqa: E402
import pickle

CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
FEAT_CACHE = ROOT / "research" / "verification" / "round5_b482b500_feats.pkl"


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
                     "L": sum(1 << u for u in mv), "g": 0, "stab": 1})
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
            "coords": [board.points[i] for i in bits],
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
        if min(rs) <= 0:
            ratio = float("inf") if max(rs) > 0 else 1.0
        else:
            ratio = max(rs) / min(rs)
        imax = rs.index(max(rs))
        imin = rs.index(min(rs))
        witnesses.append({
            "group_size": len(gs),
            "ratio": ratio if ratio != float("inf") else "inf",
            "reach_max": max(rs), "reach_min": min(rs),
            "max_coords": gs[imax]["coords"],
            "min_coords": gs[imin]["coords"],
            "sz": gs[imax]["sz"],
            "hist_head": list(gk[:12]),
            "hist_len": len(gk),
        })
    witnesses.sort(key=lambda z: (0 if z["ratio"] == "inf" else -z["ratio"] if isinstance(z["ratio"], (int, float)) else 0))
    return {"n_max": len(mfeat), "n_witness_groups": len(witnesses),
            "witnesses": witnesses[:8]}


def b490_rich(n, feats):
    rows = list(feats.values())
    # richer keys: include b_hist, u_hist hashes and more
    results = []

    def run(fields, keyfn, label):
        by = defaultdict(list)
        for r in rows:
            by[keyfn(r)].append(r)
        cg = ch = cm = c3 = 0
        nkeys = 0
        for k, rs in by.items():
            if len(rs) < 2:
                continue
            nkeys += 1
            gs = set(r["g"] for r in rs)
            ms = set(r["mu"] for r in rs)
            hs = set(r["hmax"] for r in rs)
            if len(gs) > 1:
                cg += 1
            if len(hs) > 1:
                ch += 1
            if len(ms) > 1:
                cm += 1
            if len(gs) > 1 and len(ms) > 1 and len(hs) > 1:
                c3 += 1
        results.append({
            "label": label, "fields": fields,
            "n_multi_keys": nkeys,
            "coll_g": cg, "coll_mu": cm, "coll_h": ch, "coll_3": c3,
            "sep_g": cg == 0, "sep_mu": cm == 0, "sep_h": ch == 0,
        })

    # 1) full local signature
    def sig(r):
        return (r["k"], r["nL"], r["stab"], r["n_b1"], r["b_max"], r["n_bpos"],
                round(r["b_var"], 4), r["n_distinct_u"], r["u_max"], r["u_min"],
                round(r["u_ent"], 4), r["b_hist"], r["u_hist"])
    run(["full_sig"], sig, "full_sig")

    # 2) full_sig without b_hist
    def sig2(r):
        return (r["k"], r["nL"], r["stab"], r["n_b1"], r["b_max"], r["n_bpos"],
                round(r["b_var"], 4), r["n_distinct_u"], r["u_max"], r["u_min"],
                round(r["u_ent"], 4))
    run(["sig_no_hist"], sig2, "sig_no_hist")

    # 3) search for coll_g=0 keys (g perfect) among combos of up to 6 scalar fields
    fields = ["k", "nL", "stab", "n_b1", "b_max", "n_bpos", "b_var",
              "n_distinct_u", "u_max", "u_min", "u_ent"]
    found_g = None
    found_mu = None
    found_h = None
    for r in range(1, 6):
        for combo in combinations(fields, r):
            def keyfn(r, combo=combo):
                return tuple((round(r[f], 4) if f in ("b_var", "u_ent") else r[f]) for f in combo)
            by = defaultdict(list)
            for rr in rows:
                by[keyfn(rr)].append(rr)
            cg = ch = cm = 0
            for k, rs in by.items():
                if len(rs) < 2:
                    continue
                if len(set(x["g"] for x in rs)) > 1:
                    cg += 1
                if len(set(x["hmax"] for x in rs)) > 1:
                    ch += 1
                if len(set(x["mu"] for x in rs)) > 1:
                    cm += 1
            if cg == 0 and found_g is None:
                found_g = {"combo": list(combo), "coll_mu": cm, "coll_h": ch}
            if cm == 0 and found_mu is None:
                found_mu = {"combo": list(combo), "coll_g": cg, "coll_h": ch}
            if ch == 0 and found_h is None:
                found_h = {"combo": list(combo), "coll_g": cg, "coll_mu": cm}
        if found_g and found_mu and found_h:
            break
    results.append({"label": "search_perfect_axis",
                    "sep_g_key": found_g, "sep_mu_key": found_mu, "sep_h_key": found_h})
    return results


def main():
    out = {}
    # ---- B495 witnesses ----
    print("B495 witnesses", flush=True)
    out["B495"] = {}
    for label, brd in [
        ("3x5", board_rect(3, 5)),
        ("4x4-1pt", board_square_minus(4, [(0, 0)])),
        ("3x4", board_rect(3, 4)),
    ]:
        print(" ", label, flush=True)
        recs = enumerate_states(brd)
        out["B495"][label] = hist_reach_witness(brd, recs)
        out["B495"][label]["n_states"] = len(recs)

    # ---- B490 richer ----
    print("B490 rich", flush=True)
    with open(FEAT_CACHE, "rb") as f:
        feats_all = pickle.load(f)
    out["B490"] = {}
    for n in (3, 4, 5):
        print(" n", n, flush=True)
        out["B490"][str(n)] = b490_rich(n, feats_all[n])

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
