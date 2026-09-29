#!/usr/bin/env bash
# 4-probe comparison: center 60, corner 0, edge-center 5, generic 13.
# Each: fresh process, fresh memo=27, 900 s budget, file logging.
set -u
S=/mnt/d/ghq/build11/s11
for v in 60 0 5 13; do
  echo "=== probe v=$v start $(date -u +%H:%M:%S) ==="
  "$S" --reps --memo=27 --only="$v" --budget=900 \
       --log="/tmp/n11-v$v.log" --csv="/tmp/n11-v$v.csv" > /dev/null 2>&1
  echo "=== probe v=$v rc=$? ==="
done
echo ALLDONE
for v in 60 0 5 13; do
  echo "--- v=$v timeout line ---"
  grep -h timeout "/tmp/n11-v$v.log" || echo NOTIMEOUT
  echo "--- v=$v depth line ---"
  grep -h '^\[depth\]' "/tmp/n11-v$v.log" | tail -1 || echo NODEPTH
done
