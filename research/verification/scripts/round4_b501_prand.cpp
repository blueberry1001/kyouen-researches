// Round4 B501/B502: exact random-play win rate p_rand, level-by-level, C++.
//
// Port of round3_b502_pgrand_n6.py (pure Python) to C++ so the n=7 board
// (49 points) can be solved.  n=6 took 129 s in Python; n=7 has ~10x more
// safe subsets, out of reach for pure Python but feasible here.
//
// Definition (unchanged, matches round2/round3):
//     p_rand(terminal) = 0
//     p_rand(S)        = 1 - (1/|L(S)|) * sum_{u in L(S)} p_rand(S | {u})
// with L(S) = legal moves = empty points that keep S safe, uniform over L(S).
//
// Arithmetic: exact rationals num/D_k with a per-level common denominator D_k,
// carried in a SELF-CONTAINED big integer (base 10^9 limbs, little-endian).
// boost is NOT installed in this WSL and there is no sudo, so cpp_int could not
// be used.  Only +, -, *, /, % and gcd are needed.  NO floating point in the DP.
//
// Because cnt(i) = |L(S)| always divides the level lcm Lk, the update
//     num_k(i) = ( cnt(i)*D_{k+1} - sum_children ) * ( Lk / cnt(i) )
// needs no big/big division: Lk/cnt(i) is a small integer precomputed once
// per distinct cnt value.
//
// Enumeration: BFS by level; each level a sorted vector of uint64 masks
// (n=7 -> V=49 fits in uint64).
//   blocked(occ) = OR over forbidden quads q with popcount(occ&q)==3 of (q&~occ)
//   legal(occ)   = ~occ & ~blocked
// Children of level k are occ|(1<<v) for legal v, binary-searched into the
// sorted level k+1.  The legal mask is NOT monotone along an edge (adding u
// can newly block w), so the O(F) quad pass is recomputed per state.
//
// Memory: only two adjacent levels of numerators are held at a time.
//
// Usage (WSL):
//   g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/prand round4_b501_prand.cpp
//   /tmp/prand 6
//   /tmp/prand 7 /tmp/n7.json
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>
#ifdef _OPENMP
#include <omp.h>
#endif
#include "kc_core.h"

using kc::u64;

static double now_s() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

// ============================================================ big integer
// Non-negative big integers in base 10^9, stored little-endian.  Callers pass
// explicit widths everywhere so no allocation happens in the DP hot loop.
static const uint64_t BASE = 1000000000ULL;
// 20 limbs = 180 decimal digits. The widest denominator seen at n=7 was 112
// digits (13 limbs); the numerator of p_rand is bounded by D_k * (1-0) < D_k,
// so 20 limbs covers n=8 with headroom. Reducing this from 48 shrinks the
// per-state numerator by 2.4x, which is what makes n=8 fit in memory.
#ifndef MAXL_OVERRIDE
static const int MAXL = 20;
#else
static const int MAXL = MAXL_OVERRIDE;
#endif

static inline int bn_is_zero(const uint32_t* a, int w) {
    for (int i = 0; i < w; ++i) if (a[i]) return 0;
    return 1;
}

static inline int bn_trim(const uint32_t* a, int w) {
    while (w > 1 && a[w - 1] == 0) --w;
    return w;
}

static inline void bn_set_u64(uint32_t* a, int w, uint64_t v) {
    for (int i = 0; i < w; ++i) { a[i] = (uint32_t)(v % BASE); v /= BASE; }
    if (v) { fprintf(stderr, "BIGINT OVERFLOW set\n"); exit(3); }
}

static inline int bn_cmp(const uint32_t* a, int wa, const uint32_t* b, int wb) {
    int n = wa > wb ? wa : wb;
    for (int i = n - 1; i >= 0; --i) {
        uint32_t x = i < wa ? a[i] : 0, y = i < wb ? b[i] : 0;
        if (x != y) return x < y ? -1 : 1;
    }
    return 0;
}

// a += b ; a must have room for the carry (caller passes a width >= max+1)
static inline void bn_add(uint32_t* a, int wa, const uint32_t* b, int wb) {
    uint64_t carry = 0;
    int n = wa > wb ? wa : wb;
    for (int i = 0; i < n; ++i) {
        uint64_t s = carry + (i < wa ? a[i] : 0) + (i < wb ? b[i] : 0);
        a[i] = (uint32_t)(s % BASE);
        carry = s / BASE;
    }
    for (int i = n; i < wa; ++i) {
        uint64_t s = (uint64_t)a[i] + carry;
        a[i] = (uint32_t)(s % BASE);
        carry = s / BASE;
    }
}

// a -= b, requires a >= b
static inline void bn_sub(uint32_t* a, int wa, const uint32_t* b, int wb) {
    int64_t borrow = 0;
    for (int i = 0; i < wa; ++i) {
        int64_t s = (int64_t)a[i] - borrow - (i < wb ? (int64_t)b[i] : 0);
        if (s < 0) { s += (int64_t)BASE; borrow = 1; } else borrow = 0;
        a[i] = (uint32_t)s;
    }
    if (borrow) { fprintf(stderr, "BIGINT UNDERFLOW\n"); exit(3); }
}

// out(wo) = a(wa) * b(wb) ; requires wo >= wa + wb
static inline void bn_mul(const uint32_t* a, int wa, const uint32_t* b, int wb,
                          uint32_t* out, int wo) {
    for (int i = 0; i < wo; ++i) out[i] = 0;
    for (int i = 0; i < wa; ++i) {
        if (!a[i]) continue;
        uint64_t carry = 0, ai = a[i];
        for (int j = 0; j < wb; ++j) {
            uint64_t cur = out[i + j] + ai * b[j] + carry;
            out[i + j] = (uint32_t)(cur % BASE);
            carry = cur / BASE;
        }
        int p = i + wb;
        while (carry) {
            uint64_t cur = (uint64_t)out[p] + carry;
            out[p] = (uint32_t)(cur % BASE);
            carry = cur / BASE;
            ++p;
        }
    }
}

// out(wo) = a(wa) * v ; requires wo >= wa+1
static inline void bn_mul_small(const uint32_t* a, int wa, uint64_t v,
                                uint32_t* out, int wo) {
    for (int i = 0; i < wo; ++i) out[i] = 0;
    uint64_t carry = 0;
    for (int i = 0; i < wa; ++i) {
        uint64_t cur = (uint64_t)a[i] * v + carry;
        out[i] = (uint32_t)(cur % BASE);
        carry = cur / BASE;
    }
    int p = wa;
    while (carry) {
        uint64_t cur = (uint64_t)out[p] + carry;
        out[p] = (uint32_t)(cur % BASE);
        carry = cur / BASE;
        ++p;
    }
}

// out(wo) = a(wa) * b(wb) * v  (single pass, used for Lk update)
static inline void bn_mul_small_into(const uint32_t* a, int wa, const uint32_t* b,
                                     int wb, uint64_t v, uint32_t* out, int wo) {
    for (int i = 0; i < wo; ++i) out[i] = 0;
    uint64_t carry = 0;
    for (int j = 0; j < wb; ++j) {
        uint64_t bj = (uint64_t)b[j] * v;
        uint64_t bl = bj % BASE, bh = bj / BASE;
        for (int i = 0; i < wa; ++i) {
            uint64_t cur = out[i + j] + (uint64_t)a[i] * bl + carry;
            out[i + j] = (uint32_t)(cur % BASE);
            carry = cur / BASE;
        }
        out[j + wa] = (uint32_t)(carry + bh);
        carry = 0;
    }
}

// a(wa) = q*bz + r ; q needs wa limbs, r needs wbz+1 limbs.  Exact.
static void bn_divmod(const uint32_t* a, int wa, const uint32_t* b, int wbz,
                      uint32_t* q, uint32_t* r) {
    for (int i = 0; i < wbz; ++i) r[i] = 0;
    if (q) for (int i = 0; i < wa; ++i) q[i] = 0;
    uint32_t prod[2 * MAXL + 2];
    for (int i = wa - 1; i >= 0; --i) {
        for (int j = wbz; j >= 1; --j) r[j] = r[j - 1];
        r[0] = a[i];
        if (bn_cmp(r, wbz + 1, b, wbz) < 0) { if (q) q[i] = 0; continue; }
        uint64_t num = (uint64_t)r[wbz] * BASE + r[wbz - 1];
        uint64_t den = b[wbz - 1];
        uint64_t est = den ? num / den : 0;
        if (est > BASE - 1) est = BASE - 1;
        // shrink until est*b <= r
        while (true) {
            bn_mul_small(b, wbz, est, prod, wbz + 1);
            if (bn_cmp(prod, wbz + 1, r, wbz + 1) <= 0) break;
            --est;
        }
        {   // keep the product of the final est
            uint32_t best[2 * MAXL + 2];
            bn_mul_small(b, wbz, est, best, wbz + 1);
            // grow while (est+1)*b <= r
            while (est < BASE - 1) {
                uint32_t nx[2 * MAXL + 2];
                bn_mul_small(b, wbz, est + 1, nx, wbz + 1);
                if (bn_cmp(nx, wbz + 1, r, wbz + 1) > 0) break;
                ++est;
                for (int t = 0; t < wbz + 1; ++t) best[t] = nx[t];
            }
            if (q) q[i] = (uint32_t)est;
            bn_sub(r, wbz + 1, best, wbz + 1);
        }
    }
}

// Safe wrapper: zeroes the whole quotient buffer first, so callers may read all
// wq limbs.  (bn_divmod itself only initialises `wa` limbs of q.)
static void bn_div(const uint32_t* a, int wa, const uint32_t* b, int wb,
                   uint32_t* q, int wq, uint32_t* r, int wr) {
    for (int i = 0; i < wq; ++i) q[i] = 0;
    for (int i = 0; i < wr; ++i) r[i] = 0;
    bn_divmod(a, wa, b, wb, q, r);
}

// g(wo) = gcd(a, b) ; a must be >= 1 or b >= 1
static void bn_gcd(const uint32_t* a, int wa, const uint32_t* b, int wb,
                   uint32_t* out, int wo) {
    uint32_t x[MAXL], y[MAXL], q[MAXL], r[MAXL + 1];
    int wx = bn_trim(a, wa), wy = bn_trim(b, wb);
    for (int i = 0; i < wx; ++i) x[i] = a[i];
    for (int i = 0; i < wy; ++i) y[i] = b[i];
    while (wy > 0 && !bn_is_zero(y, wy)) {
        bn_div(x, wx, y, wy, q, MAXL, r, MAXL + 1);
        for (int i = 0; i < wx; ++i) x[i] = y[i];
        wx = wy;
        wy = bn_trim(r, wy);
        for (int i = 0; i < wy; ++i) y[i] = r[i];
        if (bn_is_zero(x, wx)) break;
    }
    for (int i = 0; i < wo; ++i) out[i] = i < wx ? x[i] : 0;
}

// g(wo) = gcd(a, b) for a small b (b < 2^32)
static void bn_gcd_small2(const uint32_t* a, int wa, uint32_t b, uint32_t* out,
                          int wo) {
    uint32_t bb[MAXL];
    int wb = 0;
    if (b == 0) {
        for (int i = 0; i < wo; ++i) out[i] = i < wa ? a[i] : 0;
        return;
    }
    while (b) { bb[wb++] = b % BASE; b /= BASE; }
    bn_gcd(a, wa, bb, wb, out, wo);
}

static std::string bn_to_string(const uint32_t* a, int w) {
    w = bn_trim(a, w);
    if (w == 0 || bn_is_zero(a, w)) return "0";
    char buf[16];
    snprintf(buf, sizeof buf, "%u", a[w - 1]);
    std::string s(buf);
    for (int i = w - 2; i >= 0; --i) {
        snprintf(buf, sizeof buf, "%09u", a[i]);
        s += buf;
    }
    return s;
}

static std::string frac_str(const uint32_t* num, int wn, const uint32_t* den, int wd) {
    wn = bn_trim(num, wn); wd = bn_trim(den, wd);
    if (wn == 0 || bn_is_zero(num, wn)) return "0";
    if (wd == 1 && den[0] == 1) return bn_to_string(num, wn);
    uint32_t g[MAXL];
    bn_gcd(num, wn, den, wd, g, MAXL);
    if (bn_is_zero(g, MAXL)) return "0";
    int gw = bn_trim(g, MAXL);
    uint32_t a[MAXL + 1], b[MAXL + 1], r[MAXL + 1];
    bn_div(num, wn, g, gw, a, MAXL + 1, r, MAXL + 1);
    bn_div(den, wd, g, gw, b, MAXL + 1, r, MAXL + 1);
    return bn_to_string(a, MAXL + 1) + "/" + bn_to_string(b, MAXL + 1);
}

// truncated exact decimal expansion of num/den to `digits` places
static std::string dec_str(const uint32_t* num, int wn, const uint32_t* den,
                           int wd, int digits = 20) {
    wn = bn_trim(num, wn); wd = bn_trim(den, wd);
    if (wn == 0 || bn_is_zero(num, wn)) return "0." + std::string(digits, '0');
    uint32_t scale[2 * MAXL + 2], prod[4 * MAXL + 4];
    bn_set_u64(scale, 2 * MAXL, 1);
    for (int i = 0; i < digits; ++i) {
        bn_mul_small(scale, bn_trim(scale, 2 * MAXL), 10, prod, 2 * MAXL);
        for (int t = 0; t < 2 * MAXL; ++t) scale[t] = prod[t];
    }
    int sw = bn_trim(scale, 2 * MAXL);
    // (num * 10^digits) / den  -> the integer part of the exact expansion
    int n2w = wn + sw;
    std::vector<uint32_t> num2(n2w, 0), quot(n2w, 0), r(2 * MAXL + 2, 0);
    bn_mul(num, wn, scale, sw, num2.data(), n2w);
    bn_div(num2.data(), n2w, den, wd, quot.data(), n2w, r.data(), 2 * MAXL + 2);
    std::string s = bn_to_string(quot.data(), n2w);
    if ((int)s.size() <= digits) s = std::string(digits + 1 - s.size(), '0') + s;
    return s.substr(0, s.size() - digits) + "." + s.substr(s.size() - digits);
}

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
    ctx.n = n; ctx.V = ctx.board.V;
    ctx.FULL = ctx.board.full;
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

static void legal_level(const Ctx& ctx, const std::vector<u64>& A,
                        std::vector<u64>& out) {
    size_t M = A.size();
    out.resize(M);
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)M; ++i)
        out[(size_t)i] = legal_one(ctx, A[(size_t)i]);
}

// ============================================================== enumeration
static void enumerate_levels(const Ctx& ctx, std::vector<std::vector<u64>>& levels,
                             std::vector<std::vector<u64>>& lms, size_t& total) {
    levels.clear(); lms.clear();
    levels.push_back({0});
    lms.push_back({ctx.FULL});
    total = 1;
    for (int step = 0; step <= ctx.V; ++step) {
        const std::vector<u64>& A = levels.back();
        const std::vector<u64>& LM = lms.back();
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
        total += nxt.size();
        std::vector<u64> nlm;
        legal_level(ctx, nxt, nlm);
        levels.push_back(std::move(nxt));
        lms.push_back(std::move(nlm));
    }
}

// =============================================================== statistics
struct LevelStat {
    size_t size = 0, edges = 0;
    long long nP = 0, nN = 0, over23 = 0, over34 = 0, gt_half = 0;
    int Ddigits = 1;
    std::string Pmax = "0";
    long long best_count = 0;
    double secs = 0;
};

// ========================================================= bigint self-test
// Validates the big-integer primitives against __int128, so a bug in
// add/sub/mul/divmod/gcd cannot silently corrupt the DP.  Expected values are
// rendered to decimal strings and compared with bn_to_string, so the test
// covers every limb and not just the low ones.
static std::string u128_str(unsigned __int128 v) {
    if (v == 0) return "0";
    std::string s;
    while (v) { s += char('0' + (int)(v % 10)); v /= 10; }
    std::reverse(s.begin(), s.end());
    return s;
}
static std::string str_of(unsigned __int128 v) {
    uint32_t buf[MAXL] = {0};
    for (int i = 0; i < MAXL && v; ++i) { buf[i] = (uint32_t)(v % BASE); v /= BASE; }
    return bn_to_string(buf, MAXL);
}
static void set_u128(unsigned __int128 v, uint32_t* buf, int w) {
    for (int i = 0; i < w; ++i) { buf[i] = (uint32_t)(v % BASE); v /= BASE; }
}

static int selftest() {
    int bad = 0;
    auto chk = [&](const char* w, const std::string& got, const std::string& want) {
        if (got != want) {
            printf("  FAIL %-14s got %s want %s\n", w, got.c_str(), want.c_str());
            ++bad;
        }
    };
    const unsigned __int128 a = 987654321123456789ULL;      // 2 limbs
    const unsigned __int128 b = 42000000555ULL;             // 2 limbs
    const unsigned __int128 c = 123456789ULL;               // 1 limb
    const unsigned __int128 d = 999999999ULL;               // 1 limb
    uint32_t A[MAXL], B[MAXL], C[MAXL], Dv[MAXL];
    set_u128(a, A, MAXL); set_u128(b, B, MAXL);
    set_u128(c, C, MAXL); set_u128(d, Dv, MAXL);
    int aw = bn_trim(A, MAXL), bw = bn_trim(B, MAXL);
    int cw = bn_trim(C, MAXL), dw = bn_trim(Dv, MAXL);
    chk("set", bn_to_string(A, MAXL), u128_str(a));

    { uint32_t r[2 * MAXL + 2]; bn_mul(A, aw, B, bw, r, aw + bw);
      chk("mul", bn_to_string(r, aw + bw), u128_str(a * b)); }
    { uint32_t r[2 * MAXL + 2]; bn_mul(A, aw, Dv, dw, r, aw + dw);
      chk("mul1", bn_to_string(r, aw + dw), u128_str(a * d)); }
    { uint32_t r[MAXL + 2]; for (int i = 0; i < MAXL + 2; ++i) r[i] = 0;
      bn_add(r, MAXL + 2, A, aw); chk("add", bn_to_string(r, MAXL + 2), u128_str(a)); }
    { uint32_t r[MAXL + 2]; for (int i = 0; i < MAXL + 2; ++i) r[i] = 0;
      bn_add(r, MAXL + 2, A, aw); bn_add(r, MAXL + 2, B, bw);
      chk("add2", bn_to_string(r, MAXL + 2), u128_str(a + b)); }
    { uint32_t r[MAXL + 2]; for (int i = 0; i < MAXL + 2; ++i) r[i] = 0;
      bn_add(r, MAXL + 2, B, bw); bn_add(r, MAXL + 2, B, bw);
      chk("addcarry", bn_to_string(r, MAXL + 2), u128_str(2 * b)); }
    { uint32_t r[MAXL + 2]; for (int i = 0; i < MAXL + 2; ++i) r[i] = 0;
      bn_add(r, MAXL + 2, A, aw); bn_sub(r, MAXL + 2, B, bw);
      chk("sub", bn_to_string(r, MAXL + 2), u128_str(a - b)); }

    // division cases: exact, and with remainder
    struct { unsigned __int128 x, y; } cases[] = {
        {a, b}, {a, d}, {a, c}, {a * b, a}, {a * b, a + 1}, {a, a},
        {a * b + 7, a + 3}, {(unsigned __int128)1234567890123456789ULL, c},
    };
    for (auto& t : cases) {
        uint32_t X[MAXL], Y[MAXL], Q[MAXL + 1], R[MAXL + 1];
        set_u128(t.x, X, MAXL); set_u128(t.y, Y, MAXL);
        int xw = bn_trim(X, MAXL), yw = bn_trim(Y, MAXL);
        bn_div(X, xw, Y, yw, Q, MAXL + 1, R, MAXL + 1);
        unsigned __int128 q = t.x / t.y, r = t.x % t.y;
        chk("divmod.q", bn_to_string(Q, MAXL + 1), u128_str(q));
        chk("divmod.r", bn_to_string(R, MAXL + 1), u128_str(r));
    }
    // mul_small
    { uint32_t r[2 * MAXL + 2]; bn_mul_small(A, aw, 7, r, aw + 1);
      chk("muls", bn_to_string(r, aw + 1), u128_str(a * 7)); }
    { uint32_t r[2 * MAXL + 2]; bn_mul_small(A, aw, 1000000000ULL, r, aw + 2);
      chk("mulsB", bn_to_string(r, aw + 2), u128_str(a * 1000000000ULL)); }
    // gcd
    { uint32_t g[MAXL]; bn_gcd(A, aw, B, bw, g, MAXL);
      unsigned __int128 x = a, y = b, t;
      while (y) { t = x % y; x = y; y = t; }
      chk("gcd", bn_to_string(g, MAXL), u128_str(x)); }
    { uint32_t g[MAXL]; bn_gcd_small2(A, aw, 6, g, MAXL);
      unsigned __int128 x = a, y = 6, t;
      while (y) { t = x % y; x = y; y = t; }
      chk("gcdsmall6", bn_to_string(g, MAXL), u128_str(x)); }
    { uint32_t g[MAXL]; bn_gcd(A, aw, A, aw, g, MAXL);
      chk("gcdsame", bn_to_string(g, MAXL), u128_str(a)); }
    { uint32_t g[MAXL]; bn_gcd(C, cw, Dv, dw, g, MAXL);
      unsigned __int128 x = c, y = d, t;
      while (y) { t = x % y; x = y; y = t; }
      chk("gcd1", bn_to_string(g, MAXL), u128_str(x)); }
    // dec_str: 5162/6615 is the known n=6 answer
    { uint32_t N[MAXL], Q[MAXL]; set_u128(5162, N, MAXL); set_u128(6615, Q, MAXL);
      chk("frac", frac_str(N, MAXL, Q, MAXL), "5162/6615");
      chk("dec", dec_str(N, MAXL, Q, MAXL, 20), "0.78034769463340891912"); }
    // scale
    { uint32_t s[MAXL]; bn_set_u64(s, MAXL, 1);
      for (int i = 0; i < 20; ++i) { uint32_t p[2 * MAXL + 2];
        bn_mul_small(s, bn_trim(s, MAXL), 10, p, 2 * MAXL);
        for (int t = 0; t < MAXL; ++t) s[t] = p[t]; }
      chk("scale", bn_to_string(s, MAXL), "100000000000000000000"); }
    printf("bigint selftest: %s (%d failures)\n", bad ? "FAIL" : "PASS", bad);
    return bad;
}

// ==================================================================== main
int main(int argc, char** argv) {
    if (argc >= 2 && std::string(argv[1]) == "--selftest") return selftest();
    if (argc < 2) { fprintf(stderr, "usage: %s <n> [out.json] | --selftest\n", argv[0]); return 2; }
    int n = atoi(argv[1]);
    const char* outpath = (argc > 2) ? argv[2] : nullptr;

    Ctx ctx; build_ctx(ctx, n);
    fprintf(stderr, "[n=%d] V=%d F=%zu build %.2fs\n", n, ctx.V, ctx.quads.size(),
            ctx.build_s);

    double t_all = now_s();
    std::vector<std::vector<u64>> levels, lms;
    size_t total_states = 0;
    enumerate_levels(ctx, levels, lms, total_states);
    double enum_s = now_s() - t_all;
    int K = (int)levels.size() - 1;
    fprintf(stderr, "[n=%d] safe subsets = %zu levels=%d enum %.2fs\n", n,
            total_states, K + 1, enum_s);
    {
        std::string ls = "[";
        char b[32];
        for (int k = 0; k <= K; ++k) {
            snprintf(b, sizeof b, "%s%zu", k ? "," : "", levels[k].size());
            ls += b;
        }
        ls += "]";
        fprintf(stderr, "    level_sizes = %s\n", ls.c_str());
    }
    fflush(stderr);

    std::vector<LevelStat> st(K + 1);
    size_t edge_total = 0;

    // top level: all states terminal
    st[K].size = levels[K].size();
    st[K].nP = (long long)levels[K].size();
    st[K].Ddigits = 1;
    long long n_P = st[K].nP, n_N = 0, over23 = 0, over34 = 0, gt_half = 0;

    uint32_t D[MAXL]; bn_set_u64(D, MAXL, 1);
    int W_D = 1;
    std::vector<uint32_t> num_next(levels[K].size(), 0u);
    int W_next = 1;
    std::vector<int8_t> g_next(levels[K].size(), 0);

    uint32_t gmax_n[MAXL], gmax_d[MAXL];
    bn_set_u64(gmax_n, MAXL, 0);
    bn_set_u64(gmax_d, MAXL, 1);
    int gw = 1;                       // trimmed width of gmax_d
    long long gmax_count = 0;
    int gmax_level = -1;
    u64 gmax_occ = 0;

    double t_solve = now_s();
    for (int k = K - 1; k >= 0; --k) {
        double t_k = now_s();
        const std::vector<u64>& A = levels[k];
        const std::vector<u64>& N = levels[k + 1];
        const std::vector<u64>& LM = lms[k];
        size_t M = A.size();

        int W_acc = W_next + 2;
        std::vector<uint32_t> acc((size_t)M * W_acc, 0u);
        std::vector<uint32_t> cnt(M, 0u);
        std::vector<uint64_t> gacc(M, 0u);

        // ---- one pass over edges: child-numerator sum + grundy bit set ----
        double t_edge = now_s();
#pragma omp parallel for schedule(static)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            size_t i = (size_t)ii;
            u64 lm = LM[i];
            if (!lm) continue;
            uint32_t* a = &acc[i * W_acc];
            uint64_t ga = 0;
            uint32_t c = 0;
            while (lm) {
                int v = __builtin_ctzll(lm);
                lm &= lm - 1;
                u64 child = A[i] | (u64(1) << v);
                size_t pos = (size_t)(std::lower_bound(N.begin(), N.end(), child)
                                      - N.begin());
                if (pos >= N.size() || N[pos] != child) {
#pragma omp critical
                    fprintf(stderr, "EDGE LOOKUP FAILURE k=%d\n", k);
                    exit(4);
                }
                bn_add(a, W_acc, &num_next[pos * W_next], W_next);
                ga |= (u64(1) << g_next[pos]);
                ++c;
            }
            cnt[i] = c;
            gacc[i] = ga;
        }
        double t_e = now_s() - t_edge;

        // grundy = mex = index of the lowest zero bit of the child bit-set
        std::vector<int8_t> gk(M);
#pragma omp parallel for schedule(static)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            u64 ga = gacc[(size_t)ii];
            u64 lz = (~ga) & (ga + 1);
            gk[(size_t)ii] = (int8_t)__builtin_ctzll(lz);
        }
        edge_total += (size_t)std::accumulate(cnt.begin(), cnt.end(), (uint64_t)0);
        gacc.clear(); gacc.shrink_to_fit();

        bool any = std::any_of(cnt.begin(), cnt.end(), [](uint32_t c) { return c != 0; });

        // ---- per-level lcm of the child counts --------------------------
        uint32_t Lk[MAXL];
        bn_set_u64(Lk, MAXL, 1);
        int Lw = 1;
        if (any) {
            for (size_t i = 0; i < M; ++i) {
                uint32_t c = cnt[i];
                if (c <= 1) continue;
                uint32_t g[MAXL], q[MAXL + 1], r[MAXL + 1], prod[2 * MAXL + 2];
                bn_gcd_small2(Lk, Lw, c, g, MAXL);
                int ggw = bn_trim(g, MAXL);
                bn_div(Lk, Lw, g, ggw, q, MAXL + 1, r, MAXL + 1);
                int qw = bn_trim(q, MAXL);
                // Lk = (Lk/g) * c
                bn_mul_small(q, qw, c, prod, qw + 1);
                Lw = bn_trim(prod, qw + 1);
                for (int t = 0; t < MAXL; ++t) Lk[t] = t < Lw ? prod[t] : 0;
            }
        }
        int Lk_digits = (int)bn_to_string(Lk, Lw).size();

        // ---- D_k = D_{k+1} * Lk ----------------------------------------
        uint32_t Dk[MAXL], prod[2 * MAXL + 2];
        if (any) {
            bn_mul(D, W_D, Lk, Lw, prod, W_D + Lw);
            int need = W_D + Lw;
            if (need > MAXL) { fprintf(stderr, "D OVERFLOW\n"); return 3; }
            for (int t = 0; t < MAXL; ++t) Dk[t] = t < need ? prod[t] : 0;
        } else {
            bn_set_u64(Dk, MAXL, 1);
        }
        int Dkw = bn_trim(Dk, MAXL);

        // ---- numerators -------------------------------------------------
        int Wk = any ? Dkw : 1;
        std::vector<uint32_t> numk((size_t)M * Wk, 0u);
        if (any) {
            // mtab[c] = Lk / c for each distinct child count present
            std::vector<std::vector<uint32_t>> mtab(ctx.V + 2);
            for (uint32_t c = 1; c <= (uint32_t)ctx.V; ++c) {
                bool present = false;
                for (size_t i = 0; i < M; ++i) if (cnt[i] == c) { present = true; break; }
                if (!present) continue;
                std::vector<uint32_t> m(MAXL, 0), r(MAXL + 1, 0);
                uint32_t cc[MAXL];
                bn_set_u64(cc, MAXL, c);
                bn_div(Lk, Lw, cc, 1, m.data(), MAXL, r.data(), MAXL + 1);
                mtab[c] = m;
            }
#pragma omp parallel for schedule(static)
            for (long long ii = 0; ii < (long long)M; ++ii) {
                size_t i = (size_t)ii;
                uint32_t c = cnt[i];
                if (!c) { numk[i * Wk] = 0; continue; }
                // t = c*D_{k+1} - acc
                uint32_t t1[2 * MAXL + 2];
                bn_mul_small(D, W_D, c, t1, W_D + 1);
                int t1w = bn_trim(t1, W_D + 1);
                if (t1w < W_acc) for (int t = t1w; t < W_acc; ++t) t1[t] = 0;
                bn_sub(t1, W_acc, &acc[i * W_acc], W_acc);
                const std::vector<uint32_t>& m = mtab[c];
                int mw = bn_trim(m.data(), MAXL);
                uint32_t p[2 * MAXL + 2];
                bn_mul(t1, W_acc, m.data(), mw, p, W_acc + mw);
                for (int t = 0; t < Wk; ++t)
                    numk[i * Wk + t] = t < W_acc + mw ? p[t] : 0;
            }
            // ---- gcd reduction of the level denominator -----------------
            // NOTE: a parallel block fold is tempting (gcd is associative) but
            // a block partial gcd must start from 1, not from Dk, or the merge
            // silently produces a wrong -- too small -- denominator.  Keep this
            // sequential and exact; it is cheap because the running gcd
            // collapses to 1 very early on most levels.
            uint32_t gg[MAXL];
            for (int t = 0; t < MAXL; ++t) gg[t] = Dk[t];
            int ggw = Dkw;
            for (size_t i = 0; i < M; ++i) {
                if (bn_is_zero(&numk[i * Wk], Wk)) continue;
                if (ggw == 1 && gg[0] == 1) break;
                int nw = bn_trim(&numk[i * Wk], Wk);
                uint32_t ng[MAXL];
                bn_gcd(gg, ggw, &numk[i * Wk], nw, ng, MAXL);
                ggw = bn_trim(ng, MAXL);
                for (int t = 0; t < MAXL; ++t) gg[t] = ng[t];
            }
            if (!(ggw == 1 && gg[0] == 1)) {
#pragma omp parallel for schedule(static)
                for (long long ii = 0; ii < (long long)M; ++ii) {
                    size_t i = (size_t)ii;
                    if (bn_is_zero(&numk[i * Wk], Wk)) continue;
                    uint32_t q[MAXL + 1], r[MAXL + 1];
                    int nw = bn_trim(&numk[i * Wk], Wk);
                    bn_div(&numk[i * Wk], nw, gg, ggw, q, MAXL + 1, r, MAXL + 1);
                    for (int t = 0; t < Wk; ++t)
                        numk[i * Wk + t] = t < MAXL + 1 ? q[t] : 0;
                }
                uint32_t q[MAXL + 1], r[MAXL + 1];
                bn_div(Dk, Dkw, gg, ggw, q, MAXL + 1, r, MAXL + 1);
                Dkw = bn_trim(q, MAXL + 1);
                for (int t = 0; t < MAXL; ++t) Dk[t] = t < Dkw ? q[t] : 0;
            }
        } else {
            bn_set_u64(Dk, MAXL, 1);
            Dkw = 1;
        }
        acc.clear(); acc.shrink_to_fit();

        // ---- statistics for this level ---------------------------------
        LevelStat& s = st[k];
        s.size = M;
        s.Ddigits = (int)bn_to_string(Dk, Dkw).size();
        for (size_t i = 0; i < M; ++i) s.edges += cnt[i];
        long long nP = 0, nN = 0, o23 = 0, o34 = 0, gh = 0;
        // NOTE: every counter must be a private reduction variable.  Writing
        // straight into s.nN from all OpenMP threads would lose updates.
#pragma omp parallel for schedule(static) reduction(+ : nP, nN, o23, o34, gh)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            size_t i = (size_t)ii;
            if (gk[i] != 0) { ++nN; continue; }
            ++nP;
            const uint32_t* x = &numk[i * Wk];
            int xw = bn_trim(x, Wk);
            uint32_t t[2 * MAXL + 2];
            bn_mul_small(x, xw, 2, t, xw + 1);
            if (bn_cmp(t, xw + 1, Dk, Dkw) > 0) ++gh;
            bn_mul_small(x, xw, 3, t, xw + 1);
            uint32_t d2[2 * MAXL + 2];
            bn_mul_small(Dk, Dkw, 2, d2, Dkw + 1);
            if (bn_cmp(t, xw + 1, d2, Dkw + 1) > 0) ++o23;
            bn_mul_small(x, xw, 4, t, xw + 1);
            uint32_t d3[2 * MAXL + 2];
            bn_mul_small(Dk, Dkw, 3, d3, Dkw + 1);
            if (bn_cmp(t, xw + 1, d3, Dkw + 1) > 0) ++o34;
        }
        s.nP = nP; s.nN = nN; s.over23 = o23; s.over34 = o34; s.gt_half = gh;
        n_P += nP; over23 += o23; over34 += o34; gt_half += gh; n_N += nN;

        // level max over P positions (same denominator -> compare numerators)
        uint32_t lbest[MAXL];
        bool have = false;
        s.best_count = 0;
        for (size_t i = 0; i < M; ++i) {
            if (gk[i] != 0) continue;
            const uint32_t* x = &numk[i * Wk];
            if (bn_is_zero(x, Wk)) continue;
            if (!have) { have = true; for (int t = 0; t < MAXL; ++t) lbest[t] = t < Wk ? x[t] : 0; s.best_count = 1; }
            else {
                int cmp = bn_cmp(x, bn_trim(x, Wk), lbest, MAXL);
                if (cmp > 0) { for (int t = 0; t < MAXL; ++t) lbest[t] = t < Wk ? x[t] : 0; s.best_count = 1; }
                else if (cmp == 0) ++s.best_count;
            }
        }
        s.Pmax = have ? frac_str(lbest, MAXL, Dk, Dkw) : "0";

        if (have) {
            uint32_t p1[2 * MAXL + 2], p2[2 * MAXL + 2];
            bn_mul(lbest, MAXL, gmax_d, gw, p1, 2 * MAXL);
            bn_mul(gmax_n, MAXL, Dk, Dkw, p2, 2 * MAXL);
            int cmp = bn_cmp(p1, 2 * MAXL, p2, 2 * MAXL);
            if (cmp > 0) {
                for (int t = 0; t < MAXL; ++t) gmax_n[t] = lbest[t];
                for (int t = 0; t < MAXL; ++t) gmax_d[t] = Dk[t];
                gw = Dkw;
                gmax_count = s.best_count;
                gmax_level = k;
            } else if (cmp == 0) {
                gmax_count += s.best_count;
            }
        }

        // roll level k+1 -> k
        for (int t = 0; t < MAXL; ++t) D[t] = Dk[t];
        W_D = Dkw;
        num_next.swap(numk);
        W_next = Wk;
        g_next.swap(gk);
        cnt.clear(); cnt.shrink_to_fit();

        s.secs = now_s() - t_k;
        fprintf(stderr,
                "    k=%2d M=%10zu edges=%10zu P=%9lld N=%9lld "
                "Lk_d=%2d D_d=%2d  edge %.2fs tot %.2fs\n",
                k, M, s.edges, s.nP, s.nN, Lk_digits, s.Ddigits, t_e, s.secs);
        fflush(stderr);
    }
    double solve_s = now_s() - t_solve;
    double total_s = now_s() - t_all;

    uint32_t x0[MAXL];
    for (int t = 0; t < MAXL; ++t) x0[t] = t < W_next ? num_next[t] : 0;
    std::string empty_frac = frac_str(x0, MAXL, D, MAXL);
    int empty_g = g_next.empty() ? -1 : (int)g_next[0];
    fprintf(stderr, "[n=%d] empty board: g=%d p_rand=%s\n", n, empty_g, empty_frac.c_str());

    // ---- report -------------------------------------------------------
    std::string o;
    char b[1024];
    o += "{\n";
    o += "  \"n\": " + std::to_string(ctx.n) + ",\n";
    o += "  \"V\": " + std::to_string(ctx.V) + ",\n";
    o += "  \"F\": " + std::to_string(ctx.quads.size()) + ",\n";
    o += "  \"n_safe_subsets\": " + std::to_string(total_states) + ",\n";
    o += "  \"level_sizes\": [";
    for (int k = 0; k <= K; ++k) {
        snprintf(b, sizeof b, "%s%zu", k ? "," : "", levels[k].size());
        o += b;
    }
    o += "],\n  \"max_safe_size\": " + std::to_string(K) + ",\n";
    o += "  \"edge_total\": " + std::to_string(edge_total) + ",\n";
    o += "  \"per_level_denominator_digits\": [";
    for (int k = 0; k <= K; ++k) {
        snprintf(b, sizeof b, "%s%d", k ? "," : "", st[k].Ddigits);
        o += b;
    }
    o += "],\n";
    o += "  \"n_P\": " + std::to_string(n_P) + ",\n";
    o += "  \"n_N\": " + std::to_string(n_N) + ",\n";
    o += "  \"P_max\": \"" + frac_str(gmax_n, MAXL, gmax_d, gw) + "\",\n";
    o += "  \"P_max_dec\": \"" + dec_str(gmax_n, MAXL, gmax_d, gw) + "\",\n";
    o += "  \"P_max_level\": " + std::to_string(gmax_level) + ",\n";
    o += "  \"P_max_n_attaining\": " + std::to_string(gmax_count) + ",\n";
    o += "  \"P_gt_1_2\": " + std::to_string(gt_half) + ",\n";
    o += "  \"P_gt_2_3\": " + std::to_string(over23) + ",\n";
    o += "  \"P_gt_3_4\": " + std::to_string(over34) + ",\n";
    snprintf(b, sizeof b, "  \"empty\": {\"g\": %d, \"p_rand\": \"%s\"},\n",
             empty_g, empty_frac.c_str());
    o += b;
    o += "  \"levels\": [\n";
    for (int k = 0; k <= K; ++k) {
        snprintf(b, sizeof b,
                 "    {\"k\": %d, \"size\": %zu, \"edges\": %zu, \"n_P\": %lld, "
                 "\"n_N\": %lld, \"D_digits\": %d, \"P_max\": \"%s\", "
                 "\"P_max_count\": %lld, \"secs\": %.2f}",
                 k, st[k].size, st[k].edges, st[k].nP, st[k].nN, st[k].Ddigits,
                 st[k].Pmax.c_str(), st[k].best_count, st[k].secs);
        o += b;
        if (k < K) o += ",";
        o += "\n";
    }
    o += "  ],\n";
    snprintf(b, sizeof b,
             "  \"timing_s\": {\"build\": %.2f, \"enumerate\": %.2f, "
             "\"solve\": %.2f, \"total\": %.2f}\n",
             ctx.build_s, enum_s, solve_s, total_s);
    o += b;
    o += "}\n";
    printf("%s", o.c_str());
    if (outpath) {
        FILE* f = fopen(outpath, "w");
        if (f) { fputs(o.c_str(), f); fclose(f); fprintf(stderr, "wrote %s\n", outpath); }
    }
    return 0;
}
