#!/usr/bin/env bash
# Cross-check the CRT solver against the big-integer reference on n=6, n=7.
# CRT reproduces P_max only modulo the Mersenne prime, so the comparison is
# done in that field:  a/b  vs  a * inverse(b) mod P1.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/xcheck.log
: > "$LOG"
mkdir -p /tmp/kc_build
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/crt "$S/round5_b501_prand8.cpp" 2>>"$LOG" || { echo BUILD_FAIL; exit 1; }
export OMP_NUM_THREADS=16
for N in 6 7; do
  echo "--- n=$N ---" >>"$LOG"
  stdbuf -oL -eL /tmp/kc_build/crt "$N" "/tmp/crt_n${N}.json" >>"$LOG" 2>&1
  echo "exit=$?" >>"$LOG"
done
python3 - "$R" >>"$LOG" 2>&1 <<'PY'
import json, sys
R = sys.argv[1]
P1 = (1 << 61) - 1

def inv(a, m):
    return pow(a, m - 2, m)

ref = {
    6: (5162, 6615, R + "/research/verification/round3_b502_pgrand_n6.json"),
    7: (3709, 4620, R + "/research/verification/round4_b501_prand_n7.json"),
}
for n, (a, b, _) in ref.items():
    path = f"/tmp/crt_n{n}.json"
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"n={n}: no output ({e})")
        continue
    got = d.get("P_max_num_mod_p1")
    want = (a * inv(b, P1)) % P1
    print(f"n={n} P_max = {a}/{b}")
    print(f"   expected num mod P1 = {want}")
    print(f"   solver   num mod P1 = {got}")
    print(f"   MATCH: {str(got) == str(want)}")
    print(f"   P_max_level={d.get('P_max_level')} P_gt_3_4={d.get('P_gt_3_4')}")
    print(f"   n_safe_subsets={d.get('n_safe_subsets')} edges={d.get('edge_total')}")
    print(f"   peak_rss_gb={d.get('peak_rss_gb')}")
PY
tail -30 "$LOG"
