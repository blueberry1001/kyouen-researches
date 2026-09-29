#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$REPO/research/verification/scripts
cd "$S"
g++ -O2 -std=c++20 -o /tmp/ceil6 round5_b325_ceiling.cpp
echo "built ok"
# n=4,5 first as cross-check, then n=6
/tmp/ceil6 4 > /tmp/ceil_n4.json
echo "n4 done"
/tmp/ceil6 5 > /tmp/ceil_n5.json
echo "n5 done"
/tmp/ceil6 6 > /tmp/ceil_n6.json
echo "n6 done"
cp /tmp/ceil_n4.json /tmp/ceil_n5.json /tmp/ceil_n6.json "$REPO/research/verification/"
echo "copied"
