#!/usr/bin/env bash
# Cross-check the pipeline enumerator on n = 6, 7, 8, 9 before n=11.
# Known level sizes:
#   n=6: [1,36,630,7140,56414,301952,997796,1783296,1459292,438952,35316,464]
#   n=7: [1,49,1176,18424,205512,1633048,8796600,29688640,56927728,55173324,
#         23478868,3707028,177760,2176,16]
set -uo pipefail
R=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches-n11
S=$R/research/verification/scripts
LOG=/tmp/pipe_x.log
: > "$LOG"
mkdir -p /tmp/n11_pipe_bin
free -m >>"$LOG"
if [ ! -x /tmp/n11_pipe_bin/n11_pipe ]; then
  g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/n11_pipe_bin/n11_pipe \
      "$S/n11_pipe.cpp" >>"$LOG" 2>&1 || { echo BUILD_FAIL >>"$LOG"; tail -20 "$LOG"; exit 1; }
fi
echo "build ok" >>"$LOG"
export OMP_NUM_THREADS=16
for N in 6 7 8 9; do
  D=/tmp/pipe_n$N
  rm -rf "$D"; mkdir -p "$D"
  echo "--- n=$N ---" >>"$LOG"
  stdbuf -oL -eL /tmp/n11_pipe_bin/n11_pipe --enum "$N" --dir="$D" --checkmerge \
      --memgb=12 >>"$LOG" 2>&1
  echo "exit=$?" >>"$LOG"
  # the pipeline reports levels on stderr; collect them into the json path
  grep -E '^  level' "$LOG" | tail -1 >>"$LOG"
  rm -rf "$D"
done
python3 - "$LOG" <<'PY' >>"$LOG" 2>&1
import re, sys
txt = open(sys.argv[1], encoding="utf-8", errors="replace").read()
# the solver prints "  level k: N states" lines; group them per run
REF = {
    6:  [1,36,630,7140,56414,301952,997796,1783296,1459292,438952,35316,464],
    7:  [1,49,1176,18424,205512,1633048,8796600,29688640,56927728,55173324,
         23478868,3707028,177760,2176,16],
}
runs = re.split(r"--- n=(\d+) ---", txt)
for i in range(1, len(runs) - 1, 2):
    n = int(runs[i])
    body = runs[i + 1]
    lv = [int(x) for x in re.findall(r"level\s+\d+:\s+(\d+)\s+states", body)]
    ref = REF.get(n)
    if not lv:
        print(f"n={n}: no level lines"); continue
    if ref is None:
        print(f"n={n}  levels={len(lv)}  no reference: {lv}")
    else:
        ok = lv[:len(ref)] == ref
        print(f"n={n}  levels={len(lv)}  {'MATCH' if ok else 'MISMATCH'}")
        print(f"   got  {lv}")
        if not ok:
            print(f"   want {ref}")
PY
grep -vE 'avail_MB|spill_MB' "$LOG" | tail -40
