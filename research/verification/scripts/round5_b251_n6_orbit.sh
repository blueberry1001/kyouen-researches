#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
WORK=$REPO/scratchpad/r5b251
mkdir -p "$WORK"
SRC=$REPO/research/verification/scripts/round5_b251_n6_orbit.cpp
BIN=$WORK/n6_orbit
echo "COMPILING $(date +%T)"
g++ -O2 -march=native -std=c++20 -fopenmp -o "$BIN" "$SRC"
echo "COMPILE_OK $(date +%T)"
export OMP_NUM_THREADS=8
echo "RUN $(date +%T)"
"$BIN" > "$WORK/n6_orbit.json" 2> "$WORK/n6_orbit.err"
echo "END $(date +%T) exit=$?"
wc -c "$WORK/n6_orbit.json"
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/scratchpad/r5b251/n6_orbit.json")
d = json.loads(p.read_text())
print("n", d.get("n"), "nquads", d.get("nquads"), "norbits", d.get("norbits"),
      "g0_std", d.get("g0_std"), "tested", d.get("orbits_tested"),
      "flips", d.get("orbit_flips"), "secs", d.get("secs"))
if d.get("flip_orbit_ids"):
    print("FLIP orbits", d["flip_orbit_ids"][:20], "first", d.get("first_flip_rep"))
ns = [o["nstates"] for o in d.get("orbits", [])]
if ns:
    print("nstates min/med/max", min(ns), sorted(ns)[len(ns)//2], max(ns))
print("g0 distribution:", {})
from collections import Counter
c = Counter(o["g0"] for o in d.get("orbits", []))
print("g0 counts", dict(c))
PY
echo "ALL_DONE"
