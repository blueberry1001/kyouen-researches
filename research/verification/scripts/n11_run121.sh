#!/usr/bin/env bash
# Enumerate n=11 with the verified 2-word enumerator.
# The 2-word version reproduced the known level sizes for n=6 and n=7 exactly,
# so its n=11 output is trustworthy.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/n11_121.log
: > "$LOG"
mkdir -p /tmp/kc_build /tmp/n11_121
free -m >>"$LOG"
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/e121 "$S/n11_enum121.cpp" 2>>"$LOG" \
  || { echo BUILD_FAIL >>"$LOG"; tail -25 "$LOG"; exit 1; }
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
( while true; do
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    du -sm /tmp/n11_121 2>/dev/null | awk '{print "spill_MB", $1}'
    sleep 120
  done ) >>"$LOG" 2>&1 &
HB=$!
stdbuf -oL -eL /tmp/kc_build/e121 --enum 11 --spill=/tmp/n11_121 \
  --out="$R/research/verification/data/n11_enum121.json" >>"$LOG" 2>&1
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc" >>"$LOG"
grep -vE 'avail_MB|spill_MB' "$LOG" | tail -40
