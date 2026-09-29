#!/usr/bin/env bash
# n11_pipe.sh -- build and drive the disk-resident kyouen level pipeline.
#
# Everything goes through a .sh file on purpose: WSL invocations built inline
# from PowerShell get their quoting mangled.  This script is the only thing
# that touches wsl/bash.
#
#   wsl -d Ubuntu -- bash /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11/research/verification/scripts/n11_pipe.sh build
#   wsl -d Ubuntu -- bash .../n11_pipe.sh xcheck            # n = 6,7,8,9
#   wsl -d Ubuntu -- bash .../n11_pipe.sh run 11 [maxlevel]
set -uo pipefail

REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
SRC=$REPO/research/verification/scripts
BIN=/tmp/n11_pipe_bin/n11_pipe
LOGDIR=/tmp/n11_pipe_log
DATA=$REPO/research/verification/data
PIPE=/tmp/n11_pipe

mkdir -p /tmp/n11_pipe_bin "$LOGDIR"

build() {
    g++ -O2 -march=native -std=c++20 -pthread -fopenmp \
        -o "$BIN" "$SRC/n11_pipe.cpp" 2>&1 | tee "$LOGDIR/build.log"
    local rc=${PIPESTATUS[0]}
    echo "build rc=$rc"
    return $rc
}

# One n, full pipeline, stdout/stderr to files.  --checkmerge re-verifies at
# run time that every v-block really is ascending across chunk boundaries, so
# the cross-validation cannot pass by accident on a broken sort assumption.
one() {
    local n=$1 maxlevel=${2:-100} dir=/tmp/n11_xv_$1
    rm -rf "$dir"; mkdir -p "$dir"
    echo "=== n=$n  maxlevel=$maxlevel  dir=$dir ==="
    /usr/bin/time -v "$BIN" --enum "$n" --dir "$dir" --maxlevel "$maxlevel" \
        --checkmerge --memgb=12 --minfreegb=40 \
        > "$LOGDIR/xv_n${n}.json" 2> "$LOGDIR/xv_n${n}.time" \
        || echo "  (n=$n exited $?)"
    grep -E '^  level ' "$LOGDIR/xv_n${n}.time" || true
    echo "--- n=$n json ---"
    cat "$LOGDIR/xv_n${n}.json"
    # Every level file must be strictly ascending and duplicate free.
    local k
    k=0
    while [ -f "$dir/level_${k}.bin" ]; do
        "$BIN" --check "$dir/level_${k}.bin" || echo "  !! level_$k FAILED integrity"
        k=$((k + 1))
    done
    rm -rf "$dir"
    echo
}

xcheck() {
    build || { echo "BUILD FAILED"; exit 1; }
    : > "$LOGDIR/xcheck_all.log"
    for n in 6 7 8 9; do
        one "$n" 100 2>&1 | tee -a "$LOGDIR/xcheck_all.log"
    done
    python3 "$SRC/n11_pipe_xcheck.py" "$LOGDIR" "$DATA" 2>&1 | tee -a "$LOGDIR/xcheck_all.log"
}

run() {
    local n=${1:-11} maxlevel=${2:-100}
    build || { echo "BUILD FAILED"; exit 1; }
    mkdir -p "$PIPE" "$LOGDIR" "$DATA"
    sync
    echo "=== n=$n pipeline, maxlevel=$maxlevel ==="
    df -h /tmp
    /usr/bin/time -v "$BIN" --enum "$n" --dir "$PIPE" --maxlevel "$maxlevel" \
        --chunk=4194304 --memgb=12 --minfreegb=120 \
        > "$LOGDIR/run_n${n}.json" 2> "$LOGDIR/run_n${n}.log" &
    local pid=$!
    # Watchdog: log disk and RSS while the run is in flight.
    ( while kill -0 "$pid" 2>/dev/null; do
          echo "[watch] $(date -u +%H:%M:%S) $(df -h /tmp | tail -1 | awk '{print $4}') free"
          sleep 60
      done ) >> "$LOGDIR/watch_n${n}.log" 2>&1 &
    local wpid=$!
    wait "$pid"; local rc=$?
    kill "$wpid" 2>/dev/null
    echo "run rc=$rc"
    tail -n 40 "$LOGDIR/run_n${n}.log"
    cat "$LOGDIR/run_n${n}.json"
    return $rc
}

case "${1:-xcheck}" in
    build)  build ;;
    one)    build && one "${2:-6}" "${3:-100}" ;;
    xcheck) xcheck ;;
    run)    run "${2:-11}" "${3:-100}" ;;
    check)  "$BIN" --check "$2" ;;
    *) echo "usage: $0 {build|one N|xcheck|run N [maxlevel]|check FILE}" ; exit 2 ;;
esac
