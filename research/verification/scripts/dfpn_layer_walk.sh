#!/bin/bash
# Walk the frontier upward one layer at a time, now that per-layer
# gating works. s5 (10M worst), s6 (665k worst) and s7 (222k worst) all
# close, and the worst case has been falling as the stone count rises.
# If that trend continues, the deep layers are cheap and the bottleneck
# is entirely in s5.
#
# Each layer is opened at its legal bound 121-k with the others shut off,
# so the frontier is exactly one layer deep.
D=/mnt/d/ghq/build11/dfpn
OUT=/mnt/d/ghq/build11/logs/layergate
mkdir -p "$OUT"

sweep_layer() {  # stones, budget
  local st=$1 b=$2
  local lim=$(( 121 - st ))
  local tag="L${st}_b${b}"
  rm -f "$OUT/$tag.csv" "$OUT/$tag.log"
  # Every other stone count shut off with 0; this one open at 121-st.
  local spec
  spec=$(for k in 1 2 3 4 5 6 7 8 9 10 11 12 13 14; do
           if [ "$k" -eq "$st" ]; then echo -n "$k:$lim,"; else echo -n "$k:0,"; fi
         done)
  spec=${spec%,}
  "$D" --n=11 --reps --only=60 --memo=24 --budget=60 \
       --exact-legal=0 --exact-legal-by-stones="$spec" \
       --exact-budget="$b" --exact-retries=1 --exact-publish=root \
       --exact-record --csv="$OUT/$tag.csv" --log="$OUT/$tag.log" >/dev/null 2>&1
  local n
  n=$(grep -v '^#' "$OUT/$tag.csv" 2>/dev/null | wc -l)
  local w l u
  w=$(grep -v '^#' "$OUT/$tag.csv" 2>/dev/null | awk -F, '$11==1' | wc -l)
  l=$(grep -v '^#' "$OUT/$tag.csv" 2>/dev/null | awk -F, '$11==2' | wc -l)
  u=$(grep -v '^#' "$OUT/$tag.csv" 2>/dev/null | awk -F, '$11==0' | wc -l)
  printf '  s%-3d (L<=%-3d budget=%-8s) handoffs=%-5s WIN=%-5s LOSS=%-5s UNKNOWN=%-5s\n' \
    "$st" "$lim" "$b" "$n" "$w" "$l" "$u"
}

for S in 8 9 10 11 12; do
  echo "=== layer s$S ==="
  sweep_layer "$S" 200000
done
echo LAYERWALK_DONE