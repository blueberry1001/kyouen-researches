#!/bin/bash
# B370 follow-up: classify shrink/deform candidates on all 408 8-stone maximal sets.
set -e
cd /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
g++ -O2 -std=c++17 -I scripts -o /tmp/round5_b301_b370f scripts/round5_b301_b370f.cpp
/tmp/round5_b301_b370f round4_b371.bin
echo "done"
ls -l round5_b301_b370f.json
