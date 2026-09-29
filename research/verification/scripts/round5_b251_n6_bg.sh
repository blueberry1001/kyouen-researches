#!/bin/bash
# Background runner that survives WSL invocation end
WORK=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/scratchpad/r5b251
mkdir -p "$WORK"
BIN=$WORK/n6_orbit
export OMP_NUM_THREADS=8
echo "BG START $(date +%T)" >> "$WORK/bg.log"
setsid "$BIN" > "$WORK/n6_orbit.json" 2> "$WORK/n6_orbit.err" < /dev/null
echo "BG END $(date +%T) exit=$?" >> "$WORK/bg.log"
