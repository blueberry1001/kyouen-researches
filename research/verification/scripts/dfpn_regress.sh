#!/usr/bin/env bash
# df-pn regression: known empty-board outcomes.
# n=4 LOSS, n=5 WIN, n=6 WIN, n=7 LOSS.
set -u
D=/mnt/d/ghq/build11/dfpn
for n in 4 5 6 7; do
  echo "=== n=$n ==="
  "$D" --n="$n" --empty --memo=24 --budget=600 \
       --log="/tmp/dfpn-n$n.log" --csv="/tmp/dfpn-n$n.csv"
  echo "rc=$?"
  tail -3 "/tmp/dfpn-n$n.log"
done
echo REGRESSION_DONE
