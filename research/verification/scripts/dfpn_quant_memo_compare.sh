#!/bin/bash
# Reply 0 at memo=2^24 and 2^26, identical in every other respect.
#
# The 2^24 run filled the table to 16,676,488 / 16,777,216 = 99.4% by
# query 5, after which query 6 was free and query 7 hung. If that was
# TABLE SATURATION rather than position difficulty, then at 2^26 -- where
# 16.7M entries is only about 25% of capacity -- the queries should
# keep completing at a few million nodes each instead of degrading.
#
# Run sequentially: each holds a large table and 19 GB is not worth
# risking with two at once.
cd /mnt/d/ghq/build11 || exit 1
OUT=logs/qmemo
mkdir -p "$OUT"

run() {  # tag, memo_power
  local tag=$1 memo=$2
  rm -f "$OUT/$tag.txt"
  echo "=== $tag (memo=2^$memo) ==="
  ./dfpn --n=11 --memo="$memo" --quant-first=60 --quant-replies=0 \
    --quant-budget=20000000 --quant-timeout="${QTO:-1500}" \
    > "$OUT/$tag.txt" 2>&1
  echo "  queries completed: $(grep -c '^\[q-done\]' "$OUT/$tag.txt")"
  grep '^# SUMMARY' "$OUT/$tag.txt" | sed 's/^/  /'
}

run m24 24
run m26 26
echo QMEMO_DONE