#!/bin/bash
echo "=== procs ==="
ps aux | grep -E 'round5|j6|g\+\+' | grep -v grep
echo "=== log ==="
cat /tmp/round5_b301_j6.log
echo "=== binary ==="
ls -la /tmp/round5_b301_j6 2>/dev/null || echo "no binary"
echo "=== dumps ==="
ls -la /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts/round5_b301_j*.txt 2>/dev/null || echo "no dumps"
echo "=== free ==="
free -h
