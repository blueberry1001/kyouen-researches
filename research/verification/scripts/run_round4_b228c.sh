REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
cd "$REPO/research/verification/scripts" || exit 1
g++ -O2 -std=c++20 -o /tmp/b228c round4_b228c.cpp 2>&1 | head -40
echo "=== compile exit: $? ==="
ls -la /tmp/b228c 2>/dev/null
