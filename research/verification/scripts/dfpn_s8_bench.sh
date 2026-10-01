#!/bin/bash
# s8 looked extremely favourable (1924 WIN / 79 LOSS / 0 abort at a
# 200k budget). Confirm the count with the same per-position cold replay
# used for s5 and s7, so the WIN/LOSS split is not an artifact of the
# in-search TT state.
cd /mnt/d/ghq/build11 || exit 1
D=/mnt/d/ghq/build11/dfpn
OUT=logs/layergate
REC="$OUT/L8_b200000.csv"
[ -f "$REC" ] || { echo "no s8 record"; exit 1; }
grep -v '^#' "$REC" > "$OUT/s8roots.csv"
echo "s8 roots: $(wc -l < "$OUT/s8roots.csv")"

for B in 200000 2000000; do
  out="$OUT/s8b$B.csv"
  rm -f "$out"
  echo "=== s8 budget=$B ==="
  timeout 2400 "$D" --n=11 --memo=24 --exact-replay="$OUT/s8roots.csv" \
    --only=8 --exact-replay-budget="$B" --csv="$out" >/dev/null 2>&1
  rows=$(grep -c '^replay,' "$out" 2>/dev/null || echo 0)
  echo "  rows=$rows"
  awk -F, '/^replay,/ {
      if($7==0) u++; else { s++; n+=$8; if($8<mn||mn==0)mn=$8; if($8>mx)mx=$8
                             if($7==1)w++; else if($7==2)l++ }
    } END {
      printf "  solved=%d (WIN=%d LOSS=%d) unknown=%d nodes=%d min=%d max=%d\n",
             s+0, w+0, l+0, u+0, n+0, mn+0, mx+0
    }' "$out"
done
echo S8_BENCH_DONE