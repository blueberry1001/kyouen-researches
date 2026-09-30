#!/bin/bash
# Phase 7: re-measure the center v=60 root with the adaptive budget and
# compare against the old global-200k baseline.
#
# Baseline (from the threshold scan, memo 2^24, 60 s, publish=root):
#   L72 global 200k -> s5  29 calls /  0 win /  1 loss / 28 abort
#                     s6 116 calls / 74 win /  0 loss / 41 abort
# The question is whether giving s5 a real budget actually converts
# those 28 aborts into solved positions.
#
# These run sequentially, not in parallel: each allocates a 2^24 memo
# (~600 MB with the other tables) and 19 GB is not worth risking.
D=/mnt/d/ghq/build11/dfpn
OUT=/mnt/d/ghq/build11/logs/adaptive
mkdir -p "$OUT"
MEMO=${MEMO:-24}
BUDGET=${BUDGET:-60}

run() {  # tag, extra args...
  local tag=$1; shift
  rm -f "$OUT/$tag.csv" "$OUT/$tag.log"
  echo "=== $tag ==="
  "$D" --n=11 --reps --only=60 --memo="$MEMO" --budget="$BUDGET" \
       --exact-legal=72 --exact-retries=1 --exact-publish=root \
       --log="$OUT/$tag.log" --csv="$OUT/$tag.csv" \
       "$@" > /dev/null 2>&1
  grep -E '^\[done\]' "$OUT/$tag.log" | tail -1
  grep -E '^\[exact-depth\]' "$OUT/$tag.log" | tail -1
}

# Old behaviour: one global budget for every stone count.
run base200k --exact-budget=200000

# Adaptive: s5 gets what the benchmark says it needs, s6 keeps the old
# amount so it does not burn time on positions that already close.
run adaptive --exact-budget=200000 --exact-budget-by-stones=5:5000000,6:200000

# How much does a purely larger global budget buy? This separates "the
# adaptive split helped" from "just spend more nodes".
run global5m --exact-budget=5000000

echo ADAPTIVE_RUNS_DONE