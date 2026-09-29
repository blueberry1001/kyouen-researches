#!/usr/bin/env bash
for v in 60 0 5 13; do
  echo "--- v=$v tail ---"
  tail -6 "/tmp/dfpn-v$v.log" || echo NOLOG
done
echo DUMP_DONE
