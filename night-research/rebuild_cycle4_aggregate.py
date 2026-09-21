#!/usr/bin/env python3
"""Regenerate cycle4-exact-structure.json as a true n=2..5 aggregate."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

NR = Path(__file__).resolve().parent


def main() -> None:
    boards = []
    mobility_all = {}
    for n in (2, 3, 4, 5):
        d = json.loads((NR / f"cycle4-exact-n{n}.json").read_text(encoding="utf-8"))
        boards.append(d["board"])
        mobility_all[str(n)] = d["first_move_mobility"]
    density = json.loads((NR / "cycle4-density-table.json").read_text(encoding="utf-8"))
    audit = json.loads((NR / "cycle4-invariant-audit.json").read_text(encoding="utf-8"))
    out = {
        "density": density,
        "boards": boards,
        "first_move_mobility": mobility_all,
        "invariant_audit": audit,
        "player_to_move_note": (
            "Outcomes are for the player to move. At k=1, LOSS count equals "
            "winning-first-move count; WIN count equals losing-first-move count."
        ),
        "authoritative_per_board_files": [f"cycle4-exact-n{n}.json" for n in (2, 3, 4, 5)],
    }
    path = NR / "cycle4-exact-structure.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {path} boards={[b['n'] for b in boards]}")
    for b in boards:
        k1 = next(r for r in b["depth_profile"] if r["k"] == 1)
        print(
            f"  n={b['n']} empty={b['empty_outcome']} "
            f"k1_loss={k1['loss']} k1_loss_rate={k1['loss_rate']:.4f} "
            f"mobility_win={b['mobility_winning_first_moves']}"
        )


if __name__ == "__main__":
    main()
