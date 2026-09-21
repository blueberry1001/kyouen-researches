#!/usr/bin/env python3
"""KYOENC3 証明書の統計解析 (7x7, 8x8, 9x9)。

各証明書について:
- ノード数, LOSS/WIN 数, LOSS 割合
- rank 別ノード数 (石数別分布)
- witness の空間分布 (witness がどの点に置かれるか)
"""
import struct
import sys
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
    assert len(arr) == ncount, f"{path}: {len(arr)} != {ncount}"
    return magic, version, board, ncount, root_lo, root_hi, forbidden, arr


def main() -> None:
    for name in ["kyouen-7x7", "kyouen-8x8", "kyouen-9x9"]:
        magic, version, board, ncount, rlo, rhi, forbidden, arr = parse(CERTS / f"{name}.cert")
        loss = int((arr["outcome"] == 1).sum())
        win = int((arr["outcome"] == 2).sum())
        other = int(((arr["outcome"] != 1) & (arr["outcome"] != 2)).sum())
        ranks = Counter(arr["rank"])
        witnesses = arr[arr["outcome"] == 2]["witness"]
        # rank = n^2 - popcount(state)
        stone_count = {r: board * board - r for r in ranks}
        print(f"=== {name} (board={board}, nodes={ncount:,}, forbidden={forbidden}) ===")
        print(f"  LOSS={loss:,} ({loss/ncount:.3%})  WIN={win:,} ({win/ncount:.3%})  other={other}")
        print(f"  ルート popcount: board*board - root_rank")
        # 石数別分布 (rank でなく石数で表示)
        sr = sorted(ranks.items())
        print("  石数別ノード数 (上位10):")
        for r, c in sorted(ranks.items(), key=lambda kv: -kv[1])[:10]:
            print(f"    rank={r:2d} 石数={stone_count[r]:2d}: {c:>12,} ({c/ncount:.3%})")
        # witness 分布
        wc = Counter(witnesses)
        print(f"  witness の置かれた点 (上位10):")
        for p, c in wc.most_common(10):
            print(f"    ({p % board},{p // board}): {c:>10,} ({c/win:.3%})")
        print()


if __name__ == "__main__":
    main()