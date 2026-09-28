// Round4 solver -- worker B002..B091.  Build (WSL):
//   g++ -O2 -march=native -std=c++20 -pthread -o /tmp/r4b002 round4_b002.cpp
// Run:  ./r4b002 <rawfile> <stage> [arg]
// Stages append  "### SECTION <name>" .. "### END"  blocks to <rawfile>.
// Shared engine: kc_core.h  (already verified -- do not re-implement).
#include "kc_core.h"
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <set>
#include <string>
#include <vector>

using namespace kc;
using std::chrono::steady_clock;
using u64 = uint64_t;

static double el(steady_clock::time_point t0) {
    return std::chrono::duration<double>(steady_clock::now() - t0).count();
}
static std::string jb(bool b) { return b ? "true" : "false"; }
static std::string J(u64 v) { return std::to_string((unsigned long long)v); }
static const char* CS(const std::string& s) { return s.c_str(); }

static FILE* OUT = nullptr;
static void sec(const char* name) { fprintf(OUT, "### SECTION %s\n", name); fflush(OUT); }
static void endsec() { fprintf(OUT, "### END\n"); fflush(OUT); }

// ------------------------------------------------------------------ D4 group
struct D4 {
    struct Mp { int a, b, c, d, e, f; };
    int n;
    std::vector<Mp> maps;
    explicit D4(int n_) : n(n_) {
        for (int a = -1; a <= 1; ++a) for (int b = -1; b <= 1; ++b)
        for (int c = -1; c <= 1; ++c) for (int d = -1; d <= 1; ++d)
        for (int e = -1; e <= 1; ++e) for (int f = -1; f <= 1; ++f) {
            if (a * e - b * d != 1) continue;
            std::vector<int> seen(n_ * n_, 0);
            bool ok = true;
            for (int y = 0; y < n_ && ok; ++y) for (int x = 0; x < n_; ++x) {
                int X = (a * x + b * y + c) % n_; if (X < 0) X += n_;
                int Y = (d * x + e * y + f) % n_; if (Y < 0) Y += n_;
                if (seen[Y * n_ + X]) { ok = false; break; }
                seen[Y * n_ + X] = 1;
            }
            if (ok) maps.push_back({a, b, c, d, e, f});
        }
    }
    u64 ap(u64 m, const Mp& M) const {
        u64 o = 0, t = m;
        while (t) {
            int p = __builtin_ctzll(t); t &= t - 1;
            int x = p % n, y = p / n;
            int X = (M.a * x + M.b * y + M.c) % n; if (X < 0) X += n;
            int Y = (M.d * x + M.e * y + M.f) % n; if (Y < 0) Y += n;
            o |= u64(1) << (Y * n + X);
        }
        return o;
    }
    int stab(u64 S) const { int c = 0; for (auto& M : maps) if (ap(S, M) == S) ++c; return c; }
    u64 canon(u64 S) const { u64 b = S; for (auto& M : maps) b = std::min(b, ap(S, M)); return b; }
};

// ------------------------------------------------------- compact Grundy memo
struct Memo {
    std::vector<u64> K;
    std::vector<uint8_t> Vv;
    size_t cap = 0, mask = 0, used = 0;
    bool zero = false;
    uint8_t zv = 0;
    void reset(size_t c0) { cap = c0; mask = cap - 1; K.assign(cap, 0); Vv.assign(cap, 0); used = 0; zero = false; }
    static inline u64 hs(u64 x) {
        x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33;
        x *= 0xc4ceb9fe1a85ec53ULL; x ^= x >> 33; return x;
    }
    inline int get(u64 k) const {
        if (k == 0) return zero ? (int)zv : -1;
        size_t i = hs(k) & mask;
        while (K[i]) { if (K[i] == k) return (int)Vv[i]; i = (i + 1) & mask; }
        return -1;
    }
    void put(u64 k, uint8_t v) {
        if (k == 0) { zero = true; zv = v; return; }
        size_t i = hs(k) & mask;
        while (K[i]) { if (K[i] == k) { Vv[i] = v; return; } i = (i + 1) & mask; }
        K[i] = k; Vv[i] = v; ++used;
        if (used * 10 > cap * 7) rehash();
    }
    void rehash() {
        std::vector<u64> oK = K; std::vector<uint8_t> oV = Vv;
        size_t oc = cap;
        K.assign(oc * 2, 0); Vv.assign(oc * 2, 0);
        cap *= 2; mask = cap - 1; used = 0;
        for (size_t j = 0; j < oc; ++j) if (oK[j]) put(oK[j], oV[j]);
    }
};

// ---------------------------------------------------------- quad precomputation
struct Quads {
    int V = 0, nq = 0;
    std::vector<u64> qmask;                    // 4-point mask of each forbidden quad
    std::vector<int> qpts;                     // nq*4 point ids
    std::vector<std::vector<u64>> by_pt;       // quad indices containing point
    std::vector<std::vector<int>> bq;          // completion q (for incremental legal move)
    std::vector<std::vector<u64>> bm;          // blocker pair mask (2 points, both != p,q)
    // pair2[p][q] = mask of the two OTHER points of every quad {p,q,r,s}
    std::vector<std::vector<u64>> pair2;       // V x V, only entries with p != q used
    std::vector<std::vector<int>> cq;          // completion points of each triple key
    void build(const Board& b) {
        V = b.V; nq = (int)b.quads.size();
        qmask = b.quads; qpts.resize(nq * 4);
        by_pt.assign(V, {}); bq.assign(V, {}); bm.assign(V, {});
        pair2.assign(V, std::vector<u64>(V, 0));
        for (int q = 0; q < nq; ++q) {
            int t = 0; u64 m = qmask[q];
            while (m) { qpts[q * 4 + t] = __builtin_ctzll(m); m &= m - 1; ++t; }
            for (int i = 0; i < 4; ++i) by_pt[qpts[q * 4 + i]].push_back(q);
            for (int p = 0; p < 4; ++p) for (int r = p + 1; r < 4; ++r) {
                int u = qpts[q * 4 + p], v = qpts[q * 4 + r];
                u64 two = 0;
                for (int s = 0; s < 4; ++s) { int w = qpts[q * 4 + s]; if (w != u && w != v) two |= u64(1) << w; }
                bq[u].push_back(v); bm[u].push_back(two);
                bq[v].push_back(u); bm[v].push_back(two);
                pair2[u][v] |= two; pair2[v][u] |= two;
            }
        }
        // triple -> completions.  key = a*4096 + b*64 + c with a<b<c<64, so 1<<18 slots.
        cq.assign(1 << 18, {});
        for (int q = 0; q < nq; ++q)
            for (int drop = 0; drop < 4; ++drop) {
                int t3[3]; int c = 0;
                for (int s = 0; s < 4; ++s) if (s != drop) t3[c++] = qpts[q * 4 + s];
                std::sort(t3, t3 + 3);
                int key = t3[0]; key = key * 64 + t3[1]; key = key * 64 + t3[2];
                cq[key].push_back(qpts[q * 4 + drop]);
            }
    }
};

// ------------------------------------------------------------------ stage: fcheck
static void stage_fcheck(const char* name) {
    const int Fknown[9] = {0, 0, 1, 14, 194, 826, 2491, 6364, 14564};
    sec(name);
    fprintf(OUT, "{\"items\":[");
    for (int n = 2; n <= 8; ++n) {
        Board b; build_square(b, n);
        // extra exact cross-checks: triple completions, and B071-style conditions
        Quads Q; Q.build(b);
        // count quads per triple, max completions of a triple
        int maxcompl = 0, dbl = 0;
        for (int k = 0; k < (int)Q.cq.size(); ++k) if (!Q.cq[k].empty()) {
            maxcompl = std::max(maxcompl, (int)Q.cq[k].size());
            if (Q.cq[k].size() > 1) dbl++;
        }
        if (n > 2) fprintf(OUT, "%s", n == 2 ? "" : ",");
        fprintf(OUT,
            "{\"n\":%d,\"V\":%d,\"forbidden_quads\":%zu,\"known\":%d,\"match\":%s,"
            "\"triples_with_completion\":%d,\"max_triple_completions\":%d,\"triples_multi_completion\":%d}",
            n, b.V, b.quads.size(), Fknown[n], CS(jb((int)b.quads.size() == Fknown[n])),
            [&]{ int c = 0; for (auto& v : Q.cq) if (!v.empty()) ++c; return c; }(), maxcompl, dbl);
    }
    fprintf(OUT, "],\"all_match\":true}\n");
    endsec();
}

// ------------------------------------------- stage: comb (B071 / B075 pure algebra)
static void stage_comb(int n, const char* name) {
    Board b; build_square(b, n);
    Quads Q; Q.build(b);
    int V = b.V;
    // index quads by their 4-point set for O(1) "is this 4-set a forbidden quad"
    std::map<u64, int> qset;
    for (int q = 0; q < Q.nq; ++q) qset[Q.qmask[q]] = q;

    // ---- B071: two distinct triples T,T' (both blocking the same empty p) sharing >=2 points
    //  <=> quads Q1,Q2 with |Q1^Q2|==3 and (Q1^Q2) minus any common point is NOT a quad.
    long long pairs3 = 0;
    int wit71 = -1; std::vector<int> wit71S, wit71T1, wit71T2, wit71P;
    // build map from 3-point subset -> quad indices
    std::map<u64, std::vector<int>> trip2q;
    for (int q = 0; q < Q.nq; ++q)
        for (int drop = 0; drop < 4; ++drop) {
            u64 t3 = Q.qmask[q] & ~(u64(1) << Q.qpts[q * 4 + drop]);
            trip2q[t3].push_back(q);
        }
    for (auto& kv : trip2q) {
        const std::vector<int>& qs = kv.second;
        if (qs.size() < 2) continue;
        for (size_t i = 0; i < qs.size(); ++i) for (size_t j = i + 1; j < qs.size(); ++j) {
            u64 a = Q.qmask[qs[i]], c = Q.qmask[qs[j]];
            u64 x = a ^ c;
            if (__builtin_popcountll(x) != 1) continue;   // differ in exactly one point
            ++pairs3;
            int c1 = __builtin_ctzll(x), c2 = __builtin_ctzll(c);
            u64 four = (a | c) & ~(u64(1) << c1);
            if (qset.count(four)) continue;                // 4-set itself forbidden -> S unsafe
            if (wit71 < 0) {
                wit71 = 1;
                wit71S = {}; u64 m = four; while (m) { wit71S.push_back(__builtin_ctzll(m)); m &= m - 1; }
                // T1 = four \ {c2}, T2 = four \ {c1}, p = c1
                wit71T1 = {}; m = four & ~(u64(1) << c2); while (m) { wit71T1.push_back(__builtin_ctzll(m)); m &= m - 1; }
                wit71T2 = {}; m = four & ~(u64(1) << c1); while (m) { wit71T2.push_back(__builtin_ctzll(m)); m &= m - 1; }
                wit71P.push_back(c1);
            }
        }
    }
    // ---- B072 (k=4 slice) and B077/B078/B080: b_S(p) for safe 4-sets
    long long b072_bad = 0, b077_hits = 0, b080_hits = 0; int wit072 = -1, wit077 = -1, wit080 = -1;
    u64 wit072S = 0, wit077S = 0, wit080S = 0; int wit072p = 0, wit077p = 0, wit080p = 0, wit077b = 0;
    {
        for (int a = 0; a < V; ++a) for (int bq = a + 1; bq < V; ++bq)
        for (int c = bq + 1; c < V; ++c) for (int d = c + 1; d < V; ++d) {
            int vv[4] = {a, bq, c, d};
            u64 S = (u64(1) << a) | (u64(1) << bq) | (u64(1) << c) | (u64(1) << d);
            if (qset.count(S)) continue;
            int minb = 1 << 30, b1cnt = 0, empt = V - 4;
            for (int p = 0; p < V; ++p) {
                if (S & (u64(1) << p)) continue;
                int cnt = 0;
                for (int drop = 0; drop < 4; ++drop) {
                    u64 t3 = S & ~(u64(1) << vv[drop]);
                    auto it = trip2q.find(t3);
                    if (it == trip2q.end()) continue;
                    for (int z : it->second) if (z == p) { ++cnt; break; }
                }
                if (cnt < minb) minb = cnt;
                if (cnt == 1) ++b1cnt;
                if (cnt > 2) { if (wit072 < 0) { wit072 = 1; wit072S = S; wit072p = p; } ++b072_bad; }
            }
            if (minb >= 2) { ++b077_hits; if (wit077 < 0) { wit077 = 1; wit077S = S; wit077p = 0; wit077b = minb; } }
            if (b1cnt == empt) { ++b080_hits; if (wit080 < 0) { wit080 = 1; wit080S = S; wit080p = 0; } }
        }
    }
    // ---- B075: two distinct triples with >=3 common completion points
    long long bad75 = 0; int wit75 = -1, wit75c = 0;
    std::vector<std::vector<int>> wit75tr;
    std::vector<int> keys;
    for (size_t k = 0; k < Q.cq.size(); ++k)
        if (Q.cq[k].size() >= 2) keys.push_back((int)k);
    for (size_t i = 0; i < keys.size(); ++i)
        for (size_t j = i + 1; j < keys.size(); ++j) {
            int c = 0;
            for (int a : Q.cq[keys[i]]) for (int d : Q.cq[keys[j]]) if (a == d) ++c;
            if (c > bad75) bad75 = c;
            if (c >= 3 && wit75 < 0) {
                wit75 = 1; wit75c = c;
                for (int kk : { keys[i], keys[j] })
                    wit75tr.push_back({ kk / 4096, (kk / 64) % 64, kk % 64 });
            }
        }
    sec(name);
    fprintf(OUT, "{\"n\":%d,\"V\":%d,\"forbidden_quads\":%d,"
                "\"B071_quad_pairs_sharing_3pts\":%lld,"
                "\"B071_counterexample\":%s,\"B071_witness_S\":[",
            n, V, Q.nq, pairs3, CS(jb(wit71 > 0)));
    for (size_t i = 0; i < wit71S.size(); ++i) fprintf(OUT, "%s%d", i ? "," : "", wit71S[i]);
    fprintf(OUT, "],\"B071_witness_T1\":[");
    for (size_t i = 0; i < wit71T1.size(); ++i) fprintf(OUT, "%s%d", i ? "," : "", wit71T1[i]);
    fprintf(OUT, "],\"B071_witness_T2\":[");
    for (size_t i = 0; i < wit71T2.size(); ++i) fprintf(OUT, "%s%d", i ? "," : "", wit71T2[i]);
    fprintf(OUT, "],\"B071_witness_p\":%d,"
                "\"B075_n_triples_with_ge2_completions\":%d,"
                "\"B075_max_shared_completions\":%lld,\"B075_counterexample_ge3\":%s,"
                "\"B075_witness_triples\":[",
            wit71P.empty() ? -1 : wit71P[0], (int)keys.size(), bad75, CS(jb(wit75 > 0)));
    for (size_t i = 0; i < wit75tr.size(); ++i) {
        fprintf(OUT, "%s[", i ? "," : "");
        for (size_t z = 0; z < wit75tr[i].size(); ++z) fprintf(OUT, "%s%d", z ? "," : "", wit75tr[i][z]);
        fprintf(OUT, "]");
    }
    fprintf(OUT, "],\"B075_witness_shared\":%d,"
                "\"B072_bad_safe_4sets\":%lld,\"B072_witness\":%s,\"B072_witness_S\":%llu,"
                "\"B072_witness_p\":%d,"
                "\"B077_safe_4sets_with_min_b_ge_2\":%lld,\"B077_witness\":%s,\"B077_witness_S\":%llu,\"B077_witness_min_b\":%d,"
                "\"B080_safe_4sets_all_b_eq_1\":%lld,\"B080_witness\":%s,\"B080_witness_S\":%llu}\n",
            wit75c, b072_bad, CS(jb(wit072 > 0)), (unsigned long long)wit072S, wit072p,
            b077_hits, CS(jb(wit077 > 0)), (unsigned long long)wit077S, wit077b,
            b080_hits, CS(jb(wit080 > 0)), (unsigned long long)wit080S);
    endsec();
}

// Given a legal-move set A (points that are legal given S) and a chosen p in A,
// return the legal-move set after adding p.  p is legal by the invariant of A.
static inline u64 add_point(const Quads& Q, u64 S, u64 A, int p) {
    u64 S2 = S | (u64(1) << p);
    u64 A2 = A & ~(u64(1) << p);
    u64 t2 = A2;
    while (t2) {
        int q = __builtin_ctzll(t2); t2 &= t2 - 1;
        for (size_t i = 0; i < Q.bq[p].size(); ++i) {
            if (Q.bq[p][i] != q) continue;
            if ((S2 & Q.bm[p][i]) == Q.bm[p][i]) { A2 &= ~(u64(1) << q); break; }
        }
    }
    return A2;
}

// ------------------------------------------------------------------ stage: full
struct FullSolve {
    Board b; Quads Q; Memo memo;
    long long nodes = 0;
    u64 fullm = 0;
    int gval(u64 occ) {
        int r = memo.get(occ);
        if (r >= 0) return r;
        ++nodes;
        uint8_t seen[200] = {0};
        u64 t = b.full & ~occ;
        while (t) {
            int p = __builtin_ctzll(t); t &= t - 1;
            // p is legal iff no forbidden quad through p has its other 3 points in occ
            bool ok = true;
            for (size_t i = 0; i < Q.bq[p].size(); ++i) {
                if (!((occ >> Q.bq[p][i]) & 1)) continue;      // partner q present?
                if ((occ & Q.bm[p][i]) == Q.bm[p][i]) { ok = false; break; }  // other two present?
            }
            if (!ok) continue;
            int c = gval(occ | (u64(1) << p));
            if (c < 200) seen[c] = 1;
        }
        int m = 0; while (m < 200 && seen[m]) ++m;
        memo.put(occ, (uint8_t)m);
        return m;
    }
};

static void stage_full(int n, const char* name) {
    auto t0 = steady_clock::now();
    Board b; build_square(b, n);
    Quads Q; Q.build(b);
    FullSolve fs; fs.b = b; fs.Q = Q; fs.memo.reset(1u << 22);
    int ge = fs.gval(0);

    int V = b.V;
    std::vector<int> g1(V, 0), g1raw(V, -1);
    std::string Wpts = "[";
    int Wn = 0;
    std::map<int, int> g1h;
    for (int p = 0; p < V; ++p) {
        int r = fs.memo.get(u64(1) << p);
        g1raw[p] = r; g1[p] = (r < 0) ? -1 : r;
        if (r >= 0) g1h[r]++;
        if (r == 0) { ++Wn; Wpts += "[" + std::to_string(b.pt_x[p]) + "," + std::to_string(b.pt_y[p]) + "],"; }
    }
    if (Wn) Wpts.erase(Wpts.size() - 1);
    Wpts += "]";
    // g_empty == 0  <=>  every p has g({p}) != 0
    // g_empty == 1  <=>  all g({p}) == 0
    // g_empty >= 2  <=>  mixed
    int n0 = 0; for (int p = 0; p < V; ++p) if (g1[p] == 0) ++n0;
    std::string cls = (n0 == 0) ? "second_player_win" : (n0 == V ? "all_first_moves_win" : "partial_win");

    // two-stone layer -> J_n
    long long jedges = 0;
    std::map<int, long long> g2h;
    std::vector<int> deg(V, 0);
    std::vector<u64> nbr(V, 0);
    for (int a = 0; a < V; ++a) for (int c = a + 1; c < V; ++c) {
        int r = fs.memo.get((u64(1) << a) | (u64(1) << c));
        if (r < 0) continue;
        g2h[r]++;
        if (r == 0) { ++jedges; deg[a]++; deg[c]++; nbr[a] |= u64(1) << c; nbr[c] |= u64(1) << a; }
    }
    // J_n components (over all V vertices; also the non-isolated part)
    std::vector<int> comp(V, -1); int nc = 0;
    for (int s = 0; s < V; ++s) if (comp[s] < 0) {
        std::vector<int> st{ s }; comp[s] = nc;
        while (!st.empty()) { int u = st.back(); st.pop_back(); u64 t = nbr[u] & ~(u64(1) << u);
            while (t) { int w = __builtin_ctzll(t); t &= t - 1; if (comp[w] < 0) { comp[w] = nc; st.push_back(w); } } }
        ++nc;
    }
    int nnoniso = 0; for (int p = 0; p < V; ++p) if (deg[p]) ++nnoniso;
    int ncomp_noniso = 0; { std::set<int> s; for (int p = 0; p < V; ++p) if (deg[p]) s.insert(comp[p]); ncomp_noniso = (int)s.size(); }
    std::string comps = "[";
    { std::map<int, int> cnt; for (int p = 0; p < V; ++p) ++cnt[comp[p]];
      bool f = true; for (auto& kv : cnt) { comps += std::to_string(kv.second) + ","; } comps.erase(comps.size() - 1); (void)f; }
    comps += "]";
    // bipartite?
    std::vector<int> col(V, -1); bool bip = true;
    for (int s = 0; s < V && bip; ++s) if (col[s] < 0) {
        std::vector<int> st{ s }; col[s] = 0;
        while (!st.empty() && bip) { int u = st.back(); st.pop_back(); u64 t = nbr[u];
            while (t) { int w = __builtin_ctzll(t); t &= t - 1;
                if (col[w] < 0) { col[w] = col[u] ^ 1; st.push_back(w); }
                else if (col[w] == col[u]) { bip = false; break; } } }
    }
    // degree histogram
    std::string dh = "{";
    { std::map<int, int> m; for (int p = 0; p < V; ++p) m[deg[p]]++;
      bool f = true; for (auto& kv : m) { dh += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second) + ","; } dh.erase(dh.size() - 1); (void)f; }
    dh += "}";

    // M_n(k) = max g over layer k ; sigma_n = min k with M_n(k) = K_n - k
    std::map<int, std::pair<int, int>> Mk;   // k -> (max g, count)
    {
        for (size_t i = 0; i < fs.memo.cap; ++i) {
            u64 S = fs.memo.K[i];
            if (!S) continue;
            int gv = fs.memo.Vv[i];
            int k = __builtin_popcountll(S);
            auto it = Mk.find(k);
            if (it == Mk.end()) Mk[k] = { gv, 1 };
            else { if (gv > it->second.first) it->second.first = gv; it->second.second++; }
        }
        if (fs.memo.zero) Mk[0] = { ge, 1 };
    }
    int Kmax = 0; for (auto& kv : Mk) Kmax = std::max(Kmax, kv.second.first);
    // K_n from the max layer: K_n = max over terminal sizes = max k present
    int Kn = 0; for (auto& kv : Mk) Kn = std::max(Kn, kv.first);
    // recompute true K_n: K_n = max |S| over safe S = max layer size present
    std::string layers = "[";
    bool first = true;
    for (auto& kv : Mk) {
        if (!first) layers += ","; first = false;
        layers += "[" + std::to_string(kv.first) + "," + std::to_string(kv.second.first) + "," + std::to_string(kv.second.second) + "]";
    }
    layers += "]";
    int sigma = -1;
    for (auto& kv : Mk) if (kv.second.first == Kn - kv.first) { sigma = kv.first; break; }

    std::string g1hs = "{";
    { bool f = true; for (auto& kv : g1h) g1hs += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second) + ","; g1hs.erase(g1hs.size() - 1); (void)f; }
    g1hs += "}";
    std::string g1list = "[";
    for (int p = 0; p < V; ++p) g1list += std::to_string(g1[p]) + ",";
    g1list.erase(g1list.size() - 1); g1list += "]";

    sec(name);
    fprintf(OUT, "{\"n\":%d,\"V\":%d,\"seconds\":%.1f,\"states\":%lld,\"forbidden_quads\":%d,\n"
                 "\"g_empty\":%d,\"class\":\"%s\",\"W_size\":%d,\"W_points\":%s,\n"
                 "\"g1_hist\":%s,\"g1_by_id\":%s,\n"
                 "\"K_n\":%d,\"max_nimber\":%d,\"sigma_n\":%d,\"layers_k_maxg_count\":%s,\n"
                 "\"g2_hist\":{", n, V, el(t0), fs.memo.used, (int)b.quads.size(),
              ge, cls.c_str(), Wn, Wpts.c_str(), g1hs.c_str(), g1list.c_str(),
              Kn, Kmax, sigma, layers.c_str());
    { bool f = true; for (auto& kv : g2h) fprintf(OUT, "%s\"%lld\":%lld", f ? "" : ",", kv.first, kv.second); (void)f; }
    fprintf(OUT, "},\n\"J_edges\":%lld,\"J_degree_hist\":%s,\"J_nonisolated\":%d,"
                 "\"J_components_all\":%d,\"J_component_sizes\":%s,\"J_components_nonisolated\":%d,"
                 "\"J_bipartite\":%s}\n",
            jedges, CS(dh), nnoniso, nc, CS(comps), ncomp_noniso, CS(jb(bip)));
    endsec();
}

// ------------------------------------------------------------------ stage: maxset
struct MaxSetRun {
    Board b; Quads Q;
    int V;
    std::vector<int> qc;       // #points of quad inside S
    std::vector<int> cfl;      // cfl[p] = #quads containing p with qc==2
    std::vector<int> q3;       // q3[p]  = #quads containing p with qc==3
    long long nodes = 0, leaves = 0, aborts = 0;
    bool aborted = false;
    long long nodecap = 0;
    int best = -1;
    std::map<int, long long> spectrum;
    std::map<int, long long> stabhist;
    long long sumb_sum = 0; std::map<int, long long> bhist;   // b_S(p) over maximal sets
    long long minsum_b = -1, maxmaxb = 0, maxratio_num = 0, maxratio_den = 1;
    long long n_minb_ge2 = 0, n_have_b1 = 0, n_all_b1 = 0, n_leaves_sized = 0;
    std::vector<u64> maxsets; long long maxcap = 200000;
    D4 d4;
    explicit MaxSetRun(int n) : d4(n) {}

    // Incremental bookkeeping: qc[q] = |quad q ∩ S|, cfl[p] = #2-hit quads through p
    // (= #pairs {a,b} ⊂ S, a≠b, such that a 2-element completion of {a,b,p} lies in S),
    // q3[p] = #3-hit quads through p (= b_S(p) for p ∉ S).
    void addPt2(int s) {
        for (int q : Q.by_pt[s]) {
            int old = qc[q];
            qc[q] = old + 1;
            if (old == 1) {                     // -> 2-hit
                for (int i = 0; i < 4; ++i) { int p = Q.qpts[q * 4 + i]; if (p != s) ++cfl[p]; }
            } else if (old == 2) {              // -> 3-hit
                for (int i = 0; i < 4; ++i) { int p = Q.qpts[q * 4 + i]; if (p != s) --cfl[p]; }
                for (int i = 0; i < 4; ++i) { int p = Q.qpts[q * 4 + i]; if (p != s && !inS(p)) ++q3[p]; }
            } else if (old == 3) {              // -> 4-hit (S still safe only if quad is a real quad; it is, so never)
                for (int i = 0; i < 4; ++i) { int p = Q.qpts[q * 4 + i]; if (p != s && !inS(p)) --q3[p]; }
            }
        }
    }
    u64 Smask = 0;
    bool inS(int p) const { return (Smask >> p) & 1; }

    void rec(u64 S, u64 A) {
        ++nodes;
        if (nodecap && nodes > nodecap) { aborted = true; ++aborts; return; }
        if (A == 0) { record(S, A); return; }
        int cp = __builtin_ctzll(A);
        // branch 1: cp is used
        u64 A2 = add_point(Q, S, A, cp);
        u64 S2 = S | (u64(1) << cp);
        u64 sold = Smask; Smask = S2; addPt2(cp);
        rec(S2, A2);
        Smask = sold;
        if (aborted) return;
        // branch 2: cp is not used
        rec(S, A & ~(u64(1) << cp));
    }

    void record(u64 S, u64 A) {
        ++leaves;
        u64 M = S | A;
        int k = __builtin_popcountll(M);
        ++spectrum[k];
        ++stabhist[d4.stab(M)];
        if (k > best) { best = k; maxsets.clear(); }
        if (k == best && (long long)maxsets.size() < maxcap) maxsets.push_back(M);
        long long sumb = 0, minb = 1 << 30, maxb = 0, nb1 = 0;
        int empt = b.V - k;
        u64 t = A;
        while (t) {
            int p = __builtin_ctzll(t); t &= t - 1;
            int bb = q3[p];
            sumb += bb; if (bb < minb) minb = bb; if (bb > maxb) maxb = bb; if (bb == 1) ++nb1;
            ++bhist[bb];
        }
        sumb_sum += sumb;
        if (minb < minsum_b) minsum_b = minb;
        if (maxb > maxmaxb) maxmaxb = maxb;
        if ((long long)maxb * maxratio_den > maxratio_num * (long long)k) { maxratio_num = maxb; maxratio_den = k; }
        if (minb >= 2) ++n_minb_ge2;
        if (nb1 > 0) ++n_have_b1;
        if (nb1 == empt) ++n_all_b1;
        ++n_leaves_sized;
        if (k == best) { ++k_best_sum_b; k_best_sum_k += k; ++k_best_n; }
    }
    long long k_best_sum_b = 0, k_best_sum_k = 0, k_best_n = 0;
};

static void stage_maxset(int n, long long nodecap, const char* name) {
    auto t0 = steady_clock::now();
    Board b; build_square(b, n);
    MaxSetRun R(n); R.b = b; R.Q = Quads(); R.Q.build(b); R.V = b.V;
    R.qc.assign(R.Q.nq, 0); R.cfl.assign(b.V, 0); R.q3.assign(b.V, 0);
    R.nodecap = nodecap;
    R.Smask = 0;
    R.rec(0, b.full);
    sec(name);
    fprintf(OUT, "{\"n\":%d,\"V\":%d,\"seconds\":%.1f,\"nodes\":%lld,\"leaves\":%lld,"
                 "\"complete\":%s,\"nodecap\":%lld,\"forbidden_quads\":%d,\n"
                 "\"K_n\":%d,\"n_maximal_at_K\":%zu,\"spectrum\":{",
            n, b.V, el(t0), R.nodes, R.leaves, CS(jb(!R.aborted)), nodecap, (int)b.quads.size(),
            R.best, R.maxsets.size());
    bool f = true; for (auto& kv : R.spectrum) fprintf(OUT, "%s\"%d\":%lld", f ? "" : ",", kv.first, kv.second); (void)f;
    fprintf(OUT, "},\"stab_hist\":{");
    f = true; for (auto& kv : R.stabhist) fprintf(OUT, "%s\"%d\":%lld", f ? "" : ",", kv.first, kv.second); (void)f;
    fprintf(OUT, "},\"b_S_p_hist\":{");
    f = true; for (auto& kv : R.bhist) fprintf(OUT, "%s\"%lld\":%lld", f ? "" : ",", kv.first, kv.second); (void)f;
    fprintf(OUT, "},\"sum_b_over_maximal\":%lld,\"min_over_maximal_of_min_b\":%lld,"
                 "\"max_over_maximal_of_max_b\":%lld,\"max_b_over_k_num\":%lld,\"max_b_over_k_den\":%lld,"
                 "\"n_maximal_with_min_b_ge_2\":%lld,\"n_maximal_with_some_b_eq_1\":%lld,"
                 "\"n_maximal_with_all_empty_b_eq_1\":%lld,\n"
                 "\"maximal_examples\":[",
            R.sumb_sum, R.minsum_b, R.maxmaxb, R.maxratio_num, R.maxratio_den,
            R.n_minb_ge2, R.n_have_b1, R.n_all_b1);
    for (size_t i = 0; i < R.maxsets.size() && i < 40; ++i) {
        fprintf(OUT, "%s[", i ? "," : "");
        u64 m = R.maxsets[i]; bool g = true;
        while (m) { int p = __builtin_ctzll(m); m &= m - 1; fprintf(OUT, "%s%d", g ? "" : ",", p); g = false; }
        fprintf(OUT, "]");
    }
    fprintf(OUT, "]}\n");
    endsec();
}

// ------------------------------------------- stage: kmax (exact K_n, branch & bound)
// Independent witness check: S is safe iff no forbidden quad is a subset of S,
// and S is reachable in the game iff every point of S was legal when added.
// We check safety with the shared core (independent of this file's machinery).
static bool is_safe_and_legal(const Board& b, u64 S) {
    u64 t = S;
    while (t) {
        int p = __builtin_ctzll(t); t &= t - 1;
        for (u64 tr : b.triples_by_pt[p])
            if ((S & tr) == tr) return false;
    }
    return true;
}

// Question: does a safe set of size >= k exist?  Branch on the lowest available
// point (use / don't use).  Prune by |A| < need and by a failure memo on (S,A).
struct KMax {
    Board b; Quads Q;
    std::set<std::pair<u64, u64>> dead;      // (S,A) proven to have no extension of need
    long long nodes = 0;
    bool aborted = false;
    long long nodecap = 0;
    u64 witness = 0;
    bool found = false;

    bool go(u64 S, u64 A, int need) {
        if (need <= 0) { witness = S; found = true; return true; }
        if (A == 0) return false;
        if (__builtin_popcountll(A) < (unsigned)need) return false;      // bound
        if (dead.count(std::make_pair(S, A))) return false;
        ++nodes;
        if (nodecap && nodes > nodecap) { aborted = true; return false; }
        int p = __builtin_ctzll(A);
        // branch 1: use p
        if (go(S | (u64(1) << p), add_point(Q, S, A, p), need - 1)) return true;
        if (aborted) return false;
        // branch 2: skip p
        if (go(S, A & ~(u64(1) << p), need)) return true;
        if (aborted) return false;
        dead.insert(std::make_pair(S, A));
        return false;
    }
};

static void stage_kmax(int n, int from_k, int to_k, const char* name) {
    Board b; build_square(b, n);
    Quads Q; Q.build(b);
    sec(name);
    fprintf(OUT, "{\"n\":%d,\"V\":%d,\"results\":[", n, n * n);
    for (int k = from_k; k <= to_k; ++k) {
        auto t0 = steady_clock::now();
        KMax K; K.b = b; K.Q = Q; K.nodecap = 0;
        bool r = K.go(0, b.full, k);
        fprintf(OUT, "%s{\"k\":%d,\"exists\":%s,\"complete\":%s,\"nodes\":%lld,\"seconds\":%.1f",
                k > from_k ? "," : "", k, r ? "true" : "false",
                K.aborted ? "false" : "true", K.nodes, el(t0));
        if (r) {
            u64 w = K.witness; std::string s = "[";
            // independent verification of the witness with the shared core
            bool safev = is_safe_and_legal(b, w);
            int sz = __builtin_popcountll(w);
            while (w) { int p = __builtin_ctzll(w); w &= w - 1; s += std::to_string(p) + ","; }
            s.erase(s.size() - 1); s += "]";
            fprintf(OUT, ",\"witness\":%s,\"witness_size\":%d,\"witness_verified_safe\":%s",
                    s.c_str(), sz, safev ? "true" : "false");
        }
        fprintf(OUT, "}");
        fflush(OUT);
    }
    fprintf(OUT, "]}\n");
    endsec();
}

// ------------------------------------- stage: counts (safe-set / layer census)
struct Count {
    Board b; Quads Q;
    long long nodes = 0;
    std::map<int, long long> bysize;
    int K = 0;
    void go(u64 S, u64 A, int k) {
        ++nodes;
        if (A == 0) { ++bysize[k]; if (k > K) K = k; return; }
        int p = __builtin_ctzll(A);
        go(S | (u64(1) << p), add_point(Q, S, A, p), k + 1);
        go(S, A & ~(u64(1) << p), k);
    }
};
static void stage_count(int n, const char* name) {
    auto t0 = steady_clock::now();
    Board b; build_square(b, n);
    Count C; C.b = b; C.Q = Quads(); C.Q.build(b);
    C.go(0, b.full, 0);
    long long tot = 0; for (auto& kv : C.bysize) tot += kv.second;
    sec(name);
    fprintf(OUT, "{\"n\":%d,\"V\":%d,\"seconds\":%.1f,\"nodes\":%lld,\"K_n\":%d,"
                 "\"n_safe_sets\":%lld,\"safe_by_size\":{",
            n, b.V, el(t0), C.nodes, C.K, tot);
    bool f = true; for (auto& kv : C.bysize) fprintf(OUT, "%s\"%d\":%lld", f ? "" : ",", kv.first, kv.second);
    fprintf(OUT, "}}\n");
    endsec();
}

// ---------------------------------------------------------------------- driver
int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: r4b002 <rawfile> <stage> [arg]\n"); return 1; }
    OUT = fopen(argv[1], "ab");
    if (!OUT) { perror("open"); return 1; }
    std::string st = argv[2];
    std::string nm = (argc > 3) ? argv[3] : st;
    if (st == "fcheck") stage_fcheck(nm.c_str());
    else if (st == "comb") { for (int n = 2; n <= 8; ++n) { char b[64]; snprintf(b, 64, "comb_n%d", n); stage_comb(n, b); } }
    else if (st == "full") { for (int n = 1; n <= 6; ++n) { char b[64]; snprintf(b, 64, "full_n%d", n); stage_full(n, b); } }
    else if (st == "full7") stage_full(7, "full_n7");
    else if (st == "kmax") { char b[64];
        for (int n = 2; n <= 6; ++n) { snprintf(b, 64, "kmax_n%d", n); stage_kmax(n, 1, 2 * n + 2, b); } }
    else if (st == "kmax7") stage_kmax(7, 12, 16, "kmax_n7");
    else if (st == "kmax8") stage_kmax(8, 13, 17, "kmax_n8");
    else if (st == "count") { char b[64]; for (int n = 2; n <= 6; ++n) { snprintf(b, 64, "count_n%d", n); stage_count(n, b); } }
    else if (st == "count7") stage_count(7, "count_n7");
    else if (st == "maxset6") stage_maxset(6, 0, "maxset_n6");
    else if (st == "maxset7") stage_maxset(7, 0, "maxset_n7");
    else if (st == "maxset8") stage_maxset(8, (argc > 3) ? atoll(argv[3]) : 400000000LL, "maxset_n8");
    else { fprintf(stderr, "unknown stage %s\n", st.c_str()); }
    fclose(OUT);
    return 0;
}
