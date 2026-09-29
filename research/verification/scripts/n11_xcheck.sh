#!/usr/bin/env bash
# Cross-check the 2-word enumerator against the known small-n values, then
# report where n=11 stands.
#   F_6 = 2491, F_7 = 6364, F_8 = 14564, F_9 = 29152
#   level sizes for n=6: [1,36,630,7140,56414,301952,997796,1783296,
#                          1459292,438952,35316,464]
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/n11x.log
: > "$LOG"
mkdir -p /tmp/kc_build /tmp/n11_121
free -m >>"$LOG"
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/e121 "$S/n11_enum121.cpp" 2>>"$LOG" \
  || { echo BUILD_FAIL >>"$LOG"; tail -25 "$LOG"; exit 1; }
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
for N in 6 7; do
  echo "--- n=$N ---" >>"$LOG"
  stdbuf -oL -eL /tmp/kc_build/e121 --enum "$N" --spill=/tmp/n11_121 >>"$LOG" 2>&1
  echo "exit=$?" >>"$LOG"
done
grep -vE 'avail_MB|spill_MB' "$LOG" | tail -45
