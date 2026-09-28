#!/usr/bin/env bash
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
B=/tmp/kc_build
g++ -O2 -march=native -std=c++20 -fopenmp -o $B/crt "$S/round5_b501_prand8.cpp" || exit 1
export OMP_NUM_THREADS=8
KCDBG=0 $B/crt 4 2>&1 | grep -E 'dbg|pre |post |^\[|k= ' | head -50
