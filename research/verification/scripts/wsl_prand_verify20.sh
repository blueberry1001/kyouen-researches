#!/usr/bin/env bash
# Verify the MAXL=20 change did not alter any digit: re-run n=6 and compare
# against the recorded reference, then run n=7.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/prand_verify.log
: > "$LOG"
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand20 "$S/round4_b501_prand.cpp" 2>>"$LOG" || { echo BUILD_FAIL >>"$LOG"; exit 1; }
echo "build ok (MAXL=20)" >>"$LOG"
export OMP_NUM_THREADS=16
/tmp/kc_build/prand20 --selftest >>"$LOG" 2>&1
echo "--- n=6 (must reproduce 5162/6615) ---" >>"$LOG"
stdbuf -oL /tmp/kc_build/prand20 6 /tmp/n6_20.json >>"$LOG" 2>&1
python3 - <<'PY' >>"$LOG" 2>&1
import json
d = json.load(open("/tmp/n6_20.json", encoding="utf-8"))
r = json.load(open("/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/round3_b502_pgrand_n6.json", encoding="utf-8"))["n6"]
checks = ["n_safe_subsets", "edge_total", "max_safe_size", "n_P", "n_N", "P_max"]
for c in checks:
    print(f"  {c:18s} new={d[c]} ref={r[c]} {'OK' if str(d[c])==str(r[c]) else 'MISMATCH'}")
for c in ["P_gt_1_2", "P_gt_2_3", "P_gt_3_4"]:
    print(f"  {c:18s} new={d[c]} ref={r[c]} {'OK' if d[c]==r[c] else 'MISMATCH'}")
print("  n6 identical:", all(str(d[c]) == str(r[c]) for c in checks) and all(d[c] == r[c] for c in ["P_gt_1_2","P_gt_2_3","P_gt_3_4"]))
PY
tail -30 "$LOG"
