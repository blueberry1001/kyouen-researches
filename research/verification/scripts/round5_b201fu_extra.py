#!/usr/bin/env python3
"""Follow-up extras: B216 K on 4xm, B222 line-only W agreement, B218 area-matched."""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_rect, is_forbidden_quad  # noqa: E402

OUTDIR = Path(__file__).resolve().parents[1]


def save(name, obj):
    p = OUTDIR / f"round5_b201fu_{name}.json"
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {p}", flush=True)


def area2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def is_coll4(p4):
    return all(
        area2(p4[a], p4[b], p4[c]) == 0
        for a, b, c in [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    )


def variant(w, h, mode):
    pts = [(x, y) for y in range(h) for x in range(w)]
    V = w * h
    quads = []
    n_coll = n_circ = 0
    for ids in combinations(range(V), 4):
        p4 = [pts[t] for t in ids]
        if not is_forbidden_quad(p4):
            continue
        col = is_coll4(p4)
        if col:
            n_coll += 1
        else:
            n_circ += 1
        if mode == "std" or (mode == "circ" and not col) or (mode == "line" and col):
            quads.append(ids)
    b = Board(pts, name=f"{w}x{h}-{mode}")
    b.quads = []
    b.quads_by_pt = [[] for _ in range(V)]
    for ids in quads:
        m = 0
        for i in ids:
            m |= 1 << i
        b.quads.append(m)
        for i in ids:
            b.quads_by_pt[i].append(m)
    g = b.solve_grundy()
    K = max(occ.bit_count() for occ in g)
    W = [u for u in b.legal_moves(0) if g.get(1 << u, 0) == 0]
    return {
        "g0": g[0],
        "K": K,
        "W": len(W),
        "W_list": W,
        "npos": len(g),
        "nq": len(quads),
        "n_coll": n_coll,
        "n_circ": n_circ,
    }


def job_b216(m_list):
    """K = max_safe_size for 4 x m (B216)."""
    rows = []
    for m in m_list:
        t0 = time.time()
        b = board_rect(4, m)
        K = b.max_safe_size()
        rows.append({"w": 4, "m": m, "V": 4 * m, "K": K, "sec": round(time.time() - t0, 2)})
        print(f"  4x{m} K={K} {rows[-1]['sec']}s", flush=True)
    save("b216_k4xm", {"rows": rows})


def job_b222(pairs):
    """Line-only vs standard: look for nonempty W agreement (B222)."""
    rows = []
    for w, h in pairs:
        rec = {"w": w, "h": h}
        for mode in ["std", "line"]:
            t0 = time.time()
            r = variant(w, h, mode)
            r["sec"] = round(time.time() - t0, 2)
            rec[mode] = r
            print(
                f"  {w}x{h} {mode}: g0={r['g0']} K={r['K']} |W|={r['W']} pos={r['npos']} {r['sec']}s",
                flush=True,
            )
        std = rec["std"]
        line = rec["line"]
        rec["winner_agree"] = (std["g0"] == 0) == (line["g0"] == 0)
        rec["W_agree"] = std["W_list"] == line["W_list"]
        rec["W_nonempty"] = std["W"] > 0 or line["W"] > 0
        rec["nonempty_triple_agree"] = rec["winner_agree"] and rec["W_agree"] and rec["W_nonempty"]
        print(
            f"    winner_agree={rec['winner_agree']} W_agree={rec['W_agree']} "
            f"nonempty={rec['W_nonempty']} TRIPLE={rec['nonempty_triple_agree']}",
            flush=True,
        )
        rows.append(rec)
    save(
        "b222_line",
        {
            "rows": rows,
            "n_triple": sum(1 for r in rows if r["nonempty_triple_agree"]),
        },
    )


def job_b218_area():
    """Area-matched comparison: 2x6 (area 12) vs 3x4 (area 12) (B218)."""
    rows = []
    for w, h in [(2, 6), (3, 4), (2, 8), (4, 4), (3, 5), (2, 5), (3, 6)]:
        rec = {"w": w, "h": h, "area": w * h, "aspect": max(w, h) / min(w, h)}
        for mode in ["std", "circ"]:
            r = variant(w, h, mode)
            rec[mode] = {k: r[k] for k in ["g0", "K", "W", "npos", "nq", "n_coll", "n_circ"]}
        rec["winner_flip"] = (rec["std"]["g0"] == 0) != (rec["circ"]["g0"] == 0)
        rec["coll_frac"] = (
            rec["std"]["n_coll"] / rec["std"]["nq"] if rec["std"]["nq"] else 0
        )
        print(
            f"  {w}x{h} area={w*h} ar={rec['aspect']:.2f} "
            f"flip={rec['winner_flip']} coll%={100*rec['coll_frac']:.0f} "
            f"std_g0={rec['std']['g0']} circ_g0={rec['circ']['g0']}",
            flush=True,
        )
        rows.append(rec)
    save("b218_area", {"rows": rows})


if __name__ == "__main__":
    job = sys.argv[1]
    if job == "b216":
        job_b216([int(x) for x in sys.argv[2:]])
    elif job == "b222":
        pairs = [(2, 5), (2, 7), (3, 4), (3, 8), (2, 4), (4, 5)]
        job_b222(pairs)
    elif job == "b218":
        job_b218_area()
    else:
        print("unknown", job)
