#!/usr/bin/env bash
# Run the n=7 p_rand solve with unbuffered output and a progress heartbeat,
# so we can see which level is slow / how far it got before any OOM kill.
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O3 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand "$S/round4_b501_prand.cpp" || exit 1
export OMP_NUM_THREADS=16
# 1 GB per worker * 16 threads is what likely blew the box; cap the bigint
# allocation by keeping the level loop single-threaded if memory is tight.
ulimit -v unlimited 2>/dev/null || true
stdbuf -oL -eL /tmp/kc_build/prand "$1"
echo "exit=$?"
