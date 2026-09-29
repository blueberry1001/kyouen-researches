#!/usr/bin/env bash
# Create .ok markers for existing level_*.occ files in a spill directory.
# Usage: mark_ok.sh <spilldir>
set -euo pipefail
SPILL="${1:?usage: mark_ok.sh <spilldir>}"
for f in "$SPILL"/level_*.occ; do
  [ -f "$f" ] || continue
  base=$(basename "$f" .occ)   # level_N
  k="${base#level_}"
  sz=$(stat -c%s "$f")
  states=$((sz / 8))
  echo "$states" > "$SPILL/level_${k}.ok"
  echo "level $k: $states states marked ok"
done
echo "done: $(ls "$SPILL"/*.ok 2>/dev/null | wc -l) markers"
