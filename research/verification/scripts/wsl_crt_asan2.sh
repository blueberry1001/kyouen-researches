#!/usr/bin/env bash
# AddressSanitizer run of the CRT solver on n=4, logging to a file.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/asan.log
: > "$LOG"
mkdir -p /tmp/kc_build
g++ -O1 -g -fsanitize=address -std=c++20 -fopenmp \
    -o /tmp/kc_build/crt_asan "$S/round5_b501_prand8.cpp" >>"$LOG" 2>&1
if [ ! -x /tmp/kc_build/crt_asan ]; then echo "ASAN BUILD FAILED" >>"$LOG"; exit 1; fi
echo "asan build ok" >>"$LOG"
export OMP_NUM_THREADS=4
export ASAN_OPTIONS=detect_leaks=0
/tmp/kc_build/crt_asan 4 /tmp/asan_n4.json >>"$LOG" 2>&1
echo "exit=$?" >>"$LOG"
tail -45 "$LOG"
