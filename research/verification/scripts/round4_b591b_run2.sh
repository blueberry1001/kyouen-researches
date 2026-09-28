#!/bin/bash
# round4 b591b driver 2 -- n=8 layer max d_max (B591/B592/B593) + B599 certificate
set -u
S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
cd $S/scripts || exit 1
mkdir -p /tmp/b591bout

# ---- B591/B592/B593: search for a LARGER d_max on the n=8 14-stone layer ----
# Round4 pass 1 certified d_max=6 for the round-3 witness.  Hill-climb for more.
for SD in 1 2 3 4; do
  echo "### CLIMB n=8 K=15 k=14 seed=$SD"
  /tmp/b591b climb 8 14 15 20000 $SD 400 > /tmp/b591bout/climb8_$SD.json 2>/dev/null
  cat /tmp/b591bout/climb8_$SD.json
done

# ---- B591/B593: n=8 deficiency-2 layer (13 stones), search d_max ----
for SD in 1 2; do
  echo "### CLIMB n=8 K=15 k=13 seed=$SD"
  /tmp/b591b climb 8 13 15 20000 $SD 300 > /tmp/b591bout/climb8c2_$SD.json 2>/dev/null
  cat /tmp/b591bout/climb8c2_$SD.json
done

# ---- B599: circle/line saturation certificate for the n=7 worst 13-stone set ----
W7='0,0;1,0;1,1;5,1;6,1;0,2;2,2;3,4;6,4;4,5;1,6;2,6;3,6'
echo "### CERT n=7 K=14 worst 13-stone set"
/tmp/b591b cert 7 14 "$W7" > /tmp/b591bout/cert_n7_worst.json 2>/dev/null
cat /tmp/b591bout/cert_n7_worst.json
echo "### DONE driver2"
