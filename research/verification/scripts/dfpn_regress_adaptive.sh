#!/bin/bash
# Correctness regression for --exact-budget-by-stones.
#
# The per-stone budget must not change any proven outcome: it only
# changes HOW MANY nodes a handoff may consume before it gives up, and
# an under-budgeted handoff returns UNKNOWN, which is the same as no
# information. So n=4..7 must be identical for every setting, including
# settings that force heavy aborts.
#
# Also checks a malformed spec is rejected rather than silently ignored.
D=/mnt/d/ghq/build11/dfpn
expect() {  # n, expected_outcome, label
  local n=$1 want=$2 label=$3
  local out
  out=$("$D" --n="$n" --empty --memo=24 $4 $5 $6 2>&1 | grep '^\[done\]' | head -1)
  local got
  got=$(echo "$out" | sed -n 's/.*\] \([A-Z]*\) expansions.*/\1/p')
  if [ "$got" = "$want" ]; then
    echo "  OK   n=$n $label -> $got"
  else
    echo "  FAIL n=$n $label -> got '$got' want '$want'"
    FAILED=1
  fi
}
FAILED=0
echo "=== baseline: no per-stone budget ==="
expect 4 LOSS "" "--exact-legal=8" "--exact-budget=200000" "--exact-retries=2"
expect 5 WIN  "" "--exact-legal=8" "--exact-budget=200000" "--exact-retries=2"
expect 6 WIN  "" "--exact-legal=8" "--exact-budget=200000" "--exact-retries=2"
expect 7 LOSS "" "--exact-legal=8" "--exact-budget=200000" "--exact-retries=2"

echo "=== adaptive: s5 huge, s6 small ==="
expect 4 LOSS "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:5000000,6:200000"
expect 5 WIN  "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:5000000,6:200000"
expect 6 WIN  "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:5000000,6:200000"
expect 7 LOSS "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:5000000,6:200000"

echo "=== adaptive: tiny budgets everywhere (forces aborts) ==="
expect 4 LOSS "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:1,6:1,7:1"
expect 5 WIN  "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:1,6:1,7:1"
expect 6 WIN  "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:1,6:1,7:1"
expect 7 LOSS "" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:1,6:1,7:1"

echo "=== publish=root with adaptive ==="
expect 6 WIN  "--exact-publish=root" "--exact-legal=8" "--exact-budget=200000" "--exact-budget-by-stones=5:5000000,6:200000"

echo "=== malformed spec must be rejected ==="
"$D" --n=6 --empty --memo=24 --exact-legal=8 --exact-budget-by-stones=garbage >/dev/null 2>&1
if [ $? -eq 2 ]; then echo "  OK   malformed spec -> rc=2"; else echo "  FAIL malformed spec accepted"; FAILED=1; fi

if [ "$FAILED" = "0" ]; then echo "ADAPTIVE_REGRESS_DONE"; else echo "ADAPTIVE_REGRESS_FAILED"; exit 1; fi