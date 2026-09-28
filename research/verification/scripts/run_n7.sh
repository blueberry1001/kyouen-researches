#!/bin/bash
# n=7 full p_rand DP.  Long-running; writes progress to /tmp/prand_n7.log
# and the final JSON to /tmp/prand_n7.json.
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts"
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/prand round4_b501_prand.cpp || exit 1
echo "=== build ok, starting n=7 ==="
date
/usr/bin/time -v /tmp/prand 7 > /tmp/prand_n7.json 2>/tmp/prand_n7.log
echo "=== n=7 exit=$? ==="
date
grep -E "Maximum resident|Elapsed" /tmp/prand_n7.log
