#!/usr/bin/env python3
"""round3_chunk8_b521.py — B521: FULL exhaustive check of all quad-pair removals
on the 4x4 board.  Complete over C(194,2) = 18721 pairs, parallel over cores.

Also emits per-pair g values for reuse, plus the 3x3 analogue (F=14, all 91 pairs).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from round3_chunk8_lib import Quads, all_forbidden, is_collinear, square  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round3_chunk8_b521.json"

_PTS = None
_QUADS = None


def _init(n):
    global _PTS, _QUADS
    _PTS = square(n)
    _QUADS = all_forbidden(_PTS)


def _job(args):
    i, j = args
    q = Quads(_PTS, [t for k, t in enumerate(_QUADS) if k != i and k != j], name="v")
    return (i, j, q.grundy()[0])


def run_pairs(n, label):
    _init(n)
    F = len(_QUADS)
    pairs = list(combinations(range(F), 2))
    base = Quads(_PTS, _QUADS).grundy()[0]
    print(f"[{label}] F={F} base_g={base} pairs={len(pairs)}", flush=True)
    t0 = time.time()
    ctx = mp.get_context("spawn")
    with ctx.Pool(16, initializer=_init, initargs=(n,)) as pool:
        out = []
        for k, r in enumerate(pool.imap_unordered(_job, pairs, chunksize=64)):
            out.append(r)
            if (k + 1) % 2000 == 0:
                print(f"  {label} {k+1}/{len(pairs)} ({time.time()-t0:.0f}s)", flush=True)
    flips = [r for r in out if (r[2] == 0) != (base == 0)]
    ghist = Counter(r[2] for r in out)
    return {
        "n": n,
        "F": F,
        "base_g": base,
        "n_pairs_total": len(pairs),
        "n_pairs_expected": F * (F - 1) // 2,
        "complete": len(pairs) == F * (F - 1) // 2,
        "n_flips": len(flips),
        "flip_pairs": [{"i": i, "j": j, "g": g} for i, j, g in flips[:20]],
        "g_hist_after_removal": {str(k): v for k, v in sorted(ghist.items())},
        "seconds": round(time.time() - t0, 1),
    }


def run_sample(n, label, nsamp, seed=11):
    """Random sample of pairs on a larger board."""
    import random
    _init(n)
    F = len(_QUADS)
    rng = random.Random(seed)
    pairs = [tuple(sorted(rng.sample(range(F), 2))) for _ in range(nsamp)]
    pairs = sorted(set(pairs))
    base = Quads(_PTS, _QUADS).grundy()[0]
    print(f"[{label}] F={F} base_g={base} sample={len(pairs)}", flush=True)
    t0 = time.time()
    ctx = mp.get_context("spawn")
    with ctx.Pool(16, initializer=_init, initargs=(n,)) as pool:
        out = list(pool.imap_unordered(_job, pairs, chunksize=4))
    flips = [r for r in out if (r[2] == 0) != (base == 0)]
    return {
        "n": n, "F": F, "base_g": base,
        "n_pairs_total": F * (F - 1) // 2,
        "n_pairs_sampled": len(pairs),
        "n_flips": len(flips),
        "flip_pairs": [{"i": i, "j": j, "g": g} for i, j, g in flips[:20]],
        "g_hist_after_removal": {str(k): v for k, v in sorted(Counter(r[2] for r in out).items())},
        "seconds": round(time.time() - t0, 1),
    }


def main():
    res = {"_meta": {"script": "round3_chunk8_b521.py"}}
    res["n3"] = run_pairs(3, "n3")
    print("n3 done:", res["n3"]["n_flips"], "flips", flush=True)
    res["n4"] = run_pairs(4, "n4")
    print("n4 done:", res["n4"]["n_flips"], "flips", flush=True)
    res["n5"] = run_sample(5, "n5", 300)
    print("n5 done:", res["n5"]["n_flips"], "flips", flush=True)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
