#!/usr/bin/env bash
# Trace exactly which level is emptied and when.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/trace.log
: > "$LOG"
mkdir -p /tmp/kc_build
g++ -O1 -g -std=c++20 -fopenmp -o /tmp/kc_build/crt_tr "$S/round5_b501_prand8.cpp" >>"$LOG" 2>&1
export OMP_NUM_THREADS=1
/tmp/kc_build/crt_tr 4 /tmp/tr_n4.json >>"$LOG" 2>&1
echo "exit=$?" >>"$LOG"
grep -E 'level_sizes|UNAVAILABLE|EMPTIED|exit=' "$LOG"
