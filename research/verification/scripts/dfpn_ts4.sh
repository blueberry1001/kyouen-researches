#!/usr/bin/env bash
# 4 first moves, 10 min each, fresh process + fresh TT, persistent logs.
# Validates new heartbeat series end to end on 11x11.
set -u
D=/mnt/d/ghq/build11/dfpn
L=/mnt/d/ghq/build11/logs
mkdir -p "$L"
for v in 60 0 5 13; do
  echo "=== probe v=$v start $(date -u +%H:%M:%S) ==="
  "$D" --n=11 --reps --memo=26 --only="$v" --budget=600 \
       --log="$L/ts-v$v.log" --csv="$L/ts-v$v.csv" > /dev/null 2>&1
  echo "=== probe v=$v rc=$? ==="
done
echo TS4_DONE
for v in 60 0 5 13; do
  echo "--- v=$v hb series ---"
  grep -h '^\[hb\]' "$L/ts-v$v.log" || echo NOHB
  echo "--- v=$v final ---"
  tail -2 "$L/ts-v$v.log"
done
