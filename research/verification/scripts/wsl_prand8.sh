#!/usr/bin/env bash
# n=8 p_rand with MAXL=20. Peaks near 1.4e8 states in the widest level.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/prand_n8.log
: > "$LOG"
free -m >>"$LOG"
mkdir -p /tmp/kc_build
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand20 "$S/round4_b501_prand.cpp" 2>>"$LOG" || { echo BUILD_FAIL >>"$LOG"; exit 1; }
echo "build ok MAXL=20" >>"$LOG"
export OMP_NUM_THREADS=16
( while true; do
    ps -o rss= -C prand20 2>/dev/null | awk '{s+=$1} END {if (s) print "rss_MB", s/1024}'
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    sleep 60
  done ) >>"$LOG" 2>&1 &
HB=$!
stdbuf -oL -eL /tmp/kc_build/prand20 8 "$R/research/verification/round4_b501_prand_n8.json" >>"$LOG" 2>&1
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc" >>"$LOG"
grep -v rss_MB "$LOG" | grep -v avail_MB | tail -40
