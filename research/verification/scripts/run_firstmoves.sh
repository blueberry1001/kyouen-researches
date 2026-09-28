#!/bin/bash
# Build + run the round4 first-move solver.
# maxk_n8 = 4 by default: the n=8 mid-layer enumeration is the long pole and
# its exact growth is only needed to justify "n=8 full Grundy is out of reach".
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
g++ -O2 -march=native -std=c++20 -o /tmp/fm round4_firstmoves.cpp
echo "BUILD OK $(date +%T)"
cd "$REPO/research/verification"
echo "START $(date +%T)"
/usr/bin/time -v /tmp/fm "${1:-4}" > round4_firstmoves.json 2> /tmp/fm_time.txt || echo "RUN FAILED"
echo "DONE $(date +%T)"
grep -E "Elapsed|Maximum resident" /tmp/fm_time.txt || true
wc -c round4_firstmoves.json
