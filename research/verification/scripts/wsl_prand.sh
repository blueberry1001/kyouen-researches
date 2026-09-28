#!/usr/bin/env bash
# Run the p_rand solver for a single board size.
# Usage: wsl_prand.sh <n> [threads]
set -euo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand "$S/round4_b501_prand.cpp"
export OMP_NUM_THREADS="${2:-16}"
/tmp/kc_build/prand "$1"
