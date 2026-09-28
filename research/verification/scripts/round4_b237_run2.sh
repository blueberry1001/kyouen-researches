#!/usr/bin/env bash
# Round4 worker part 2: deletion / sub / q5 / ext / greedy / disagree
# Runs concurrently with round4_b237_run.sh (which is doing the MC jobs).
set -u
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
SC=$REPO/research/verification/scripts
OUT=$REPO/research/verification/round4_b237
mkdir -p "$OUT"
cd "$SC"
g++ -O2 -march=native -std=c++20 -o /tmp/r4b237b round4_b168.cpp 2>>"$OUT/build2.log" \
  || { echo "BUILD FAILED"; exit 1; }
echo "BUILD OK (part2)"

# B201 / B202 / B203 / B205 : one-point deletion, n=3,4,5
for n in 3 4 5; do
  echo "### del1 $n"
  timeout 1500 /tmp/r4b237b del1 $n >>"$OUT/del.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

# B206 / B207 / B209 / B210 : two-point deletion on 4x4
echo "### del2 4"
timeout 1500 /tmp/r4b237b del2 4 >>"$OUT/del2.jsonl" 2>>"$OUT/err.log"
echo "rc=$?"

# B177 : sub-board f-vectors
for wh in "2 8" "1 16" "3 5" "4 4"; do
  set -- $wh
  echo "### sub $1 x $2"
  timeout 400 /tmp/r4b237b sub $1 $2 >>"$OUT/sub.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

# B225 : q=5 concyclic rule
for n in 3 4; do
  echo "### q5 $n"
  timeout 600 /tmp/r4b237b q5 $n >>"$OUT/q5.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

echo "PART2 DONE"
