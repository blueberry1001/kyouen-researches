#!/usr/bin/env bash
# Main run: 8x8 board, 8-stone maximal safe sets. This is the family that
# B371, B372, B373, B374, B375, B378, B380 are all about.
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
V=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/r4b371 "$S/round4_b371.cpp" || exit 1
/tmp/kc_build/r4b371 8 8 "$V/round4_b371"
