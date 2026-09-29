#!/usr/bin/env bash
# Exact level-2 count for n = 6..11, checked against the recorded F_n.
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11/research/verification/scripts
LOG=/tmp/lvl2c.log
: > "$LOG"
mkdir -p /tmp/kc_build
g++ -O3 -march=native -std=c++20 -o /tmp/kc_build/lvl2 "$S/n11_lvl2.cpp" 2>>"$LOG" \
  || { echo BUILD_FAIL >>"$LOG"; tail -20 "$LOG"; exit 1; }
echo "n   N      F       total_pairs  bad_pairs  LEVEL2   expectedF" >>"$LOG"
for N in 6 7 8 9 10 11; do
  /tmp/kc_build/lvl2 "$N" >>"$LOG" 2>&1
done
cat "$LOG"
