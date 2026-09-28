#!/usr/bin/env bash
# n=8 memory probe, writing to a file we can poll.
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
LOG=/tmp/probe8.log
: > "$LOG"
mkdir -p /tmp/kc_build
free -m >>"$LOG"
g++ -O2 -march=native -std=c++20 -o /tmp/kc_build/probe8 "$S/prand8_probe.cpp" 2>>"$LOG" || { echo BUILD_FAIL >>"$LOG"; exit 1; }
echo "build ok" >>"$LOG"
stdbuf -oL -eL /tmp/kc_build/probe8 "${1:-8}" >>"$LOG" 2>&1
echo "exit=$?" >>"$LOG"
