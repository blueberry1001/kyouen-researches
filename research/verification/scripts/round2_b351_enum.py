#!/usr/bin/env python3
"""Enumerate all safe masks for small boards and cache to disk (uint64 le).

n=2..5 small; n=6 cached once (5,081,289 masks).
Output: research/verification/data/safe_n{n}.bin
"""
from __future__ import annotations

import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from batch04_geom import all_safe_masks  # noqa: E402
from kyouen_core import board_square  # noqa: E402

DATA = ROOT / "research" / "verification" / "data"
DATA.mkdir(parents=True, exist_ok=True)


def main():
    for n in range(2, 7):
        out = DATA / f"safe_n{n}.bin"
        if out.exists() and out.stat().st_size > 0:
            print(f"n={n} already cached {out.stat().st_size//8} masks", flush=True)
            continue
        t0 = time.time()
        b = board_square(n)
        masks = all_safe_masks(b)
        with out.open("wb") as f:
            for m in masks:
                f.write(struct.pack("<Q", m))
        print(f"n={n} cached {len(masks)} in {time.time()-t0:.1f}s -> {out}", flush=True)


if __name__ == "__main__":
    main()
