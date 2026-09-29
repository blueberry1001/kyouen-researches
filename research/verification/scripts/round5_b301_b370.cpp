// B370: classify why 1-out 2-in shrink candidates fail on 8-stone maximal sets.
// For each of 408 maximal 8-sets T: remove one stone, try add two others.
// Fail reasons: (a) new forbidden quad, (b) uncovered legal point remains.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
#include "kc_core.h"

using u64 = uint64_t;
using namespace kc;

static std::vector<u64> load_masks(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) { perror(path); exit(1); }
    u64 c = 0;
    fread(&c, 8, 1, f);
    std::vector<u64> v(c);
    if (c) fread(v.data(), 8, c, f);
    fclose(f);
    return v;
}

int main(int argc, char** argv) {
    const char* binpath = (argc > 1) ? argv[1] : "round4_b371.bin";
    auto masks = load_masks(binpath);
    Board b;
    build_square(b, 8);
    long long total = 0, fail_forbidden = 0, fail_uncovered = 0, success = 0;
    for (u64 T : masks) {
        for (int out = 0; out < 64; ++out) {
            if (!((T >> out) & 1)) continue;
            u64 base = T & ~(u64(1) << out);
            u64 empty = b.full & ~base;
            std::vector<int> es;
            for (int i = 0; i < 64; ++i) if ((empty >> i) & 1) es.push_back(i);
            for (size_t i = 0; i < es.size(); ++i)
                for (size_t j = i + 1; j < es.size(); ++j) {
                    u64 cand = base | (u64(1) << es[i]) | (u64(1) << es[j]);
                    ++total;
                    if (!is_maximal(b, cand)) {
                        // distinguish: unsafe vs safe-but-not-maximal
                        // safe iff no quad fully inside
                        bool safe = true;
                        for (u64 q : b.quads) {
                            if ((cand & q) == q) { safe = false; break; }
                        }
                        if (!safe) ++fail_forbidden;
                        else ++fail_uncovered;
                    } else {
                        ++success;
                    }
                }
        }
    }
    printf("total=%lld fail_forbidden=%lld fail_uncovered=%lld success=%lld\n",
           total, fail_forbidden, fail_uncovered, success);
    FILE* f = fopen("round5_b301_b370.json", "w");
    if (f) {
        fprintf(f, "{\"n_sets\": %zu, \"n_candidates\": %lld, \"fail_forbidden_quad\": %lld, \"fail_uncovered_point\": %lld, \"success_size9_maximal\": %lld}\n",
                masks.size(), total, fail_forbidden, fail_uncovered, success);
        fclose(f);
    }
    return 0;
}
