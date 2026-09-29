#!/bin/bash
echo "=== processes ==="
ps aux | grep -E 'r5b251|n6_orbit|g[+][+]' | grep -v grep || true
echo "=== log ==="
cat /tmp/r5b251/n6_orbit_run.log 2>/dev/null || true
echo "=== files ==="
ls -la /tmp/r5b251/ | tail -20
echo "=== free ==="
free -h | head -2
