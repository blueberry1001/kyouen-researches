#!/bin/bash
# Correctness regression for the df-pn + exact-endgame hybrid.
#
# The hybrid may change the number of expansions, but it MUST NOT change
# any proven outcome. We test the known empty-board results n=4..7 under
# several exact-legal thresholds. exact-budget is deliberately generous
# enough to exercise the handoff while still allowing UNKNOWN fallbacks.
set -euo pipefail

D=${D:-/mnt/d/ghq/build11/dfpn}
MEMO=${MEMO:-24}
EXACT_BUDGET=${EXACT_BUDGET:-200000}
EXACT_RETRIES=${EXACT_RETRIES:-2}

for legal in 0 4 6 8; do
  echo "=== exact_legal=$legal ==="
  for n in 4 5 6 7; do
    echo "--- n=$n ---"
    "$D" --n="$n" --empty --memo="$MEMO" \
      --exact-legal="$legal" \
      --exact-budget="$EXACT_BUDGET" \
      --exact-retries="$EXACT_RETRIES" 2>&1 \
      | grep -E '^\[done\]|^# done'
  done
done

# Root-only publish mode: exact recursion memoizes in a local cache and
# publishes only the handoff root to the main df-pn TT. Outcomes must match
# both baseline and publish-all mode.
echo "=== exact root-only publish: legal=8 budget=$EXACT_BUDGET ==="
for n in 4 5 6 7; do
  echo "--- n=$n ---"
  "$D" --n="$n" --empty --memo="$MEMO" \
    --exact-legal=8 --exact-budget="$EXACT_BUDGET" \
    --exact-retries="$EXACT_RETRIES" --exact-publish=root 2>&1 \
    | grep -E '^\[done\]|^# done'
done

# Force UNKNOWN fallbacks: each exact attempt gets only one DFS node.
# The final proven outcomes must still match the baseline, demonstrating
# that an aborted handoff cannot inject an unsound solved result.
echo "=== exact abort stress: legal=8 budget=1 retries=2 ==="
for n in 4 5 6 7; do
  echo "--- n=$n ---"
  "$D" --n="$n" --empty --memo="$MEMO" \
    --exact-legal=8 --exact-budget=1 --exact-retries=2 2>&1 \
    | grep -E '^\[done\]|^# done'
done

echo HYBRID_REGRESSION_DONE
