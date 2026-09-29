#!/bin/bash
set -x
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$REPO/research/verification/scripts
cd "$S"
echo "=== build ==="
g++ -O2 -std=c++20 -o /tmp/round5_b301_j6 round5_b301_j6.cpp 2>&1
echo "build exit: $?"
ls -la /tmp/round5_b301_j6
echo "=== run n=4 ==="
/tmp/round5_b301_j6 4 2>&1
echo "run4 exit: $?"
