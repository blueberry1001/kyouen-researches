REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts" || exit 1
/tmp/b228c > /tmp/b228c.json 2>/tmp/b228c.err
echo "exit=$?  bytes=$(wc -c < /tmp/b228c.json)"
tail -5 /tmp/b228c.err
