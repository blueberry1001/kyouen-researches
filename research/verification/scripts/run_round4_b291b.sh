#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd $REPO/research/verification/scripts
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/r4b291b round4_b291.cpp
echo "=== compiled ==="
/tmp/r4b291b $REPO/research/verification/round4_b291.json
echo "=== done ==="
