#!/bin/bash
# Benchmark the exact frontier ABOVE s5.
#
# s5 turned out to be cheap: all 23 roots close by 10M nodes. The open
# question is what sits above it, because a two-stone root cannot close
# while BOTH of its children are still open, and s7+ is unexplored.
#
# The s6 handoff roots from the L72 record are the first place to look.
# `--only=` filters by stone count, so each layer is a separate pass.
#
# Budgets escalate until a layer stops closing. Node counts are NOT
# extrapolated to a solve time for the full board.
cd /mnt/d/ghq/build11 || exit 1
REC=logs/exactrec/L72.csv
LAYERS=${LAYERS:-"6 7 8 9 10"}
BUDGETS=${BUDGETS:-"200000 2000000 10000000 20000000"}

for L in $LAYERS; do
  n=$(grep -v '^#' "$REC" | awk -F, -v s="$L" '$3==s' | wc -l)
  echo "=== s$L: $n recorded handoffs ==="
  if [ "$n" -eq 0 ]; then
    echo "    (no s$L handoffs were recorded at L72; raise the threshold first)"
    continue
  fi
  for B in $BUDGETS; do
    out="l${L}_b$B.csv"
    rm -f "$out"
    timeout 1800 /mnt/d/ghq/build11/dfpn --n=11 --memo=24 \
      --exact-replay="$REC" --only="$L" --exact-replay-budget="$B" \
      --csv="$out" > /dev/null 2>&1
    rc=$?
    rows=$(grep -c '^replay,' "$out" 2>/dev/null || echo 0)
    awk -F, -v b="$B" -v l="$L" -v r="$rows" -v rc="$rc" '
      /^replay,/ {
        if ($7==0) u++; else { s++; n+=$8; if($8<mn||mn==0)mn=$8; if($8>mx)mx=$8 }
      }
      END {
        printf "    budget=%-9d rc=%s rows=%-4d solved=%-4d unknown=%-4d nodes=%d min=%d max=%d\n", \
               b, rc, r, s+0, u+0, n, mn, mx
      }' "$out" 2>/dev/null || echo "    budget=$B rc=$rc rows=$rows (no data)"
  done
done
echo LAYER_BENCH_DONE