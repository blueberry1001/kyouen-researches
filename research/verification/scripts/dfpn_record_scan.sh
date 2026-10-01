#!/bin/bash
# Raise the handoff threshold to reach the layers ABOVE s5.
#
# The L72 record only contains s5 (23) and s6 (45) handoffs, so there is
# nothing above s6 to benchmark yet. Raising --exact-legal widens the
# handoff gate and should pull s7, s8 ... into the record, which is what
# a layer benchmark needs.
#
# Same memo (2^24) and same budget as the L72 record so the resulting
# roots are directly comparable with the s5/s5 numbers already recorded.
#
# publish=root keeps the main TT clean, and --exact-budget-by-stones
# gives s5/s6 the budgets already validated in the L72 adaptive probe.
D=/mnt/d/ghq/build11/dfpn
OUT=/mnt/d/ghq/build11/logs/exactrec
mkdir -p "$OUT"
MEMO=${MEMO:-24}
BUDGET=${BUDGET:-60}
# s5 budget for the scan. The default 5,000,000 is what the L72 adaptive
# probe validated, but it solves the s5 frontier outright, so the search
# never descends far enough to hand off an s6 or deeper position and the
# record comes back with s5 only. Pass a small SB5 to keep s6 expensive
# and expose the layers above it.
SB5=${SB5:-200000}

for L in "$@"; do
  echo "=== recording L$L (s5 budget=$SB5) ==="
  rm -f "$OUT/R$L.csv" "$OUT/R$L.log"
  "$D" --n=11 --reps --only=60 --memo="$MEMO" --budget="$BUDGET" \
       --exact-legal="$L" --exact-retries=1 --exact-publish=root \
       --exact-budget=200000 --exact-budget-by-stones="5:$SB5,6:200000" \
       --exact-record --csv="$OUT/R$L.csv" --log="$OUT/R$L.log" >/dev/null 2>&1
  echo "  rc=$? stone counts seen:"
  grep -v '^#' "$OUT/R$L.csv" 2>/dev/null | cut -d, -f3 | sort -n | uniq -c \
    | sed 's/^/    /'
  echo "  histogram line:"
  grep -h '^\[exact-depth\]' "$OUT/R$L.log" | tail -1 | sed 's/^/    /'
done
echo RECORD_SCAN_DONE