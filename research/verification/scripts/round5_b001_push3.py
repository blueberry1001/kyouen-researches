#!/usr/bin/env python3
"""Round5 B001-B100 push3: weakened forms + K_10 / s_n witness search."""
from __future__ import annotations
import json, sys, random, itertools, math
from collections import Counter, defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points, board_square, is_forbidden_quad, det4

OUT = {}

def save():
    with open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_push3.json", "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)

# ---------- B009: period check of win/lose sequence ----------
def b009_period_check():
    # F=1 (first player win), S=0
    seq = [1, 1, 1, 0, 1, 1, 0, 0, 1, 0]  # n=1..10
    periods = {}
    for p in range(1, 8):
        ok = True
        conflict = []
        for i in range(len(seq) - p):
            if seq[i] != seq[i + p]:
                ok = False
                conflict.append((i + 1, i + 1 + p, seq[i], seq[i + p]))
        periods[p] = {"consistent": ok, "conflicts": len(conflict), "first_conflicts": conflict[:4]}
    # also: would a period-p extension be unique?
    OUT["b009"] = {
        "seq_n1_10": seq,
        "period_checks": periods,
        "conclusion": "no period 1..7 fits the 10-term window; eventual non-periodicity still open",
    }

# ---------- B032: separation mechanism lemma ----------
def b0032_lemma_check():
    # From existing data:
    # n=5: all winning first moves have max_t = 9 = K_5
    # n=6: all 36 first moves have T_max = 11 = K_6
    # Lemma: if every winning first move p attains max T*({p}) = K_n,
    # then longest = all winning first moves, so shortest ⊆ longest and separation impossible.
    OUT["b032"] = {
        "lemma": "If for every winning first move p, max T*({p}) = K_n, then the longest-first-move set equals the full winning set, so it intersects every shortest set; B032 separation cannot occur.",
        "n5": {"K": 9, "all_winners_max_t_eq_K": True, "longest_covers_all": True, "separation": False},
        "n6": {"K": 11, "all_winners_max_t_eq_K": True, "longest_covers_all": True, "separation": False},
        "necessary_condition_for_separation": "There must exist winning first moves p with max T*({p}) < K_n.",
    }

# ---------- B007: parity+corners exact description of W_5 ----------
def b007_w5_description():
    # W_5 = {(x,y): (x+y) even} \\ corners
    corners = {(0, 0), (4, 0), (0, 4), (4, 4)}
    pred = {(x, y) for y in range(5) for x in range(5) if (x + y) % 2 == 0 and (x, y) not in corners}
    known = {(2, 0), (1, 1), (3, 1), (0, 2), (2, 2), (4, 2), (1, 3), (3, 3), (2, 4)}
    OUT["b007"] = {
        "predicted": sorted(map(list, pred)),
        "known": sorted(map(list, known)),
        "exact_match": pred == known,
        "error": len(pred ^ known),
    }

# ---------- K_10 / s_9 / s_10 search ----------
def forbidden_quads_n(n: int) -> list[tuple[int, int, int, int]]:
    pts = square_points(n)
    quads = []
    for ids in itertools.combinations(range(n * n), 4):
        a, b, c, d = (pts[i] for i in ids)
        if is_forbidden_quad((a, b, c, d)):
            quads.append(ids)
    return quads, pts

def build_index(n: int):
    quads, pts = forbidden_quads_n(n)
    by_pt = [[] for _ in range(n * n)]
    for q in quads:
        for i in q:
            by_pt[i].append(q)
    return pts, quads, by_pt

def is_safe(occ_set, quads):
    s = set(occ_set)
    for q in quads:
        if q[0] in s and q[1] in s and q[2] in s and q[3] in s:
            return False
    return True

def can_add(p, occ_set, quads_by_pt, occ_bits):
    bit = 1 << p
    for q in quads_by_pt[p]:
        mask = 0
        for i in q:
            mask |= 1 << i
        if (occ_bits | bit) & mask == mask:
            return False
    return True

def greedy_build(pts, quads, by_pt, n, rng, start=None):
    occ = set()
    occ_bits = 0
    if start:
        for p in start:
            occ.add(p)
            occ_bits |= 1 << p
    order = list(range(n * n))
    rng.shuffle(order)
    for p in order:
        if p not in occ and can_add(p, occ, by_pt, occ_bits):
            occ.add(p)
            occ_bits |= 1 << p
    return occ

def try_add_one(occ, by_pt, n):
    occ_bits = 0
    for p in occ:
        occ_bits |= 1 << p
    for p in range(n * n):
        if p not in occ and can_add(p, occ, by_pt, occ_bits):
            occ.add(p)
            return True
    return False

def local_search_max(pts, quads, by_pt, n, rng, iters=200):
    best = greedy_build(pts, quads, by_pt, n, rng)
    for _ in range(iters):
        cand = greedy_build(pts, quads, by_pt, n, rng)
        if len(cand) > len(best):
            best = cand
    # try to grow best by forced additions then random kicks
    for _ in range(iters):
        cur = set(best)
        while try_add_one(cur, by_pt, n):
            pass
        if len(cur) > len(best):
            best = cur
        # kick: remove 1-2 random, re-greedy
        if len(best) > 2:
            kicked = set(best)
            for _k in range(rng.randint(1, 2)):
                kicked.discard(rng.choice(list(kicked)))
            # regrow
            occ_bits = 0
            for p in kicked:
                occ_bits |= 1 << p
            order = [p for p in range(n * n) if p not in kicked]
            rng.shuffle(order)
            for p in order:
                if can_add(p, kicked, by_pt, occ_bits):
                    kicked.add(p)
                    occ_bits |= 1 << p
            if len(kicked) > len(best):
                best = kicked
    return best

def is_maximal_set(occ, by_pt, n):
    occ_bits = 0
    for p in occ:
        occ_bits |= 1 << p
    for p in range(n * n):
        if p not in occ and can_add(p, occ, by_pt, occ_bits):
            return False
    return True

def search_k_and_s(n: int, seeds=40, iters=120, seed=42):
    rng = random.Random(seed + n)
    pts, quads, by_pt = build_index(n)
    print(f"n={n}: {len(quads)} forbidden quads", flush=True)
    max_safe = set()
    min_max = None
    min_max_witness = None
    size_hist = Counter()
    maximal_sizes = Counter()
    for t in range(seeds):
        s = local_search_max(pts, quads, by_pt, n, rng, iters=iters)
        while try_add_one(s, by_pt, n):
            pass
        size_hist[len(s)] += 1
        if len(s) > len(max_safe):
            max_safe = set(s)
            print(f"  n={n} trial {t}: new max safe {len(s)}", flush=True)
        if is_maximal_set(s, by_pt, n):
            maximal_sizes[len(s)] += 1
            if min_max is None or len(s) < min_max:
                min_max = len(s)
                min_max_witness = sorted(s)
                print(f"  n={n} trial {t}: new min maximal {min_max}", flush=True)
    return {
        "n": n,
        "n_quads": len(quads),
        "max_safe_size_found": len(max_safe),
        "max_safe_witness": sorted(max_safe),
        "min_maximal_found": min_max,
        "min_maximal_witness": min_max_witness,
        "greedy_size_hist": dict(size_hist),
        "maximal_size_hist": dict(maximal_sizes),
    }

def embed_witness(src_pts, n_src, n_dst, offset=(0, 0)):
    """Map (x,y) in n_src to offset+(x,y) in n_dst; return point ids (y*n+x)."""
    out = []
    for (x, y) in src_pts:
        X, Y = x + offset[0], y + offset[1]
        if 0 <= X < n_dst and 0 <= Y < n_dst:
            out.append(Y * n_dst + X)
    return out

def try_extend_embedded(n_dst=10):
    """Take known K_9=18 (or any large safe set) and try to add points on larger board."""
    # We need an 18-stone safe set on 9x9. Construct from known K values via greedy on 9x9 first.
    pass

# ---------- B088: explicit 2n-O(1) families ----------
def b088_constructions():
    """Try algebraic constructions: parabola subsets, two-line unions, etc."""
    results = {}
    for n in range(2, 16):
        # construction A: {(x, x*x mod p)} is not good.
        # Construction: points on a line are collinear -> any 4 collinear are forbidden!
        # So a full line is NOT safe (4 collinear points are a forbidden quad).
        # Safe means no 4 concyclic AND no 4 collinear.
        # Parabola y=x^2: 4 points on parabola are concyclic iff ... the det test.
        # Actually 4 points on a parabola CAN be concyclic (circle intersects parabola in ≤4 pts,
        # so generically 4 parabola-points are NOT concyclic unless special).
        # Circle ∩ parabola: substitute y=x^2 into circle eq -> degree 4 -> ≤4 intersections.
        # So 4 parabola points ARE concyclic iff they are the full intersection of some circle.
        # Generic 4 parabola points are NOT concyclic. But some special 4-tuples are.
        # Line: any 4 collinear are forbidden.
        # So we want no 4 collinear (automatic on parabola) and no 4 concyclic.
        pts = [(x, x * x) for x in range(n)]
        safe = True
        bad = None
        for ids in itertools.combinations(range(len(pts)), 4):
            a, b, c, d = (pts[i] for i in ids)
            if is_forbidden_quad((a, b, c, d)):
                safe = False
                bad = ids
                break
        results[f"parabola_n{n}"] = {"size": n, "safe": safe, "bad": bad}
    # stronger: take every other x on parabola to avoid special circles
    results["parabola_thin"] = {}
    for n in [8, 10, 12, 16]:
        pts = [(x, x * x) for x in range(0, 2 * n, 2)]  # n points
        safe = True
        bad = None
        for ids in itertools.combinations(range(len(pts)), 4):
            a, b, c, d = (pts[i] for i in ids)
            if is_forbidden_quad((a, b, c, d)):
                safe = False
                bad = ids
                break
        results["parabola_thin"][n] = {"size": n, "safe": safe, "bad": bad}
    # two parallel lines with ≤3 per line
    results["two_lines_3"] = {}
    for n in [6, 8, 10, 12]:
        # 3 on y=0 (x=0,1,2) and 3 on y=5 (x=0,1,2) — need no 4 concyclic
        pts = [(0, 0), (1, 0), (2, 0), (0, 5), (1, 5), (2, 5)]
        # scale to board
        if n < 6:
            continue
        safe = True
        bad = None
        for ids in itertools.combinations(range(len(pts)), 4):
            a, b, c, d = (pts[i] for i in ids)
            if is_forbidden_quad((a, b, c, d)):
                safe = False
                bad = ids
                break
        results["two_lines_3"][n] = {"size": 6, "safe": safe, "bad": bad}
    OUT["b088"] = results

# ---------- B043: 180-degree pairing legality on small boards ----------
def b043_pairing_check(n: int):
    """On n×n, pair (x,y) <-> (n-1-x, n-1-y). After a move at p, is the paired point always legal?"""
    pts = square_points(n)
    board = Board(pts, f"n{n}")
    V = n * n
    total = 0
    illegal = 0
    center_illegal = 0
    examples = []
    for p in range(V):
        # play p, then try paired response
        x, y = p % n, p // n
        qx, qy = n - 1 - x, n - 1 - y
        q = qy * n + qx
        if q == p:
            # center: no pair
            center_illegal += 1
            continue
        total += 1
        if q not in board.legal_moves(1 << p):
            illegal += 1
            if len(examples) < 5:
                examples.append((p, q))
    OUT.setdefault("b043", {})[f"n{n}"] = {
        "pairs_checked": total,
        "illegal_responses": illegal,
        "center_fixed_points": center_illegal,
        "examples_illegal": examples,
    }

if __name__ == "__main__":
    print("=== B009 period check ===", flush=True)
    b009_period_check()
    print("=== B032 lemma ===", flush=True)
    b0032_lemma_check()
    print("=== B007 W5 description ===", flush=True)
    b007_w5_description()
    print("=== B088 constructions ===", flush=True)
    b088_constructions()
    print("=== B043 pairing n=4,5,6 ===", flush=True)
    for n in (4, 5, 6):
        b043_pairing_check(n)
        print(f"  n={n} done: {OUT['b043'][f'n{n}']}", flush=True)
    save()
    print("=== K/s search n=9 ===", flush=True)
    OUT["k_s_search"] = {}
    OUT["k_s_search"]["n9"] = search_k_and_s(9, seeds=30, iters=80, seed=7)
    save()
    print("=== K/s search n=10 ===", flush=True)
    OUT["k_s_search"]["n10"] = search_k_and_s(10, seeds=40, iters=100, seed=11)
    save()
    print("=== K/s search n=8 (control) ===", flush=True)
    OUT["k_s_search"]["n8"] = search_k_and_s(8, seeds=20, iters=60, seed=3)
    save()
    print("DONE", flush=True)
    print(json.dumps({k: OUT[k] for k in OUT if k != "k_s_search"}, ensure_ascii=False, indent=1)[:3000])
    print("k_s_search summary:")
    for k, v in OUT["k_s_search"].items():
        print(k, {kk: v[kk] for kk in v if "hist" not in kk})
