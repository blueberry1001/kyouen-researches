#!/usr/bin/env bash
# CRT solver on n=4 with full diagnostics captured, for the CSR failure hunt.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/csr.log
: > "$LOG"
mkdir -p /tmp/kc_build
g++ -O1 -g -std=c++20 -fopenmp -o /tmp/kc_build/crt_dbg "$S/round5_b501_prand8.cpp" >>"$LOG" 2>&1
if [ ! -x /tmp/kc_build/crt_dbg ]; then echo "BUILD_FAIL" >>"$LOG"; tail -20 "$LOG"; exit 1; fi
export OMP_NUM_THREADS=1
/tmp/kc_build/crt_dbg 4 /tmp/csr_n4.json >"$LOG" 2>&1
echo "exit=$?" >>"$LOG"
tail -12 "$LOG"
