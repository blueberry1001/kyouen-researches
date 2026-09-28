#!/usr/bin/env bash
# Build and run the geometry self-check (F_n must match known values).
set -euo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -o /tmp/kc_build/geom "$S/kc_geomcheck.cpp"
/tmp/kc_build/geom
