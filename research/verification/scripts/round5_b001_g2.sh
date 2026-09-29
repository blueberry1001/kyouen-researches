#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$REPO/research/verification/scripts
g++ -O2 -march=native -std=c++20 -o /tmp/r5g2 "$S/round5_b001_g2.cpp"
echo "=== n=5 (self-check) ==="
/tmp/r5g2 5
echo "=== n=6 (B024 target) ==="
/tmp/r5g2 6
