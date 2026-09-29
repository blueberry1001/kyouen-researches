#!/bin/bash
set -x
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
cd "$S"
echo "=== run n=2..6 ==="
/tmp/round5_b301_j6 6 2>&1
echo "run exit: $?"
ls -la round5_b301_j*.txt 2>/dev/null
echo "=== done ==="
