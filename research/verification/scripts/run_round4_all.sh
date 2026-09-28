#!/bin/bash
# Round4 batch b092-b127: full run.
set -u
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
V=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
cd "$S" || exit 1
g++ -O2 -march=native -std=c++20 -o /tmp/r4 round4_b092.cpp 2> /tmp/r4_build.log || { echo BUILD FAILED; cat /tmp/r4_build.log; exit 1; }
echo "BUILD OK"
if [ "${FRESH:-0}" = "1" ]; then rm -f "$V/round4_b092.json"; fi
for j in "$@"; do
  echo "===== job $j  ($(date +%H:%M:%S)) ====="
  /tmp/r4 "$j" 2>&1 || echo "job $j FAILED rc=$?"
done
echo "===== ALL JOBS DONE ====="
