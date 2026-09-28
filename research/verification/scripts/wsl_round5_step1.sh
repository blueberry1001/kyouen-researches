#!/usr/bin/env bash
# Step 1: minimal reproducer + baseline run of the current CRT solver at n=4.
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build

echo "===== swap_repro (minimal release-pattern check) ====="
g++ -O0 -g -o /tmp/kc_build/swap_repro "$S/swap_repro.cpp" || exit 1
/tmp/kc_build/swap_repro
echo "swap_repro exit=$?"

echo
echo "===== round5_b501_prand8.cpp --selftest ====="
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/crt "$S/round5_b501_prand8.cpp" || exit 1
/tmp/kc_build/crt --selftest
echo "selftest exit=$?"

echo
echo "===== round5_b501_prand8.cpp n=4 (current, unmodified) ====="
export OMP_NUM_THREADS=4
/tmp/kc_build/crt 4 /tmp/kc_build/n4_base.json
echo "n4 exit=$?"
