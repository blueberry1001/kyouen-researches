// Measure the n=8 memory requirement without running the full DP: enumerate
// the levels only (no Grundy, no p_rand) and report the peak footprint.
//
// The n=7 run needed 10.5 GB with MAXL=48. With MAXL=20 the per-state
// numerator is 80 B instead of 192 B, a 2.4x cut, but the level enumeration
// also keeps every level resident, so the sum over levels may still dominate.
//
// Usage: prand8_probe <n>
#include "kc_core.h"
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <string>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

using kc::u64;

static double now_s() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

static long rss_kb() {
    std::ifstream f("/proc/self/status");
    std::string k;
    long v = 0;
    while (f >> k) {
        if (k == "VmRSS:") { f >> v; return v; }
    }
    return 0;
}

int main(int argc, char** argv) {
    int n = argc > 1 ? atoi(argv[1]) : 8;
    kc::Board B;
    kc::build_square(B, n);
    std::fprintf(stderr, "n=%d V=%d F=%zu rss=%ld kB\n", n, B.V, B.quads.size(), rss_kb());

    // one bitmask per point: the quads that would complete if we placed it
    std::vector<std::vector<u64>> tpp(B.V);
    for (size_t qi = 0; qi < B.quads.size(); ++qi) {
        u64 q = B.quads[qi];
        for (int p = 0; p < B.V; ++p) {
            if (q & (u64(1) << p)) {
                u64 o = q & ~(u64(1) << p);
                tpp[p].push_back(o);
            }
        }
    }

    u64 full = (B.V >= 64) ? ~u64(0) : ((u64(1) << B.V) - 1);
    std::vector<u64> cur{0}, nxt;
    std::vector<u64> curLM{full}, nxtLM;
    long peak = 0;
    double t0 = now_s();
    for (int k = 0; k <= 40; ++k) {
        long r = rss_kb();
        if (r > peak) peak = r;
        std::fprintf(stderr, "k=%2zu M=%9zu rss=%7ld MB (%.1f s)\n",
                     cur.size() ? (size_t)0 : (size_t)0, cur.size(), r / 1024, now_s() - t0);
        if (cur.empty()) break;
        // legal moves per state
        nxt.clear(); nxtLM.clear();
        for (size_t i = 0; i < cur.size(); ++i) {
            u64 occ = cur[i], lm = 0;
            for (int p = 0; p < B.V; ++p) {
                u64 bit = u64(1) << p;
                if (occ & bit) continue;
                bool ok = true;
                for (u64 t : tpp[p]) if ((occ & t) == t) { ok = false; break; }
                if (ok) lm |= bit;
            }
            u64 c = lm;
            while (c) {
                int v = __builtin_ctzll(c); c &= c - 1;
                nxt.push_back(occ | (u64(1) << v));
            }
        }
        std::sort(nxt.begin(), nxt.end());
        nxt.erase(std::unique(nxt.begin(), nxt.end()), nxt.end());
        cur.swap(nxt);
        long r2 = rss_kb();
        if (r2 > peak) peak = r2;
    }
    std::fprintf(stderr, "PEAK RSS = %ld MB\n", peak / 1024);
    return 0;
}
