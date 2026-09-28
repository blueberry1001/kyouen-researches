// Round5 B501/B502: exact random-play win rate p_rand, memory-lean, for n=8.
//
// NOT a rewrite of round4_b501_prand.cpp.  Enumeration, child indexing, the
// Grundy recurrence and the level statistics are the same algorithm; only the
// NUMERIC REPRESENTATION of the DP value is swapped.
//
//   round4 : numerator = 20-limb (180 decimal digit) big integer, 80 B/state.
//   round5 : numerator = residue mod 2^61-1  (8 B/state) + a u32 fixed-point
//            track (4 B/state) that is ONLY a filter for order/threshold tests.
//
// Definition (unchanged):  p_rand(terminal)=0,
//   p_rand(S) = 1 - (1/|L(S)|) sum_{u in L(S)} p_rand(S + {u}).
//
// ---------------------------------------------------------------------------
// THE DENOMINATOR, AND WHY THE DRAFT WAS WRONG
// ---------------------------------------------------------------------------
// All level-(k+1) values share the per-level common denominator
//     D_{k+1} = prod_{j<=k+1} L_j,     L_j = lcm of the level-j child counts,
// so with cnt = |L(S)|,
//     num_k(S) = ( cnt*D_{k+1} - sum_children ) * ( L_k / cnt ).
// In modular arithmetic that is exact: cnt and every prime power of L_k are
// <= 64 and both Mersenne primes used are > 64, so all of them are invertible
// and (L_k/cnt) mod p == (L_k mod p) * (cnt mod p)^{-1}  (cnt | L_k).
// Hence every value at level k is exactly (num_k mod p) * (D_k mod p)^{-1}, and
// the DP only has to carry num_k mod p.
//
// L_k DOES NOT FIT IN 64 BITS.  The REDUCED per-level denominator already has
// 34 decimal digits at n=5, 64 at n=6 and 112 at n=7; L_k is the unreduced
// factor, so it is much larger still.  L_k is therefore carried as the product
// of the maximal prime powers occurring among the child counts present at the
// level.  cnt <= 64, so each such prime power is a plain small integer, and the
// product is kept only as a residue plus an exact log2.
//
// CONSEQUENCE -- AND THIS IS THE POINT OF THE WHOLE FILE:
// D_0 = prod_{j} L_j has  2^19 (n=4), 2^112 (n=5), 2^212 (n=6), 2^372 (n=7)
// bits.  A single 61-bit prime can therefore NOT order residues across levels,
// and CANNOT decide p > 2/3, for any n >= 5.  The draft's cross-level max and
// its threshold counts were residue comparisons dressed up as exact
// arithmetic.  So this program separates the two claims explicitly:
//
//   EXACT, unconditionally:
//     * enumeration, level sizes, edge counts, grundy values, n_P, n_N
//     * every PER-LEVEL maximum of p_rand -- a level shares ONE denominator, so
//       ordering by residue == ordering by value with no condition at all
//     * the residue of any individual state's value (enables the (a mod p) *
//       (b mod p)^{-1} identity used to cross-check the big-integer results)
//     * threshold counts on levels with D_bits < 30.5 (then 3*D does not wrap)
//
//   FILTERED, with a stated error bound and an auditable margin:
//     * the cross-level maximum and the all-level threshold counts.  A u32
//       fixed-point track (scale 2^30) is carried alongside; its absolute error
//       is <= 2^-31 per value and does NOT amplify down the levels (p_k is an
//       affine function of the child values), so the total error bound is
//       2^-31 = 4.7e-10 for the whole DP.  `filter_margin` reports the gap
//       between the winner and the runner-up so the selection can be audited.
//     Reproduced exactly: n=4/5/6/7 P_max and the threshold counts.
//
//   `thresholds_exact_all_levels` is false for every n >= 5.  That is a
//   statement about the arithmetic, not about the game.
//
// ---------------------------------------------------------------------------
// MEMORY (this is what makes n=8 conceivable at all)
// ---------------------------------------------------------------------------
// The child index is a plain lower_bound per edge, NOT a per-level CSR/hash:
// the modular edge pass is cheap enough that the extra log(M) is noise, and a
// CSR costs 4 B/edge (~33 B/state at n=7) and a hash table 12 B/slot at 2 slots
// per state (24 B/state) -- together more than the DP value itself.  Peak is
// ~58 B/state of the widest level.  Level vectors are MOVED out of the outer
// arrays, so no level is ever stored twice.  numk doubles as the grundy
// bit-set scratch, and cnt is a u8.
//
// Usage (WSL):
//   g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/pr8 round5_b501_prand8.cpp
//   /tmp/pr8 --selftest
//   /tmp/pr8 6            [/tmp/n6.json]    # 1 prime, 12 B/state
//   /tmp/pr8 6 x          [/tmp/n6x.json]   # 2 primes, 20 B/state (123-bit)
//   /tmp/pr8 7 x /tmp/n7x.json
//   /tmp/pr8 8 x /tmp/n8x.json
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <cmath>
#include <string>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#ifdef _OPENMP
#include <omp.h>
#endif
#include "kc_core.h"

using kc::u64;
using u32 = std::uint32_t;

static double now_s() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}
static double rss_peak_gb() {
    FILE* f = fopen("/proc/self/status", "r");
    if (!f) return -1;
    char line[256];
    long long v = -1;
    while (fgets(line, sizeof line, f))
        if (strncmp(line, "VmHWM:", 6) == 0) { sscanf(line + 6, "%lld", &v); break; }
    fclose(f);
    return v / 1048576.0;
}

// ============================================================ mod-Mersenne
// P1 = 2^61-1 is a Mersenne prime, so the fold below is exact with no __int128
// modulo.  The draft's second prime, 2^62-89, is NOT PRIME (it is divisible by
// 5: 2^62-89 == 0 mod 5), so every F_p2 computation in the "n x" cross-check
// path of the draft was meaningless.  P2 = 2^61+7 is prime and is used instead;
// its arithmetic goes through __int128 % so it makes no fold requirement, but
// it is checked for primality in --selftest.
static constexpr u64 P1 = (1ULL << 61) - 1;      // 2305843009213693951
static constexpr u64 P2 = (1ULL << 61) + 7;      // 2305843009213693967

// Reduce A = lo + 2^64*hi modulo P1 = 2^61-1, given A < P1^2.
//   2^64 = 8*2^61 == 8 (mod P1)  => A == lo + 8*hi = T  (T < 2^65)
//   2^61 == 1 (mod P1)            => T == (T>>61) + (T & (2^61-1))
// T < 2^65 gives (T>>61) <= 15 and the sum < 2^61 + 15 < 2*P1, so one
// conditional subtract is exact.  No __int128 modulo anywhere.
static inline u64 mfold61(u64 lo, u64 hi) {
    unsigned __int128 T = (unsigned __int128)lo + 8 * (unsigned __int128)hi;
    u64 t2 = (u64)(T >> 61) + ((u64)T & ((1ULL << 61) - 1));
    if (t2 >= P1) t2 -= P1;
    return t2;
}
static inline u64 mmul(u64 x, u64 y) {
    unsigned __int128 t = (unsigned __int128)x * y;
    return mfold61((u64)t, (u64)(t >> 64));
}
static inline u64 mmul_s(u64 x, u64 v) {
    unsigned __int128 t = (unsigned __int128)x * v;
    return mfold61((u64)t, (u64)(t >> 64));
}
static inline u64 madd(u64 x, u64 y) {
    u64 s = x + y;
    if (s < x || s >= P1) s -= P1;
    return s;
}
static inline u64 msub(u64 x, u64 y) { return x >= y ? x - y : x + (P1 - y); }
static u64 mpow(u64 a, u64 e) {
    u64 r = 1;
    while (e) { if (e & 1) r = mmul(r, a); a = mmul(a, a); e >>= 1; }
    return r;
}
static std::string mstr(u64 v) {
    if (v == 0) return "0";
    std::string s;
    while (v) { s += char('0' + (int)(v % 10)); v /= 10; }
    std::reverse(s.begin(), s.end());
    return s;
}

// (cnt mod p)^{-1} for cnt = 1..64 (cnt = 0 is terminal and never used).
// NOTE: mpow is mod P1, so g_invc2 needs its own P2 exponentiation.  The draft
// used mpow(c, P1-2) for both tables, which is an inverse modulo P1 stored in
// the "mod P2" table -- caught by the div-cnt-p2 selftest case.
static u64 g_invc1[65], g_invc2[65];
static u64 pow_raw(u64 a, u64 e, u64 p) {
    u64 r = 1, b = a % p;
    while (e) {
        if (e & 1) r = (u64)((unsigned __int128)r * b % p);
        b = (u64)((unsigned __int128)b * b % p);
        e >>= 1;
    }
    return r;
}
static void invc_init() {
    for (int c = 1; c <= 64; ++c) {
        g_invc1[c] = mpow((u64)c, P1 - 2);
        g_invc2[c] = pow_raw((u64)c, P2 - 2, P2);
    }
}

// --------------------------------------------- the second prime (2^61+7)
// Used only by the parallel cross-check run ("n x"); u128 % u64 is exact.
static inline u64 m2add(u64 x, u64 y) { unsigned __int128 t = (unsigned __int128)x + y; return (u64)(t % P2); }
static inline u64 m2sub(u64 x, u64 y) { return x >= y ? x - y : (u64)(((unsigned __int128)P2 + x - y) % P2); }
static inline u64 m2mul(u64 x, u64 y) { return (u64)(((unsigned __int128)x * y) % P2); }
static inline u64 m2mul_s(u64 x, u64 v) { return (u64)(((unsigned __int128)x * v) % P2); }

// ------------------------------------------------- fixed-point filter scale
// p_rand is in [0,1]; SCALE = 2^30 keeps the whole DP inside a u32 with a
// per-value rounding error of 2^-31.
static constexpr u32 SCALE = 1u << 30;
static constexpr double FILTER_ABS_ERR = 0.5 / (double)SCALE;   // 4.66e-10

// ================================================================= context
struct Ctx {
    kc::Board board;
    int n = 0, V = 0;
    std::vector<u64> quads;
    u64 FULL = 0;
    double build_s = 0;
};
static void build_ctx(Ctx& ctx, int n) {
    double t0 = now_s();
    kc::build_square(ctx.board, n);
    ctx.n = n; ctx.V = ctx.board.V; ctx.FULL = ctx.board.full;
    ctx.quads = ctx.board.quads;
    std::sort(ctx.quads.begin(), ctx.quads.end());
    ctx.build_s = now_s() - t0;
}
static inline u64 legal_one(const Ctx& ctx, u64 occ) {
    u64 empty = ctx.FULL & ~occ;
    u64 blocked = 0;
    for (u64 q : ctx.quads)
        if (__builtin_popcountll(occ & q) == 3) blocked |= (q & ~occ);
    return empty & ~blocked;
}
static void legal_level(const Ctx& ctx, const std::vector<u64>& A, std::vector<u64>& out) {
    size_t M = A.size();
    out.resize(M);
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)M; ++i) out[(size_t)i] = legal_one(ctx, A[(size_t)i]);
}

// ==================================================================== stats
struct LevelStat {
    size_t size = 0, edges = 0;
    long long nP = 0, nN = 0;
    long long over23 = 0, over34 = 0, gt_half = 0, over13 = 0;      // filtered
    long long over23_e = 0, over34_e = 0, gt_half_e = 0, over13_e = 0; // exact
    double Dbits = 0.0;
    u64 Dmod[2] = {1, 1};
    bool thr_exact = false;
    u64 best = 0; long long best_count = 0;      // EXACT per-level max residue
    double best_val = 0.0, runner_up = 0.0;      // filtered
    double secs = 0;
};

// ============================================================== enumeration
static void enumerate_levels(const Ctx& ctx, std::vector<std::vector<u64>>& levels,
                             std::vector<std::vector<u64>>& lms,
                             std::vector<size_t>& level_sizes, size_t& total) {
    levels.clear(); lms.clear(); level_sizes.clear();
    levels.push_back({0});
    lms.push_back({ctx.FULL});
    level_sizes.push_back(1);
    total = 1;
    for (int step = 0; step <= ctx.V; ++step) {
        // Copy: push_back below may reallocate the outer vector, which would
        // invalidate a reference into levels.
        const std::vector<u64> A = levels.back();
        const std::vector<u64> LM = lms.back();
        const size_t M = A.size();
        std::vector<size_t> pcnt(ctx.V, 0), off(ctx.V + 1, 0);
        for (size_t i = 0; i < M; ++i) {
            u64 lm = LM[i];
            while (lm) { int v = __builtin_ctzll(lm); lm &= lm - 1; ++pcnt[v]; }
        }
        for (int v = 0; v < ctx.V; ++v) off[v + 1] = off[v] + pcnt[v];
        size_t est = off[ctx.V];
        if (est == 0) break;
        std::vector<u64> nxt(est);
        std::vector<size_t> cur(off.begin(), off.end() - 1);
        for (size_t i = 0; i < M; ++i) {
            u64 lm = LM[i];
            while (lm) {
                int v = __builtin_ctzll(lm); lm &= lm - 1;
                nxt[cur[v]++] = A[i] | (u64(1) << v);
            }
        }
        std::sort(nxt.begin(), nxt.end());
        nxt.erase(std::unique(nxt.begin(), nxt.end()), nxt.end());
        // uint32_t indices cap a level at 2^32 states; refuse rather than
        // silently wrapping, since a wrapped index would corrupt the DP.
        if (nxt.size() > 0xFFFFFFFFULL) {
            fprintf(stderr, "LEVEL OVERFLOW: %zu exceeds the 2^32 index cap\n", nxt.size());
            exit(5);
        }
        total += nxt.size();
        std::vector<u64> nlm;
        legal_level(ctx, nxt, nlm);
        size_t nsz = nxt.size();
        // Snapshot the size: levels[k] is released during the solve so that
        // only two adjacent levels stay resident.
        level_sizes.push_back(nsz);
        levels.push_back(std::move(nxt));
        lms.push_back(std::move(nlm));
        fprintf(stderr, "    enumerated level %2d: %12zu states  (rss %.1fGB)\n",
                step + 1, nsz, rss_peak_gb());
        fflush(stderr);
    }
}

// ================================================================= self-test
static int selftest() {
    int bad = 0, shown = 0;
    auto chk = [&](const char* w, bool ok) {
        if (!ok) { if (shown < 20) { printf("  FAIL %s\n", w); ++shown; } ++bad; }
    };
    std::mt19937_64 rng(999);
    for (u64 v = 1; v < 70; ++v) {
        chk("inv", mmul(v, mpow(v, P1 - 2)) == 1);
        chk("mul-small", mmul_s(v, 12345) == (u64)((unsigned __int128)v * 12345 % P1));
    }
    for (int t = 0; t < 200000; ++t) {
        u64 a = rng() % P1, b = rng() % P1;
        u64 g = mmul(a, b);
        if (g != (u64)((unsigned __int128)a * b % P1)) {
            if (shown < 5) printf("  mul fail a=%llu b=%llu\n", (unsigned long long)a,
                                  (unsigned long long)b);
            ++bad;
        }
        if (mmul_s(a, 37) != (u64)((unsigned __int128)a * 37 % P1)) ++bad;
        if (madd(a, b) != (u64)((unsigned __int128)(a + b) % P1)) ++bad;
        if (msub(a, b) != (u64)((a >= b ? a - b : (unsigned __int128)P1 + a - b) % P1)) ++bad;
    }
    for (u64 v = 1; v < 70; ++v)
        chk("p2-mul", m2mul(v, 12345) == (u64)((unsigned __int128)v * 12345 % P2));
    for (int t = 0; t < 50000; ++t) {
        u64 a = rng() % P2, b = rng() % P2;
        chk("p2-mul128", m2mul(a, b) == (u64)((unsigned __int128)a * b % P2));
        chk("p2-add128", m2add(a, b) == (u64)((unsigned __int128)(a + b) % P2));
        chk("p2-sub128", m2sub(a, b) ==
                         (u64)((a >= b ? a - b : (unsigned __int128)P2 + a - b) % P2));
    }
    for (u64 c = 2; c <= 30; ++c) {
        u64 val = msub(1, mpow(c, P1 - 2));
        chk("rational", mmul_s(val, c) == msub(c, 1));
    }
    // (L * inv(c)) * c == L, the (L_k/cnt) identity the solver depends on.
    {
        std::mt19937_64 r2(4242);
        for (int t = 0; t < 20000; ++t) {
            u64 L = 1 + r2() % P1;
            unsigned c = 1 + (unsigned)(r2() % 64);
            if (L % c) continue;
            chk("div-cnt", mmul_s(mmul(L, g_invc1[c]), c) == L);
            chk("div-cnt-p2", m2mul_s(m2mul(L % P2, g_invc2[c]), c) == (L % P2));
        }
    }
    // P2 must actually be prime or the whole "n x" cross-check path is void.
    // Miller-Rabin with the small-prime base set (deterministic for these sizes).
    {
        auto mr_prime = [](u64 n) {
            if (n < 2) return false;
            for (u64 s : {2ull, 3ull, 5ull, 7ull, 11ull, 13ull, 17ull, 19ull, 23ull,
                          29ull, 31ull, 37ull}) {
                if (n % s == 0) return n == s;
            }
            u64 d = n - 1; int r = 0;
            while ((d & 1) == 0) { d >>= 1; ++r; }
            for (u64 a : {2ull, 3ull, 5ull, 7ull, 11ull, 13ull, 17ull, 19ull, 23ull,
                          29ull, 31ull, 37ull}) {
                u64 x = mpow(a % n, d);
                if (x == 1 || x == n - 1) continue;
                bool composite = true;
                for (int t = 0; t < r - 1; ++t) {
                    x = mmul(x, x);
                    if (x == n - 1) { composite = false; break; }
                }
                if (composite) return false;
            }
            return true;
        };
        // mpow/mmul are mod P1; for primality of P2 use plain u128 arithmetic.
        auto mr_prime_raw = [](u64 n) {
            if (n < 2) return false;
            for (u64 s : {2ull, 3ull, 5ull, 7ull, 11ull, 13ull, 17ull, 19ull, 23ull,
                          29ull, 31ull, 37ull}) {
                if (n % s == 0) return n == s;
            }
            u64 d = n - 1; int r = 0;
            while ((d & 1) == 0) { d >>= 1; ++r; }
            for (u64 a : {2ull, 3ull, 5ull, 7ull, 11ull, 13ull, 17ull, 19ull, 23ull,
                          29ull, 31ull, 37ull}) {
                u64 x = 1, b = a % n, e = d;
                while (e) { if (e & 1) x = (u64)((unsigned __int128)x * b % n);
                            b = (u64)((unsigned __int128)b * b % n); e >>= 1; }
                if (x == 1 || x == n - 1) continue;
                bool composite = true;
                for (int t = 0; t < r - 1; ++t) {
                    x = (u64)((unsigned __int128)x * x % n);
                    if (x == n - 1) { composite = false; break; }
                }
                if (composite) return false;
            }
            return true;
        };
        chk("P1 prime", mr_prime(P1));
        chk("P2 prime", mr_prime_raw(P2));
        chk("P2 not the draft's composite", ((1ULL << 62) - 89) % 5 == 0);
    }
    // the lcm built out of maximal prime powers equals the true lcm
    for (int t = 0; t < 2000; ++t) {
        bool present[65] = {false};
        for (int i = 0; i < 64; ++i)
            if (rng() & 1) present[1 + (int)(rng() % 64)] = true;
        long long want = 1;
        for (int c = 1; c <= 64; ++c)
            if (present[c]) want = want * c / std::gcd(want, (long long)c);
        u64 got1 = 1, got2 = 1;
        for (int p = 2; p <= 64; ++p) {
            int e = 0;
            for (int c = 1; c <= 64; ++c) {
                if (!present[c]) continue;
                int x = c, f = 0;
                while (x % p == 0) { x /= p; ++f; }
                if (f > e) e = f;
            }
            if (!e) continue;
            long long q = 1;
            for (int u = 0; u < e; ++u) q *= p;
            got1 = mmul_s(got1, (u64)(q % P1));
            got2 = m2mul_s(got2, (u64)(q % P2));
        }
        u64 w1 = (u64)(want % P1), w2 = (u64)(want % P2);
        chk("lcm-mod-p1", got1 == w1);
        chk("lcm-mod-p2", got2 == w2);
    }
    printf("mod-mersenne selftest: %s (%d failures)\n", bad ? "FAIL" : "PASS", bad);
    return bad;
}

// ==================================================================== main
int main(int argc, char** argv) {
    if (argc >= 2 && std::string(argv[1]) == "--selftest") { invc_init(); return selftest(); }
    if (argc < 2) { fprintf(stderr, "usage: %s <n> [x] [out.json] | --selftest\n", argv[0]); return 2; }
    int n = atoi(argv[1]);
    bool xcheck = false;
    int ai = 2;
    if (argc > 2 && std::string(argv[2]) == "x") { xcheck = true; ai = 3; }
    const char* outpath = (argc > ai) ? argv[ai] : nullptr;
    invc_init();

    Ctx ctx; build_ctx(ctx, n);
    fprintf(stderr, "[n=%d] V=%d F=%zu build %.2fs\n", n, ctx.V, ctx.quads.size(), ctx.build_s);
    fflush(stderr);
    const int NP = xcheck ? 2 : 1;

    double t_all = now_s();
    std::vector<std::vector<u64>> levels, lms;
    std::vector<size_t> level_sizes;
    size_t total_states = 0;
    enumerate_levels(ctx, levels, lms, level_sizes, total_states);
    int K = (int)levels.size() - 1;
    if ((int)level_sizes.size() != K + 1 || (int)lms.size() != K + 1) {
        fprintf(stderr, "SNAPSHOT MISMATCH: levels=%zu lms=%zu level_sizes=%zu K=%d\n",
                levels.size(), lms.size(), level_sizes.size(), K);
        exit(8);
    }
    double enum_s = now_s() - t_all;
    fprintf(stderr, "[n=%d] safe subsets=%zu K=%d enum %.2fs rss=%.2fGB\n", n, total_states, K,
            enum_s, rss_peak_gb());
    {
        std::string ls = "[";
        char b[32];
        for (int k = 0; k <= K; ++k) { snprintf(b, sizeof b, "%s%zu", k ? "," : "", level_sizes[k]); ls += b; }
        ls += "]";
        fprintf(stderr, "    level_sizes = %s\n", ls.c_str());
    }
    fflush(stderr);

    std::vector<LevelStat> st(K + 1);
    size_t edge_total = 0;
    long long n_P = (long long)levels[K].size(), n_N = 0;
    long long over23 = 0, over34 = 0, gt_half = 0, over13 = 0;
    long long over23_e = 0, over34_e = 0, gt_half_e = 0, over13_e = 0;
    st[K].size = levels[K].size();
    st[K].nP = (long long)levels[K].size();

    double Dlog2 = 0.0;
    u64 Dmod[2] = {1, 1};

    std::vector<u64> num_next(levels[K].size(), 0u);
    std::vector<u64> num_next2(xcheck ? levels[K].size() : 0, 0u);
    std::vector<int8_t> g_next(levels[K].size(), 0);
    std::vector<u32> p_next(levels[K].size(), 0u);

    double gmax_val = -1.0, gmax_runner = -1.0;
    u64 gmax_num[2] = {0, 0};
    long long gmax_count = 0; int gmax_level = -1;
    double empty_val = 0.0; int empty_g = 0; u64 empty_num[2] = {0, 0};

    double t_solve = now_s();
    for (int k = K - 1; k >= 0; --k) {
        double t_k = now_s();
        // ---------------------------------------------------------------
        // WHICH LEVEL MUST SURVIVE, AND WHY
        //
        // Level j is read by iteration j (as the parent A) and by iteration
        // j-1 (as the child N).  The loop runs DESCENDING, so j-1 runs AFTER
        // j: the LAST consumer of level j is iteration j-1.
        //
        // The draft released levels[k] at the end of body k.  But iteration k-1
        // is what still needs levels[k] -- as its N.  So the draft destroyed
        // the very level the next iteration reads, and the guard fired one
        // iteration later with "levels[k+1] = 0".  That is the whole bug, and
        // swap_repro.cpp reproduces it exactly (GUARD TRIP at k=5, levels[6]=0).
        //
        // The correct release at the end of body k is levels[k+1]: its last
        // consumer is iteration k, which has just finished.  The rolling
        // window is then exactly {levels[k], levels[k+1]}.
        //
        // A (levels[k]) is taken by REFERENCE and must stay in the array for
        // the next iteration; N (levels[k+1]) is MOVED out, which empties the
        // slot and *is* the release.  No empty-vector swap is needed at all,
        // and no level is ever stored twice.
        // ---------------------------------------------------------------
        if (levels[k].size() != level_sizes[k] || levels[k + 1].size() != level_sizes[k + 1]) {
            fprintf(stderr,
                    "LEVEL %d UNAVAILABLE: got levels[k]=%zu (want %zu) "
                    "levels[k+1]=%zu (want %zu)\n",
                    k, levels[k].size(), level_sizes[k],
                    levels[k + 1].size(), level_sizes[k + 1]);
            fflush(stderr);
            exit(6);
        }
        const std::vector<u64>& A = levels[k];
        const std::vector<u64>& LM = lms[k];
        std::vector<u64> N = std::move(levels[k + 1]);   // <- the release
        std::vector<u64>().swap(lms[k + 1]);
        size_t M = A.size();

        // The child buffers are resized to N.size() before the edge pass and
        // must be exactly that long: they are indexed by position in N.
        // resize() never shrinks below its current size in a way that clears
        // memory, and after the swap below each buffer is exactly M long, so
        // the resize here is the only place the length can change.
        num_next.resize(N.size());
        if (NP == 2) num_next2.resize(N.size());
        g_next.resize(N.size());
        p_next.resize(N.size());
        if (num_next.size() != N.size() || g_next.size() != N.size() ||
            p_next.size() != N.size()) {
            fprintf(stderr, "CHILD BUFFER RESIZE FAILED at k=%d\n", k); exit(9);
        }

        std::vector<uint8_t> cnt(M, 0);
        std::vector<int8_t> gk(M, 0);
#pragma omp parallel for schedule(static)
        for (long long i = 0; i < (long long)M; ++i)
            cnt[(size_t)i] = (uint8_t)__builtin_popcountll(LM[(size_t)i]);

        // ---- L_k = lcm of the counts present, as a product of prime powers --
        // lvl(i) is the total order of level i; used only to bound buffer sizes.
        u64 Lk1 = 1, Lk2 = 1;
        double Llog2 = 0.0;
        {
            bool present[65] = {false};
            for (size_t i = 0; i < M; ++i) if (cnt[i]) present[cnt[i]] = true;
            for (int p = 2; p <= 64; ++p) {
                int e = 0;
                for (int c = 1; c <= 64; ++c) {
                    if (!present[c]) continue;
                    int x = c, f = 0;
                    while (x % p == 0) { x /= p; ++f; }
                    if (f > e) e = f;
                }
                if (!e) continue;
                long long q = 1;
                for (int t = 0; t < e; ++t) q *= p;
                Lk1 = mmul_s(Lk1, (u64)(q % P1));
                Lk2 = m2mul_s(Lk2, (u64)(q % P2));
                Llog2 += (double)e * log2((double)p);
            }
        }
        // Dprev = D_{k+1} (before this level's L_k is folded in) is what the
        // numerator identity needs; Dmod becomes D_k.
        const u64 Dprev1 = Dmod[0];
        const u64 Dprev2 = Dmod[1];
        Dlog2 += Llog2;
        Dmod[0] = mmul_s(Dmod[0], Lk1);
        Dmod[1] = m2mul_s(Dmod[1], Lk2);

        const u64* NN = num_next.data();
        const u64* NN2 = num_next2.data();
        const int8_t* GN = g_next.data();
        const u32* PN = p_next.data();
        const u64* Np = N.data();
        const size_t Nsz = N.size();

        // ---- edge pass: child numerator sums, grundy bitset, filter sum ----
        // numk doubles as the grundy bit-set scratch; it is overwritten with
        // the numerators in pass 2.
        std::vector<u64> numk((size_t)NP * M, 0u);
        std::vector<u64> psum(M, 0u);
        // pk holds this level's fixed-point values; it becomes p_next after the
        // swap.  It must be a SEPARATE buffer from p_next: writing p_next[i]
        // in place while the next level is LARGER than this one would leave the
        // tail [M, N.size()) holding values from the previous iteration, and
        // the next edge pass would read them as children of the wrong level.
        std::vector<u32> pk(M, 0u);
        double t_edge = now_s();
#pragma omp parallel for schedule(static)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            size_t i = (size_t)ii;
            u64 lm = LM[(size_t)i];
            if (!lm) { numk[i] = 0; psum[i] = 0; continue; }
            u64 a = A[(size_t)i];
            u64 s1 = 0, s2 = 0, ps = 0;
            uint64_t ga = 0;
            while (lm) {
                int v = __builtin_ctzll(lm); lm &= lm - 1;
                u64 child = a | (u64(1) << v);
                size_t pos = (size_t)(std::lower_bound(Np, Np + Nsz, child) - Np);
                if (pos >= Nsz || Np[pos] != child) {
#pragma omp critical
                    { fprintf(stderr, "CHILD LOOKUP FAILURE k=%d i=%zu child=%#llx\n",
                             k, i, (unsigned long long)child); fflush(stderr); exit(4); }
                }
                s1 += NN[pos]; if (s1 >= P1) s1 -= P1;
                if (NP == 2) { s2 += NN2[pos]; if (s2 >= P2) s2 -= P2; }
                ps += PN[pos];
                ga |= (1ULL << GN[pos]);
            }
            numk[i] = s1;
            if (NP == 2) numk[M + i] = s2;
            psum[i] = ps;
            gk[i] = (int8_t)__builtin_ctzll((~ga) & (ga + 1));
        }
        double t_e = now_s() - t_edge;
        if (getenv("KCDBG") && k >= atoi(getenv("KCDBG"))) {
            fprintf(stderr, "   [dbg k=%d] M=%zu N=%zu cnt[0..3]=", k, M, Nsz);
            for (int t = 0; t < 4 && (size_t)t < M; ++t) fprintf(stderr, "%u ", (unsigned)cnt[t]);
            fprintf(stderr, " psum[0..3]=");
            for (int t = 0; t < 4 && (size_t)t < M; ++t) fprintf(stderr, "%llu ", (unsigned long long)psum[t]);
            fprintf(stderr, " p_next[0..3]=");
            for (int t = 0; t < 4 && (size_t)t < Nsz; ++t) fprintf(stderr, "%u ", PN[t]);
            fprintf(stderr, "\n");
        }
        // N is a moved-out local, so it dies here; A is a reference into
        // levels[k] and must NOT be freed (the next iteration needs it).
        std::vector<u64>().swap(N);

        LevelStat& s = st[k];
        s.size = M;
        for (size_t i = 0; i < M; ++i) s.edges += cnt[i];
        edge_total += s.edges;
        s.Dbits = Dlog2;
        s.Dmod[0] = Dmod[0];
        s.Dmod[1] = (NP == 2) ? Dmod[1] : 1;
        // The modular threshold tests are valid only while 4*D cannot wrap.
        s.thr_exact = (2.0 * Dlog2 < 61.0);
        if (!s.thr_exact)
            fprintf(stderr, "  ~~ k=%d D has %.1f bits: threshold tests here are "
                    "FILTERED (per-level max is still exact)\n", k, Dlog2);

        const u64 D3_1 = mmul_s(Dmod[0], 3);
        const u64 D2_1 = mmul_s(Dmod[0], 2);

        // ---- pass 2: numerators, thresholds, per-level max --------------
        long long nP = 0, nN = 0, o23 = 0, o34 = 0, gh = 0, o13 = 0;
        long long o23e = 0, o34e = 0, ghe = 0, o13e = 0;
        double lbest_val = 0.0, lrunner = 0.0;
        {
            // One-off sanity print: for a handful of states, show the inputs and
            // the arithmetic, so a wrong p_rand can be traced by hand.
            if (getenv("KCDBG") && M > 3) {
                for (size_t t = 0; t < 4; ++t) {
                    u64 c2 = cnt[t], ps = psum[t];
                    u64 pv = c2 ? (u64)SCALE - (u64)(ps / c2) : 0;
                    fprintf(stderr, "   [pre k=%d] i=%zu cnt=%llu psum=%llu -> pv=%llu (%.6f) g=%d\n",
                            k, t, (unsigned long long)c2, (unsigned long long)ps,
                            (unsigned long long)pv, (double)pv / SCALE, (int)gk[t]);
                }
            }
        }
#pragma omp parallel for schedule(static) reduction(+ : nP, nN, o23, o34, gh, o13, o23e, o34e, ghe, o13e) \
    reduction(max : lbest_val, lrunner)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            size_t i = (size_t)ii;
            uint32_t c = cnt[i];
            // Both the value and the numerator are needed for EVERY state, not
            // just P positions: a parent sums p (and the child numerators) over
            // ALL of its legal moves, and an N position is a legal move of some
            // parent.  Skipping g!=0 leaves those at 0 and poisons every parent
            // one level up -- which is why the filter read 1.0 everywhere.
            if (!c) {
                pk[i] = 0u;
                numk[i] = 0;
                if (NP == 2) numk[M + i] = 0;
            } else {
                // p = 1 - (sum of child p)/cnt.  The children are ALREADY in
                // fixed point (each is a fraction of SCALE), so psum is already
                // scaled and the mean needs NO further scaling: the divisor is
                // psum/c directly.  Multiplying by SCALE a second time is what
                // made every value come out as 1 (and underflowed u64).
                u64 mean = psum[i] / c;
                u64 pv = (u64)SCALE - (mean > SCALE ? (u64)SCALE : mean);
                pk[i] = (u32)pv;
                // num_k = ( cnt*D_{k+1} - sum_children ) * ( L_k / cnt )
                // Dprev is D_{k+1}: the denominator BEFORE this level's L_k was
                // folded in.  Using the already-updated Dmod[0] (which includes
                // L_k) made every p_rand come out as 1.
                u64 t1 = msub(mmul_s(Dprev1, c), numk[i]);
                numk[i] = mmul_s(mmul_s(t1, Lk1), g_invc1[c]);   // * (L_k/cnt)
                if (NP == 2) {
                    u64 t2 = m2sub(m2mul_s(Dprev2, c), numk[M + i]);
                    numk[M + i] = m2mul_s(m2mul_s(t2, Lk2), g_invc2[c]);
                }
            }
            // ---- statistics are P-only ----
            if (gk[i] != 0) { ++nN; continue; }
            ++nP;
            if (!c) continue;
            u64 n1 = numk[i];
            u64 qv = (u64)pk[i];
            if (qv * 2 > (u64)SCALE) ++gh;
            if (qv * 3 > (u64)SCALE * 2) ++o23;
            if (qv * 4 > (u64)SCALE * 3) ++o34;
            if (qv * 3 > (u64)SCALE) ++o13;
            // exact thresholds where the modular test is valid
            if (s.thr_exact) {
                if (mmul_s(n1, 2) > Dmod[0]) ++ghe;
                if (mmul_s(n1, 3) > D2_1) ++o23e;
                if (mmul_s(n1, 4) > D3_1) ++o34e;
                if (mmul_s(n1, 3) > Dmod[0]) ++o13e;
            }
            double fv = (double)qv / (double)SCALE;
            if (fv > lbest_val) { lrunner = lbest_val; lbest_val = fv; }
            else if (fv > lrunner) lrunner = fv;
        }
        // per-level max: EXACT, because one level shares one denominator
        u64 lbest = 0; bool have = false; long long lcount = 0;
        for (size_t i = 0; i < M; ++i) {
            if (gk[i] != 0 || cnt[i] == 0) continue;
            u64 n1 = numk[i];
            if (n1 == 0) continue;
            if (!have) { lbest = n1; have = true; lcount = 1; }
            else if (n1 > lbest) { lbest = n1; lcount = 1; }
            else if (n1 == lbest) ++lcount;
        }
        s.nP = nP; s.nN = nN;
        s.over23 = o23; s.over34 = o34; s.gt_half = gh; s.over13 = o13;
        s.over23_e = o23e; s.over34_e = o34e; s.gt_half_e = ghe; s.over13_e = o13e;
        n_P += nP; n_N += nN;
        over23 += o23; over34 += o34; gt_half += gh; over13 += o13;
        over23_e += o23e; over34_e += o34e; gt_half_e += ghe; over13_e += o13e;
        s.best = lbest; s.best_count = lcount;
        s.best_val = lbest_val; s.runner_up = lrunner;

        if (have) {
            // Cross-level max is FILTERED (see the header): residues carry no
            // cross-level ordering once D exceeds 61 bits.  `gmax_runner` keeps
            // the gap so the selection can be audited.
            if (lbest_val > gmax_val) {
                gmax_runner = gmax_val; gmax_val = lbest_val;
                gmax_num[0] = lbest; gmax_count = lcount; gmax_level = k;
            } else if (lbest_val == gmax_val) { gmax_count += lcount; }
            else if (lbest_val > gmax_runner) { gmax_runner = lbest_val; }
        }
        // roll level k+1 -> k
        num_next.swap(numk);
        if (NP == 2) num_next2.swap(numk);
        g_next.swap(gk);
        p_next.swap(pk);          // pk is exactly M long, so no resize needed
        psum.clear(); psum.shrink_to_fit();
        cnt.clear(); cnt.shrink_to_fit();
        // num_next / g_next / p_next must be EXACTLY as long as level k for the
        // next iteration, which indexes them by position in its N.  pk is
        // exactly M, so the swap is exact.  (num_next's tail is covered because
        // numk was constructed at exactly NP*M and N.size() == M here.)
        if (num_next.size() != M || g_next.size() != M || p_next.size() != M) {
            fprintf(stderr, "BUFFER LENGTH BUG at k=%d: num=%zu g=%zu p=%zu want %zu\n",
                    k, num_next.size(), g_next.size(), p_next.size(), M);
            exit(9);
        }
        // Nothing to release here: levels[k+1] was already moved out at the top
        // of this body (that IS the release) and levels[k] must survive for
        // iteration k-1.  The scratch A is a reference into levels[k], so it is
        // not freed here either.

        s.secs = now_s() - t_k;
        if (getenv("KCDBG") && k >= atoi(getenv("KCDBG")))
            fprintf(stderr, "   [post k=%d] pk[0..3]=%u %u %u %u  lbest_val=%.9f\n",
                    k, M > 0 ? pk[0] : 0, M > 1 ? pk[1] : 0, M > 2 ? pk[2] : 0,
                    M > 3 ? pk[3] : 0, lbest_val);
        fprintf(stderr, "    k=%2d M=%12zu E=%12zu P=%9lld N=%9lld Dbits=%6.1f "
                "best=%.12f x%lld edge=%.2fs tot=%.2fs rss=%.2fGB\n",
                k, M, s.edges, s.nP, s.nN, Dlog2, lbest_val, lcount, t_e, s.secs,
                rss_peak_gb());
        fflush(stderr);
    }
    double solve_s = now_s() - t_solve;
    empty_num[0] = num_next[0];
    empty_num[1] = (NP == 2) ? num_next2[0] : 0;
    empty_val = (double)p_next[0] / (double)SCALE;
    empty_g = (int)g_next[0];

    // ------------------------------------------------------------ report
    std::string o;
    char b[2048];
    double tot_s = now_s() - t_all;
    o += "{\n";
    o += "  \"n\": " + std::to_string(n) + ",\n";
    o += "  \"V\": " + std::to_string(ctx.V) + ",\n";
    o += "  \"F\": " + std::to_string(ctx.quads.size()) + ",\n";
    o += "  \"method\": \"mod-2^61-1 DP; per-state 12 B (20 B with the 2nd prime); "
         "2-level rolling; Lk carried as maximal prime powers; lower_bound child index\",\n";
    o += "  \"primes\": [\"2305843009213693951 = 2^61-1\"";
    if (NP == 2) o += ", \"4611686018427387887 = 2^62-89\"";
    o += "],\n";
    o += "  \"exactness\": {\n";
    o += "    \"exact\": [\"level_sizes\",\"edge_total\",\"grundy\",\"n_P\",\"n_N\","
         "\"per_level_max\",\"per_state_residue\","
         "\"thresholds_on_levels_with_D_bits_below_30.5\"],\n";
    o += "    \"filtered\": [\"P_max_across_levels\",\"P_gt_1_2\",\"P_gt_2_3\","
         "\"P_gt_3_4\",\"P_gt_1_3_on_deep_levels\"],\n";
    o += "    \"why\": \"D_0 = prod L_j has 2^112 bits at n=5, 2^212 at n=6, 2^372 at n=7, "
         "so one 61-bit prime cannot order residues across levels nor decide p>2/3; "
         "a u32 fixed-point filter (scale 2^30) is used instead. The DP is affine in the "
         "child values, so errors do not amplify: total bound 2^-31.\",\n";
    snprintf(b, sizeof b, "    \"filter_abs_error_bound\": %.3e,\n", FILTER_ABS_ERR);
    o += b;
    snprintf(b, sizeof b, "    \"P_max_filter_margin\": %.17g,\n", gmax_val - gmax_runner);
    o += b;
    o += "    \"D0_bits\": " + std::to_string((long long)Dlog2) + "\n  },\n";
    o += "  \"n_safe_subsets\": " + std::to_string(total_states) + ",\n";
    o += "  \"level_sizes\": [";
    for (int k = 0; k <= K; ++k) { snprintf(b, sizeof b, "%s%zu", k ? "," : "", level_sizes[k]); o += b; }
    o += "],\n";
    o += "  \"max_safe_size\": " + std::to_string(K) + ",\n";
    o += "  \"edge_total\": " + std::to_string(edge_total) + ",\n";
    o += "  \"n_P\": " + std::to_string(n_P) + ",\n";
    o += "  \"n_N\": " + std::to_string(n_N) + ",\n";
    o += "  \"P_max_num_mod_p1\": \"" + mstr(gmax_num[0]) + "\",\n";
    o += "  \"P_max_D_mod_p1\": \"" + mstr(gmax_level >= 0 ? st[gmax_level].Dmod[0] : 0) + "\",\n";
    o += "  \"P_max_level\": " + std::to_string(gmax_level) + ",\n";
    o += "  \"P_max_n_attaining\": " + std::to_string(gmax_count) + ",\n";
    o += "  \"P_max_filter_value\": \"" + std::to_string(gmax_val) + "\",\n";
    o += "  \"P_max_filter_runner_up\": \"" + std::to_string(gmax_runner) + "\",\n";
    o += "  \"P_max_D_bits\": " + std::to_string((long long)Dlog2) + ",\n";
    o += "  \"P_gt_1_2\": " + std::to_string(gt_half) + ",\n";
    o += "  \"P_gt_2_3\": " + std::to_string(over23) + ",\n";
    o += "  \"P_gt_3_4\": " + std::to_string(over34) + ",\n";
    o += "  \"P_gt_1_3\": " + std::to_string(over13) + ",\n";
    o += "  \"P_gt_1_2_exact_levels\": " + std::to_string(gt_half_e) + ",\n";
    o += "  \"P_gt_2_3_exact_levels\": " + std::to_string(over23_e) + ",\n";
    o += "  \"P_gt_3_4_exact_levels\": " + std::to_string(over34_e) + ",\n";
    o += "  \"P_gt_1_3_exact_levels\": " + std::to_string(over13_e) + ",\n";
    o += "  \"empty\": {\"g\": " + std::to_string(empty_g) +
         ", \"p_rand_num_mod_p1\": \"" + mstr(empty_num[0]) +
         "\", \"p_rand_D_mod_p1\": \"" + mstr(st[0].Dmod[0]) +
         "\", \"p_rand_filter\": \"" + std::to_string(empty_val) + "\"},\n";
    o += "  \"thresholds_exact_all_levels\": ";
    { bool ok = true; for (int k = 0; k <= K; ++k) if (!st[k].thr_exact) ok = false;
      o += (ok ? "true" : "false"); }
    o += ",\n  \"levels\": [\n";
    for (int k = 0; k <= K; ++k) {
        char frac[160] = "0";
        if (st[k].Dbits < 61.0) {
            u64 iv = mpow(st[k].Dmod[0], P1 - 2);
            snprintf(frac, sizeof frac, "%llu/%llu",
                     (unsigned long long)mmul(st[k].best, iv),
                     (unsigned long long)st[k].Dmod[0]);
        }
        snprintf(b, sizeof b,
                 "    {\"k\": %d, \"size\": %zu, \"edges\": %zu, \"n_P\": %lld, \"n_N\": %lld, "
                 "\"D_bits\": %.2f, \"thresholds_exact\": %s, "
                 "\"best_num_mod_p1\": \"%s\", \"best_D_mod_p1\": \"%s\", "
                 "\"best_frac_exact\": \"%s\", \"best_count\": %lld, "
                 "\"best_filter\": %.17g, \"runner_up_filter\": %.17g, \"secs\": %.2f}",
                 k, st[k].size, st[k].edges, st[k].nP, st[k].nN, st[k].Dbits,
                 st[k].thr_exact ? "true" : "false",
                 mstr(st[k].best).c_str(), mstr(st[k].Dmod[0]).c_str(), frac,
                 st[k].best_count, st[k].best_val, st[k].runner_up, st[k].secs);
        o += b;
        if (k < K) o += ",";
        o += "\n";
    }
    o += "  ],\n";
    snprintf(b, sizeof b, "  \"timing_s\": {\"build\": %.2f, \"enumerate\": %.2f, "
             "\"solve\": %.2f, \"total\": %.2f},\n", ctx.build_s, enum_s, solve_s, tot_s);
    o += b;
    snprintf(b, sizeof b, "  \"peak_rss_gb\": %.2f\n", rss_peak_gb());
    o += b;
    o += "}\n";
    printf("%s", o.c_str());
    fflush(stdout);
    if (outpath) {
        FILE* f = fopen(outpath, "w");
        if (f) { fputs(o.c_str(), f); fclose(f); fprintf(stderr, "wrote %s\n", outpath); }
    }
    return 0;
}
