#!/usr/bin/env bash
# Run the streaming (v-max partitioned, spill-based) enumerator.
# Usage: wsl_stream.sh <n> [--solve] [spilldir]
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/stream.log
: > "$LOG"
N="${1:-8}"
MODE="${2:---enum}"
SPILL="${3:-/tmp/lk_$N}"
mkdir -p /tmp/kc_build "$SPILL"
free -m >>"$LOG"
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream "$S/round5_prand_stream.cpp" 2>>"$LOG"; then
  echo BUILD_FAIL >>"$LOG"; tail -25 "$LOG"; exit 1
fi
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
( while true; do
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    du -sm "$SPILL" 2>/dev/null | awk '{print "spill_MB", $1}'
    sleep 60
  done ) >>"$LOG" 2>&1 &
HB=$!
if [ "$MODE" = "--enum" ]; then
  stdbuf -oL -eL /tmp/kc_build/stream --enum "$N" --spill="$SPILL" \
      --out="$R/research/verification/data/n${N}_stream_enum.json" >>"$LOG" 2>&1
else
  stdbuf -oL -eL /tmp/kc_build/stream --solve "$N" --spill="$SPILL" \
      --out="$R/research/verification/round5_prand_n${N}.json" >>"$LOG" 2>&1
fi
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc" >>"$LOG"
grep -v avail_MB "$LOG" | grep -v spill_MB | tail -35
