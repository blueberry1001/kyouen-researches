#!/bin/bash
# Build + run the T*/WFT solver for n = 4,5,6,7.
# n=6 is the decisive board for B034 (the only "not explained by parity"
# candidate), so it is included; n=7 is cheap in principle because K_7=14 and
# there are only 16 maximal safe sets, but the enumeration is the long pole.
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
g++ -O2 -march=native -std=c++20 -o /tmp/tstar round4_tstar.cpp
echo "BUILD OK $(date +%T)"
cd "$REPO/research/verification"
echo "START $(date +%T)"
/usr/bin/time -v /tmp/tstar "$@" > round4_tstar.json 2> /tmp/tstar_time.txt || echo "RUN FAILED"
echo "DONE $(date +%T)"
grep -E "Elapsed|Maximum resident" /tmp/tstar_time.txt || true
wc -c round4_tstar.json
