// Enumerate every maximal safe set of a given size on the n x n board.
//
// A safe set is maximal when no further point can be added. Enumerating
// *maximal* sets of small size is tractable even where enumerating all
// subsets is not: branch and bound with the standard "adding p kills the
// candidates that would complete a quad" pruning, plus a size cap so we
// stop growing once the target size is reached.
//
// Usage: kc_maximal <n> <k> [threads]
// Writes a binary file: u64 count, then count * u64 masks.
#include "kc_core.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <mutex>
#include <algorithm>

using kc::u64;
using kc::Board;

static Board B;
static int K;
static std::vector<u64> found;
static std::mutex mu;

static void emit(u64 occ) {
    std::lock_guard<std::mutex> lk(mu);
    found.push_back(occ);
}

// Depth-first growth that keeps every node which is either maximal or exactly
// size K. Once |occ| == K we only record it if it is maximal.
static void grow(u64 occ, u64 cand, int size) {
    if (size == K) {
        if (kc::is_maximal(B, occ)) emit(occ);
        return;
    }
    // Prune: if nothing can be added, the node is maximal at its current size.
    if (cand == 0) {
        if (kc::is_maximal(B, occ)) emit(occ);
        return;
    }
    u64 c = cand;
    while (c) {
        int p = __builtin_ctzll(c);
        c &= c - 1;
        u64 bit = u64(1) << p;
        if (!kc::can_add(B, occ, p)) continue;
        u64 nxt = occ | bit;
        u64 kill = 0;
        for (u64 t : B.triples_by_pt[p]) {
            u64 miss = t & ~nxt;
            if (miss && (miss & (miss - 1)) == 0) kill |= miss;
        }
        grow(nxt, c & ~kill, size + 1);
    }
}

int main(int argc, char** argv) {
    int n = argc > 1 ? atoi(argv[1]) : 8;
    K = argc > 2 ? atoi(argv[2]) : 8;
    kc::build_square(B, n);
    std::fprintf(stderr, "n=%d V=%d F=%zu k=%d\n", n, B.V, B.quads.size(), K);

    u64 start = (B.V >= 64) ? ~u64(0) : ((u64(1) << B.V) - 1);
    grow(0, start, 0);
    std::fprintf(stderr, "maximal size-%d sets: %zu\n", K, found.size());

    // dedupe (grow may reach the same maximal set by different orders)
    std::vector<u64> uniq = found;
    std::sort(uniq.begin(), uniq.end());
    uniq.erase(std::unique(uniq.begin(), uniq.end()), uniq.end());
    std::fprintf(stderr, "after dedupe: %zu\n", uniq.size());

    char path[512];
    std::snprintf(path, sizeof(path), "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/kc_maximal_n%d_k%d.bin", n, K);
    FILE* f = std::fopen(path, "wb");
    if (!f) { std::perror("fopen"); return 1; }
    u64 c = uniq.size();
    std::fwrite(&c, sizeof(c), 1, f);
    if (c) std::fwrite(uniq.data(), sizeof(u64), uniq.size(), f);
    std::fclose(f);
    std::fprintf(stderr, "wrote %s\n", path);
    return 0;
}
