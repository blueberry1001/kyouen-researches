#!/usr/bin/env python3
"""Package C — minimal determining sets for n=7 (K=14, 16 sets) and n=6 (K=11, 464 sets).

Evidence: complete enumerations (maxsafe_n7_K14.bin / maxsafe_n6_K11.bin).
No board re-enumeration. Determining-set search is subset-containment only.

Outputs:
  results/cycle8_c_determining_n7.csv
  results/cycle8_c_determining_n6.csv
  night-research/cycle8_cd_result.json   (package C section; D appends later)
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (  # noqa: E402
    NR,
    RES,
    canon,
    cell_key,
    cell_orbits,
    d4_perms,
    load_n6,
    load_n7,
    orbit_members,
    stones,
    xy,
)


def analyze_board(n: int, sets: list[int], phase_of=None) -> dict:
    v = n * n
    k = sets[0].bit_count()
    N = len(sets)
    full = (1 << N) - 1

    # bitset over set-ids for each cell
    cell_mask = [0] * v
    for i, s in enumerate(sets):
        for p in stones(s, v):
            cell_mask[p] |= 1 << i
    cell_freq = [cell_mask[p].bit_count() for p in range(v)]

    # pair co-occurrence
    pair_freq: dict[tuple[int, int], int] = {}
    pair_max = 0
    pair_argmax: list[tuple[int, int]] = []
    pair_min_positive = N + 1
    n_pairs_pos = 0
    n_pairs_unique = 0
    for a in range(v):
        if cell_mask[a] == 0:
            continue
        for b in range(a + 1, v):
            if cell_mask[b] == 0:
                continue
            c = (cell_mask[a] & cell_mask[b]).bit_count()
            if c == 0:
                continue
            pair_freq[(a, b)] = c
            n_pairs_pos += 1
            if c == 1:
                n_pairs_unique += 1
            if c > pair_max:
                pair_max = c
                pair_argmax = [(a, b)]
            elif c == pair_max:
                pair_argmax.append((a, b))
            if c < pair_min_positive:
                pair_min_positive = c

    ords = cell_orbits(n)
    okey = {p: cell_key(n, *xy(p, n)) for p in range(v)}
    perms = d4_perms(n)
    osize = {ok: len(pts) for ok, pts in orbit_members(n).items()}

    def contain_count(pts) -> int:
        m = full
        for p in pts:
            m &= cell_mask[p]
            if m == 0:
                return 0
        return m.bit_count()

    def witness_record(D: tuple[int, ...]) -> dict:
        return {
            "pts": list(D),
            "xy": [list(xy(p, n)) for p in D],
            "orbits": [list(okey[p]) for p in D],
            "contain_count": contain_count(D),
        }

    rows = []
    min_det_hist: Counter[int] = Counter()
    phase_min_det: dict[str, Counter[int]] = defaultdict(Counter)
    phase_witness_orbit_sets: dict[str, Counter] = defaultdict(Counter)
    n_by_phase: Counter[str] = Counter()

    for i, s in enumerate(sets):
        pts = stones(s, v)
        ck = canon(s, perms)
        phase = phase_of(i, s, n) if phase_of else "all"
        n_by_phase[phase] += 1

        min_det = None
        witness = None
        size_stats: dict[int, dict] = {}

        for sz in range(1, k + 1):
            hist: Counter[int] = Counter()
            example_unique = None
            found_sz = False
            for D in combinations(pts, sz):
                c = contain_count(D)
                hist[c] += 1
                if c == 1:
                    found_sz = True
                    if example_unique is None:
                        example_unique = D
                    if min_det is None:
                        min_det = sz
                        witness = D
            size_stats[sz] = {
                "n_subsets": sum(hist.values()),
                "max_contain": max(hist) if hist else 0,
                "n_unique": hist.get(1, 0),
                "hist": {str(a): b for a, b in sorted(hist.items())},
                "example_unique_xy": (
                    [list(xy(p, n)) for p in example_unique] if example_unique else None
                ),
            }
            if min_det is not None and sz >= min_det:
                break

        assert min_det is not None, f"set {i} has no determining subset (should be S itself)"
        assert witness is not None
        w = witness_record(witness)
        min_det_hist[min_det] += 1
        phase_min_det[phase][min_det] += 1
        phase_witness_orbit_sets[phase][tuple(tuple(o) for o in w["orbits"])] += 1

        row = {
            "id": i,
            "mask_hex": f"{s:0{2 * ((v + 7) // 8)}x}",
            "n": n,
            "K": k,
            "phase": phase,
            "center": int(n % 2 == 1 and (s >> (n // 2 * n + n // 2)) & 1),
            "canonical_key_hex": f"{ck:0{2 * ((v + 7) // 8)}x}",
            "min_det": min_det,
            "witness_xy": ";".join(f"{x},{y}" for x, y in w["xy"]),
            "witness_orbits": ";".join(f"{a},{b}" for a, b in w["orbits"]),
            "witness_contain": w["contain_count"],
        }
        for sz in range(1, min_det + 1):
            st = size_stats[sz]
            row[f"size{sz}_max_contain"] = st["max_contain"]
            row[f"size{sz}_n_unique"] = st["n_unique"]
            row[f"size{sz}_hist"] = json.dumps(st["hist"], separators=(",", ":"))
        row["board"] = "\n".join(
            "".join("X" if (s >> (y * n + x)) & 1 else "." for x in range(n)) for y in range(n)
        )
        rows.append(row)

    # cutoff distribution: how many sets have min_det <= t
    cutoff = {}
    for t in range(1, k + 1):
        cutoff[t] = sum(c for d, c in min_det_hist.items() if d <= t)

    result = {
        "n": n,
        "K": k,
        "n_sets": N,
        "evidence": "complete enumeration",
        "d4_orbit_count": len({r["canonical_key_hex"] for r in rows}),
        "cell_orbits": [list(o) for o in ords],
        "orbit_sizes": {f"{a},{b}": osize[(a, b)] for a, b in ords},
        "cell_freq": {
            f"{xy(p, n)[0]},{xy(p, n)[1]}": cell_freq[p] for p in range(v)
        },
        "cell_freq_by_orbit": {
            f"{a},{b}": sum(cell_freq[p] for p in range(v) if okey[p] == (a, b))
            for a, b in ords
        },
        "min_det_hist": {str(d): c for d, c in sorted(min_det_hist.items())},
        "min_det_cutoff": {str(t): cutoff[t] for t in sorted(cutoff)},
        "min_det_min": min(min_det_hist),
        "min_det_max": max(min_det_hist),
        "min_det_mean": sum(d * c for d, c in min_det_hist.items()) / N,
        "n_min_det_eq_1": min_det_hist.get(1, 0),
        "n_min_det_le_2": cutoff.get(2, 0),
        "n_min_det_le_3": cutoff.get(3, 0),
        "n_min_det_le_4": cutoff.get(4, 0),
        "n_min_det_le_5": cutoff.get(5, 0),
        "phase_min_det": {ph: {str(d): c for d, c in sorted(h.items())} for ph, h in phase_min_det.items()},
        "phase_n": dict(n_by_phase),
        "phase_witness_orbit_multiset": {
            ph: [
                {"orbits": [list(o) for o in key], "count": c}
                for key, c in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
            ]
            for ph, cnt in phase_witness_orbit_sets.items()
        },
        "pair_stats": {
            "n_positive_pairs": n_pairs_pos,
            "n_unique_pairs": n_pairs_unique,
            "pair_max_cooccur": pair_max,
            "pair_max_argmax_xy": [
                [list(xy(a, n)), list(xy(b, n))] for a, b in pair_argmax[:20]
            ],
            "pair_min_positive": pair_min_positive if n_pairs_pos else None,
        },
        "rows": rows,
    }
    return result


def phase_n7(i: int, s: int, n: int) -> str:
    center = (n // 2) * n + (n // 2)
    return "A_center" if (s >> center) & 1 else "B_nocenter"


def phase_n6(i: int, s: int, n: int) -> str:
    # even board: phase by occupancy signature of corner / mid-edge orbits
    return "all"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    # stable preferred order
    prefer = [
        "id",
        "n",
        "K",
        "phase",
        "center",
        "mask_hex",
        "canonical_key_hex",
        "min_det",
        "witness_xy",
        "witness_orbits",
        "witness_contain",
    ]
    keys = [k for k in prefer if k in keys] + [k for k in keys if k not in prefer]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    n7_sets = load_n7()
    n6_sets = load_n6()
    print("=== Package C: minimal determining sets (complete enumeration) ===")
    print(f"n=7: {len(n7_sets)} max safe sets, K=14")
    print(f"n=6: {len(n6_sets)} max safe sets, K=11")

    c7 = analyze_board(7, n7_sets, phase_of=phase_n7)
    c6 = analyze_board(6, n6_sets, phase_of=phase_n6)

    write_csv(RES / "cycle8_c_determining_n7.csv", c7["rows"])
    write_csv(RES / "cycle8_c_determining_n6.csv", c6["rows"])

    # compact stdout tables
    def det_table(tag: str, c: dict) -> None:
        print(f"\n--- {tag} min_det distribution ---")
        print(f"  sets={c['n_sets']}  D4_orbits={c['d4_orbit_count']}  "
              f"min_det in [{c['min_det_min']},{c['min_det_max']}]  mean={c['min_det_mean']:.3f}")
        hist = c["min_det_hist"]
        for d, cnt in sorted(hist.items(), key=lambda kv: int(kv[0])):
            print(f"  min_det={d}: {cnt}  (cum<= {c['min_det_cutoff'][d]})")
        print(f"  min_det=1: {c['n_min_det_eq_1']}   <=2: {c['n_min_det_le_2']}   "
              f"<=3: {c['n_min_det_le_3']}   <=4: {c['n_min_det_le_4']}   <=5: {c['n_min_det_le_5']}")
        ps = c["pair_stats"]
        print(f"  pair cooccur: max={ps['pair_max_cooccur']}  unique(freq=1) pairs={ps['n_unique_pairs']}  "
              f"positive pairs={ps['n_positive_pairs']}")
        print(f"  phase hist: {c['phase_min_det']}")
        # witness orbit summary per phase
        for ph, lst in c["phase_witness_orbit_multiset"].items():
            top = lst[:6]
            print(f"  witness-orbit patterns [{ph}] (top):")
            for item in top:
                orbs = ",".join(f"({a},{b})" for a, b in item["orbits"])
                print(f"    {item['count']:4d}  {orbs}")

    det_table("n=7", c7)
    det_table("n=6", c6)

    print("\n--- n=7 per-set witnesses ---")
    for r in c7["rows"]:
        print(f"  id={r['id']:2d} phase={r['phase']:10s} min_det={r['min_det']}  "
              f"D={r['witness_xy']}  orbits={r['witness_orbits']}  "
              f"size1_unique={r.get('size1_n_unique')} size2_unique={r.get('size2_n_unique')} "
              f"size3_unique={r.get('size3_n_unique')}")

    # A vs B comparison
    print("\n--- n=7 phase A vs B ---")
    for ph in ("A_center", "B_nocenter"):
        rows = [r for r in c7["rows"] if r["phase"] == ph]
        dets = [r["min_det"] for r in rows]
        print(f"  {ph}: n={len(rows)} min_det hist={Counter(dets)}  "
              f"all_equal={len(set(dets))==1} value={dets[0] if len(set(dets))==1 else dets}")

    payload = {
        "package": "C",
        "evidence": "complete enumeration",
        "counts": {"n7_sets": 16, "n7_K": 14, "n6_sets": 464, "n6_K": 11},
        "n7": {kk: vv for kk, vv in c7.items() if kk != "rows"},
        "n6": {kk: vv for kk, vv in c6.items() if kk != "rows"},
        "n7_rows_min_det": [
            {
                "id": r["id"],
                "phase": r["phase"],
                "min_det": r["min_det"],
                "witness_xy": r["witness_xy"],
                "witness_orbits": r["witness_orbits"],
            }
            for r in c7["rows"]
        ],
    }
    out = NR / "cycle8_cd_result.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {RES / 'cycle8_c_determining_n7.csv'}")
    print(f"Wrote {RES / 'cycle8_c_determining_n6.csv'}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
