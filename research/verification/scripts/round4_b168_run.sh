#!/bin/bash
# Round4 batch B168-B227 driver.
#   wsl -d Ubuntu -- bash <repo>/research/verification/scripts/round4_b168_run.sh
set -u
BIN=/tmp/r4b168
D=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
cd "$D" || exit 1
g++ -O2 -march=native -std=c++20 -o "$BIN" round4_b168.cpp || { echo "BUILD FAILED"; exit 1; }
echo "=== built ==="

T() { local tag="$1"; shift; local s=$(date +%s); "$@"; local e=$(date +%s); echo "###TIME $tag $((e-s))s"; }

echo "=== SELFCHECK (must match PROTOCOL) ==="
T sc_cnt $BIN cnt 4
T sc_full4 $BIN full 4 0 1
T sc_full5 $BIN full 5 0 1
T sc_circles $BIN circles 9
T sc_mod2_4 $BIN mod2 4
T sc_mod2_5 $BIN mod2 5
T sc_mod2_6 $BIN mod2 6
T sc_betti4 $BIN betti 4 20000
T sc_betti5 $BIN betti 5 60000

echo "=== A: full n=2..6 (exact random-greedy rationals ON) ==="
for n in 2 3 4 5 6; do T full_$n $BIN full $n 1 1 ; done

echo "=== A2: rectangles 2xm, 3xm, 4xm ==="
for m in 1 2 3 4 5 6 7 8 9 10 11; do T r2x$m $BIN rect 2 $m 0 0 1 ; done
for m in 1 2 3 4 5 6 7 8 9 10 11 12 13; do T r3x$m $BIN rect 3 $m 0 0 1 ; done
for m in 1 2 3 4 5 6 7 8 9 10; do T r4xm $BIN rect 4 $m 0 0 1 ; done

echo "=== B: rule variants n=2..6 ==="
for n in 2 3 4 5 6; do T circ_$n $BIN rect $n $n 1 0 1 ; done
for n in 2 3 4 5 6; do T line_$n $BIN rect $n $n 2 0 1 ; done

echo "=== C: q=5 forbidden family ==="
for n in 2 3 4 5; do T q5_$n $BIN q5 $n $n 0 1 ; done

echo "=== D: one-point deletions ==="
for n in 3 4 5; do T del1_$n $BIN del1 $n 0 0 ; done

echo "=== E: sub-board f-vectors (B177) ==="
for w in 2 3 4 5; do for h in 2 3 4 5; do
  if [ $((w*h)) -le 20 ]; then T sub_${w}x${h} $BIN sub $w $h 0 ; fi
done; done

echo "=== F: P/N disagreement (B218, B223) ==="
T dis_n4 $BIN disagree 0 4 4 1 4 4
T dis_n5 $BIN disagree 0 5 5 1 5 5
T dis_2x5 $BIN disagree 0 2 5 1 2 5
T dis_2x6 $BIN disagree 0 2 6 1 2 6
T dis_3x4 $BIN disagree 0 3 4 1 3 4
T dis_3x7 $BIN disagree 0 3 7 1 3 7

echo "=== G: external point (B208) ==="
T ext_5 $BIN ext 5 0
T ext_6 $BIN ext 6 0

echo "=== H: random-greedy MC ==="
for n in 4 5 6 7 8; do T mc_$n $BIN mc $n 100000 ; done

echo "=== I: downward family search keeping W (B224) ==="
T greedy_4 $BIN greedy 4 400
T greedy_5 $BIN greedy 5 200

echo "=== DONE ==="
