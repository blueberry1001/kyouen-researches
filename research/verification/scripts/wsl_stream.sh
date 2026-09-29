#!/usr/bin/env bash
# Run the streaming (v-max partitioned, spill-based) enumerator.
# Usage: wsl_stream.sh <n> [--enum|--solve] [spilldir] [--resume]
# Extra flags after the first three are passed through (e.g. --resume).
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/stream.log
N="${1:-8}"
MODE="${2:---enum}"
SPILL="${3:-/tmp/lk_$N}"
shift 3 2>/dev/null || shift $# 2>/dev/null || true
EXTRA="$*"
mkdir -p /tmp/kc_build "$SPILL" "$R/research/verification/data"
echo "=== wsl_stream.sh n=$N mode=$MODE spill=$SPILL extra='$EXTRA' $(date -Is) ===" >>"$LOG"
free -m >>"$LOG"
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream "$S/round5_prand_stream.cpp" 2>>"$LOG"; then
  echo BUILD_FAIL >>"$LOG"; tail -25 "$LOG"; exit 1
fi
echo "build ok $(date -Is)" >>"$LOG"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-12}
( while true; do
    free -m | awk '/^Mem:/{print "avail_MB", $7}'
    du -sm "$SPILL" 2>/dev/null | awk '{print "spill_MB", $1}'
    date -Is
    sleep 120
  done ) >>"$LOG" 2>&1 &
HB=$!
if [ "$MODE" = "--enum" ]; then
  OUTJSON="$R/research/verification/data/n${N}_stream_enum.json"
  stdbuf -oL -eL /tmp/kc_build/stream --enum "$N" --spill="$SPILL" $EXTRA \
      > "$OUTJSON" 2>>"$LOG"
else
  OUTJSON="$R/research/verification/round5_prand_n${N}.json"
  stdbuf -oL -eL /tmp/kc_build/stream --solve "$N" --spill="$SPILL" $EXTRA \
      > "$OUTJSON" 2>>"$LOG"
fi
rc=$?
kill $HB 2>/dev/null
echo "exit=$rc $(date -Is) wrote=$OUTJSON" >>"$LOG"
# also copy to data/ for solve mode
if [ "$MODE" != "--enum" ] && [ -f "$OUTJSON" ]; then
  cp "$OUTJSON" "$R/research/verification/data/n${N}_stream_solve.json" 2>/dev/null
fi
echo "=== last 35 log lines ==="
grep -v avail_MB "$LOG" | grep -v spill_MB | tail -35
echo "=== output json ==="
ls -la "$OUTJSON" 2>/dev/null || echo "NO JSON at $OUTJSON"
