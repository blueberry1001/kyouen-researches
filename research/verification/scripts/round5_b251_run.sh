#!/bin/bash
# Stage runner for round5_b251_solver
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
SRC=$REPO/research/verification/scripts/round5_b251_solver.cpp
OUTDIR=$REPO/research/verification
BIN=/tmp/r5b251_solver
mkdir -p /tmp/r5b251

echo "COMPILING..."
g++ -O2 -march=native -std=c++20 -o "$BIN" "$SRC"
echo "COMPILE_OK"

run() {
  local name="$1"; shift
  echo "START $name $(date +%T)"
  "$BIN" "$@" > /tmp/r5b251/${name}.json 2>/tmp/r5b251/${name}.err
  local ec=$?
  echo "END $name exit=$ec bytes=$(wc -c < /tmp/r5b251/${name}.json)"
  if [ -s /tmp/r5b251/${name}.err ]; then
    echo "ERR $name:"; head -5 /tmp/r5b251/${name}.err
  fi
  head -c 400 /tmp/r5b251/${name}.json; echo
}

run ugains_n4 ugains 4
run corr_n4 corr 4
run ugains_n5 ugains 5
run corr_n5 corr 5
run singles_n4 singles 4

# merge
python3 - <<'PY'
import json
from pathlib import Path
d = {}
for name in ["ugains_n4","corr_n4","ugains_n5","corr_n5","singles_n4"]:
    p = Path(f"/tmp/r5b251/{name}.json")
    if p.exists() and p.stat().st_size > 0:
        try:
            d[name] = json.loads(p.read_text())
        except Exception as e:
            d[name] = {"error": str(e), "raw": p.read_text()[:200]}
    else:
        d[name] = {"error": "missing"}
out = Path("/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/round5_b251_solver.json")
out.write_text(json.dumps(d, indent=2))
print("WROTE", out, "size", out.stat().st_size)
# summary
for k,v in d.items():
    if "error" in v:
        print(k, "ERROR", v["error"])
    else:
        keys = [x for x in v.keys() if x.startswith("B")]
        print(k, "g0", v.get("g0_std", v.get("g0")), "flips", v.get("B251_flips"), "B264", v.get("B264_positions"), "B265", v.get("B265_positions"), "B271f", v.get("B271_cov_sign_flips"))
PY
echo "ALL_DONE"
