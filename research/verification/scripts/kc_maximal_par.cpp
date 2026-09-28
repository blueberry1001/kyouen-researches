// Parallel enumeration of every maximal safe set of size k on the n x n board.
//
// Same semantics as kc_maximal.cpp, but the top level is split across threads
// by seeding each worker with one of the lowest candidates. Needs a work-steal
// free design: each root's subtree is disjoint, because a maximal set is
// reached by exactly one increasing sequence, and we assign each state to the
// thread that owns its lowest still-undecided point.
//
// Usage: kc_maximal_par <n> <k> <threads>
// Writes: research/verification/data/kc_maximal_n<n>_k<k>.bin
#include "kc_core.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <mutex>
#include <algorithm>
#include <atomic>
#include <thread>

using kc::u64;
using kc::Board;

static Board B;
static int K;
static std::vector<u64> found;
static std::mutex mu;
static std::atomic<u64> visited{0};

static void grow(u64 occ, u64 cand, int size) {
    visited.fetch_add(1, std::memory_order_relaxed);
    if (size == K) {
        if (kc::is_maximal(B, occ)) {
            std::lock_guard<std::mutex> lk(mu);
            found.push_back(occ);
        }
        return;
    }
    if (cand == 0) {
        if (kc::is_maximal(B, occ)) {
            std::lock_guard<std::mutex> lk(mu);
            found.push_back(occ);
        }
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
    int nth = argc > 3 ? atoi(argv[3]) : 16;
    kc::build_square(B, n);
    std::fprintf(stderr, "n=%d V=%d F=%zu k=%d threads=%d\n",
                 n, B.V, B.quads.size(), K, nth);

    u64 start = (B.V >= 64) ? ~u64(0) : ((u64(1) << B.V) - 1);

    // Split the search: thread t owns subtrees whose lowest chosen point is
    // congruent in a strided way. Because grow() always picks the lowest
    // available candidate, every maximal set has a unique increasing sequence,
    // so partitioning by the *first* point (position 0) is a clean split.
    std::vector<std::thread> th;
    for (int t = 0; t < nth; ++t) {
        th.emplace_back([&, t] {
            u64 c = start;
            int idx = 0;
            while (c) {
                int p = __builtin_ctzll(c);
                c &= c - 1;
                if (idx++ % nth != t) continue;
                u64 bit = u64(1) << p;
                if (!kc::can_add(B, 0, p)) continue;
                u64 nxt = bit;
                u64 kill = 0;
                for (u64 q : B.triples_by_pt[p]) {
                    u64 miss = q & ~nxt;
                    if (miss && (miss & (miss - 1)) == 0) kill |= miss;
                }
                grow(nxt, c & ~kill, 1);
            }
        });
    }
    for (auto& x : th) x.join();

    std::vector<u64> uniq = found;
    std::sort(uniq.begin(), uniq.end());
    uniq.erase(std::unique(uniq.begin(), uniq.end()), uniq.end());
    std::fprintf(stderr, "nodes=%llu maximal_k=%zu after_dedupe=%zu\n",
                 (unsigned long long)visited.load(), found.size(), uniq.size());

    char path[512];
    std::snprintf(path, sizeof(path),
        "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/kc_maximal_n%d_k%d.bin", n, K);
    FILE* f = std::fopen(path, "wb");
    if (!f) { std::perror("fopen"); return 1; }
    u64 c = uniq.size();
    std::fwrite(&c, sizeof(c), 1, f);
    if (c) std::fwrite(uniq.data(), sizeof(u64), uniq.size(), f);
    std::fclose(f);
    std::fprintf(stderr, "wrote %s\n", path);
    return 0;
}
