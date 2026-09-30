#!/bin/bash
# Compare baseline df-pn against exact-endgame handoff thresholds on v=60.
#
# Four fresh processes are intended to run in parallel on a 16-core/19GB
# machine. With memo=26 they use roughly ~2GB RSS each; verify free memory
# before launching. The comparison is wall-time matched.
#
# Usage:
#   BUDGET=300 MEMO=26 EXACT_BUDGET=200000 EXACT_RETRIES=2 ./dfpn_hybrid_probe.sh
set -euo pipefail

D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-300}
MEMO=${MEMO:-26}
EXACT_BUDGET=${EXACT_BUDGET:-200000}
EXACT_RETRIES=${EXACT_RETRIES:-2}
OUT="$L/hybrid_probe"
mkdir -p "$OUT"

run_arm(){
  local legal="$1"
  local tag="L$legal"
  rm -f "$OUT/$tag.log" "$OUT/$tag.csv"
  "$D" --n=11 --reps --only=60 --memo="$MEMO" --budget="$BUDGET" \
    --exact-legal="$legal" --exact-budget="$EXACT_BUDGET" \
    --exact-retries="$EXACT_RETRIES" \
    --log="$OUT/$tag.log" --csv="$OUT/$tag.csv" \
    > /dev/null 2>&1
}

pids=()
for legal in 0 4 6 8; do
  run_arm "$legal" &
  pids+=("$!")
done

rc=0
for p in "${pids[@]}"; do
  wait "$p" || rc=1
done

echo "legal,outcome,root_pn,root_dn,expansions,solved,exact_calls,exact_nodes,exact_abort,exact_win,exact_loss,exact_stores"
for legal in 0 4 6 8; do
  tag="L$legal"
  if grep -q '^\[done\]' "$OUT/$tag.log" 2>/dev/null; then
    line=$(grep '^\[done\]' "$OUT/$tag.log" | tail -1)
    outcome=$(printf '%s\n' "$line" | sed -n 's/.*] \(WIN\|LOSS\).*/\1/p')
  else
    line=$(grep 'TIMEOUT' "$OUT/$tag.csv" | tail -1)
    outcome=TIMEOUT
  fi
  python3 - "$legal" "$outcome" "$line" <<'PY'
import re,sys
legal,outcome,line=sys.argv[1:4]
def get(k, default="-"):
    m=re.search(r'\b'+re.escape(k)+r'=([^ ]+)', line)
    return m.group(1) if m else default
print(",".join([
    legal,outcome,get("root_pn"),get("root_dn"),get("expansions"),
    get("solved"),get("exact_calls"),get("exact_nodes"),get("exact_abort"),
    get("exact_win"),get("exact_loss"),get("exact_stores")
]))
PY
done

exit "$rc"
