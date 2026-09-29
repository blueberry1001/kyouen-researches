#!/bin/bash
cd /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
echo "START b254n5 $(date)"
./scripts/round5_b251a_weak.exe b254n5 > round5_b251a_weak_b254.json 2> round5_b251a_weak_b254.log
echo "END b254n5 $(date) exit=$?"
cat round5_b251a_weak_b254.log
echo '---JSON---'
cat round5_b251a_weak_b254.json
