#!/usr/bin/env bash
# Long runs on top candidates from the 21-orbit screen.
# v=60 (center, best pn/dn), v=27 (2nd pn), v=12 (most solved).
# 1 hour each, sequential. ~3 h total.
set -u
D=/mnt/d/ghq/build11/dfpn
L=/mnt/d/ghq/build11/logs
mkdir -p "$L/longrun"
for v in 60 27 12; do
  echo "=== longrun v=$v start $(date -u +%H:%M:%S) ==="
  "$D" --n=11 --reps --memo=26 --only="$v" --budget=3600 \
       --log="$L/longrun/v$v.log" --csv="$L/longrun/v$v.csv" > /dev/null 2>&1
  echo "=== longrun v=$v rc=$? ==="
done
echo LONGRUN_DONE
for v in 60 27 12; do
  echo "--- v=$v csv ---"
  cat "$L/longrun/v$v.csv" 2>/dev/null || echo NOCSV
  echo "--- v=$v hb-tail ---"
  grep -h '^\[hb\]' "$L/longrun/v$v.log" 2>/dev/null | tail -4 || echo NOHB
done
