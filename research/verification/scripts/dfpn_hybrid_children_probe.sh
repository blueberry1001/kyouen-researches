#!/bin/bash
# Baseline vs exact-handoff root-child diagnostic for center v=60.
set -euo pipefail

D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-300}
MEMO=${MEMO:-26}
EXACT_BUDGET=${EXACT_BUDGET:-200000}
EXACT_RETRIES=${EXACT_RETRIES:-2}
HYBRID_LEGAL=${HYBRID_LEGAL:-44}
OUT="$L/hybrid_children"
mkdir -p "$OUT"

run_arm(){
  local tag="$1"
  local legal="$2"
  rm -f "$OUT/$tag.log" "$OUT/$tag.csv"
  "$D" --n=11 --reps --only=60 --children     --memo="$MEMO" --budget="$BUDGET"     --exact-legal="$legal" --exact-budget="$EXACT_BUDGET"     --exact-retries="$EXACT_RETRIES"     --log="$OUT/$tag.log" --csv="$OUT/$tag.csv"     >/dev/null 2>&1
}

run_arm baseline 0 &
p0=$!
run_arm hybrid "$HYBRID_LEGAL" &
p1=$!
wait "$p0"
wait "$p1"

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python3 "$SCRIPT_DIR/dfpn_children_parse.py"   "baseline=$OUT/baseline.log" "hybrid=$OUT/hybrid.log"

echo
echo "=== outcomes ==="
for tag in baseline hybrid; do
  if grep -q '^\[done\]' "$OUT/$tag.log"; then
    grep '^\[done\]' "$OUT/$tag.log" | tail -1
  else
    grep 'TIMEOUT' "$OUT/$tag.csv" | tail -1
  fi
done
