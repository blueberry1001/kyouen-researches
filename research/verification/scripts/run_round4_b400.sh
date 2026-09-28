#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku-kyouen-researches
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
g++ -O2 -march=native -std=c++20 -o /tmp/r4b400 round4_b400.cpp
echo "=== BUILD OK ==="
for j in n4all n7layer; do
  echo "=== JOB $j ==="
  /tmp/r4b400 $j
done
echo "=== JOB col (may take a while) ==="
/tmp/r4b400 col
echo "=== ALL DONE ==="
