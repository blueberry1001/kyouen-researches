#!/usr/bin/env bash
# Launch n=8 enum in background with nohup.
# Usage: launch_n8.sh [--enum|--solve] [--spill=DIR] [extra flags]
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
MODE="---enum"
SPILL="/home/yuubi/spill8"
EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --enum|--solve) MODE="$1"; shift ;;
    --spill=*) SPILL="${1#--spill=}"; shift ;;
    --spill) SPILL="$2"; shift 2 ;;
    *) EXTRA="$EXTRA $1"; shift ;;
  esac
done
LOG=/tmp/n8_stream.log
mkdir -p /tmp/kc_build "$SPILL" "$R/research/verification/data"

# Build
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream_n8 "$S/round5_prand_stream.cpp" 2>"$LOG"; then
  echo BUILD_FAIL | tee -a "$LOG"; exit 1
fi
echo "build ok $(date -Is) spill=$SPILL mode=$MODE extra=$EXTRA" >>"$LOG"

export OMP_NUM_THREADS=${OMP_NUM_THREADS:-12}
pkill -f stream_n8 2>/dev/null || true; sleep 1

if [ "$MODE" = "--enum" ]; then
  OUTJSON="$R/research/verification/data/n8_stream_enum.json"
  nohup stdbuf -oL -eL /tmp/kc_build/stream_n8 --enum 8 --spill="$SPILL" $EXTRA \
      > "$OUTJSON" 2>>"$LOG" &
else
  OUTJSON="$R/research/verification/round5_prand_n8.json"
  nohup stdbuf -oL -eL /tmp/kc_build/stream_n8 --solve 8 --spill="$SPILL" $EXTRA \
      > "$OUTJSON" 2>>"$LOG" &
fi
PID=$!
echo "launched pid=$PID mode=$MODE $(date -Is) out=$OUTJSON spill=$SPILL" | tee -a "$LOG"

# Heartbeat
nohup bash -c '
  while kill -0 '"$PID"' 2>/dev/null; do
    free -m | awk "/^Mem:/{print \"avail_MB\", \$7}"
    du -sm '"$SPILL"' 2>/dev/null | awk "{print \"spill_MB\", \$1}"
    date -Is
    sleep 120
  done
  echo "PROCESS ENDED $(date -Is)"
' >>"$LOG" 2>&1 &
echo "PID=$PID LOG=$LOG"
