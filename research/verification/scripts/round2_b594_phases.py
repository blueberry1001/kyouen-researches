"""round2_b594_phases.py — n=7 A/B phase distances and path lengths.

B594: (d_A, d_B) class count for maximal 13-stone sets.
B595: one-sided vs equal-distance witnesses.
B596: G_12 / G_11 path length sample (equal vs one-sided).
B599: circle/line capacity notes on far 13-stone sets.

Loads maxsafe_n7_K14.bin and safe_n7_k{12,13}.bin.
Writes research/verification/round2_b591.json (merges key "b594_phases").
"""
from __future__ import annotations

import json
import struct
import time
from collections import Counter, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b591.json"

N = 7
V = N * N
CENTER = 3 * N + 3  # id of (3,3)


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


def xy(pid: int) -> tuple[int, int]:
    return pid % N, pid // N


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


def build_addable_index(quads, k_sets: dict[int, list[int]]):
    """For each mask in k_sets[size], precompute addable points (stay safe at size+1).

    Returns dict mask -> frozenset of addable point ids (may be empty).
    Also a reverse index from (size, mask) for BFS.
    """
    # point -> list of (other3_bitmask) such that point+other3 is forbidden
    inc: list[list[int]] = [[] for _ in range(V)]
    for a, b, c, d in quads:
        for p, others in ((a, (1 << b) | (1 << c) | (1 << d)),
                          (b, (1 << a) | (1 << c) | (1 << d)),
                          (c, (1 << a) | (1 << b) | (1 << d)),
                          (d, (1 << a) | (1 << b) | (1 << c))):
            inc[p].append(others)

    addable: dict[int, frozenset] = {}
    for size, masks in k_sets.items():
        for m in masks:
            add = []
            empty = (~m) & ((1 << V) - 1)
            for p in range(V):
                if not (empty >> p) & 1:
                    continue
                ok = True
                for others in inc[p]:
                    if m & others == others:
                        ok = False
                        break
                if ok:
                    add.append(p)
            addable[m] = frozenset(add)
    return addable, inc


def shortest_to_max_bfs(source: int, size: int, k_sets: dict[int, list[int]],
                        addable: dict, max_masks: set[int],
                        floor: int) -> int | None:
    """BFS in the 1-stone add/remove graph restricted to sizes in [floor, K].

    States are bitmasks. Returns min moves to reach any max_mask, or None.
    """
    allowed: dict[int, set[int]] = {s: set(ms) for s, ms in k_sets.items() if s >= floor}
    # index membership
    def is_allowed(sz: int, m: int) -> bool:
        return m in allowed.get(sz, ())

    if source in max_masks:
        return 0
    seen: set[tuple[int, int]] = {(size, source)}
    q: deque = deque([(size, source, 0)])
    while q:
        sz, m, dist = q.popleft()
        # removals -> sz-1
        if sz - 1 >= floor:
            mm = m
            while mm:
                p = (mm & -mm).bit_length() - 1
                mm ^= 1 << p
                child = m ^ (1 << p)
                if child in max_masks:
                    return dist + 1
                if is_allowed(sz - 1, child) and (sz - 1, child) not in seen:
                    seen.add((sz - 1, child))
                    q.append((sz - 1, child, dist + 1))
        # additions -> sz+1
        for p in addable.get(m, ()):
            child = m | (1 << p)
            if child in max_masks:
                return dist + 1
            if is_allowed(sz + 1, child) and (sz + 1, child) not in seen:
                seen.add((sz + 1, child))
                q.append((sz + 1, child, dist + 1))
    return None


def main():
    t0 = time.time()
    max7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    s13 = load_bin(DATA / "safe_n7_k13.bin")
    s12 = load_bin(DATA / "safe_n7_k12.bin")
    print(f"max7={len(max7)} s13={len(s13)} s12={len(s12)}", flush=True)

    center_bit = 1 << CENTER
    A = [m for m in max7 if m & center_bit]
    B = [m for m in max7 if not (m & center_bit)]
    print(f"A(center)={len(A)} B(nocenter)={len(B)}", flush=True)

    # d_A, d_B for every safe 13-set
    rows = []
    for s in s13:
        dA = min((s & ~m).bit_count() for m in A)
        dB = min((s & ~m).bit_count() for m in B)
        dmax = min(dA, dB)
        rows.append({"mask": s, "dA": dA, "dB": dB, "dmax": dmax})

    # maximal 13-stone = dmax >= 1
    maximal = [r for r in rows if r["dmax"] >= 1]
    extendable = [r for r in rows if r["dmax"] == 0]
    print(f"extendable(=subset of max)={len(extendable)} maximal13={len(maximal)}", flush=True)

    pair_hist = Counter((r["dA"], r["dB"]) for r in maximal)
    pair_hist_all = Counter((r["dA"], r["dB"]) for r in rows)

    # B595: one-sided (dA != dB) vs equal (dA == dB)
    one_sided = [r for r in maximal if r["dA"] != r["dB"]]
    equal = [r for r in maximal if r["dA"] == r["dB"]]
    only_A = [r for r in maximal if r["dA"] < r["dB"]]
    only_B = [r for r in maximal if r["dB"] < r["dA"]]

    # witnesses: one set with dA < dB, one with dB < dA, one with dA == dB (max d)
    def pick(lst):
        if not lst:
            return None
        r = max(lst, key=lambda x: x["dmax"])
        return {
            "mask": r["mask"],
            "pts": [i for i in range(V) if (r["mask"] >> i) & 1],
            "coords": [list(xy(i)) for i in range(V) if (r["mask"] >> i) & 1],
            "dA": r["dA"],
            "dB": r["dB"],
            "dmax": r["dmax"],
        }

    # classify phases of nearest max sets
    nearest_phase = Counter()
    for r in maximal:
        # which phase achieves the min
        a_hit = r["dA"] == r["dmax"]
        b_hit = r["dB"] == r["dmax"]
        if a_hit and b_hit:
            nearest_phase["both"] += 1
        elif a_hit:
            nearest_phase["A_only"] += 1
        else:
            nearest_phase["B_only"] += 1

    b594 = {
        "maximal_13_count": len(maximal),
        "extendable_13_count": len(extendable),
        "pair_hist_maximal": {f"{a},{b}": c for (a, b), c in sorted(pair_hist.items())},
        "pair_hist_all13": {f"{a},{b}": c for (a, b), c in sorted(pair_hist_all.items())},
        "distinct_pairs_maximal": len(pair_hist),
        "distinct_pairs_all13": len(pair_hist_all),
    }
    b595 = {
        "one_sided_count": len(one_sided),
        "equal_distance_count": len(equal),
        "closer_to_A_count": len(only_A),
        "closer_to_B_count": len(only_B),
        "nearest_phase_hist": dict(nearest_phase),
        "witness_closer_A": pick(only_A),
        "witness_closer_B": pick(only_B),
        "witness_equal": pick(equal),
    }

    # ---------- B596: path length sample ----------
    # G_12 = sizes 12,13,14; G_11 = sizes 11,12,13,14
    # We sample from equal-distance and one-sided maximal 13-sets.
    quads = forbidden_quads(N)
    k_sets_12 = {12: s12, 13: s13, 14: max7}
    print("building addable index for G_12 ...", flush=True)
    addable12, _ = build_addable_index(quads, k_sets_12)
    max_set = set(max7)

    import random
    rng = random.Random(591)
    eq_sample = rng.sample(equal, min(12, len(equal)))
    one_sample = rng.sample(one_sided, min(12, len(one_sided)))
    # also the globally farthest (max dmax)
    far_sample = sorted(maximal, key=lambda r: -r["dmax"])[:6]

    def path_stats(sample, floor, label):
        dists = []
        for r in sample:
            d = shortest_to_max_bfs(r["mask"], 13, k_sets_12, addable12, max_set, floor)
            dists.append(d)
        vals = [d for d in dists if d is not None]
        return {
            "label": label,
            "floor": floor,
            "sample_size": len(sample),
            "dists": dists,
            "dists_found": vals,
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
            "mean": (sum(vals) / len(vals)) if vals else None,
            "none_count": len(dists) - len(vals),
        }

    print("B596: BFS samples G_12 ...", flush=True)
    b596 = {
        "G12_equal": path_stats(eq_sample, 12, "equal G_12"),
        "G12_one_sided": path_stats(one_sample, 12, "one-sided G_12"),
        "G12_far": path_stats(far_sample, 12, "farthest G_12"),
    }
    # G_11 would need size-11 layer (not fully enumerated). Skip full G_11;
    # note as limited.
    b596["note"] = (
        "G_11 path lengths not computed (safe_n7_k11.bin absent, 未完全列挙). "
        "G_12 only; floor=12."
    )

    # ---------- B599: circle/line occupancy on farthest 13-sets ----------
    # For each far 13-set, compute how many forbidden quads it "almost" hits,
    # and a simple lower-bound heuristic: for each max set M, |S\\M| = d.
    # Certificate sketch: points of S scattered so every max M misses many.
    far_info = []
    for r in far_sample:
        s = r["mask"]
        # overlap profile with all 16 max sets
        overlaps = [(m & s).bit_count() for m in max7]
        # empty points addable?
        add = addable12.get(s, frozenset())
        far_info.append({
            "mask": s,
            "pts": [i for i in range(V) if (s >> i) & 1],
            "coords": [list(xy(i)) for i in range(V) if (s >> i) & 1],
            "dA": r["dA"],
            "dB": r["dB"],
            "dmax": r["dmax"],
            "overlaps_with_16_max": overlaps,
            "max_overlap": max(overlaps),
            "addable_count": len(add),
            "addable_pts": sorted(add),
        })

    # row/col occupancy of farthest
    def rowcol(mask):
        rows_c = [0] * N
        cols_c = [0] * N
        for i in range(V):
            if (mask >> i) & 1:
                x, y = xy(i)
                rows_c[y] += 1
                cols_c[x] += 1
        return rows_c, cols_c

    for info in far_info:
        rc, cc = rowcol(info["mask"])
        info["row_counts"] = rc
        info["col_counts"] = cc

    b599 = {
        "far_sets": far_info,
        "comment": (
            "dmax=8 の 13 石は全 16 最大集合との共通部分が最大 5 石。"
            "行・列占有の偏りと addable=0 を併記。"
            "円・直線容量証明の自動抽出は未実施。"
        ),
    }

    result = {
        "b594": b594,
        "b595": b595,
        "b596": b596,
        "b599": b599,
    }

    # merge into existing JSON
    if OUT.exists():
        data = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        data = {}
    data.update(result)
    data.setdefault("_meta", {})["b594_elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"merged b594-b599 into {OUT}", flush=True)
    print("pair_hist_maximal:", b594["pair_hist_maximal"], flush=True)
    print("nearest_phase:", b595["nearest_phase_hist"], flush=True)
    print("B596 G12_equal:", b596["G12_equal"]["dists_found"], flush=True)
    print("B596 G12_one_sided:", b596["G12_one_sided"]["dists_found"], flush=True)
    print("B596 G12_far:", b596["G12_far"]["dists_found"], flush=True)


if __name__ == "__main__":
    main()
