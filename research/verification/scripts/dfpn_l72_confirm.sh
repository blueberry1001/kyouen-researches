#!/bin/bash
# Confirmation run: L72 with the validated adaptive s5 budget, longer
# budget (5 min) and the larger memo, to see whether the s5 frontier
# stays collapsed and whether any direct child of the center finally
# becomes solved.
#
# Resource note: memo 2^26 is ~1 GB of tables for this solver and the
# machine has 19 GB, so this runs alone. No swap use is tolerated: if
# swap starts, the timing numbers are discarded rather than trusted.
D=/mnt/d/ghq/build11/dfpn
OUT=/mnt/d/ghq/build11/logs/l72_confirm
mkdir -p "$OUT"
MEMO=${MEMO:-26}
BUDGET=${BUDGET:-300}
LEVEL=${LEVEL:-72}

rm -f "$OUT"/c.csv "$OUT"/c.log
echo "=== L$LEVEL adaptive, ${BUDGET}s, memo 2^$MEMO, --children ==="
"$D" --n=11 --reps --only=60 --memo="$MEMO" --budget="$BUDGET" --children \
     --exact-legal="$LEVEL" --exact-retries=1 --exact-publish=root \
     --exact-budget=200000 --exact-budget-by-stones=5:5000000,6:200000 \
     --log="$OUT/c.log" --csv="$OUT/c.csv" > /dev/null 2>&1
echo "=== rc=$? ==="
grep -hE '^\[done\]|TIMEOUT reason' "$OUT/c.log" "$OUT/c.csv" | tail -1
echo "--- exact-depth:"
grep -h '^\[exact-depth\]' "$OUT/c.log" | tail -1
echo "--- direct children of the root (solved status is the st column):"
grep -A 21 '^\[children\] t=' "$OUT/c.log" | tail -21
echo "--- swap check:"
free -m | grep -i swap
echo CONFIRM_DONE