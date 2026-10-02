#!/bin/bash
# Cache robustness: the cache is proof material now, so a corrupt or
# foreign file must be refused rather than loaded.
cd /mnt/d/ghq/build11 || exit 1
T=logs/s5cache
mkdir -p "$T"

echo "=== 1. good cache loads ==="
./dfpn --n=11 --memo=24 --cover --cover-first=60 --cover-r2=0 \
  --s5-cache="$T/s5_verdicts.csv" > "$T/cover.txt" 2>&1
grep -E '^# (LOSS-edge cover|edges|COVER)' "$T/cover.txt" | head -4

echo
echo "=== 2. conflicting verdicts for one key are refused ==="
{ echo '# s5 verdict cache: n=11 schema=1'
  echo 's5verdict,12345,0,5,2,100'
  echo 's5verdict,12345,0,5,1,100'
} > "$T/conflict.csv"
./dfpn --n=11 --memo=24 --cover --cover-first=60 --cover-r2=0 \
  --s5-cache="$T/conflict.csv" 2>&1 | tail -2

echo
echo "=== 3. foreign header is refused ==="
{ echo '# some other cache'
  echo 's5verdict,12345,0,5,2,100'
} > "$T/foreign.csv"
./dfpn --n=11 --memo=24 --cover --cover-first=60 --cover-r2=0 \
  --s5-cache="$T/foreign.csv" 2>&1 | tail -2

echo
echo "=== 4. UNKNOWN verdicts in the file are ignored, not loaded ==="
{ echo '# s5 verdict cache: n=11 schema=1'
  echo 's5verdict,12345,0,5,0,100'
} > "$T/unk.csv"
./dfpn --n=11 --memo=24 --cover --cover-first=60 --cover-r2=0 \
  --s5-cache="$T/unk.csv" 2>&1 | grep -E 'edges total|error' | head -2

echo
echo "=== 5. re-saving with no new proofs appends nothing ==="
cp "$T/s5_verdicts.csv" "$T/nosave.csv"
before=$(wc -l < "$T/nosave.csv")
./dfpn --n=11 --memo=24 --quant-first=60 --quant-replies=0 \
  --quant-budget=1000 --quant-timeout=3 \
  --s5-cache="$T/nosave.csv" --s5-cache-out="$T/nosave.csv" >/dev/null 2>&1
after=$(wc -l < "$T/nosave.csv")
echo "  lines before=$before after=$after (must be equal)"
exit 0