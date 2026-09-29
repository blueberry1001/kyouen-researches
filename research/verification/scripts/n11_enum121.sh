#!/usr/bin/env bash
# 2-word (128-bit) occupancy enumeration. Usage:
#   n11_enum121.sh quads          # F_n for n=2..12 only (seconds)
#   n11_enum121.sh validate       # F_9/F_10 match + n=6 layer sizes match
#   n11_enum121.sh levels 6 7 8   # full layer enumeration for given n
#   n11_enum121.sh n11 [maxlevel]# 2-word n=11 enumeration, spill /tmp/n11_121
#
# NOTE: must be run as a script file. Inlining into PowerShell breaks quoting.
# NOTE: spill dir is /tmp/n11_121 -- /tmp/n11 belongs to the 1-word agent.
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11/research/verification/scripts
SPILL=/tmp/n11_121
LOG=/tmp/n11_121.log
BIN=/tmp/kc_build/n11enum121
mkdir -p /tmp/kc_build "$SPILL"

g++ -O3 -march=native -std=c++20 -fopenmp -o "$BIN" "$S/n11_enum121.cpp" 2>/tmp/n11_121_build.err \
  || { echo BUILD_FAIL; tail -30 /tmp/n11_121_build.err; exit 1; }
echo "build ok -> $BIN"

cmd="${1:-quads}"

case "$cmd" in
  quads)
    : > "$LOG"
    # n*n must be <= 128, so n=12 (144 points) is out of range for Bits.
    for n in 2 3 4 5 6 7 8 9 10 11; do
      "$BIN" --enum "$n" --quads >>"$LOG" 2>>"$LOG"
    done
    cat "$LOG"
    ;;

  validate)
    : > "$LOG"
    echo "== F_n ==" >>"$LOG"
    for n in 9 10; do "$BIN" --enum "$n" --quads >>"$LOG" 2>>"$LOG"; done
    echo "== n=6 layers (expect 1,36,630,7140,56414,301952,997796,1783296,1459292,438952,35316,464) ==" >>"$LOG"
    "$BIN" --enum 6 --spill="$SPILL/n6" >>"$LOG" 2>>"$LOG"
    grep -E '^\{|^\[n=|NOT SORTED' "$LOG"
    ;;

  levels)
    shift
    : > "$LOG"
    for n in "$@"; do
      echo "== n=$n ==" >>"$LOG"
      "$BIN" --enum "$n" --spill="$SPILL/n$n" --maxlevel 200 >>"$LOG" 2>>"$LOG"
    done
    grep -E '^\{|^\[n=|NOT SORTED' "$LOG"
    ;;

  n11)
    MAX="${2:-200}"
    : > "$LOG"
    free -m >>"$LOG"
    export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
    ( while true; do
        free -m | awk '/^Mem:/{print "avail_MB", $7}'
        du -sm "$SPILL" 2>/dev/null | awk '{print "spill_MB", $1}'
        sleep 120
      done ) >>"$LOG" 2>&1 &
    HB=$!
    stdbuf -oL -eL "$BIN" --enum 11 --spill="$SPILL" --maxlevel "$MAX" \
      > /tmp/n11_121.json 2>>"$LOG"
    rc=$?
    kill $HB 2>/dev/null
    echo "exit=$rc" >>"$LOG"
    echo "--- stderr ---"
    grep -v avail_MB "$LOG" | grep -v spill_MB | tail -40
    echo "--- json ---"
    cat /tmp/n11_121.json
    ;;

  *) echo "unknown command: $cmd" >&2; exit 2 ;;
esac
