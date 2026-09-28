REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts" || exit 1
# quick LP-only smoke test: run and show the lp block as soon as it appears
timeout 300 /tmp/b228c > /tmp/b228c.json 2>/tmp/b228c.err &
PID=$!
for i in $(seq 1 60); do
  if grep -q 'stage_lp_done' /tmp/b228c.json 2>/dev/null; then break; fi
  sleep 2
done
sed -n '/"lp":/,/stage_lp_done/p' /tmp/b228c.json
kill $PID 2>/dev/null
echo "=== smoke test done ==="
