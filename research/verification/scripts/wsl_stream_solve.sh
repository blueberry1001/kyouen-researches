#!/usr/bin/env bash
# Build and run the streaming p_rand DP solver.
# Usage: wsl_stream_solve.sh [n] [spilldir]
set -euo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
N="${1:-8}"
SPILL="${2:-/home/yuubi/spill$N}"
LOG=/tmp/stream_solve.log
OUT=$R/research/verification/round5_prand_n${N}.json
mkdir -p /tmp/kc_build "$R/research/verification/data"
: > "$LOG"
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream_solve \
    "$S/round5_stream_solve.cpp" 2>>"$LOG"; then
  echo BUILD_FAIL >>"$LOG"; cat "$LOG"; exit 1
fi
echo "build ok $(date -Is) spill=$SPILL" >>"$LOG"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-10}
stdbuf -oL -eL /tmp/kc_build/stream_solve "$N" --spill="$SPILL" --out="$OUT" >>"$LOG" 2>&1
rc=$?
echo "exit=$rc $(date -Is)" >>"$LOG"
echo "=== log tail ==="
tail -40 "$LOG"
echo "=== json ==="
ls -la "$OUT" 2>/dev/null || echo "NO JSON"
