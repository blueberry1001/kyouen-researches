#!/bin/bash
# Round5 B201/B202: compile and run one-point deletion on n x n.
set -e
cd "$(dirname "$0")"
echo "=== free memory ==="
free -h
echo "=== compile ==="
g++ -O2 -march=native -std=c++20 -o /tmp/round5_b201_del1 round5_b201_del1.cpp
echo "=== run n=$1 ==="
/tmp/round5_b201_del1 "$1" "${2:-}"
