#!/bin/bash
# Re-sweep the 20 center replies now that the layers are understood.
#
# What changed since the last sweep (N11-DFPN-CENTER20-ADAPTIVE.md):
#
#   layer   closes at   worst nodes   WIN / LOSS
#   s5      10,000,000   5,677,449    12 / 11
#   s6       1,000,000     665,057    43 / 0
#   s7       1,000,000     222,479    47 / 254
#   s8         200,000      67,804  1924 / 79
#
# s6, s7 and s8 all close well inside a 200k budget, so a single
# threshold at 72 was leaving the cheap layers unexploited while
# overfeeding s5. The gate is therefore opened per layer, each at the
# largest legal bound that still targets something useful, and the
# budget is set from the measured cost of that layer.
#
# Parity (verified): move 60 is the original first player's, so a
# two-stone root {60,r} has is_or(2)=true and the original first player
# is the maximizing side. Child WIN = first player wins (pn=0), child
# LOSS = second player wins (dn=0). At the AND node {60} proving needs
# all 20 WIN and refuting needs any one LOSS.
#
# pn is not a distance; these are interim numbers only.
D=/mnt/d/ghq/build11/dfpn
OUT=/mnt/d/ghq/build11/logs/c20_layers
mkdir -p "$OUT"
MEMO=${MEMO:-26}
BUDGET=${BUDGET:-60}
ROUNDS=${ROUNDS:-1}

# The solver appends to --log/--csv, so truncate first.
rm -f "$OUT"/c*.csv "$OUT"/c*.log

csv="$OUT/roots.csv"
{
  echo 'canonical_parent,move'
  for _ in $(seq 1 "$ROUNDS"); do
    for r in 0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49; do
      printf '"60",%s\n' "$r"
    done
  done
} > "$csv"

# Gate: open s5, s6, s7, s8 at their legal bounds, everything else off.
# Budget per layer from the measured worst case, with headroom.
GATE="5:116,6:115,7:114,8:113,9:0,10:0,11:0,12:0"
BUDGETS="5:20000000,6:1000000,7:1000000,8:200000"

echo "=== center20 layered sweep: budget=${BUDGET}s/root rounds=$ROUNDS memo=$MEMO ==="
echo "=== gate: $GATE ==="
echo "=== budgets: $BUDGETS ==="
echo "=== wall ~ $(( 20 * ROUNDS * BUDGET / 60 )) min ==="

"$D" --n=11 --memo="$MEMO" --budget="$BUDGET" \
     --roots-csv="$csv" \
     --exact-legal=0 --exact-legal-by-stones="$GATE" \
     --exact-budget=200000 --exact-budget-by-stones="$BUDGETS" \
     --exact-retries=1 --exact-publish=root \
     --log="$OUT/c.log" --csv="$OUT/c.csv" > /dev/null 2>&1
echo "=== solver exited rc=$? ==="

win=0; loss=0; timeout=0; missing=0
printf '%-5s %-8s %-10s %-10s\n' reply outcome root_pn root_dn
for r in 0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49; do
  line=$(grep -h "roots{60,$r}" "$OUT/c.csv" | tail -1)
  if [ -z "$line" ]; then
    printf '%-5s %-8s\n' "$r" MISSING; missing=$((missing+1)); continue
  fi
  if echo "$line" | grep -q ' WIN '; then oc=WIN; win=$((win+1))
  elif echo "$line" | grep -q ' LOSS '; then oc=LOSS; loss=$((loss+1))
  else oc=TIMEOUT; timeout=$((timeout+1)); fi
  pn=$(echo "$line" | grep -o 'root_pn=[0-9]*' | cut -d= -f2)
  dn=$(echo "$line" | grep -o 'root_dn=[0-9]*' | cut -d= -f2)
  printf '%-5s %-8s %-10s %-10s\n' "$r" "$oc" "$pn" "$dn"
done
echo "SUMMARY WIN=$win LOSS=$loss TIMEOUT=$timeout MISSING=$missing TOTAL=20"
echo "--- final exact-depth histogram (cumulative over the sweep):"
grep -h '^\[exact-depth\]' "$OUT/c.log" | tail -1
echo "--- totals:"
awk '/TIMEOUT reason|\] (WIN|LOSS) / {
      for(i=1;i<=NF;i++){
        if($i~/^expansions=/){split($i,a,"=");e+=a[2]}
        if($i~/^exact_nodes=/){split($i,b,"=");n+=b[2]}
        if($i~/^exact_abort=/){split($i,c,"=");ab+=c[2]}
      }} END {print "  expansions="e" exact_nodes="n" exact_abort="ab}' "$OUT/c.csv"