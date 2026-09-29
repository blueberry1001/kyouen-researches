#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$REPO/research/verification/scripts
cd "$S"
echo "=== build ==="
g++ -O2 -std=c++20 -o /tmp/round5_b301_j6 round5_b301_j6.cpp
echo "=== run n=2..4 first (self-check) ==="
/tmp/round5_b301_j6 4
echo "=== run n=2..6 (full) ==="
/tmp/round5_b301_j6 6
echo "=== done ==="
free -h
