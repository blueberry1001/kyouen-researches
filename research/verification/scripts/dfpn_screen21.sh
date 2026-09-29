#!/usr/bin/env bash
# 21-orbit screening: all D4-distinct one-stone first moves, 5 min each.
# Fresh process + fresh TT per orbit, memo=26. Sequential (1 proc at a time)
# to keep TT pressure and timing comparable. ~105 min total.
set -u
D=/mnt/d/ghq/build11/dfpn
L=/mnt/d/ghq/build11/logs
mkdir -p "$L/screen21"
# 21 D4 orbits for 11x11: fundamental domain {(x,y): 0<=x<=5, 0<=y<=x}
# v = y*11+x. Center 60 first, then the rest in solver order.
for v in 60 0 1 12 2 13 24 3 14 25 36 4 15 26 37 48 5 16 27 38 49; do
  echo "=== screen v=$v start $(date -u +%H:%M:%S) ==="
  "$D" --n=11 --reps --memo=26 --only="$v" --budget=300 \
       --log="$L/screen21/v$v.log" --csv="$L/screen21/v$v.csv" > /dev/null 2>&1
  echo "=== screen v=$v rc=$? ==="
done
echo SCREEN21_DONE
for v in 60 0 1 12 2 13 24 3 14 25 36 4 15 26 37 48 5 16 27 38 49; do
  echo "--- v=$v ---"
  grep -hE 'TIMEOUT|^\[done\]' "$L/screen21/v$v.csv" 2>/dev/null || echo NOCSV
  grep -h '^\[hb\]' "$L/screen21/v$v.log" 2>/dev/null | tail -2 || echo NOHB
done
