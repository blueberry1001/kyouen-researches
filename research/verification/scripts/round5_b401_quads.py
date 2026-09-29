#!/usr/bin/env python3
"""Round5 B521/B522: 4x4 forbidden-quad removal winner flips.

4x4 has F=194 forbidden quads (10 line + 184 circle), empty board g=0 (second wins).

B521: ALL pairs of quads simultaneously un-forbidden — does the empty-board
      winner ever flip to first?
B522: ALL triples? (sample / structured) — any triple that flips?

Method: precompute for every subset of the 16 points which quads it contains.
A subset is legal under removed set R iff C(S) ⊆ R.
For pair removal, legal(S) = C(S) ⊆ {a,b}, so we only need the buckets
C(S)=∅, {a}, {b}, {a,b}. Solve impartial win/lose on that state set.
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

OUT = REPO_ROOT / "research" / "verification" / "round5_b401_quads.json"


_WIN_CACHE: dict[frozenset, int] = {}


def solve_winner(states: set[int], V: int, forbidden: list[int] | None = None) -> int:
    """Return g(empty): 1 if first player wins (N), 0 if second (P)."""
    key = frozenset(states)
    hit = _WIN_CACHE.get(key)
    if hit is not None:
        return hit
    present = bytearray(1 << V)
    for s in states:
        present[s] = 1
    win = bytearray(1 << V)  # 0 unknown/lose, 1 win; only meaningful if present
    # process by descending popcount
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
                v = lsb.bit_length() - 1
                child = s | lsb
                if present[child] and win[child] == 0:
                    w = 1
                    break
                e ^= lsb
            win[s] = w
    result = 1 if win[0] else 0
    if len(_WIN_CACHE) < 64:
        _WIN_CACHE[key] = result
    return result


def main():
    t0 = time.time()
    n = 4
    bd = board_square(n)
    V = bd.V  # 16
    quads = list(bd.quads)  # 194
    F = len(quads)
    print(f"V={V} F={F}", flush=True)

    # map quad bitmask -> index
    qidx = {q: i for i, q in enumerate(quads)}

    # For all 2^16 subsets, compute contained-quad fingerprint
    # fingerprint = frozenset of quad indices (usually tiny)
    full = (1 << V) - 1
    bucket0: list[int] = []  # C(S)=∅
    bucket1: dict[int, list[int]] = {i: [] for i in range(F)}  # C(S)={q_i}
    bucket2: dict[tuple[int, int], list[int]] = {}  # C(S)={q_i,q_j}
    n_other = 0  # |C(S)|>=3 or other

    t1 = time.time()
    for s in range(full + 1):
        cont = []
        for qi, q in enumerate(quads):
            if (s & q) == q:
                cont.append(qi)
                if len(cont) > 2:
                    break
        if len(cont) == 0:
            bucket0.append(s)
        elif len(cont) == 1:
            bucket1[cont[0]].append(s)
        elif len(cont) == 2:
            key = (cont[0], cont[1]) if cont[0] < cont[1] else (cont[1], cont[0])
            # need full cont - we broke early? No, len==2 and not >2 so complete
            bucket2.setdefault(key, []).append(s)
        else:
            n_other += 1
    print(f"buckets: empty={len(bucket0)} single={sum(len(v) for v in bucket1.values())} "
          f"pair={sum(len(v) for v in bucket2.values())} other={n_other} "
          f"scan={time.time()-t1:.1f}s", flush=True)

    # baseline (no removal): winner on bucket0 only
    base_g = solve_winner(set(bucket0), V, quads)
    print(f"base g={base_g} ({time.time()-t0:.1f}s)", flush=True)

    # B521: all pairs
    t2 = time.time()
    pair_flips = []
    n_tested = 0
    # For speed, note: if |C(S)|>=3, S never legal under 2 removals. Good.
    for a, b in combinations(range(F), 2):
        states = set(bucket0)
        states.update(bucket1[a])
        states.update(bucket1[b])
        states.update(bucket2.get((a, b), []))
        g = solve_winner(states, V, quads)
        n_tested += 1
        if g != base_g:
            pair_flips.append({"a": a, "b": b, "g": g,
                               "a_kind": "line" if a < 10 else "circle",
                               "b_kind": "line" if b < 10 else "circle",
                               "n_states": len(states)})
        if n_tested % 500 == 0:
            print(f"  pairs {n_tested}/{F*(F-1)//2} flips={len(pair_flips)} "
                  f"{time.time()-t2:.1f}s", flush=True)

    print(f"B521 done: tested={n_tested} flips={len(pair_flips)} "
          f"{time.time()-t2:.1f}s", flush=True)

    out = {
        "n": 4,
        "V": V,
        "F": F,
        "kind_hist": {"line": 10, "circle": 184},
        "base_g": base_g,
        "bucket_sizes": {
            "empty": len(bucket0),
            "single_total": sum(len(v) for v in bucket1.values()),
            "pair_total": sum(len(v) for v in bucket2.values()),
            "other": n_other,
        },
        "B521": {
            "n_pairs_tested": n_tested,
            "n_expected": F * (F - 1) // 2,
            "complete": n_tested == F * (F - 1) // 2,
            "n_flips": len(pair_flips),
            "flips": pair_flips[:20],
        },
        "timing_s": {"total": round(time.time() - t0, 2)},
    }

    # B522 sample: structured triples sharing 3 points already 0; try
    # triples from bucket structure — a triple flip needs states with C(S)⊆{a,b,c}
    # Quick structured scan: all triples within each circle bundle is too many.
    # Do all triples (a,b,c) where there exists S with C(S) ⊇ {a,b,c} and |C(S)|=3,
    # i.e. the pair-bucket extended. We scan all combinations of 3 quads that
    # co-occur in some S with C(S) exactly those 3.
    print("B522: scanning triple-cooccurrence buckets...", flush=True)
    bucket3: dict[tuple, list[int]] = {}
    t3 = time.time()
    for s in range(full + 1):
        cont = [qi for qi, q in enumerate(quads) if (s & q) == q]
        if len(cont) == 3:
            key = tuple(sorted(cont))
            bucket3.setdefault(key, []).append(s)
    print(f"  exact-3 buckets={len(bucket3)} states={sum(len(v) for v in bucket3.values())} "
          f"{time.time()-t3:.1f}s", flush=True)

    # also need states with C(S) subset of triple that aren't already in smaller buckets
    # For triple {a,b,c}: legal = bucket0 ∪ single[a,b,c] ∪ pair[a,b],pair[a,c],pair[b,c] ∪ triple[a,b,c]
    t4 = time.time()
    triple_flips = []
    n3 = 0
    # Only test triples that actually have a nonempty bucket3 (otherwise same as some pair)
    candidates = list(bucket3.keys())
    print(f"  candidate triples with |C(S)|=3 exactly: {len(candidates)}", flush=True)
    for (a, b, c) in candidates:
        states = set(bucket0)
        for x in (a, b, c):
            states.update(bucket1[x])
        for xy in ((a, b), (a, c), (b, c)):
            key = tuple(sorted(xy))
            states.update(bucket2.get(key, []))
        states.update(bucket3[(a, b, c)])
        g = solve_winner(states, V, quads)
        n3 += 1
        if g != base_g:
            triple_flips.append({"a": a, "b": b, "c": c, "g": g, "n_states": len(states)})
        if n3 % 200 == 0:
            print(f"  triples {n3}/{len(candidates)} flips={len(triple_flips)} "
                  f"{time.time()-t4:.1f}s", flush=True)

    out["B522"] = {
        "n_triples_tested": n3,
        "n_candidates": len(candidates),
        "note": "only triples with some S having C(S) exactly {a,b,c}; others reduce to pair/single",
        "n_flips": len(triple_flips),
        "flips": triple_flips[:20],
    }
    out["timing_s"]["total"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, flush=True)
    print(json.dumps({k: out[k] for k in ("base_g", "bucket_sizes", "B521", "B522")},
                     ensure_ascii=False, indent=1)[:2500], flush=True)


if __name__ == "__main__":
    main()
