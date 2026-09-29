#!/bin/bash
cd /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
echo "start misere 5 $(date)" > /tmp/fu_misere5.log
python3 round5_b201_core.py misere 5 >> /tmp/fu_misere5.log 2>&1
echo "done $(date)" >> /tmp/fu_misere5.log
