#!/usr/bin/env python3
"""Assemble research/verification/round4_b501_prand.json from the C++ runs.

Pulls /tmp/prand_n{4,5,6,7}.json (produced by round4_b501_prand.cpp in WSL)
and records the n=6 cross-check against the pure-Python reference in
round3_b502_pgrand_n6.json.
"""
import json, os, sys

REPO = '/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches'
OUT = os.path.join(REPO, 'research/verification/round4_b501_prand.json')
REF = os.path.join(REPO, 'research/verification/round3_b502_pgrand_n6.json')

data = {
    "task": "B501 / B502 — exact p_rand on P-positions, C++ (WSL) port, n=6 verify + n=7",
    "script": "research/verification/scripts/round4_b501_prand.cpp",
    "definition": ("p_rand(terminal)=0; p_rand(S)=1-(1/|L(S)|)*sum_{u in L(S)} p_rand(S|{u}); "
                   "L(S)=legal moves, uniform.  Identical to round3_b502_pgrand_n6.py."),
    "arithmetic": ("exact rationals num/D_k with a per-level common denominator; "
                   "self-contained base-10^9 big integers (boost unavailable, no sudo). "
                   "No floating point in the DP.  bn_* primitives unit-tested against "
                   "__int128 via --selftest."),
    "population": "ALL safe subsets reachable from the empty board (exact enumeration).",
    "n6_crosscheck": {},
}

runs = {}
for n in (4, 5, 6, 7):
    p = '/tmp/prand_n%d.json' % n
    if os.path.exists(p) and os.path.getsize(p) > 10:
        try:
            runs[n] = json.load(open(p))
        except Exception as e:
            print('n=%d: could not parse (%s)' % (n, e), file=sys.stderr)

for n, d in runs.items():
    data['n%d' % n] = d

# --- n=6 cross-check against the pure-Python reference ------------------
if 6 in runs and os.path.exists(REF):
    ref = json.load(open(REF))['n6']
    got = runs[6]
    checks = {}
    for key in ('n_safe_subsets', 'edge_total', 'max_safe_size', 'n_P', 'n_N',
                'P_max', 'P_max_dec', 'P_max_level', 'P_gt_1_2',
                'P_gt_2_3', 'P_gt_3_4', 'level_sizes', 'F', 'V'):
        rv, gv = ref.get(key), got.get(key)
        checks[key] = {"cpp": gv, "python": rv, "match": rv == gv}
    data['n6_crosscheck'] = {
        "reference_file": "research/verification/round3_b502_pgrand_n6.json",
        "all_match": all(c['match'] for c in checks.values()),
        "checks": checks,
        "empty_p_rand_match": ref['empty']['p_rand'] == got['empty']['p_rand'],
    }

json.dump(data, open(OUT, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print('wrote', OUT)
print('runs present:', sorted(runs))
if 'n6_crosscheck' in data and data['n6_crosscheck']:
    print('n6 all_match =', data['n6_crosscheck']['all_match'])
