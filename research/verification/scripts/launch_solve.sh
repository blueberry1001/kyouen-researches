#!/usr/bin/env bash
# Launch streaming solve in background.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
N=8
SPILL=/home/yuubi/spill8
LOG=/tmp/stream_solve.log
OUT=$R/research/verification/round5_prand_n${N}.json
mkdir -p /tmp/kc_build
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream_solve \
    "$S/round5_stream_solve.cpp" 2>"$LOG"; then
  echo BUILD_FAIL; cat "$LOG"; exit 1
fi
echo "build ok $(date -Is) spill=$SPILL" >>"$LOG"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-12}
pkill -f stream_solve 2>/dev/null; sleep 1
nohup stdbuf -oL -eL /tmp/kc_build/stream_solve "$N" --spill="$SPILL" --out="$OUT" >>"$LOG" 2>&1 &
PID=$!
echo "launched solve pid=$PID $(date -Is)"
# Heartbeat
nohup bash -c '
  while kill -0 '"$PID"' 2>/dev/null; do
    free -m | awk "/^Mem:/{print \"avail_MB\", \$7}"
    date -Is
    sleep 60
  done
  echo "SOLVE ENDED $(date -Is)"
' >>"$LOG" 2>&1 &
echo "PID=$PID LOG=$LOG"
