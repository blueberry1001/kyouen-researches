#!/usr/bin/env bash
# Build and run the DP scanner.
set -euo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/dp_scan "$S/dp_scan.cpp"
echo "build ok"
export OMP_NUM_THREADS=12
/tmp/kc_build/dp_scan /home/yuubi/spill8 8 --out="$R/research/verification/round5_prand_n8.json"
