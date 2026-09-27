#!/usr/bin/env python3
"""Batch08 quick: B169 residues, B179 I_n(-1), save prior results."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")

OUT = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\batch08_results3.json"
report = {}

# B169
n = 5
pts = [(i % n, i // n) for i in range(n * n)]
corners = {(0, 0), (4, 0), (0, 4), (4, 4)}
W5 = {(x, y) for y in range(5) for x in range(5) if (x + y) % 2 == 0 and (x, y) not in corners}
b169 = {}
for m in (2, 3, 4, 5, 6):
    groups = defaultdict(list)
    for i in range(n * n):
        x, y = pts[i]
        outcome = "WIN" if (x, y) in W5 else "LOSS"
        groups[(x % m, y % m)].append((x, y, outcome))
    mixed = {str(k): v for k, v in groups.items() if len(set(o for _, _, o in v)) > 1}
    b169[m] = {"n_groups": len(groups), "mixed": len(mixed),
               "sample": list(mixed.items())[:2]}
    print(f"B169 m={m}: mixed groups={len(mixed)}/{len(groups)}", flush=True)
report["b169"] = b169

# B179 I_n(-1)
FVEC = {
    2: [1, 4, 6, 4],
    3: [1, 9, 36, 84, 112, 56],
    4: [1, 16, 120, 560, 1626, 2360, 1064, 64],
    5: [1, 25, 300, 2300, 11824, 37272, 59192, 35208, 5172, 100],
}
K = {2: 3, 3: 5, 4: 7, 5: 9}
NMAX = {2: None, 3: 56, 4: 64, 5: 100}
b179 = {}
for n, f in FVEC.items():
    I = sum(((-1) ** k) * fk for k, fk in enumerate(f))
    tot = sum(f)
    b179[n] = {
        "I": I, "abs_I": abs(I), "total_safe": tot,
        "abs_I_over_total": abs(I) / tot,
        "K_n": K[n], "n_max_sets": NMAX[n],
    }
    print(f"B179 n={n}: I(-1)={I} |I|/tot={abs(I)/tot:.4f} K={K[n]}", flush=True)
report["b179"] = b179

# B171-B173 quick recount of log-concavity margins
b171 = {}
for n, f in FVEC.items():
    peak = f.index(max(f))
    uni = all(f[i] <= f[i + 1] for i in range(peak)) and all(f[i] >= f[i + 1] for i in range(peak, len(f) - 1))
    logc = all(f[k] ** 2 >= f[k - 1] * f[k + 1] for k in range(1, len(f) - 1))
    N = n * n
    a = [f[k] / math.comb(N, k) for k in range(len(f))]
    alogc = all(a[k] ** 2 >= a[k - 1] * a[k + 1] - 1e-18 for k in range(1, len(a) - 1))
    b171[n] = {"peak": peak, "unimodal": uni, "logc": logc, "prob_logc": alogc, "f": f}
    print(f"B171-3 n={n}: peak={peak} uni={uni} logc={logc} prob_logc={alogc}", flush=True)
report["b171_173"] = b171

# P-rate mixing by layer (B176) from cycle4 depth profiles
print("\nB176 P-rate by layer:", flush=True)
profiles = {
    4: [1.0, 0.0, 0.7, 0.0286, 0.3936, 0.1407, 0.6466, 1.0],
    5: [0.0, 0.36, 0.0667, 0.2391, 0.1057, 0.1917, 0.2383, 0.3637, 0.8391, 1.0],
}
b176 = {}
for n, rates in profiles.items():
    # first k where rate is strictly between 0 and 1 (mixing onset)
    onset = next((k for k, r in enumerate(rates) if 0 < r < 1), None)
    b176[n] = {"loss_rates": rates, "mixing_onset_k": onset}
    print(f"  n={n} mixing starts at k={onset}", flush=True)
report["b176"] = b176

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
print(f"Wrote {OUT}")
