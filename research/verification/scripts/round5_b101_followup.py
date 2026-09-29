#!/usr/bin/env python3
"""Round5 B101-B200 follow-up: settle PARTIAL/INCONCLUSIVE via weakened forms.

Jobs (n<=6 only, no n>=7 enumeration, no full p_rand):
  b106_ext  - extend ident curve c=6..8, exact min_det for n=4,5,6
  b159      - boundary-effect reach: degree profile vs distance from boundary
  b166_167  - prime certificates & covering number (more primes)
  b177      - n=4 two-point-deletion subboards: f-vector vs nimber
  b130      - n=5 (and n=4 all k) layer components vs P/N purity
  b123_125  - n=5 all max-pair deformations inside A∪B (aux-point demand)
  b157      - 2-stone bias features vs P/N (classification power)
  b169      - same residue class, different outcome (more m)
  b104      - orbit usage: min-maximal unused points n=4,5,6
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "round5_b101_followup.json"


def load_u64(path: Path) -> list[int]:
    raw = path.read_bytes()
    return list(struct.unpack(f"<{len(raw)//8}Q", raw))


_OUTCOME_CACHE = Path(__file__).resolve().parent.parent / "data" / "round5_outcomes_cache.json"


def outcomes_for(n: int) -> dict[int, int]:
    """Cached solve_outcomes for n×n (keys as str)."""
    cache = {}
    if _OUTCOME_CACHE.exists():
        cache = json.loads(_OUTCOME_CACHE.read_text(encoding="utf-8"))
    key = f"n{n}"
    if key in cache:
        return {int(k): v for k, v in cache[key].items()}
    board = Board(square_points(n))
    memo = board.solve_outcomes()
    cache[key] = {str(k): v for k, v in memo.items()}
    _OUTCOME_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return memo


def points_of(n: int, mask: int) -> list[tuple[int, int]]:
    return [(i % n, i // n) for i in range(n * n) if (mask >> i) & 1]


# ---------------------------------------------------------------------------
# B106/B107: identification curve extended
# ---------------------------------------------------------------------------
def job_b106_ext() -> dict:
    out = {}
    for n in (4, 5, 6):
        maximal = load_u64(DATA / f"maximal_n{n}.bin")
        sizes = [m.bit_count() for m in maximal]
        K = max(sizes)
        max_sets = [m for m in maximal if m.bit_count() == K]
        M = len(max_sets)
        # For each c, count max sets that have a c-subset contained in exactly one max set.
        # c=K always works. Use inverted index: for each c-subset of each set, count owners.
        curve = {}
        min_det = K  # upper bound
        # Definition (matches round3 min_det_family): a max set S is identified
        # at level c if some c-subset of S is contained in no other max set.
        for c in range(1, K + 1):
            owners = Counter()
            subsets_of = []
            for m in max_sets:
                pts = [i for i in range(n * n) if (m >> i) & 1]
                subs = []
                for comb in combinations(pts, c):
                    key = 0
                    for p in comb:
                        key |= 1 << p
                    owners[key] += 1
                    subs.append(key)
                subsets_of.append(subs)
            identified = 0
            for subs in subsets_of:
                if any(owners[k] == 1 for k in subs):
                    identified += 1
            curve[str(c)] = f"{identified}/{M}"
            if identified == M:
                min_det = c
                break
        out[f"n{n}"] = {
            "M": M,
            "K": K,
            "min_det": min_det,
            "ident_curve": curve,
            "log2_M": round(__import__("math").log2(M), 3),
            "min_det_over_log2M": round(min_det / __import__("math").log2(M), 3) if M > 1 else None,
        }
        print(f"B106 n={n}: min_det={min_det} curve={curve}")
    return out


# ---------------------------------------------------------------------------
# B159: boundary-effect reach
# ---------------------------------------------------------------------------
def job_b159() -> dict:
    """Degree of each point (number of forbidden quads through it).

    Boundary distance d = min(x, y, n-1-x, n-1-y). Profile deg by d.
    If boundary effect had fixed reach R, then d >= R would show flat degree
    (or match infinite-lattice asymptote). We measure variation up to center.
    """
    out = {}
    for n in (4, 5, 6):
        board = Board(square_points(n))
        deg = [0] * (n * n)
        for q in board.quads:
            for i in range(n * n):
                if q >> i & 1:
                    deg[i] += 1
        by_d = defaultdict(list)
        for y in range(n):
            for x in range(n):
                d = min(x, y, n - 1 - x, n - 1 - y)
                by_d[d].append(deg[y * n + x])
        profile = {}
        for d in sorted(by_d):
            vals = by_d[d]
            profile[str(d)] = {
                "count": len(vals),
                "min": min(vals),
                "max": max(vals),
                "mean": sum(vals) / len(vals),
                "range": max(vals) - min(vals),
            }
        dvals = sorted(by_d)
        center_d = max(dvals)
        # ratio center_mean / boundary_mean (d=0)
        b0 = profile["0"]["mean"]
        bc = profile[str(center_d)]["mean"]
        # variation among points at the SAME d (arithmetic fluctuation)
        same_d_range = {str(d): profile[str(d)]["range"] for d in dvals}
        out[f"n{n}"] = {
            "profile_by_boundary_dist": profile,
            "center_to_boundary_ratio": bc / b0 if b0 else None,
            "max_same_d_range": max(same_d_range.values()),
            "deg_total": sum(deg),
            "n_quads": len(board.quads),
        }
        print(f"B159 n={n}: center/boundary={bc/b0:.3f} profile={profile}")
    return out


# ---------------------------------------------------------------------------
# B166/B167: prime certificates
# ---------------------------------------------------------------------------
def max_set_quad_dets(board: Board, mask: int) -> list[int]:
    pts = [i for i in range(board.V) if (mask >> i) & 1]
    dets = []
    for ids in combinations(pts, 4):
        r = [board.rows[i] for i in ids]
        dets.append(det4(*r))
    return dets


def job_b166_167() -> dict:
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]
    out = {}
    for n in (4, 5):
        board = Board(square_points(n))
        maximal = load_u64(DATA / f"maximal_n{n}.bin")
        sizes = [m.bit_count() for m in maximal]
        K = max(sizes)
        max_sets = [m for m in maximal if m.bit_count() == K]
        # per-set certifying primes (all dets nonzero mod p)
        cert_lists = []
        all_dets = []
        for m in max_sets:
            dets = max_set_quad_dets(board, m)
            all_dets.append(dets)
            certs = []
            for p in primes:
                if all(d % p != 0 for d in dets):
                    certs.append(p)
            cert_lists.append(certs)
        # sets uncertified by any of these primes
        uncertified = sum(1 for c in cert_lists if not c)
        # prime_hits: how many sets each p certifies
        prime_hits = {str(p): sum(1 for c in cert_lists if p in c) for p in primes}
        # covering: min |P| subset of primes s.t. every det (across all sets) is
        # nonzero mod at least one p in P.  This is a hitting set:
        # each det d is "witnessed" by primes that do NOT divide d.
        # We need P hitting every det, i.e. for each det exists p in P with d % p != 0.
        # Equiv: P is NOT a subset of the prime divisors of any single det.
        # Greedy + brute for small prime pool.
        pool = primes[:12]  # 2..37
        dets_flat = [d for ds in all_dets for d in ds]
        # det is "missed by p" if d % p == 0. Cover means some p has d % p != 0.
        # So a det is uncovered by P iff every p in P divides d.
        # Find min P such that no det is divisible by all of P.
        # Equiv: for each det, P is not subset of prime_divisors(|d|) restricted to pool.
        def primes_dividing(d, pool):
            d = abs(d)
            return frozenset(p for p in pool if d % p == 0)

        div_sets = [primes_dividing(d, pool) for d in dets_flat]
        # unique patterns
        uniq = set(div_sets)
        # min P hitting: P not subset of any div_set  <=>  for each div_set S, P \ S != empty
        # i.e. P must contain at least one prime outside each S.
        # This is a hitting set on complements. Brute force |P| = 1,2,3,...
        cover_size = None
        cover_example = None
        for r in range(1, min(8, len(pool)) + 1):
            found = False
            for P in combinations(pool, r):
                PS = set(P)
                ok = True
                for S in uniq:
                    if PS <= S:
                        ok = False
                        break
                if ok:
                    cover_size = r
                    cover_example = list(P)
                    found = True
                    break
            if found:
                break
        out[f"n{n}"] = {
            "K": K,
            "n_max_sets": len(max_sets),
            "n_quads_per_set": len(all_dets[0]) if all_dets else 0,
            "prime_hits": prime_hits,
            "n_uncertified_by_pool": uncertified,
            "cover_size_in_pool12": cover_size,
            "cover_example": cover_example,
            "cert_list_sizes": dict(Counter(len(c) for c in cert_lists)),
            "max_abs_det": max(abs(d) for ds in all_dets for d in ds),
            "min_abs_det": min(abs(d) for ds in all_dets for d in ds),
        }
        print(f"B166/167 n={n}: uncert={uncertified} cover={cover_size} hits={prime_hits}")
    return out


# ---------------------------------------------------------------------------
# B177: same f-vector, different nimber on subboards
# ---------------------------------------------------------------------------
def f_vector_and_grundy(board: Board) -> tuple[tuple, int]:
    """f-vector (counts of safe sets by size) + nimber of empty position."""
    V = board.V
    # count safe sets by size via DP on bits (V <= 14 for our subboards)
    # brute over all subsets is 2^14 = 16384, fine
    f = [0] * (V + 1)
    for m in range(1 << V):
        if board.is_safe(m):
            f[m.bit_count()] += 1
    g = board.solve_grundy()[0]
    return tuple(f), g


def job_b177() -> dict:
    n = 4
    board0 = Board(square_points(n))
    pts = square_points(n)
    V = n * n
    results = []
    # 1-point deletions (16) and 2-point deletions (120)
    for r in (1, 2):
        for dels in combinations(range(V), r):
            dead = {pts[i] for i in dels}
            keep = [p for p in pts if p not in dead]
            b = Board(keep, name=f"n4-del{r}")
            fv, g = f_vector_and_grundy(b)
            results.append({
                "dels": [list(pts[i]) for i in dels],
                "r": r,
                "f": list(fv),
                "nimber": g,
                "V": b.V,
            })
    # group by f-vector
    by_f = defaultdict(list)
    for rec in results:
        by_f[tuple(rec["f"])].append(rec)
    conflicts = []
    for fv, recs in by_f.items():
        gs = set(r["nimber"] for r in recs)
        if len(gs) > 1:
            conflicts.append({
                "f": list(fv),
                "n_boards": len(recs),
                "nimbers": sorted(gs),
                "example_A": recs[0],
                "example_B": next(r for r in recs if r["nimber"] != recs[0]["nimber"]),
            })
    out = {
        "n_boards": len(results),
        "n_distinct_f": len(by_f),
        "n_conflict_f_vectors": len(conflicts),
        "conflicts": conflicts[:10],
        "nimber_hist": dict(Counter(r["nimber"] for r in results)),
    }
    print(f"B177: boards={len(results)} distinct_f={len(by_f)} conflicts={len(conflicts)}")
    return out


# ---------------------------------------------------------------------------
# B130: layer components vs P/N
# ---------------------------------------------------------------------------
def job_b130() -> dict:
    out = {}
    for n, ks in ((4, [2, 3, 4, 5, 6]), (5, [3, 4, 5])):
        board = Board(square_points(n))
        memo = outcomes_for(n)
        safe_all = load_u64(DATA / f"safe_n{n}.bin")
        for k in ks:
            level = [m for m in safe_all if m.bit_count() == k]
            if not level:
                continue
            index = {m: i for i, m in enumerate(level)}
            parent = list(range(len(level)))

            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            def union(a, b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

            for m in level:
                stones = [i for i in range(n * n) if (m >> i) & 1]
                empties = [i for i in range(n * n) if not (m >> i & 1)]
                for p in stones:
                    base = m ^ (1 << p)
                    for q in empties:
                        nb = base | (1 << q)
                        if nb in index:
                            union(index[m], index[nb])
            comps = defaultdict(list)
            for i, m in enumerate(level):
                comps[find(i)].append(m)
            mixed = 0
            pure_p = 0
            pure_n = 0
            for root, members in comps.items():
                labels = set(memo.get(m, -1) for m in members)
                # outcome: 1=WIN=N-position (player to move wins), 0=LOSS=P
                if labels == {0}:
                    pure_p += 1
                elif labels == {1}:
                    pure_n += 1
                else:
                    mixed += 1
            # does component structure determine P/N? (all pure and some of each)
            determines = (mixed == 0 and pure_p > 0 and pure_n > 0)
            out[f"n{n}_k{k}"] = {
                "n_safe_k": len(level),
                "n_components": len(comps),
                "n_mixed": mixed,
                "n_pure_P": pure_p,
                "n_pure_N": pure_n,
                "component_determines_PN": determines,
                "largest_component": max(len(v) for v in comps.values()),
            }
            print(f"B130 n={n} k={k}: comps={len(comps)} mixed={mixed} pureP={pure_p} pureN={pure_n}")
    return out


# ---------------------------------------------------------------------------
# B123-B125: aux points in A-B deformation (weak form n<=5)
# ---------------------------------------------------------------------------
def job_b123_125() -> dict:
    """For all max-set pairs on n=5 (and n=4), can A be deformed to B
    using only points of A∪B? If not, how many aux points are needed?

    Weak form REFUTED if no pair needs >=2 aux on n<=5.
    """
    out = {}
    ns = (4,) if __import__("os").environ.get("B123_N") == "4" else (4, 5)
    for n in ns:
        board = Board(square_points(n))
        maximal = load_u64(DATA / f"maximal_n{n}.bin")
        K = max(m.bit_count() for m in maximal)
        max_sets = [m for m in maximal if m.bit_count() == K]
        # Represent points as bit ids 0..V-1
        pairs_stats = Counter()
        need_aux_ge1 = 0
        need_aux_ge2 = 0
        pairs = 0
        examples = []
        for a, b in combinations(range(len(max_sets)), 2):
            A, B = max_sets[a], max_sets[b]
            pairs += 1
            U = A | B  # allowed point universe without aux
            # BFS on safe sets S with S ⊆ U, moves = add/remove one point
            # (the full safe-set complex restricted to U). If A,B are in
            # different components, aux points are required.
            from collections import deque

            def reachable(uni):
                visited = {A}
                q = deque([A])
                while q:
                    m = q.popleft()
                    if m == B:
                        return True
                    # remove one stone
                    stones = [i for i in range(n * n) if (m >> i) & 1]
                    for p in stones:
                        nb = m ^ (1 << p)
                        if nb not in visited and board.is_safe(nb):
                            visited.add(nb)
                            q.append(nb)
                    # add one empty point inside uni
                    empties = [i for i in range(n * n) if not (m >> i & 1) and (uni >> i & 1)]
                    for p in empties:
                        nb = m | (1 << p)
                        if nb not in visited and board.is_safe(nb):
                            visited.add(nb)
                            q.append(nb)
                return False

            if reachable(U):
                pairs_stats["aux0"] += 1
            else:
                need_aux_ge1 += 1
                pairs_stats["need_aux"] += 1
                if len(examples) < 5:
                    examples.append({"A": points_of(n, A), "B": points_of(n, B), "AandB": points_of(n, A & B)})
                # try with 1 aux: expand U by each single outside point
                outside = [i for i in range(n * n) if not (U >> i & 1)]
                found1 = False
                for aux in outside:
                    if reachable(U | (1 << aux)):
                        found1 = True
                        break
                if found1:
                    pairs_stats["aux1"] += 1
                else:
                    need_aux_ge2 += 1
                    pairs_stats["aux2plus"] += 1
        out[f"n{n}"] = {
            "n_max_sets": len(max_sets),
            "K": K,
            "n_pairs": pairs,
            "pairs_stats": dict(pairs_stats),
            "need_aux_ge1": need_aux_ge1,
            "need_aux_ge2": need_aux_ge2,
            "examples_need_aux": examples,
        }
        print(f"B123 n={n}: pairs={pairs} stats={dict(pairs_stats)}")
    return out


# ---------------------------------------------------------------------------
# B157: 2-stone bias features vs P/N
# ---------------------------------------------------------------------------
def job_b157() -> dict:
    n = 5
    board = Board(square_points(n))
    memo = outcomes_for(n)
    # point degrees (number of quads through the point)
    deg = [0] * (n * n)
    for q in board.quads:
        for i in range(n * n):
            if q >> i & 1:
                deg[i] += 1
    # all safe 2-stone positions
    rows = []
    for i, j in combinations(range(n * n), 2):
        m = (1 << i) | (1 << j)
        if not board.is_safe(m):
            continue
        # shared forbidden quads count: quads containing both i and j
        shared = sum(1 for q in board.quads if (q >> i & 1) and (q >> j & 1))
        outcome = memo.get(m, -1)
        # 2x2 "joint degree" proxy: deg_i, deg_j, shared
        rows.append({
            "i": i, "j": j,
            "deg_sum": deg[i] + deg[j],
            "deg_diff": abs(deg[i] - deg[j]),
            "shared": shared,
            "outcome": outcome,  # 1=N (next wins), 0=P
        })
    # classification: can deg_sum alone determine outcome? (already known no)
    # can shared alone? can deg_diff? can (deg_sum, shared)?
    def purity(key_fn):
        groups = defaultdict(lambda: [0, 0])
        for r in rows:
            groups[key_fn(r)][r["outcome"]] += 1
        # majority-vote accuracy
        correct = 0
        for k, (p, nn) in groups.items():
            correct += max(p, nn)
        return correct / len(rows), len(groups)

    acc_degsum, ng_deg = purity(lambda r: r["deg_sum"])
    acc_shared, ng_sh = purity(lambda r: r["shared"])
    acc_diff, ng_df = purity(lambda r: r["deg_diff"])
    acc_both, ng_bo = purity(lambda r: (r["deg_sum"], r["shared"]))
    acc_diffsh, ng_ds = purity(lambda r: (r["deg_diff"], r["shared"]))
    # mutual information style: does shared reduce entropy within deg_sum groups?
    out = {
        "n": n,
        "n_pairs": len(rows),
        "outcome_hist": dict(Counter(r["outcome"] for r in rows)),
        "acc_deg_sum_only": acc_degsum,
        "acc_shared_only": acc_shared,
        "acc_deg_diff_only": acc_diff,
        "acc_degsum_plus_shared": acc_both,
        "acc_diff_plus_shared": acc_diffsh,
        "n_groups": {"deg_sum": ng_deg, "shared": ng_sh, "deg_diff": ng_df,
                     "both": ng_bo, "diffsh": ng_ds},
    }
    print(f"B157: acc degsum={acc_degsum:.3f} shared={acc_shared:.3f} "
          f"diff={acc_diff:.3f} both={acc_both:.3f} diffsh={acc_diffsh:.3f}")
    return out


# ---------------------------------------------------------------------------
# B169: same residue pattern, different outcome
# ---------------------------------------------------------------------------
def job_b169() -> dict:
    out = {}
    for n in (5,):
        board = Board(square_points(n))
        memo = outcomes_for(n)
        for m_mod in (2, 3, 4, 5, 6, 7):
            groups = defaultdict(list)
            for i in range(n * n):
                x, y = i % n, i // n
                key = (x % m_mod, y % m_mod)
                g = memo.get(1 << i, -1)
                groups[key].append((i, x, y, g))
            mixed = 0
            examples = []
            for key, members in groups.items():
                gs = set(t[3] for t in members)
                if len(gs) > 1:
                    mixed += 1
                    if len(examples) < 3:
                        examples.append({
                            "class": list(key),
                            "members": [(x, y, g) for _, x, y, g in members],
                        })
            out[f"n{n}_m{m_mod}"] = {
                "n_classes": len(groups),
                "n_mixed_classes": mixed,
                "examples": examples,
                "has_witness": mixed > 0,
            }
            print(f"B169 n={n} m={m_mod}: mixed={mixed}/{len(groups)}")
    return out


# ---------------------------------------------------------------------------
# B104: orbit usage on min-maximal and max sets
# ---------------------------------------------------------------------------
def job_b104() -> dict:
    out = {}
    for n in (4, 5, 6):
        maximal = load_u64(DATA / f"maximal_n{n}.bin")
        sizes = [m.bit_count() for m in maximal]
        smin, smax = min(sizes), max(sizes)
        min_sets = [m for m in maximal if m.bit_count() == smin]
        max_sets = [m for m in maximal if m.bit_count() == smax]

        def usage(sets):
            u = [0] * (n * n)
            for m in sets:
                for i in range(n * n):
                    if m >> i & 1:
                        u[i] += 1
            return u

        def never_used(sets):
            u = usage(sets)
            return [ (i % n, i // n) for i, c in enumerate(u) if c == 0 ]

        out[f"n{n}"] = {
            "smin": smin,
            "smax": smax,
            "n_min_sets": len(min_sets),
            "n_max_sets": len(max_sets),
            "max_never_used": never_used(max_sets),
            "min_never_used": never_used(min_sets),
            "max_usage_min": min(usage(max_sets)),
            "min_usage_min": min(usage(min_sets)),
            "all_never_used": never_used(maximal),
        }
        print(f"B104 n={n}: max_unused={never_used(max_sets)} min_unused={never_used(min_sets)}")
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="*", default=["all"])
    args = ap.parse_args()
    jobs = args.jobs
    if "all" in jobs:
        jobs = ["b104", "b106_ext", "b159", "b166_167", "b169", "b157", "b130", "b177", "b123_125"]

    out = {}
    if OUT.exists():
        try:
            out = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            out = {}

    for name in jobs:
        fn = {
            "b104": job_b104,
            "b106_ext": job_b106_ext,
            "b159": job_b159,
            "b166_167": job_b166_167,
            "b169": job_b169,
            "b157": job_b157,
            "b130": job_b130,
            "b177": job_b177,
            "b123_125": job_b123_125,
        }[name]
        print(f"=== {name} ===")
        out[name] = fn()
        OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"saved {name}")

    print("DONE", list(out.keys()))


if __name__ == "__main__":
    main()
