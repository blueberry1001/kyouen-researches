#!/usr/bin/env python3
"""探索13: Grundy の空盤値・証明書圧縮・円上格子点の一般則の検証。"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def odd_repr_theory():
    """N=a²+b² (a,b 奇) の表現数の数論。

    N=2m, m 奇。A=2k+1, B=2l+1 とおくと A²+B²=2(2k²+2k+2l²+2l+1)。
    つまり N/2 は奇、かつ N/2 = k(k+1)+l(l+1)+1 = (2k+1)²+(2l+1)² / 2。
    等価に N=2m が 2 つの奇平方和に書ける。
    """
    def odd_repr(n):
        if n <= 0:
            return 0
        seen = set()
        lim = math.isqrt(n)
        for a in range(-lim, lim + 1):
            if a % 2 == 0:
                continue
            b2 = n - a * a
            if b2 < 0:
                continue
            b = math.isqrt(b2)
            if b * b != b2 or b % 2 == 0:
                continue
            for sb in ({b, -b} if b else {0}):
                seen.add((a, sb))
        return len(seen)

    rows = []
    for N in (2, 10, 50, 130, 650, 850, 1250, 2210, 3250):
        # factorization
        m = N // 2
        rows.append({
            "N": N,
            "odd_repr": odd_repr(N),
            "m": m,
            "m_mod_4": m % 4,
            "note": "N=2·m with primes 1 mod 4 in m",
        })
    return rows


def compression_table():
    nodes = {1: 2, 2: 5, 3: 28, 4: 135, 5: 1217, 6: 21712, 7: 393550, 8: 8744406, 9: 13457134}
    raw = {1: 72, 2: 120, 3: 488, 4: 2200, 5: 19512, 6: 347432, 7: 6296840, 8: 139910536, 9: 215314184}
    zst = {1: 49, 2: 68, 3: 151, 4: 514, 5: 4480, 6: 81715, 7: 1517374, 8: 33069195, 9: 62027637}
    rows = []
    for n in range(1, 10):
        rows.append({
            "n": n,
            "nodes": nodes[n],
            "raw_bytes": raw[n],
            "zst_bytes": zst[n],
            "bytes_per_node": raw[n] / nodes[n],
            "zst_ratio": zst[n] / raw[n],
        })
    return rows


def circle_max_formula_status():
    """M(n) = max lattice points on a circle in n×n.
    実測: 4,4,8,8,8,8,12,12,12,12,16,16,16,16,16,16,16,16,16,16,16,16,16,16,20,24,24,...
    """
    return {
        "measured_n2_to_n31": {
            2: 4, 3: 4, 4: 8, 5: 8, 6: 8, 7: 8, 8: 12, 9: 12, 10: 12, 11: 12,
            12: 16, 13: 16, 14: 16, 15: 16, 16: 16, 17: 16, 18: 16, 19: 16,
            20: 16, 21: 16, 22: 16, 23: 16, 24: 16, 25: 20, 26: 24, 27: 24,
            28: 24, 29: 24, 30: 24, 31: 24,
        },
        "plateaus": "16 for 12<=n<=24 (13 consecutive), 24 for 26<=n<=31",
        "witness_N": {2: 2, 4: 10, 8: 50, 12: 130, 25: 650, 26: 650},
        "rejected_formula": "4(floor(n/4)+1) fails at n=16",
        "mechanism": "odd representations of N=a^2+b^2 times embedding |a|,|b| <= 2n-1",
    }


def grundy_summary():
    """CYCLE5 の空盤 Grundy を再録し、n=7 の可否を論評。"""
    return {
        "empty_g": {2: 1, 3: 1, 4: 0, 5: 1, 6: 1},
        "max_nimber": {2: 1, 3: 1, 4: 5, 5: 6, 6: 8},
        "interpretation": "g=0 iff second win. n=2,3 only nimbers {0,1}. n=5 losing first moves all have g=3.",
        "open": "empty g for n=7,8,9 (expect 0 for 7,8 and 1 for 9)",
    }


def main():
    report = {
        "odd_repr": odd_repr_theory(),
        "compression": compression_table(),
        "circle_max": circle_max_formula_status(),
        "grundy": grundy_summary(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    out = OUT / "exploration_report_13.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()
