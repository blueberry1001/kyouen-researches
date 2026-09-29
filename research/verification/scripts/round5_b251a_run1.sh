#!/bin/bash
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
V=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/round5_b251a "$S/round5_b251a.cpp" || exit 1
STAGE="$1"
echo "=== $STAGE ==="
/tmp/round5_b251a "$STAGE" > "$V/round5_b251a_${STAGE}.json" 2> "$V/round5_b251a_${STAGE}.log"
echo EXIT:$?
tail -4 "$V/round5_b251a_${STAGE}.log"
echo "--- json head ---"
head -c 800 "$V/round5_b251a_${STAGE}.json"; echo
