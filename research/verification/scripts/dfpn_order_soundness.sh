#!/bin/bash
# Soundness for --exact-order: ordering must change the WORK, never the
# RESULT. Every mode has to return the same WIN/LOSS/UNKNOWN for every
# replayed position, otherwise the A/B is comparing different problems.
cd /mnt/d/ghq/build11 || exit 1
REC=logs/exactrec/L72.csv
BUDGET=${BUDGET:-5000000}

for m in count countd key; do
  rm -f "ord_$m.csv"
  /mnt/d/ghq/build11/dfpn --n=11 --memo=24 --exact-replay="$REC" --only=5 \
    --exact-replay-budget="$BUDGET" --exact-order="$m" \
    --csv="ord_$m.csv" > /dev/null 2>&1
done

echo "=== results identical across orderings? ==="
python3 - <<'PYEOF'
import io
def load(p):
    d={}
    for line in io.open(p, encoding='utf-8', errors='replace'):
        line=line.strip()
        if not line.startswith('replay,'): continue
        f=line.split(',')
        if len(f)<11: continue
        d[(f[9],f[10])]=(f[6], int(f[7]))   # key -> (result, nodes)
    return d
a=load('ord_count.csv'); b=load('ord_countd.csv'); c=load('ord_key.csv')
print('  keys: count=%d countd=%d key=%d' % (len(a),len(b),len(c)))
bad=[]
for k in a:
    ra=a[k][0]
    for nm,src in (('countd',b),('key',c)):
        if k not in src or src[k][0]!=ra:
            bad.append((k,nm,ra,src.get(k,('missing',))[0]))
print('  result mismatches: %d' % len(bad))
for x in bad[:10]: print('   ', x)
ta=sum(v[1] for v in a.values()); tb=sum(v[1] for v in b.values()); tc=sum(v[1] for v in c.values())
print('  total nodes: count-asc=%d count-desc=%d key-asc=%d' % (ta,tb,tc))
if ta:
    print('  desc vs asc: %+.1f%%   key vs asc: %+.1f%%' % (
        100.0*(tb-ta)/ta, 100.0*(tc-ta)/ta))
print('  ORDER_SOUND' if not bad else '  ORDER_UNSOUND')
PYEOF
echo ORDER_CHECK_DONE