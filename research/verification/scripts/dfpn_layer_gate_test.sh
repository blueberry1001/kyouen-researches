#!/bin/bash
# Does --exact-legal-by-stones actually isolate a layer?
#
# The claim in N11-DFPN-FRONTIER-LAYERS.md is that the single
# --exact-legal cannot separate s7 from s5/s6, but a per-stone-count
# threshold can. This checks that directly by running the center root
# with s5 and s6 disabled and s7 opened, and confirming that only s7
# handoffs appear.
#
# A control arm keeps the global threshold so the difference is
# attributable to the per-stone gate and not to the budget.
cd /mnt/d/ghq/build11 || exit 1
D=/mnt/d/ghq/build11/dfpn
OUT=logs/layergate
mkdir -p "$OUT"

run() {  # tag, extra args
  local tag=$1; shift
  rm -f "$OUT/$tag.csv" "$OUT/$tag.log"
  "$D" --n=11 --reps --only=60 --memo=24 --budget=60 \
       --exact-retries=1 --exact-publish=root \
       --exact-budget=200000 \
       --exact-record --csv="$OUT/$tag.csv" --log="$OUT/$tag.log" \
       "$@" > /dev/null 2>&1
  echo "=== $tag ==="
  echo "  stone counts handed off:"
  grep -v '^#' "$OUT/$tag.csv" 2>/dev/null | cut -d, -f3 | sort -n | uniq -c \
    | sed 's/^/    /' || echo "    (none)"
  echo "  histogram:"
  grep -h '^\[exact-depth\]' "$OUT/$tag.log" 2>/dev/null | tail -1 | sed 's/^/    /'
}

# Control: the highest global threshold that still produces s5/s6.
run control --exact-legal=80

# Per-stone gate: s5 and s6 shut off, s7+ open at their legal bound.
# A k-stone position has at most 121-k legal moves, so 7 -> 114.
run s7only --exact-legal=0 --exact-legal-by-stones=7:114,8:113,9:112,10:111,11:110,12:109

echo LAYERGATE_DONE