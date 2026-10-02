#!/bin/bash
# Persist the s5 verdicts proved by the cold classification, then confirm
# the quant search refutes third moves from the cache alone.
#
# The cache holds only decided verdicts. UNKNOWN is never persisted, so a
# later better funded query can never inherit an earlier failure.
cd /mnt/d/ghq/build11 || exit 1
OUT=logs/s5cache
mkdir -p "$OUT"
CACHE="$OUT/s5_verdicts.csv"
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
rm -f "$CACHE"

python3 "$S/dfpn_s5_cache.py"

echo
echo "=== quant run with the cache loaded ==="
./dfpn --n=11 --memo=24 --quant-first=60 --quant-replies=0 \
  --quant-budget=20000000 --quant-timeout=240 \
  --s5-cache="$CACHE" --s5-cache-out="$CACHE" > "$OUT/cachetest.txt" 2>&1
grep -E '^quant,|^# SUMMARY' "$OUT/cachetest.txt"
echo
echo "--- oracle queries actually run (cache hits do not count):"
echo "  q-done: $(grep -c '^\[q-done\]' "$OUT/cachetest.txt")"
echo "  cache-loaded line:"
grep -o 'cache_loaded=[0-9]*' "$OUT/cachetest.txt" | head -1
echo "  hits:"
grep -o 'oracle_hits=[0-9]*' "$OUT/cachetest.txt" | head -1