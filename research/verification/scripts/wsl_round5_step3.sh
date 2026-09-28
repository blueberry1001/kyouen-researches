#!/usr/bin/env bash
# Build + run the fixed CRT solver at n=4,5,6 and dump the key figures.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
B=/tmp/kc_build
mkdir -p $B
g++ -O2 -march=native -std=c++20 -fopenmp -o $B/crt "$S/round5_b501_prand8.cpp" || exit 1
echo "build ok"
$B/crt --selftest 2>&1 | tail -3
export OMP_NUM_THREADS=16
for N in 4 5 6; do
  echo "===== n=$N ====="
  $B/crt $N $B/n$N.json 2>&1 | grep -E '^\[|^    k=|~~|##' | tail -25
  echo "n$N exit=${PIPESTATUS[0]}"
done
