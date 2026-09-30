#!/bin/bash
# Shared-TT sweep over the center's 20 second replies.
#
# GOAL
#   Measure how much the 20 sibling proofs help each other when they
#   share one transposition table, versus solving them in isolation.
#   The single process behind --roots-csv already reuses one DfPn
#   instance across roots, so the TT survives from one root to the
#   next. All 20 roots are written into ONE csv, repeated ROUNDS
#   times, so the solver sweeps the same 20 roots several times over.
#
#   The "knowledge one root gained helps the other 19" question is
#   then answered by comparing, per round, each root's pn against the
#   same root's pn when it ran alone with a fresh TT
#   (research/verification/N11-DFPN-CENTER20.md).
#
# POLARITY (verified; see N11-DFPN-CENTER20.md)
#   Move 60 is the original first player's. After it the original
#   second player is to move, so a two-stone root {60,r} has
#   is_or(2)=true and the original first player is the maximizing
#   side. Child WIN = first player wins (pn=0), child LOSS = second
#   player wins (dn=0). At the AND node {60}, proving needs all 20
#   children WIN and refuting needs any one LOSS.
#
#   NOTE ON READING pn: a proof number is NOT a countdown of work
#   remaining. Unexpanded leaves start at (1,1) and the number
#   normally GROWS as the search refines; it drops to 0 only when the
#   proof line closes. So a smaller pn means "cheaper on the proof
#   side by the current estimate", never "6,660 steps from done", and
#   these numbers must not be extrapolated in time.
#
# USAGE
#   BUDGET=30 ROUNDS=3 MEMO=26 ORDER=fwd  ./dfpn_center20_sweep.sh
#   BUDGET=30 ROUNDS=3 MEMO=26 ORDER=rev  ./dfpn_center20_sweep.sh
#
#   BUDGET is SECONDS PER ROOT (not per sweep), so one sweep of 20
#   roots costs 20*BUDGET seconds and ROUNDS sweeps cost
#   20*BUDGET*ROUNDS.
#
# OUTPUT
#   $OUT/sweep-<order>.log   per-root [hb]/[done]/TIMEOUT lines
#   $OUT/sweep-<order>.csv   per-root outcome rows (shared TT)
#   $OUT/sweep-<order>.tsv   one tidy row per (round, reply)
set -u

D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-30}
ROUNDS=${ROUNDS:-3}
MEMO=${MEMO:-26}
ORDER=${ORDER:-fwd}
OUT="$L/center20_sweep"
mkdir -p "$OUT"

replies=(0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49)
if [ "$ORDER" = "rev" ]; then
  replies=(49 48 38 37 36 27 26 25 24 16 15 14 13 12 5 4 3 2 1 0)
fi

# ONE csv containing the 20 roots repeated ROUNDS times. The solver
# reads it sequentially in a single process, so the TT is shared
# across all 20*ROUNDS entries.
csv="$OUT/roots-$ORDER.csv"
{
  echo 'canonical_parent,move'
  for _ in $(seq 1 "$ROUNDS"); do
    for r in "${replies[@]}"; do
      printf '"60",%s\n' "$r"
    done
  done
} > "$csv"

n=$(( ${#replies[@]} * ROUNDS ))
echo "=== shared-TT sweep order=$ORDER rounds=$ROUNDS budget=${BUDGET}s/root memo=$MEMO entries=$n ==="
echo "=== total expected wall ~ $(( ${#replies[@]} * ROUNDS * BUDGET / 60 )) min ==="

"$D" --n=11 --memo="$MEMO" --budget="$BUDGET" \
     --roots-csv="$csv" \
     --log="$OUT/sweep-$ORDER.log" --csv="$OUT/sweep-$ORDER.csv" \
     > /dev/null 2>&1
echo "=== solver exited rc=$? ==="

# ---- tidy table: one row per (round, reply) -----------------------
# Done by dfpn_sweep_parse.py: it walks the two streams in lockstep
# (i-th log entry pairs with the i-th root in the schedule), which is
# far more robust than matching individual replies by text, and it
# verifies that the reply each stream claims matches the schedule.
R=${REPLIES:-0,1,2,3,4,5,12,13,14,15,16,24,25,26,27,36,37,38,48,49}
if [ "$ORDER" = "rev" ]; then
  R=49,48,38,37,36,27,26,25,24,16,15,14,13,12,5,4,3,2,1,0
fi
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python3 "$SCRIPT_DIR/dfpn_sweep_parse.py" \
  "$OUT/sweep-$ORDER.log" "$OUT/sweep-$ORDER.csv" "$R" "$ROUNDS"

echo "SWEEP_DONE order=$ORDER"
