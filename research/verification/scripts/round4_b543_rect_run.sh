#!/usr/bin/env bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
exec > >(tee /tmp/r4run2.log) 2>&1
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/r4rect round4_b543_rect.cpp
echo "BUILD_OK"
export OMP_NUM_THREADS=16
VER="$REPO/research/verification"
rm -f "$VER/round4_3row_part.json"
# 2-row: section 1 (Grundy m<=16) and section 2 with a sane m cap
/tmp/r4rect --out="$VER/round4_b543_rect.json" --sec=12 --m2=16 --m2c=60
echo "TWOROW_DONE"
# 3-row: one m per invocation so a slow m cannot kill the batch
for M in 3 4 5 6 7 8; do
  /tmp/r4rect --out=/tmp/r4_3row_$M.json --sec=3 --m3=$M
  echo "THREE_ROW_M${M}_DONE"
done
for M in 9 10; do
  /tmp/r4rect --out=/tmp/r4_3row_$M.json --sec=3 --m3=$M || echo "THREE_ROW_M${M}_TIMEOUT"
  echo "THREE_ROW_M${M}_ATTEMPTED"
done
echo "THREE_ROW_DONE"
# variants + row spacing + AP construction
/tmp/r4rect --out="$VER/round4_b543_rect_v.json" --sec=45 || true
echo "VARIANTS_DONE"
echo "ALL_DONE"
