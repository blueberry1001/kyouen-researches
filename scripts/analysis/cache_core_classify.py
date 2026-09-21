#!/usr/bin/env python3
"""D4正規化 (kyouen_solver の canonical と同一の辞書順最小形) を使って、
outcome-cache.json の LOSS 4石を「どの2石LOSSコア(の正規形)を含むかで分類する。

tbit[] 対応 (C++ の nx/ny から座標変換後の点 (nx,ny) から id = ny*N+nx):
  k=0:(x,y) k=1:(N-1-x,y) k=2:(x,N-1-y) k=3:(N-1-x,N-1-y)
  k=4:(y,x) k=5:(N-1-y,x) k=6:(y,N-1-x) k=7:(N-1-y,N-1-x)
比較は (hi 優先) の辞書順。
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
N = 10


def norm(pts) -> list[int]:
    xs = [p % N for p in pts]; ys = [p // N for p in pts]
    best = None
    for k in range(8):
        if k == 0: tx, ty = list(xs), list(ys)
        elif k == 1: tx, ty = [N - 1 - x for x in xs], list(ys)
        elif k == 2: tx, ty = list(xs), [N - 1 - y for y in ys]
        elif k == 3: tx, ty = [N - 1 - x for x in xs], [N - 1 - y for y in ys]
        elif k == 4: tx, ty = list(ys), list(xs)
        elif k == 5: tx, ty = [N - 1 - y for y in ys], list(xs)
        elif k == 6: tx, ty = list(ys), [N - 1 - x for x in xs]
        else: tx, ty = [N - 1 - y for y in ys], [N - 1 - x for x in xs]
        bits = 0
        for x, y in zip(tx, ty):
            bits |= 1 << (y * N + x)
        if best is None or bits < best:
            best = bits
    return sorted(i for i in range(100) if (best >> i) & 1)


def main() -> None:
    # 既知の正規形を出力しておく (手計算と一致確認)
    for name, pts in [
        ("{90,61}", [90, 61]), ("{61,66}", [61, 66]), ("{90,69}", [90, 69]),
        ("{90,2,91}", [90, 2, 91]), ("{90,73,91}", [90, 73, 91]),
        ("R", [90, 61, 2, 73, 69, 66, 13, 91]),
    ]:
        print(f"  norm({name}) = {norm(pts)}")

    cache = json.loads(
        (ROOT / "scratch" / "kyouen-local-handoff" / "outcome-cache.json").read_text()
    )
    loss4 = [frozenset(int(x) for x in k.split(",")) for k, v in cache.items()
             if len(k.split(",")) == 4 and v == "LOSS"]
    win3 = [frozenset(int(x) for x in k.split(",")) for k, v in cache.items()
            if len(k.split(",")) == 3 and v == "WIN"]

    core2 = {"013": frozenset({0, 13}), "3136": frozenset({31, 36}),
             "039": frozenset({0, 39}), "016": frozenset({0, 16}),
             "090": frozenset({0, 90})}
    # 各 LOSS4 がどの2石コアを含むか (正規形で直接)
    hits = Counter()
    for s in loss4:
        for name, c in core2.items():
            if c <= s:
                hits[name] += 1
    print(f"\n4石LOSS {len(loss4)}個 の 2石コア含有:")
    for name, c in hits.most_common():
        print(f"  {name}: {c}")
    print(f"  どの既知コアも含まない: {sum(1 for s in loss4 if not any(c <= s for c in core2.values()))}")

    # 3石WIN の2石コア含有
    h3 = Counter()
    for s in win3:
        for name, c in core2.items():
            if c <= s:
                h3[name] += 1
    print(f"\n3石WIN {len(win3)}個 の2石コア含有:")
    for name, c in h3.most_common():
        print(f"  {name}: {c}")
    print(f"  どのコアも含まない: {sum(1 for s in win3 if not any(c <= s for c in core2.values()))}")


if __name__ == "__main__":
    main()