#!/usr/bin/env bash
# Round4 worker: the 23 previously-unwritten IDs (B177,B178,B180,B188,B189,B190,B193,
# B197..B203,B205..B210,B223,B224,B225)
set -u
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
SC=$REPO/research/verification/scripts
OUT=$REPO/research/verification/round4_b237
mkdir -p "$OUT"
cd "$SC"
g++ -O2 -march=native -std=c++20 -o /tmp/r4b237 round4_b168.cpp 2>"$OUT/build.log" \
  || { echo "BUILD FAILED"; cat "$OUT/build.log"; exit 1; }
echo "BUILD OK"

# --- cheap / high value first -----------------------------------------------
# B189 + B188 + B184 + B181 + B182 : random-greedy Monte Carlo
for n in 4 5 6 7 8; do
  echo "### mc $n"
  timeout 900 /tmp/r4b237 mc $n 200000 >>"$OUT/mc.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

# B177 : sub-board f-vectors (same point count, different board shape)
for wh in "2 8" "1 16" "3 5" "2 9" "1 18" "4 4"; do
  set -- $wh
  echo "### sub $1 x $2"
  timeout 600 /tmp/r4b237 sub $1 $2 >>"$OUT/sub.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

# B201 / B202 / B203 : one-point deletion
for n in 3 4 5; do
  echo "### del1 $n"
  timeout 1800 /tmp/r4b237 del1 $n >>"$OUT/del.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

# B225 : q-point concyclic rule (q=5)
for n in 3 4; do
  echo "### q5 $n"
  timeout 900 /tmp/r4b237 q5 $n >>"$OUT/q5.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

# B223 : standard vs circle-only P/N disagreement, n=5
echo "### disagree 0 5 5 1 5 5"
timeout 1800 /tmp/r4b237 disagree 0 5 5 1 5 5 >>"$OUT/dis.jsonl" 2>>"$OUT/err.log"
echo "rc=$?"

# B208 : n x n plus one external point
for n in 2 3; do
  echo "### ext $n"
  timeout 1800 /tmp/r4b237 ext $n >>"$OUT/ext.jsonl" 2>>"$OUT/err.log"
  echo "rc=$?"
done

# B224 : greedy down-search for a small forbidden family reproducing W
echo "### greedy 4 4000"
timeout 1200 /tmp/r4b237 greedy 4 4000 >>"$OUT/greedy.jsonl" 2>>"$OUT/err.log"
echo "rc=$?"

echo "ALL DONE"
