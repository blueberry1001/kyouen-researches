#!/usr/bin/env bash
# Measure the n=11 state space. Usage: n11_probe.sh [n] [maxlevel]
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11/research/verification/scripts
N="${1:-11}"
MAX="${2:-200}"
LOG=/tmp/n11_probe.log
: > "$LOG"
mkdir -p /tmp/kc_build /tmp/n11
free -m >>"$LOG"
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/n11probe "$S/n11_probe.cpp" 2>>"$LOG" \
  || { echo BUILD_FAIL >>"$LOG"; tail -25 "$LOG"; exit 1; }
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
( while true; do
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    du -sm /tmp/n11 2>/dev/null | awk '{print "spill_MB", $1}'
    sleep 60
  done ) >>"$LOG" 2>&1 &
HB=$!
stdbuf -oL -eL /tmp/kc_build/n11probe --enum "$N" --spill=/tmp/n11 --maxlevel "$MAX" \
  >>"$LOG" 2>&1
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc" >>"$LOG"
grep -v avail_MB "$LOG" | grep -v spill_MB | tail -40
