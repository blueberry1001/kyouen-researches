#!/bin/bash
cd /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
echo "start rect3 11 $(date)" > /tmp/fu_rect3_11.log
python3 round5_b201_core.py rect3 11 >> /tmp/fu_rect3_11.log 2>&1
echo "done $(date)" >> /tmp/fu_rect3_11.log
