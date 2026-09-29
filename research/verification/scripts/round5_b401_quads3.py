#!/usr/bin/env python3
"""Round5 B522 focused: triples of 4x4 quads whose simultaneous removal flips winner.

Only triples with some S having C(S) exactly {a,b,c} need testing for a NEW flip
beyond what pairs already showed (pairs: 0 flips). Also test a broader
structured set: all triples co-occurring in some S with |C(S)|<=3.
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

OUT = REPO_ROOT / "research" / "verification" / "round5_b401_quads3.json"


def solve_winner(present: bytearray, win: bytearray, states: list[int], V: int) -> int:
    win[:] = b"\x00" * (1 << V)
    by_size: list[list[int]] = [[] for _ in range(V + 1)]
    for s in states:
        by_size[s.bit_count()].append(s)
    for k in range(V, -1, -1):
        for s in by_size[k]:
            empty = ((1 << V) - 1) ^ s
            w = 0
            e = empty
            while e:
                lsb = e & -e
                child = s | lsb
                if present[child] and win[child] == 0:
                    w = 1
                    break
                e ^= lsb
            win[s] = w
    return 1 if win[0] else 0


def main():
    t0 = time.time()
    n = 4
    bd = board_square(n)
    V = bd.V
    quads = list(bd.quads)
    F = len(quads)
    full = (1 << V) - 1

    # classify all subsets by C(S) size <= 3
    bucket: dict[tuple, list[int]] = {}
    n_ge4 = 0
    for s in range(full + 1):
        cont = []
        for qi, q in enumerate(quads):
            if (s & q) == q:
                cont.append(qi)
                if len(cont) > 3:
                    break
        if len(cont) > 3:
            n_ge4 += 1
            continue
        bucket.setdefault(tuple(sorted(cont)), []).append(s)

    sizes = {k: len(v) for k, v in bucket.items()}
    n0 = len(bucket.get((), []))
    n1 = sum(len(v) for k, v in bucket.items() if len(k) == 1)
    n2 = sum(len(v) for k, v in bucket.items() if len(k) == 2)
    n3 = sum(len(v) for k, v in bucket.items() if len(k) == 3)
    print(f"buckets empty={n0} 1={n1} 2={n2} 3={n3} ge4={n_ge4} "
          f"keys3={sum(1 for k in bucket if len(k)==3)}", flush=True)

    present = bytearray(1 << V)
    win = bytearray(1 << V)

    def winner_for(removed: tuple) -> int:
        states = []
        present[:] = b"\x00" * (1 << V)
        rset = frozenset(removed)
        for k, lst in bucket.items():
            if set(k) <= rset:
                states.extend(lst)
        for s in states:
            present[s] = 1
        return solve_winner(present, win, states, V)

    base = winner_for(())
    print(f"base g={base}", flush=True)

    # All triples that appear as a key of size 3, plus all triples that are
    # subsets of some key of size 3 (redundant) — just use size-3 keys.
    # ALSO: any triple {a,b,c} where some S has C(S) ⊆ {a,b,c} and |C(S)|=3.
    # That's exactly the size-3 keys.
    # For completeness also test ALL triples among quads that co-occur in ANY
    # bucket key of size <=3 (broader structured set).
    quads_in_small = set()
    for k in bucket:
        quads_in_small.update(k)
    print(f"quads appearing in |C|<=3: {len(quads_in_small)}", flush=True)

    # First: exact size-3 keys (minimal new legal states vs pairs)
    keys3 = [k for k in bucket if len(k) == 3]
    flips = []
    t1 = time.time()
    for i, trip in enumerate(keys3):
        g = winner_for(trip)
        if g != base:
            flips.append({"triple": list(trip), "g": g, "n_states": sum(
                len(v) for k, v in bucket.items() if set(k) <= set(trip))})
        if (i + 1) % 500 == 0:
            print(f"  keys3 {i+1}/{len(keys3)} flips={len(flips)} {time.time()-t1:.1f}s", flush=True)
    print(f"keys3 done flips={len(flips)} {time.time()-t1:.1f}s", flush=True)

    # Broader: all triples from quads_in_small would be C(|Q|,3) — too many if
    # |Q| large. Sample: all triples that share at least one pair-key with a third.
    # pair_keys = size-2 keys; extend each with every other quad that co-occurs
    # in some size-3 key with that pair.
    pair_to_thirds: dict[tuple, set[int]] = {}
    for k in bucket:
        if len(k) == 3:
            a, b, c = k
            pair_to_thirds.setdefault((a, b), set()).add(c)
            pair_to_thirds.setdefault((a, c), set()).add(b)
            pair_to_thirds.setdefault((b, c), set()).add(a)
    extra = []
    seen = set(keys3)
    for pair, thirds in pair_to_thirds.items():
        for c in thirds:
            trip = tuple(sorted(pair + (c,)))
            if trip not in seen:
                seen.add(trip)
                extra.append(trip)
    print(f"extra structured triples: {len(extra)}", flush=True)
    t2 = time.time()
    for i, trip in enumerate(extra):
        g = winner_for(trip)
        if g != base:
            flips.append({"triple": list(trip), "g": g, "extra": True})
        if (i + 1) % 500 == 0:
            print(f"  extra {i+1}/{len(extra)} flips={len(flips)} {time.time()-t2:.1f}s", flush=True)

    out = {
        "n": 4,
        "V": V,
        "F": F,
        "base_g": base,
        "bucket_sizes": {"empty": n0, "single": n1, "pair": n2, "exact3": n3, "ge4": n_ge4},
        "B522": {
            "n_keys3_tested": len(keys3),
            "n_extra_tested": len(extra),
            "n_flips": len(flips),
            "flips": flips[:30],
            "delta_quad_bounds": {"lower": 3, "upper": 70,
                                  "note": "B521: all pairs keep second win; circle-bundle 70 flips"},
        },
        "timing_s": {"total": round(time.time() - t0, 2)},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)
    print(json.dumps(out["B522"], indent=1)[:1500])


if __name__ == "__main__":
    main()
