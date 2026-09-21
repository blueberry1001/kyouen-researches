#!/usr/bin/env python3
"""証明書の LOSS/WIN を分けた石数分布と、小さい盤面 (1x1..6x6) の LOSS 割合。
LOSS 割合が盤面サイズに依存しないという観察の検証。
"""
import struct
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CERTS = ROOT / "scratch" / "certs" / "extracted"


def parse(path: Path):
    with open(path, "rb") as f:
        head = f.read(40)
        magic, version, board, ncount, root_lo, root_hi, forbidden = struct.unpack(
            "<8sIIQQII", head
        )
        data = f.read(16 * ncount)
    arr = np.frombuffer(data, dtype=np.dtype([
        ("lo", "<u8"), ("hi", "<u4"), ("outcome", "u1"),
        ("witness", "u1"), ("rank", "u1"), ("reserved", "u1"),
    ]))
    return board, arr


def popcount_state(r):
    """rank から石数を引く: rank = n^2 - popcount は KYOENC3 の定義だが、
    rank フィールドが 8bit なので n^2 でなくても良い。ここでは 石数 = n^2 - rank。"""
    return r


def main() -> None:
    print("size | total | LOSS比率 | 平均石数(LOSS/WIN別)")
    for name in ["kyouen-1x1", "kyouen-2x2", "kyouen-3x3", "kyouen-4x4",
                 "kyouen-5x5", "kyouen-6x6", "kyouen-7x7", "kyouen-8x8", "kyouen-9x9"]:
        p = CERTS / f"{name}.cert"
        if not p.exists():
            continue
        board, arr = parse(p)
        n = len(arr)
        loss = arr[arr["outcome"] == 1]
        win = arr[arr["outcome"] == 2]
        lr = len(loss) / n
        mean_stones_loss = float(((board * board - loss["rank"]).mean()))
        mean_stones_win = float(((board * board - win["rank"]).mean()))
        print(f"  {name}: nodes={n:>10,}  LOSS={lr:.3%}  "
              f"石数LOSS={mean_stones_loss:5.2f} 石数WIN={mean_stones_win:5.2f}")

    # 9x9 の LOSS/WIN 石数分布を表示
    board, arr = parse(CERTS / "kyouen-9x9.cert")
    n = board * board
    print("\n9x9: 石数別 LOSS/WIN (代表):")
    print("  石数 | LOSS数 | WIN数 | LOSS(WIN内)比率")
    for stones in range(5, 16):
        sel = arr[(n - arr["rank"]) == stones]
        if len(sel) == 0:
            continue
        l = int((sel["outcome"] == 1).sum())
        w = int((sel["outcome"] == 2).sum())
        print(f"    {stones:3d} | {l:>10,} | {w:>10,} | {l/(l+w):.4f}")


if __name__ == "__main__":
    main()