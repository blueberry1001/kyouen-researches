#!/usr/bin/env bash
set -euo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O2 -std=c++20 -o /tmp/kc_build/dbg371 "$S/dbg_b371.cpp"
for n in "$@"; do
  /tmp/kc_build/dbg371 "$n"
done
