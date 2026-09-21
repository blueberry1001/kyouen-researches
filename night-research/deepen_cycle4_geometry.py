#!/usr/bin/env python3
"""Deepen Cycle 4: n=5 two-stone LOSS geometry + cross-board invariants."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

NR = Path(__file__).resolve().parent
sys.path.insert(0, str(NR))
from exact_structure_cycle4 import (  # noqa: E402
    build_index,
    forbidden_quads,
    legal_moves,
    outcomes_table,
)


def coords(i: int, n: int) -> list[int]:
    return [i % n, i // n]


def main() -> None:
    n = 5
    quads = forbidden_quads(n)
    qb, _ = build_index(n, quads)
    outc = outcomes_table(n, qb)
    V = n * n

    loss_pairs = []
    for a, b in combinations(range(V), 2):
        occ = (1 << a) | (1 << b)
        ok = True
        for i in (a, b):
            for q in qb[i]:
                if (q & occ) == q:
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue
        if outc.get(occ) != 0:
            continue
        replies = legal_moves(occ, V, qb)
        win_replies = [r for r in replies if outc.get(occ | (1 << r)) == 0]
        # geometric descriptors
        ax, ay = coords(a, n)
        bx, by = coords(b, n)
        dx, dy = abs(ax - bx), abs(ay - by)
        chebyshev = max(dx, dy)
        manhattan = dx + dy
        # are both on even sublattice?
        def cell_class(x, y):
            if (x + y) % 2 == 1:
                return "odd-sum"
            if (x, y) in {(0, 0), (0, 4), (4, 0), (4, 4)}:
                return "corner"
            return "even-win"

        ca, cb = cell_class(ax, ay), cell_class(bx, by)
        # is pair a subset of some known winning-reply edge from first-move analysis?
        loss_pairs.append(
            {
                "ids": [a, b],
                "coords": [[ax, ay], [bx, by]],
                "cell_classes": [ca, cb],
                "dx": dx,
                "dy": dy,
                "chebyshev": chebyshev,
                "manhattan": manhattan,
                "legal_replies": len(replies),
                "winning_replies_for_ptm": len(win_replies),
                "winning_reply_coords": [coords(r, n) for r in win_replies[:12]],
            }
        )

    # Cross-check: every LOSS 2-stone should appear as a winning second-player
    # reply from some LOSS first move (directed edge first->reply).
    directed = set()
    mob = json.loads((NR / "cycle4-exact-n5.json").read_text(encoding="utf-8"))[
        "first_move_mobility"
    ]
    for row in mob:
        if row["result_for_first_player"] != "LOSS":
            continue
        # full winning replies: recompute rather than truncated list
        first = row["id"]
        occ = 1 << first
        replies = legal_moves(occ, V, qb)
        for r in replies:
            if outc.get(occ | (1 << r)) == 0:
                pair = tuple(sorted((first, r)))
                directed.add(pair)

    undirected_from_pairs = {tuple(p["ids"]) for p in loss_pairs}
    only_directed = directed - undirected_from_pairs
    only_pairs = undirected_from_pairs - directed

    class_pair_counts = Counter(tuple(sorted(p["cell_classes"])) for p in loss_pairs)
    cheb_counts = Counter(p["chebyshev"] for p in loss_pairs)
    # do all LOSS pairs consist of points that are individually losing first moves?
    # (player-to-move at k=1 WIN = losing first move)
    losing_first = {
        i for i in range(V) if outc.get(1 << i) == 1
    }  # WIN for player to move after first = first player loses
    winning_first = {i for i in range(V) if outc.get(1 << i) == 0}
    both_losing_first = sum(
        1 for p in loss_pairs if p["ids"][0] in losing_first and p["ids"][1] in losing_first
    )
    both_winning_first = sum(
        1 for p in loss_pairs if p["ids"][0] in winning_first and p["ids"][1] in winning_first
    )
    mixed = len(loss_pairs) - both_losing_first - both_winning_first

    report = {
        "n": n,
        "safe_2stone": 300,
        "loss_2stone": len(loss_pairs),
        "directed_first_to_reply_loss_children": len(directed),
        "match_directed_vs_undirected": {
            "only_in_directed": [list(p) for p in sorted(only_directed)],
            "only_in_loss_pairs": [list(p) for p in sorted(only_pairs)],
            "equal": directed == undirected_from_pairs,
        },
        "cell_class_pair_counts": {str(k): v for k, v in class_pair_counts.items()},
        "chebyshev_counts": {str(k): v for k, v in cheb_counts.items()},
        "endpoint_types": {
            "both_losing_first_moves": both_losing_first,
            "both_winning_first_moves": both_winning_first,
            "mixed": mixed,
        },
        "interpretation": [
            "LOSS 2-stone positions are exactly the undirected pairs that appear as "
            "winning second-player replies from some losing first move (if equal=true).",
            "Player-to-move: a 2-stone LOSS means the player about to move has 0 winning replies.",
            "Geometry: see cell_class_pair_counts and chebyshev_counts — pure distance "
            "does not determine LOSS; composition of first-move classes may.",
        ],
        "loss_pairs": loss_pairs,
    }

    out = NR / "cycle4-n5-two-stone-geometry.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    print("loss_2stone", report["loss_2stone"])
    print("directed", report["directed_first_to_reply_loss_children"])
    print("equal", report["match_directed_vs_undirected"]["equal"])
    print("only_directed", report["match_directed_vs_undirected"]["only_in_directed"][:5])
    print("only_pairs", report["match_directed_vs_undirected"]["only_in_loss_pairs"][:5])
    print("class_pairs", report["cell_class_pair_counts"])
    print("chebyshev", report["chebyshev_counts"])
    print("endpoint_types", report["endpoint_types"])

    # Cross-board: k=1 LOSS rate vs winner vs density for n=2..5 exact + known
    cross = []
    for nn in (2, 3, 4, 5):
        d = json.loads((NR / f"cycle4-exact-n{nn}.json").read_text(encoding="utf-8"))
        b = d["board"]
        k1 = next(r for r in b["depth_profile"] if r["k"] == 1)
        # peak interior LOSS among k>=2 with both win and loss nonzero
        mid = [
            r
            for r in b["depth_profile"]
            if r["k"] >= 2 and r["loss"] > 0 and r["win"] > 0
        ]
        peak = max(mid, key=lambda r: r["loss_rate"]) if mid else None
        cross.append(
            {
                "n": nn,
                "winner": b["expected_winner"],
                "density": b["mobility_density"],
                "k1_loss_rate": k1["loss_rate"],
                "k1_loss_equals_winning_first_moves": k1["loss"]
                == b["mobility_winning_first_moves"],
                "mid_peak": peak,
                "forbidden": b["forbidden_quadruples"],
            }
        )

    inv = {
        "cross_board_exact": cross,
        "standing_claims": {
            "H_dense": "SUPPORTED on complete n<=10 first-move data (not a clean holdout)",
            "parity_locking": "exact only n=2,3",
            "mobility_discriminator": False,
            "winning_reply_multiplicity_discriminator_on_n5": True,
            "embedding_transfer": "REJECTED",
        },
        "github": {
            "local_branch": "replicate-8x8-o-stratum @ db50e40",
            "origin_main": "4152c1a factorial Holm (lags local Cycle 3)",
        },
    }
    inv_path = NR / "cycle4-cross-board-invariants.json"
    inv_path.write_text(json.dumps(inv, indent=2), encoding="utf-8")
    print(f"wrote {inv_path}")
    for row in cross:
        print(row)


if __name__ == "__main__":
    main()
