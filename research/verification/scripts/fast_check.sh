#!/usr/bin/env bash
# Quick cross-check of optimized legal_one on n=6 (fast).
set -euo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/fast_check.log
: > "$LOG"
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream_fast "$S/round5_prand_stream.cpp" 2>>"$LOG"
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=8
rm -rf /tmp/lk_fast6
mkdir -p /tmp/lk_fast6
/tmp/kc_build/stream_fast --solve 6 --spill=/tmp/lk_fast6 --out=/tmp/fast_n6.json >>"$LOG" 2>&1
echo "exit=$?" >>"$LOG"
python3 "$S/xcheck_parse.py" /tmp/fast_n6.json 6
