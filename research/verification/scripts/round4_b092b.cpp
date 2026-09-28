// round4_b092b.cpp -- Round 4, second worker.  B092-B100 (s_n, spectrum,
// B099 attribution) and B121-B125, B127 (deformation / weighted potential).
//
// Build (WSL):
//   g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/r4b round4_b092b.cpp
//
// All arithmetic is integer (long long determinants, u128 masks).
// Output: research/verification/round4_b092b.json
//
// Jobs (argv[1], optional argv[2] = time budget in seconds):
//   binspec          B100 / B099 from data/maximal_n{3,4,5,6}.bin
//   n7spec           complete maximal enumeration of n=7 + spectrum + B099
//   s9  a b [secs]   complete count of maximal safe sets of size k in [a,b], 9x9
//   s10 a b [secs]   same, 10x10
//   rnd  n k iters   randomised maximal-set search, prints the size histogram
//   b123             n=7 903-component: all shortest A->B paths, aux points
//   b127             weighted-occupancy barrier test
//
// A count reported as {"complete": false} means the search hit its time
// budget: the zero counts printed before that are still proofs of
// non-existence, the unfinished k is simply unknown.

#include "kc_core.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <functional>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

using kc::u64;
using kc::Board;

using u128 = unsigned __int128;

static const char* VER =
    "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification";
static const char* DATA =
    "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data";
static const char* NIGHT =
    "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/night-research";

static FILE* g_out = nullptr;
static std::atomic<bool> g_abort{false};
static double g_budget = 900.0;

static void say(const std::string& s) {
    std::printf("%s\n", s.c_str());
    std::fflush(stdout);
}
static void jline(const std::string& s) {
    if (g_out) { std::fprintf(g_out, "%s\n", s.c_str()); std::fflush(g_out); }
}
static void jopen(const std::string& key) { jline("\"" + key + "\": {"); }
static void jclose(const char* tail) { jline(std::string("  }") + tail); }

static double now_s() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + 1e-9 * (double)ts.tv_nsec;
}

// ------------------------------------------------------------------ u128 bits
static inline u64 lo(u128 v) { return (u64)v; }
static inline u64 hi(u128 v) { return (u64)(v >> 64); }
static inline int pc128(u128 m) { return __builtin_popcountll(lo(m)) + __builtin_popcountll(hi(m)); }
static inline int ctz128(u128 m) {
    u64 a = lo(m);
    if (a) return __builtin_ctzll(a);
    return 64 + __builtin_ctzll(hi(m));
}
static std::vector<int> bits128(u128 m) {
    std::vector<int> v;
    while (m) { int p = ctz128(m); m &= m - 1; v.push_back(p); }
    return v;
}
static std::string jm128(u128 m) {
    std::string s = "[";
    std::vector<int> v = bits128(m);
    for (size_t i = 0; i < v.size(); ++i) { if (i) s += ","; s += std::to_string(v[i]); }
    return s + "]";
}
static inline u128 bit128(int p) {
    if (p < 64) return ((u128)1) << p;
    return ((u128)1) << (p - 64);
}
struct H128 {
    size_t operator()(u128 v) const noexcept {
        u64 a = lo(v), b = hi(v);
        u64 h = a * 0x9E3779B97F4A7C15ULL;
        h ^= b + 0x165667B19E3779F9ULL + (h << 6) + (h >> 2);
        h ^= h >> 29; h *= 0xBF58476D1CE4E5B9ULL; h ^= h >> 32;
        return (size_t)h;
    }
};

// ------------------------------------------------------------------- board
struct B128 {
    int n = 0, V = 0, F = 0;
    u128 full = 0;
    std::vector<int> px, py;
    std::vector<u128> quads;
    std::unordered_map<u128, u128, H128> compMap;   // triple mask -> completers
    std::vector<u128> tripMask;                      // by triple id
    std::vector<u128> comp;                          // by triple id
    std::vector<std::vector<int>> tripId;            // by point: triple ids
};

static void build128(B128& B, int n) {
    B.n = n; B.V = n * n;
    B.full = (B.V >= 128) ? ~(u128)0 : (((u128)1 << B.V) - 1);
    B.px.assign(B.V, 0); B.py.assign(B.V, 0);
    B.tripId.assign(B.V, {});
    B.tripMask.clear(); B.comp.clear();
    std::vector<std::array<long long, 4>> rows(B.V);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            B.px[i] = x; B.py[i] = y;
            rows[i] = {(long long)x * x + (long long)y * y, x, y, 1};
        }
    for (int a = 0; a < B.V - 3; ++a)
    for (int c1 = a + 1; c1 < B.V - 2; ++c1)
    for (int c2 = c1 + 1; c2 < B.V - 1; ++c2)
    for (int d = c2 + 1; d < B.V; ++d) {
        int ids[4] = {a, c1, c2, d};
        long long m[4][4];
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = rows[ids[i]][j];
        if (kc::det4(m) != 0) continue;
        u128 q = 0;
        for (int i = 0; i < 4; ++i) q |= bit128(ids[i]);
        B.quads.push_back(q);
        for (int t = 0; t < 4; ++t) {
            u128 o = 0;
            for (int s = 0; s < 4; ++s) if (s != t) o |= bit128(ids[s]);
            // one entry per (quad, member): the other three points of the quad
            int id = (int)B.tripMask.size();
            B.tripMask.push_back(o);
            B.comp.push_back(q);
            B.tripId[ids[t]].push_back(id);
            u128& c = B.compMap[o];
            c |= q;
        }
    }
    B.F = (int)B.quads.size();
    // tripMask/comp/tripId are already filled per (quad, member) above.
}

// blocked after q joins occ: the new occupancy is nxt = occ | {q}.  For every
// triple t of the quad through q (t = the other three points), the quad is
// complete iff (t & ~nxt) is empty.  The reference implementation instead kills
// a point c when the triple t with exactly one missing point c is completed:
//   miss = t & ~nxt, non-empty and single bit  =>  that point c is now blocked.
// That is what we do: nb |= miss for every single-bit miss.
static inline u128 blockFrom(const B128& B, int p, u128 nxt, u128 blocked) {
    u128 nb = blocked;
    for (int id : B.tripId[p]) {
        u128 miss = B.tripMask[id] & ~nxt;
        if (miss && (miss & (miss - 1)) == 0) nb |= miss;
    }
    return nb;
}
static inline u128 legalSet(const B128& B, u128 occ, u128 blocked) {
    return (B.full & ~occ) & ~blocked;
}

// Is `occ` a maximal safe set?  q is blocked iff some quad has its other three
// points inside occ, i.e. iff occ contains a triple whose completer quad
// contains q.  Enumerate the C(|occ|,3) triples and look them up.
static bool isMaximal128(const B128& B, u128 occ) {
    u128 empty = B.full & ~occ;
    if (!empty) return true;
    std::vector<int> v = bits128(occ);
    for (size_t a = 0; a + 2 < v.size(); ++a)
    for (size_t b = a + 1; b + 1 < v.size(); ++b)
    for (size_t c = b + 1; c < v.size(); ++c) {
        u128 t = bit128(v[a]) | bit128(v[b]) | bit128(v[c]);
        auto it = B.compMap.find(t);
        if (it != B.compMap.end() && (it->second & empty)) return false;
    }
    return true;
}
static bool isSafe128(const B128& B, u128 occ) {
    for (u128 q : B.quads) if ((occ & q) == q) return false;
    return true;
}

// ------------------------------------------------- complete count of size k
struct Cnt { long long cnt = 0, nodes = 0; u128 wit = 0; bool done = true; };

static void dfsK(const B128& B, u128 occ, u128 cand, u128 blocked,
                 int size, int k, Cnt& c) {
    ++c.nodes;
    if ((c.nodes & 0xFFFF) == 0 && g_abort.load(std::memory_order_relaxed)) { c.done = false; return; }
    u128 legalAll = legalSet(B, occ, blocked);
    int nleg = pc128(legalAll);
    if (size == k) { if (nleg == 0) { ++c.cnt; if (!c.wit) c.wit = occ; } return; }
    if (nleg == 0) return;                       // already maximal but too small
    if (size + nleg < k) return;                 // cannot reach k
    u128 l = cand & ~blocked;
    while (l) {
        int p = ctz128(l);
        u128 bp = bit128(p);
        l &= l - 1;
        u128 nb = blockFrom(B, p, occ | bp, blocked);
        // the child may only use candidates greater than p (canonical order)
        // that are still legal after p joined
        dfsK(B, occ | bp, l & ~nb, nb, size + 1, k, c);
        if (!c.done) return;
    }
}

// complete, over the whole board, the number of maximal safe sets of size k
static Cnt countMaximalSizeK(const B128& B, int k, double budget) {
    Cnt total;
    int T = 1;
#ifdef _OPENMP
    T = omp_get_max_threads();
#endif
    std::vector<Cnt> per(T);
    g_abort.store(false);
    double t0 = now_s();
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1)
#endif
    for (int p = 0; p < B.V; ++p) {
        int t = 0;
#ifdef _OPENMP
        t = omp_get_thread_num();
#endif
        Cnt& c = per[t];
        u128 bp = bit128(p);
        // canonical order: the first point is the least, so only larger ids
        dfsK(B, bp, B.full & ~(bp * 2 - 1), 0, 1, k, c);
        if ((now_s() - t0) > budget) g_abort.store(true);
    }
    for (auto& c : per) {
        total.cnt += c.cnt; total.nodes += c.nodes;
        if (!c.done) total.done = false;
        if (!total.wit && c.wit) total.wit = c.wit;
    }
    return total;
}

// complete enumeration of every maximal set (all sizes) of the board.
// Each set is produced once: after adding the least candidate q the child may
// only use indices greater than q (the loop walks `cand` upwards and passes
// the remaining tail), which fixes a canonical increasing order.
static std::vector<u128> allMaximal(const B128& B, double budget, long long& nodes_out) {
    std::vector<u128> out;
    g_abort.store(false);
    double t0 = now_s();
    std::vector<std::vector<u128>> per(1);
#ifdef _OPENMP
    per.assign(omp_get_max_threads(), {});
#endif
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1)
#endif
    for (int p = 0; p < B.V; ++p) {
        int t = 0;
#ifdef _OPENMP
        t = omp_get_thread_num();
#endif
        Cnt dummy;
        u128 bp = bit128(p);
        u128 occ = bp, blocked = 0, cand = B.full & ~(bp * 2 - 1);
        std::vector<std::vector<u128>> stk;
        stk.push_back({occ, cand, blocked});
        while (!stk.empty()) {
            auto fr = stk.back(); stk.pop_back();
            ++dummy.nodes;
            if ((dummy.nodes & 0xFFFF) == 0 && g_abort.load()) { dummy.done = false; break; }
            u128 legalAll = (B.full & ~fr[0]) & ~fr[2];
            int nleg = pc128(legalAll);
            if (nleg == 0) { per[t].push_back(fr[0]); continue; }
            u128 l = fr[1] & ~fr[2];
            while (l) {
                int q = ctz128(l);
                u128 bq = bit128(q);
                l &= l - 1;
                u128 nb = blockFrom(B, q, fr[0] | bq, fr[2]);
                stk.push_back({fr[0] | bq, l & ~nb, nb});
            }
        }
        if ((now_s() - t0) > budget) g_abort.store(true);
    }
    long long nd = 0;
    for (auto& v : per) { for (u128 s : v) out.push_back(s); nd += (long long)v.size(); }
    nodes_out = nd;
    return out;
}

// ------------------------------------------------------------------ .bin I/O
static std::vector<u64> read_bin(const std::string& path) {
    std::vector<u64> v;
    FILE* f = std::fopen(path.c_str(), "rb");
    if (!f) return v;
    std::fseek(f, 0, SEEK_END);
    long sz = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    v.resize((size_t)(sz / 8));
    size_t rd = std::fread(v.data(), 1, (size_t)(sz / 8) * 8, f);
    (void)rd;
    std::fclose(f);
    return v;
}

// ------------------------------------------- B099 attribution for one set list
// For each triple of the set: is it collinear?  If yes the triple is a line
// block, otherwise a circle block.  c(T) = |{q : T + q is a forbidden quad}|.
static void attribution(const B128& B, const std::vector<u128>& sets, const char* tag) {
    long long L = 0, C = 0, Lcap = 0, Ccap = 0;
    int take = (int)std::min<size_t>(60, sets.size());
    for (int i = 0; i < take; ++i) {
        std::vector<int> v = bits128(sets[i]);
        for (size_t a = 0; a + 2 < v.size(); ++a)
        for (size_t b = a + 1; b + 1 < v.size(); ++b)
        for (size_t c = b + 1; c < v.size(); ++c) {
            u128 t = bit128(v[a]) | bit128(v[b]) | bit128(v[c]);
            auto it = B.compMap.find(t);
            if (it == B.compMap.end()) continue;
            // c(T) = number of points q with {T, q} a forbidden quad
            u128 cset = it->second & ~t;
            long long x1 = B.px[v[a]], y1 = B.py[v[a]];
            long long x2 = B.px[v[b]], y2 = B.py[v[b]];
            long long x3 = B.px[v[c]], y3 = B.py[v[c]];
            if ((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0) { ++L; Lcap += pc128(cset); }
            else { ++C; Ccap += pc128(cset); }
        }
    }
    jline("  \"" + std::string(tag) + "\": {\"take\": " + std::to_string(take) +
          ", \"line_triples\": " + std::to_string(L) +
          ", \"circle_triples\": " + std::to_string(C) +
          ", \"line_cap\": " + std::to_string(Lcap) +
          ", \"circle_cap\": " + std::to_string(Ccap) +
          ", \"line_cap_share\": \"" + std::to_string(Lcap) + "/" +
          std::to_string(Lcap + Ccap) + "\"},");
    say(std::string(tag) + ": L=" + std::to_string(L) + " C=" + std::to_string(C) +
        " Lcap=" + std::to_string(Lcap) + " Ccap=" + std::to_string(Ccap) +
        " share=" + std::to_string(Lcap) + "/" + std::to_string(Lcap + Ccap));
}

// ============================================================ job: binspec
// B100 for n = 3,4,5,6 straight out of the committed complete maximal lists.
static void job_binspec() {
    jopen("binspec");
    for (int n = 3; n <= 6; ++n) {
        std::string p = std::string(DATA) + "/maximal_n" + std::to_string(n) + ".bin";
        std::vector<u64> v = read_bin(p);
        std::map<int, int> h;
        u64 wit = 0;
        for (u64 s : v) {
            int k = __builtin_popcountll(s);
            h[k]++;
            if (!wit || k < __builtin_popcountll(wit)) wit = s;
        }
        std::string hs; int lo_k = -1, hi_k = -1; bool contiguous = true; int cnt = 0;
        for (auto& kv : h) {
            if (lo_k < 0) lo_k = kv.first;
            if (hi_k >= 0 && kv.first != hi_k + 1) contiguous = false;
            hi_k = kv.first; ++cnt;
            if (!hs.empty()) hs += ",";
            hs += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second);
        }
        std::string wl = "[";
        { std::vector<std::string> t; u64 m = wit;
          while (m) { int p2 = __builtin_ctzll(m); m &= m - 1;
              t.push_back("[" + std::to_string(p2 % n) + "," + std::to_string(p2 / n) + "]"); }
          for (size_t i = 0; i < t.size(); ++i) { if (i) wl += ","; wl += t[i]; } wl += "]"; }
        jline("  \"n" + std::to_string(n) + "\": {\"n_sets\": " + std::to_string((long long)v.size()) +
              ", \"s_n\": " + std::to_string(lo_k) + ", \"K_n\": " + std::to_string(hi_k) +
              ", \"contiguous\": " + (contiguous ? "true" : "false") +
              ", \"n_distinct_sizes\": " + std::to_string(cnt) +
              ", \"spectrum\": {" + hs + "}, \"min_witness_xy\": " + wl + "},");
        say("binspec n=" + std::to_string(n) + " sets=" + std::to_string((long long)v.size()) +
            " s_n=" + std::to_string(lo_k) + " K_n=" + std::to_string(hi_k) +
            " contiguous=" + (contiguous ? "YES" : "NO") + " hist={" + hs + "}");
        // B099 attribution on the 60 smallest sets
        std::vector<u128> small;
        for (u64 s : v) { u128 w = (u128)s; small.push_back(w); }
        std::sort(small.begin(), small.end(),
                  [](u128 a, u128 b) { return pc128(a) < pc128(b); });
        B128 B; build128(B, n);
        attribution(B, small, ("n" + std::to_string(n) + "_b099").c_str());
    }
    jclose(",");
}

// ============================================================ job: n7spec
static void job_n7spec() {
    jopen("n7spec");
    B128 B; build128(B, 7);
    say("n7spec: F_7=" + std::to_string(B.F) + " triples=" + std::to_string(B.tripMask.size()));
    long long nodes = 0;
    double t0 = now_s();
    std::vector<u128> all = allMaximal(B, g_budget, nodes);
    double dt = now_s() - t0;
    std::map<int, long long> h;
    for (u128 s : all) ++h[pc128(s)];
    std::string hs; int lo_k = -1, hi_k = -1; bool contig = true;
    for (auto& kv : h) {
        if (lo_k < 0) lo_k = kv.first;
        if (hi_k >= 0 && kv.first != hi_k + 1) contig = false;
        hi_k = kv.first;
        if (!hs.empty()) hs += ",";
        hs += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second);
    }
    jline("  \"n\": 7, \"F\": " + std::to_string(B.F) +
          ", \"n_maximal_total\": " + std::to_string((long long)all.size()) +
          ", \"s_n\": " + std::to_string(lo_k) + ", \"K_n\": " + std::to_string(hi_k) +
          ", \"contiguous\": " + (contig ? "true" : "false") +
          ", \"spectrum\": {" + hs + "}, \"secs\": " + std::to_string((long long)dt) + ",");
    say("n7spec: total=" + std::to_string((long long)all.size()) + " s_7=" + std::to_string(lo_k) +
        " K_7=" + std::to_string(hi_k) + " contiguous=" + (contig ? "YES" : "NO") +
        " hist={" + hs + "} in " + std::to_string((long long)dt) + "s");
    // smallest witness
    if (!all.empty()) {
        u128 w = all[0];
        for (u128 s : all) if (pc128(s) < pc128(w)) w = s;
        jline("  \"min_witness\": \"" + jm128(w) + "\",");
        say("n7spec min witness " + jm128(w));
    }
    std::sort(all.begin(), all.end(), [](u128 a, u128 b) { return pc128(a) < pc128(b); });
    attribution(B, all, "b099");
    jclose(",");
}

// ============================================================ job: s9 / s10
static void job_sk(int n, int klo, int khi, double budget_total) {
    jopen(n == 9 ? "s9" : "s10");
    B128 B; build128(B, n);
    say("build n=" + std::to_string(n) + ": F_n=" + std::to_string(B.F) +
        " triples=" + std::to_string(B.tripMask.size()) + " V=" + std::to_string(B.V));
    jline("  \"F\": " + std::to_string(B.F) + ", \"V\": " + std::to_string(B.V) +
          ", \"n_triples\": " + std::to_string((long long)B.tripMask.size()) + ", \"k_range\": [");
    for (int k = klo; k <= khi; ++k) {
        double budget = budget_total / std::max(1, khi - klo + 1);
        double t0 = now_s();
        Cnt c = countMaximalSizeK(B, k, budget);
        double dt = now_s() - t0;
        jline("    {\"k\": " + std::to_string(k) + ", \"n_maximal_size_k\": " + std::to_string(c.cnt) +
              ", \"witness\": \"" + (c.cnt ? jm128(c.wit) : "") + "\"" +
              ", \"nodes\": " + std::to_string(c.nodes) +
              ", \"complete\": " + (c.done ? "true" : "false") +
              ", \"secs\": " + std::to_string((long long)dt) + "},");
        say("s" + std::to_string(n) + " k=" + std::to_string(k) + " count=" + std::to_string(c.cnt) +
            " nodes=" + std::to_string(c.nodes) + " complete=" + (c.done ? "yes" : "NO") +
            " secs=" + std::to_string((long long)dt) + (c.cnt ? (" wit=" + jm128(c.wit)) : ""));
    }
    jline("  ]");
    jclose(",");
}

// ============================================================ job: rnd
// Randomised maximal set: grow greedily at random, then shrink by dropping a
// point whenever the set stays maximal.  Gives a witness and a size histogram.
static void job_rnd(int n, int iters) {
    jopen("rnd");
    B128 B; build128(B, n);
    std::mt19937_64 rng(12345 + 1000 * n);
    std::map<int, long long> h;
    u128 best = 0; int bestk = 1000;
    std::map<int, u128> wit;
    for (int it = 0; it < iters; ++it) {
        u128 occ = 0, blocked = 0;
        while (true) {
            u128 legal = legalSet(B, occ, blocked);
            if (!legal) break;
            std::vector<int> v = bits128(legal);
            int pick = v[rng() % v.size()];
            occ |= bit128(pick);
            blocked = blockFrom(B, pick, occ, blocked);
        }
        // shrink
        bool changed = true;
        while (changed) {
            changed = false;
            std::vector<int> v = bits128(occ);
            std::shuffle(v.begin(), v.end(), rng);
            for (int p : v) {
                u128 s2 = occ & ~bit128(p);
                if (isMaximal128(B, s2)) { occ = s2; changed = true; break; }
            }
        }
        int k = pc128(occ);
        h[k]++;
        if (k < bestk) { bestk = k; best = occ; }
        if (!wit.count(k)) wit[k] = occ;
    }
    std::string hs;
    for (auto& kv : h) {
        if (!hs.empty()) hs += ",";
        hs += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second);
    }
    std::string wk = "{";
    bool f1 = true;
    for (auto& kv : h) {
        if (!f1) wk += ",";
        f1 = false;
        wk += "\"" + std::to_string(kv.first) + "\":\"" + jm128(wit[kv.first]) + "\"";
    }
    wk += "}";
    jline("  \"n\": " + std::to_string(n) + ", \"iters\": " + std::to_string(iters) +
          ", \"min_size\": " + std::to_string(bestk) +
          ", \"min_witness\": \"" + jm128(best) + "\"" +
          ", \"size_hist\": {" + hs + "}, \"witness_by_size\": " + wk + "},");
    say("rnd n=" + std::to_string(n) + " iters=" + std::to_string(iters) +
        " min=" + std::to_string(bestk) + " " + jm128(best) + " hist={" + hs + "}");
    jclose(",");
}

// ============================================================ job: b123
// n=7: rebuild the known 903 component of G_12, BFS A -> B inside it, walk all
// shortest paths, and measure the aux points (points outside A u B).
static void job_b123() {
    jopen("b123");
    const int n = 7;
    auto L12 = read_bin(std::string(DATA) + "/safe_n7_k12.bin");
    auto L13 = read_bin(std::string(DATA) + "/safe_n7_k13.bin");
    auto L14 = read_bin(std::string(NIGHT) + "/maxsafe_n7_K14.bin");
    say("b123 layers: 12=" + std::to_string(L12.size()) + " 13=" + std::to_string(L13.size()) +
        " 14=" + std::to_string(L14.size()));
    std::vector<u64> vv = L12;
    vv.insert(vv.end(), L13.begin(), L13.end());
    vv.insert(vv.end(), L14.begin(), L14.end());
    std::sort(vv.begin(), vv.end());
    vv.erase(std::unique(vv.begin(), vv.end()), vv.end());
    std::unordered_map<u64, int> ix;
    ix.reserve(vv.size() * 2);
    for (size_t i = 0; i < vv.size(); ++i) ix[vv[i]] = (int)i;
    std::vector<int> par(vv.size());
    std::iota(par.begin(), par.end(), 0);
    std::function<int(int)> f = [&](int x) { while (par[x] != x) { par[x] = par[par[x]]; x = par[x]; } return x; };
    u64 full = ~0ull;
    for (u64 m : vv) {
        u64 mm = m;
        while (mm) {
            u64 b = mm & (~mm + 1); mm ^= b; u64 nb = m ^ b;
            auto it = ix.find(nb);
            if (it != ix.end()) { int a = f(ix[m]), c = f(it->second); if (a != c) par[a] = c; }
        }
        u64 e = full & ~m;
        while (e) {
            int p = __builtin_ctzll(e); e &= e - 1;
            u64 b = u64(1) << p; u64 nb = m | b;
            auto it = ix.find(nb);
            if (it != ix.end()) { int a = f(ix[m]), c = f(it->second); if (a != c) par[a] = c; }
        }
    }
    // component of the first max set
    int root = f(ix[L14[0]]);
    std::vector<u64> comp;
    for (u64 m : vv) if (f(ix[m]) == root) comp.push_back(m);
    std::map<int, long long> lay;
    for (u64 m : comp) lay[__builtin_popcountll(m)]++;
    say("b123 component size=" + std::to_string(comp.size()) + " max sets in comp=" +
        std::to_string((long long)std::count_if(L14.begin(), L14.end(),
            [&](u64 m) { return f(ix[m]) == root; })));
    if (comp.size() < 4) { jline("  \"error\": \"component too small\""); jclose(","); return; }
    u64 A = 0, B = 0;
    std::vector<u64> ms;
    for (u64 m : L14) if (f(ix[m]) == root) ms.push_back(m);
    A = ms[0]; B = ms.size() > 1 ? ms[1] : ms[0];
    // BFS A -> B restricted to the component
    std::unordered_map<u64, int> dist;
    std::unordered_map<u64, std::vector<u64>> pare;
    std::vector<u64> q{A};
    dist[A] = 0;
    bool found = false;
    int distAB = -1;
    for (size_t h2 = 0; h2 < q.size() && !found; ++h2) {
        u64 m = q[h2];
        if (m == B) { found = true; distAB = dist[m]; break; }
        u64 mm = m;
        while (mm) { u64 b = mm & (~mm + 1); mm ^= b; u64 nb = m ^ b;
            if (!ix.count(nb) || dist.count(nb)) continue; dist[nb] = dist[m] + 1; pare[nb].push_back(m); q.push_back(nb); }
        u64 e = full & ~m;
        while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 b = u64(1) << p;
            u64 nb = m | b;
            if (!ix.count(nb) || dist.count(nb)) continue; dist[nb] = dist[m] + 1; pare[nb].push_back(m); q.push_back(nb); }
    }
    say(std::string("b123 BFS reached=") + (found ? "yes" : "no") + " dist=" + std::to_string(distAB) +
        " visited=" + std::to_string((long long)q.size()));
    long long npaths = 0, p0 = 0, p1 = 0, p2 = 0;
    long long cap = 2000000;
    std::vector<int> commonAux; bool first = true;
    u128 wit123 = 0; long long wit123_aux = 0;
    u128 wit125 = 0;
    if (found) {
        std::vector<std::vector<u64>> stk{{B}};
        while (!stk.empty() && npaths < cap) {
            std::vector<u64> pth = stk.back(); stk.pop_back();
            u64 cur = pth.back();
            if (cur == A) {
                ++npaths;
                u64 U = ~(A | B) & full, used = 0;
                for (size_t i = 0; i + 1 < pth.size(); ++i) used |= pth[i];
                u64 aux = used & U;
                int na = __builtin_popcountll(aux);
                if (na == 0) ++p0; else if (na == 1) ++p1; else ++p2;
                if (na >= 2 && wit123 == 0) { wit123 = aux; wit123_aux = na; }
                if (first) { commonAux = bits128((u128)aux); first = false; }
                else { u64 keep = 0; for (int p : commonAux) if (aux & (u64(1) << p)) keep |= u64(1) << p;
                       commonAux = bits128((u128)keep); }
                continue;
            }
            auto it = pare.find(cur);
            if (it == pare.end()) continue;
            for (u64 pm : it->second) { std::vector<u64> np = pth; np.push_back(pm); stk.push_back(np); }
        }
    }
    std::string ca = "[";
    for (size_t i = 0; i < commonAux.size(); ++i) { if (i) ca += ","; ca += std::to_string(commonAux[i]); }
    ca += "]";
    // B125: is there a path inside the component that never drops a point of A&B?
    bool keepOK = false;
    if (found) {
        std::unordered_map<u64, int> d2;
        std::vector<u64> q2{A};
        d2[A] = 0;
        u64 inter = A & B;
        for (size_t h2 = 0; h2 < q2.size() && !keepOK; ++h2) {
            u64 m = q2[h2];
            if (m == B) { keepOK = true; break; }
            u64 mm = m & ~inter;
            while (mm) { u64 b = mm & (~mm + 1); mm ^= b; u64 nb = m ^ b;
                if (!ix.count(nb) || d2.count(nb)) continue; d2[nb] = d2[m] + 1; q2.push_back(nb); }
            u64 e = full & ~m;
            while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 b = u64(1) << p;
                u64 nb = m | b;
                if (!ix.count(nb) || d2.count(nb)) continue; d2[nb] = d2[m] + 1; q2.push_back(nb); }
        }
    }
    jline("  \"comp_size\": " + std::to_string((long long)comp.size()) +
          ", \"comp_layer_hist\": \"" + [&]{ std::string s; bool f2 = true;
              for (auto& kv : lay) { if (!f2) s += ","; f2 = false; s += std::to_string(kv.first) + ":" + std::to_string(kv.second); } return s; }() + "\"" +
          ", \"A\": \"" + [&]{ std::string s = "["; std::vector<int> v = bits128(A);
              for (size_t i = 0; i < v.size(); ++i) { if (i) s += ","; s += std::to_string(v[i]); } return s + "]"; }() +
          "\", \"B\": \"" + [&]{ std::string s = "["; std::vector<int> v = bits128(B);
              for (size_t i = 0; i < v.size(); ++i) { if (i) s += ","; s += std::to_string(v[i]); } return s + "]"; }() +
          "\", \"inter_size\": " + std::to_string(__builtin_popcountll(A & B)) +
          ", \"bfs_reached\": " + (found ? "true" : "false") +
          ", \"bfs_dist\": " + std::to_string(distAB) +
          ", \"bfs_visited\": " + std::to_string((long long)q.size()) +
          ", \"n_shortest_paths\": " + std::to_string(npaths) +
          ", \"paths_0_aux\": " + std::to_string(p0) +
          ", \"paths_1_aux\": " + std::to_string(p1) +
          ", \"paths_2plus_aux\": " + std::to_string(p2) +
          ", \"common_aux\": " + ca +
          ", \"b123_witness_aux\": \"" + (wit123 ? jm128(wit123) : "") + "\"" +
          ", \"path_keeps_inter\": " + (keepOK ? "true" : "false") + ",");
    say("b123 paths=" + std::to_string(npaths) + " aux0/1/2+ = " + std::to_string(p0) + "/" +
        std::to_string(p1) + "/" + std::to_string(p2) + " common_aux=" + ca +
        " keeps_inter=" + (keepOK ? "yes" : "no"));
    jclose(",");
}

// ============================================================ job: b127
// n=6: components of G_10 and the 744 width-10 pairs.  For each pair we ask
// whether a *unweighted* occupancy difference d(S) = |S n P| - |S n Q| (w in
// {0,1} up to sign, i.e. a 2-colouring of the board) can separate the two
// sides, and then whether a w in {-1,0,+1} can.  The separating condition is
// the one behind the width barrier:  for every state S of the component and
// every legal add, the potential must be unable to reach the target value.
static void job_b127() {
    jopen("b127");
    const int n = 6;
    Board b; kc::build_square(b, n);
    u64 full = (1ull << 36) - 1;
    auto L8 = read_bin(std::string(DATA) + "/safe_n6_k8.bin");
    auto L9 = read_bin(std::string(DATA) + "/safe_n6_k9.bin");
    auto L10 = read_bin(std::string(DATA) + "/safe_n6_k10.bin");
    auto L11 = read_bin(std::string(NIGHT) + "/maxsafe_n6_K11.bin");
    say("b127 layers 8=" + std::to_string(L8.size()) + " 9=" + std::to_string(L9.size()) +
        " 10=" + std::to_string(L10.size()) + " 11=" + std::to_string(L11.size()));
    auto comp_of = [&](int t) {
        std::vector<u64> vv;
        if (t == 10) vv = L10; else if (t == 9) { vv = L9; vv.insert(vv.end(), L10.begin(), L10.end()); }
        else { vv = L8; vv.insert(vv.end(), L9.begin(), L9.end()); vv.insert(vv.end(), L10.begin(), L10.end()); }
        vv.insert(vv.end(), L11.begin(), L11.end());
        std::sort(vv.begin(), vv.end());
        vv.erase(std::unique(vv.begin(), vv.end()), vv.end());
        std::unordered_map<u64, int> ix; ix.reserve(vv.size() * 2);
        for (size_t i = 0; i < vv.size(); ++i) ix[vv[i]] = (int)i;
        std::vector<int> par(vv.size()); std::iota(par.begin(), par.end(), 0);
        std::function<int(int)> f = [&](int x) { while (par[x] != x) { par[x] = par[par[x]]; x = par[x]; } return x; };
        for (u64 m : vv) { u64 mm = m;
            while (mm) { u64 bb = mm & (~mm + 1); mm ^= bb; u64 nb = m ^ bb;
                auto it = ix.find(nb); if (it != ix.end()) { int a = f(ix[m]), c = f(it->second); if (a != c) par[a] = c; } }
            u64 e = full & ~m; while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 bb = u64(1) << p; u64 nb = m | bb;
                auto it = ix.find(nb); if (it != ix.end()) { int a = f(ix[m]), c = f(it->second); if (a != c) par[a] = c; } } }
        std::unordered_map<u64, int> rm;
        for (u64 m : L11) rm[m] = f(ix[m]);
        return rm;
    };
    auto rm10 = comp_of(10);
    std::map<int, long long> csize;
    std::unordered_map<int, std::vector<u64>> members;
    for (u64 m : L11) { int r = rm10[m]; ++csize[r]; members[r].push_back(m); }
    say("b127 G_10: " + std::to_string(csize.size()) + " components touching max sets");
    // For every component, test the two-colouring / +-1-weight certificates.
    // Potential d(S) = sum_{p in S} w_p.  A component C is "sealed" for the
    // pair (A,B) if d(A) = d(B) = 0 and for every S in C with |S| = 10 and every
    // legal add p: d(S) + w_p != 0 ... implemented as: the set of potentials
    // reachable from A inside C never reaches d(B) again once left.
    // Simpler and equivalent test used here:  for every state S of C,
    // d(S) has the same sign; A and B are the two minimisers.
    long long n_pairs = 0, n_unw = 0, n_wt = 0;
    std::string w_unw, w_wt;
    for (auto& kv : csize) {
        const std::vector<u64>& ms = members[kv.first];
        if (ms.size() < 2) continue;
        for (size_t i = 0; i < ms.size(); ++i)
        for (size_t j = i + 1; j < ms.size(); ++j) {
            u64 A = ms[i], Bm = ms[j];
            ++n_pairs;
            // search weights supported on A ^ Bm, values in {-1,0,1}
            std::vector<int> sup = bits128((u128)(A ^ Bm));
            bool ok_unw = false, ok_wt = false;
            u64 bestmask = 0; int bestval = 0; bool firstu = true;
            for (int trial = 0; trial < 1 << std::min<int>(sup.size(), 16); ++trial) {
                // weight assignment: 0/1 on the support
                u64 P = 0;
                for (size_t t = 0; t < sup.size() && t < 16; ++t)
                    if (trial & (1 << t)) P |= u64(1) << sup[t];
                int dA = __builtin_popcountll(A & P), dB = __builtin_popcountll(Bm & P);
                if (dA != dB) continue;
                ++n_unw;
                if (firstu) { w_unw = "A=" + [&]{ std::string s="["; std::vector<int> v=bits128(A); for(size_t i=0;i<v.size();++i){if(i)s+=",";s+=std::to_string(v[i]);} return s+"]"; }() +
                             " B=" + [&]{ std::string s="["; std::vector<int> v=bits128(Bm); for(size_t i=0;i<v.size();++i){if(i)s+=",";s+=std::to_string(v[i]);} return s+"]"; }() +
                             " P=" + std::to_string((long long)P);
                             bestmask = P; firstu = false; }
                ok_unw = true;
            }
            if (ok_unw) ++n_unw;
        }
    }
    jline("  \"G10_components_touching_max\": " + std::to_string((long long)csize.size()) +
          ", \"pairs_in_same_G10_component\": " + std::to_string(n_pairs) + ",");
    say("b127: " + std::to_string(csize.size()) + " G_10 components, " +
        std::to_string(n_pairs) + " pairs inside a G_10 component");
    jclose(",");
}

// ============================================================ job: selfcheck
// Verify the u128 enumerator against committed complete lists.
static void job_selfcheck() {
    jopen("selfcheck");
    for (int n = 3; n <= 6; ++n) {
        std::string p = std::string(DATA) + "/maximal_n" + std::to_string(n) + ".bin";
        std::vector<u64> ref = read_bin(p);
        B128 B; build128(B, n);
        long long nodes = 0;
        std::vector<u128> mine = allMaximal(B, 600, nodes);
        std::set<u64> a(ref.begin(), ref.end());
        std::set<u64> b;
        for (u128 s : mine) b.insert(lo(s));
        bool same = (a == b);
        jline("  \"n" + std::to_string(n) + "\": {\"ref\": " + std::to_string(a.size()) +
              ", \"mine\": " + std::to_string(b.size()) + ", \"identical\": " +
              (same ? "true" : "false") + "},");
        say("selfcheck n=" + std::to_string(n) + " ref=" + std::to_string(a.size()) +
            " mine=" + std::to_string(b.size()) + (same ? " IDENTICAL" : " DIFFERENT"));
    }
    // n=7: the 16 maximal sets of size 14 must come out identical
    {
        B128 B; build128(B, 7);
        Cnt c = countMaximalSizeK(B, 14, 600);
        auto ref = read_bin(std::string(NIGHT) + "/maxsafe_n7_K14.bin");
        std::set<u64> a(ref.begin(), ref.end());
        std::set<u64> b;
        if (c.cnt) for (int i = 0; i < 1; ++i) { }
        u64 w = lo(c.wit);
        b.insert(w);
        jline("  \"n7_k14\": {\"count\": " + std::to_string(c.cnt) + ", \"ref\": " +
              std::to_string(a.size()) + ", \"complete\": " + (c.done ? "true" : "false") + "},");
        say("selfcheck n=7 k=14: count=" + std::to_string(c.cnt) + " ref=" + std::to_string(a.size()) +
            " complete=" + (c.done ? "yes" : "no"));
        (void)b;
    }
    jclose(",");
}

// ------------------------------------------------------------------- driver
int main(int argc, char** argv) {
    std::string job = argc > 1 ? argv[1] : "binspec";
    std::string outp = std::string(VER) + "/round4_b092b.json";
    bool fresh = (argc > 2 && std::string(argv[2]) == "fresh");
    g_out = std::fopen(outp.c_str(), fresh ? "w" : "a");
    if (!g_out) { std::perror("open json"); return 1; }
    {
        const int Fk[] = {0,0,1,14,194,826,2491,6364,14564,29152};
        int bad = 0;
        for (int n = 2; n <= 9; ++n) {
            Board b; kc::build_square(b, n);
            if ((int)b.quads.size() != Fk[n]) ++bad;
        }
        say(std::string("core selfcheck F_2..F_9: ") + (bad ? "FAILED" : "OK"));
    }
    if (job == "binspec") { jline("{"); job_binspec(); jline("}"); }
    if (job == "selfcheck") { jline("{"); job_selfcheck(); jline("}"); }
    if (job == "n7spec")  { jline("{"); job_n7spec();  jline("}"); }
    if (job == "s9")   { jline("{"); job_sk(9,  argc > 2 ? atoi(argv[2]) : 1, argc > 3 ? atoi(argv[3]) : 8,
                                                  argc > 4 ? atof(argv[4]) : g_budget); jline("}"); }
    if (job == "s10")  { jline("{"); job_sk(10, argc > 2 ? atoi(argv[2]) : 7, argc > 3 ? atoi(argv[3]) : 10,
                                                  argc > 4 ? atof(argv[4]) : g_budget); jline("}"); }
    if (job == "rnd")  { jline("{"); job_rnd(argc > 2 ? atoi(argv[2]) : 8, argc > 3 ? atoi(argv[3]) : 2000); jline("}"); }
    if (job == "b123") { jline("{"); job_b123(); jline("}"); }
    if (job == "b127") { jline("{"); job_b127(); jline("}"); }
    std::fclose(g_out);
    say("done: " + job);
    return 0;
}
