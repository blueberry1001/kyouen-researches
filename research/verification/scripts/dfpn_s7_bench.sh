#!/bin/bash
# The s7 layer is reachable and looks very different from s5/s6:
# mostly LOSS, and it closes at a 200k budget. Benchmark it properly.
cd /mnt/d/ghq/build11 || exit 1
D=/mnt/d/ghq/build11/dfpn
OUT=logs/layergate
REC="$OUT/s7only.csv"
[ -f "$REC" ] || { echo "no s7 record at $REC"; exit 1; }

# Extract just the s7 rows into a replayable record file.
grep -v '^#' "$REC" | awk -F, '$3==7' > "$OUT/s7roots.csv"
echo "s7 roots extracted: $(wc -l < "$OUT/s7roots.csv")"
echo
for B in 200000 1000000 5000000; do
  out="$OUT/s7b$B.csv"
  rm -f "$out"
  echo "=== s7 budget=$B ==="
  timeout 1800 "$D" --n=11 --memo=24 --exact-replay="$OUT/s7roots.csv" \
    --only=7 --exact-replay-budget="$B" --csv="$out" >/dev/null 2>&1
  rows=$(grep -c '^replay,' "$out" 2>/dev/null || echo 0)
  echo "  rows=$rows"
  awk -F, '/^replay,/ {
      if($7==0) u++; else { s++; n+=$8; if($8<mn||mn==0)mn=$8; if($8>mx)mx=$8
                             if($7==1)w++; else if($7==2)l++ }
    } END {
      printf "  solved=%d (WIN=%d LOSS=%d)  unknown=%d  nodes=%d min=%d max=%d\n",
             s+0, w+0, l+0, u+0, n+0, mn+0, mx+0
    }' "$out"
done
echo S7_BENCH_DONE