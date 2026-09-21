#!/usr/bin/env python3
"""9x9 証明書の末端 (石数17 LOSS) ノードの合法手を数え、飽和か検証する。
4 点組の共円・共線判定は 4x4 行列式 (整数, fractions) で行う。
"""
import struct
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "scratch" / "certs" / "extracted" / "kyouen-9x9.cert"


def open_cert(path):
    with open(path, "rb") as f:
        head = f.read(40)
        magic, version, board, ncount, rlo, rhi, forbidden = struct.unpack(
            "<8sIIQQII", head
        )
        data = f.read(16 * ncount)
    arr = np.frombuffer(data, dtype=np.dtype([
        ("lo", "<u8"), ("hi", "<u4"), ("outcome", "u1"),
        ("witness", "u1"), ("rank", "u1"), ("reserved", "u1"),
    ]))
    return board, arr


def id_bits(lo, hi, nn):
    v = (int(hi) << 64) | int(lo)
    return [i for i in range(nn) if (v >> i) & 1]


def det4(rows):
    """4x4 整数行列式 (Fraction で厳密)。"""
    m = [[Fraction(v) for v in r] for r in rows]
    d = Fraction(1)
    # ガウス消去
    for col in range(4):
        piv = None
        for r in range(col, 4):
            if m[r][col] != 0:
                piv = r
                break
        if piv is None:
            return 0
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
            d = -d
        pv = m[col][col]
        for r in range(col + 1, 4):
            if m[r][col] != 0:
                f = m[r][col] / pv
                for c in range(col, 4):
                    m[r][c] -= f * m[col][c]
        d *= pv
    return d


def concyclic(q, p1, p2, p3):
    """4点 q,p1,p2,p3 が共円または共線なら True (整数行列式)。"""
    rows = []
    for x, y in [q, p1, p2, p3]:
        rows.append([x * x + y * y, x, y, 1])
    return det4(rows) == 0


def main():
    board, arr = open_cert(CERT)
    nn = board * board
    for stones in (17, 16):
        sel = arr[arr["rank"] == nn - stones]
        print(f"石数{stones} ノード: {len(sel)} 個")
        for row in sel:
            pts = id_bits(row["lo"], row["hi"], nn)
            coords = {p: (p % board, p // board) for p in pts}
            legal = []
            for q in range(nn):
                if q in coords:
                    continue
                qc = (q % board, q // board)
                ok = True
                for i in range(len(pts)):
                    if not ok:
                        break
                    for j in range(i + 1, len(pts)):
                        if not ok:
                            break
                        for k in range(j + 1, len(pts)):
                            if concyclic(qc, coords[pts[i]], coords[pts[j]], coords[pts[k]]):
                                ok = False
                                break
                if ok:
                    legal.append(q)
            print(f"  outcome={row['outcome']} witness={row['witness']} "
                  f"合法手={len(legal)} 点={pts}")
            print(f"  合法手の内訳: {legal}")


if __name__ == "__main__":
    main()