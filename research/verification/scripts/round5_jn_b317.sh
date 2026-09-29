#!/bin/bash
set -x
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S=$REPO/research/verification/scripts
cd "$S"
echo "=== free ==="
free -h
echo "=== build (ASan) ==="
g++ -O1 -g -fsanitize=address,undefined -std=c++20 -o /tmp/jn_b317 round5_jn_b317.cpp 2>&1
echo "build exit: $?"
echo "=== run n=4 ==="
/tmp/jn_b317 4 2>&1
echo "run exit: $?"
echo "=== copy json ==="
if [ -f /tmp/jn_b317_out.json ]; then
  cp /tmp/jn_b317_out.json "$REPO/research/verification/round5_jn_b317.json"
  echo "copied"
  cat /tmp/jn_b317_out.json
fi
