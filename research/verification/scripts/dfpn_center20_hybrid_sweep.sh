#!/bin/bash
# One-process shared-TT sweep over all 20 second replies after center v=60,
# with the exact-endgame hybrid enabled. Designed for mixed outcomes; the
# solver tags each root with seq=N and dfpn_sweep_parse.py aligns by seq.
set -euo pipefail

D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-30}
MEMO=${MEMO:-25}
ROUNDS=${ROUNDS:-1}
EXACT_LEGAL=${EXACT_LEGAL:-44}
EXACT_BUDGET=${EXACT_BUDGET:-200000}
EXACT_RETRIES=${EXACT_RETRIES:-2}
EXACT_PUBLISH=${EXACT_PUBLISH:-root}
ORDER=${ORDER:-fwd}
OUT="$L/center20_hybrid_sweep"
mkdir -p "$OUT"

fwd=(0 1 2 3 4 5 12 13 14 15 16 24 25 26 27 36 37 38 48 49)
rev=(49 48 38 37 36 27 26 25 24 16 15 14 13 12 5 4 3 2 1 0)
if [ "$ORDER" = "rev" ]; then replies=("${rev[@]}"); else replies=("${fwd[@]}"); fi

tag="L${EXACT_LEGAL}-${EXACT_PUBLISH}-${ORDER}"
roots="$OUT/roots-$tag.csv"
{
  echo 'canonical_parent,move'
  for _ in $(seq 1 "$ROUNDS"); do
    for r in "${replies[@]}"; do
      printf '"60",%s\n' "$r"
    done
  done
} > "$roots"

rm -f "$OUT/$tag.log" "$OUT/$tag.csv"
"$D" --n=11 --memo="$MEMO" --budget="$BUDGET"   --roots-csv="$roots"   --exact-legal="$EXACT_LEGAL" --exact-budget="$EXACT_BUDGET"   --exact-retries="$EXACT_RETRIES" --exact-publish="$EXACT_PUBLISH"   --log="$OUT/$tag.log" --csv="$OUT/$tag.csv" >/dev/null 2>&1

R=$(IFS=,; echo "${replies[*]}")
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python3 "$SCRIPT_DIR/dfpn_sweep_parse.py"   "$OUT/$tag.log" "$OUT/$tag.csv" "$R" "$ROUNDS"

echo
echo "=== final heartbeat ==="
grep '^\[hb\]' "$OUT/$tag.log" | tail -1 || true
echo "=== final timeout/done ==="
grep -hE '^\[done\]|TIMEOUT' "$OUT/$tag.log" "$OUT/$tag.csv" | tail -3 || true
