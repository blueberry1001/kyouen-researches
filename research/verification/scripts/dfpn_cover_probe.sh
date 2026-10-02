#!/bin/bash
# Which edges does the current cache already prove, and which vertex
# pairs does that cover? This is the structural view of the quantified
# search: a proved LOSS edge on {a,b} refutes BOTH third moves a and b.
cd /mnt/d/ghq/build11 || exit 1
CACHE=logs/s5cache/s5_verdicts.csv
./dfpn --n=11 --memo=24 --cover --cover-first=60 --cover-r2=0 \
  --s5-cache="$CACHE" > logs/s5cache/cover.txt 2>&1
echo "--- summary:"
grep -E '^# (LOSS-edge|edges|COVER|ALL|uncovered)' logs/s5cache/cover.txt | head -4
echo "--- edges the cache proves:"
grep '^cover,' logs/s5cache/cover.txt