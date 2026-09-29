#!/usr/bin/env python3
"""Round5 B561/B563: log-concavity of extension counts f_S(r).

f_S(r) = # of r-point subsets T of legal empty points with S∪T safe.
Log-concave iff f(r)^2 >= f(r-1)*f(r+1) for all interior r.

B561 [universal]: every safe S has log-concave f_S. Counterexample => REFUTED.
B563 [exists]: there is a board and a single stone p such that f_{p} is NOT
log-concave (empty is log-concave). Witness => SUPPORTED.
"""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

OUT = REPO_ROOT / "research" / "verification" / "round5_b401_logconc.json"


def f_vector(bd, occ: int) -> list[int]:
    """f_S(r) for r=0.. via DFS over empty points (small boards)."""
    V = bd.V
    empty = ((1 << V) - 1) ^ occ
    empties = []
    e = empty
    v = 0
    while e:
        if e & 1:
            empties.append(v)
        e >>= 1
        v += 1
    # count by recursion with pruning via is_safe
    max_r = len(empties)
    f = [0] * (max_r + 1)

    def rec(start: int, cur: int, r: int):
        f[r] += 1
        for i in range(start, len(empties)):
            child = cur | (1 << empties[i])
            if bd.is_safe(child):
                rec(i + 1, child, r + 1)

    rec(0, occ, 0)
    return f


def is_log_concave(f: list[int]) -> tuple[bool, int | None]:
    # f[0]=1 always; find first interior violation
    for r in range(1, len(f) - 1):
        if f[r] * f[r] < f[r - 1] * f[r + 1]:
            return False, r
    return True, None


def analyze(n: int) -> dict:
    t0 = time.time()
    bd = board_square(n)
    V = bd.V

    # B563 first: single-stone
    single_results = []
    n_single_fail = 0
    fail_example = None
    for p in range(V):
        f = f_vector(bd, 1 << p)
        ok, r = is_log_concave(f)
        if not ok:
            n_single_fail += 1
            if fail_example is None:
                fail_example = {
                    "p": p, "coords": (p % n, p // n), "f": f, "fail_r": r,
                }
        single_results.append({"p": p, "f": f, "log_concave": ok, "fail_r": r})

    empty_f = f_vector(bd, 0)
    empty_ok, empty_r = is_log_concave(empty_f)

    # B561: sample / all states depending on n
    # n<=4: all safe subsets. n=5: all singles + all pairs + random sample of larger
    all_fail = []
    n_checked = 0
    if n <= 4:
        # enumerate all safe subsets
        levels = [[0]]
        seen = {0}
        full = (1 << V) - 1
        for _ in range(V):
            nxt = set()
            for occ in levels[-1]:
                e = full ^ occ
                v = 0
                while e:
                    if e & 1:
                        child = occ | (1 << v)
                        if bd.is_safe(child):
                            nxt.add(child)
                    e >>= 1
                    v += 1
            if not nxt:
                break
            levels.append(sorted(nxt))
            seen |= nxt
        for occ in seen:
            n_checked += 1
            f = f_vector(bd, occ)
            ok, r = is_log_concave(f)
            if not ok:
                all_fail.append({
                    "occ": occ, "k": occ.bit_count(), "f": f, "fail_r": r,
                    "points": [(bx, by) for by in range(n) for bx in range(n)
                               if occ & (1 << (by * n + bx))],
                })
    else:
        # n=5: check all subsets of size <=2 and a systematic sample of size 3
        full = (1 << V) - 1
        for occ in range(full + 1):
            k = occ.bit_count()
            if k > 3:
                continue
            if not bd.is_safe(occ):
                continue
            n_checked += 1
            f = f_vector(bd, occ)
            ok, r = is_log_concave(f)
            if not ok:
                all_fail.append({
                    "occ": occ, "k": k, "f": f, "fail_r": r,
                    "points": [(bx, by) for by in range(n) for bx in range(n)
                               if occ & (1 << (by * n + bx))],
                })

    return {
        "n": n,
        "V": V,
        "F": len(bd.quads),
        "empty_f": empty_f,
        "empty_log_concave": empty_ok,
        "empty_fail_r": empty_r,
        "B563": {
            "n_single_fail": n_single_fail,
            "fail_example": fail_example,
            "all_singles": single_results,
        },
        "B561": {
            "n_checked": n_checked,
            "n_fail": len(all_fail),
            "failures": all_fail[:10],
            "scope": "all safe subsets" if n <= 4 else "all safe subsets with k<=3",
        },
        "timing_s": round(time.time() - t0, 2),
    }


def main():
    ns = [3, 4]
    if len(sys.argv) > 1:
        ns = [int(x) for x in sys.argv[1].split(",")]
    out = {}
    for n in ns:
        print(f"=== n={n} ===", flush=True)
        r = analyze(n)
        out[f"n{n}"] = r
        brief = {
            "empty_f": r["empty_f"], "empty_log_concave": r["empty_log_concave"],
            "B563_n_single_fail": r["B563"]["n_single_fail"],
            "B563_example": r["B563"]["fail_example"],
            "B561": {k: r["B561"][k] for k in ("n_checked", "n_fail", "scope")},
            "B561_first_fail": r["B561"]["failures"][:1],
        }
        print(json.dumps(brief, ensure_ascii=False, indent=1)[:2000], flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
