#!/usr/bin/env python3
"""B538/B539: circle-only vs line-only vs combined (standard) synergy witnesses.

For every occupied set S that is safe under the standard rule (hence under
both sub-families), compute g_circles(S), g_lines(S), g_standard(S).

B538: exists S with both sub-families P (g=0) but combined N (g!=0).
B539: exists S with both sub-families N (g!=0) but combined P (g=0).

Primary board 4x4 (cheap, complete). Secondary 5x5 if time allows.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch10_core import Game, classify_quads, grundy_map  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round2_b531.json"


def analyze(n: int) -> dict:
    t0 = time.time()
    coll, circ = classify_quads(n)
    std = coll + circ
    games = {
        "circles": Game(n, circ),
        "lines": Game(n, coll),
        "standard": Game(n, std),
    }
    gms = {}
    for name, gme in games.items():
        t1 = time.time()
        gms[name] = grundy_map(gme, 0)
        print(f"  n={n} {name}: pos={len(gms[name])} ({time.time()-t1:.1f}s)", flush=True)

    b538 = []
    b539 = []
    both_p_comb_n = 0
    both_n_comb_p = 0
    disagree = 0
    # iterate over states present in standard map (safe under standard)
    for S, g_std in gms["standard"].items():
        g_c = gms["circles"].get(S)
        g_l = gms["lines"].get(S)
        if g_c is None or g_l is None:
            # should not happen: standard-safe implies sub-family-safe
            continue
        p_c = g_c == 0
        p_l = g_l == 0
        p_s = g_std == 0
        if p_c and p_l and not p_s:
            both_p_comb_n += 1
            if len(b538) < 20:
                b538.append(
                    {
                        "S": S,
                        "popcount": S.bit_count(),
                        "g_circles": g_c,
                        "g_lines": g_l,
                        "g_std": g_std,
                    }
                )
        if (not p_c) and (not p_l) and p_s:
            both_n_comb_p += 1
            if len(b539) < 20:
                b539.append(
                    {
                        "S": S,
                        "popcount": S.bit_count(),
                        "g_circles": g_c,
                        "g_lines": g_l,
                        "g_std": g_std,
                    }
                )
        if p_c != p_s or p_l != p_s:
            disagree += 1

    # smallest-popcount witnesses
    b538.sort(key=lambda d: d["popcount"])
    b539.sort(key=lambda d: d["popcount"])
    return {
        "n": n,
        "n_std_pos": len(gms["standard"]),
        "n_circ_pos": len(gms["circles"]),
        "n_line_pos": len(gms["lines"]),
        "b538_count": both_p_comb_n,
        "b539_count": both_n_comb_p,
        "b538_examples": b538,
        "b539_examples": b539,
        "n_pn_disagreements": disagree,
        "seconds": round(time.time() - t0, 1),
    }


def main():
    out = {}
    for n in (3, 4, 5):
        print(f"[b538/539] n={n}", flush=True)
        try:
            out[f"n{n}"] = analyze(n)
        except Exception as e:
            out[f"n{n}"] = {"error": str(e)}
            print("  error", e, flush=True)

    path = OUT
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("b538_synergy", {}).update(out)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
