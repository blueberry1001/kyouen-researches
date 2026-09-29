#!/usr/bin/env bash
# Solve n=11. The solver is verified: it reproduced g(empty) and the P/N counts
# for n=6 and n=7 exactly. It enumerates its own levels and computes the
# Grundy values, so it does not depend on the spill from the other enumerator.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/n11_solve.log
: > "$LOG"
free -m >>"$LOG"
mkdir -p /tmp/kc_build /tmp/n11_solve
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/g121 "$S/n11_grundy.cpp" 2>>"$LOG"; then
  echo BUILD_FAIL >>"$LOG"; tail -30 "$LOG"; exit 1
fi
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
( while true; do
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    du -sm /tmp/n11_solve 2>/dev/null | awk '{print "spill_MB", $1}'
    sleep 120
  done ) >>"$LOG" 2>&1 &
HB=$!
stdbuf -oL -eL /tmp/kc_build/g121 --n 11 --spill=/tmp/n11_solve \
  --out="$R/research/verification/data/n11_grundy.json" >>"$LOG" 2>&1
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc" >>"$LOG"
grep -vE 'avail_MB|spill_MB' "$LOG" | tail -45
