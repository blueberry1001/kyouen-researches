#!/usr/bin/env bash
set -euo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
S="$R/research/verification/scripts"
N="${1:-7}"
D="/home/yuubi/round28_n$N"
mkdir -p "$D"
g++ -O3 -march=native -std=c++20 -fopenmp "$S/round5_prand_stream.cpp" -o "$D/enumerate"
g++ -O3 -march=native -std=c++20 -fopenmp "$S/round28_low_layers.cpp" -o "$D/solve"
export OMP_NUM_THREADS=8
"$D/enumerate" --enum "$N" --spill="$D" --resume > "$R/research/verification/round28_n${N}_enum.json"
"$D/solve" "$N" "$D" "$R/research/verification/round28_n${N}_layers.json"
