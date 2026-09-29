#!/usr/bin/env bash
for v in 60 0 5 13; do
  echo "=== v=$v ==="
  grep -hE 'TIMEOUT|^\[hb\]' "/tmp/dfpn-v$v.log" | tail -4 || echo NOLOG
done
echo DUMP2_DONE
