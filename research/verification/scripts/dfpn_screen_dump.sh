#!/usr/bin/env bash
L=/mnt/d/ghq/build11/logs/screen21
for v in 60 0 1 12 2 13 24 3 14 25 36 4 15 26 37 48 5 16 27 38 49; do
  echo "=== v=$v ==="
  cat "$L/v$v.csv" 2>/dev/null || echo NOCSV
done
echo SCREENDUMP_DONE
