#!/usr/bin/env bash
# Cross-check df-pn vs DFS on sampled mid-game roots (n=6,7).
# Same input CSV feeds both solvers; outcomes compared row by row.
set -u
B=/mnt/d/ghq/build11
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/cpp/solvers
L=$B/xcheck-logs
mkdir -p "$L"
g++ -O3 -march=native -std=c++20 -o "$B/s6" "$S/kyouen_solver_6_root.cpp" || exit 1
g++ -O3 -march=native -std=c++20 -o "$B/s7" "$S/kyouen_solver_7_root.cpp" || exit 1
echo "built s6 s7"
python3 - "$L" <<'EOF'
import random
random.seed(42)
def emit(rows, path):
    with open(path, "w") as f:
        f.write("canonical_parent,move\n")
        for parent, move in rows:
            f.write('"%s",%d\n' % (",".join(map(str,parent)), move))
rows6 = [([], v) for v in [0,1,7,13,14,21]]
rows6 += [([0], v) for v in [7,14,21,35]]
rows6 += [([0,7], v) for v in [14,21,28,35]]
rows6 += [([0,7,14], v) for v in [21,28,35]]
rows6 += [([1,8], v) for v in [15,22,29]]
emit(rows6, "/mnt/d/ghq/build11/xcheck-logs/in6.csv")
rows7 = [([], v) for v in [0,1,8,16,24,32,48]]
rows7 += [([0], v) for v in [8,16,24,48]]
rows7 += [([0,8], v) for v in [16,24,32,48]]
rows7 += [([0,8,16], v) for v in [24,32,48]]
rows7 += [([1,9], v) for v in [17,25,33]]
emit(rows7, "/mnt/d/ghq/build11/xcheck-logs/in7.csv")
print("wrote inputs: %d + %d rows" % (len(rows6), len(rows7)))
EOF
for n in 6 7; do
  echo "=== n=$n DFS ==="
  "$B/s$n" "$L/in$n.csv" 24 > "$L/dfs$n.csv" 2>"$L/dfs$n.err"
  echo "dfs$n rc=$?"
  echo "=== n=$n dfpn ==="
  /mnt/d/ghq/build11/dfpn --n="$n" --memo=24 --budget=300 \
      --roots-csv="$L/in$n.csv" \
      --log="$L/dfpn$n.log" --csv="$L/dfpn$n.csv" > /dev/null 2>&1
  echo "dfpn$n rc=$?"
done
echo XCHECK_RUNS_DONE
