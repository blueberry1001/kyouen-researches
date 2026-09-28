#!/usr/bin/env bash
# Build and run the PARALLEL maximal-set enumerator. Usage: wsl_maximal_par.sh <n> <k> [threads]
set -euo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -pthread -o /tmp/kc_build/maxpar "$S/kc_maximal_par.cpp"
/tmp/kc_build/maxpar "$1" "$2" "${3:-16}"
