#!/bin/bash
# Compare exact result publication policies on center v=60.
# baseline: no exact handoff
# all:      exact DFS publishes every solved internal state to the df-pn TT
# root:     per-handoff local cache; publish only the solved handoff root
# separate: persistent exact cache across handoffs; publish only handoff roots
set -euo pipefail

D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-60}
MEMO=${MEMO:-24}
EXACT_LEGAL=${EXACT_LEGAL:-44}
EXACT_BUDGET=${EXACT_BUDGET:-200000}
EXACT_RETRIES=${EXACT_RETRIES:-2}
OUT="$L/exact_publish_probe"
mkdir -p "$OUT"

run_arm(){
  local tag="$1" legal="$2" publish="$3"
  rm -f "$OUT/$tag.log" "$OUT/$tag.csv"
  "$D" --n=11 --reps --only=60 --memo="$MEMO" --budget="$BUDGET" \
    --exact-legal="$legal" --exact-budget="$EXACT_BUDGET" \
    --exact-retries="$EXACT_RETRIES" --exact-publish="$publish" \
    --log="$OUT/$tag.log" --csv="$OUT/$tag.csv" >/dev/null 2>&1
}

run_arm baseline 0 all & p0=$!
run_arm all "$EXACT_LEGAL" all & p1=$!
run_arm root "$EXACT_LEGAL" root & p2=$!
run_arm separate "$EXACT_LEGAL" separate & p3=$!
wait "$p0"
wait "$p1"
wait "$p2"
wait "$p3"

echo "arm,outcome,root_pn,root_dn,expansions,memo,solved,solved_disc,evict_open,evict_solved,exact_calls,exact_nodes,exact_abort,exact_win,exact_loss,exact_stores,exact_local"
for tag in baseline all root separate; do
  if grep -q '^\[done\]' "$OUT/$tag.log" 2>/dev/null; then
    line=$(grep '^\[done\]' "$OUT/$tag.log" | tail -1)
    outcome=$(printf '%s\n' "$line" | sed -n 's/.*] \(WIN\|LOSS\).*/\1/p')
  else
    line=$(grep 'TIMEOUT' "$OUT/$tag.csv" | tail -1)
    outcome=TIMEOUT
  fi
  python3 - "$tag" "$outcome" "$line" <<'PY'
import re,sys
tag,outcome,line=sys.argv[1:4]
def get(k, default="-"):
    m=re.search(r'\b'+re.escape(k)+r'=([^ ]+)',line)
    return m.group(1) if m else default
print(",".join([
    tag,outcome,get("root_pn"),get("root_dn"),get("expansions"),get("memo"),
    get("solved"),get("solved_disc"),get("evict_open"),get("evict_solved"),
    get("exact_calls"),get("exact_nodes"),get("exact_abort"),get("exact_win"),
    get("exact_loss"),get("exact_stores"),get("exact_local")
]))
PY
done
