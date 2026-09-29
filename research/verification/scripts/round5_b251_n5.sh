#!/bin/bash
# n=5 single-quad removal (826) + limited pairs
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
BIN=/tmp/r5b251_solver
if [ ! -x "$BIN" ]; then
  g++ -O2 -march=native -std=c++20 -o "$BIN" "$REPO/research/verification/scripts/round5_b251_solver.cpp"
fi
echo "START singles_n5 $(date +%T)"
"$BIN" singles 5 > /tmp/r5b251/singles_n5.json 2>/tmp/r5b251/singles_n5.err
echo "END singles_n5 $(date +%T) bytes=$(wc -c < /tmp/r5b251/singles_n5.json)"
head -c 600 /tmp/r5b251/singles_n5.json
echo
