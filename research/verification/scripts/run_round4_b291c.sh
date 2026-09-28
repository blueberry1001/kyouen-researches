#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd $REPO/research/verification/scripts
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/r4b291c round4_b291c.cpp
echo "=== compiled c ==="
/tmp/r4b291c $REPO/research/verification/round4_b291c.json
echo "=== done c ==="
