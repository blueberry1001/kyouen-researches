// round5_b001_g2.cpp — two-stone Grundy on n=6 for B024
#include "kc_core.h"
#include <cstdio>
#include <cstdlib>
#include <map>
#include <unordered_map>
#include <vector>
using namespace std;
using kc::u64;
using kc::Board;

static Board B;
static unordered_map<u64, int> gmemo;

static int grundy(u64 occ) {
    auto it = gmemo.find(occ);
    if (it != gmemo.end()) return it->second;
    bool seen[64] = {false};
    bool has = false;
    u64 empty = B.full ^ occ;
    int v = 0;
    while (empty) {
        if (empty & 1) {
            u64 bit = u64(1) << v;
            bool ok = true;
            for (u64 t : B.triples_by_pt[v]) {
                if ((occ & t) == t) { ok = false; break; }
            }
            if (ok) {
                has = true;
                int g = grundy(occ | bit);
                if (g < 64) seen[g] = true;
            }
        }
        empty >>= 1; v++;
    }
    if (!has) { gmemo[occ] = 0; return 0; }
    int g = 0;
    while (g < 64 && seen[g]) g++;
    gmemo[occ] = g;
    return g;
}

int main(int argc, char** argv) {
    int n = (argc > 1) ? atoi(argv[1]) : 6;
    kc::build_square(B, n);
    fprintf(stderr, "n=%d V=%d quads=%zu\n", n, B.V, B.quads.size());

    // safe check
    auto is_safe = [&](u64 occ) -> bool {
        for (u64 q : B.quads) if ((occ & q) == q) return false;
        return true;
    };

    // 2-stone
    map<int,int> g2;
    int even_nz = 0;
    for (int i = 0; i < B.V; i++)
        for (int j = i+1; j < B.V; j++) {
            u64 s = (u64(1)<<i) | (u64(1)<<j);
            if (!is_safe(s)) continue;
            int g = grundy(s);
            g2[g]++;
            if (g > 0 && g % 2 == 0) even_nz++;
        }
    printf("n=%d two-stone g hist:", n);
    for (auto& [g,c] : g2) printf("  g=%d:%d", g, c);
    printf("\n  even_nonzero=%d memo=%zu\n", even_nz, gmemo.size());

    // 1-stone
    map<int,int> g1;
    for (int i = 0; i < B.V; i++) g1[grundy(u64(1)<<i)]++;
    printf("n=%d one-stone g hist:", n);
    for (auto& [g,c] : g1) printf("  g=%d:%d", g, c);
    printf("\n");
    return 0;
}
