// Round5 B207/B209/B210: n x n two-point deletion — K and empty g.
// Usage: ./round5_b201_del2 <n>
#include "kc_core.h"
#include <bits/stdc++.h>
using namespace kc;
using namespace std;

struct DelBoard {
    int V;
    u64 full;
    vector<vector<u64>> triples_by_pt;
    vector<int> xs, ys;
};

DelBoard build_del(int n, const vector<int>& del_ids) {
    DelBoard b;
    vector<pair<int,int>> pts;
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int id = y * n + x;
            if (find(del_ids.begin(), del_ids.end(), id) != del_ids.end()) continue;
            pts.push_back({x, y});
        }
    b.V = (int)pts.size();
    b.full = (b.V >= 64) ? ~u64(0) : ((u64(1) << b.V) - 1);
    b.triples_by_pt.assign(b.V, {});
    b.xs.resize(b.V); b.ys.resize(b.V);
    vector<array<long long,4>> rows(b.V);
    for (int i = 0; i < b.V; ++i) {
        int x = pts[i].first, y = pts[i].second;
        b.xs[i] = x; b.ys[i] = y;
        rows[i] = {(long long)x*x + (long long)y*y, x, y, 1};
    }
    for (int a = 0; a < b.V - 3; ++a)
    for (int c1 = a+1; c1 < b.V - 2; ++c1)
    for (int c2 = c1+1; c2 < b.V - 1; ++c2)
    for (int d = c2+1; d < b.V; ++d) {
        int ids[4] = {a,c1,c2,d};
        long long m[4][4];
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = rows[ids[i]][j];
        if (det4(m) != 0) continue;
        for (int t = 0; t < 4; ++t) {
            u64 o = 0;
            for (int s = 0; s < 4; ++s) if (s != t) o |= u64(1) << ids[s];
            b.triples_by_pt[ids[t]].push_back(o);
        }
    }
    return b;
}

u64 legal_mask_del(const DelBoard& b, u64 occ) {
    u64 out = 0;
    u64 empty = b.full & ~occ;
    while (empty) {
        int p = __builtin_ctzll(empty);
        empty &= empty - 1;
        bool ok = true;
        for (u64 t : b.triples_by_pt[p]) {
            if ((occ & t) == t) { ok = false; break; }
        }
        if (ok) out |= u64(1) << p;
    }
    return out;
}

struct Solver {
    const DelBoard& b;
    unordered_map<u64, uint8_t> memo;
    Solver(const DelBoard& bb) : b(bb) { memo.reserve(1 << 20); }
    uint8_t ev(u64 occ) {
        auto it = memo.find(occ);
        if (it != memo.end()) return it->second;
        u64 mv = legal_mask_del(b, occ);
        if (!mv) { memo[occ] = 0; return 0; }
        uint32_t seen = 0;
        while (mv) {
            int p = __builtin_ctzll(mv);
            mv &= mv - 1;
            uint8_t g = ev(occ | (u64(1) << p));
            if (g < 32) seen |= 1u << g;
        }
        uint8_t g = 0;
        while (seen & (1u << g)) ++g;
        memo[occ] = g;
        return g;
    }
};

int max_safe(const DelBoard& b) {
    int best = 0;
    function<void(u64,u64,int)> dfs = [&](u64 occ, u64 cand, int size) {
        if (size > best) best = size;
        if (!cand) return;
        if (size + __builtin_popcountll(cand) <= best) return;
        while (cand) {
            u64 bit = cand & -cand;
            int v = __builtin_ctzll(cand);
            cand ^= bit;
            u64 nxt = occ | bit;
            bool ok = true;
            for (u64 t : b.triples_by_pt[v]) {
                if ((nxt & t) == t) { ok = false; break; }
            }
            if (!ok) continue;
            u64 remain = cand;
            u64 bad = 0;
            for (u64 t : b.triples_by_pt[v]) {
                if ((nxt & t) == t) continue;
                u64 missing = t & ~nxt;
                if (missing && (missing & (missing - 1)) == 0) bad |= missing;
            }
            dfs(nxt, remain & ~bad, size + 1);
        }
    };
    dfs(0, b.full, 0);
    return best;
}

int main(int argc, char** argv) {
    int n = atoi(argv[1]);
    // baseline
    {
        DelBoard b = build_del(n, {});
        Solver s(b);
        uint8_t g0 = s.ev(0);
        int K = max_safe(b);
        printf("{\"job\":\"base\",\"n\":%d,\"g0\":%u,\"K\":%d,\"n_pos\":%zu}\n", n, g0, K, s.memo.size());
        fflush(stdout);
    }
    int V = n * n;
    int count = 0;
    for (int i = 0; i < V; ++i)
    for (int j = i+1; j < V; ++j) {
        DelBoard b = build_del(n, {i, j});
        int K = max_safe(b);
        Solver s(b);
        uint8_t g0 = s.ev(0);
        printf("{\"job\":\"del2\",\"n\":%d,\"i\":%d,\"j\":%d,\"di\":[%d,%d],\"dj\":[%d,%d],\"g0\":%u,\"K\":%d,\"n_pos\":%zu}\n",
               n, i, j, i%n, i/n, j%n, j/n, g0, K, s.memo.size());
        fflush(stdout);
        ++count;
        if (count % 20 == 0) fprintf(stderr, "done %d pairs\n", count);
    }
    return 0;
}
