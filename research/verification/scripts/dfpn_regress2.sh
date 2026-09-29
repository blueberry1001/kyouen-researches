#!/usr/bin/env bash
# df-pn regression with per-n timeout capture.
set -u
D=/mnt/d/ghq/build11/dfpn
for n in 4 5 6 7; do
  echo "=== n=$n ==="
  "$D" --n="$n" --empty --memo=24 --budget=300 \
       --log="/tmp/rg$n.log" --csv="/tmp/rg$n.csv"
  echo "rc=$?"
  tail -2 "/tmp/rg$n.log"
done
echo REGRESSION_DONE
