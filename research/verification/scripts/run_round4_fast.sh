#!/bin/bash
# Fast jobs for round4 b092-b127.
set -u
V=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
rm -f "$V/round4_b092.json"
for j in sat shape b110 defo; do
  echo "===== job $j ====="
  /tmp/r4 "$j" || echo "job $j FAILED rc=$?"
done
echo "===== JSON ====="
cat "$V/round4_b092.json"
