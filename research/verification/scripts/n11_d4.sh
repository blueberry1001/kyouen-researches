#!/usr/bin/env bash
# D4-symmetry Grundy solver driver.
#
#   n11_d4.sh build          compile only
#   n11_d4.sh n6             cross-validate n=6  (g=1, P=1,265,112, N=3,816,177)
#   n11_d4.sh n7             cross-validate n=7  (g=0, P=41,264,615, N=138,545,735)
#   n11_d4.sh n6n7           both, in sequence
#   n11_d4.sh n11 [MAXK]     n=11, generate levels 0..MAXK then run the DP
#
# NOTE: must be invoked as a script file. Inlining into PowerShell breaks the
# quoting, and the run is long, so everything is redirected to a log file.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
BIN=/tmp/kc_build/d4
LOG=/tmp/n11_d4.log
DATA=$R/research/verification/data
mkdir -p /tmp/kc_build "$DATA"

g++ -O3 -march=native -std=c++20 -fopenmp -o "$BIN" "$S/n11_d4.cpp" \
    2>/tmp/n11_d4_build.err || { echo BUILD_FAIL; tail -40 /tmp/n11_d4_build.err; exit 1; }
echo "build ok -> $BIN"
[ "${1:-}" = build ] && exit 0

export OMP_NUM_THREADS=${OMP:-12}
MAXK=${2:-11}

run_one() {   # $1 = n, $2 = extra args
  local N=$1; shift
  local D=/tmp/n11_d4_$N
  rm -rf "$D"; mkdir -p "$D"
  echo "=== n=$N $(date -Is) OMP=$OMP_NUM_THREADS ===" >>"$LOG"
  stdbuf -oL -eL "$BIN" --n "$N" --threads "$OMP_NUM_THREADS" --spill "$D" \
      --out "$DATA/n11_d4_n$N.json" "$@" >>"$LOG" 2>&1
  echo "exit=$? n=$N" >>"$LOG"
  grep -E 'raw level sizes|g\(empty\)|FATAL|STOPPED' "$LOG" | tail -4
}

case "${1:-n11}" in
  n6)  run_one 6 --maxlevel 12 ;;
  n7)  run_one 7 --maxlevel 15 ;;
  n6n7) run_one 6 --maxlevel 12; run_one 7 --maxlevel 15 ;;
  n11) run_one 11 --maxlevel "$MAXK" ;;
  *) echo "unknown: $1" >&2; exit 2 ;;
esac
echo "log: $LOG"
