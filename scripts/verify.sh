#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
"$ROOT/scripts/check-all-certificates.sh" "${1:-$ROOT/release-assets}"
command -v lake >/dev/null || { echo "Lake is required for the Lean build" >&2; exit 2; }
cd "$ROOT"
lake build
lake exe kyouen-classification-demo
