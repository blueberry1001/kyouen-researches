#!/bin/bash
# Export the fifth moves of the fixed s4 position, with the rank each
# would get under BOTH child orderings, so the export doubles as the
# input for the cold-replay classification.
#
# The direct exact DFS orders children: decisive-solved first, then open
# children by legal count ASC, then key ASC. The quant solver uses board
# index order. If a cheap WIN exists, its position in these two orders
# is what decides whether ordering is the problem.
cd /mnt/d/ghq/build11 || exit 1
OUT=logs/s5dist
mkdir -p "$OUT"
R2=${R2:-0}; M3=${M3:-1}; M4=${M4:-2}
rm -f "$OUT/children.csv" "$OUT/replay_in.csv"
./dfpn --n=11 --memo=24 --quant-first=60 \
  --s4-ab="$R2,$M3,$M4" --s4-ab-budget=1000 \
  > "$OUT/children.raw" 2>&1
# keep only the enumeration rows
grep '^m5,' "$OUT/children.raw" > "$OUT/children.csv"
echo "children: $(wc -l < "$OUT/children.csv")"
head -3 "$OUT/children.csv"