#!/usr/bin/env python3
"""サイズ 10 極大集合の幾何的構造。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from fact_10x10_maximal_sample import Engine, build_forbidden, PTS  # noqa: E402

N = 10


def xy(p: int):
    return (p % N, p // N)


def main() -> None:
    quads = build_forbidden()
    eng = Engine(quads)
    sets = [
        [1, 2, 3, 4, 5, 8, 10, 11, 20, 27],
        [1, 2, 3, 4, 5, 10, 11, 20, 27, 97],
        [1, 2, 3, 4, 5, 10, 11, 20, 27, 8],
    ]
    rows = []
    for S in sets:
        assert eng.is_maximal(S)
        coords = [xy(p) for p in S]
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        # bounding box
        bbox = (min(xs), min(ys), max(xs), max(ys))
        # how many on border
        border = sum(1 for x, y in coords if x in (0, 9) or y in (0, 9))
        rows.append(
            {
                "set": S,
                "coords": coords,
                "bbox": bbox,
                "bbox_span": (bbox[2] - bbox[0], bbox[3] - bbox[1]),
                "n_border_points": border,
                "mean_x": sum(xs) / len(xs),
                "mean_y": sum(ys) / len(ys),
            }
        )
        print(rows[-1])

    # Compare to size-11
    s11 = [0, 1, 2, 3, 4, 5, 6, 10, 11, 20, 27]
    coords = [xy(p) for p in s11]
    print("s11 coords", coords)

    path = ROOT / "research" / "exploration" / "fact_10x10_size10_geometry.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
