#!/usr/bin/env bash
# TT capacity check on v=60: memo 25 vs 26, 5 min each.
set -u
D=/mnt/d/ghq/build11/dfpn
L=/mnt/d/ghq/build11/logs
mkdir -p "$L/ttcap"
for p in 25 26; do
  echo "=== memo=$p start $(date -u +%H:%M:%S) ==="
  /usr/bin/time -v "$D" --n=11 --reps --memo=$p --only=60 --budget=300 \
       --log="$L/ttcap/p$p.log" --csv="$L/ttcap/p$p.csv" 2>"$L/ttcap/time-p$p.txt" > /dev/null 2>&1
  echo "=== memo=$p rc=$? ==="
done
echo TTCAP_DONE
for p in 25 26; do
  echo "--- memo=$p csv ---"
  cat "$L/ttcap/p$p.csv" 2>/dev/null || echo NOCSV
  echo "--- memo=$p maxRSS ---"
  grep -h "Maximum resident" "$L/ttcap/time-p$p.txt" 2>/dev/null || echo NOTIME
done
