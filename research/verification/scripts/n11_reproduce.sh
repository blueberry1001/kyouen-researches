#!/usr/bin/env bash
# Reproduce the n=11 verdict from scratch, on the two code paths that matter.
#
#   step 1  n11_lvl2.cpp     count the forbidden 4-sets directly for n=6..11
#                            and check F_9 = 29152, F_10 = 54441, F_11 = 95670
#   step 2  n11_d4.cpp       D4-symmetry Grundy solver; n=6 and n=7 reproduce the
#                            recorded g(empty) and P/N counts exactly, then n=11
#   step 3  n11_verdict.py   read level 1 of the n=11 output and conclude
#
# Usage: bash n11_reproduce.sh [--with-n11]
#   without --with-n11 it runs steps 1-2 on n=6,7 only (a few minutes)
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/n11_repro.log
: > "$LOG"
mkdir -p /tmp/kc_build

WANT_N11=0
[ "${1:-}" = "--with-n11" ] && WANT_N11=1

say() { echo "== $*" | tee -a "$LOG"; }

# ---------------------------------------------------------------- step 1
say "step 1: forbidden 4-sets, counted directly (n11_lvl2.cpp)"
g++ -O3 -march=native -std=c++20 -o /tmp/kc_build/lvl2 "$S/n11_lvl2.cpp" 2>>"$LOG" \
  || { echo "build failed" | tee -a "$LOG"; exit 1; }
for N in 9 10 11; do /tmp/kc_build/lvl2 "$N" 2>&1 | tee -a "$LOG"; done

# ---------------------------------------------------------------- step 2
say "step 2: D4-symmetry Grundy solver (n11_d4.cpp)"
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/d4 "$S/n11_d4.cpp" 2>>"$LOG" \
  || { echo "build failed" | tee -a "$LOG"; exit 1; }
export OMP_NUM_THREADS=16
for N in 6 7; do
  say "  n=$N (cross-check against the recorded values)"
  /tmp/kc_build/d4 --n "$N" --out /tmp/repro_n$N.json 2>&1 | tail -6 | tee -a "$LOG"
done

if [ "$WANT_N11" = 1 ]; then
  say "step 2b: n=11 (takes about 4 minutes)"
  mkdir -p /tmp/d4_n11
  /tmp/kc_build/d4 --n 11 --spill /tmp/d4_n11 \
      --out "$R/research/verification/data/n11_d4_final.json" 2>&1 \
      | tail -20 | tee -a "$LOG"
  # ---------------------------------------------------------------- step 3
  say "step 3: conclude from level 1 (n11_verdict.py)"
  python3 "$S/n11_verdict.py" 2>&1 | tee -a "$LOG"
else
  say "step 2b/3 skipped (pass --with-n11 to run n=11, ~4 min)"
fi
