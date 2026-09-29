// Grundy DP for the kyouen (no-4-concyclic) game on an n x n grid, n*n <= 128.
//
//   g(empty) is the answer: 0 => second player wins, >0 => first player wins.
//
//   g(S) = mex { g(S + {u}) : u in L(S) },   g(terminal) = 0
//   L(S) = { u : u unoccupied, S+{u} contains no forbidden 4-set }
//
// A state is the set of occupied points, p = y*n + x, in the 2-word kc::Bits.
// A state is safe iff it contains no forbidden 4-set.
//
// ---------------------------------------------------------------------------
// Why the levels are re-enumerated here instead of read from a spill
// ---------------------------------------------------------------------------
// The v-max construction of n11_enum121.cpp emits every child at v = its top
// point, walking v ascending and visiting parents in stored order. Because each
// level is stored sorted, that emission is already strictly increasing in the
// 128-bit order, so each level comes out sorted AND duplicate free with no sort
// at all. The same construction therefore regenerates the levels in memory, and
// the sortedness is what the child lookup below relies on.
//
// ---------------------------------------------------------------------------
// Child lookup: binary search
// ---------------------------------------------------------------------------
// Every legal (S, u) pair is looked up directly in the sorted level k+1 with a
// lower_bound, so correctness rests on nothing but the sortedness above.
//
// A v-block linear merge was implemented first and REJECTED. Block v of level
// k+1 is emitted by the v-max construction only from parents with top(S) < v,
// so a state S with top(S) >= v has children sitting in other blocks and the
// cursor silently dropped them: on n=5 the state {1} collected 23 children
// instead of 24 (it lost the child {0,1}) and g(empty) came out 11 instead of
// 1. The guard meant to catch this compared the cursor total against the child
// count, which is the wrong identity -- a child has k+1 parents, so the edge
// count is (k+1)*|level k+1|, not |level k+1|. Both the merge and that guard
// are gone; failed lookups are now checked instead, and were 0.
//
// Cost is edges * log2|level k+1|, ~1.9e9 * 27 probes for n=11, against the
// measured n=7 rate of 1.5e9 edges in 434 s.
//
// ---------------------------------------------------------------------------
// Legal-move pass: triple-rank table
// ---------------------------------------------------------------------------
// A point u is illegal iff some quad through u has its other three points all
// occupied, i.e. iff some 3-subset T of occ has T + {u} a quad.
// kc::legal_mask tests every empty point against every quad through it, i.e.
// |L| * |triples_by_pt[u]| ~ 115*3163 ~ 3.6e5 subset tests per n=11 state.
// Instead we precompute, for every 3-subset T of the board, the mask
//
//     tri4[T] = { u : T + {u} is a forbidden 4-set }
//
// and OR in the entries for only the C(k,3) triples actually present in occ --
// 20 lookups for a k=6 state. T is addressed by its rank in the combinatorial
// number system, rank(p0<p1<p2) = C(p0,1) + C(p1,2) + C(p2,3), a bijection from
// the 3-subsets of {0..V-1} onto [0, C(V,3)), so tri4 is a direct-indexed
// table with no hashing and no collisions. For n=11 it is C(121,3)*16 B = 4.6 MB.
//
// A first attempt that OR-ed triples_by_pt[p] over OCCUPIED p was wrong: the
// triple {0,1,2} of the quad {0,1,2,3} is filed under triples_by_pt[3] and 3 is
// unoccupied, so the blocking of 3 was missed. --check-legal caught it.
//
// ---------------------------------------------------------------------------
// Memory
// ---------------------------------------------------------------------------
// Levels are kept as 16-byte records; the DP walks k descending and frees
// level k+1 as soon as g(k) is done, so only two adjacent levels are live.
// g is one byte per state (g(S) <= maxrem(S) = K-k <= K), and the mex
// accumulator is 4 bytes per state of the parent level.
//
// Usage:
//   n11_grundy --enum 6
//   n11_grundy --enum 11 --out out.json [--spill=dir] [--threads=16]
//   n11_grundy --read-spill=/tmp/n11_121 --n=11 --expect-levels=1,121,7007,...
//   n11_grundy --enum 6 --check-legal        # free-mask vs kc::legal_mask
#include "kc_core121.h"

#include <algorithm>
#include <atomic>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

using kc::u64;
using kc::Bits;
using kc::Board;

static double now_s() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

static long rss_mb() {
    FILE* f = fopen("/proc/self/status", "r");
    if (!f) return -1;
    char line[256];
    long v = -1;
    while (fgets(line, sizeof line, f))
        if (!strncmp(line, "VmHWM:", 6)) { sscanf(line + 6, "%ld", &v); break; }
    fclose(f);
    return v / 1024;
}

static int top_point(const Bits& b) {  // caller guarantees b is non-empty
    if (b.hi) return 127 - __builtin_clzll(b.hi);
    return 63 - __builtin_clzll(b.lo);
}

// ------------------------------------------------------- legal moves (fast)
// A point u is illegal iff some quad through u has its other three points all
// occupied, i.e. iff there is a 3-subset T of occ with T + {u} a quad.
//
// kc::legal_mask tests every empty point against every quad through it:
// |L| * |triples_by_pt[u]| ~ 3.6e5 subset tests per n=11 state. Instead we
// precompute, for every 3-subset T of the board, the mask
//
//     tri4[T] = { u : T + {u} is a forbidden 4-set }
//
// and then walk only the C(k,3) triples actually present in occ, OR-ing their
// tri4 masks in. That is 20 lookups for a k=6 state instead of 3.6e5 tests.
//
// T is addressed by its rank in the combinatorial number system,
// rank(p0<p1<p2) = C(p0,1) + C(p1,2) + C(p2,3), which is a bijection from the
// 3-subsets of {0..V-1} onto [0, C(V,3)) -- so tri4 is a direct-indexed table,
// no hashing and no collisions. For n=11 it is C(121,3)*16 B = 4.6 MB and
// stays resident in L3.
//
// A first attempt that OR-ed triples_by_pt[p] over OCCUPIED p was wrong: the
// triple {0,1,2} of the quad {0,1,2,3} is filed under triples_by_pt[3], and 3
// is unoccupied, so the blocking of 3 was missed. --check-legal caught it.
struct Tri4 {
    std::vector<Bits> tab;
    std::vector<int> c1, c2, c3;   // C(p,1), C(p,2), C(p,3)
    int V = 0;
    void build(const Board& B) {
        V = B.V;
        c1.resize((size_t)V);
        c2.resize((size_t)V);
        c3.resize((size_t)V);
        for (int p = 0; p < V; ++p) {
            c1[(size_t)p] = p;
            c2[(size_t)p] = p * (p - 1) / 2;
            c3[(size_t)p] = p > 2 ? p * (p - 1) * (p - 2) / 6 : 0;
        }
        tab.assign((size_t)V * (V - 1) * (V - 2) / 6, Bits{0, 0});
        for (const Bits& q : B.quads) {
            int p[4], c = 0;
            u64 e = q.lo;
            while (e) { p[c++] = __builtin_ctzll(e); e &= e - 1; }
            e = q.hi;
            while (e) { p[c++] = 64 + __builtin_ctzll(e); e &= e - 1; }
            if (c != 4) { fprintf(stderr, "FATAL: quad with %d points\n", c); exit(9); }
            for (int t = 0; t < 4; ++t) {
                int a, b, d;
                if (t == 0) { a = p[1]; b = p[2]; d = p[3]; }
                else if (t == 1) { a = p[0]; b = p[2]; d = p[3]; }
                else if (t == 2) { a = p[0]; b = p[1]; d = p[3]; }
                else { a = p[0]; b = p[1]; d = p[2]; }
                size_t r = (size_t)(c1[(size_t)a] + c2[(size_t)b] + c3[(size_t)d]);
                if (r >= tab.size()) { fprintf(stderr, "FATAL: tri4 rank %zu\n", r); exit(9); }
                tab[r].set(p[t]);
            }
        }
    }
};

static void free_mask_level(const Board& B, const Tri4& T,
                            const std::vector<Bits>& A, std::vector<Bits>& out) {
    out.resize(A.size());
    const Bits* tab = T.tab.data();
    const int* c1 = T.c1.data();
    const int* c2 = T.c2.data();
    const int* c3 = T.c3.data();
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)A.size(); ++i) {
        const Bits& S = A[(size_t)i];
        int pt[128], k = 0;
        u64 e = S.lo;
        while (e) { pt[k++] = __builtin_ctzll(e); e &= e - 1; }
        e = S.hi;
        while (e) { pt[k++] = 64 + __builtin_ctzll(e); e &= e - 1; }
        Bits blk{0, 0};
        for (int a = 0; a < k; ++a) {
            const int ca = c1[pt[a]], va = pt[a];
            for (int b = a + 1; b < k; ++b) {
                const int cb = c2[pt[b]] + ca, vb = pt[b];
                const Bits* row = tab + cb;
                for (int d = b + 1; d < k; ++d) {
                    const Bits& q = row[c3[pt[d]]];
                    blk.lo |= q.lo;
                    blk.hi |= q.hi;
                }
                (void)vb;
            }
        }
        Bits f;
        f.lo = B.full_lo & ~S.lo & ~blk.lo;
        f.hi = B.hi_marks & ~S.hi & ~blk.hi;
        out[(size_t)i] = f;
    }
}

// Bit-for-bit check that free_mask_level agrees with kc::legal_mask. With
// diag>0 the first mismatching state is dumped (state, fast, reference).
static u64 check_legal(const Board& B, const std::vector<Bits>& A,
                       const std::vector<Bits>& freem, size_t limit, int diag = 0) {
    u64 bad = 0;
    size_t n = std::min(limit, A.size());
#pragma omp parallel for schedule(static) reduction(+ : bad)
    for (long long i = 0; i < (long long)n; ++i) {
        Bits ref = kc::legal_mask(B, A[(size_t)i]);
        if (ref != freem[(size_t)i]) {
            bad++;
            if (diag) {
#pragma omp critical
                {
                    if (bad <= (u64)diag) {
                        Bits d{freem[(size_t)i].lo & ~ref.lo, freem[(size_t)i].hi & ~ref.hi};
                        Bits m{ref.lo & ~freem[(size_t)i].lo, ref.hi & ~freem[(size_t)i].hi};
                        fprintf(stderr, "    MISMATCH i=%lld fast_legal=ref_legal: ", i);
                        if (d.lo | d.hi) {
                            fprintf(stderr, "pts ");
                            Bits z = d;
                            while (z.lo) { int p = __builtin_ctzll(z.lo); z.lo &= z.lo - 1; fprintf(stderr, "(%d,%d) ", B.pt_x[p], B.pt_y[p]); }
                            while (z.hi) { int p = 64 + __builtin_ctzll(z.hi); z.hi &= z.hi - 1; fprintf(stderr, "(%d,%d) ", B.pt_x[p], B.pt_y[p]); }
                        }
                        fprintf(stderr, "| missing-from-fast: ");
                        if (m.lo | m.hi) {
                            Bits z = m;
                            while (z.lo) { int p = __builtin_ctzll(z.lo); z.lo &= z.lo - 1; fprintf(stderr, "(%d,%d) ", B.pt_x[p], B.pt_y[p]); }
                            while (z.hi) { int p = 64 + __builtin_ctzll(z.hi); z.hi &= z.hi - 1; fprintf(stderr, "(%d,%d) ", B.pt_x[p], B.pt_y[p]); }
                        }
                        Bits sz = A[(size_t)i];
                        fprintf(stderr, "| occ {");
                        while (sz.lo) { int p = __builtin_ctzll(sz.lo); sz.lo &= sz.lo - 1; fprintf(stderr, "%d,", p); }
                        while (sz.hi) { int p = 64 + __builtin_ctzll(sz.hi); sz.hi &= sz.hi - 1; fprintf(stderr, "%d,", p); }
                        fprintf(stderr, "}\n");
                    }
                }
            }
        }
    }
    return bad;
}

// ------------------------------------------------------------ enumeration
// level k+1 from level k, in the v-max order (see file header). Parallel over
// v: pass 1 counts each block, pass 2 lays the blocks out contiguously, pass 3
// fills them. The result is sorted and duplicate free by construction.
static void build_next(const Board& B, const std::vector<Bits>& cur,
                       const std::vector<Bits>& freem, std::vector<Bits>& nxt) {
    const int V = B.V;
    std::vector<int> plen((size_t)V);
#pragma omp parallel for schedule(static)
    for (int v = 0; v < V; ++v) {
        Bits bit; bit.set(v);
        plen[(size_t)v] = (int)(std::lower_bound(cur.begin(), cur.end(), bit) - cur.begin());
    }
    std::vector<u64> bs((size_t)V, 0);
#pragma omp parallel for schedule(static)
    for (int v = 0; v < V; ++v) {
        u64 c = 0;
        for (int i = 0; i < plen[(size_t)v]; ++i)
            if (freem[(size_t)i].test(v)) c++;
        bs[(size_t)v] = c;
    }
    std::vector<u64> off((size_t)V + 1, 0);
    for (int v = 0; v < V; ++v) off[(size_t)v + 1] = off[(size_t)v] + bs[(size_t)v];
    nxt.resize((size_t)off[(size_t)V]);
#pragma omp parallel for schedule(static)
    for (int v = 0; v < V; ++v) {
        Bits bit; bit.set(v);
        u64 p = off[(size_t)v];
        for (int i = 0; i < plen[(size_t)v]; ++i)
            if (freem[(size_t)i].test(v)) {
                nxt[(size_t)p].lo = cur[(size_t)i].lo | bit.lo;
                nxt[(size_t)p].hi = cur[(size_t)i].hi | bit.hi;
                p++;
            }
    }
    if (!kc::is_sorted_unique(nxt)) {
        fprintf(stderr, "FATAL: generated level is not sorted/unique\n");
        exit(9);
    }
}

// ----------------------------------------------------------------- the DP
struct LevelStat {
    size_t size = 0;
    u64 edges = 0;      // out-edges of this level
    u64 nP = 0, nN = 0;
    std::vector<u64> ghist;  // g value -> count
    double secs = 0;
};

int main(int argc, char** argv) {
    int n = 0, threads = 0, check_legal_limit = 0;
    std::string spill, outjson, read_spill, expect;
    int maxlevel = 1 << 20;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto val = [&](void) -> std::string { return (i + 1 < argc) ? argv[++i] : ""; };
        if (a == "--enum") n = atoi(val().c_str());
        else if (a == "--n") n = atoi(val().c_str());
        else if (a == "--threads") threads = atoi(val().c_str());
        else if (a == "--maxlevel") maxlevel = atoi(val().c_str());
        else if (a == "--check-legal") check_legal_limit = 1 << 30;
        else if (a == "--check-legal-first") check_legal_limit = atoi(val().c_str());
        else if (a.rfind("--spill=", 0) == 0) spill = a.substr(8);
        else if (a == "--spill") spill = val();
        else if (a.rfind("--out=", 0) == 0) outjson = a.substr(6);
        else if (a == "--out") outjson = val();
        else if (a.rfind("--read-spill=", 0) == 0) read_spill = a.substr(12);
        else if (a == "--read-spill") read_spill = val();
        else if (a.rfind("--expect-levels=", 0) == 0) expect = a.substr(16);
        else if (a == "--expect-levels") expect = val();
        else { fprintf(stderr, "unknown arg %s\n", a.c_str()); return 2; }
    }
    if (n <= 0) {
        fprintf(stderr, "usage: --enum <n> | --read-spill <dir> --n <n>\n");
        return 2;
    }
    if (threads > 0) {
#ifdef _OPENMP
        omp_set_num_threads(threads);
#endif
    }
#ifdef _OPENMP
    int nth = omp_get_max_threads();
#else
    int nth = 1;
#endif

    double t_start = now_s(), t_build = 0, t_enum = 0, t_dp = 0;
    fprintf(stderr, "[n=%d] threads=%d\n", n, nth);

    // ------------------------------------------------------------ geometry
    double tb = now_s();
    Board B;
    kc::build_square(B, n);
    t_build = now_s() - tb;
    fprintf(stderr, "[n=%d] V=%d F=%zu build %.2fs rss=%ldMB\n", n, B.V,
            B.quads.size(), t_build, rss_mb());
    fflush(stderr);

    std::vector<std::vector<Bits>> levels;
    std::vector<u64> level_edges;
    Tri4 T4;
    T4.build(B);
    fprintf(stderr, "[n=%d] tri4 table C(V,3)=%zu entries, %.1f MB, rss=%ldMB\n", n,
            T4.tab.size(), T4.tab.size() * 16.0 / 1048576.0, rss_mb());

    if (!read_spill.empty()) {
        // ------------------------------------------------- read a spill dir
        kc::Spill sp(read_spill);
        levels.push_back(sp.read(0));
        for (int k = 1;; ++k) {
            std::vector<Bits> nx = sp.read(k);
            if (nx.empty()) break;
            if (!kc::is_sorted_unique(nx)) {
                fprintf(stderr, "FATAL: spill level %d not sorted/unique\n", k);
                return 9;
            }
            levels.push_back(std::move(nx));
            if ((int)levels.size() - 1 >= maxlevel) break;
        }
        fprintf(stderr, "[n=%d] spill %s -> %zu levels\n", n, read_spill.c_str(),
                levels.size());
    } else {
        // --------------------------------------------------- enumerate in RAM
        levels.push_back(std::vector<Bits>(1, Bits{0, 0}));
        std::vector<Bits> freem;
        double te = now_s();
        for (int k = 0; k < maxlevel; ++k) {
            free_mask_level(B, T4, levels[(size_t)k], freem);
            if (check_legal_limit) {
                u64 bad = check_legal(B, levels[(size_t)k], freem, (size_t)check_legal_limit, 3);
                fprintf(stderr, "  level %d: free-mask vs kc::legal_mask mismatches=%llu\n",
                        k, (unsigned long long)bad);
                if (bad) return 9;
            }
            u64 e = 0;
            for (const Bits& m : freem) e += (u64)m.count();
            levels.push_back(std::vector<Bits>());
            build_next(B, levels[(size_t)k], freem, levels.back());
            level_edges.push_back(e);
            if (!spill.empty()) kc::Spill(spill).write(k + 1, levels.back());
            fprintf(stderr, "  level %d: %zu states  edges=%llu  rss=%ldMB  %.1fs\n",
                    k + 1, levels.back().size(), (unsigned long long)e, rss_mb(),
                    now_s() - te);
            fflush(stderr);
            if (levels.back().empty()) { levels.pop_back(); level_edges.pop_back(); break; }
        }
        t_enum = now_s() - te;
    }

    const int K = (int)levels.size() - 1;
    u64 total = 0;
    std::vector<size_t> sizes;
    for (int k = 0; k <= K; ++k) { total += (u64)levels[(size_t)k].size(); sizes.push_back(levels[(size_t)k].size()); }
    fprintf(stderr, "[n=%d] K=%d total=%llu widest=%zu(k=%d) rss=%ldMB\n", n, K,
            (unsigned long long)total, *std::max_element(sizes.begin(), sizes.end()),
            (int)(std::max_element(sizes.begin(), sizes.end()) - sizes.begin()), rss_mb());

    if (!expect.empty()) {
        // comma separated expected level sizes
        std::vector<u64> exp;
        size_t p = 0;
        while (p < expect.size()) {
            size_t q = expect.find(',', p);
            if (q == std::string::npos) q = expect.size();
            exp.push_back(strtoull(expect.substr(p, q - p).c_str(), nullptr, 10));
            p = q + 1;
        }
        bool ok = exp.size() == sizes.size();
        if (ok) for (size_t i = 0; i < sizes.size(); ++i) if (exp[i] != (u64)sizes[i]) ok = false;
        fprintf(stderr, "[n=%d] level-size check vs expectation: %s\n", n, ok ? "MATCH" : "MISMATCH");
        if (!ok) {
            fprintf(stderr, "  got     :");
            for (size_t s : sizes) fprintf(stderr, " %zu", s);
            fprintf(stderr, "\n  expected:");
            for (u64 s : exp) fprintf(stderr, " %llu", (unsigned long long)s);
            fprintf(stderr, "\n");
            return 9;
        }
    }

    // ------------------------------------------------------ the Grundy DP
    double td = now_s();
    std::vector<LevelStat> stat((size_t)K + 1);
    std::vector<uint8_t> gnext;      // g of level k+1
    std::vector<Bits> freem;         // free masks of level k
    std::vector<unsigned> acc;       // seen-nimber mask per state of level k
    u64 gbound_violations = 0;

    // level K is terminal: no level K+1 exists, so every state there has g=0
    {
        LevelStat& st = stat[(size_t)K];
        st.size = levels[(size_t)K].size();
        st.nP = st.size;
        st.ghist.assign(2, 0);
        st.ghist[0] = st.size;
        if (K > 0) st.edges = (level_edges.empty() || (int)level_edges.size() <= K) ? 0 : level_edges[(size_t)K];
    }

    for (int k = K - 1; k >= 0; --k) {
        double tk = now_s();
        const std::vector<Bits>& Lk = levels[(size_t)k];
        const std::vector<Bits>& Lk1 = levels[(size_t)k + 1];
        const size_t Mk = Lk.size(), Mk1 = Lk1.size();

        free_mask_level(B, T4, Lk, freem);
        if (check_legal_limit) {
            u64 bad = check_legal(B, Lk, freem, (size_t)check_legal_limit);
            if (bad) { fprintf(stderr, "FATAL: legal mask mismatch at level %d\n", k); return 9; }
        }
        if (gnext.size() != Mk1) gnext.assign(Mk1, 0);

        acc.assign(Mk, 0u);
        // Locate each child by binary search in the sorted level k+1.
        //
        // A v-block linear merge was tried here and REJECTED: block v of level
        // k+1 is emitted by the v-max construction only from the parents with
        // top(S) < v, so a state S with top(S) >= v contributes a child S+{v}
        // that sits in a different block and the cursor never credits it. On
        // n=5 the state {1} came out with 23 children instead of 24 (it lost
        // the child {0,1}), which is what made the first g(empty) come out 11
        // instead of 1. Binary search has no such blind spot: every legal
        // (S, u) pair is looked up directly, and n5_mergecheck confirmed 0
        // lookup failures and g(empty)=1.
        //
        // Cost is edges * log2|level k+1| ~ 1.9e9 * 27 probes for n=11, which
        // at the measured n=7 rate (1.5e9 edges in 434 s) is ~10 minutes.
        // Parallelised over parents; acc is thread-private, so no atomics.
        u64 edges_seen = 0, lookup_fail = 0;
        std::vector<std::vector<unsigned>> tacc((size_t)nth);
#pragma omp parallel reduction(+ : edges_seen, lookup_fail)
        {
            int tid = 0;
#ifdef _OPENMP
            tid = omp_get_thread_num();
#endif
            std::vector<unsigned>& a = tacc[(size_t)tid];
            a.assign(Mk, 0u);
#pragma omp for schedule(static)
            for (long long ii = 0; ii < (long long)Mk; ++ii) {
                const size_t i = (size_t)ii;
                const Bits& S = Lk[i];
                const Bits fr = freem[i];
                u64 e = fr.lo, eh = fr.hi;
                while (e) {
                    int v = __builtin_ctzll(e);
                    e &= e - 1;
                    Bits c; c.set(v);
                    c.lo |= S.lo; c.hi |= S.hi;
                    size_t lo = 0, hi = Mk1;
                    while (lo < hi) { size_t mid = (lo + hi) >> 1; if (Lk1[mid] < c) lo = mid + 1; else hi = mid; }
                    if (lo < Mk1 && Lk1[lo] == c) a[i] |= 1u << gnext[lo];
                    else lookup_fail++;
                    edges_seen++;
                }
                while (eh) {
                    int v = 64 + __builtin_ctzll(eh);
                    eh &= eh - 1;
                    Bits c; c.set(v);
                    c.lo |= S.lo; c.hi |= S.hi;
                    size_t lo = 0, hi = Mk1;
                    while (lo < hi) { size_t mid = (lo + hi) >> 1; if (Lk1[mid] < c) lo = mid + 1; else hi = mid; }
                    if (lo < Mk1 && Lk1[lo] == c) a[i] |= 1u << gnext[lo];
                    else lookup_fail++;
                    edges_seen++;
                }
            }
        }
        for (int t = 0; t < nth; ++t)
            for (size_t i = 0; i < Mk; ++i) acc[i] |= tacc[(size_t)t][i];
        tacc.clear(); tacc.shrink_to_fit();
        if (lookup_fail) {
            fprintf(stderr, "FATAL: level %d had %llu failed child lookups\n", k,
                    (unsigned long long)lookup_fail);
            return 9;
        }

        LevelStat& st = stat[(size_t)k];
        st.size = Mk;
        st.ghist.assign((size_t)K + 2, 0);
        gnext.resize(Mk);
#pragma omp parallel for schedule(static)
        for (long long i = 0; i < (long long)Mk; ++i) {
            unsigned a = acc[(size_t)i];
            unsigned z = ~a;
            int m = z ? __builtin_ctz(z) : -1;
            gnext[(size_t)i] = (uint8_t)(m < 0 ? 0 : m);
        }
        u64 pv = 0;
#pragma omp parallel for schedule(static) reduction(+ : pv)
        for (long long i = 0; i < (long long)Mk; ++i)
            if (gnext[(size_t)i] > (uint8_t)(K - k)) pv++;
        gbound_violations += pv;
        u64 nP = 0;
        for (size_t i = 0; i < Mk; ++i) {
            uint8_t g = gnext[i];
            st.ghist[g]++;
            if (g == 0) nP++;
        }
        st.nP = nP;
        st.nN = (u64)Mk - nP;
        st.edges = (level_edges.empty() || (int)level_edges.size() <= k) ? 0 : level_edges[(size_t)k];
        st.secs = now_s() - tk;

        fprintf(stderr, "  k=%2d M=%-10zu edges=%-12llu P=%-10llu N=%-10llu  %.1fs\n",
                k, Mk, (unsigned long long)st.edges, (unsigned long long)st.nP,
                (unsigned long long)st.nN, st.secs);
        fflush(stderr);

        acc.clear(); acc.shrink_to_fit();
        if (k > 0) { std::vector<Bits>().swap(levels[(size_t)k + 1]); }
    }
    t_dp = now_s() - td;

    // ------------------------------------------------------------- report
    const int g_empty = levels[0].empty() ? -1 : gnext[0];
    u64 nP = 0, nN = 0, edges = 0;
    for (int k = 0; k <= K; ++k) { nP += stat[(size_t)k].nP; nN += stat[(size_t)k].nN; edges += stat[(size_t)k].edges; }
    int gmax = 0;
    for (int k = 0; k <= K; ++k)
        for (size_t gi = 0; gi < stat[(size_t)k].ghist.size(); ++gi)
            if (stat[(size_t)k].ghist[gi] && (int)gi > gmax) gmax = (int)gi;

    double t_all = now_s() - t_start;
    fprintf(stderr, "=== n=%d  g(empty)=%d  K=%d  P=%llu N=%llu  edges=%llu  gmax=%d  %.1fs  rss=%ldMB\n",
            n, g_empty, K, (unsigned long long)nP, (unsigned long long)nN,
            (unsigned long long)edges, gmax, t_all, rss_mb());

    std::string j;
    char buf[4096];
    auto app = [&](const char* fmt, ...) {
        va_list ap; va_start(ap, fmt);
        vsnprintf(buf, sizeof buf, fmt, ap);
        va_end(ap);
        j += buf;
    };
    app("{\n  \"n\": %d,\n  \"V\": %d,\n  \"F\": %zu,\n  \"K\": %d,\n", n, B.V, B.quads.size(), K);
    app("  \"words_per_state\": 2,\n  \"bytes_per_state\": 16,\n");
    app("  \"g_empty\": %d,\n  \"winner\": \"%s\",\n", g_empty, g_empty == 0 ? "second" : (g_empty > 0 ? "first" : "UNKNOWN"));
    app("  \"g_max\": %d,\n", gmax);
    app("  \"n_safe_subsets\": %llu,\n", (unsigned long long)total);
    app("  \"edge_total\": %llu,\n", (unsigned long long)edges);
    app("  \"n_P\": %llu,\n  \"n_N\": %llu,\n", (unsigned long long)nP, (unsigned long long)nN);
    app("  \"level_sizes\": [");
    for (int k = 0; k <= K; ++k) app("%s%zu", k ? "," : "", sizes[(size_t)k]);
    app("],\n");
    app("  \"levels\": [\n");
    for (int k = 0; k <= K; ++k) {
        app("    {\"k\": %d, \"size\": %zu, \"edges\": %llu, \"n_P\": %llu, \"n_N\": %llu, \"secs\": %.2f",
            k, sizes[(size_t)k], (unsigned long long)stat[(size_t)k].edges,
            (unsigned long long)stat[(size_t)k].nP, (unsigned long long)stat[(size_t)k].nN, stat[(size_t)k].secs);
        bool first = true;
        for (size_t gi = 0; gi < stat[(size_t)k].ghist.size(); ++gi)
            if (stat[(size_t)k].ghist[gi]) {
                app("%s\"g%zu\": %llu", first ? ", " : ", ", gi, (unsigned long long)stat[(size_t)k].ghist[gi]);
                first = false;
            }
        app("}%s\n", k < K ? "," : "");
    }
    app("  ],\n");
    app("  \"g_bound_violations\": %llu,\n", (unsigned long long)gbound_violations);
    app("  \"threads\": %d,\n", nth);
    app("  \"timing_s\": {\"build\": %.2f, \"enumerate\": %.2f, \"grundy\": %.2f, \"total\": %.2f},\n",
        t_build, t_enum, t_dp, t_all);
    app("  \"peak_rss_mb\": %ld\n}\n", rss_mb());

    if (!outjson.empty()) {
        FILE* f = fopen(outjson.c_str(), "wb");
        if (!f) { fprintf(stderr, "cannot write %s\n", outjson.c_str()); return 9; }
        fwrite(j.data(), 1, j.size(), f);
        fclose(f);
        fprintf(stderr, "wrote %s\n", outjson.c_str());
    }
    printf("%s", j.c_str());
    return g_empty < 0 ? 9 : 0;
}
