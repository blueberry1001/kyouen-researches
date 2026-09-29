# B528/B530: addition-order flip experiments (empty -> standard)
import sys, json, time, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kyouen_core import Board, board_square, is_forbidden_quad, det4

OUT = Path(__file__).resolve().parent.parent / "round5_b401_fu_path.json"
N = 4

def get_all_quads(board):
    """Return list of quad masks (ints) for the standard board."""
    return board.quads[:]

def solve_g_with_quads(quads_list, V):
    """Build a temporary board with given quads and solve grundy(0)."""
    b = Board.__new__(Board)
    b.V = V
    b.quads = quads_list
    b.quads_by_pt = [[] for _ in range(V)]
    for q in quads_list:
        for i in range(V):
            if q & (1 << i):
                b.quads_by_pt[i].append(q)
    b.full = (1 << V) - 1
    b.points = []  # unused
    import sys as _sys
    _sys.setrecursionlimit(100000)
    memo = {}
    def ev(occ):
        if occ in memo:
            return memo[occ]
        mv = b.legal_moves(occ)
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
    return ev(0)

def quad_points(q, V):
    return [i for i in range(V) if q & (1 << i)]

def main():
    t0 = time.time()
    board = board_square(N)
    all_quads = get_all_quads(board)
    V = board.V
    print(f"V={V} F={len(all_quads)}", flush=True)

    # Empty board (no quads) and standard
    g_empty = solve_g_with_quads([], V)
    g_std = solve_g_with_quads(all_quads, V)
    print(f"g_empty={g_empty} g_std={g_std}", flush=True)

    # Classify quads by geometry: line vs circle
    # A quad is a line-quad if all 4 points are collinear
    def is_line_quad(q):
        pts = quad_points(q, V)
        coords = [(i % N, i // N) for i in pts]
        # collinear check
        (x0,y0),(x1,y1) = coords[0], coords[1]
        for (x2,y2) in coords[2:]:
            if (x1-x0)*(y2-y0) != (x2-x0)*(y1-y0):
                return False
        return True

    line_quads = [q for q in all_quads if is_line_quad(q)]
    circle_quads = [q for q in all_quads if not is_line_quad(q)]
    print(f"line_quads={len(line_quads)} circle_quads={len(circle_quads)}", flush=True)

    # Identify circle bundles (sets of quads on the same circle of >=5 points)
    # Group by the set of points that lie on a common circle
    # For simplicity: group quads that share 3 points (same circle)
    from collections import defaultdict
    # Build a map: frozenset of 3 points -> list of quads containing them
    triple_map = defaultdict(list)
    for q in all_quads:
        pts = quad_points(q, V)
        for triple in __import__('itertools').combinations(pts, 3):
            triple_map[frozenset(triple)].append(q)
    # Bundles: maximal sets of quads where any two share >=3 points
    # Simpler: for each circle of >=5 points, all C(k,4) quads
    # Find circles: sets of >=5 cocircular points
    # Use: two quads share a circle if they share 3 points
    visited = set()
    bundles = []
    for q in all_quads:
        if q in visited:
            continue
        # BFS via shared triples
        cluster = {q}
        changed = True
        while changed:
            changed = False
            for qq in list(cluster):
                pts = quad_points(qq, V)
                for triple in __import__('itertools').combinations(pts, 3):
                    for q2 in triple_map[frozenset(triple)]:
                        if q2 not in cluster:
                            cluster.add(q2)
                            changed = True
        visited |= cluster
        if len(cluster) >= 5:
            bundles.append(sorted(cluster))
    print(f"bundles (>=5 quads): {len(bundles)} sizes={[len(b) for b in bundles]}", flush=True)

    # Experiment 1: geometric order (add bundles together) vs random order
    # Count winner flips along the path
    def run_path(order):
        """Add quads one by one, count g-changes."""
        current = []
        g_prev = solve_g_with_quads([], V)
        flips = 0
        gs = [g_prev]
        for q in order:
            current.append(q)
            g = solve_g_with_quads(current, V)
            if (g == 0) != (g_prev == 0):
                flips += 1
            g_prev = g
            gs.append(g)
        return flips, gs

    # Geometric order: sort by bundle membership
    bundle_ids = {}
    for bi, b in enumerate(bundles):
        for q in b:
            bundle_ids[q] = bi
    geo_order = sorted(all_quads, key=lambda q: (bundle_ids.get(q, 999), q))
    rand_order = all_quads[:]
    rng = random.Random(42)
    rng.shuffle(rand_order)

    print("running geometric path...", flush=True)
    flips_geo, gs_geo = run_path(geo_order)
    print(f"geo flips={flips_geo}", flush=True)

    print("running random path 1...", flush=True)
    flips_r1, gs_r1 = run_path(rand_order)
    print(f"rand1 flips={flips_r1}", flush=True)

    rng2 = random.Random(123)
    rand_order2 = all_quads[:]
    rng2.shuffle(rand_order2)
    print("running random path 2...", flush=True)
    flips_r2, gs_r2 = run_path(rand_order2)
    print(f"rand2 flips={flips_r2}", flush=True)

    # Experiment 2: single addition from empty (B527 follow-up)
    # Already known: any single quad flips empty g=0 -> g=1. Verify sample.
    single_flips = 0
    for q in all_quads[:20]:
        g = solve_g_with_quads([q], V)
        if g != g_empty:
            single_flips += 1
    print(f"single-quad flips from empty: {single_flips}/20", flush=True)

    result = {
        "g_empty": g_empty, "g_std": g_std,
        "n_quads": len(all_quads), "n_line": len(line_quads), "n_circle": len(circle_quads),
        "bundles": [{"size": len(b), "quads": b} for b in bundles],
        "geo_flips": flips_geo,
        "rand_flips": [flips_r1, flips_r2],
        "gs_geo_tail": gs_geo[-10:],
        "gs_rand_tail": gs_r1[-10:],
        "single_flip_sample": single_flips,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"done in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()
