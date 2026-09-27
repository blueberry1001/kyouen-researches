#!/usr/bin/env python3
"""B568 follow-up: scan many maximal 13-sets / 12-sets for homology kills."""
from __future__ import annotations

import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b561.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round2_b561_homology import (  # noqa: E402
    betti_from_faces,
    load_bin,
    mask_to_pts,
    nerve_faces,
)
from kyouen_core import board_square  # noqa: E402


def is_maximal(board, m: int) -> bool:
    if not board.is_safe(m):
        return False
    empties = board.full ^ m
    e = empties
    v = 0
    while e:
        if e & 1:
            ok = True
            bit = 1 << v
            for q in board.quads_by_pt[v]:
                if (q & (m | bit)) == q:
                    ok = False
                    break
            if ok:
                return False
        e >>= 1
        v += 1
    return True


def betti_with_extra(stars, n_max, extra_mask_on_board, board_n):
    """Add one new vertex whose star is extra_mask_on_board (points of the new set).
    Link of new vertex = union of old stars(p) for p in the new set."""
    faces = {d: set(s) for d, s in nerve_faces(stars, n_max).items()}
    faces.setdefault(0, set()).add(1 << n_max)
    mm = extra_mask_on_board
    v = 0
    while mm:
        if mm & 1:
            star = stars[v]
            sub = star
            while sub:
                faces.setdefault(sub.bit_count(), set()).add(sub | (1 << n_max))
                sub = (sub - 1) & star
        mm >>= 1
        v += 1
    faces = {d: sorted(s) for d, s in faces.items()}
    return betti_from_faces(faces, n_max + 1)


def main():
    n = 7
    report = json.loads(OUT.read_text(encoding="utf-8"))
    max7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    stars = [0] * (n * n)
    for i, m in enumerate(max7):
        mm = m
        v = 0
        while mm:
            if mm & 1:
                stars[v] |= 1 << i
            mm >>= 1
            v += 1
    n_max = len(max7)
    faces0 = nerve_faces(stars, n_max)
    betti0 = betti_from_faces(faces0, n_max)
    print("base betti", betti0, flush=True)

    board = board_square(n)
    k13 = load_bin(DATA / "safe_n7_k13.bin")
    max13 = [m for m in k13 if is_maximal(board, m)]
    print(f"max13={len(max13)}", flush=True)

    kills = []
    increases = []
    unchanged = 0
    # scan up to 400 of them
    for idx, m in enumerate(max13[:400]):
        b2 = betti_with_extra(stars, n_max, m, n)
        # compare nonzero betti in degrees 0..5
        for d in range(0, 6):
            before = betti0.get(d, 0)
            after = b2.get(d, 0)
            if after < before:
                kills.append({
                    "idx": idx,
                    "m_pts": mask_to_pts(m, n),
                    "deg": d,
                    "before": before,
                    "after": after,
                    "betti_after": {str(k): v for k, v in b2.items() if v},
                })
                break
        else:
            changed_up = any(b2.get(d, 0) > betti0.get(d, 0) for d in range(0, 6))
            if changed_up:
                increases.append(idx)
            else:
                unchanged += 1
        if (idx + 1) % 100 == 0:
            print(f"  scanned {idx+1} kills={len(kills)} inc={len(increases)} unch={unchanged}", flush=True)

    print(f"RESULT kills={len(kills)} increases={len(increases)} unchanged={unchanged}", flush=True)
    if kills:
        print("first kill", kills[0], flush=True)

    # 12-stone maximal: scan more
    k12 = load_bin(DATA / "safe_n7_k12.bin")
    max12 = [m for m in k12 if is_maximal(board, m)]
    print(f"max12={len(max12)}", flush=True)
    kills12 = []
    inc12 = 0
    for idx, m in enumerate(max12[:200]):
        b2 = betti_with_extra(stars, n_max, m, n)
        for d in range(0, 6):
            if b2.get(d, 0) < betti0.get(d, 0):
                kills12.append({
                    "idx": idx,
                    "m_pts": mask_to_pts(m, n),
                    "deg": d,
                    "before": betti0.get(d, 0),
                    "after": b2.get(d, 0),
                })
                break
        else:
            if any(b2.get(d, 0) > betti0.get(d, 0) for d in range(0, 6)):
                inc12 += 1
    print(f"k12 kills={len(kills12)} inc={inc12}", flush=True)

    report["n7"]["b568_scan"] = {
        "n_max13_total": len(max13),
        "scanned_13": min(400, len(max13)),
        "n_kills_13": len(kills),
        "n_increases_13": len(increases),
        "n_unchanged_13": unchanged,
        "first_kill_13": kills[0] if kills else None,
        "n_max12_total": len(max12),
        "scanned_12": min(200, len(max12)),
        "n_kills_12": len(kills12),
        "n_increases_12": inc12,
        "first_kill_12": kills12[0] if kills12 else None,
        "base_betti": {str(k): v for k, v in betti0.items() if v},
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
