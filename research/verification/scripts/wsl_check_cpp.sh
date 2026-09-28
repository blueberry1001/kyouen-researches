#!/usr/bin/env bash
# Build and run the C++ self-check under WSL. Usage: wsl_check_cpp.sh
set -euo pipefail
SCRIPTS=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
OUT=/tmp/kc_build
mkdir -p "$OUT"
g++ -O2 -march=native -std=c++20 -o "$OUT/kc_selfcheck" "$SCRIPTS/kc_selfcheck.cpp"
"$OUT/kc_selfcheck"
