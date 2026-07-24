#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
ASSET_DIR=${1:-"$ROOT/release-assets"}
[[ "$ASSET_DIR" = /* ]] || ASSET_DIR="$ROOT/$ASSET_DIR"
command -v zstd >/dev/null || { echo "zstd is required" >&2; exit 2; }
[[ -f "$ASSET_DIR/SHA256SUMS.txt" ]] || { echo "SHA256SUMS.txt not found in $ASSET_DIR" >&2; exit 2; }

cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ROOT/build" --target kyouen-certcheck --parallel 2

while read -r expected listed; do
  file="$ASSET_DIR/$(basename "$listed")"
  [[ -f "$file" ]] || { echo "missing asset: $file" >&2; exit 1; }
  actual=$(sha256sum "$file" | awk '{print $1}')
  [[ "$actual" == "$expected" ]] || { echo "SHA-256 mismatch: $file" >&2; exit 1; }
  tmp=$(mktemp "${TMPDIR:-/tmp}/kyouen.XXXXXX.cert")
  zstd -q -d -f "$file" -o "$tmp"
  echo "== $(basename "$file") =="
  "$ROOT/build/kyouen-certcheck" "$tmp"
  rm -f "$tmp"
done < "$ASSET_DIR/SHA256SUMS.txt"
