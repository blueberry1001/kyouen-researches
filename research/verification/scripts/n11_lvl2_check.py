"""Is the level-2 count really zero? Check against a known case.

The C++ run says every one of the C(N,2) pairs lies inside some forbidden
4-set, for every n from 6 to 11. If that were true the recorded level_sizes
would start [1, N, 0, ...] and the game could never reach 3 stones, which
contradicts the recorded n=6 sequence [1,36,630,7140,...].

So either the C++ pair set is wrong, or the recorded level-2 numbers mean
something else. n=6 has 36 points and 630 = C(36,2), i.e. *all* pairs: the
recorded level 2 is the set of 2-stone positions reachable by *playing*, and
a 2-stone position is legal iff no forbidden quad is completed *by the second
stone*, which is a different condition from "lies in some forbidden 4-set".

Resolve it by brute force: build a 2-stone position and test it directly with
the same predicate the game uses.
"""
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

for n in (6, 7, 8, 11):
    b = board_square(n)
    full = (1 << (n * n)) - 1
    empty_moves = set(b.legal_moves(0))          # legal on the empty board
    safe2 = 0
    total = 0
    for u in empty_moves:
        occ = 1 << u
        for v in empty_moves:
            if v <= u:
                continue
            total += 1
            # the 2-stone set is a position iff it contains no forbidden 4-set
            if b.is_safe(occ | (1 << v)):
                safe2 += 1
    print(f"n={n:2d}  legal points={len(empty_moves):4d}  pairs tried={total:6d}  "
          f"safe 2-stone positions={safe2:6d}")
