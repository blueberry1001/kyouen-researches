#!/usr/bin/env bash
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
python3 "$R/research/verification/scripts/crt_threshold_audit.py" > /tmp/audit.log 2>&1
cat /tmp/audit.log
