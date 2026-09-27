"""round2_b591_followup.py — B594 orbit-occupancy comparison, B600 structural search.

B594: count distinct D4 orbit-occupancy vectors among maximal 13-sets
      vs distinct (d_A,d_B) pairs.
B600: find safe S with d_max(S)=1 and h(S)=K(S)-|S| >= 3 on n=5 (full) and n=6 (sample).
      Note: d_max>=1 implies K(S)<K_n, hence |S|<=K_n-4 is necessary for h>=3.

Merges keys "b594_orbit" and "b600_structural" into round2_b591.json.
"""
from __future__ import annotations

import json
import struct
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b591.json"


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


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


def forbidden_quads(n: int):
    pts = [(i % n, i // n) for i in range(n * n)]
    rows = [pt_row(x, y) for x, y in pts]
    quads = []
    for a, b, c, d in combinations(range(n * n), 4):
        if det4_rows(rows[a], rows[b], rows[c], rows[d]) == 0:
            quads.append((a, b, c, d))
    return quads


def build_inc(n: int, quads):
    v = n * n
    inc: list[list[int]] = [[] for _ in range(v)]
    for a, b, c, d in quads:
        for p, others in (
            (a, (1 << b) | (1 << c) | (1 << d)),
            (b, (1 << a) | (1 << c) | (1 << d)),
            (c, (1 << a) | (1 << b) | (1 << d)),
            (d, (1 << a) | (1 << b) | (1 << c)),
        ):
            inc[p].append(others)
    return inc


def d4_orbit_index(n: int):
    def transform(kind, x, y):
        return [
            (x, y), (y, x), (n - 1 - x, y), (x, n - 1 - y),
            (n - 1 - x, n - 1 - y), (n - 1 - y, n - 1 - x),
            (y, n - 1 - x), (n - 1 - y, x),
        ][kind]

    parent = list(range(n * n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for p in range(n * n):
        x, y = p % n, p // n
        for kind in range(8):
            tx, ty = transform(kind, x, y)
            union(p, ty * n + tx)
    roots: dict[int, int] = {}
    orbit_id = []
    for p in range(n * n):
        r = find(p)
        if r not in roots:
            roots[r] = len(roots)
        orbit_id.append(roots[r])
    return orbit_id, len(roots)


def occupancy_key(mask: int, orbit_id: list[int], n_orb: int) -> tuple:
    cnt = [0] * n_orb
    for p in range(len(orbit_id)):
        if (mask >> p) & 1:
            cnt[orbit_id[p]] += 1
    return tuple(cnt)


def addable_points(mask: int, n: int, inc: list[list[int]]) -> list[int]:
    out = []
    for p in range(n * n):
        if (mask >> p) & 1:
            continue
        ok = True
        for others in inc[p]:
            if mask & others == others:
                ok = False
                break
        if ok:
            out.append(p)
    return out


def enum_safe(n: int, k: int, inc: list[list[int]]) -> list[int]:
    v = n * n
    out: list[int] = []

    def dfs(start: int, chosen: int, count: int) -> None:
        if count == k:
            out.append(chosen)
            return
        if count + (v - start) < k:
            return
        for p in range(start, v):
            ok = True
            for others in inc[p]:
                if chosen & others == others:
                    ok = False
                    break
            if ok:
                dfs(p + 1, chosen | (1 << p), count + 1)

    dfs(0, 0, 0)
    return out


def main():
    t0 = time.time()
    results: dict = {}

    # ---------- B594 orbit occupancy ----------
    n = 7
    s13 = load_bin(DATA / "safe_n7_k13.bin")
    max7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    center_bit = 1 << (3 * n + 3)
    A = [m for m in max7 if m & center_bit]
    B = [m for m in max7 if not (m & center_bit)]
    orbit_id, n_orb = d4_orbit_index(n)
    print(f"D4 orbits on {n}x{n}: {n_orb}", flush=True)

    occ_keys = set()
    pair_of_key: dict[tuple, set] = {}
    maximal_occ = set()
    maximal_pairs = set()
    for s in s13:
        dA = min((s & ~m).bit_count() for m in A)
        dB = min((s & ~m).bit_count() for m in B)
        key = occupancy_key(s, orbit_id, n_orb)
        occ_keys.add(key)
        pair_of_key.setdefault(key, set()).add((dA, dB))
        if min(dA, dB) >= 1:
            maximal_occ.add(key)
            maximal_pairs.add((dA, dB))

    multi = {k: v for k, v in pair_of_key.items() if len(v) > 1}
    results["b594_orbit"] = {
        "n_orbits": n_orb,
        "distinct_occ_all13": len(occ_keys),
        "distinct_occ_maximal13": len(maximal_occ),
        "distinct_pairs_maximal": len(maximal_pairs),
        "occ_keys_with_multiple_pairs": len(multi),
        "comment": (
            f"極大13石の (dA,dB) 型 {len(maximal_pairs)} に対し軌道占有ベクトルは "
            f"{len(maximal_occ)} 通り。"
        ),
    }
    print("B594:", results["b594_orbit"], flush=True)

    # ---------- B600 structural ----------
    # d_max(S)>=1 => K(S)<K_n => h<=K_n-1-|S|; h>=3 needs |S|<=K_n-4.
    b600_out = {}

    # ---- n=5 full ----
    n, K = 5, 9
    quads = forbidden_quads(n)
    inc = build_inc(n, quads)
    v = n * n
    max_sets = enum_safe(n, K, inc)
    safe8 = enum_safe(n, 8, inc)
    size5 = enum_safe(n, 5, inc)
    print(f"n=5 max={len(max_sets)} safe8={len(safe8)} size5={len(size5)}", flush=True)

    contains: set[int] = set()
    for t in safe8:
        pts = [i for i in range(v) if (t >> i) & 1]
        for comb in combinations(pts, 5):
            m = 0
            for p in comb:
                m |= 1 << p
            contains.add(m)
    print(f"n=5 size5 contained in some safe8: {len(contains)}", flush=True)

    candidates = []
    for s in size5:
        if s not in contains:
            continue
        dmax = min((s & ~m).bit_count() for m in max_sets)
        if dmax != 1:
            continue
        # K(S)>=8 and K(S)<=8 (dmax>=1 forbids 9) so K(S)=8, h=3
        add = addable_points(s, n, inc)
        cands = set()
        best_discards = []
        for m in max_sets:
            diff = s & ~m
            if diff.bit_count() == 1:
                best_discards.append((diff.bit_length() - 1, m & ~s))
        for disc, addpts in best_discards:
            for p in range(v):
                if (addpts >> p) & 1:
                    cands.add(p)
        candidates.append({
            "size": 5,
            "mask": s,
            "pts": [i for i in range(v) if (s >> i) & 1],
            "coords": [[i % n, i // n] for i in range(v) if (s >> i) & 1],
            "dmax": 1,
            "K_S": 8,
            "h": 3,
            "addable": add,
            "shortmod_cands": sorted(cands),
            "shortmod_addable": sorted(set(add) & cands),
            "n_best_max": len(best_discards),
        })
    print(f"n=5 B600 structural candidates: {len(candidates)}", flush=True)
    b600_out["5"] = {
        "K_n": K,
        "max_set_count": len(max_sets),
        "size5_safe": len(size5),
        "size5_in_some_safe8": len(contains),
        "candidates_count": len(candidates),
        "candidates_sample": candidates[:8],
        "h_hist": {"3": len(candidates)},
        "note": "構造条件のみ。g(S)・必勝手・勝敗維持対局は未判定。",
    }

    # ---- n=6 sample ----
    n, K = 6, 11
    quads = forbidden_quads(n)
    inc = build_inc(n, quads)
    max_sets = load_bin(NIGHT / "maxsafe_n6_K11.bin")
    size5 = enum_safe(n, 5, inc)
    print(f"n=6 size5 safe={len(size5)}", flush=True)
    d1 = []
    for s in size5:
        dmax = min((s & ~m).bit_count() for m in max_sets)
        if dmax == 1:
            d1.append(s)
    print(f"n=6 size5 dmax=1: {len(d1)}", flush=True)

    def max_extend_size(mask, n, inc, known_K):
        v = n * n
        best = mask.bit_count()

        def dfs(chosen, start):
            nonlocal best
            cur = chosen.bit_count()
            if cur + (v - start) < best:
                return
            if cur > best:
                best = cur
            for p in range(start, v):
                if (chosen >> p) & 1:
                    continue
                ok = True
                for others in inc[p]:
                    if chosen & others == others:
                        ok = False
                        break
                if ok:
                    dfs(chosen | (1 << p), p + 1)

        dfs(mask, 0)
        return best

    sample = d1[:: max(1, len(d1) // 25)][:25]
    cand6 = []
    for s in sample:
        ks = max_extend_size(s, n, inc, K)
        h = ks - 5
        if h >= 3:
            add = addable_points(s, n, inc)
            cands = set()
            best_discards = []
            for m in max_sets:
                diff = s & ~m
                if diff.bit_count() == 1:
                    best_discards.append((diff.bit_length() - 1, m & ~s))
            for disc, addpts in best_discards:
                for p in range(n * n):
                    if (addpts >> p) & 1:
                        cands.add(p)
            cand6.append({
                "size": 5,
                "mask": s,
                "pts": [i for i in range(n * n) if (s >> i) & 1],
                "coords": [[i % n, i // n] for i in range(n * n) if (s >> i) & 1],
                "dmax": 1,
                "K_S": ks,
                "h": h,
                "addable": add,
                "shortmod_cands": sorted(cands),
                "shortmod_addable": sorted(set(add) & cands),
                "n_best_max": len(best_discards),
            })
    b600_out["6"] = {
        "K_n": K,
        "max_set_count": len(max_sets),
        "size5_safe": len(size5),
        "size5_dmax1": len(d1),
        "sample_tested": len(sample),
        "candidates_count": len(cand6),
        "candidates_sample": cand6[:6],
        "h_hist": {str(k): v for k, v in sorted(Counter(c["h"] for c in cand6).items())},
        "note": "size5 dmax=1 から標本で K(S) 計算。全数未。ゲーム論的判定は未実施。",
    }
    print(f"n=6 B600 candidates: {len(cand6)}", flush=True)

    results["b600_structural"] = b600_out

    if OUT.exists():
        data = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        data = {}
    data.update(results)
    data.setdefault("_meta", {})["followup_elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"merged followup into {OUT}", flush=True)


if __name__ == "__main__":
    main()
