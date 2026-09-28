#!/usr/bin/env bash
# Verify the CRT solver's n=6 output against the big-integer reference.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
LOG=/tmp/v6.log
: > "$LOG"
python3 "$R/research/verification/scripts/verify_crt_n6.py" >>"$LOG" 2>&1
cat "$LOG"
