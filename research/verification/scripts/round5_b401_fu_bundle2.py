# B522/B523/B524 follow-up: analyze minimal flipping families
import sys, json, time, random
from pathlib import Path
from itertools import combinations
sys.path.insert(0, str(Path(__file__).parent))
from kyouen_core import Board, board_square, is_forbidden_quad

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

def is_minimal_flip(board, family):
    """Check that family flips (g!=0) and every proper subset does not."""
    g = solve_g_unlocked(board, family)
    if g == 0:
        return False, "not flipping"
    for q in family:
        sub = family - {q}
        gs = solve_g_unlocked(board, sub)
        if gs != 0:
            return False, f"subset without {sorted(q)} still flips g={gs}"
    return True, "minimal"

def main():
    t0 = time.time()
    board = board_square(N)
    quads8 = all_quads_from_8(EIGHT, N)
    print(f"quads8: {len(quads8)}", flush=True)

    result = {"eight_pts": EIGHT, "n_quads8": len(quads8)}

    # Greedy one-at-a-time
    current = set(quads8)
    while True:
        removed = False
        for q in sorted(current, key=lambda x: sorted(x)):
            trial = current - {q}
            g = solve_g_unlocked(board, trial)
            if g != 0:
                current = trial
                removed = True
                break
        if not removed:
            break
        print(f"  greedy size={len(current)}", flush=True)

    g_min = solve_g_unlocked(board, current)
    print(f"greedy min: size={len(current)} g={g_min}", flush=True)
    minim, why = is_minimal_flip(board, current)
    all_pts = set.intersection(*[set(q) for q in current]) if current else set()
    result["greedy"] = {
        "size": len(current), "g": g_min,
        "quads": sorted([sorted(list(q)) for q in current]),
        "is_minimal": minim, "minimal_why": why,
        "common_points": sorted(all_pts),
        "n_common": len(all_pts),
    }
    print(f"  minimal={minim} common_pts={sorted(all_pts)}", flush=True)

    # Random search for size < greedy
    rng = random.Random(42)
    quads_list = list(quads8)
    best = None
    for sz in range(2, len(current)):
        for attempt in range(400):
            subset = frozenset(rng.sample(quads_list, sz))
            g = solve_g_unlocked(board, subset)
            if g != 0:
                minim2, why2 = is_minimal_flip(board, subset)
                pts2 = set.intersection(*[set(q) for q in subset])
                best = {
                    "size": sz, "g": g,
                    "quads": sorted([sorted(list(q)) for q in subset]),
                    "is_minimal": minim2, "minimal_why": why2,
                    "common_points": sorted(pts2), "n_common": len(pts2),
                    "attempt": attempt,
                }
                print(f"  random found size={sz} g={g} minimal={minim2} common={sorted(pts2)}", flush=True)
                break
        if best:
            break
        print(f"  random size {sz}: none", flush=True)
    result["random_best"] = best

    # If we found a minimal family with no common points, B523 is refuted (if it's truly minimal)
    # and B524 is supported.
    OUT.write_text(json.dumps(result, indent=2))
    print(f"saved. elapsed={time.time()-t0:.1f}s", flush=True)

    # Extra: try to find size 3-5 families more systematically
    # Focus on families built from "complementary" quads
    if not best or best["size"] > 4:
        print("systematic size 3-4 search (sample)...", flush=True)
        found34 = None
        for sz in (3, 4, 5):
            hits = 0
            for attempt in range(800):
                subset = frozenset(rng.sample(quads_list, sz))
                g = solve_g_unlocked(board, subset)
                if g != 0:
                    hits += 1
                    minim3, _ = is_minimal_flip(board, subset)
                    pts3 = set.intersection(*[set(q) for q in subset])
                    found34 = {
                        "size": sz, "g": g,
                        "quads": sorted([sorted(list(q)) for q in subset]),
                        "is_minimal": minim3,
                        "common_points": sorted(pts3), "n_common": len(pts3),
                    }
                    print(f"  size {sz} hit at attempt {attempt}: g={g} minimal={minim3}", flush=True)
                    break
            if found34:
                break
            print(f"  size {sz}: 0 hits in 800", flush=True)
        if found34:
            result["systematic_34"] = found34
            OUT.write_text(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
