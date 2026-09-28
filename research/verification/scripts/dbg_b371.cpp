// Audit the triple-completion table used by round4_b371.cpp and cross-check the
// DFS against brute force at small depths.
#include "kc_core.h"
#include <cstdio>
#include <vector>
#include <algorithm>
#include <functional>
using kc::u64;
using kc::Board;
static Board B;
static int V, ntri;
static std::vector<int> st, li;
static int idx(int a, int b, int c) { return a + b * (b - 1) / 2 + c * (c - 1) * (c - 2) / 6; }

static bool quad(u64 s) {
    for (u64 q : B.quads) if (q == s) return true;
    return false;
}

int main(int argc, char** argv) {
    int N = argc > 1 ? atoi(argv[1]) : 5;
    int D = argc > 2 ? atoi(argv[2]) : 4;
    kc::build_square(B, N);
    V = B.V;
    ntri = V * (V - 1) * (V - 2) / 6;
    std::vector<int> cnt(ntri, 0);
    for (u64 q : B.quads) {
        int ids[4], t = 0;
        for (int i = 0; i < V; ++i) if ((q >> i) & 1) ids[t++] = i;
        for (int s = 0; s < 4; ++s) {
            int o[3], m = 0;
            for (int r = 0; r < 4; ++r) if (r != s) o[m++] = ids[r];
            cnt[idx(o[0], o[1], o[2])]++;
        }
    }
    st.assign(ntri + 1, 0);
    int acc = 0;
    for (int i = 0; i < ntri; ++i) { st[i] = acc; acc += cnt[i]; }
    st[ntri] = acc;
    li.assign(acc, -1);
    std::vector<int> fill(st.begin(), st.end() - 1);
    for (u64 q : B.quads) {
        int ids[4], t = 0;
        for (int i = 0; i < V; ++i) if ((q >> i) & 1) ids[t++] = i;
        for (int s = 0; s < 4; ++s) {
            int o[3], m = 0;
            for (int r = 0; r < 4; ++r) if (r != s) o[m++] = ids[r];
            int ti = idx(o[0], o[1], o[2]);
            li[fill[ti]++] = ids[s];
        }
    }
    // audit: every listed completion must really form a quad with the triple
    long long bad = 0, listed = 0, dup = 0;
    for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b)
            for (int c = b + 1; c < V; ++c) {
                int ti = idx(a, b, c);
                u64 seen = 0;
                for (int t = st[ti]; t < st[ti + 1]; ++t) {
                    int p = li[t];
                    ++listed;
                    if (p == a || p == b || p == c) { ++bad; continue; }
                    if (seen & (1ULL << p)) { ++dup; continue; }
                    seen |= 1ULL << p;
                    u64 q = (1ULL << a) | (1ULL << b) | (1ULL << c) | (1ULL << p);
                    if (!quad(q)) ++bad;
                }
            }
    std::printf("n=%d V=%d ntri=%d listed=%lld bad=%lld dup=%lld\n", N, V, ntri, listed, bad, dup);

    // brute-force count of safe D-subsets, compared with the DFS node count
    long long bf = 0;
    std::function<void(int, int, u64)> rec = [&](int start, int d, u64 s) {
        if (d == D) {
            for (u64 q : B.quads) if ((s & q) == q) return;
            ++bf;
            return;
        }
        for (int p = start; p < V; ++p) rec(p + 1, d + 1, s | (1ULL << p));
    };
    rec(0, 0, 0);
    std::printf("brute-force safe %d-subsets = %lld\n", D, bf);

    // DFS node count at depth D (must equal bf)
    long long nodes[20] = {0};
    int ch[16];
    std::function<void(u64, u64, int)> go = [&](u64 blk, u64 cand, int size) {
        ++nodes[size];
        if (size == D) return;
        u64 c = cand;
        while (c) {
            int p = __builtin_ctzll(c);
            c &= c - 1;
            if ((blk >> p) & 1) continue;
            u64 nb = blk;
            for (int i = 0; i < size; ++i)
                for (int j = i + 1; j < size; ++j) {
                    int t3[3] = {ch[i], ch[j], p};
                    std::sort(t3, t3 + 3);
                    int ti = idx(t3[0], t3[1], t3[2]);
                    for (int t = st[ti]; t < st[ti + 1]; ++t) nb |= 1ULL << li[t];
                }
            ch[size] = p;
            go(nb, c & ~nb, size + 1);
        }
    };
    for (int b = 1; b <= V - 2; ++b)
        for (int a = 0; a < b; ++a) {
            ch[0] = a; ch[1] = b;
            go(0ULL, B.full & ~((1ULL << (b + 1)) - 1), 2);
        }
    for (int d = 2; d <= D; ++d) std::printf("dfs depth %d: %lld\n", d, nodes[d]);
    return 0;
}
