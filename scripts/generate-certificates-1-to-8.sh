#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
OUT=${1:-"$ROOT/certificates/raw"}
mkdir -p "$OUT"
cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ROOT/build" --target kyouen-certgen-1-to-8 --parallel 2
for n in {1..8}; do
  "$ROOT/build/kyouen-certgen-1-to-8" "$n" "$OUT/kyouen-${n}x${n}.cert"
done
