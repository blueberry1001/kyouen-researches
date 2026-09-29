#!/bin/bash
set -e
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
D=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
cd "$S"
g++ -O2 -std=c++20 -o /tmp/round5_b301_b379 round5_b301_b379.cpp
/tmp/round5_b301_b379 "$D/round4_b371.bin"
echo "exit: $?"
cat round5_b301_b379.json 2>/dev/null || cat "$S/round5_b301_b379.json" 2>/dev/null
