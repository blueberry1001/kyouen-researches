#!/usr/bin/env bash
# Screen all 20 D4-distinct second replies after the 11x11 center move v=60.
#
# Goal:
#   Root {60} is an AND node for the proposition "the original first player wins".
#   Proving center requires ALL 20 two-stone children {60,r} to be WIN (pn=0).
#   Refuting center requires ONE child to be LOSS (dn=0).
#
# Every reply is run in a FRESH PROCESS with a FRESH TT so difficulty is
# comparable and no sibling can inherit transposition work from another run.
#
# Usage:
#   BUDGET=300 MEMO=26 ./research/verification/scripts/dfpn_center20.sh
#
# Output:
#   /mnt/d/ghq/build11/logs/center20/r<R>.log
#   /mnt/d/ghq/build11/logs/center20/r<R>.csv
#
# The 20 representatives below are the D4 orbits of the 120 non-center points.
# They are mechanically the fundamental-domain representatives:
#   0,1,2,3,4,5,12,13,14,15,16,24,25,26,27,36,37,38,48,49
set -u

D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-300}
MEMO=${MEMO:-26}
OUT="$L/center20"
mkdir -p "$OUT"

replies=(0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49)

# Move v=60 (the center) is played by the ORIGINAL FIRST PLAYER.
# After it, the ORIGINAL SECOND PLAYER to move, so each two-stone root
# {60,r} has 2 stones on the board => is_or(2) is true => OR node from
# the side-to-move's perspective, i.e. the ORIGINAL FIRST PLAYER is to
# move and is the maximizing side.
#
# Therefore at each child root:
#   WIN  = the original first player wins  (pn = 0, the proof side)
#   LOSS = the original second player wins (dn = 0, the disproof side)
# and at the parent {60} (1 stone, AND node for that same proposition):
#   proving the center needs ALL 20 children WIN
#   refuting the center needs ANY ONE child LOSS
#
# This is the parity relation that makes the aggregate verdict correct.
# The DFS cross-check on n=6/n=7 depends on the same inversion:
# odd-stone roots invert the reported side.

for r in "${replies[@]}"; do
  roots="$OUT/root-$r.csv"
  printf 'canonical_parent,move\n"60",%s\n' "$r" > "$roots"
  echo "=== center reply r=$r start $(date -u +%H:%M:%S) ==="
  "$D" --n=11 --memo="$MEMO" --budget="$BUDGET" \
       --roots-csv="$roots" \
       --log="$OUT/r$r.log" --csv="$OUT/r$r.csv" \
       > /dev/null 2>&1
  rc=$?
  echo "=== center reply r=$r rc=$rc ==="
done

echo CENTER20_DONE

# OUTCOME STREAMS (verified 2026-09-30, do not "unify" these):
#   run_one() writes "[done] ... WIN/LOSS" to the LOG stream (L<<), and
#   writes the "# ... TIMEOUT" line to the CSV stream (C<<). They are
#   deliberately different streams, so a solved root shows up in the
#   log and an unsolved one shows up in the csv.
#
# Verified on a board that actually solves: n=6 root {30,1} finishes in
# 0 s and its log contains
#   [done] [roots{30,1}] WIN expansions=20462 root_pn=0 ...
# with an empty csv, while n=11 root {60,5} times out and puts
#   # [roots{60,5}] TIMEOUT reason=TIME_BUDGET ...
# in the csv. So: outcome from the log, timeout detail from the csv.
win=0
loss=0
timeout=0
for r in "${replies[@]}"; do
  echo "--- reply=$r ---"
  if grep -q '^\[done\].* WIN ' "$OUT/r$r.log" 2>/dev/null; then
    win=$((win+1))
    grep '^\[done\]' "$OUT/r$r.log" | tail -1
  elif grep -q '^\[done\].* LOSS ' "$OUT/r$r.log" 2>/dev/null; then
    loss=$((loss+1))
    grep '^\[done\]' "$OUT/r$r.log" | tail -1
  else
    timeout=$((timeout+1))
    grep -hE 'TIMEOUT' "$OUT/r$r.csv" 2>/dev/null | tail -1 || true
    grep -h '^\[hb\]' "$OUT/r$r.log" 2>/dev/null | tail -1 || true
  fi
done

echo "SUMMARY WIN=$win LOSS=$loss TIMEOUT=$timeout TOTAL=${#replies[@]}"
if [ "$loss" -gt 0 ]; then
  echo "CENTER_REFUTED: at least one second reply is LOSS for the original first-player proposition."
elif [ "$win" -eq 20 ]; then
  echo "CENTER_PROVED: all 20 D4-distinct second replies are WIN."
else
  echo "CENTER_UNRESOLVED"
fi
