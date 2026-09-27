"""round2_b591_dmax.py — d_max distribution for B591/B592/B593/B597/B598.

d_max(S) = min_{M maximum safe} |S \\ M|.
For n<=5 enumerates safe sets and max sets directly.
For n=6,7 loads pre-enumerated layers from research/verification/data and night-research.
Writes research/verification/round2_b591.json.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b591.json"

# Known K_n (PROTOCOL / batch-05)
KNOWN_K = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15}


def det4_rows(r0, r1, r2, r3):
    def det3(m):
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    m = [r1, r2, r3]
    total = 0
    for i in range(4):
        minor = [[m[a][b] for b in range(4) if b != i] for a in range(3)]
        total += (1 if i % 2 == 0 else -1) * r0[i] * det3(minor)
    return total


def pt_row(x, y):
    return [x * x + y * y, x, y, 1]


def forbidden_quad_masks(n: int) -> list[int]:
    pts = [(i % n, i // n) for i in range(n * n)]
    rows = [pt_row(x, y) for x, y in pts]
    quads = []
    for a, b, c, d in combinations(range(n * n), 4):
        if det4_rows(rows[a], rows[b], rows[c], rows[d]) == 0:
            quads.append((1 << a) | (1 << b) | (1 << c) | (1 << d))
    return quads


def is_safe(mask: int, quads: list[int]) -> bool:
    for q in quads:
        if mask & q == q:
            return False
    return True


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


def enumerate_safe_k(n: int, k: int, quads: list[int]) -> list[int]:
    """All safe k-subsets as bitmasks, pruned DFS (points id = y*n+x)."""
    v = n * n
    quads_by_point: list[list[int]] = [[] for _ in range(v)]
    for q in quads:
        pts = [i for i in range(v) if (q >> i) & 1]
        for p in pts:
            quads_by_point[p].append(q & ~(1 << p))

    out: list[int] = []

    def dfs(start: int, chosen: int, count: int) -> None:
        if count == k:
            out.append(chosen)
            return
        # remaining points insufficient
        if count + (v - start) < k:
            return
        for p in range(start, v):
            ok = True
            for others in quads_by_point[p]:
                if chosen & others == others:
                    ok = False
                    break
            if ok:
                dfs(p + 1, chosen | (1 << p), count + 1)

    dfs(0, 0, 0)
    return out


def dmax_layer(safe_sets: list[int], max_sets: list[int]) -> dict:
    """d_max histogram and extremes for one layer."""
    hist: Counter = Counter()
    dvals = []
    worst = None
    worst_d = -1
    for s in safe_sets:
        best = 10**9
        for m in max_sets:
            d = (s & ~m).bit_count()
            if d < best:
                best = d
                if best == 0:
                    break
        hist[best] += 1
        dvals.append(best)
        if best > worst_d:
            worst_d = best
            worst = s
    dvals_sorted = sorted(dvals)
    n = len(dvals)
    return {
        "count": n,
        "dmax_hist": {str(k): hist[k] for k in sorted(hist)},
        "dmax_min": dvals_sorted[0] if n else None,
        "dmax_max": dvals_sorted[-1] if n else None,
        "dmax_mean": (sum(dvals) / n) if n else None,
        "dmax_median": dvals_sorted[n // 2] if n else None,
        "worst_mask": worst,
        "num_extendable": hist.get(0, 0),
        "num_not_extendable": n - hist.get(0, 0),
    }


def dmax_layer_numpy(safe_sets: list[int], max_sets: list[int]) -> dict:
    """Vectorized d_max via numpy popcount (for large layers)."""
    import numpy as np

    popc = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)

    def popcount_u64(arr: np.ndarray) -> np.ndarray:
        b = arr.view(np.uint8).reshape(-1, 8)
        return popc[b].sum(axis=1).astype(np.int16)

    s_arr = np.array(safe_sets, dtype=np.uint64)
    m_arr = np.array(max_sets, dtype=np.uint64)
    max_inter = np.zeros(len(s_arr), dtype=np.int16)
    for m in m_arr:
        inter = popcount_u64(s_arr & m)
        np.maximum(max_inter, inter, out=max_inter)
    # |S| is constant within layer
    k = int(s_arr[0]).bit_count()
    dvals = k - max_inter
    hist = Counter(int(x) for x in dvals)
    worst_idx = int(np.argmax(dvals))
    return {
        "count": len(safe_sets),
        "dmax_hist": {str(kk): hist[kk] for kk in sorted(hist)},
        "dmax_min": int(dvals.min()),
        "dmax_max": int(dvals.max()),
        "dmax_mean": float(dvals.mean()),
        "dmax_median": int(np.median(dvals)),
        "worst_mask": int(s_arr[worst_idx]),
        "num_extendable": int(hist.get(0, 0)),
        "num_not_extendable": int(len(safe_sets) - hist.get(0, 0)),
    }


def main():
    t0 = time.time()
    results: dict = {"_meta": {"script": "round2_b591_dmax.py", "K_n": KNOWN_K}}

    # ---------- n=2..5 direct enumeration ----------
    for n in range(2, 6):
        print(f"n={n}: enumerating forbidden quads", flush=True)
        quads = forbidden_quad_masks(n)
        K = KNOWN_K[n]
        v = n * n
        print(f"  F_{n}={len(quads)}, K_{n}={K}", flush=True)

        # max sets = safe sets of size K (automatically maximal)
        max_sets = enumerate_safe_k(n, K, quads)
        print(f"  max sets size {K}: {len(max_sets)}", flush=True)
        assert len(max_sets) > 0

        entry = {
            "n": n,
            "K_n": K,
            "F_n": len(quads),
            "max_set_count": len(max_sets),
            "layers": {},
            "counts": {},
        }
        for c in range(0, min(K, 5) + 1):
            k = K - c
            if k <= 0:
                continue
            if k == K:
                entry["counts"][str(k)] = len(max_sets)
                entry["layers"][str(k)] = {
                    "count": len(max_sets),
                    "dmax_hist": {"0": len(max_sets)},
                    "dmax_max": 0,
                    "num_extendable": len(max_sets),
                }
                continue
            t1 = time.time()
            sets = enumerate_safe_k(n, k, quads)
            print(f"  size {k} (def {c}): {len(sets)} safe, {time.time()-t1:.1f}s", flush=True)
            entry["counts"][str(k)] = len(sets)
            st = dmax_layer(sets, max_sets)
            entry["layers"][str(k)] = st
            print(
                f"    dmax max={st['dmax_max']} hist={st['dmax_hist']}",
                flush=True,
            )
        results[f"n{n}"] = entry

    # ---------- n=6 from bins ----------
    print("n=6: loading bins", flush=True)
    max6 = load_bin(NIGHT / "maxsafe_n6_K11.bin")
    assert all(m.bit_count() == 11 for m in max6)
    entry6 = {
        "n": 6,
        "K_n": 11,
        "max_set_count": len(max6),
        "layers": {},
        "counts": {},
    }
    for k, fn in [(8, "safe_n6_k8.bin"), (9, "safe_n6_k9.bin"), (10, "safe_n6_k10.bin"), (11, "maxsafe_n6_K11.bin")]:
        path = DATA / fn if k < 11 else NIGHT / fn
        sets = load_bin(path)
        entry6["counts"][str(k)] = len(sets)
        t1 = time.time()
        if k == 11:
            entry6["layers"]["11"] = {
                "count": len(sets),
                "dmax_hist": {"0": len(sets)},
                "dmax_max": 0,
                "num_extendable": len(sets),
            }
        else:
            print(f"  computing dmax size {k} ({len(sets)} sets) vs {len(max6)} max", flush=True)
            st = dmax_layer_numpy(sets, max6)
            entry6["layers"][str(k)] = st
            print(f"    dmax max={st['dmax_max']} hist={st['dmax_hist']} ({time.time()-t1:.1f}s)", flush=True)
    results["n6"] = entry6

    # ---------- n=7 from bins ----------
    print("n=7: loading bins", flush=True)
    max7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    assert all(m.bit_count() == 14 for m in max7)
    entry7 = {
        "n": 7,
        "K_n": 14,
        "max_set_count": len(max7),
        "layers": {},
        "counts": {},
    }
    for k, fn in [(12, "safe_n7_k12.bin"), (13, "safe_n7_k13.bin"), (14, "maxsafe_n7_K14.bin")]:
        path = DATA / fn if k < 14 else NIGHT / fn
        sets = load_bin(path)
        entry7["counts"][str(k)] = len(sets)
        if k == 14:
            entry7["layers"]["14"] = {
                "count": len(sets),
                "dmax_hist": {"0": len(sets)},
                "dmax_max": 0,
                "num_extendable": len(sets),
            }
        else:
            t1 = time.time()
            print(f"  computing dmax size {k} ({len(sets)} sets)", flush=True)
            st = dmax_layer_numpy(sets, max7)
            entry7["layers"][str(k)] = st
            print(f"    dmax max={st['dmax_max']} hist={st['dmax_hist']} ({time.time()-t1:.1f}s)", flush=True)
    results["n7"] = entry7

    # ---------- B591/B592 summary: max d_max among (K_n-1) sets ----------
    b591 = {}
    for n in range(2, 8):
        key = f"n{n}"
        if key not in results:
            continue
        K = results[key]["K_n"]
        layer = results[key]["layers"].get(str(K - 1))
        if layer:
            b591[str(n)] = {
                "K_n": K,
                "layer_size": K - 1,
                "count": layer["count"],
                "dmax_max": layer["dmax_max"],
                "dmax_hist": layer["dmax_hist"],
                "dmax_mean": layer.get("dmax_mean"),
            }
    results["b591_b592_deficiency1"] = b591

    # ---------- B593: d_max / deficiency ratio ----------
    b593 = {}
    for n in range(2, 8):
        key = f"n{n}"
        if key not in results:
            continue
        K = results[key]["K_n"]
        ratios = {}
        for ks, layer in results[key]["layers"].items():
            k = int(ks)
            c = K - k
            if c <= 0 or layer.get("dmax_max") is None:
                continue
            ratios[str(c)] = {
                "deficiency": c,
                "dmax_max": layer["dmax_max"],
                "ratio": layer["dmax_max"] / c if c else None,
                "count": layer["count"],
            }
        b593[str(n)] = ratios
    results["b593_ratios"] = b593

    # ---------- B597/B598: counts ----------
    counts_table = {}
    for n in range(2, 8):
        key = f"n{n}"
        if key not in results:
            continue
        K = results[key]["K_n"]
        nmax = results[key]["max_set_count"]
        row = {"K_n": K, "max_set_count": nmax, "layers": {}}
        for ks, cnt in results[key]["counts"].items():
            c = K - int(ks)
            if c < 0:
                continue
            row["layers"][str(c)] = {
                "size": int(ks),
                "count": cnt,
                "ratio_to_max": cnt / nmax if nmax else None,
            }
        counts_table[str(n)] = row
    results["b597_b598_counts"] = counts_table

    results["_meta"]["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} in {results['_meta']['elapsed_sec']}s", flush=True)


if __name__ == "__main__":
    main()
