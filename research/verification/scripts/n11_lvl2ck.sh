#!/usr/bin/env bash
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
LOG=/tmp/lvl2ck.log
: > "$LOG"
cd "$R" && python3 research/verification/scripts/n11_lvl2_check.py >>"$LOG" 2>&1
echo "exit=$?" >>"$LOG"
cat "$LOG"
