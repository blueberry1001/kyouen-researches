#!/usr/bin/env bash
# Compile the pipeline enumerator and report errors clearly.
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/pipe_build.log
: > "$LOG"
mkdir -p /tmp/n11_pipe_bin
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/n11_pipe_bin/n11_pipe \
    "$S/n11_pipe.cpp" >>"$LOG" 2>&1
rc=$?
echo "exit=$rc" >>"$LOG"
if [ $rc -ne 0 ]; then
  grep -E "error|Error" "$LOG" | head -20
else
  echo "BUILD OK"
fi
