#!/usr/bin/env bash
# Verify the WSL C++ toolchain end to end, including access to the repo.
set -euo pipefail
mkdir -p /tmp/kc_test
cd /tmp/kc_test

cat > a.cpp <<'CPP'
#include <cstdio>
#include <cstdint>
int main() {
    // 64-bit popcount, the primitive the whole solver needs
    std::uint64_t m = 0xDEADBEEFCAFEBABEULL;
    int c = __builtin_popcountll(m);
    std::printf("ok popcount=%d\n", c);
    return c > 0 ? 0 : 1;
}
CPP

g++ -O2 -march=native -o a a.cpp
./a
echo "g++ works: $(g++ --version | head -1)"
echo "nproc=$(nproc)"
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
test -d "$REPO" && echo "repo mount OK: $REPO"
test -f "$REPO/research/verification/scripts/kyouen_core.py" && echo "kyouen_core reachable"
