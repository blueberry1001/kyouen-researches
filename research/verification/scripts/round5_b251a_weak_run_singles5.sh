#!/bin/bash
cd /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
echo "START singles5sens $(date)"
export OMP_NUM_THREADS=4
./scripts/round5_b251a_weak.exe singles5sens > round5_b251a_weak_singles5.json 2> round5_b251a_weak_singles5.log
echo "END singles5sens $(date) exit=$?"
cat round5_b251a_weak_singles5.log
echo '---JSON---'
cat round5_b251a_weak_singles5.json
