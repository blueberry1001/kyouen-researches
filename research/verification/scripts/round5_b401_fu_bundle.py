# B522/B523/B524: minimize the 70-quad flipping family
import sys, json, time, random
from pathlib import Path
from itertools import combinations
sys.path.insert(0, str(Path(__file__).parent))
from kyouen_core import Board, board_square, det4, is_forbidden_quad

OUT = Path(__file__).resolve().parent.parent / "round5_b401_fu_bundle.json"

EIGHT = [(0,1),(0,2),(1,0),(1,3),(2,0),(2,3),(3,1),(3,2)]
N = 4

def pt_id(p, n=N):
    return p[1]*n + p[0]

def all_quads_from_8(pts8, n=N):
    ids = [pt_id(p, n) for p in pts8]
    quads = []
    for comb in combinations(ids, 4):
        coords = [(i % n, i // n) for i in comb]
        if is_forbidden_quad(coords):
            quads.append(frozenset(comb))
    return quads

def mask_of(qset):
    m = 0
    for i in qset:
        m |= (1 << i)
    return m

def solve_g_unlocked(board, unlocked_ids):
    orig_quads = board.quads[:]
    orig_by_pt = [lst[:] for lst in board.quads_by_pt]
    unlock_masks = {mask_of(q) for q in unlocked_ids}
    board.quads = [q for q in board.quads if q not in unlock_masks]
    board.quads_by_pt = [[] for _ in range(board.V)]
    for q in board.quads:
        for i in range(board.V):
            if q & (1 << i):
                board.quads_by_pt[i].append(q)
    import sys as _sys
    _sys.setrecursionlimit(100000)
    memo = {}
    def ev(occ):
        if occ in memo:
            return memo[occ]
        mv = board.legal_moves(occ)
        if not mv:
            memo[occ] = 0
            return 0
        seen = set()
        for u in mv:
            seen.add(ev(occ | (1 << u)))
        g = 0
        while g in seen:
            g += 1
        memo[occ] = g
        return g
    g = ev(0)
    board.quads = orig_quads
    board.quads_by_pt = orig_by_pt
    return g

def main():
    t0 = time.time()
    board = board_square(N)
    g_std = solve_g_unlocked(board, set())
    print(f"standard g={g_std} F={len(board.quads)}", flush=True)

    quads8 = all_quads_from_8(EIGHT, N)
    print(f"quads in 8-pt circle: {len(quads8)}", flush=True)

    g_all = solve_g_unlocked(board, set(quads8))
    print(f"unlock all 70: g={g_all}", flush=True)

    # Greedy: remove ONE quad at a time if flip preserved
    current = set(quads8)
    while True:
        removed_one = False
        for q in sorted(current, key=lambda x: sorted(x)):
            trial = current - {q}
            g = solve_g_unlocked(board, trial)
            if g != 0:
                current = trial
                removed_one = True
                break  # restart scan
        if not removed_one:
            break
        print(f"  greedy: size={len(current)}", flush=True)

    g_min = solve_g_unlocked(board, current)
    print(f"greedy minimal: size={len(current)} g={g_min}", flush=True)
    result = {
        "eight_pts": EIGHT,
        "n_quads8": len(quads8),
        "g_standard": g_std,
        "g_unlock_all": g_all,
        "greedy_min_size": len(current),
        "greedy_min_quads": sorted([sorted(list(q)) for q in current]),
        "g_greedy_min": g_min,
    }
    if current:
        all_pts = set.intersection(*[set(q) for q in current])
        result["common_points"] = sorted(all_pts)
        result["has_common_3"] = len(all_pts) >= 3
        result["has_common_1"] = len(all_pts) >= 1
        print(f"common points: {sorted(all_pts)}", flush=True)

    # Verify: is greedy-min truly minimal? (each single removal breaks flip)
    if current and g_min != 0:
        ok = True
        for q in current:
            g = solve_g_unlocked(board, current - {q})
            if g != 0:
                ok = False
                break
        result["greedy_is_minimal"] = ok
        print(f"greedy minimal check: {ok}", flush=True)

    # Random search for even smaller families (size 1..greedy_min-1)
    rng = random.Random(42)
    quads_list = list(quads8)
    best_small = None
    for sz in range(1, min(len(current), 15)):
        found = False
        trials = min(500, max(50, 500 // max(sz, 1)))
        for _ in range(trials):
            subset = frozenset(rng.sample(quads_list, sz))
            g = solve_g_unlocked(board, subset)
            if g != 0:
                best_small = {"size": sz, "quads": sorted([sorted(list(q)) for q in subset]), "g": g}
                found = True
                break
        print(f"  random size {sz}: {'FOUND' if found else 'none'} ({trials} trials)", flush=True)
        if found:
            break
    result["random_search"] = best_small

    # Brute-force size 1 and 2 only (fast)
    print("brute size 1-2...", flush=True)
    bf = {"1": 0, "2": 0}
    bf_ex = []
    for q in quads8:
        g = solve_g_unlocked(board, {q})
        if g != 0:
            bf["1"] += 1
            bf_ex.append((1, [sorted(list(q))]))
    for a, b in combinations(quads8, 2):
        g = solve_g_unlocked(board, {a, b})
        if g != 0:
            bf["2"] += 1
            if len(bf_ex) < 8:
                bf_ex.append((2, [sorted(list(a)), sorted(list(b))]))
    print(f"brute: {bf}", flush=True)
    result["brute_small"] = {"counts": bf, "examples": bf_ex[:8]}

    # Also check: what is delta_quad lower bound from B521 (pairs of ALL 194 quads)?
    # Already known: 0 flips in all 18721 pairs. So delta_quad >= 3.
    # Our question: is there a flipping family of size 3-6 from the 70?
    # Try systematic: all triples that share a common point pattern
    if g_min != 0 and len(current) > 3:
        # Try shrinking further via ILP-like: which 3-subset of greedy-min?
        print("shrink greedy-min via subsets...", flush=True)
        qlist = sorted(current, key=lambda x: sorted(x))
        found_smaller = None
        for sz in range(2, len(current)):
            for subset in combinations(qlist, sz):
                g = solve_g_unlocked(board, set(subset))
                if g != 0:
                    found_smaller = {"size": sz, "quads": sorted([sorted(list(q)) for q in subset]), "g": g}
                    break
            if found_smaller:
                break
        if found_smaller:
            result["subset_of_greedy"] = found_smaller
            print(f"found subset of greedy of size {found_smaller['size']}", flush=True)

    result["elapsed"] = time.time() - t0
    OUT.write_text(json.dumps(result, indent=2))
    print(f"done in {result['elapsed']:.1f}s", flush=True)

if __name__ == "__main__":
    main()
