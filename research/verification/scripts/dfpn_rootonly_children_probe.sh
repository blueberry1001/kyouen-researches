#!/bin/bash
set -euo pipefail
D=${D:-/mnt/d/ghq/build11/dfpn}
L=${L:-/mnt/d/ghq/build11/logs}
BUDGET=${BUDGET:-300}
MEMO=${MEMO:-25}
EXACT_LEGAL=${EXACT_LEGAL:-44}
EXACT_BUDGET=${EXACT_BUDGET:-200000}
EXACT_RETRIES=${EXACT_RETRIES:-2}
OUT="$L/rootonly_children"
mkdir -p "$OUT"
rm -f "$OUT/root.log" "$OUT/root.csv"

"$D" --n=11 --reps --only=60 --children   --memo="$MEMO" --budget="$BUDGET"   --exact-legal="$EXACT_LEGAL" --exact-budget="$EXACT_BUDGET"   --exact-retries="$EXACT_RETRIES" --exact-publish=root   --log="$OUT/root.log" --csv="$OUT/root.csv" >/dev/null 2>&1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python3 "$SCRIPT_DIR/dfpn_children_parse.py" "rootonly=$OUT/root.log"
echo
grep 'TIMEOUT' "$OUT/root.csv" | tail -1 || true
grep '^\[done\]' "$OUT/root.log" | tail -1 || true
