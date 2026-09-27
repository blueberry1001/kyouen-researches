#!/usr/bin/env python3
"""Quick n=4 pair-deletion scan for B204/B207/B209 (cheap, seconds)."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square, board_square_minus  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "batch09_pairs_n4.json"


def summ(b):
    g = b.solve_grundy()
    return {"g": g[0], "K": max(x.bit_count() for x in g), "n": len(g),
            "winner": "F" if g[0] != 0 else "S"}


def main():
    full = board_square(4)
    fs = summ(full)
    singles = {}
    for p in range(16):
        singles[p] = summ(board_square_minus(4, [(p % 4, p // 4)]))
    rows = []
    for p, q in itertools.combinations(range(16), 2):
        b = board_square_minus(4, [(p % 4, p // 4), (q % 4, q // 4)])
        s = summ(b)
        sp, sq = singles[p], singles[q]
        rows.append({
            "p": p, "q": q,
            "g_pair": s["g"], "g_p": sp["g"], "g_q": sq["g"], "g_full": fs["g"],
            "K_pair": s["K"], "K_p": sp["K"], "K_q": sq["K"], "K_full": fs["K"],
            "flip_pair": s["winner"] != fs["winner"],
            "flip_p": sp["winner"] != fs["winner"],
            "flip_q": sq["winner"] != fs["winner"],
            "K_loss_additive": (fs["K"] - s["K"]) == (fs["K"] - sp["K"]) + (fs["K"] - sq["K"]),
            "g_combo_effect": s["g"] not in (sp["g"], sq["g"]),
        })
    n_flip_pair = sum(r["flip_pair"] for r in rows)
    n_k_drop = sum(1 for r in rows if r["K_pair"] < fs["K"])
    n_add = sum(r["K_loss_additive"] for r in rows)
    n_combo = sum(r["g_combo_effect"] for r in rows)
    b204 = [r for r in rows if r["flip_pair"] and not r["flip_p"] and not r["flip_q"]]
    b207 = [r for r in rows if r["K_loss_additive"] and r["g_combo_effect"]]
    out = {
        "full": fs,
        "n_pairs": len(rows),
        "n_flip_pair": n_flip_pair,
        "n_K_drop": n_k_drop,
        "n_K_loss_additive": n_add,
        "n_g_combo_effect": n_combo,
        "B204_witnesses": b204[:10],
        "B207_witnesses": b207[:10],
        "rows": rows,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("full", fs)
    print("pairs", len(rows), "flip_pair", n_flip_pair, "K_drop", n_k_drop,
          "additive", n_add, "g_combo", n_combo)
    print("B204", len(b204), "B207", len(b207))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
