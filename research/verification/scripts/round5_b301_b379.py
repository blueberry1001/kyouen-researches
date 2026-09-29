#!/usr/bin/env python3
"""B379: embed 8-stone maximal sets from 8x8 into 9x9, try remove <=2 + add
to reach a 9-stone maximal. Existence claim: some 8-stone maximal works.
"""
from __future__ import annotations

import json
import struct
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
BIN = ROOT / "research" / "verification" / "round4_b371.bin"
OUT = ROOT / "research" / "verification" / "round5_b301_b379.json"


def load_masks(path: Path):
    data = path.read_bytes()
    (count,) = struct.unpack_from("<Q", data, 0)
    return list(struct.unpack_from(f"<{count}Q", data, 8))


def embed_8to9(mask8: int) -> int:
    """Map 8x8 point id = y*8+x to 9x9 id = y*9+x (same x,y, leave 9th row/col empty)."""
    out = 0
    for y in range(8):
        for x in range(8):
            if (mask8 >> (y * 8 + x)) & 1:
                out |= 1 << (y * 9 + x)
    return out


def try_one(b9: Board, base: int, target_k: int = 9):
    """base is an 8-stone safe set on 9x9. Try remove r<=2, add a=target_k-(8-r)."""
    bits8 = [i for i in range(81) if (base >> i) & 1]
    assert len(bits8) == 8
    found = []
    # r = 0: add 1
    L = b9.legal_moves(base)
    for a in L:
        cand = base | (1 << a)
        if len(b9.legal_moves(cand)) == 0 and bin(cand).count("1") == 9:
            found.append(("r0", bits8, [a], cand))
            return found  # one is enough
    # r = 1: add 2
    for out in bits8:
        b1 = base & ~(1 << out)
        L = b9.legal_moves(b1)
        for a, c in combinations(L, 2):
            cand = b1 | (1 << a) | (1 << c)
            if not b9.is_safe(cand):
                continue
            if bin(cand).count("1") == 9 and len(b9.legal_moves(cand)) == 0:
                found.append(("r1", bits8, [out], [a, c], cand))
                return found
    # r = 2: add 3 (only if L is small enough)
    for out1, out2 in combinations(bits8, 2):
        b2 = base & ~(1 << out1) & ~(1 << out2)
        L = b9.legal_moves(b2)
        if len(L) > 16:
            continue  # keep search tractable
        for a, c, d in combinations(L, 3):
            cand = b2 | (1 << a) | (1 << c) | (1 << d)
            if not b9.is_safe(cand):
                continue
            if bin(cand).count("1") == 9 and len(b9.legal_moves(cand)) == 0:
                found.append(("r2", bits8, [out1, out2], [a, c, d], cand))
                return found
    return found


def main():
    masks = load_masks(BIN)
    b9 = board_square(9)
    print(f"9x9 V={b9.V} quads={len(b9.quads)}", flush=True)
    results = []
    n_ok = 0
    # try a sample first (first 30), then more if time permits
    sample = masks[:10]
    for si, m8 in enumerate(sample):
        base = embed_8to9(m8)
        assert b9.is_safe(base), f"embedded set {si} not safe on 9x9"
        found = try_one(b9, base)
        if found:
            n_ok += 1
            results.append({"idx": si, "ok": True, "how": found[0][0]})
            print(f"  set {si}: FOUND via {found[0][0]}", flush=True)
        else:
            results.append({"idx": si, "ok": False})
        if si % 5 == 0:
            print(f"  ... {si}/{len(sample)} ok={n_ok}", flush=True)
    res = {
        "n_tried": len(sample),
        "n_success": n_ok,
        "results": results,
    }
    OUT.write_text(json.dumps(res, indent=2))
    print(f"success {n_ok}/{len(sample)}", flush=True)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
