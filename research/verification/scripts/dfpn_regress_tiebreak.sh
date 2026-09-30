#!/bin/bash
# Regression for BOTH tie-break modes. The tie-break only orders
# equally-bounded children, so every proven outcome must be
# IDENTICAL between asc and desc. Any divergence is a bug.
set -e
D=/mnt/d/ghq/build11/dfpn
for n in 4 5 6 7; do
  for mode in asc desc; do
    flag=""
    if [ "$mode" = "desc" ]; then flag="--tiebreak=desc"; fi
    echo "=== n=$n $mode ==="
    # NO 2>/dev/null: attach_log defaults to cerr, so the [done] line
    # goes to stderr. Redirecting stderr discards the result.
    $D --n=$n --empty --memo=24 $flag 2>&1 | grep -E '^\[done\]|^# done'
  done
done
echo REGRESS2_BOTH_DONE
