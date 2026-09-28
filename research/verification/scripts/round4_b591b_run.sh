#!/bin/bash
# round4 b591b driver -- B591,B592,B593,B596,B597,B598,B599 second pass
set -u
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
cd $S/scripts || exit 1
g++ -O2 -march=native -std=c++20 -o /tmp/b591b round4_b591b.cpp 2>/tmp/cc.log
if [ $? -ne 0 ]; then echo "COMPILE FAILED"; cat /tmp/cc.log; exit 1; fi
echo "=== BUILD OK ==="
mkdir -p /tmp/b591bout

NIGHT=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/night-research

# ---- B596: G_12 and G_11 BFS on n=7, K=14, all 16 maximum sets ----
echo "### BFS n=7 K=14 floor=12 (G_12)"
/tmp/b591b bfs 7 14 $NIGHT/maxsafe_n7_K14.bin 12 40000000 900 > /tmp/b591bout/b596_g12.json 2>/tmp/b591bout/b596_g12.err
cat /tmp/b591bout/b596_g12.json
echo "### BFS n=7 K=14 floor=11 (G_11) -- THE ROUND2/3 GAP"
/tmp/b591b bfs 7 14 $NIGHT/maxsafe_n7_K14.bin 11 40000000 1500 > /tmp/b591bout/b596_g11.json 2>/tmp/b591bout/b596_g11.err
cat /tmp/b591bout/b596_g11.json
echo "### DONE BFS"
