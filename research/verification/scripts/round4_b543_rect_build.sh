#!/usr/bin/env bash
# build + smoke test of round4_b543_rect.cpp
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/r4rect round4_b543_rect.cpp 2>&1 | head -50
echo "BUILD_OK"
/tmp/r4rect --out=/tmp/smoke.json --sec=12 --m2=8 --m2c=8 2>&1 | tail -30
echo "SMOKE_OK"
cat /tmp/smoke.json
