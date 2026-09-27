#!/usr/bin/env python3
"""Round2 B361-B370: fault tolerance rho(S) for maximal safe sets.

rho(S) = min over empty p of tau(F_p), F_p = {T c S : T u {p} forbidden}.
tau = min hitting-set size of the triple family (linear by B071).
Also: per-stone essentialness (B368/B369), min-b>=2 + rho>=2 search (B362/B367).
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square  # noqa: E402

DATA = ROOT / "research" / "verification" / "data"
OUT = ROOT / "research" / "verification" / "round2_b351.json"
NR = ROOT / "night-research"


def load_u64(path: Path):
    data = path.read_bytes()
    return [struct.unpack_from("<Q", data, i)[0] for i in range(0, len(data), 8)]


def mask_ids(m: int):
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def build_triple_comp(board):
    tc = {}
    for q in board.quads:
        ids = mask_ids(q)
        for p in ids:
            t = q & ~(1 << p)
            tc.setdefault(t, []).append(p)
    return tc


def families_for_S(S, tc, V):
    """Return list of (p, family_of_triple_bitmasks) for empty p with |F_p|>0."""
    ids = mask_ids(S)
    fam = {p: [] for p in range(V) if not ((S >> p) & 1)}
    for a, b, c in combinations(ids, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for p in tc.get(tm, ()):
            if p in fam:
                fam[p].append(tm)
    return fam


def tau_of_family(triples, S_ids):
    """Min hitting set size for a 3-uniform family (as triple bitmasks)."""
    if not triples:
        return 0
    # universe = points appearing
    # tau=1?
    common = triples[0]
    for t in triples[1:]:
        common &= t
    if common:
        return 1
    # tau=2? try all pairs from union
    pts = []
    seen = 0
    for t in triples:
        seen |= t
    pts = mask_ids(seen)
    # if some point hits all but we need 2
    n = len(triples)
    # brute force size-2
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            cover = (1 << pts[i]) | (1 << pts[j])
            if all(t & cover for t in triples):
                return 2
    # size-3.. via DFS
    # since families are small (b<=~12), recursive hitting set
    def dfs(k, chosen, remaining):
        if not remaining:
            return k
        if k >= 6:
            return 99
        # pick a triple, branch on its 3 points
        t = remaining[0]
        best = 99
        for v in mask_ids(t):
            if (chosen >> v) & 1:
                continue
            new_rem = [u for u in remaining if not (u & (1 << v))]
            best = min(best, dfs(k + 1, chosen | (1 << v), new_rem))
            if best <= k + 1:
                break
        return best

    return dfs(0, 0, triples)


def analyze_rho(board, tc, masks, name, sample_limit=None):
    V = board.V
    rho_hist = Counter()
    s_min = min((m.bit_count() for m in masks), default=0)
    s_max = max((m.bit_count() for m in masks), default=0)
    # size-s_n only stats
    by_size = {}
    rho_ge2_witness = None
    rho_ge3_witness = None
    min_rho_overall = 99
    max_rho_overall = 0
    # B368/B369
    essential_fail_smin = []  # size-smin maximal with a non-essential stone
    inessential_witness = None  # B369: maximal (any size) with a stone not needed
    b367_witness = None  # min_b>=2 and some stone unlocks >=1 empty  (almost always)
    b367_unlock_frac = []  # stone unlocking >=10% of empties while min_b>=2
    # B370: for size-smin, reason a 1-remove + 2-add fails: coverage vs safety
    # (deferred: only count stones whose removal leaves some empty uncovered)
    n = 0
    for S in masks:
        k = S.bit_count()
        if sample_limit and n >= sample_limit:
            break
        n += 1
        fam = families_for_S(S, tc, V)
        # rho = min tau over empty p with family nonempty; if some empty has empty family, not maximal
        taus = {}
        for p, triples in fam.items():
            if not triples:
                taus[p] = 0
            else:
                taus[p] = tau_of_family(triples, mask_ids(S))
        if not taus:
            continue  # no empty points (full)
        rho = min(taus.values()) if taus else 99
        # actually if some p has tau=0, S is not maximal — filter
        if rho == 0:
            continue
        rho_hist[rho] += 1
        min_rho_overall = min(min_rho_overall, rho)
        max_rho_overall = max(max_rho_overall, rho)
        by_size.setdefault(k, Counter())[rho] += 1
        if rho >= 2 and rho_ge2_witness is None:
            rho_ge2_witness = {"k": k, "S": mask_ids(S), "taus_sample": dict(list(taus.items())[:8])}
        if rho >= 3 and rho_ge3_witness is None:
            rho_ge3_witness = {"k": k, "S": mask_ids(S)}
        # B368: every stone essential for some empty p
        # stone a essential iff exists empty p with all triples in F_p containing a
        # B369: exists stone a with no empty p having all triples contain a
        ids = mask_ids(S)
        essential = {a: False for a in ids}
        min_b = min((len(t) for t in fam.values()), default=0)
        unlock = {a: 0 for a in ids}
        for p, triples in fam.items():
            if not triples:
                continue
            common = triples[0]
            for t in triples[1:]:
                common &= t
            for a in mask_ids(common):
                essential[a] = True
                unlock[a] += 1
        if k == s_min:
            bad = [a for a in ids if not essential[a]]
            if bad:
                essential_fail_smin.append({"k": k, "S": mask_ids(S), "nonessential": bad})
        if inessential_witness is None:
            bad = [a for a in ids if not essential[a]]
            if bad:
                inessential_witness = {
                    "k": k,
                    "S": mask_ids(S),
                    "nonessential": bad,
                    "min_b": min_b,
                }
        if min_b >= 2:
            best_a = max(unlock, key=lambda a: unlock[a])
            n_empty = len(fam)
            frac = unlock[best_a] / n_empty if n_empty else 0
            if frac >= 0.1:
                b367_unlock_frac.append(
                    {
                        "k": k,
                        "S": mask_ids(S),
                        "stone": best_a,
                        "unlock": unlock[best_a],
                        "n_empty": n_empty,
                        "frac": round(frac, 4),
                        "min_b": min_b,
                    }
                )
            if b367_witness is None and unlock[best_a] > 0:
                b367_witness = {
                    "k": k,
                    "S": mask_ids(S),
                    "stone": best_a,
                    "unlock": unlock[best_a],
                    "n_empty": n_empty,
                    "min_b": min_b,
                }

    return {
        "board": name,
        "n_analyzed": n,
        "size_range": [s_min, s_max],
        "rho_hist": {str(k): v for k, v in sorted(rho_hist.items())},
        "min_rho": min_rho_overall,
        "max_rho": max_rho_overall,
        "rho_hist_by_size": {
            str(k): {str(r): c for r, c in sorted(hist.items())}
            for k, hist in sorted(by_size.items())
        },
        "rho_ge2_witness": rho_ge2_witness,
        "rho_ge3_witness": rho_ge3_witness,
        "b368_fails_size_smin": essential_fail_smin[:5],
        "n_b368_fails_size_smin": len(essential_fail_smin),
        "b369_inessential_witness": inessential_witness,
        "b367_minb2_witness": b367_witness,
        "b367_unlock_frac_top": sorted(b367_unlock_frac, key=lambda r: -r["frac"])[:8],
    }


def main():
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    data.setdefault("rho", {})

    for n in range(2, 6):
        b = board_square(n)
        tc = build_triple_comp(b)
        path = DATA / f"maximal_n{n}.bin"
        if not path.exists():
            # n=2..4 maximal not yet cached — derive from safe
            safe = load_u64(DATA / f"safe_n{n}.bin")
            V = b.V
            max_all = []
            for S in safe:
                fam = families_for_S(S, tc, V)
                # maximal iff every empty p has |F_p|>0
                if fam and all(len(t) > 0 for t in fam.values()):
                    max_all.append(S)
            with path.open("wb") as f:
                for m in max_all:
                    f.write(struct.pack("<Q", m))
        masks = load_u64(path)
        print(f"n={n} maximal {len(masks)}", flush=True)
        data["rho"][f"n{n}"] = analyze_rho(b, tc, masks, f"{n}x{n} maximal")

    # n=6: all 349k may be slow for tau; do k<=9 all + sample of k=10 + all k=11
    b6 = board_square(6)
    tc6 = build_triple_comp(b6)
    masks6 = load_u64(DATA / "maximal_n6.bin")
    small = [m for m in masks6 if m.bit_count() <= 9]
    k10 = [m for m in masks6 if m.bit_count() == 10]
    k11 = [m for m in masks6 if m.bit_count() == 11]
    print(f"n=6 small(k<=9) {len(small)} k10 {len(k10)} k11 {len(k11)}", flush=True)
    data["rho"]["n6_kle9"] = analyze_rho(b6, tc6, small, "6x6 maximal k<=9")
    data["rho"]["n6_k10"] = analyze_rho(b6, tc6, k10, "6x6 maximal k=10")
    data["rho"]["n6_k11"] = analyze_rho(b6, tc6, k11, "6x6 maximal k=11")

    # n=7 maxsafe 16
    b7 = board_square(7)
    tc7 = build_triple_comp(b7)
    max7 = load_u64(NR / "maxsafe_n7_K14.bin")
    data["rho"]["n7_k14"] = analyze_rho(b7, tc7, max7, "7x7 K=14")

    # n=8 witnesses
    b8 = board_square(8)
    tc8 = build_triple_comp(b8)
    s8 = [0, 1, 6, 20, 24, 32, 34, 60]
    m8 = sum(1 << i for i in s8)
    wit = json.loads((NR / "cycle6-maxsafeset-n8-15.json").read_text())
    m15 = 0
    for xy in wit["witness"]:
        m15 |= 1 << (int(xy[1]) * 8 + int(xy[0]))
    data["rho"]["n8_8stone"] = analyze_rho(b8, tc8, [m8], "8x8 8-stone")
    data["rho"]["n8_15stone"] = analyze_rho(b8, tc8, [m15], "8x8 15-stone")

    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print("rho done")


if __name__ == "__main__":
    main()
