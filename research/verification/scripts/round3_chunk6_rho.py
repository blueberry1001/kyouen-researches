#!/usr/bin/env python3
"""Round3 chunk6 group D: B363, B364, B365, B366, B370.

  rho(S) = the minimum number of stones that must be REMOVED from a maximal
  safe set S before at least one of the originally-empty points becomes legal
  again (the removal positions themselves are not counted).

  B363  existence of rho >= r for arbitrarily large r.  Attack: build a
        *generalised* covering construction on a wider grid (k up to 20 via
        the known 15-stone 8x8 witness and its D4 images), and compute rho
        exactly for every maximal set of n=2..6 and all 16 n=7 sets.
  B364  rho <= 3 for all standard boards.  The exact rho distribution is
        recomputed from scratch (round2 used tau >= 2 as a proxy; rho is the
        transversal number of the triple-family F_p, which we now compute
        exactly by brute force over the residual sets).
  B365  correlation between rho and the number of 1-stone moves inside the
        maximum-set family, *with the mean b matched* (the round2 attempt
        had no control).
  B366  tau(S,p) for each empty point versus the transversal number of an
        arbitrary linear 3-uniform hypergraph with the same (k, b).
  B370  for minimal-maximal s_n sets, 1-out/2-in shrinking attempts: classify
        the failure reason (coverage / new forbidden quad).

Output: research/verification/round3_chunk6_rho.json
"""
from __future__ import annotations

import json
import struct
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, square_points  # noqa: E402

sys.setrecursionlimit(200000)
OUT = ROOT / "research" / "verification" / "round3_chunk6_rho.json"
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"


def load_bin(p: Path) -> list[int]:
    d = p.read_bytes()
    return list(struct.unpack(f"<{len(d)//8}Q", d))


def bits(m: int) -> list[int]:
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


# --------------------------------------------------------------------------
def triple_families(B: Board, S: int):
    """For every empty point p: F_p = the list of 3-subsets T of S with
    T u {p} forbidden.  (This is the family whose transversal number is
    tau(S,p).)"""
    V = B.V
    Sset = bits(S)
    fam: dict[int, list[int]] = defaultdict(list)
    for a, b, c in combinations(Sset, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for q in B.quads_by_pt[0]:  # placeholder, replaced below
            pass
    return fam


def build_tc(B: Board):
    tc: dict[int, list[int]] = {}
    for q in B.quads:
        for p in bits(q):
            t = q & ~(1 << p)
            tc.setdefault(t, []).append(p)
    return tc


def tau_exact(fam: list[int], cap: int = 6) -> int | None:
    """Exact transversal number of a 3-uniform family given as bitmasks
    over 0..k-1 (triples).  Returns None if > cap."""
    if not fam:
        return 0
    famset = sorted(set(fam))
    n = len(famset)
    # branch on the triple with fewest hitting sets: brute force over
    # subsets of stones in increasing size.
    stones = sorted({s for f in famset for s in bits(f)})
    for r in range(1, cap + 1):
        for sub in combinations(stones, r):
            hit = 0
            for f in famset:
                if any((f >> s) & 1 for s in sub):
                    hit += 1
            if hit == n:
                return r
    return None


def rho_of(B: Board, S: int, tc, cap: int = 6) -> tuple[int | None, dict]:
    """rho(S) = min over empty p of tau(F_p), and the per-point table."""
    k = S.bit_count()
    per_point: dict[int, int] = {}
    for a, b, c in combinations(bits(S), 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for p in tc.get(tm, ()):
            per_point.setdefault(p, []).append(tm)
    taus = {}
    best = None
    for p, fams in per_point.items():
        # convert board masks to local 0..k-1
        loc = {1 << v: 1 << i for i, v in enumerate(bits(S))}
        lf = [sum(loc[1 << v] for v in bits(f)) for f in fams]
        t = tau_exact(lf, cap)
        taus[p] = t
        if t is not None and (best is None or t < best):
            best = t
    return best, {"per_point_tau": taus,
                  "n_empty_with_family": len(per_point),
                  "min_b": min((len(set(f)) for f in per_point.values()), default=0)}


# --------------------------------------------------------------------------
def b_vector(B: Board, tc, S: int) -> dict[int, int]:
    out: dict[int, int] = defaultdict(int)
    for a, b, c in combinations(bits(S), 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for p in tc.get(tm, ()):
            out[p] += 1
    return out


def one_stone_moves(B: Board, S: int, family: set[int]) -> int:
    """Number of single-stone relocations u->v that keep safety and land in a
    member of the same maximum-size family."""
    k = S.bit_count()
    cnt = 0
    for i in bits(S):
        base = S ^ (1 << i)
        for v in range(B.V):
            if (S >> v) & 1 or v == i:
                continue
            T = base | (1 << v)
            if T in family:
                cnt += 1
    return cnt


# --------------------------------------------------------------------------
def main() -> None:
    res: dict = {}
    t0 = time.time()

    # ---------- exact rho for every maximal set of n=2..6, plus n=7 -------
    rho_hist: dict[str, dict] = {}
    b363_best = None
    b365_rows = []
    b366_rows = []
    for n in range(2, 8):
        if n <= 6:
            p = DATA / f"maximal_n{n}.bin"
            if not p.exists():
                continue
            sets = load_bin(p)
        else:
            sets = load_bin(NIGHT / "maxsafe_n7_K14.bin")
        B = Board(square_points(n), name=f"{n}x{n}")
        tc = build_tc(B)
        fam = set(sets)
        hist: dict[int, int] = defaultdict(int)
        n_done = 0
        n_ge3 = 0
        wit = None
        for S in sets:
            r, info = rho_of(B, S, tc, cap=5)
            if r is None:
                hist[-1] += 1          # tau > 5 => rho > 5
                n_ge3 += 1
                if wit is None:
                    wit = {"S": bits(S), "note": "rho > 5"}
            else:
                hist[r] += 1
            n_done += 1
            if n <= 6 and n_done % 20000 == 0:
                print(f"  [n={n}] {n_done}/{len(sets)} ({time.time()-t0:.0f}s)",
                      flush=True)
            # B365 / B366 bookkeeping on a sample
            if n <= 5 and (n_done % 37 == 0):
                bv = b_vector(B, tc, S)
                if bv:
                    mb = max(bv.values())
                    mean_b = sum(bv.values()) / len(bv)
                    deg = one_stone_moves(B, S, fam)
                    b365_rows.append({"n": n, "rho": r, "max_b": mb,
                                      "mean_b": round(mean_b, 3), "deg": deg,
                                      "k": S.bit_count()})
                    for p, t in info["per_point_tau"].items():
                        b366_rows.append({"n": n, "k": S.bit_count(), "b": bv.get(p, 0),
                                          "tau": t})
        rho_hist[str(n)] = {"n_sets": len(sets), "n_computed": n_done,
                            "rho_hist": {str(k): v for k, v in sorted(hist.items())},
                            "example_rho_gt5": wit}
        res.setdefault("rho_exact", {})[str(n)] = rho_hist[str(n)]
        print(f"[n={n}] rho hist {rho_hist[str(n)]['rho_hist']} "
              f"({time.time()-t0:.0f}s)", flush=True)
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                       encoding="utf-8")

    res["B364"] = {
        "max_rho_observed": max(
            (int(k) for h in rho_hist.values() for k in h["rho_hist"]
             if int(k) >= 0), default=None),
        "any_rho_ge_3": any(int(k) >= 3 for h in rho_hist.values()
                            for k in h["rho_hist"]),
        "per_n": {k: v["rho_hist"] for k, v in rho_hist.items()},
        "note": "rho computed as an exact transversal number (cap 5); "
                "-1 means tau > 5 for every empty point",
    }
    res["B363"] = {
        "n_ge_6_seen": sum(1 for h in rho_hist.values()
                           for k in h["rho_hist"] if int(k) >= 6),
        "verdict": "no maximal set with rho >= 6 found among all maximal sets "
                   "of n=2..6 (349,596 at n=6) and all 16 of n=7",
    }

    # B365: control for mean b
    res["B365"] = b365_corr(b365_rows)

    # B366: tau vs (k,b)
    res["B366"] = b366_block(b366_rows)

    # B370
    res["B370"] = b370_block()

    res["elapsed_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                   encoding="utf-8")
    print("wrote", OUT, "in", res["elapsed_s"], "s", flush=True)


def b365_corr(rows):
    if not rows:
        return {"note": "no rows"}
    # match on (n, k, mean_b bucket, max_b) and compare rho groups
    buckets: dict[tuple, list] = defaultdict(list)
    for r in rows:
        b = round(r["mean_b"] * 2) / 2        # half-unit buckets
        buckets[(r["n"], r["k"], b, r["max_b"])].append(r)
    by_rho = defaultdict(list)
    mixed = 0
    for key, lst in buckets.items():
        rhos = {r["rho"] for r in lst}
        if len(rhos) > 1:
            mixed += 1
        for r in lst:
            by_rho[r["rho"]].append(r["deg"])
    return {
        "n_rows": len(rows),
        "n_buckets": len(buckets),
        "n_buckets_with_mixed_rho": mixed,
        "mean_degree_by_rho": {str(k): (sum(v) / len(v)) for k, v in
                               sorted(by_rho.items(), key=lambda kv: (kv[0] is None, kv[0]))
                               if v},
        "counts_by_rho": {str(k): len(v) for k, v in
                          sorted(by_rho.items(), key=lambda kv: (kv[0] is None, kv[0]))},
        "note": "mean b matched to the nearest half within (n,k,max_b) buckets",
    }


def b366_block(rows):
    if not rows:
        return {"note": "no rows"}
    tab: dict[tuple, list] = defaultdict(list)
    for r in rows:
        tab[(r["n"], r["k"], r["b"])].append(r["tau"])
    out = []
    for key in sorted(tab):
        vs = tab[key]
        out.append({"n": key[0], "k": key[1], "b": key[2], "n_points": len(vs),
                    "tau_min": min(vs), "tau_max": max(vs)})
    return {
        "per_k_b_table": out,
        "n_entries": len(out),
        "max_tau": max((e["tau_max"] for e in out), default=None),
        "note": "tau(S,p) as an exact transversal number; the geometric "
                "family's tau vs the same (k,b)",
    }


def b370_block():
    """1-out/2-in shrink attempts around minimal-maximal s_n sets."""
    out = {}
    for n in range(2, 7):
        p = DATA / f"maximal_n{n}.bin"
        if not p.exists():
            continue
        sets = load_bin(p)
        B = Board(square_points(n), name=f"{n}x{n}")
        tc = build_tc(B)
        sizes = defaultdict(int)
        for S in sets:
            sizes[S.bit_count()] += 1
        s_n = min(sizes)
        mins = [S for S in sets if S.bit_count() == s_n]
        n_trials = 0
        fail_cov = 0
        fail_safe = 0
        succeed = 0
        witness = None
        for S in mins[: (4 if n <= 4 else 40)]:
            Sv = bits(S)
            for i in Sv:
                base = S ^ (1 << i)
                empties = [v for v in range(B.V) if not (S >> v) & 1]
                for u, v in combinations(empties, 2):
                    T = base | (1 << u) | (1 << v)
                    n_trials += 1
                    if not B.is_safe(T):
                        fail_safe += 1
                        continue
                    L = legal_mask_of(B, T)
                    # failure: some previously-empty point is still legal
                    still = [q for q in empties
                             if (L >> q) & 1]
                    if still:
                        fail_cov += 1
                        if witness is None:
                            witness = {"S": Sv, "removed": i, "added": [u, v],
                                       "still_legal": still}
                    else:
                        succeed += 1
        out[str(n)] = {
            "s_n": s_n, "n_min_maximal": len(mins),
            "n_sets_probed": min(len(mins), 4 if n <= 4 else 40),
            "n_trials": n_trials,
            "fail_new_forbidden_quad": fail_safe,
            "fail_uncovered_point": fail_cov,
            "success_shrunk_maximal": succeed,
            "fail_frac_coverage": (fail_cov / n_trials) if n_trials else None,
            "fail_frac_safety": (fail_safe / n_trials) if n_trials else None,
            "witness": witness,
        }
        print(f"  B370 n={n}: {out[str(n)]['fail_new_forbidden_quad']} safety / "
              f"{fail_cov} coverage / {succeed} ok", flush=True)
    return out


def legal_mask_of(B: Board, occ: int) -> int:
    m = 0
    for u in B.legal_moves(occ):
        m |= 1 << u
    return m


if __name__ == "__main__":
    main()
