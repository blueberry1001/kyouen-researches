// B379: embed 8-stone maximal (8x8) into 9x9, try remove<=2 + add to 9-stone maximal.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <array>
#include <algorithm>
#include <chrono>
#include "kc_core.h"

using u64 = uint64_t;
using namespace kc;

static std::vector<u64> load_masks(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) { perror(path); exit(1); }
    u64 c = 0;
    if (fread(&c, 8, 1, f) != 1) exit(2);
    std::vector<u64> v(c);
    if (c && fread(v.data(), 8, c, f) != c) exit(3);
    fclose(f);
    return v;
}

static u64 embed_8to9(u64 m8) {
    u64 out = 0;
    for (int y = 0; y < 8; ++y)
        for (int x = 0; x < 8; ++x)
            if ((m8 >> (y * 8 + x)) & 1) out |= u64(1) << (y * 9 + x);
    return out;
}

int main(int argc, char** argv) {
    const char* binpath = (argc > 1) ? argv[1] : "round4_b371.bin";
    auto masks = load_masks(binpath);
    printf("loaded %zu masks\n", masks.size());
    Board b9;
    build_square(b9, 9);
    printf("9x9 V=%d quads=%zu\n", b9.V, b9.quads.size());

    int n_ok = 0, n_tried = 0;
    int how_hist[4] = {0, 0, 0, 0};  // r0, r1, r2, fail
    // try up to 40 sets (or all if small)
    size_t limit = masks.size();  // all 408
    auto t0 = std::chrono::steady_clock::now();
    for (size_t si = 0; si < limit; ++si) {
        u64 base = embed_8to9(masks[si]);
        ++n_tried;
        bool found = false;
        int how = 3;
        // r=0: add 1
        u64 L = legal_mask(b9, base);
        {
            u64 m = L;
            while (m) {
                int a = __builtin_ctzll(m); m &= m - 1;
                u64 cand = base | (u64(1) << a);
                if (legal_mask(b9, cand) == 0) { found = true; how = 0; break; }
            }
        }
        // r=1: add 2
        if (!found) {
            for (int out = 0; out < 64 && !found; ++out) {
                if (!((base >> out) & 1)) continue;
                u64 b1 = base & ~(u64(1) << out);
                u64 L1 = legal_mask(b9, b1);
                std::vector<int> ls;
                for (int i = 0; i < 81; ++i) if ((L1 >> i) & 1) ls.push_back(i);
                for (size_t i = 0; i < ls.size() && !found; ++i)
                    for (size_t j = i + 1; j < ls.size() && !found; ++j) {
                        u64 cand = b1 | (u64(1) << ls[i]) | (u64(1) << ls[j]);
                        if (!legal_mask(b9, b1) /*dummy*/) {}
                        // safe check via can_add twice
                        if (!can_add(b9, b1, ls[i])) continue;
                        if (!can_add(b9, b1 | (u64(1) << ls[i]), ls[j])) continue;
                        if (legal_mask(b9, cand) == 0) { found = true; how = 1; }
                    }
            }
        }
        // r=2: add 3 (only if legal set is small)
        if (!found) {
            for (int o1 = 0; o1 < 81 && !found; ++o1) {
                if (!((base >> o1) & 1)) continue;
                for (int o2 = o1 + 1; o2 < 81 && !found; ++o2) {
                    if (!((base >> o2) & 1)) continue;
                    u64 b2 = base & ~(u64(1) << o1) & ~(u64(1) << o2);
                    u64 L2 = legal_mask(b9, b2);
                    std::vector<int> ls;
                    for (int i = 0; i < 81; ++i) if ((L2 >> i) & 1) ls.push_back(i);
                    if (ls.size() > 18) continue;
                    for (size_t i = 0; i < ls.size() && !found; ++i)
                        for (size_t j = i + 1; j < ls.size() && !found; ++j)
                            for (size_t k = j + 1; k < ls.size() && !found; ++k) {
                                u64 c2 = b2 | (u64(1) << ls[i]);
                                if (!can_add(b9, b2, ls[i])) continue;
                                if (!can_add(b9, c2, ls[j])) continue;
                                c2 |= (u64(1) << ls[j]);
                                if (!can_add(b9, c2, ls[k])) continue;
                                c2 |= (u64(1) << ls[k]);
                                if (legal_mask(b9, c2) == 0) { found = true; how = 2; }
                            }
                }
            }
        }
        if (found) { ++n_ok; how_hist[how]++; printf("  set %zu: FOUND r=%d\n", si, how); }
        else printf("  set %zu: not found\n", si);
        fflush(stdout);
        if (si % 5 == 0) {
            auto t1 = std::chrono::steady_clock::now();
            printf("  progress %zu/%zu ok=%d time=%.1fs\n", si, limit, n_ok,
                   std::chrono::duration<double>(t1 - t0).count());
            fflush(stdout);
        }
    }
    printf("SUMMARY tried=%d ok=%d r0=%d r1=%d r2=%d fail=%d\n", n_tried, n_ok,
           how_hist[0], how_hist[1], how_hist[2], how_hist[3]);
    FILE* f = fopen("round5_b301_b379.json", "w");
    if (f) {
        fprintf(f, "{\"n_tried\": %d, \"n_success\": %d, \"how\": {\"r0\": %d, \"r1\": %d, \"r2\": %d, \"fail\": %d}}\n",
                n_tried, n_ok, how_hist[0], how_hist[1], how_hist[2], how_hist[3]);
        fclose(f);
    }
    return 0;
}
