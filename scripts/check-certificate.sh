#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
INPUT=${1:?usage: check-certificate.sh CERTIFICATE.cert[.zst]}
[[ "$INPUT" = /* ]] || INPUT="$ROOT/$INPUT"
[[ -f "$INPUT" ]] || { echo "certificate not found: $INPUT" >&2; exit 2; }

cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ROOT/build" --target kyouen-certcheck --parallel 2

TMP=""
cleanup() { [[ -z "$TMP" ]] || rm -f "$TMP"; }
trap cleanup EXIT
CERT="$INPUT"
if [[ "$INPUT" == *.zst ]]; then
  command -v zstd >/dev/null || { echo "zstd is required" >&2; exit 2; }
  TMP=$(mktemp "${TMPDIR:-/tmp}/kyouen.XXXXXX.cert")
  zstd -q -d -f "$INPUT" -o "$TMP"
  CERT="$TMP"
fi
"$ROOT/build/kyouen-certcheck" "$CERT"
