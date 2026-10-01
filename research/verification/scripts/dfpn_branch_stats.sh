#!/bin/bash
# Long reply-0 run with branch-level telemetry.
#
# The feasibility question is entirely about short-circuit rates, so
# this records per query: canonical key, result, nodes, ms, and the
# main-PnTT hit/miss/growth deltas. With publish=ALL the exact DFS
# publishes its interior solved states, so a later query overlapping an
# earlier one can be much cheaper even when the oracle root cache never
# hits -- which is why nodes-per-query, and not the root cache ratio,
# is the reuse signal that matters.
cd /mnt/d/ghq/build11 || exit 1
OUT=logs/qbranch
mkdir -p "$OUT"
rm -f "$OUT"/r0.txt

REPLY=${REPLY:-0}
QTO=${QTO:-1800}
QBUD=${QBUD:-20000000}

./dfpn --n=11 --memo=24 --quant-first=60 \
  --quant-replies="$REPLY" --quant-budget="$QBUD" --quant-timeout="$QTO" \
  > "$OUT/r$REPLY.txt" 2>&1
echo "rc=$?"
echo "queries done : $(grep -c '^\[q-done\]' "$OUT/r$REPLY.txt")"
echo "result rows  : $(grep -c '^quant,' "$OUT/r$REPLY.txt")"
grep '^quant,' "$OUT/r$REPLY.txt"
grep '^# SUMMARY' "$OUT/r$REPLY.txt"
grep '^# quantified' "$OUT/r$REPLY.txt"