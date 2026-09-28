#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
g++ -O2 -march=native -std=c++20 -o /tmp/tstar round4_tstar.cpp
g++ -O2 -march=native -std=c++20 -o /tmp/n7l round4_n7_layers.cpp
echo "BUILD OK $(date +%T)"
cd "$REPO/research/verification"
/usr/bin/time -f 'TSTAR_ELAPSED %e s MAXRSS %M KB' /tmp/tstar 6 7 > round4_tstar_n67.json 2> /tmp/t67_time.txt || echo "TSTAR FAILED"
cat /tmp/t67_time.txt
/usr/bin/time -f 'N7L_ELAPSED %e s MAXRSS %M KB' /tmp/n7l 6 > round4_n7_layers.json 2> /tmp/n7l_time.txt || echo "N7L FAILED"
cat /tmp/n7l_time.txt
echo "ALL DONE $(date +%T)"
