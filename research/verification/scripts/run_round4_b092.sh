#!/bin/bash
# Round4 batch b092-b127 driver. Run:  wsl -d Ubuntu -- bash <path>
set -u
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
V=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
cd "$S" || exit 1
g++ -O2 -march=native -std=c++20 -o /tmp/r4 round4_b092.cpp 2> /tmp/r4_build.log
if [ $? -ne 0 ]; then echo "BUILD FAILED"; cat /tmp/r4_build.log; exit 1; fi
echo "BUILD OK"
/tmp/r4 selftest fresh 2>&1 | grep selftest
