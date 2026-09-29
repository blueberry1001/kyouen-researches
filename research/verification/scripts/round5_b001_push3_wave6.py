#!/usr/bin/env python3
"""Push3 wave6: random-greedy K10 + constructive s_n."""
from __future__ import annotations
import json, sys, random, itertools
from collections import Counter

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, board_square

PATH = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_push3.json"
OUT = json.load(open(PATH, encoding="utf-8"))

def save():
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)

def greedy_random(B, rng):
    occ = 0
    while True:
        mv = B.legal_moves(occ)
        if not mv:
            return occ
        occ |= 1 << mv[rng.randrange(len(mv))]

def grow_max(B, occ):
    changed = True
    while changed:
        changed = False
        for p in range(B.V):
            bit = 1 << p
            if occ & bit:
                continue
            ok = True
            for q in B.quads_by_pt[p]:
                if (occ | bit) & q == q:
                    ok = False
                    break
            if ok:
                occ |= bit
                changed = True
    return occ

print("=== K10 random greedy ===", flush=True)
B10 = board_square(10)
rng = random.Random(12345)
best = 0
best_w = None
hist = Counter()
for t in range(200):
    occ = grow_max(B10, greedy_random(B10, rng))
    k = bin(occ).count("1")
    hist[k] += 1
    if k > best:
        best = k
        best_w = [p for p in range(100) if (occ >> p) & 1]
        print(f"  t={t} new best {best}", flush=True)
        OUT.setdefault("k10_search", {})
        OUT["k10_search"]["random_greedy"] = {"size": best, "witness": best_w, "hist": dict(hist)}
        save()
print("  final best", best, "hist", dict(hist), flush=True)
OUT["k10_search"]["random_greedy"] = {"size": best, "witness": best_w, "hist": dict(hist)}
save()

# known 11-stone maximal on 10x10 from exploration
known11 = [11, 20, 23, 32, 43, 50, 59, 63, 68, 81, 98]
mask = 0
for p in known11:
    mask |= 1 << p
print("  known11 safe?", B10.is_safe(mask), "maximal?", B10.is_maximal(mask), flush=True)
OUT["k10_search"]["known11_check"] = {
    "safe": B10.is_safe(mask), "maximal": B10.is_maximal(mask), "size": len(known11)
}

# try to shrink known11 to 10: remove one point and re-grow to maximal of size 10?
# better: search for 10-stone maximal by starting from subsets of known11 + random
print("=== s10 constructive from known11 ===", flush=True)
hits10 = []
rng2 = random.Random(77)
for t in range(3000):
    # random 10-subset of 100, biased toward known11 neighborhood
    if t % 3 == 0:
        base = known11[:9] if t % 2 == 0 else known11[1:]
        s = list(base) + [rng2.randrange(100)]
    else:
        s = rng2.sample(range(100), 10)
    m = 0
    for p in s:
        m |= 1 << p
    if B10.is_safe(m) and B10.is_maximal(m):
        hits10.append(sorted(s))
        print("  found 10-stone maximal!", s, flush=True)
        if len(hits10) >= 3:
            break
print("  10-stone hits", len(hits10), flush=True)
OUT.setdefault("s_search", {})
OUT["s_search"]["n10_k10_constructive"] = {"hits": hits10, "n_hits": len(hits10), "trials": 3000}
save()

# n=9: try 8,9-stone maximal via random + grow-down
print("=== s9 constructive ===", flush=True)
B9 = board_square(9)
hits9 = []
for t in range(3000):
    s = rng2.sample(range(81), 9)
    m = 0
    for p in s:
        m |= 1 << p
    if B9.is_safe(m) and B9.is_maximal(m):
        hits9.append(sorted(s))
        print("  found 9-stone maximal n=9!", s, flush=True)
        if len(hits9) >= 2:
            break
print("  n9 k9 hits", len(hits9), flush=True)
OUT["s_search"]["n9_k9_constructive"] = {"hits": hits9, "n_hits": len(hits9), "trials": 3000}
save()
print("WAVE6 DONE", flush=True)
