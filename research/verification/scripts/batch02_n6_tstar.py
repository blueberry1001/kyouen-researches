#!/usr/bin/env python3
"""n=6: lazy T*(empty) and WFT(empty) only (win-preserving paths)."""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square


def main() -> None:
    n = 6
    t0 = time.time()
    B = board_square(n)
    V = B.V
    print("quads", len(B.quads), flush=True)
    reachable = set()
    dq = deque([0])
    reachable.add(0)
    while dq:
        occ = dq.popleft()
        for u in B.legal_moves(occ):
            nxt = occ | (1 << u)
            if nxt not in reachable:
                reachable.add(nxt)
                dq.append(nxt)
    print("reachable", len(reachable), time.time() - t0, flush=True)
    L = {occ: B.legal_moves(occ) for occ in reachable}
    print("L done", time.time() - t0, flush=True)
    g: dict[int, int] = {}

    def ev(occ: int) -> int:
        if occ in g:
            return g[occ]
        mv = L[occ]
        if not mv:
            g[occ] = 0
            return 0
        seen = set()
        for u in mv:
            seen.add(ev(occ | (1 << u)))
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        return x

    ev(0)
    print("grundy done max", max(g.values()), time.time() - t0, flush=True)

    tstar: dict[int, frozenset] = {}

    def ev_t(occ: int) -> frozenset:
        if occ in tstar:
            return tstar[occ]
        mv = L[occ]
        if not mv:
            tstar[occ] = frozenset({occ.bit_count()})
            return tstar[occ]
        s: set[int] = set()
        if g[occ] == 0:
            for u in mv:
                s |= ev_t(occ | (1 << u))
        else:
            for u in mv:
                ch = occ | (1 << u)
                if g[ch] == 0:
                    s |= ev_t(ch)
        tstar[occ] = frozenset(s)
        return tstar[occ]

    ts0 = ev_t(0)
    print("T*(empty)", sorted(ts0), "visited", len(tstar), time.time() - t0, flush=True)

    wft: dict[int, frozenset] = {}

    def ev_w(occ: int) -> frozenset:
        if occ in wft:
            return wft[occ]
        mv = L[occ]
        if not mv:
            wft[occ] = frozenset({occ.bit_count()})
            return wft[occ]
        if g[occ] == 0:
            acc = None
            for u in mv:
                s = ev_w(occ | (1 << u))
                acc = s if acc is None else (acc & s)
                if not acc:
                    break
            wft[occ] = frozenset(acc or set())
        else:
            accs: set[int] = set()
            for u in mv:
                ch = occ | (1 << u)
                if g[ch] == 0:
                    accs |= ev_w(ch)
            wft[occ] = frozenset(accs)
        return wft[occ]

    wf0 = ev_w(0)
    print("WFT(empty)", sorted(wf0), "visited", len(wft), time.time() - t0, flush=True)

    fm = []
    for u in range(V):
        occ = 1 << u
        ts = sorted(ev_t(occ))
        wf = sorted(ev_w(occ))
        fm.append({
            "cell": f"({u % n},{u // n})",
            "g": g[occ],
            "Tstar": ts,
            "WFT": wf,
        })
    print("all first g", [x["g"] for x in fm])
    print("all WFT", [x["WFT"] for x in fm])
    print("all Tmin", [min(x["Tstar"]) if x["Tstar"] else None for x in fm])
    print("all Tmax", [max(x["Tstar"]) if x["Tstar"] else None for x in fm])

    out = {
        "n": 6,
        "K_n": 11,
        "empty_g": g[0],
        "Tstar_empty": sorted(ts0),
        "WFT_empty": sorted(wf0),
        "first_moves": fm,
        "tstar_visited": len(tstar),
        "wft_visited": len(wft),
        "seconds": round(time.time() - t0, 1),
    }
    Path("research/verification/scripts/batch02_n6_out.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote n6 out", flush=True)


if __name__ == "__main__":
    main()
