"""Reproduce the CSR FAIL from the CRT solver, standalone.

The solver reports CSR FAIL at k=5 after finishing k=6. The CSR for level k is
built from levels[k] and levels[k+1]; the failure means a child mask was not
found in levels[k+1] by binary search. Either the child enumeration and the
sorted-level invariant disagree, or the level was released too early.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402


def levels_of(n):
    """All safe subsets grouped by size, sorted, as masks over point ids."""
    b = board_square(n)
    lv = [[0]]
    full = (1 << (n * n)) - 1
    cur = [0]
    while True:
        nxt = set()
        for occ in cur:
            for v in b.legal_moves(occ):
                nxt.add(occ | (1 << v))
        if not nxt:
            break
        cur = sorted(nxt)
        lv.append(cur)
    return b, lv


for n in (4,):
    b, lv = levels_of(n)
    print(f"n={n} levels={[len(x) for x in lv]}")
    # verify the invariant the CSR relies on
    bad = 0
    for k in range(len(lv) - 1):
        A, N = lv[k], lv[k + 1]
        Nset = set(N)
        assert N == sorted(N), f"level {k+1} is not sorted"
        for occ in A:
            for v in b.legal_moves(occ):
                child = occ | (1 << v)
                if child not in Nset:
                    bad += 1
                    if bad < 4:
                        print(f"  MISSING k={k} occ={occ:#x} child={child:#x}")
        print(f"  k={k}: {len(A)} parents, all children present"
              if bad == 0 else f"  k={k}: {bad} missing so far")
    print("CSR invariant holds" if bad == 0 else f"CSR invariant BROKEN ({bad})")
