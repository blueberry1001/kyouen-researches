#!/usr/bin/env bash
# Eviction stress: tiny memo forces massive open eviction; results must not change.
set -u
D=/mnt/d/ghq/build11/dfpn
L=/mnt/d/ghq/build11/xcheck-logs
for pow in 20 16 12; do
  echo "=== n=6 memo=$pow ==="
  $D --n=6 --memo=$pow --budget=300 --roots-csv=$L/in6.csv \
     --log=$L/evict6-p$pow.log --csv=$L/evict6-p$pow.csv >/dev/null 2>&1
  echo "rc=$?"
  grep -hE '^\[done\]' $L/evict6-p$pow.log | head -20
  echo "=== n=7 memo=$pow ==="
  $D --n=7 --memo=$pow --budget=300 --roots-csv=$L/in7.csv \
     --log=$L/evict7-p$pow.log --csv=$L/evict7-p$pow.csv >/dev/null 2>&1
  echo "rc=$?"
  grep -hE '^\[done\]' $L/evict7-p$pow.log | head -22
done
echo EVICT_DONE
