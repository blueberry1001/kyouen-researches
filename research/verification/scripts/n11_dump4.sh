#!/usr/bin/env bash
for v in 60 0 5 13; do
  echo "--- v=$v timeout line ---"
  grep -h timeout "/tmp/n11-v$v.log" || echo NOTIMEOUT
  echo "--- v=$v depth line ---"
  grep -h '^\[depth\]' "/tmp/n11-v$v.log" | tail -1 || echo NODEPTH
done
echo ALLDONE
