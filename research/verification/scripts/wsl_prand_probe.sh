#!/usr/bin/env bash
# Build the p_rand solver and report its CLI usage / argument handling.
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
if ! g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand "$S/round4_b501_prand.cpp"; then
  echo "BUILD FAILED"
  exit 1
fi
echo "build ok"
echo "--- usage / help ---"
/tmp/kc_build/prand --help 2>&1 | head -30 || true
echo "--- selftest ---"
/tmp/kc_build/prand --selftest 2>&1 | tail -20 || true
