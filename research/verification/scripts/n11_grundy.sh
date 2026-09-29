#!/usr/bin/env bash
# Compile and run the n=11 Grundy solver.
#
#   n11_grundy.sh build
#   n11_grundy.sh n6
#   n11_grundy.sh n7
#   n11_grundy.sh n11            # full run, output to research/verification/data
#
# NOTE: must be run as a script file. Inlining into PowerShell breaks quoting.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
BIN=/tmp/kc_build/grundy121
mkdir -p /tmp/kc_build "$R/research/verification/data"

g++ -O3 -march=native -std=c++20 -fopenmp -o "$BIN" "$S/n11_grundy.cpp" 2>/tmp/grundy121_build.err \
  || { echo BUILD_FAIL; tail -30 /tmp/grundy121_build.err; exit 1; }
echo "build ok -> $BIN"

cmd="${1:-n11}"
case "$cmd" in
  build) ;;
  n6|n7)
    # cross-validation: --check-legal also asserts the fast free-mask equals
    # kc::legal_mask on every state, and --expect-levels pins the enumeration
    # to the published layer sizes.
    case "$cmd" in
      n6) EXP=1,36,630,7140,56414,301952,997796,1783296,1459292,438952,35316,464
          G=1; P=1265112; N=3816177 ;;
      n7) EXP=1,49,1176,18424,205512,1633048,8796600,29688640,56927728,55173324,23478868,3707028,177760,2176,16
          G=0; P=41264615; N=138545735 ;;
    esac
    NNUM="${cmd#n}"
    export OMP_NUM_THREADS=16
    "$BIN" --enum "$NNUM" --threads 16 --check-legal \
      --expect-levels="$EXP" --out "/tmp/grundy_${cmd}.json" \
      > "/tmp/grundy_${cmd}.out" 2>&1
    rc=$?
    echo "--- $cmd (exit=$rc) ---"
    grep -E 'level-size check|=== n=|FATAL|mismatch' "/tmp/grundy_${cmd}.out"
    python3 - "/tmp/grundy_${cmd}.json" "$G" "$P" "$N" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); g,p,nn=int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4])
ok = d["g_empty"]==g and d["n_P"]==p and d["n_N"]==nn
print("  got    g_empty=%d n_P=%d n_N=%d K=%d gmax=%d" % (d["g_empty"],d["n_P"],d["n_N"],d["K"],d["g_max"]))
print("  expect g_empty=%d n_P=%d n_N=%d" % (g,p,nn))
print("  CROSS-VALIDATION:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
PY
    ;;
  n11)
    # Self-contained: re-enumerates in RAM (the /tmp spill dirs are shared with
    # other agents and were found to be contaminated, so they are not read).
    export OMP_NUM_THREADS=16
    ( while true; do
        free -m | awk '/^Mem:/{print "avail_MB", $7}'
        sleep 120
      done ) >/tmp/grundy121_mem.log 2>&1 &
    HB=$!
    stdbuf -oL -eL "$BIN" --enum 11 --threads 16 --spill=/tmp/n11_grundy \
      --expect-levels=1,121,7007,228485,3863862,29108488,82177064,72669632,15795232,572800,1536 \
      --out "$R/research/verification/data/n11_grundy.json" \
      > /tmp/n11_grundy.json 2>/tmp/n11_grundy.log
    rc=$?
    kill $HB 2>/dev/null
    echo "exit=$rc"
    tail -30 /tmp/n11_grundy.log
    echo "--- json ---"; cat /tmp/n11_grundy.json
    ;;
  *) echo "unknown command: $cmd" >&2; exit 2 ;;
esac
