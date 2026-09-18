#!/usr/bin/env python3
"""Cycle 8 shared geometry / data library for kyouen max-safe analysis.

Reads complete enumerations committed at 2d3855a / 99659da:
  night-research/maxsafe_n7_K14.bin  (16 sets)
  night-research/maxsafe_n6_K11.bin  (464 sets)
No new board search is performed here.
"""
from __future__ import annotations

import struct
from collections import defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
NR = ROOT / "night-research"
RES = ROOT / "results"


def load_sets(name: str, k: int, v: int) -> list[int]:
    data = (NR / name).read_bytes()
    sets = [struct.unpack_from("<Q", data, i)[0] for i in range(0, len(data), 8)]
    for s in sets:
        assert s.bit_count() == k and s < (1 << v), (hex(s), k, v)
    return sets


def load_n7() -> list[int]:
    return load_sets("maxsafe_n7_K14.bin", 14, 49)


def load_n6() -> list[int]:
    return load_sets("maxsafe_n6_K11.bin", 11, 36)


def xy(pid: int, n: int) -> tuple[int, int]:
    return pid % n, pid // n


def pid(x: int, y: int, n: int) -> int:
    return y * n + x


def stones(mask: int, v: int) -> list[int]:
    out = []
    m = mask
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def mask_from(pts: Iterable[int]) -> int:
    m = 0
    for p in pts:
        m |= 1 << p
    return m


def coords(mask: int, n: int) -> list[tuple[int, int]]:
    return [xy(p, n) for p in stones(mask, n * n)]


def board_str(mask: int, n: int, center_id: int | None = None) -> str:
    lines = []
    for y in range(n):
        row = []
        for x in range(n):
            p = pid(x, y, n)
            if (mask >> p) & 1:
                row.append("X")
            elif center_id is not None and p == center_id:
                row.append("c")
            else:
                row.append(".")
        lines.append("".join(row))
    return "\n".join(lines)


def det4(rows: list[list[int]]) -> int:
    """4x4 determinant via cofactor expansion on column 0."""
    m = rows
    total = 0
    for i in range(4):
        mm = [[m[r][c] for c in range(1, 4)] for r in range(4) if r != i]
        det3 = (
            mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
            - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
            + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0])
        )
        total += (1 if i % 2 == 0 else -1) * m[i][0] * det3
    return total


def forbidden_quads(n: int) -> list[tuple[int, int, int, int]]:
    v = n * n
    rows = [[x * x + y * y, x, y, 1] for y in range(n) for x in range(n)]
    quads = []
    for a in range(v - 3):
        for b in range(a + 1, v - 2):
            for c in range(b + 1, v - 1):
                for d in range(c + 1, v):
                    if det4([rows[a], rows[b], rows[c], rows[d]]) == 0:
                        quads.append((a, b, c, d))
    return quads


def triples_by_point(n: int, quads: list[tuple[int, int, int, int]] | None = None):
    if quads is None:
        quads = forbidden_quads(n)
    tbp: dict[int, list[int]] = defaultdict(list)
    for q in quads:
        qm = mask_from(q)
        for t in q:
            others = qm & ~(1 << t)
            tbp[t].append(others)
    return tbp, quads


def d4_perms(n: int) -> list[list[int]]:
    P = []
    for m in range(8):
        fx, fy, tr = bool(m & 1), bool(m & 2), bool(m & 4)
        p = []
        for y in range(n):
            for x in range(n):
                sx = (n - 1 - x) if fx else x
                sy = (n - 1 - y) if fy else y
                nx, ny = (sy, sx) if tr else (sx, sy)
                p.append(ny * n + nx)
        P.append(p)
    return P


def apply_perm(mask: int, p: list[int]) -> int:
    o = 0
    w = mask
    while w:
        b = w & -w
        i = b.bit_length() - 1
        w ^= b
        o |= 1 << p[i]
    return o


def canon(mask: int, perms: list[list[int]]) -> int:
    return min(apply_perm(mask, p) for p in perms)


def cell_orbit_key(n: int, x: int, y: int) -> tuple[int, int]:
    return min(
        {
            (x, y),
            (n - 1 - x, y),
            (x, n - 1 - y),
            (n - 1 - x, n - 1 - y),
            (y, x),
            (n - 1 - y, x),
            (y, n - 1 - x),
            (n - 1 - y, n - 1 - x),
        }
    )


def cell_orbits(n: int) -> list[tuple[int, int]]:
    seen = set()
    ords = []
    for y in range(n):
        for x in range(n):
            k = cell_key(n, x, y)
            if k not in seen:
                seen.add(k)
                ords.append(k)
    return sorted(ords)


def cell_key(n: int, x: int, y: int) -> tuple[int, int]:
    return cell_orbit_key(n, x, y)


def orbit_members(n: int) -> dict[tuple[int, int], list[int]]:
    members: dict[tuple[int, int], list[int]] = defaultdict(list)
    for y in range(n):
        for x in range(n):
            members[cell_key(n, x, y)].append(pid(x, y, n))
    return dict(members)


def occupancy_vector(mask: int, n: int) -> dict[tuple[int, int], int]:
    members = orbit_members(n)
    occ = {}
    for k, pts in members.items():
        occ[k] = sum(1 for p in pts if (mask >> p) & 1)
    return occ


def is_safe(mask: int, quads: list[tuple[int, int, int, int]]) -> bool:
    for a, b, c, d in quads:
        bit = (1 << a) | (1 << b) | (1 << c) | (1 << d)
        if (mask & bit) == bit:
            return False
    return True


def blocker_triples(mask: int, v_empty: int, tbp: dict[int, list[int]]) -> list[int]:
    """For empty point v, triples T⊂mask such that T∪{v} is forbidden."""
    out = []
    for o in tbp.get(v_empty, []):
        if (mask & o) == o:
            out.append(o)
    return out


def tau_bruteforce(mask: int, v_empty: int, tbp: dict[int, list[int]]) -> int:
    """Min hitting-set size of blocker family (0 if no blockers)."""
    fam = blocker_triples(mask, v_empty, tbp)
    if not fam:
        return 0
    stones_l = stones(mask, mask.bit_length() if False else 49)
    # use exact popcount of mask
    stones_l = stones(mask, max(v_empty + 1, mask.bit_length()))
    # mask may include only board cells; filter to bits in mask
    stones_l = [p for p in range(mask.bit_length()) if (mask >> p) & 1]
    for t in range(1, 5):
        from itertools import combinations

        for comb in combinations(stones_l, t):
            cm = mask_from(comb)
            if all(cm & o for o in fam):
                return t
    return 99


def centers(n: int) -> list[int]:
    return [pid(n // 2, n // 2, n)] if n % 2 == 1 else []


def corners(n: int) -> list[int]:
    return [pid(0, 0, n), pid(n - 1, 0, n), pid(0, n - 1, n), pid(n - 1, n - 1, n)]


def max_safe_under(
    n: int,
    quads: list[tuple[int, int, int, int]],
    forced: int = 0,
    forbidden: int = 0,
    corner_count: int | None = None,
    known_K: int = 14,
) -> dict:
    """Branch-and-bound max safe set size with occupancy constraints.

    Returns {max_size, n_attainers, first_example or None, complete: bool}.
    Search is complete for the constrained problem when it finishes;
    known_K is only an upper bound for pruning.
    """
    tbp, _ = triples_by_point(n, quads)
    v = n * n
    all_cells = (1 << v) - 1
    assert forced & forbidden == 0
    assert (forced & all_cells) == forced
    assert (forbidden & all_cells) == forbidden
    if not is_safe(forced, quads):
        return {"max_size": -1, "n_attainers": 0, "first": None, "reason": "forced unsafe"}

    cn = corners(n)
    best = {"size": 0, "count": 0, "first": None}
    # order cells for branching: forced first, then by constraint relevance
    order = stones(forced, v) + [p for p in range(v) if not ((forced | forbidden) >> p) & 1]

    ccount = [0] * v
    chosen = 0

    def corner_ok(mask: int) -> bool:
        if corner_count is None:
            return True
        got = sum(1 for p in cn if (mask >> p) & 1)
        # cannot exceed final count; remaining corners may still be added
        return got <= corner_count

    def dfs(cand: int, count: int, chosen_mask: int) -> None:
        nonlocal chosen
        if not corner_ok(chosen_mask):
            return
        room = count + cand.bit_count()
        if room < best["size"]:
            return
        if room < known_K and best["size"] >= room:
            # cannot beat current best
            pass
        # if even filling all remaining cannot reach a new record, skip counting
        if count + cand.bit_count() < best["size"]:
            return
        if count + cand.bit_count() < known_K and best["size"] > count + cand.bit_count():
            return

        if cand == 0:
            # evaluate terminal: corner exactness only at end
            if corner_count is not None:
                got = sum(1 for p in cn if (chosen_mask >> p) & 1)
                if got != corner_count:
                    return
            if count > best["size"]:
                best["size"] = count
                best["count"] = 1
                best["first"] = chosen_mask
            elif count == best["size"]:
                best["count"] += 1
            return

        # branch on lowest candidate
        u = (cand & -cand).bit_length() - 1
        # option 1: skip u permanently
        dfs(cand & ~chosen_mask & ~(1 << u) & all_cells if False else cand & ~(1 << u), count, chosen_mask)
        # option 2: take u
        newcand = cand & ~(1 << u)
        undo = []
        ok = True
        for o in tbp.get(u, []):
            pc = bin(o & chosen_mask).count("1")
            if pc == 2:
                wmask = o & ~chosen_mask & all_cells
                if wmask == 0:
                    ok = False
                    break
                w = (wmask & -wmask).bit_length() - 1
                if ccount[w] == 0:
                    newcand &= ~(1 << w)
                ccount[w] += 1
                undo.append(w)
        if ok:
            dfs(newcand, count + 1, chosen_mask | (1 << u))
        for w in undo:
            ccount[w] -= 1

    # initial candidates: all non-forbidden
    cand0 = all_cells & ~forbidden
    # place forced stones first via synthetic take-all
    # simpler: run DFS from empty but forbid `forbidden` and require forced
    # Require forced: start by taking forced cells one by one
    def take_forced(chosen_mask: int, ccount_local: list[int]) -> tuple[int, int, bool]:
        cand = all_cells & ~forbidden
        count = 0
        for u in stones(forced, v):
            if not ((cand >> u) & 1) and not ((chosen_mask >> u) & 1):
                # forced cell already closed? should not happen if safe
                if not ((chosen_mask >> u) & 1):
                    return cand, count, False
            if (chosen_mask >> u) & 1:
                continue
            cand &= ~(1 << u)
            for o in tbp.get(u, []):
                pc = bin(o & chosen_mask).count("1")
                if pc == 2:
                    wmask = o & ~chosen_mask & all_cells
                    if wmask == 0:
                        return cand, count, False
                    w = (wmask & -wmask).bit_length() - 1
                    if ccount_local[w] == 0:
                        cand &= ~(1 << w)
                    ccount_local[w] += 1
            chosen_mask |= 1 << u
            count += 1
            # also remove forced from cand
            cand &= ~chosen_mask
            cand &= ~forbidden
        return cand, count, True

    ccount = [0] * v
    chosen_mask = 0
    cand, count, ok = take_forced(chosen_mask, ccount)
    if not ok:
        return {"max_size": -1, "n_attainers": 0, "first": None, "reason": "forced conflict"}
    chosen_mask = forced
    # recompute ccount cleanly
    ccount = [0] * v
    for u in stones(forced, v):
        for o in tbp.get(u, []):
            pc = bin(o & forced).count("1")
            if pc == 2:
                wmask = o & ~forced & all_cells
                if wmask:
                    w = (wmask & -wmask).bit_length() - 1
                    ccount[w] += 1
    cand = all_cells & ~forbidden & ~forced
    for p in range(v):
        if ccount[p] > 0:
            cand &= ~(1 << p)

    dfs(cand, forced.bit_count(), forced)
    return {
        "max_size": best["size"],
        "n_attainers": best["count"],
        "first": best["first"],
        "forced": forced,
        "forbidden": forbidden,
        "corner_count": corner_count,
        "complete": True,
        "known_upper": known_K,
    }
