#!/bin/bash
set -e
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
D=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
cd "$S"
echo "=== build B379 ==="
g++ -O2 -std=c++20 -o /tmp/round5_b301_b379 round5_b301_b379.cpp
echo "=== run B379 all 408 ==="
/tmp/round5_b301_b379 "$D/round4_b371.bin"
echo "=== build B370 ==="
g++ -O2 -std=c++20 -o /tmp/round5_b301_b370 round5_b301_b370.cpp
echo "=== run B370 ==="
/tmp/round5_b301_b370 "$D/round4_b371.bin"
echo "=== done ==="
