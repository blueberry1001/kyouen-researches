#!/usr/bin/env bash
# Isolate the CRT solver on n=4 only: fast, and enough to catch a lifetime bug.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O1 -g -fsanitize=address -std=c++20 -fopenmp \
    -o /tmp/kc_build/crt_asan "$S/round5_b501_prand8.cpp" 2>&1 | head -20
if [ ! -x /tmp/kc_build/crt_asan ]; then echo "ASAN BUILD FAILED"; exit 1; fi
echo "asan build ok"
export OMP_NUM_THREADS=4
export ASAN_OPTIONS=detect_leaks=0:abort_on_error=0
/tmp/kc_build/crt_asan 4 /tmp/asan_n4.json 2>&1 | tail -40
