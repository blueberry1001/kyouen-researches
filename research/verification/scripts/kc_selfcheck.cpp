// Self-check for kc_core.h: the forbidden-quad count F_n must reproduce the
// known values (README / PROTOCOL.md) for n = 2..9, and the K_n maximum safe
// sizes for n = 2..7.
#include "kc_core.h"
#include <cstdio>
#include <map>

using kc::u64;
using kc::Board;

int main() {
    const int F_known[] = {0, 0, 1, 14, 194, 826, 2491, 6364, 14564, 29152};
    const int K_known[] = {0, 0, 2, 4, 8, 11, 14, -1, -1, -1};

    int bad = 0;
    for (int n = 2; n <= 9; ++n) {
        kc::Board b;
        kc::build_square(b, n);
        int F = (int)b.quads.size();
        bool okF = (F == F_known[n]);
        std::printf("n=%d  F=%6d expected=%6d %s\n", n, F, F_known[n],
                    okF ? "OK" : "MISMATCH");
        if (!okF) ++bad;

        // maximum safe set size by exhaustive branch and bound
        int best = 0;
        auto dfs = [&](auto&& self, u64 occ, u64 cand, int size) -> void {
            if (size > best) best = size;
            if (!cand) return;
            if (size + __builtin_popcountll(cand) <= best) return;
            u64 c = cand;
            while (c) {
                int p = __builtin_ctzll(c);
                c &= c - 1;
                u64 bit = u64(1) << p;
                if (!kc::can_add(b, occ, p)) continue;
                u64 nxt = occ | bit;
                // candidates that would complete a quad with nxt
                u64 kill = 0;
                for (u64 t : b.triples_by_pt[p]) {
                    u64 miss = t & ~nxt;
                    if (miss && (miss & (miss - 1)) == 0) kill |= miss;
                }
                self(self, nxt, c & ~kill, size + 1);
            }
        };
        u64 start = (n * n >= 64) ? ~u64(0) : ((u64(1) << (n * n)) - 1);
        dfs(dfs, 0, start, 0);
        bool okK = (K_known[n] < 0) || (best == K_known[n]);
        std::printf("n=%d  K=%6d expected=%6d %s\n", n, best, K_known[n],
                    okK ? "OK" : "MISMATCH");
        if (!okK) ++bad;
    }
    std::printf(bad ? "SELFCHECK FAILED (%d)\n" : "SELFCHECK PASSED (%d)\n", bad);
    return bad ? 1 : 0;
}
