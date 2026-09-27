#!/usr/bin/env python3
"""B561-B566: f_S vectors, log-concavity, conditional a_S, peak/distribution.

f_S(r) = #{safe T : S subseteq T, |T| = |S|+r}
a_S(r) = f_S(r) / C(|L(S)|, r)

Claims:
  B561 all safe S have log-concave f_S
  B563 exists one-stone S with non-log-concave f_S  (competing with B561)
  B562 a_S log-concave when R(S) has only 2-point edges
  B564 failures explained by small induced residual subtypes
  B565 peak of f_S explains random-terminal length better than nimber
  B566 same f_S but different random-terminal distributions

Integer arithmetic only.  n<=5 complete f-vectors via subset-zeta over
enumerated safe sets.  No n>=7 search.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b561.json"


# ---------------------------------------------------------------------------
# enumeration
# ---------------------------------------------------------------------------
def enumerate_safe(board: Board) -> list[int]:
    """All safe bitmasks, ascending by size then lex."""
    V = board.V
    by_size: list[list[int]] = [[] for _ in range(V + 1)]

    def dfs(occ: int, start: int, size: int) -> None:
        by_size[size].append(occ)
        for v in range(start, V):
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                dfs(occ | bit, v + 1, size + 1)

    dfs(0, 0, 0)
    return by_size


def all_fvecs(board: Board, safe_by_size: list[list[int]]) -> dict[int, list[int]]:
    """f_S(r) for every safe S, via subset walk of each safe T."""
    safe_set = set()
    for g in safe_by_size:
        safe_set.update(g)
    fvec: dict[int, list[int]] = {m: [0] * (board.V + 1) for m in safe_set}
    for g in safe_by_size:
        for T in g:
            kT = T.bit_count()
            sub = T
            while True:
                fs = fvec.get(sub)
                if fs is not None:
                    fs[kT - sub.bit_count()] += 1
                if sub == 0:
                    break
                sub = (sub - 1) & T
    return fvec


def is_log_concave(f: list[int]) -> tuple[bool, int | None]:
    """Check f_k^2 >= f_{k-1} f_{k+1} on positive-support indices.
    Returns (ok, first_failing_k). Leading/trailing zeros trimmed."""
    # trim to support
    a = list(f)
    while a and a[0] == 0:
        a.pop(0)
    while a and a[-1] == 0:
        a.pop()
    if len(a) < 3:
        return True, None
    for k in range(1, len(a) - 1):
        if a[k] * a[k] < a[k - 1] * a[k + 1]:
            return False, k
    return True, None


def is_unimodal(f: list[int]) -> bool:
    a = [x for x in f if x > 0]
    if len(a) <= 1:
        return True
    peak = a.index(max(a))
    return all(a[i] <= a[i + 1] for i in range(peak)) and all(
        a[i] >= a[i + 1] for i in range(peak, len(a) - 1)
    )


def peak_index(f: list[int]) -> int | None:
    nz = [(i, x) for i, x in enumerate(f) if x > 0]
    if not nz:
        return None
    return max(nz, key=lambda t: (t[1], -t[0]))[0]


def legal_mask(board: Board, occ: int) -> int:
    out = 0
    for v in board.legal_moves(occ):
        out |= 1 << v
    return out


def residual_R(board: Board, occ: int) -> list[int]:
    empties = board.full ^ occ
    L = legal_mask(board, occ)
    seen = set()
    for q in board.quads:
        rest = q & empties
        if rest and (rest & ~L) == 0:
            seen.add(rest)
    minimal = []
    for r in seen:
        ok = True
        x = r
        while x:
            x = (x - 1) & r
            if x == 0:
                break
            if x in seen:
                ok = False
                break
        if ok:
            minimal.append(r)
    return sorted(minimal)


def residual_size_counts(R: list[int]) -> tuple[int, int, int]:
    c = [0, 0, 0, 0, 0]
    for r in R:
        c[r.bit_count()] += 1
    return c[2], c[3], c[4]


def mask_to_pts(mask: int, n: int) -> list[tuple[int, int]]:
    return [(i % n, i // n) for i in range(n * n) if (mask >> i) & 1]


# ---------------------------------------------------------------------------
# exact random-greedy terminal distribution (small |L| only)
# ---------------------------------------------------------------------------
def exact_terminal_dist(board: Board, occ: int, memo: dict[int, dict[int, float]] | None = None) -> dict[int, float]:
    if memo is None:
        memo = {}
    hit = memo.get(occ)
    if hit is not None:
        return hit
    mv = board.legal_moves(occ)
    if not mv:
        d = {occ.bit_count(): 1.0}
        memo[occ] = d
        return d
    acc: dict[int, float] = defaultdict(float)
    w = 1.0 / len(mv)
    for u in mv:
        for t, p in exact_terminal_dist(board, occ | (1 << u), memo).items():
            acc[t] += p * w
    d = dict(acc)
    memo[occ] = d
    return d


def monte_carlo_terminal(board: Board, occ: int, trials: int = 200, seed: int = 0) -> dict[int, float]:
    rng = random.Random(seed)
    counts: dict[int, int] = defaultdict(int)
    for _ in range(trials):
        o = occ
        while True:
            mv = board.legal_moves(o)
            if not mv:
                counts[o.bit_count()] += 1
                break
            o |= 1 << mv[rng.randrange(len(mv))]
    tot = sum(counts.values())
    return {t: c / tot for t, c in sorted(counts.items())}


def expected_size(dist: dict[int, float]) -> float:
    return sum(t * p for t, p in dist.items())


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    report: dict = {"note": "B561-B566 f-vectors; integer arithmetic; n<=5"}
    rng = random.Random(20260927)

    for n in (2, 3, 4, 5):
        print(f"=== n={n} ===", flush=True)
        board = board_square(n)
        t_safe = enumerate_safe(board)
        safe_set = set()
        for g in t_safe:
            safe_set.update(g)
        print(f"  safe sets: {sum(len(g) for g in t_safe)} by size={[len(g) for g in t_safe if g]}", flush=True)

        fvec = all_fvecs(board, t_safe)
        print(f"  fvecs computed: {len(fvec)}", flush=True)

        # --- B561 / B563 log-concavity of f_S ---
        failures = []
        uni_fail = 0
        one_stone = []
        for m, f in fvec.items():
            ok, fk = is_log_concave(f)
            if not is_unimodal(f):
                uni_fail += 1
            if not ok:
                rec = {
                    "mask": m,
                    "size": m.bit_count(),
                    "pts": mask_to_pts(m, n),
                    "f": f,
                    "fail_k": fk,
                }
                failures.append(rec)
            if m.bit_count() == 1:
                p = (m.bit_length() - 1) % n, (m.bit_length() - 1) // n
                ok1, fk1 = is_log_concave(f)
                one_stone.append({
                    "p": list(p),
                    "f": f,
                    "logc": ok1,
                    "fail_k": fk1,
                })

        # B561: universal over checked S
        b561_ok = len(failures) == 0
        # B563: exists one-stone failure
        b563_witness = next((x for x in one_stone if not x["logc"]), None)

        # empty-board f
        empty_f = fvec.get(0, [])

        entry = {
            "V": board.V,
            "n_quad": len(board.quads),
            "safe_by_size": [len(g) for g in t_safe],
            "n_safe": sum(len(g) for g in t_safe),
            "empty_f": empty_f,
            "empty_logc": is_log_concave(empty_f)[0],
            "n_unimodal_fail": uni_fail,
            "b561_logc_failures": failures[:20],
            "b561_n_failures": len(failures),
            "b561_all_checked_logc": b561_ok,
            "b563_one_stone": one_stone,
            "b563_witness": b563_witness,
        }

        # --- B562: a_S log-concave when R(S) all 2-point ---
        # compute R(S) for S with |S|>=1 (empty always has high-order)
        b562_sample = []
        b562_checked = 0
        b562_fail = 0
        b562_fail_ex = None
        # every S of size 0..2 plus 400 random larger
        targets = [m for m in fvec if m.bit_count() <= 2]
        larger = [m for m in fvec if m.bit_count() >= 3]
        rng.shuffle(larger)
        targets.extend(larger[: min(400, len(larger))])
        for m in targets:
            R = residual_R(board, m)
            c2, c3, c4 = residual_size_counts(R)
            if c3 + c4 > 0:
                continue
            b562_checked += 1
            L = legal_mask(board, m)
            lsz = L.bit_count()
            f = fvec[m]
            k0 = m.bit_count()
            # a_S(r) for r=0.. up to support
            a = []
            valid = True
            for r in range(0, board.V - k0 + 1):
                if f[r] == 0 and r > 0 and all(x == 0 for x in f[r:]):
                    break
                denom = math.comb(lsz, r) if r <= lsz else 0
                if denom == 0:
                    if f[r] != 0:
                        valid = False
                    break
                a.append(f[r] / denom)
            ok_a, fk_a = is_log_concave([x for x in a])  # float: use tolerance
            # re-check with integer cross-multiplication via fractions of comb
            # a_k^2 >= a_{k-1} a_{k+1}  <=>  f_k^2 * C(L,k-1)*C(L,k+1) >= f_{k-1} f_{k+1} * C(L,k)^2
            ok_int = True
            fail_k = None
            for k in range(1, len(a) - 1):
                r = k
                Ckm1 = math.comb(lsz, r - 1)
                Ck = math.comb(lsz, r)
                Ckp1 = math.comb(lsz, r + 1)
                lhs = f[r] * f[r] * Ckm1 * Ckp1
                rhs = f[r - 1] * f[r + 1] * Ck * Ck
                if lhs < rhs:
                    ok_int = False
                    fail_k = r
                    break
            if not ok_int:
                b562_fail += 1
                if b562_fail_ex is None:
                    b562_fail_ex = {
                        "pts": mask_to_pts(m, n),
                        "size": m.bit_count(),
                        "f": f[: len(a) + 1],
                        "L": lsz,
                        "fail_r": fail_k,
                        "R2_only": True,
                    }
            if b562_checked <= 8:
                b562_sample.append({
                    "size": m.bit_count(),
                    "L": lsz,
                    "c2": c2,
                    "logc_a": ok_int,
                    "f": f[: min(12, len(f))],
                })
        entry["b562"] = {
            "checked": b562_checked,
            "fail": b562_fail,
            "fail_example": b562_fail_ex,
            "sample": b562_sample,
            "all_checked_logc": b562_fail == 0,
        }

        # --- B566: same f_S, different random-terminal distributions ---
        # group by f-vector, look for pairs with different E[terminal] or dist
        by_f: dict[tuple, list[int]] = defaultdict(list)
        for m, f in fvec.items():
            key = tuple(x for x in f if x > 0 or True)
            # compress trailing zeros
            ff = list(f)
            while ff and ff[-1] == 0:
                ff.pop()
            by_f[tuple(ff)].append(m)
        b566_witness = None
        b566_pairs_same = 0
        # pick groups with 2+ members, sample some
        multi = [g for g in by_f.values() if len(g) >= 2]
        print(f"  f-vector classes with >=2 S: {len(multi)}", flush=True)
        rng.shuffle(multi)
        checked_pairs = 0
        for group in multi[: 80 if n >= 4 else 200]:
            if b566_witness is not None:
                break
            for i in range(min(3, len(group) - 1)):
                S, T = group[i], group[i + 1]
                # terminal distributions (exact if |L| small else MC)
                LS = legal_mask(board, S).bit_count()
                LT = legal_mask(board, T).bit_count()
                if LS <= 12 and LT <= 12:
                    dS = exact_terminal_dist(board, S)
                    dT = exact_terminal_dist(board, T)
                    method = "exact"
                else:
                    dS = monte_carlo_terminal(board, S, trials=150, seed=1)
                    dT = monte_carlo_terminal(board, T, trials=150, seed=2)
                    method = "mc"
                checked_pairs += 1
                eS, eT = expected_size(dS), expected_size(dT)
                # different if expected differs by > 0.02 or support differs
                if abs(eS - eT) > 0.02 or set(dS) != set(dT):
                    b566_witness = {
                        "n": n,
                        "S_pts": mask_to_pts(S, n),
                        "T_pts": mask_to_pts(T, n),
                        "f_shared": list(next(k for k, g in by_f.items() if S in g)),
                        "ES": eS,
                        "ET": eT,
                        "distS": dS,
                        "distT": dT,
                        "method": method,
                    }
                    break
        entry["b566"] = {
            "pairs_checked": checked_pairs,
            "witness": b566_witness,
        }

        # --- B565: peak of f_S vs random terminal vs nimber ---
        # sample 120 S with 4<=|L|<=10, compute peak, E[term], g
        sample = [m for m in fvec if 4 <= legal_mask(board, m).bit_count() <= 10]
        rng.shuffle(sample)
        sample = sample[: min(120, len(sample))]
        rows = []
        gcache: dict[int, int] = {}

        def grundy(occ: int) -> int:
            if occ in gcache:
                return gcache[occ]
            mv = board.legal_moves(occ)
            if not mv:
                gcache[occ] = 0
                return 0
            seen = set()
            for u in mv:
                seen.add(grundy(occ | (1 << u)))
            g = 0
            while g in seen:
                g += 1
            gcache[occ] = g
            return g

        for m in sample:
            f = fvec[m]
            L = legal_mask(board, m)
            lsz = L.bit_count()
            if lsz <= 10:
                dist = exact_terminal_dist(board, m)
            else:
                dist = monte_carlo_terminal(board, m, trials=80, seed=3)
            rows.append({
                "size": m.bit_count(),
                "L": lsz,
                "peak": peak_index(f),
                "g": grundy(m),
                "Eterm": expected_size(dist),
                "h_proxy": max(dist) - m.bit_count() if dist else 0,
            })
        # rank correlations (Spearman) peak vs Eterm, g vs Eterm
        def spearman(xs: list[float], ys: list[float]) -> float:
            def rank(v):
                order = sorted(range(len(v)), key=lambda i: v[i])
                r = [0] * len(v)
                for i, idx in enumerate(order):
                    r[idx] = i
                return r
            if len(xs) < 3:
                return 0.0
            rx, ry = rank(xs), rank(ys)
            mx = sum(rx) / len(rx)
            my = sum(ry) / len(ry)
            num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
            denx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(len(rx))))
            deny = math.sqrt(sum((ry[i] - my) ** 2 for i in range(len(ry))))
            return num / (denx * deny) if denx * deny else 0.0

        peaks = [r["peak"] if r["peak"] is not None else 0 for r in rows]
        eterm = [r["Eterm"] for r in rows]
        gs = [r["g"] for r in rows]
        entry["b565"] = {
            "n_rows": len(rows),
            "spearman_peak_Eterm": spearman(peaks, eterm),
            "spearman_g_Eterm": spearman(gs, eterm),
            "spearman_peak_g": spearman(peaks, gs),
            "note": "peak=argmax_r f_S(r); Eterm=E random-greedy terminal |S|",
            "rows_sample": rows[:12],
        }

        # --- B564: if failures, extract minimal witness structure ---
        b564 = {"n_failures": len(failures), "analysis": []}
        for rec in failures[:8]:
            m = rec["mask"]
            R = residual_R(board, m)
            c2, c3, c4 = residual_size_counts(R)
            L = legal_mask(board, m)
            # induced residual on small subsets of L: find min |U| subset of L
            # such that f of S on U is already non-log-concave (as extension count
            # restricted to U).  Use residual only.
            pts_l = [i for i in range(board.V) if (L >> i) & 1]
            min_u = None
            # try subsets of L of size 3..min(8,|L|) that already break logc
            # of the restricted independent-set counts
            for usz in range(3, min(9, len(pts_l) + 1)):
                found = False
                for combo in combinations(pts_l, usz):
                    umask = 0
                    for i in combo:
                        umask |= 1 << i
                    # residuals contained in umask
                    Ru = [r for r in R if (r & ~umask) == 0]
                    # count independent sets of each size on umask
                    ulist = list(combo)
                    maxs = 0
                    counts = [0] * (usz + 1)

                    def dfs_ind(occ_u: int, idx: int, sz: int) -> None:
                        counts[sz] += 1
                        for j in range(idx, len(ulist)):
                            bit = 1 << ulist[j]
                            ok = True
                            for r in Ru:
                                if (r & (occ_u | bit)) == r:
                                    ok = False
                                    break
                            if ok:
                                dfs_ind(occ_u | bit, j + 1, sz + 1)

                    dfs_ind(0, 0, 0)
                    oku, _ = is_log_concave(counts)
                    if not oku:
                        min_u = {
                            "U_pts": [mask_to_pts(1 << i, n)[0] for i in combo],
                            "R_U_sizes": [r.bit_count() for r in Ru],
                            "R_U_pts": [mask_to_pts(r, n) for r in Ru],
                            "counts_U": counts,
                        }
                        found = True
                        break
                if found:
                    break
            b564["analysis"].append({
                "S_pts": rec["pts"],
                "fail_k": rec["fail_k"],
                "R_sizes": (c2, c3, c4),
                "minimal_U": min_u,
            })
        entry["b564"] = b564

        report[f"n{n}"] = entry
        print(
            f"  B561 fails={len(failures)} B563 witness={b563_witness is not None} "
            f"B562 checked={b562_checked} fail={b562_fail} "
            f"B566 pairs={checked_pairs} witness={b566_witness is not None}",
            flush=True,
        )

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
