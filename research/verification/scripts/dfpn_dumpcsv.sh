#!/usr/bin/env bash
for v in 60 0 5 13; do
  echo "=== v=$v csv ==="
  cat "/tmp/dfpn-v$v.csv"
done
echo CSVDUMP_DONE
