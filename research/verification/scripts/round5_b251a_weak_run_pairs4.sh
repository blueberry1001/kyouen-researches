#!/bin/bash
cd /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
./scripts/round5_b251a_weak.exe pairs4sens > round5_b251a_weak_pairs4.json 2> round5_b251a_weak_pairs4.log
echo EXIT:$?
cat round5_b251a_weak_pairs4.log
echo '---'
cat round5_b251a_weak_pairs4.json
