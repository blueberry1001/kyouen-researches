// B370 follow-up: full 408 classification of shrink/deform candidates.
// Modes: 2-out 1-in (8->7), 3-out 2-in (8->7), 1-out 1-in (8->8), 1-out 2-in (8->9).
// Fail classes: fail_forbidden (unsafe), fail_uncovered (safe but not maximal), success (maximal).
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
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

// Safety of cand, checking only quads that contain any of add[0..nadd).
static bool safe_touching(const Board& b, u64 cand, const int* add, int nadd) {
    for (int t = 0; t < nadd; ++t) {
        for (u64 tr : b.triples_by_pt[add[t]]) {
            if ((cand & tr) == tr) return false;
        }
    }
    return true;
}

int main(int argc, char** argv) {
    const char* binpath = (argc > 1) ? argv[1] : "round4_b371.bin";
    auto masks = load_masks(binpath);
    Board b;
    build_square(b, 8);
    printf("loaded %zu masks quads=%zu\n", masks.size(), b.quads.size());

    long long t21=0, f21=0, u21=0, s21=0;
    long long t32=0, f32=0, u32=0, s32=0;
    long long t11=0, f11=0, u11=0, s11=0;
    long long t12=0, f12=0, u12=0, s12=0;

    std::vector<int> stones;
    std::vector<int> empty;

    for (size_t si = 0; si < masks.size(); ++si) {
        u64 T = masks[si];
        stones.clear(); empty.clear();
        for (int i = 0; i < 64; ++i) {
            if ((T >> i) & 1) stones.push_back(i);
            else empty.push_back(i);
        }
        int ns = (int)stones.size();
        int ne = (int)empty.size();
        if (ns != 8) continue;

        // 2-out 1-in (size 7). s_8=8 so no 7-stone maximal exists: safe => fail_uncovered.
        for (int i = 0; i < ns; ++i) {
            for (int j = i + 1; j < ns; ++j) {
                u64 base = T & ~(u64(1) << stones[i]) & ~(u64(1) << stones[j]);
                for (int e = 0; e < ne; ++e) {
                    u64 cand = base | (u64(1) << empty[e]);
                    int add[1] = {empty[e]};
                    ++t21;
                    if (!safe_touching(b, cand, add, 1)) ++f21;
                    else ++u21;  // cannot be maximal at size 7
                }
            }
        }

        // 3-out 2-in (size 7). same: safe => fail_uncovered.
        for (int i = 0; i < ns; ++i) {
            for (int j = i + 1; j < ns; ++j) {
                for (int k = j + 1; k < ns; ++k) {
                    u64 base = T & ~(u64(1) << stones[i]) & ~(u64(1) << stones[j]) & ~(u64(1) << stones[k]);
                    for (int a = 0; a < ne; ++a) {
                        for (int b2 = a + 1; b2 < ne; ++b2) {
                            u64 cand = base | (u64(1) << empty[a]) | (u64(1) << empty[b2]);
                            int add[2] = {empty[a], empty[b2]};
                            ++t32;
                            if (!safe_touching(b, cand, add, 2)) ++f32;
                            else ++u32;
                        }
                    }
                }
            }
        }

        // 1-out 1-in
        for (int i = 0; i < ns; ++i) {
            u64 base = T & ~(u64(1) << stones[i]);
            for (int e = 0; e < ne; ++e) {
                u64 cand = base | (u64(1) << empty[e]);
                int add[1] = {empty[e]};
                ++t11;
                if (!safe_touching(b, cand, add, 1)) ++f11;
                else if (is_maximal(b, cand)) ++s11;
                else ++u11;
            }
        }

        // 1-out 2-in
        for (int i = 0; i < ns; ++i) {
            u64 base = T & ~(u64(1) << stones[i]);
            for (int a = 0; a < ne; ++a) {
                for (int b2 = a + 1; b2 < ne; ++b2) {
                    u64 cand = base | (u64(1) << empty[a]) | (u64(1) << empty[b2]);
                    int add[2] = {empty[a], empty[b2]};
                    ++t12;
                    if (!safe_touching(b, cand, add, 2)) ++f12;
                    else if (is_maximal(b, cand)) ++s12;
                    else ++u12;
                }
            }
        }

        if ((si + 1) % 128 == 0) {
            printf("progress %zu/%zu\n", si + 1, masks.size());
            fflush(stdout);
        }
    }

    printf("2out1in  total=%lld fail_forbidden=%lld fail_uncovered=%lld success=%lld\n", t21, f21, u21, s21);
    printf("3out2in  total=%lld fail_forbidden=%lld fail_uncovered=%lld success=%lld\n", t32, f32, u32, s32);
    printf("1out1in  total=%lld fail_forbidden=%lld fail_uncovered=%lld success=%lld\n", t11, f11, u11, s11);
    printf("1out2in  total=%lld fail_forbidden=%lld fail_uncovered=%lld success=%lld\n", t12, f12, u12, s12);

    FILE* f = fopen("round5_b301_b370f.json", "w");
    if (f) {
        fprintf(f,
            "{\n"
            "  \"n_sets\": %zu,\n"
            "  \"2out1in\": {\"total\": %lld, \"fail_forbidden_quad\": %lld, \"fail_uncovered_point\": %lld, \"success_maximal\": %lld},\n"
            "  \"3out2in\": {\"total\": %lld, \"fail_forbidden_quad\": %lld, \"fail_uncovered_point\": %lld, \"success_maximal\": %lld},\n"
            "  \"1out1in\": {\"total\": %lld, \"fail_forbidden_quad\": %lld, \"fail_uncovered_point\": %lld, \"success_maximal\": %lld},\n"
            "  \"1out2in\": {\"total\": %lld, \"fail_forbidden_quad\": %lld, \"fail_uncovered_point\": %lld, \"success_maximal\": %lld}\n"
            "}\n",
            masks.size(),
            t21, f21, u21, s21,
            t32, f32, u32, s32,
            t11, f11, u11, s11,
            t12, f12, u12, s12);
        fclose(f);
    }
    return 0;
}
