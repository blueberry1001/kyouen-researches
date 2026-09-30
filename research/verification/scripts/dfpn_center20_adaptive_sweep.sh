#!/bin/bash
# Phase 8: re-sweep the 20 center replies with the adaptive s5 budget
# that Phase 7 validated, to see whether any two-stone root now closes.
#
# Context: N11-DFPN-CENTER20-HYBRID-SWEEP.md recorded WIN 0 / LOSS 0 /
# TIMEOUT 20 for both L44 and L56. Phase 7 showed that at L72 with a
# 5M s5 budget the s5 frontier collapses, so the question here is
# whether the same budget helps the two-stone roots.
#
# Parity (verified, see dfpn_center20_sweep.sh): move 60 is the original
# first player's, so a two-stone root {60,r} is an OR node with the
# original first player to move. Child WIN = first player wins (pn=0),
# child LOSS = second player wins (dn=0). At the AND node {60}, proving
# needs all 20 WIN and refuting needs any one LOSS.
#
# pn is not a distance; these are interim numbers only.
D=/mnt/d/ghq/build11/dfpn
OUT=/mnt/d/ghq/build11/logs/c20_adaptive
mkdir -p "$OUT"
MEMO=${MEMO:-26}
BUDGET=${BUDGET:-60}
ROUNDS=${ROUNDS:-1}
LEVEL=${LEVEL:-72}
SB5=${SB5:-5000000}

# The solver opens --log/--csv in APPEND mode; truncate first or stale
# entries from an earlier run get counted as part of this one.
rm -f "$OUT"/c20*.csv "$OUT"/c20*.log

csv="$OUT/roots.csv"
{
  echo 'canonical_parent,move'
  for _ in $(seq 1 "$ROUNDS"); do
    for r in 0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49; do
      printf '"60",%s\n' "$r"
    done
  done
} > "$csv"

echo "=== center20 adaptive sweep L$LEVEL s5=$SB5 budget=${BUDGET}s/root rounds=$ROUNDS memo=$MEMO ==="
echo "=== wall ~ $(( 20 * ROUNDS * BUDGET / 60 )) min ==="
"$D" --n=11 --memo="$MEMO" --budget="$BUDGET" \
     --roots-csv="$csv" \
     --exact-legal="$LEVEL" --exact-retries=1 --exact-publish=root \
     --exact-budget=200000 --exact-budget-by-stones="5:$SB5,6:200000" \
     --log="$OUT/c20.log" --csv="$OUT/c20.csv" > /dev/null 2>&1
echo "=== solver exited rc=$? ==="

win=0; loss=0; timeout=0
for r in 0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49; do
  if grep -q "^\[done\].*roots{60,$r}.* WIN " "$OUT/c20.log" 2>/dev/null; then
    win=$((win+1)); echo "r=$r WIN  $(grep "roots{60,$r}" "$OUT/c20.log" | grep '^\[done\]' | tail -1)"
  elif grep -q "^\[done\].*roots{60,$r}.* LOSS " "$OUT/c20.log" 2>/dev/null; then
    loss=$((loss+1)); echo "r=$r LOSS $(grep "roots{60,$r}" "$OUT/c20.log" | grep '^\[done\]' | tail -1)"
  else
    timeout=$((timeout+1))
  fi
done
echo "SUMMARY WIN=$win LOSS=$loss TIMEOUT=$timeout TOTAL=20"
grep -h '^\[exact-depth\]' "$OUT/c20.log" | tail -1
echo "--- last TIMEOUT row:"
grep -hE 'TIMEOUT' "$OUT/c20.csv" | tail -1