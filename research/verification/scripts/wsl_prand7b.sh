#!/usr/bin/env bash
# Memory-capped n=7 run. Writes progress to a log file we can tail.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/prand_n7.log
: > "$LOG"
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand \
  "$S/round4_b501_prand.cpp" 2>>"$LOG" || { echo BUILD_FAIL >>"$LOG"; exit 1; }
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=8
ulimit -v 12000000
stdbuf -oL -eL /tmp/kc_build/prand 7 /tmp/n7.json >>"$LOG" 2>&1
echo "exit=$?" >>"$LOG"
ls -la /tmp/n7.json >>"$LOG" 2>&1 || echo "no output" >>"$LOG"
tail -40 "$LOG"
