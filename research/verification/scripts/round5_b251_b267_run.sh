#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
SRC=$REPO/research/verification/scripts/round5_b251_b267.cpp
BIN=/tmp/r5b267
mkdir -p /tmp/r5b251
echo "COMPILING..."
g++ -O2 -march=native -std=c++20 -fopenmp -o "$BIN" "$SRC"
echo "COMPILE_OK"

echo "B267 n=4"
"$BIN" b267 4 > /tmp/r5b251/b267_n4.json
cat /tmp/r5b251/b267_n4.json

echo "B267 n=5"
"$BIN" b267 5 > /tmp/r5b251/b267_n5.json
cat /tmp/r5b251/b267_n5.json

echo "SINGLES n=5 (OpenMP)"
date +%T
"$BIN" singles 5 > /tmp/r5b251/singles_n5.json
date +%T
cat /tmp/r5b251/singles_n5.json

echo "B267 n=6"
"$BIN" b267 6 > /tmp/r5b251/b267_n6.json
cat /tmp/r5b251/b267_n6.json

echo "ALL_OK"
