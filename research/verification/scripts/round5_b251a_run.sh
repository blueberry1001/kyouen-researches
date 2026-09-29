#!/bin/bash
set -e
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
V=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/round5_b251a "$S/round5_b251a.cpp"
g++ -O2 -march=native -std=c++20 -o /tmp/round5_families "$S/round5_b251a_families.cpp"
echo COMPILED

echo "=== families n=4 ==="
/tmp/round5_families 4 > "$V/round5_b251a_families4.json" 2> "$V/round5_b251a_families4.log"
echo EXIT:$?
tail -2 "$V/round5_b251a_families4.log"
head -c 400 "$V/round5_b251a_families4.json"; echo

echo "=== triples4fast ==="
/tmp/round5_b251a triples4fast > "$V/round5_b251a_triples4fast.json" 2> "$V/round5_b251a_triples4fast.log"
echo EXIT:$?
tail -5 "$V/round5_b251a_triples4fast.log"
head -c 600 "$V/round5_b251a_triples4fast.json"; echo
