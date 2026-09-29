#!/usr/bin/env python3
"""B520 weak: n=3 δ_K achievement sets — does W survive?"""
import sys, json
from itertools import combinations
sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
from kyouen_core import board_square, board_square_minus

def idx_to_xy(n, idx):
    return (idx % n, idx // n)

def analyze(n, deleted_idx, label):
    coords = [idx_to_xy(n, i) for i in deleted_idx]
    b = board_square_minus(n, coords)
    K = b.max_safe_size()
    outcomes = b.solve_outcomes()
    g0 = outcomes.get(0, -1)
    W = [v for v in range(b.V) if outcomes.get(1 << v, 1) == 0]
    return {"label": label, "deleted_idx": list(deleted_idx),
            "deleted_xy": coords, "V": b.V,
            "K": K, "g0": g0, "W_count": len(W), "W": W,
            "winner": "First" if g0 != 0 else "Second"}

def main():
    n = 3
    base = board_square(n)
    K0 = base.max_safe_size()
    o0 = base.solve_outcomes()
    g00 = o0.get(0, -1)
    W0 = [v for v in range(base.V) if o0.get(1 << v, 1) == 0]
    print(f"BASE n={n}: V={base.V} K={K0} g0={g00} winner={'First' if g00 else 'Second'} |W|={len(W0)} W={W0}")

    # Collinear triples by index
    lines = []
    for y in range(n):
        lines.append([y * n + x for x in range(n)])
    for x in range(n):
        lines.append([y * n + x for y in range(n)])
    lines.append([0, 4, 8])
    lines.append([2, 4, 6])
    print(f"collinear triples: {len(lines)}")

    results = []
    for ids in lines:
        r = analyze(n, ids, f"line{ids}")
        # map W back to original indices for comparison is hard (re-indexed)
        # instead compare winner and |W|
        preserved = (r["g0"] == g00)
        results.append({**r, "winner_preserved": preserved})
        print(f"  del_idx={ids} del_xy={r['deleted_xy']}: V={r['V']} K={r['K']} g0={r['g0']} |W|={r['W_count']} winner_preserved={preserved}")

    # All 3-point deletions
    all_Kdrop = []
    for combo in combinations(range(9), 3):
        r = analyze(n, combo, f"c{combo}")
        if r["K"] < K0:
            winner_pres = (r["g0"] == g00)
            all_Kdrop.append({**r, "winner_preserved": winner_pres})
    print(f"\nAll 3-point deletions that drop K below {K0}: {len(all_Kdrop)}")
    if all_Kdrop:
        wp = sum(1 for r in all_Kdrop if r["winner_preserved"])
        print(f"  winner preserved: {wp}/{len(all_Kdrop)}")
        for r in all_Kdrop[:15]:
            print(f"  del={r['deleted_xy']}: K={r['K']} g0={r['g0']} |W|={r['W_count']} preserved={r['winner_preserved']}")

    # Also: does any 3-point deletion change the winner?
    winner_changes = []
    for combo in combinations(range(9), 3):
        r = analyze(n, combo, f"c{combo}")
        if r["g0"] != g00:
            winner_changes.append(r)
    print(f"\n3-point deletions that change winner: {len(winner_changes)}")
    for r in winner_changes[:10]:
        print(f"  del={r['deleted_xy']}: g0={r['g0']} |W|={r['W_count']}")

    out = {"base": {"K": K0, "g0": g00, "W": W0},
           "line_results": results,
           "Kdrop_3pt": all_Kdrop,
           "Kdrop_count": len(all_Kdrop),
           "winner_changes": winner_changes,
           "winner_change_count": len(winner_changes)}
    with open("round5_b520_n3.json", "w") as f:
        json.dump(out, f, indent=2)
    print("saved round5_b520_n3.json")

if __name__ == "__main__":
    main()
