#!/usr/bin/env bash
# n=7 p_rand, no artificial cap, logging progress so we can see the levels.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/prand_n7.log
: > "$LOG"
free -m >>"$LOG"
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand \
  "$S/round4_b501_prand.cpp" 2>>"$LOG" || { echo BUILD_FAIL >>"$LOG"; exit 1; }
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
# heartbeat: sample RSS every 30 s in the background
( while true; do
    ps -o rss= -C prand 2>/dev/null | awk '{s+=$1} END {if (s) print "rss_MB", s/1024}'
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    sleep 30
  done ) >>"$LOG" 2>&1 &
HB=$!
stdbuf -oL -eL /tmp/kc_build/prand 7 /tmp/n7.json >>"$LOG" 2>&1
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc" >>"$LOG"
ls -la /tmp/n7.json >>"$LOG" 2>&1 || echo "no output" >>"$LOG"
tail -50 "$LOG"
