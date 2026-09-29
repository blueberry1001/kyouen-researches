# B587: nimber2 -> nimber4 amplification search on n=4
# B591: near-max analysis with delta_K(7)=2
import sys, json, time
from pathlib import Path
from itertools import combinations
sys.path.insert(0, str(Path(__file__).parent))
from kyouen_core import Board, board_square

OUT = Path(__file__).resolve().parent.parent / "round5_b401_fu_amp.json"

def solve_grundy_for(board, occ_memo=None):
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
    return ev, memo

def main():
    t0 = time.time()
    n = 4
    board = board_square(n)
    ev, memo = solve_grundy_for(board)
    g0 = ev(0)
    print(f"empty g={g0}", flush=True)

    # Find all safe sets with g=2 (nimber 2 components)
    # We need sets S where g(S)=2
    g2_sets = []
    g1_sets = []
    g3_sets = []
    g4_sets = []
    g5_sets = []
    for occ in range(1 << board.V):
        if not board.is_safe(occ):
            continue
        g = ev(occ)
        if g == 2:
            g2_sets.append(occ)
        elif g == 1:
            g1_sets.append(occ)
        elif g == 3:
            g3_sets.append(occ)
        elif g == 4:
            g4_sets.append(occ)
        elif g == 5:
            g5_sets.append(occ)
    print(f"g=1: {len(g1_sets)}, g=2: {len(g2_sets)}, g=3: {len(g3_sets)}, g=4: {len(g4_sets)}, g=5: {len(g5_sets)}", flush=True)

    # B587: compose two nimber-2 components to get nimber 4
    # Try placing two disjoint g=2 sets and see the combined g
    # (combined game is not xor because of shared circle constraints)
    found_amp = []
    checked = 0
    for s1 in g2_sets[:100]:
        pts1 = [i for i in range(board.V) if s1 & (1 << i)]
        for s2 in g2_sets[:100]:
            if s2 & s1:
                continue  # must be disjoint stones
            pts2 = [i for i in range(board.V) if s2 & (1 << i)]
            combined = s1 | s2
            if not board.is_safe(combined):
                continue
            checked += 1
            g = ev(combined)
            if g >= 3:
                found_amp.append({"s1": s1, "s2": s2, "g": g,
                                   "pts1": pts1, "pts2": pts2})
                if g >= 4:
                    print(f"  AMPLIFIED g={g}: pts1={pts1} pts2={pts2}", flush=True)
            if checked >= 5000:
                break
        if checked >= 5000:
            break
    print(f"checked {checked} disjoint pairs, found {len(found_amp)} with g>=3", flush=True)

    # Max g from two g=2 components
    max_g_amp = max((a["g"] for a in found_amp), default=0)
    print(f"max g from two g=2: {max_g_amp}", flush=True)

    # B588: same component twice, different separation -> different g
    # Take a g=2 set and translate it (shift x) to get a second copy
    # On 4x4, translation is limited. Try all placements of same shape.
    # Simpler: find pairs of isomorphic g=2 sets at different distances
    # and check if combined g differs
    xor_break = []
    xor_ok = []
    for s1 in g2_sets[:80]:
        pts1 = frozenset(i for i in range(board.V) if s1 & (1 << i))
        for s2 in g2_sets[:80]:
            if s2 & s1:
                continue
            pts2 = frozenset(i for i in range(board.V) if s2 & (1 << i))
            # check isomorphism by relative shape (translation)
            if len(pts1) != len(pts2):
                continue
            # try to match by translation
            p1 = sorted(pts1)
            p2 = sorted(pts2)
            # simple check: same multiset of coordinate differences
            combined = s1 | s2
            if not board.is_safe(combined):
                continue
            g = ev(combined)
            expected_xor = 2 ^ 2  # = 0
            if g != expected_xor:
                xor_break.append({"s1": s1, "s2": s2, "g": g, "xor": expected_xor,
                                   "pts1": sorted(pts1), "pts2": sorted(pts2)})
            else:
                xor_ok.append(1)
    print(f"xor break: {len(xor_break)}, xor ok: {len(xor_ok)}", flush=True)

    # B591: near-max analysis
    # K(4)=7. Count safe sets of size 6 (one short of max) and their d_max
    K = board.max_safe_size()
    print(f"K(4)={K}", flush=True)
    size_k = []
    size_km1 = []
    for occ in range(1 << board.V):
        if not board.is_safe(occ):
            continue
        k = occ.bit_count()
        if k == K:
            size_k.append(occ)
        elif k == K - 1:
            size_km1.append(occ)
    print(f"size K={K}: {len(size_k)}, size K-1: {len(size_km1)}", flush=True)

    # d_max(S) = min Hamming distance to a max set
    def hamming(a, b):
        return (a ^ b).bit_count()

    dmax_list = []
    for s in size_km1:
        dmin = min(hamming(s, m) for m in size_k)
        dmax_list.append(dmin)
    if dmax_list:
        print(f"d_max for |S|=K-1: max={max(dmax_list)}, min={min(dmax_list)}, avg={sum(dmax_list)/len(dmax_list):.2f}", flush=True)

    result = {
        "n": n,
        "g1_count": len(g1_sets), "g2_count": len(g2_sets),
        "g3_count": len(g3_sets), "g4_count": len(g4_sets), "g5_count": len(g5_sets),
        "amp_checked": checked, "amp_found": len(found_amp),
        "amp_max_g": max_g_amp,
        "amp_examples": found_amp[:5],
        "xor_break_count": len(xor_break),
        "xor_ok_count": len(xor_ok),
        "xor_break_examples": xor_break[:5],
        "K": K,
        "n_max_sets": len(size_k),
        "n_km1": len(size_km1),
        "dmax_max": max(dmax_list) if dmax_list else None,
        "dmax_min": min(dmax_list) if dmax_list else None,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"done in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()
