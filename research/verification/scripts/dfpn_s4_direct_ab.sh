#!/bin/bash
# A/B on ONE fixed 4-stone position: direct exact solve vs enumerating
# the fifth moves through the s5 oracle.
#
# The two are equivalent questions -- an s4 position is an OR node, so
# "exists m5 with WIN(s5)" is the same as solving s4 exactly -- but the
# direct solve gets the exact DFS child ordering and shares transpositions
# between the fifth moves inside a single search.
#
# The position is the one the quant search reaches first: reply r2=0,
# third move 1, fourth move = the lowest legal index.
cd /mnt/d/ghq/build11 || exit 1
OUT=logs/s4ab
mkdir -p "$OUT"

R2=${R2:-0}
M3=${M3:-1}
# lowest legal fourth reply for that three-stone position
M4=${M4:-0}
BUD=${BUD:-20000000}
MEMO=${MEMO:-24}

rm -f "$OUT/ab.txt"
timeout "${TMO:-2400}" ./dfpn --n=11 --memo="$MEMO" \
  --quant-first=60 --s4-ab="$R2,$M3,$M4" --s4-ab-budget="$BUD" \
  > "$OUT/ab.txt" 2>&1
echo "rc=$?"
grep '^#' "$OUT/ab.txt" | head -3
grep -E '^(direct|enum_m5),' "$OUT/ab.txt"