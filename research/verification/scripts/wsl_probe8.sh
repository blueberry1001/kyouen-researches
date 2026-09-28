#!/usr/bin/env bash
set -uo pipefail
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -o /tmp/kc_build/probe8 "$S/prand8_probe.cpp" || exit 1
free -m
stdbuf -oL /tmp/kc_build/probe8 "${1:-8}"
