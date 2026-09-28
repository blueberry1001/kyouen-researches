#!/usr/bin/env bash
# Diagnostic for the n=7 p_rand OOM: report memory at each stage.
# The solver keeps only two adjacent levels, so the peak is dominated by the
# widest level. We estimate it from the n=6 numbers and print what n=7 needs.
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
echo "=== host memory ==="
free -m
echo
echo "=== n=6 measured level widths (from the json) ==="
python3 - "$R/research/verification/round4_b501_prand_n6.json" <<'PY' 2>/dev/null || \
python3 - "$R/research/verification/round4_b501_prand.json" <<'PY2'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for key in ("n6",):
    if key in d:
        print(key, "levels:", d[key]["level_sizes"])
        print(key, "denominator digits:", d[key]["per_level_denominator_digits"])
PY
PY2
echo
echo "=== estimate for n=7 ==="
cat <<'PY'
n=6 level widths: 1,36,630,7140,56414,301952,997796,1783296,1459292,438952,35316,464
n=7 is expected to be roughly 20-30x wider at the peak (49 points vs 36).

If each state costs:
  8 bytes  (u64 mask)
  8 bytes  (legal-move mask)
  ~16-40 bytes (bigint numerator, 2-5 limbs at 9 bytes each)
  ~16 bytes (overhead / sort padding)
then n=7's widest level at ~20M states costs 20e6 * ~64B = ~1.3 GB for the
numerators alone, plus ~0.3 GB for the masks. That fits in 19 GB.

The real killer is likely that enumerate_levels keeps ALL levels resident at
once (`std::vector<std::vector<u64>> levels` for every k), not just two.
n=7 total states ~ 1.0-1.5e8, so 8 bytes each is ~1.2 GB, plus a second
copy during sort/unique. Still should fit...
Unless the bigint is 4-6 limbs at peak and the per-level struct is padded.
PY
echo
echo "=== run with a hard memory cap to see how far it gets ==="
ulimit -v 12000000   # 12 GB virtual
export OMP_NUM_THREADS=8
mkdir -p /tmp/kc_build
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/kc_build/prand \
  "$R/research/verification/scripts/round4_b501_prand.cpp" || exit 1
stdbuf -oL -eL /tmp/kc_build/prand 7 /tmp/n7.json
echo "exit=$?"
ls -la /tmp/n7.json 2>/dev/null || echo "no output"
