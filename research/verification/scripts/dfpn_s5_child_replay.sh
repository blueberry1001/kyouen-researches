#!/bin/bash
# Classify all 115 fifth moves by COLD exact replay.
#
# Each position gets a fresh solver and a fresh table (the replay driver
# already builds a new DfPn per row and caps the memo at 2^22), so no
# transposition work is shared between positions. That is the whole
# point: the earlier "deep TT reuse" numbers came from a warm table and
# say nothing about how hard each position is on its own.
#
# Stage 1: every child at 5M. Stage 2 is run separately for the
# UNKNOWN ones only.
cd /mnt/d/ghq/build11 || exit 1
OUT=logs/s5dist
IN=${IN:-$OUT/replay_in.csv}
B=${B:-5000000}
TAG=${TAG:-b5}
MEMO=${MEMO:-22}

rm -f "$OUT/replay_$TAG.csv"
timeout 14000 ./dfpn --n=11 --memo=$MEMO \
  --exact-replay="$IN" --only=5 --exact-replay-budget="$B" \
  --csv="$OUT/replay_$TAG.csv" > /dev/null 2>&1
echo "rc=$? rows=$(grep -c '^replay,' "$OUT/replay_$TAG.csv")"
awk -F, '/^replay,/ {
    if($7==0) u++; else if($7==1) w++; else l++
  } END {printf "WIN=%d LOSS=%d UNKNOWN=%d\n", w+0, l+0, u+0}' "$OUT/replay_$TAG.csv"