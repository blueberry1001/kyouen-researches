#!/usr/bin/env bash
# Run p_rand for one n and write the JSON next to the repo.
# Usage: wsl_prand_n.sh <n> [threads]
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
N="${1:-7}"
T="${2:-16}"
mkdir -p /tmp/kc_build
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand "$S/round4_b501_prand.cpp" || { echo BUILD_FAIL; exit 1; }
export OMP_NUM_THREADS="$T"
OUT=$R/research/verification/round4_b501_prand_n${N}.json
echo "start n=$N threads=$T out=$OUT"
stdbuf -oL -eL /tmp/kc_build/prand "$N" "$OUT"
rc=$?
echo "exit=$rc"
ls -la "$OUT" 2>/dev/null || echo "no output file"
exit $rc
