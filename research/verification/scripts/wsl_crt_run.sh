#!/usr/bin/env bash
# Build and self-test the CRT streaming solver, then run n=6 and n=7 to
# cross-check against the big-integer reference before attempting n=8.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/crt.log
: > "$LOG"
free -m >>"$LOG"
mkdir -p /tmp/kc_build
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/crt "$S/round5_b501_prand8.cpp" 2>>"$LOG"; then
  echo "BUILD_FAIL" >>"$LOG"
  tail -30 "$LOG"
  exit 1
fi
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16

if /tmp/kc_build/crt --selftest >>"$LOG" 2>&1; then
  echo "selftest PASS" >>"$LOG"
else
  echo "selftest FAIL" >>"$LOG"
fi

for N in 6 7; do
  echo "--- n=$N ---" >>"$LOG"
  stdbuf -oL -eL /tmp/kc_build/crt "$N" "/tmp/crt_n${N}.json" >>"$LOG" 2>&1
  echo "exit=$?" >>"$LOG"
done
grep -v '^ *k=' "$LOG" | grep -v rss_MB | grep -v avail_MB | tail -40
