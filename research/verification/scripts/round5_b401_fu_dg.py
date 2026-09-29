# B572: max |Δg| on one-stone exchange graph (n=4)
# B507: fit Carrier-type upper bound for P_max(h)
import sys, json, time
from pathlib import Path
from fractions import Fraction
sys.path.insert(0, str(Path(__file__).parent))
from kyouen_core import Board, board_square

OUT = Path(__file__).resolve().parent.parent / "round5_b401_fu_dg.json"

def main():
    t0 = time.time()
    n = 4
    board = board_square(n)
    print(f"n={n} V={board.V}", flush=True)
    grundy = board.solve_grundy()
    print(f"grundy states: {len(grundy)}", flush=True)

    # One-stone exchange: S and T = S - {a} + {b} where a in S, b not in S
    # Both must be safe
    max_dg = 0
    max_pair = None
    dg_hist = {}
    n_pairs = 0
    n_safe = 0
    for occ, g in grundy.items():
        if occ == 0:
            continue
        pts_in = [i for i in range(board.V) if occ & (1 << i)]
        pts_out = [i for i in range(board.V) if not (occ & (1 << i))]
        for a in pts_in:
            base = occ & ~(1 << a)
            for b in pts_out:
                new_occ = base | (1 << b)
                if not board.is_safe(new_occ):
                    continue
                n_safe += 1
                g2 = grundy.get(new_occ)
                if g2 is None:
                    continue
                n_pairs += 1
                dg = abs(g - g2)
                dg_hist[dg] = dg_hist.get(dg, 0) + 1
                if dg > max_dg:
                    max_dg = dg
                    max_pair = (occ, g, new_occ, g2, a, b)
    print(f"safe exchanges: {n_safe}, scored: {n_pairs}", flush=True)
    print(f"max |Δg| = {max_dg}", flush=True)
    if max_pair:
        occ, g, new_occ, g2, a, b = max_pair
        print(f"  witness: g={g} -> g={g2}, swap {a}->{b}", flush=True)
        print(f"  S bits: {occ}, T bits: {new_occ}", flush=True)

    # Also check same-k exchanges (same number of stones)
    max_dg_samek = 0
    for occ, g in grundy.items():
        k = occ.bit_count()
        if k == 0:
            continue
        pts_in = [i for i in range(board.V) if occ & (1 << i)]
        pts_out = [i for i in range(board.V) if not (occ & (1 << i))]
        for a in pts_in:
            base = occ & ~(1 << a)
            for b in pts_out:
                new_occ = base | (1 << b)
                if not board.is_safe(new_occ):
                    continue
                g2 = grundy.get(new_occ)
                if g2 is None:
                    continue
                dg = abs(g - g2)
                if dg > max_dg_samek:
                    max_dg_samek = dg
    print(f"max |Δg| same-k = {max_dg_samek}", flush=True)

    # B507: P_max by h from existing data
    # We'll compute p_rand for n=4 by h directly
    # p_rand(S) = probability of winning under random legal play from S with player to move
    # For P positions (g=0), measure max p_rand by remaining safe moves h
    def prand(occ, memo):
        if occ in memo:
            return memo[occ]
        mv = board.legal_moves(occ)
        if not mv:
            # terminal: if g(occ)==0 the player to move lost, so win=0
            # Actually p_rand = P(player to move eventually wins)
            # Terminal: player to move cannot move => loses => p=0
            memo[occ] = Fraction(0)
            return Fraction(0)
        # p = 1 - (prod of p(children))? No.
        # Random play: uniformly random legal move. p_rand(occ) = avg over moves of (1 - p_rand(child))
        # Because if child is losing for opponent (p_rand(child)=0), we win.
        acc = Fraction(0)
        for u in mv:
            child = occ | (1 << u)
            acc += (1 - prand(child, memo))
        memo[occ] = acc / len(mv)
        return memo[occ]

    # Compute p_rand for all reachable states
    memo = {}
    pvals = []
    for occ in grundy:
        g = grundy[occ]
        p = prand(occ, memo)
        # h = max remaining safe moves (approx: |L| = number of legal moves)
        L = len(board.legal_moves(occ))
        pvals.append((occ, g, L, p))
    # P positions with g=0
    P_by_h = {}
    for occ, g, L, p in pvals:
        if g != 0:
            continue
        h = L  # using legal move count as h proxy
        if h not in P_by_h or p > P_by_h[h]:
            P_by_h[h] = p
    print("P_max by h (n=4):", flush=True)
    for h in sorted(P_by_h):
        print(f"  h={h}: {P_by_h[h]} = {float(P_by_h[h]):.4f}", flush=True)

    result = {
        "n": n,
        "max_dg": max_dg,
        "max_dg_samek": max_dg_samek,
        "dg_hist": {str(k): v for k, v in sorted(dg_hist.items())},
        "n_safe_exchanges": n_safe,
        "P_max_by_h": {str(k): str(v) for k, v in sorted(P_by_h.items())},
    }
    if max_pair:
        result["witness"] = {"g_from": max_pair[1], "g_to": max_pair[3],
                              "swap": [max_pair[4], max_pair[5]],
                              "S": max_pair[0], "T": max_pair[2]}
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"done in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()
