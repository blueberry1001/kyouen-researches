// Boundary test: for small k, count maximal sets our DFS accepts and compare
// with the shared core's kc::is_maximal over ALL C(V,k) subsets.
#include "kc_core.h"
#include <cstdio>
#include <vector>
#include <algorithm>
#include <functional>
using kc::u64;
using kc::Board;
static Board B;
static int V, ntri, N;
static std::vector<int> st, li;
static int idx(int a, int b, int c) { return a + b * (b - 1) / 2 + c * (c - 1) * (c - 2) / 6; }

static void add_blocked(int a, int b, int c, u64& blk) {
    int ti = idx(a, b, c);
    for (int t = st[ti]; t < st[ti + 1]; ++t) blk |= 1ULL << li[t];
}

static int K = 5;
static long long n_leaf = 0, n_max = 0;

static void dfs(u64 occ, u64 blk, u64 cand, int size, int* ch) {
    if (size == K) {
        ++n_leaf;
        if ((blk | occ) == B.full) ++n_max;
        return;
    }
    for (int p = ch[size - 1] + 1; p < V; ++p) {
        u64 bit = 1ULL << p;
        if ((blk >> p) & 1) continue;
        u64 nb = blk;
        for (int i = 0; i < size; ++i)
            for (int j = i + 1; j < size; ++j) add_blocked(ch[i], ch[j], p, nb);
        ch[size] = p;
        dfs(occ | bit, nb, 0ULL, size + 1, ch);
    }
}

int main(int argc, char** argv) {
    N = argc > 1 ? atoi(argv[1]) : 4;
    K = argc > 2 ? atoi(argv[2]) : 5;
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
    int ch[16];
    for (int b = 1; b <= V - 2; ++b)
        for (int a = 0; a < b; ++a) {
            ch[0] = a; ch[1] = b;
            dfs((1ULL << a) | (1ULL << b), 0ULL, B.full & ~((1ULL << (b + 1)) - 1), 2, ch);
        }
    // reference: ALL C(V,K) subsets that are BOTH safe and maximal
    long long ref_safe = 0, ref = 0;
    std::function<void(int, int, u64)> rec = [&](int start, int d, u64 s) {
        if (d == K) {
            bool safe = true;
            for (u64 q : B.quads)
                if ((s & q) == q) { safe = false; break; }
            if (safe) ++ref_safe;
            if (safe && kc::is_maximal(B, s)) ++ref;
            return;
        }
        for (int p = start; p < V; ++p) rec(p + 1, d + 1, s | (1ULL << p));
    };
    rec(0, 0, 0);
    std::printf("n=%d k=%d  dfs_leaves=%lld dfs_maximal=%lld  brute_safe=%lld "
                "brute_safe_and_maximal=%lld  %s\n",
                N, K, n_leaf, n_max, ref_safe, ref,
                (n_max == ref && n_leaf == ref_safe) ? "MATCH" : "MISMATCH");
    return 0;
}
