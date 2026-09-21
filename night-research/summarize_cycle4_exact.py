#!/usr/bin/env python3
"""Summarize Cycle 4 exact artifacts and compute F/S invariant audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NR = ROOT / "night-research"


def load_board(n: int) -> dict:
    return json.loads((NR / f"cycle4-exact-n{n}.json").read_text(encoding="utf-8"))


def main() -> None:
    sizes = [2, 3, 4, 5]
    rows = []
    for n in sizes:
        d = load_board(n)
        b = d["board"]
        mob = d["first_move_mobility"]
        prof = b["depth_profile"]
        # interior LOSS-rate peak among k with safe>1, excluding k=0 and terminal-all-loss layers
        interior = [
            r
            for r in prof
            if r["k"] >= 1
            and r["safe"] > 1
            and not (r["loss"] == r["safe"] and r["k"] == max(x["k"] for x in prof))
        ]
        peak = max(interior, key=lambda r: r["loss_rate"]) if interior else None
        win = [r for r in mob if r["result_for_first_player"] == "WIN"]
        loss = [r for r in mob if r["result_for_first_player"] == "LOSS"]
        # parity check on depth profile
        odd_loss = all(
            r["loss"] == r["safe"] for r in prof if r["k"] % 2 == 1 and r["k"] > 0
        )
        even_win = all(r["loss"] == 0 for r in prof if r["k"] % 2 == 0 and r["k"] > 0)
        parity_locked = odd_loss and even_win and any(r["k"] % 2 == 1 for r in prof)
        rows.append(
            {
                "n": n,
                "winner": b["expected_winner"],
                "forbidden": b["forbidden_quadruples"],
                "reachable": b["reachable_safe_sets"],
                "density": b["mobility_density"],
                "winning_first_moves": len(win),
                "parity_locked_outcomes": parity_locked,
                "interior_peak": peak,
                "profile": prof,
                "win_reply_counts": Counter(r["legal_reply_count"] for r in win),
                "loss_second_win_reply_counts": Counter(
                    r["second_player_winning_reply_count"] for r in loss
                ),
                "win_second_win_reply_counts": Counter(
                    r["second_player_winning_reply_count"] for r in win
                ),
                "all_first_reply_counts": Counter(r["legal_reply_count"] for r in mob),
            }
        )
        print(f"\n===== n={n} winner={b['expected_winner']} =====")
        print(f"forbidden={b['forbidden_quadruples']} reachable={b['reachable_safe_sets']}")
        print(f"density={b['mobility_density']} winning_first={len(win)}/{n*n}")
        print(f"parity_locked={parity_locked}")
        print(f"interior_peak={peak}")
        print("depth profile k safe loss rate:")
        for r in prof:
            rate = r["loss_rate"]
            print(f"  k={r['k']:2d} safe={r['safe']:6d} loss={r['loss']:6d} rate={rate:.4f}")
        print(f"legal reply counts all first moves: {dict(Counter(r['legal_reply_count'] for r in mob))}")
        print(f"second-player winning reply counts on LOSS first moves: {dict(Counter(r['second_player_winning_reply_count'] for r in loss))}")
        print(f"second-player winning reply counts on WIN first moves: {dict(Counter(r['second_player_winning_reply_count'] for r in win))}")

    # known larger boards
    larger = {
        6: {"winner": "F", "density": 1.0, "winning_first_moves": 36, "source": "certificates/prior"},
        7: {"winner": "S", "density": 0.0, "winning_first_moves": 0, "source": "certificates/prior"},
        8: {"winner": "S", "density": 0.0, "winning_first_moves": 0, "source": "certificates/prior"},
        9: {
            "winner": "F",
            "density": 1.0,
            "winning_first_moves": 81,
            "source": "CYCLE3 first-moves-9x9.csv",
        },
        10: {"winner": "S", "density": 0.0, "winning_first_moves": 0, "source": "10x10 probes"},
    }

    f_boards = [1, 2, 3, 5, 6, 9]
    s_boards = [4, 7, 8, 10]
    audit = {
        "exact_boards_measured": sizes,
        "candidates": [
            {
                "quantity": "empty-board winner F/S",
                "separates_F_S": True,
                "note": "definitional, not predictive",
            },
            {
                "quantity": "winning-first-move density",
                "F": {n: (1.0 if n != 5 else 0.36) for n in f_boards},
                "S": {n: 0.0 for n in s_boards},
                "separates_F_S": True,
                "note": "density=0 on S-boards is definitional; non-trivial content is density=1 on all F n<=9 except n=5",
            },
            {
                "quantity": "parity-locking of all reachable safe-set outcomes by k mod 2",
                "exact": {str(n): next(r["parity_locked_outcomes"] for r in rows if r["n"] == n) for n in sizes},
                "separates_F_S": False,
                "note": "holds for n=2,3 (F-boards) and fails on n=4 (S) and n=5 (F); not an F/S separator",
            },
            {
                "quantity": "legal reply count after any first move",
                "exact": {str(n): dict(next(r["all_first_reply_counts"] for r in rows if r["n"] == n)) for n in sizes},
                "separates_F_S": False,
                "note": "on n=2..5 every first move leaves exactly n*n-1 legal replies (1-stone positions never illegal)",
            },
            {
                "quantity": "mean legal replies after first move (win vs loss)",
                "n5": {"win": 24.0, "loss": 24.0},
                "separates_F_S": False,
                "note": "reply mobility does not distinguish winning vs losing first moves on n=5",
            },
            {
                "quantity": "second-player winning-reply multiplicity after first move",
                "n4_S_all_loss": "9 or 12 winning second replies depending on first-move orbit",
                "n5_F": "0 on all 9 WIN first moves; 2 or 4 on LOSS first moves",
                "separates_local_outcome": True,
                "note": "sharp discriminator on n=5: WIN first move iff opponent winning-reply count = 0",
            },
            {
                "quantity": "forbidden quadruple count",
                "values": {2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564, 9: 29152, 10: 54441},
                "separates_F_S": False,
                "note": "monotone in n; does not match F/S pattern",
            },
            {
                "quantity": "H-dense (among F-win n<=10, only n=5 has a losing first move)",
                "status": "SUPPORTED on complete data",
                "separates_F_S": False,
                "note": "characterizes exceptional F-board, not S-boards",
            },
        ],
        "rows": [
            {
                "n": r["n"],
                "winner": r["winner"],
                "density": r["density"],
                "parity_locked": r["parity_locked_outcomes"],
                "reachable": r["reachable"],
            }
            for r in rows
        ],
        "larger_boards_from_prior_work": larger,
    }

    out = {
        "exact_rows": [
            {
                **{k: v for k, v in r.items() if k != "profile"},
                "profile": r["profile"],
                "win_reply_counts": {str(k): v for k, v in r["win_reply_counts"].items()},
                "loss_second_win_reply_counts": {
                    str(k): v for k, v in r["loss_second_win_reply_counts"].items()
                },
                "win_second_win_reply_counts": {
                    str(k): v for k, v in r["win_second_win_reply_counts"].items()
                },
                "all_first_reply_counts": {
                    str(k): v for k, v in r["all_first_reply_counts"].items()
                },
            }
            for r in rows
        ],
        "invariant_audit": audit,
    }
    path = NR / "cycle4-invariant-audit.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
