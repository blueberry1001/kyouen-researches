#!/usr/bin/env bash
# Run the D4-symmetry solver on n=11, resuming past level 5 if a spill exists.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/d4_n11.log
: > "$LOG"
free -m >>"$LOG"
mkdir -p /tmp/kc_build /tmp/d4_n11
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/d4 "$S/n11_d4.cpp" 2>>"$LOG" \
  || { echo BUILD_FAIL >>"$LOG"; grep -E 'error' "$LOG" | head -10; exit 1; }
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
( while true; do
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    du -sm /tmp/d4_n11 2>/dev/null | awk '{print "spill_MB", $1}'
    sleep 90
  done ) >>"$LOG" 2>&1 &
HB=$!
stdbuf -oL -eL /tmp/kc_build/d4 --n 11 --spill /tmp/d4_n11 \
  --out "$R/research/verification/data/n11_d4_final.json" >>"$LOG" 2>&1
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc" >>"$LOG"
grep -vE 'avail_MB|spill_MB' "$LOG" | tail -40
