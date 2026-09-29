"""B333/B334/B340: multi-WFT width and first-move forced-length variation
on small rectangle boards (and n=6 sampled midgame if cheap).
"""
import sys, json, time
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import board_rect, board_square

def analyze_board(B, name, max_states=200000):
    t0 = time.time()
    g = B.solve_grundy()
    if len(g) > max_states:
        print(f"[{name}] too many states {len(g)}", flush=True)
        return {"name": name, "n_states": len(g), "skipped": True}
    occ0 = 0
    # WFT / T* recurrence (winner-preserving terminal sizes)
    # T*(S) = union over winner-preserving children of (|S|+1 + extras)
    # We compute two memo tables via recursion on increasing size (bottom-up by k).
    # States in g are all safe occ. Group by popcount.
    from collections import defaultdict
    by_k = defaultdict(list)
    for occ in g:
        by_k[occ.bit_count()].append(occ)
    Kmax = max(by_k) if by_k else 0

    # legal moves helper
    def children(occ):
        return [occ | (1 << v) for v in B.legal_moves(occ)]

    # T*: frozenset of terminal sizes (absolute stone counts)
    T = {}
    W = {}  # WFT
    # terminal positions (no legal moves): T = {k}, W = {k} if g=0 else {k}?
    # At terminal, game ends with k stones. Winner already determined by g.
    # WFT at terminal = {k} (forced, no choice).
    for k in range(Kmax, -1, -1):
        for occ in by_k.get(k, []):
            ch = children(occ)
            if not ch:
                T[occ] = frozenset({k})
                W[occ] = frozenset({k})
                continue
            # g[occ] != 0 => player to move is winner: they choose a move to g=0
            # g[occ] == 0 => player to move is loser: they must move to some child (all g!=0),
            #                 winner then plays from that child.
            if g[occ] != 0:
                # winner chooses among winning children (g==0)
                win_ch = [c for c in ch if g[c] == 0]
                if not win_ch:
                    win_ch = ch  # should not happen
                tset = set()
                wset = set()
                for c in win_ch:
                    tset |= set(T[c])
                # WFT: winner can FORCE a particular terminal length iff for every
                # loser response the eventual terminal is that length.
                # From a winning child c (P-position, loser to move):
                # WFT(c) is already the forced set from c.
                # Winner chooses c to optimize. WFT(S) = union over chosen c of WFT(c)?
                # Actually: winner picks ONE strategy (a function). The forced lengths
                # they can guarantee = intersection over their winning choices? No.
                # WFT(S) = set of t such that winner has a strategy forcing terminal t.
                # Winner picks a winning child c (and a plan from c). So
                # WFT(S) = union_{winning c} WFT(c).
                for c in win_ch:
                    wset |= set(W[c])
                T[occ] = frozenset(tset)
                W[occ] = frozenset(wset)
            else:
                # loser to move: they choose any child (all N). Winner faces each.
                # T*(S) = union over children of T(child)  (loser can pick path)
                # WFT(S) = intersection over children of WFT(child)
                #   (winner must force regardless of loser's choice)
                tset = set()
                first = True
                iset = set()
                for c in ch:
                    tset |= set(T[c])
                    if first:
                        iset = set(W[c])
                        first = False
                    else:
                        iset &= set(W[c])
                T[occ] = frozenset(tset)
                W[occ] = frozenset(iset)

    empty_T = sorted(T.get(0, []))
    empty_W = sorted(W.get(0, []))
    # multi-WFT widths
    widths = {}
    n_multi = 0
    max_w = 0
    w_hist = {}
    t3_empty_w = 0
    t3 = 0
    for occ in g:
        ws = W[occ]
        ts = T[occ]
        w = len(ws)
        w_hist[w] = w_hist.get(w, 0) + 1
        if w >= 2:
            n_multi += 1
            max_w = max(max_w, w)
        if len(ts) >= 3:
            t3 += 1
            if len(ws) == 0:
                t3_empty_w += 1

    # B340: winning first moves
    firsts = []
    for v in range(B.V):
        occ = 1 << v
        if occ not in g:
            continue
        winning = (g[occ] == 0)
        wft = sorted(W[occ])
        tstar = sorted(T[occ])
        firsts.append({"v": v, "xy": B.points[v], "g": g[occ], "winning": winning,
                       "WFT": wft, "Tstar": tstar})
    win = [f for f in firsts if f["winning"]]
    forced_vals = sorted({f["WFT"][0] for f in win if len(f["WFT"]) == 1})
    res = {
        "name": name,
        "n_states": len(g),
        "g_empty": g.get(0),
        "Tstar_empty": empty_T,
        "WFT_empty": empty_W,
        "wft_width_hist": {str(k): v for k, v in sorted(w_hist.items())},
        "n_multi_WFT": n_multi,
        "max_wft_width": max_w,
        "n_Tstar_ge3": t3,
        "n_Tstar_ge3_WFT_empty": t3_empty_w,
        "n_first": len(firsts),
        "n_winning_firsts": len(win),
        "winning_forced_vals": forced_vals,
        "forced_is_constant_among_winners": len(forced_vals) <= 1,
        "winning_firsts_sample": win[:12],
        "elapsed_s": round(time.time() - t0, 2),
    }
    print(f"[{name}] g0={res['g_empty']} T*={empty_T} WFT={empty_W} "
          f"multi={n_multi} maxW={max_w} t3={t3} t3_emptyW={t3_empty_w} "
          f"win_firsts={len(win)} forced_vals={forced_vals} "
          f"states={len(g)} {res['elapsed_s']}s", flush=True)
    return res

def main():
    out = {}
    boards = [
        (board_rect(2, 4), "2x4"),
        (board_rect(2, 5), "2x5"),
        (board_rect(3, 3), "3x3"),
        (board_rect(3, 4), "3x4"),
        (board_rect(3, 5), "3x5"),
        (board_rect(4, 4), "4x4"),
        (board_rect(2, 6), "2x6"),
        (board_rect(3, 6), "3x6"),
    ]
    for B, name in boards:
        try:
            out[name] = analyze_board(B, name)
        except Exception as e:
            print(f"[{name}] ERROR {e}", flush=True)
            out[name] = {"name": name, "error": str(e)}

    # also n=4,5 squares for cross-check (should match known)
    for n in (4, 5):
        B = board_square(n)
        out[f"n{n}"] = analyze_board(B, f"n{n}")

    path = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b325_wftrect.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote", path, flush=True)

if __name__ == "__main__":
    main()
