#!/usr/bin/env bash
# df-pn 4-point comparison: same 4 first moves as the DFS matrix.
# Each: fresh process, fresh TT, 900 s budget, file logging.
# Success criterion is NOT solving: it is pushing root pn/dn one-sidedly
# with clearly fewer expansions than DFS in the same 15 min.
set -u
D=/mnt/d/ghq/build11/dfpn
for v in 60 0 5 13; do
  echo "=== dfpn probe v=$v start $(date -u +%H:%M:%S) ==="
  "$D" --n=11 --reps --memo=26 --only="$v" --budget=900 \
       --log="/tmp/dfpn-v$v.log" --csv="/tmp/dfpn-v$v.csv" > /dev/null 2>&1
  echo "=== dfpn probe v=$v rc=$? ==="
done
echo DFPN4_DONE
for v in 60 0 5 13; do
  echo "--- v=$v tail ---"
  tail -4 "/tmp/dfpn-v$v.log" || echo NOLOG
done
