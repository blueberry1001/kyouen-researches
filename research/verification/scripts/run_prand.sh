#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/prand round4_b501_prand.cpp
echo "=== build ok ==="
/tmp/prand --selftest
for N in "$@"; do
  echo "=== running n=$N ==="
  /usr/bin/time -v /tmp/prand "$N" > /tmp/prand_n${N}.json 2>/tmp/prand_n${N}.log || true
  grep -E "Maximum resident|Elapsed" /tmp/prand_n${N}.log || true
done
