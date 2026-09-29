#!/usr/bin/env bash
L=/mnt/d/ghq/build11/logs
for v in 60 0 5 13; do
  echo "=== v=$v csv ==="
  cat "$L/dfpn-v$v.csv" 2>/dev/null || echo NOCSV
  echo "=== v=$v hb-tail ==="
  grep -h '^\[hb\]' "$L/dfpn-v$v.log" 2>/dev/null | tail -6 || echo NOHB
done
echo CSVDUMP_DONE
