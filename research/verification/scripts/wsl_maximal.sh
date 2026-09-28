#!/usr/bin/env bash
# Enumerate maximal safe sets. Usage: wsl_maximal.sh <n> <k>
set -euo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -o /tmp/kc_build/maximal "$S/kc_maximal.cpp"
/tmp/kc_build/maximal "$1" "$2"
