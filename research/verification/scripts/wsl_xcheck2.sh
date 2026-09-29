#!/usr/bin/env bash
# Cross-validate stream solver on small n. Writes JSON to the REPO (Windows side)
# so results survive WSL /tmp cleanup.
# Usage: wsl_xcheck2.sh <n>
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=$R/research/verification/data/xcheck_n${1}.log
JSON=$R/research/verification/data/xcheck_n${1}.json
N="${1:-6}"
SPILL=/tmp/lk_x$N
mkdir -p /tmp/kc_build "$SPILL" "$R/research/verification/data"
: > "$LOG"
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream_x "$S/round5_prand_stream.cpp" 2>>"$LOG"; then
  echo BUILD_FAIL >>"$LOG"; cat "$LOG"; exit 1
fi
echo "build ok $(date -Is)" >>"$LOG"
export OMP_NUM_THREADS=8
# Use fewer threads so we don't starve the other agents' jobs
stdbuf -oL -eL /tmp/kc_build/stream_x --solve "$N" --spill="$SPILL" \
    --out="$JSON" >>"$LOG" 2>&1
rc=$?
echo "exit=$rc $(date -Is)" >>"$LOG"
echo "=== log tail ==="
tail -30 "$LOG"
echo "=== json exists? ==="
ls -la "$JSON" 2>/dev/null || echo "NO JSON"
if [ -f "$JSON" ]; then
  python3 "$S/xcheck_parse.py" "$JSON" "$N"
fi
