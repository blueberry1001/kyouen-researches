#!/usr/bin/env bash
# Cross-check the n=11 Grundy solver on n=6 and n=7 before running n=11.
#   n=6: g(empty)=1, P=1,265,112  N=3,816,177
#   n=7: g(empty)=0, P= 41,264,615 N=138,545,735
# (from research/verification/round3_b502_pgrand_n6.json and
#  research/verification/round4_b501_prand_n7.json)
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/grundy_x.log
: > "$LOG"
free -m >>"$LOG"
mkdir -p /tmp/kc_build
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/g121 "$S/n11_grundy.cpp" 2>>"$LOG"; then
  echo BUILD_FAIL >>"$LOG"; tail -30 "$LOG"; exit 1
fi
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
for N in 6 7; do
  echo "--- n=$N ---" >>"$LOG"
  stdbuf -oL -eL /tmp/kc_build/g121 --n "$N" --out=/tmp/g$N.json >>"$LOG" 2>&1
  echo "exit=$?" >>"$LOG"
done
python3 - <<'PY' >>"$LOG" 2>&1
import json
ref = {6: ("/tmp/g6.json", 1, 1265112, 3816177),
       7: ("/tmp/g7.json", 0, 41264615, 138545735)}
for n, (path, g0, nP, nN) in ref.items():
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"n={n}: no output ({e})"); continue
    got = (d.get("g_empty"), d.get("n_P"), d.get("n_N"))
    want = (g0, nP, nN)
    print(f"n={n}  g_empty={got[0]} (want {g0})  n_P={got[1]} (want {nP})  "
          f"n_N={got[2]} (want {nN})  MATCH={got == want}")
    print(f"       level_sizes={d.get('level_sizes')}")
    print(f"       peak_rss_gb={d.get('peak_rss_gb')}  seconds={d.get('timing_s')}")
PY
grep -vE 'avail_MB|spill_MB' "$LOG" | tail -35
