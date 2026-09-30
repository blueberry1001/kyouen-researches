#!/bin/bash
# Determinism / isolation check for --exact-replay.
#
# 1. Running the same replay twice must give byte-identical results.
#    A DFS with a hash table and eviction can be order-dependent; if it
#    is, node counts are not a stable benchmark and move-ordering work
#    cannot be graded against them.
# 2. The per-row solver must not leak state: reversing the row order
#    must give each position the same result and node count.
cd /mnt/d/ghq/build11 || exit 1
REC=logs/exactrec/L72.csv
rm -f det_a.csv det_b.csv det_rev.csv

/mnt/d/ghq/build11/dfpn --n=11 --memo=24 --exact-replay="$REC" --only=5 \
  --exact-replay-budget=5000000 --csv=det_a.csv >/dev/null 2>&1
/mnt/d/ghq/build11/dfpn --n=11 --memo=24 --exact-replay="$REC" --only=5 \
  --exact-replay-budget=5000000 --csv=det_b.csv >/dev/null 2>&1

echo "=== repeat run identical? (result + nodes; wall_s is timing noise) ==="
# The wall_s column is wall-clock and will differ between runs; what must
# be reproducible is the RESULT and the NODE COUNT, since those are what
# a move-ordering change would be graded against.
strip() { grep '^replay,' "$1" | cut -d, -f1-8,10,11; }
if diff <(strip det_a.csv) <(strip det_b.csv) >/dev/null; then
  echo "  OK  result and nodes identical across two runs"
else
  echo "  DIFFERS:"
  diff <(strip det_a.csv) <(strip det_b.csv) | head -10
fi

# Reverse the row order of the record file, then replay.
{ head -1 "$REC"; grep -v '^#' "$REC" | tac; } > det_rev_in.csv
/mnt/d/ghq/build11/dfpn --n=11 --memo=24 --exact-replay=det_rev_in.csv --only=5 \
  --exact-replay-budget=5000000 --csv=det_rev.csv >/dev/null 2>&1

echo "=== order-independent (same result+nodes per key)? ==="
python3 - <<'PYEOF'
import io
def load(p):
    d={}
    for line in io.open(p, encoding='utf-8', errors='replace'):
        line=line.strip()
        if not line.startswith('replay,'): continue
        f=line.split(',')
        if len(f)<11: continue
        d[(f[9],f[10])]=(f[6],f[7])   # key -> (result, nodes)
    return d
a=load('det_a.csv'); b=load('det_rev.csv')
common=set(a)&set(b)
mism=[(k,a[k],b[k]) for k in common if a[k]!=b[k]]
print('  keys compared: %d' % len(common))
print('  result/node mismatches: %d' % len(mism))
for m in mism[:8]: print('   ', m)
print('  ORDER_INDEPENDENT' if not mism else '  ORDER_DEPENDENT')
PYEOF
echo DET_CHECK_DONE