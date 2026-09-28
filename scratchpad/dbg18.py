"""Validate depth() and proof_size() against a plain-Python reference."""
import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *

for n in (3, 4):
    q = quad_masks(n)
    s = Solve(q, n * n)
    pn = s.pn()
    st = s.states
    K = len(s.levels) - 1
    sys.setrecursionlimit(100000)

    # reference depth
    dref = {}

    def d(occ):
        if occ in dref:
            return dref[occ]
        mv = s.legal_mask(occ)
        if mv == 0:
            dref[occ] = 0
            return 0
        best = None
        m, v = mv, 0
        while m:
            if m & 1:
                nxt = occ | (1 << v)
                d1 = 1 + d(nxt)
                if not pn[s.idx[occ]]:
                    pass
                if pn[s.idx[occ]]:
                    # winner to move: choose the P child with min length
                    if not pn[s.idx[nxt]]:
                        if best is None or d1 < best:
                            best = d1
                else:
                    if best is None or d1 > best:
                        best = d1
            m >>= 1
            v += 1
        dref[occ] = 0 if best is None else best
        return dref[occ]

    # pref for P nodes = max over children; for N nodes = 1 + max over P children
    eref = {}

    def e(occ):
        if occ in eref:
            return eref[occ]
        mv = s.legal_mask(occ)
        if mv == 0:
            eref[occ] = 0
            return 0
        best = 0
        m, v = mv, 0
        while m:
            if m & 1:
                nxt = occ | (1 << v)
                e(nxt)
                if d(nxt) + 1 > best:
                    best = d(nxt) + 1
                if not pn[s.idx[occ]] and not pn[s.idx[nxt]]:
                    pass
            m >>= 1
            v += 1
        eref[occ] = best
        return best

    def d2(occ):
        if occ in dref:
            return dref[occ]
        mv = s.legal_mask(occ)
        if mv == 0:
            dref[occ] = 0
            return 0
        vals = []
        m, v = mv, 0
        while m:
            if m & 1:
                vals.append((occ | (1 << v), pn[s.idx[occ | (1 << v)]]))
            m >>= 1
            v += 1
        r = 0
        for nxt, isn in vals:
            r = max(r, 1 + d2(nxt))
        if pn[s.idx[occ]]:
            pc = [1 + d2(nxt) for nxt, isn in vals if not isn]
            r = min(pc) if pc else 0
        dref[occ] = r
        return r

    for occ in st:
        d2(occ)
    dv = s.depth(pn)
    bad = [(st[i], int(dv[i]), dref[st[i]]) for i in range(s.N) if int(dv[i]) != dref[st[i]]]
    print(f'n={n} depth mismatches: {len(bad)}', bad[:3])

    # proof size
    pref = {}

    def psz(occ):
        if occ in pref:
            return pref[occ]
        mv = s.legal_mask(occ)
        if mv == 0:
            pref[occ] = 1
            return 1
        vals = []
        m, v = mv, 0
        while m:
            if m & 1:
                vals.append(occ | (1 << v))
            m >>= 1
            v += 1
        if pn[s.idx[occ]]:
            r = 1 + min(psz(c) for c in vals if not pn[s.idx[c]])
        else:
            r = 1 + sum(psz(c) for c in vals)
        pref[occ] = r
        return r

    for occ in st:
        psz(occ)
    pv = s.proof_size(pn)
    bad2 = [(st[i], int(pv[i]), pref[st[i]]) for i in range(s.N) if int(pv[i]) != pref[st[i]]]
    print(f'n={n} proof mismatches: {len(bad2)}', bad2[:3])
    print(f'  max depth {int(dv.max())}, max proof {int(pv.max())}')
