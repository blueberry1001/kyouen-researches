#!/bin/bash
# Capture the FIRST s5 oracle query the quantified search actually
# makes, then report its identity. This is the measurement that was
# missing: the earlier run reported queries=0 and stalled, but that line
# was printed BEFORE the query and never refreshed, so it said nothing
# about whether a query had started.
#
# With [q-start] / [q-done] tracing the first query's canonical key,
# legal count and cost are directly observable, and the key can then be
# replayed on its own via --exact-replay.
cd /mnt/d/ghq/build11 || exit 1
OUT=logs/qcap
mkdir -p "$OUT"
rm -f "$OUT"/first.txt "$OUT"/first_rec.csv

timeout "${QS_TIMEOUT:-420}" ./dfpn --n=11 --memo=24 \
  --quant-first=60 --quant-replies="${REPLY:-0}" \
  --quant-budget="${QBUD:-20000000}" --quant-timeout=300 \
  > "$OUT/first.txt" 2>&1
echo "run rc=$?"

echo "--- first q-start / q-done pairs:"
grep -m 3 '^\[q-start\]' "$OUT/first.txt"
grep -m 3 '^\[q-done\]'  "$OUT/first.txt"
echo
echo "--- counts:"
echo "  q-start lines: $(grep -c '^\[q-start\]' "$OUT/first.txt")"
echo "  q-done  lines: $(grep -c '^\[q-done\]'  "$OUT/first.txt")"
echo "  last quant line:"
grep '^\[quant\]' "$OUT/first.txt" | tail -1
echo
echo "--- summary line (if reached):"
grep '^# SUMMARY' "$OUT/first.txt"

# Write the first query as a one-row record file so --exact-replay can
# be pointed straight at it. Record columns are
#   tag,seq,stones,key_lo,key_hi,legal,depth,is_or,retries,nodes,result
K=$(grep -m 1 '^\[q-start\]' "$OUT/first.txt" | sed -n 's/.*key=\([0-9]*\),\([0-9]*\).*/\1 \2/p')
if [ -n "$K" ]; then
  LO=$(echo "$K" | cut -d' ' -f1)
  HI=$(echo "$K" | cut -d' ' -f2)
  printf 'canonical_parent,move\n"5",0\n' > /dev/null
  echo "q,0,5,$LO,$HI,0,0,1,0,0,0" > "$OUT/first_rec.csv"
  echo
  echo "wrote $OUT/first_rec.csv for key lo=$LO hi=$HI"
else
  echo "no q-start captured"
fi