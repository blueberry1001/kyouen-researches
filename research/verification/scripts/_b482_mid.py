def _empties_of(occ: int, V: int) -> list[int]:
    out = []
    em = ((1 << V) - 1) ^ occ
    i = 0
    while em:
        if em & 1:
            out.append(i)
        em >>= 1
        i += 1
    return out


def extract_features(board: Board, occ: int) -> dict:
    """Bit-optimized tri / n_comp_ge3 / b / u features."""
    V = board.V
    empty = _empties_of(occ, V)
    epos = {e: idx for idx, e in enumerate(empty)}
    ne = len(empty)
    adj = [0] * ne
    n_bridge3 = 0
    for q in board.quads:
        pc = (q & occ).bit_count()
        if pc == 2:
            em2 = q & ~occ
            a = (em2 & -em2).bit_length() - 1
            b = (em2 & (em2 - 1)).bit_length() - 1
            ia, ib = epos[a], epos[b]
            adj[ia] |= 1 << ib
            adj[ib] |= 1 << ia
        elif pc == 3:
            n_bridge3 += 1

    # triangles
    tri = 0
    for a in range(ne):
        aa = adj[a]
        x = aa
        while x:
            bb = (x & -x).bit_length() - 1
            if bb > a:
                tri += (adj[a] & adj[bb]).bit_count()
            x &= x - 1

    # components
    seen = 0
    sizes = []
    for i in range(ne):
        if (seen >> i) & 1:
            continue
        stack = [i]
        seen |= 1 << i
        sz = 0
        while stack:
            u = stack.pop()
            sz += 1
            x = adj[u]
            while x:
                v = (x & -x).bit_length() - 1
                if not (seen >> v) & 1:
                    seen |= 1 << v
                    stack.append(v)
                x &= x - 1
        sizes.append(sz)
    n_comp = len(sizes)
    n_comp_ge3 = sum(1 for s in sizes if s >= 3)

    # b stats
    qbp = board.quads_by_pt
    bs = []
    n_b1 = 0
    pts_b1 = []
    for p in empty:
        bit = 1 << p
        bp = 0
        for q in qbp[p]:
            if (q & bit) == bit and (q & occ).bit_count() == 3:
                bp += 1
        bs.append(bp)
        if bp == 1:
            n_b1 += 1
            pts_b1.append(p)
    if not bs:
        bres = dict(b_mean=0.0, b_var=0.0, b_max=0, b_frac0=1.0, n_empty=0,
                    b_var_pos=0.0, b_mean_pos=0.0, n_b1=0, n_bpos=0,
                    spread_b1=0.0, b_hist={})
    else:
        m = sum(bs) / len(bs)
        var = sum((x - m) ** 2 for x in bs) / len(bs)
        pos = [x for x in bs if x > 0]
        spread = 0.0
        if len(pts_b1) >= 2:
            coords = board.points
            tot = 0
            cnt = 0
            for i in range(len(pts_b1)):
                for j in range(i + 1, len(pts_b1)):
                    x1, y1 = coords[pts_b1[i]]
                    x2, y2 = coords[pts_b1[j]]
                    tot += max(abs(x1 - x2), abs(y1 - y2))
                    cnt += 1
            spread = tot / cnt
        bres = dict(
            b_mean=m, b_var=var, b_max=max(bs),
            b_frac0=sum(1 for x in bs if x == 0) / len(bs),
            n_empty=len(bs),
            b_var_pos=(sum((x - sum(pos) / len(pos)) ** 2 for x in pos) / len(pos)) if pos else 0.0,
            b_mean_pos=(sum(pos) / len(pos)) if pos else 0.0,
            n_b1=n_b1,
            n_bpos=len(pos),
            spread_b1=spread,
            b_hist={str(v): bs.count(v) for v in sorted(set(bs))},
        )

    # legal + u gain
    legal = []
    for p in empty:
        bit = 1 << p
        ok = True
        for q in qbp[p]:
            if (q & (occ | bit)) == q:
                ok = False
                break
        if ok:
            legal.append(p)
    if not legal:
        ures = dict(n_legal=0, u_mean=0.0, u_max=0, u_min=0, n_distinct_u=0, u_hist={})
    else:
        legal_set = set(legal)
        us = []
        for p in legal:
            bit = 1 << p
            newly = 0
            for q in qbp[p]:
                if (q & bit) != bit:
                    continue
                others = q & ~bit
                if (others & occ).bit_count() == 2:
                    miss = others & ~occ
                    if miss.bit_count() == 1:
                        qv = (miss & -miss).bit_length() - 1
                        if qv != p and qv in legal_set:
                            newly += 1
            us.append(newly)
        ures = dict(
            n_legal=len(us),
            u_mean=sum(us) / len(us),
            u_max=max(us),
            u_min=min(us),
            n_distinct_u=len(set(us)),
            u_hist={str(v): us.count(v) for v in sorted(set(us))},
        )

    return {
        "tri": tri,
        "n_comp": n_comp,
        "n_comp_ge3": n_comp_ge3,
        "n_bridge3": n_bridge3,
        "n_legal_extract": len(legal),
        **bres,
        **ures,
    }


def analyze_n(n: int, boards, recs) -> dict:
    b = boards[n]
    rows = recs[n]
    print(f"n={n}: {len(rows)} states, tree DP", flush=True)

    by_occ = {r["occ"]: r for r in rows}
    rows_sorted = sorted(rows, key=lambda r: -r["k"])
    mu = {}
    hmax = {}
    win_ratio = {}
    n_win = {}
    rand_odd = {}
    for r in rows_sorted:
        occ = r["occ"]
        L = r["L"]
        if L == 0:
            mu[occ] = 0
            hmax[occ] = 0
            win_ratio[occ] = 0.0
            n_win[occ] = 0
            rand_odd[occ] = 0.0
            continue
        mus = []
        hs = []
        wins = 0
        ro_acc = 0.0
        v = 0
        Lm = L
        while Lm:
            if Lm & 1:
                ch = occ | (1 << v)
                mus.append(mu[ch])
                hs.append(hmax[ch])
                if by_occ[ch]["g"] == 0:
                    wins += 1
                ro_acc += 1.0 - rand_odd[ch]
            Lm >>= 1
            v += 1
        mu[occ] = 1 + min(mus)
        hmax[occ] = 1 + max(hs)
        nL = r["nL"]
        n_win[occ] = wins
        win_ratio[occ] = (wins / nL) if r["g"] != 0 else 0.0
        rand_odd[occ] = ro_acc / nL

    feats = []
    for i, r in enumerate(rows):
        if i % 20000 == 0:
            print(f"  feats {i}/{len(rows)}", flush=True)
        occ = r["occ"]
        fx = extract_features(b, occ)
        feats.append({
            "occ": occ,
            "k": r["k"],
            "g": r["g"],
            "P": 1 if r["g"] == 0 else 0,
            "nL": r["nL"],
            "stab": r["stab"],
            "Rhash": r["Rhash"],
            "tri": fx["tri"],
            "n_comp": fx["n_comp"],
            "n_comp_ge3": fx["n_comp_ge3"],
            "n_bridge3": fx["n_bridge3"],
            "b_var": fx["b_var"],
            "b_var_pos": fx["b_var_pos"],
            "b_mean": fx["b_mean"],
            "b_frac0": fx["b_frac0"],
            "b_max": fx["b_max"],
            "n_b1": fx["n_b1"],
            "n_bpos": fx["n_bpos"],
            "spread_b1": fx["spread_b1"],
            "b_hist": fx["b_hist"],
            "u_mean": fx["u_mean"],
            "u_max": fx["u_max"],
            "u_min": fx["u_min"],
            "n_distinct_u": fx["n_distinct_u"],
            "u_hist": fx["u_hist"],
            "mu": mu[occ],
            "hmax": hmax[occ],
            "win_ratio": win_ratio[occ],
            "n_win": n_win[occ],
            "rand_odd": rand_odd[occ],
            "illusion": rand_odd[occ] if r["g"] == 0 else (1.0 - rand_odd[occ]),
        })
    return {"feats": feats, "mu": mu, "rand_odd": rand_odd, "by_occ": by_occ}


