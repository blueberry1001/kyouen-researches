#!/usr/bin/env bash
# Build + run the round4 B371-B380 solver.
#   wsl_b371.sh <n> <k> <outprefix>
set -euo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/r4b371 "$S/round4_b371.cpp"
/tmp/kc_build/r4b371 "$1" "$2" "$3"
