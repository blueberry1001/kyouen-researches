#!/usr/bin/env bash
# Cross-validate round5_prand_stream.cpp against known n=6 / n=7 values.
# Usage: wsl_xcheck.sh [6|7|both]
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$R/research/verification/scripts
LOG=/tmp/xcheck.log
: > "$LOG"
WHICH="${1:-both}"
mkdir -p /tmp/kc_build
if ! g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/stream "$S/round5_prand_stream.cpp" 2>>"$LOG"; then
  echo BUILD_FAIL >>"$LOG"; cat "$LOG"; exit 1
fi
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16

run_one() {
  local N=$1
  local SPILL=/tmp/lk_x$N
  rm -rf "$SPILL"
  mkdir -p "$SPILL"
  echo "=== n=$N SOLVE ===" >>"$LOG"
  stdbuf -oL -eL /tmp/kc_build/stream --solve "$N" --spill="$SPILL" \
      --out=/tmp/xcheck_n${N}.json >>"$LOG" 2>&1
  local rc=$?
  echo "n=$N exit=$rc" >>"$LOG"
}

if [ "$WHICH" = "6" ] || [ "$WHICH" = "both" ]; then
  run_one 6
fi
if [ "$WHICH" = "7" ] || [ "$WHICH" = "both" ]; then
  run_one 7
fi
echo "=== DONE ===" >>"$LOG"
# print summary lines
grep -E 'level |safe subsets|wrote|exit=|BUILD|SIZE MISMATCH|CHILD LOOKUP|BUFFER|NOT SORTED|SPILL SHORT' "$LOG" | tail -80
echo "--- JSON heads ---"
for n in 6 7; do
  if [ -f /tmp/xcheck_n${n}.json ]; then
    echo "n=$n:"
    python3 -c "
import json,sys
d=json.load(open('/tmp/xcheck_n${n}.json'))
print('  n_safe_subsets', d['n_safe_subsets'])
print('  level_sizes', d['level_sizes'])
print('  edge_total', d['edge_total'])
print('  n_P', d['n_P'], 'n_N', d['n_N'])
print('  P_max_level', d.get('P_max_level'))
print('  P_max_filter', d.get('P_max_filter_value'))
print('  peak_rss', d.get('peak_rss_gb'))
print('  timing', d.get('timing_s'))
"
  fi
done
