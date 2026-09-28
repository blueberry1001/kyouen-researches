#!/usr/bin/env python3
"""Asymptotic bookkeeping for the m=4 share of C_n (the B475/B476 crux).

Let H_n[m] = #{circles in [0,n)^2 with exactly m grid points}.  Then
    C_n = sum_{m>=4} C(m,4) * H_n[m]
and the B475 / B476 dispute is entirely about the tail

    T_n(m0) = 1 - f_n(m0) = sum_{m>m0} C(m,4) H_n[m] / C_n .

B475 says: some fixed m0 has liminf_n f_n(m0) > 0  <=>  limsup_n T_n(m0) < 1.
B476 says: for EVERY fixed m0, f_n(m0) -> 0     <=>  T_n(m0) -> 1 for every m0.

Both are about the same quantity.  The honest way to attack it is to compare the
m=4 bulk, which is enumerated exactly, against the total C_n, and to see whether
the m=4 share is decaying like a power of n or like 1/n^2 (i.e. towards 0) or
like a positive constant (B475) or growing (B476).

The m=4 share is a ratio of two exactly-computed integers, so we can fit it
against n^2 exactly: if H_n[4] ~ c * n^2 (the standard count of "ordinary"
circles, i.e. the circles through 3 points with no 4th) and C_n ~ c' * n^4, then
f_n(4) = H_n[4]/C_n ~ (c/c') n^-2 -> 0, which is B476.  If instead H_n[4] grew
like n^4 the ratio would be constant (B475).  So the decisive measurement is the
growth exponent of H_n[4].

This script measures, for the exactly-computed n, the ratio
    H_n[4] / n^2   and   H_n[4] / n^4
and the implied exponent via consecutive ratios (all exact integer/Fraction work,
floats only for a display column).
"""
from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "round3_b475_mn.json"


def main():
    rep = json.loads(DATA.read_text(encoding="utf-8"))
    S = rep["spectra"]
    ns = sorted(int(k[1:]) for k in S)

    print("n   H4        C_n        H4/n^2      H4/n^4      f4=H4/C_n   Cn/n^4")
    rows = []
    for n in ns:
        h4 = int(S[f"n{n}"]["H"].get("4", 0))
        cn = S[f"n{n}"]["C_n"]
        rows.append({
            "n": n,
            "H4": h4,
            "C_n": cn,
            "M_n": S[f"n{n}"]["M_n"],
            "H4_over_n2": Fraction(h4, n * n),
            "H4_over_n4": Fraction(h4, n ** 4),
            "f4": Fraction(h4, cn) if cn else None,
            "Cn_over_n4": Fraction(cn, n ** 4),
        })
        r = rows[-1]
        print(f"{n:<3} {h4:<9} {cn:<9} {float(r['H4_over_n2']):<11.2f} "
              f"{float(r['H4_over_n4']):<11.6f} {float(r['f4']):<10.4f} "
              f"{float(r['Cn_over_n4']):.5f}")

    # growth exponent of H_n[4] estimated from consecutive n (log2 ratio / log2 n)
    print("\nestimated growth exponent of H_n[4]  ( log2(H[n2]/H[n1]) / log2(n2/n1) )")
    exp_rows = []
    for a, b in zip(rows, rows[1:]):
        if a["H4"] > 0 and b["H4"] > 0 and b["n"] > a["n"]:
            num = Fraction(b["H4"], a["H4"])
            den = Fraction(b["n"], a["n"])
            # exponent = log(num)/log(den); use math.log only for this display metric
            e = math.log(num.numerator / num.denominator) / math.log(den.numerator / den.denominator)
            exp_rows.append({"n_from": a["n"], "n_to": b["n"], "exponent": e})
            print(f"  n={a['n']}->{b['n']}:  exponent ~ {e:.3f}")

    # tail shares for the decision
    print("\nT_n(m0) = share of C_n from circles with MORE than m0 grid points")
    hdr = "n    " + "".join(f"T({m0})" .ljust(10) for m0 in [4, 6, 8, 12])
    print(hdr)
    tail_rows = []
    for n in ns:
        cum = S[f"n{n}"]["cum_le_m0"]
        line = f"{n:<5}"
        tr = {"n": n}
        for m0 in [4, 6, 8, 12]:
            f = Fraction(cum[str(m0)]["quads_from_m_le_m0"], S[f"n{n}"]["C_n"])
            t = 1 - f
            tr[f"T{m0}"] = float(t)
            line += f"{float(t):<10.4f}"
        tail_rows.append(tr)
        print(line)

    rep["asymptotic_bookkeeping"] = {
        "rows": [
            {k: (str(v) if isinstance(v, Fraction) else v) for k, v in r.items()}
            for r in rows
        ],
        "H4_growth_exponent": exp_rows,
        "tail_shares": tail_rows,
    }
    DATA.write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("\nupdated", DATA)


if __name__ == "__main__":
    main()
