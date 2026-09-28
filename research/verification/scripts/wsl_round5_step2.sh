#!/usr/bin/env bash
# Step 2: build the fixed CRT solver, selftest, and run n=4 / n=5.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
B=/tmp/kc_build
mkdir -p $B
g++ -O2 -march=native -std=c++20 -fopenmp -o $B/crt "$S/round5_b501_prand8.cpp" || exit 1
echo "build ok"
$B/crt --selftest; echo "selftest exit=$?"
export OMP_NUM_THREADS=8
echo "===== n=4 ====="
$B/crt 4 $B/n4.json 2>&1 | tail -20
echo "n4 exit=$?"
echo "===== n=5 ====="
$B/crt 5 $B/n5.json 2>&1 | tail -20
echo "n5 exit=$?"
