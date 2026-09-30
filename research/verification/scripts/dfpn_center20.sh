#!/usr/bin/env bash
# Screen all 20 D4-distinct second replies after the 11x11 center move v=60.
#
# Goal:
#   Root {60} is an AND node for the proposition "the original first player wins".
#   Proving center requires ALL 20 two-stone children {60,r} to be WIN (pn=0).
#   Refuting center requires ONE child to be LOSS (dn=0).
#
# Every reply is run in a FRESH PROCESS with a FRESH TT so difficulty is
# comparable and no sibling can inherit transposition work from another run.
#
# Usage:
#   BUDGET=300 MEMO=26 ./research/verification/scripts/dfpn_center20.sh
#
# Output:
#   /mnt/d/ghq/build11/logs/center20/r<R>.log
#   /mnt/d/ghq/build11/logs/center20/r<R>.csv
#
# The 20 representatives below are the D4 orbits of the 120 non-center points.
# They are mechanically the fundamental-domain representatives:
#   0,1,2,3,4,5,12,13,14,15,16,24,25,26,27,36,37,38,48,49
set -u

D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-300}
MEMO=${MEMO:-26}
OUT="$L/center20"
mkdir -p "$OUT"

replies=(0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49)

for r in "${replies[@]}"; do
  roots="$OUT/root-$r.csv"
  printf 'canonical_parent,move\n"60",%s\n' "$r" > "$roots"
  echo "=== center reply r=$r start $(date -u +%H:%M:%S) ==="
  "$D" --n=11 --memo="$MEMO" --budget="$BUDGET" \
       --roots-csv="$roots" \
       --log="$OUT/r$r.log" --csv="$OUT/r$r.csv" \
       > /dev/null 2>&1
  rc=$?
  echo "=== center reply r=$r rc=$rc ==="
done

echo CENTER20_DONE

win=0
loss=0
timeout=0
for r in "${replies[@]}"; do
  echo "--- reply=$r ---"
  if grep -q '^\[done\].* WIN ' "$OUT/r$r.log" 2>/dev/null; then
    win=$((win+1))
    grep '^\[done\]' "$OUT/r$r.log" | tail -1
  elif grep -q '^\[done\].* LOSS ' "$OUT/r$r.log" 2>/dev/null; then
    loss=$((loss+1))
    grep '^\[done\]' "$OUT/r$r.log" | tail -1
  else
    timeout=$((timeout+1))
    grep -hE 'TIMEOUT' "$OUT/r$r.csv" 2>/dev/null | tail -1 || true
    grep -h '^\[hb\]' "$OUT/r$r.log" 2>/dev/null | tail -1 || true
  fi
done

echo "SUMMARY WIN=$win LOSS=$loss TIMEOUT=$timeout TOTAL=${#replies[@]}"
if [ "$loss" -gt 0 ]; then
  echo "CENTER_REFUTED: at least one second reply is LOSS for the original first-player proposition."
elif [ "$win" -eq 20 ]; then
  echo "CENTER_PROVED: all 20 D4-distinct second replies are WIN."
else
  echo "CENTER_UNRESOLVED"
fi
