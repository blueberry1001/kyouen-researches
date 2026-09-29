#!/usr/bin/env bash
L=/mnt/d/ghq/build11/logs
for v in 60 0 5 13; do
  echo "=== v=$v hb ==="
  grep -h '^\[hb\]' "$L/ts-v$v.log" || echo NOHB
  echo "=== v=$v final ==="
  tail -3 "$L/ts-v$v.log"
done
echo TS_DUMP_DONE
