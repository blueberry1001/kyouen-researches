#!/usr/bin/env python3
"""Round2 B411-B420 follow-up: linear-extension count, B418 non-trivial corner reuse."""
from __future__ import annotations

import json
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
RES = ROOT / "results"
OUT = ROOT / "research/verification/round2_b411.json"

CORNER = 48


def main():
    data = json.loads((OUT).read_text())
    cd = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    closed = set(cd["closed_set"])
    A, B = cd["reachable_14_sets"]

    # adjacency as lists of ints
    clist = sorted(closed)
    idx = {s: i for i, s in enumerate(clist)}
    adj = [[] for _ in clist]
    for s in clist:
        si = idx[s]
        for i in range(49):
            t = s ^ (1 << i)
            if t in idx:
                adj[si].append(idx[t])

    # ---- B412: number of linear extensions of the common poset ----
    paths = data["paths"]
    events = [tuple(e) for e in data["B412"]["events"]]  # 14
    # common order pairs
    first = True
    common = set()
    for p in paths:
        ev = [tuple(e) for e in p["ops"]]
        pos = {e: k for k, e in enumerate(ev)}
        pairs = set()
        for a, b in combinations(events, 2):
            pairs.add((a, b) if pos[a] < pos[b] else (b, a))
        common = pairs if first else (common & pairs)
        first = False
    # poset as cover: a < b if (a,b) in common and no c with a<c<b
    # count linear extensions by DP over subsets of 14 events (2^14 = 16384)
    n = 14
    below = [0] * n  # bitmask of events that must precede i
    for a, b in common:
        below[events.index(b)] |= 1 << events.index(a)
    # transitive closure already in common (84 pairs)
    # DP
    N = 1 << n
    dp = [0] * N
    dp[0] = 1
    for mask in range(N):
        if dp[mask] == 0:
            continue
        for i in range(n):
            if (mask >> i) & 1:
                continue
            if (below[i] & mask) == below[i]:
                dp[mask | (1 << i)] += dp[mask]
    n_le = dp[N - 1]
    data["B412"]["n_linear_extensions_of_common_poset"] = n_le
    data["B412"]["exactly_the_8_paths"] = n_le == 8

    # ---- B416: diamond structure = 3 binary choices ----
    # identify the 3 independent order bits from the 8 path sequences
    seqs = [tuple(tuple(e) for e in p["ops"]) for p in paths]
    # bit0: order of +6,+25 (last two)
    # bit1: order of first two removals in each block
    # bit2: block type (which rearrangement of the first 5 events)
    def features(seq):
        tail = tuple(seq[-2:])
        head5 = tuple(seq[:5])
        # first two cells
        first2 = tuple(seq[0][1] for seq in [seq] for _ in [0])
        return tail, head5

    tails = sorted({tuple(s[-2:]) for s in seqs})
    heads = sorted({tuple(s[:5]) for s in seqs})
    data["B416"]["distinct_tails"] = [[list(e) for e in t] for t in tails]
    data["B416"]["distinct_head5"] = [[list(e) for e in h] for h in heads]
    data["B416"]["n_tail_orders"] = len(tails)
    data["B416"]["n_head5_blocks"] = len(heads)
    # within each head block, the first-two cell order
    first2s = sorted({(s[0][1], s[1][1]) for s in seqs})
    data["B416"]["distinct_first2"] = [list(x) for x in first2s]

    # ---- B418: non-trivial corner reuse ----
    # BFS on (node, enters, has, gap) gap = ops corner continuously occupied
    # A longstay means some occupation lasted >=2 ops (gap>=2 at some point)
    # We only need min dist to B for (enters=2, longstay=?) and (enters=2, not longstay)
    # Compact: state = (idx, enters, has, gap0_or_1plus, longstay)
    # gap capped at 2 (0,1,2+)
    def gapc(g):
        return 2 if g >= 2 else g

    st0 = (idx[A], 1 if (A >> CORNER) & 1 else 0, (A >> CORNER) & 1, 0, False)
    dist = {st0: 0}
    dq = deque([st0])
    hit = {}
    while dq:
        u, e, has, gap, ls = dq.popleft()
        dcur = dist[(u, e, has, gap, ls)]
        if clist[u] == B:
            key = (e, ls, gap)
            if key not in hit or dcur < hit[key]:
                hit[key] = dcur
        if e > 3:
            continue
        for v in adj[u]:
            sv = clist[v]
            nh = (sv >> CORNER) & 1
            if nh == 1 and has == 0:
                ne, ng, nls = e + 1, 0, ls
            elif nh == 1 and has == 1:
                ng = gapc(gap + 1)
                ne, nls = e, ls or (ng == 2)
            else:
                ne, ng, nls = e, 0, ls
            st = (v, ne, nh, ng, nls)
            if st not in dist and ne <= 3:
                dist[st] = dcur + 1
                dq.append(st)
    # summarize
    summary = {}
    for (e, ls, gap), dval in sorted(hit.items(), key=lambda x: (x[0][0], x[0][1], x[1])):
        summary[f"enters{e}_longstay{int(ls)}_gap{gap}"] = dval
    data["B418"]["refined_min_len"] = summary
    # key comparisons
    e1 = min((d for (e, ls, g), d in hit.items() if e == 1), default=None)
    e2_triv = min((d for (e, ls, g), d in hit.items() if e == 2 and not ls), default=None)
    e2_real = min((d for (e, ls, g), d in hit.items() if e == 2 and ls), default=None)
    e2_any = min((d for (e, ls, g), d in hit.items() if e == 2), default=None)
    data["B418"]["enter1_len"] = e1
    data["B418"]["enter2_immediate_only_len"] = e2_triv
    data["B418"]["enter2_with_longstay_len"] = e2_real
    data["B418"]["enter2_any_len"] = e2_any
    data["B418"]["excess_enter2_real_vs_enter1"] = (e2_real - e1) if (e2_real and e1) else None
    data["B418"]["excess_enter2_any_vs_enter1"] = (e2_any - e1) if (e2_any and e1) else None

    OUT.write_text(json.dumps(data, indent=2, default=str))
    print("n_le", n_le, "tails", len(tails), "heads", len(heads), "first2", first2s)
    print("B418 refined", summary)
    print("e1", e1, "e2_triv", e2_triv, "e2_real", e2_real, "e2_any", e2_any)


if __name__ == "__main__":
    main()
