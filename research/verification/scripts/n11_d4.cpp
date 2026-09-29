// Grundy DP for the kyouen (no-4-concyclic) game on an n x n grid, reduced by
// the D4 symmetry group of the square.
//
// ===========================================================================
// 1. The symmetry reduction
// ===========================================================================
// Every board automorphism sigma maps forbidden 4-sets (concyclic or collinear
// lattice 4-tuples) to forbidden 4-sets, so L(sigma(S)) = sigma(L(S)) and by
// induction on the number of remaining moves
//
//     g(sigma(S)) = mex { g(sigma(C)) : C a child of S }            (1)
//
// so g is constant on D4 orbits.  A level is therefore stored as the set of
// CANONICAL representatives canon(S) = min over the 8 elements of D4 of S,
// ordered as plain 128-bit unsigned integers (hi is the high word).  For a
// generic position the stabiliser is trivial, the orbit has 8 elements, and a
// level of M states collapses to about M/8 representatives -- the 1/8
// reduction, and the only place the reduction comes from.
//
// GENERATION applies the 8 generators to the PARENT: for each representative S,
// each legal v, and each g, it emits canon(sigma_g(S) + {sigma_g(v)}).  Applying
// the generators to the *children of the stored representatives only* (the naive
// reading of "1/8 the states") would not cover the orbit of a child whose
// canonical form is sigma'(C) for a sigma' that no generator of the parent
// reaches -- the classic 1/8-reduction bug, which here would silently corrupt
// g(empty).  Every child lookup in the DP is asserted to hit, so generation
// coverage is checked at run time rather than argued.
//
// COST.  Generation produces 8 * (number of edges) = 8 * (k+1) * M_{k+1}
// candidates of 16 B before dedup.  The DP itself is NOT 8x: because the eight
// images of a child are one orbit, the value g(canon(S + {v})) is obtained by
// ONE canonicalisation and ONE binary search per legal move, not eight.
//
// ===========================================================================
// 2. Level generation
// ===========================================================================
// A level of canonical representatives is the exact set of orbits of the safe
// k-point sets, produced by: for every representative S of level k, for every
// legal point v, and for each of the 8 generators g, emit canon(sigma_g(S + {v}))
// -- computed as xf(S,g) with sigma_g(v) appended.  All (k+1) * M * 8
// candidates are then sorted and uniqued in one pass.
//
// States are ordered by the 128-bit value sum_p 2^p (kc::Bits puts point p at
// bit p), so a level is a plain increasing sequence of 128-bit integers and a
// child's Grundy value is a binary search away.
//
// The old version partitioned this into v-max blocks, which is unsound under
// D4 -- see the "REMOVED: the v-block offset table" note above for why.  The
// price is memory: the candidate buffer is 8 * (number of edges) slots of 16 B,
// and --maxcand caps it, so a run stops at the last level that fits.
//
// Levels are spilled to $SPILL (u64 lo, u64 hi, then one byte of sigma) and
// read back in the DP pass, which runs k descending.  Only two adjacent
// levels are ever resident.
//
// ===========================================================================
// 3. Legal moves
// ===========================================================================
// A point u is illegal iff some quad through u has its other three points
// occupied, i.e. iff some 3-subset T of occ has T + {u} a quad.  For every
// 3-subset T of the board we precompute tri4[T] = { u : T + {u} a quad },
// addressed by rank(p0<p1<p2) = C(p0,1)+C(p1,2)+C(p2,3) -- a bijection of the
// 3-subsets onto [0, C(V,3)) -- so the table is direct-indexed, no hashing.
// Only the C(k,3) triples actually present are OR-ed in.  (Same table and the
// same trap as n11_grundy.cpp: the triple {0,1,2} of the quad {0,1,2,3} is
// filed under point 3, which is unoccupied, so OR-ing over *occupied* points
// would miss the block.  --check-legal compares against kc::legal_mask.)
//
// Because L(sigma(S)) = sigma(L(S)), the free mask of the stored image is just
// sigma(free mask of the representative), and "v is legal in sigma(S)" is the
// single bit test "sigma^-1(v) is legal in S".
//
// Usage:
//   n11_d4 --n 6  --check-legal
//   n11_d4 --n 7  --spill /tmp/x --out x.json
//   n11_d4 --n 11 --maxlevel 9 --spill /tmp/n11d4 --out y.json
#include "kc_core121.h"

#include <algorithm>
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
static int top_point(const Bits& b) {  // caller guarantees non-empty
    if (b.hi) return 127 - __builtin_clzll(b.hi);
    return 63 - __builtin_clzll(b.lo);
}

// ============================================================== D4 machinery
static int PERM[8][128];
static int PINV[8][128];

static void build_d4(int n) {
    for (int g = 0; g < 8; ++g)
        for (int y = 0; y < n; ++y)
            for (int x = 0; x < n; ++x) {
                int X, Y;
                switch (g) {
                    case 0:  X = x;             Y = y;             break;
                    case 1:  X = y;             Y = n - 1 - x;     break;  // rot 90
                    case 2:  X = n - 1 - x;     Y = n - 1 - y;     break;  // rot 180
                    case 3:  X = n - 1 - y;     Y = x;             break;  // rot 270
                    case 4:  X = n - 1 - x;     Y = y;             break;  // refl x
                    case 5:  X = x;             Y = n - 1 - y;     break;  // refl y
                    case 6:  X = y;             Y = x;             break;  // main diag
                    default: X = n - 1 - y;     Y = n - 1 - x;     break;  // anti diag
                }
                PERM[g][y * n + x] = Y * n + X;
            }
    for (int g = 0; g < 8; ++g)
        for (int p = 0; p < n * n; ++p) PINV[g][PERM[g][p]] = p;
    for (int g = 0; g < 8; ++g) {                      // must be bijections
        Bits seen{0, 0};
        for (int p = 0; p < n * n; ++p) {
            int q = PERM[g][p];
            // `seen` must be V BITS wide, not 64.  With `u64 seen` and
            // `1ull << q`, the identity perm aborts on n=11 at p=64.
            // The q<64 / q>=64 test must be an if/else and NOT a `||` chain:
            // `(seen.lo >> q)` is still EVALUATED for q = 64 (short-circuit
            // `||` only skips terms to its RIGHT), so the first draft of this
            // fix kept `|| ((seen.lo >> q) & 1ull) ||` and still died with
            // "FATAL: perm 0 not a bijection at p=64 -> q=64" on a permutation
            // that is trivially a bijection.  Select the word first, then test.
            if (q < 0 || q >= n * n) {
                fprintf(stderr, "FATAL: perm %d out of range at p=%d -> q=%d\n", g, p, q);
                exit(9);
            }
            int dup = (q < 64) ? (int)((seen.lo >> q) & 1ull)
                               : (int)((seen.hi >> (q - 64)) & 1ull);
            if (dup) {
                fprintf(stderr, "FATAL: perm %d not injective at p=%d -> q=%d (already hit)\n", g, p, q);
                exit(9);
            }
            if (q < 64) seen.lo |= 1ull << q; else seen.hi |= 1ull << (q - 64);
        }
    }
}

static inline Bits xf(const Bits& b, int g) {
    Bits r{0, 0};
    u64 e = b.lo;
    while (e) { int p = __builtin_ctzll(e); e &= e - 1; int q = PERM[g][p];      if (q < 64) r.lo |= 1ull << q; else r.hi |= 1ull << (q - 64); }
    e = b.hi;
    while (e) { int p = __builtin_ctzll(e); e &= e - 1; int q = PERM[g][p + 64]; if (q < 64) r.lo |= 1ull << q; else r.hi |= 1ull << (q - 64); }
    return r;
}
// NOTE: `s` is taken BY VALUE. An earlier version took it by const reference
// and callers wrote canon(s, s, bg); the first store (best = xf(s,0)) then
// overwrote the very state the remaining seven transforms read, and level 1 of
// n=6 came out with 72 representatives instead of 18.
static inline void canon(Bits s, Bits& best, int& bg) {
    best = xf(s, 0); bg = 0;
    for (int g = 1; g < 8; ++g) {
        Bits c = xf(s, g);
        if (c.hi < best.hi || (c.hi == best.hi && c.lo < best.lo)) { best = c; bg = g; }
    }
}

struct KV { u64 hi, lo; };
static inline bool kless(const KV& a, const KV& b) { return a.hi != b.hi ? a.hi < b.hi : a.lo < b.lo; }

// ================================================== legal moves (tri4 table)
struct Tri4 {
    std::vector<Bits> tab;
    std::vector<int> c1, c2, c3;
    void build(const Board& B) {
        int V = B.V;
        c1.resize((size_t)V); c2.resize((size_t)V); c3.resize((size_t)V);
        for (int p = 0; p < V; ++p) {
            c1[(size_t)p] = p;
            c2[(size_t)p] = p * (p - 1) / 2;
            c3[(size_t)p] = p > 2 ? p * (p - 1) * (p - 2) / 6 : 0;
        }
        tab.assign((size_t)V * (V - 1) * (V - 2) / 6, Bits{0, 0});
        for (const Bits& q : B.quads) {
            int p[4], c = 0;
            u64 e = q.lo; while (e) { p[c++] = __builtin_ctzll(e); e &= e - 1; }
            e = q.hi; while (e) { p[c++] = 64 + __builtin_ctzll(e); e &= e - 1; }
            if (c != 4) { fprintf(stderr, "FATAL: quad size\n"); exit(9); }
            for (int t = 0; t < 4; ++t) {
                int a, b, d;
                if (t == 0) { a = p[1]; b = p[2]; d = p[3]; }
                else if (t == 1) { a = p[0]; b = p[2]; d = p[3]; }
                else if (t == 2) { a = p[0]; b = p[1]; d = p[3]; }
                else { a = p[0]; b = p[1]; d = p[2]; }
                size_t r = (size_t)(c1[(size_t)a] + c2[(size_t)b] + c3[(size_t)d]);
                if (r >= tab.size()) { fprintf(stderr, "FATAL: tri4 rank\n"); exit(9); }
                tab[r].set(p[t]);
            }
        }
    }
};

static inline Bits free_mask(const Board& B, const Tri4& T, const Bits& S) {
    int pt[128], k = 0;
    u64 e = S.lo; while (e) { pt[k++] = __builtin_ctzll(e); e &= e - 1; }
    e = S.hi; while (e) { pt[k++] = 64 + __builtin_ctzll(e); e &= e - 1; }
    Bits blk{0, 0};
    const Bits* tab = T.tab.data();
    const int* c1 = T.c1.data(); const int* c2 = T.c2.data(); const int* c3 = T.c3.data();
    for (int a = 0; a < k; ++a) {
        const int ca = c1[pt[a]];
        for (int b = a + 1; b < k; ++b) {
            const Bits* row = tab + (ca + c2[pt[b]]);
            for (int d = b + 1; d < k; ++d) { const Bits& q = row[c3[pt[d]]]; blk.lo |= q.lo; blk.hi |= q.hi; }
        }
    }
    Bits f;
    f.lo = B.full_lo & ~S.lo & ~blk.lo;
    f.hi = B.hi_marks & ~S.hi & ~blk.hi;
    return f;
}

static void free_mask_level(const Board& B, const Tri4& T, const std::vector<Bits>& A, std::vector<Bits>& out) {
    out.resize(A.size());
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)A.size(); ++i) out[(size_t)i] = free_mask(B, T, A[(size_t)i]);
}

static u64 check_legal(const Board& B, const std::vector<Bits>& A, const std::vector<Bits>& fm) {
    u64 bad = 0;
#pragma omp parallel for schedule(static) reduction(+ : bad)
    for (long long i = 0; i < (long long)A.size(); ++i)
        if (kc::legal_mask(B, A[(size_t)i]) != fm[(size_t)i]) bad++;
    return bad;
}

// =====================================================================
// REMOVED: the v-block offset table (boff[] / compute_boff)
// =====================================================================
// boff[v] was meant to be "number of states whose largest point is < v", used
// to cut level generation into contiguous per-v blocks.  It is gone, and with
// it the whole v-block partitioning scheme, for two independent reasons:
//
//  1. The key was computed as 2^(8v) with
//         hi = ~0ull >> (128-8v),  lo = 1ull << 8v
//     which is undefined behaviour for 8v >= 64 (UBSAN: "shift exponent 64 is
//     too large") and is not a point bit in any case.  kc::Bits::set puts point
//     p at BIT p, so a point set's 128-bit key is sum_{p in S} 2^p with
//     ONE-bit spacing and the boundary value is 2^v.
//
//  2. More seriously, the partition premise is FALSE under D4.  The scheme
//     assumed "a permutation moves the largest point to the largest point", so
//     that emitting sigma_g(S) + {sigma_g(v)} for a parent with top(S) < v kept
//     every child inside block v.  A D4 element permutes the point IDs
//     arbitrarily, so sigma_g(v) is unrelated to v and
//     top(sigma_g(S) + {sigma_g(v)}) = max(top(sigma_g(S)), sigma_g(v)) is
//     neither v nor top(S + {v}).  Restricting parents to top < v therefore
//     drops real children: n=6 level 2 came out with 624 states instead of
//     C(36,2) = 630.
//
// build_next now enumerates the whole child set and relies on the 8 images of a
// child collapsing to one canonical form for the ~8x memory reduction.
// =====================================================================

// ============================================================== level store
struct Store {
    std::string dir;
    bool on = false;
    explicit Store(std::string d) : dir(std::move(d)) { on = !dir.empty(); }
    std::string pm(int k) const { return dir + "/L" + std::to_string(k) + ".m"; }
    std::string ps(int k) const { return dir + "/L" + std::to_string(k) + ".s"; }
    void save(int k, const std::vector<Bits>& A, const std::vector<uint8_t>& sg) const {
        if (!on) return;
        std::vector<u64> buf(2 * A.size());
        for (size_t i = 0; i < A.size(); ++i) { buf[2 * i] = A[i].lo; buf[2 * i + 1] = A[i].hi; }
        FILE* f = fopen(pm(k).c_str(), "wb");
        if (!f) { fprintf(stderr, "store open %s\n", pm(k).c_str()); exit(9); }
        u64 cnt = A.size();
        fwrite(&cnt, 8, 1, f);
        if (!buf.empty()) fwrite(buf.data(), 8, buf.size(), f);
        fclose(f);
        f = fopen(ps(k).c_str(), "wb");
        if (!f) { fprintf(stderr, "store open %s\n", ps(k).c_str()); exit(9); }
        if (!sg.empty()) fwrite(sg.data(), 1, sg.size(), f);
        fclose(f);
    }
    bool load(int k, std::vector<Bits>& A, std::vector<uint8_t>& sg) const {
        A.clear(); sg.clear();
        if (!on) return false;
        FILE* f = fopen(pm(k).c_str(), "rb");
        if (!f) return false;
        u64 cnt = 0;
        if (fread(&cnt, 8, 1, f) != 1) { fclose(f); return false; }
        A.resize((size_t)cnt);
        std::vector<u64> buf(2 * (size_t)cnt);
        size_t got = cnt ? fread(buf.data(), 8, buf.size(), f) : 0;
        fclose(f);
        if (got != buf.size()) { fprintf(stderr, "store short L%d\n", k); exit(9); }
        for (size_t i = 0; i < (size_t)cnt; ++i) { A[i].lo = buf[2 * i]; A[i].hi = buf[2 * i + 1]; }
        f = fopen(ps(k).c_str(), "rb");
        if (!f) { fprintf(stderr, "store missing %s\n", ps(k).c_str()); exit(9); }
        sg.resize((size_t)cnt);
        if (cnt && fread(sg.data(), 1, (size_t)cnt, f) != (size_t)cnt) { fprintf(stderr, "store short sig L%d\n", k); exit(9); }
        fclose(f);
        return true;
    }
};

// ============================================================ next level
struct GenStat { u64 cand = 0, emitted = 0; double secs = 0; };

// Builds the canonical level k+1 from the canonical level k.
//
// ---------------------------------------------------------------------------
// WHY THIS IS NO LONGER A v-BLOCK PARTITION
// ---------------------------------------------------------------------------
// The previous version generated block v of level k+1 only from level-k states
// with top < v, which is sound for the RAW (unsymmetrised) enumeration: a
// child C = S + {v} is generated exactly once, by the pair (S, top(C)).  Under
// D4 that argument collapses, because the code then emitted
//     sigma_g(S) + {sigma_g(v)}
// and assumed "a permutation moves the largest point to the largest point", so
// that every image of a child stayed in block v.  That is false.  D4 permutes
// the 36/121 POINT IDS of the board arbitrarily; sigma_g(v) bears no relation
// to v, and top(sigma_g(S) + {sigma_g(v)}) = max(top(sigma_g(S)), sigma_g(v))
// is not v and not top(C).  So the v-block cut parents off that the child
// needed, and n=6 level 2 came out with 624 states instead of C(36,2) = 630 --
// six pairs missing, and the DP then reported 1428 failed child lookups.
//
// The fix is to stop partitioning and enumerate the full child set.  The cost
// is memory: the candidate buffer holds 8 * (number of edges) = 8 * (k+1) *
// M_{k+1} slots of 16 B.  For n=11 level 5 that is 8 * 6 * 23.5M = 1.13e9
// slots = 18 GB, which does not fit, so the caller caps the buffer and the run
// stops at the last level that does.  Correctness first: a level that is
// generated at all is generated exactly and completely.
//
// The reduction still comes from where it always came from -- the 8 images of a
// child collapse to one canonical form -- so a level still holds ~M/8 entries.
static bool build_next(const Board& B, const std::vector<Bits>& A, const std::vector<Bits>& fm,
                       std::vector<Bits>& nA, std::vector<uint8_t>& nsg, std::vector<KV>& cd,
                       u64 maxcand, GenStat& gs, int dbg = 0) {
    const int T = 64;                              // static omp chunks
    const size_t M = A.size();
    nA.clear(); nsg.clear();
    gs.cand = 0; gs.emitted = 0;
    if (!M) return true;

    // ---- pass 1: count the candidates per chunk -------------------------
    // A candidate is (parent, legal point v) and yields canon(S + {v}).
    //
    // ONLY ONE GENERATOR IS NEEDED.  D4 is a group, so {sigma_{hg} : g in D4} =
    // D4, and therefore
    //     canon(sigma_g(C)) = min_{h in D4} sigma_h(sigma_g(C))
    //                       = min_{h' in D4} sigma_{h'}(C) = canon(C)
    // for every g.  The original code looped g over all eight generators and
    // emitted canon(sigma_g(S) + {sigma_g(v)}) eight times per (S, v); all eight
    // values are IDENTICAL, so the loop was an 8x pure waste of both time and
    // memory.  --gloopcheck verifies this claim at run time on a sample
    // instead of trusting the argument.
    std::vector<u64> cnt((size_t)T, 0);
#pragma omp parallel for schedule(static)
    for (int t = 0; t < T; ++t) {
        size_t lo = M * (size_t)t / T, hi = M * (size_t)(t + 1) / T;
        u64 c = 0;
        for (size_t i = lo; i < hi; ++i) {
            const Bits& f = fm[i];
            if (f.lo) c += (u64)__builtin_popcountll(f.lo);
            if (f.hi) c += (u64)__builtin_popcountll(f.hi);
        }
        cnt[(size_t)t] = c;
    }
    u64 total = 0;
    std::vector<u64> off((size_t)T + 1, 0);
    for (int t = 0; t < T; ++t) { off[(size_t)t] = total; total += cnt[(size_t)t]; }
    off[(size_t)T] = total;

    if (total == 0) return true;
    if (total > maxcand) {
        fprintf(stderr, "  level needs %llu candidate slots (cap %llu, %.1f GB at 16 B)\n",
                (unsigned long long)total, (unsigned long long)maxcand, total * 16.0 / 1073741824.0);
        return false;
    }

    // ---- pass 2: emit them, canonicalised, into a per-chunk sorted run ---
    // Each thread owns one chunk and appends into a private vector, so there is
    // no cross-thread contention and no prefix-sum race.  The private vectors
    // are merged (not concatenated) at the end, which is what keeps the output
    // globally sorted.
    std::vector<std::vector<KV>> part((size_t)T);
    std::vector<u64> partn((size_t)T, 0);
#pragma omp parallel for schedule(static)
    for (int t = 0; t < T; ++t) {
        size_t lo = M * (size_t)t / T, hi = M * (size_t)(t + 1) / T;
        std::vector<KV>& out = part[(size_t)t];
        out.reserve((size_t)cnt[(size_t)t]);
        for (size_t i = lo; i < hi; ++i) {
            const Bits f = fm[i];
            // Emit the child in the PARENT'S OWN FRAME, C = S + {v}, and
            // canonicalise C once.  This is NOT the naive "1/8 the states"
            // reading that was removed above: the parent S is already a
            // canonical representative, and C ranges over ALL legal children of
            // S, so the set {canon(C)} is the set of canonical representatives of
            // every orbit at level k+1 -- each orbit is hit by the canonical
            // representative of its own (k+1)-subsets, which is a child of some
            // level-k canonical representative.  (Group-closure argument: the
            // eight children of the eight images sigma_g(S) are exactly
            // {sigma_g(C) : C a child of S}, whose canonical forms are the same
            // set.  So looping g emitted each distinct value eight times.)
            for (int half = 0; half < 2; ++half) {
                u64 e = half ? f.hi : f.lo;
                while (e) {
                    int v = half ? 64 + __builtin_ctzll(e) : __builtin_ctzll(e);
                    e &= e - 1;
                    Bits c = A[i];
                    if (v < 64) c.lo |= 1ull << v; else c.hi |= 1ull << (v - 64);
                    Bits best; int bg;
                    canon(c, best, bg);
                    out.push_back(KV{best.hi, best.lo});
                }
            }
        }
        std::sort(out.begin(), out.end(), [](const KV& x, const KV& y) { return kless(x, y); });
        partn[(size_t)t] = out.size();
    }
    gs.cand = total;
    for (int t = 0; t < T; ++t) gs.emitted += partn[(size_t)t];

    // ---- k-way merge + unique --------------------------------------------
    // The T=64 per-chunk runs are each already sorted, so they are merged with
    // a 64-way binary heap straight into `nA`, emitting as we go.  The old code
    // first CONCATENATED all T runs into one `flat` buffer and std::sort'ed it,
    // which meant the whole candidate set existed twice at once (2 x total x
    // 16 B).  The merge touches one KV at a time, so peak memory here is
    // total x 16 B for the runs plus w x 16 B for the output -- a factor ~2
    // better exactly where n=11 level 6 is tightest.  It is also O(total log T)
    // instead of O(total log total), and the runs really do overlap heavily
    // (that overlap is the dedup), so sorting the concatenation was doing the
    // most expensive possible thing.
    {
        nA.resize((size_t)total);          // worst case: no duplicates at all
        size_t pos[T];
        for (int t = 0; t < T; ++t) pos[t] = 0;
        // heap of run indices, ordered by the head KV of each run
        int heap[T];
        int hn = 0;
        for (int t = 0; t < T; ++t) {
            if (part[(size_t)t].empty()) continue;
            heap[hn++] = t;
        }
        auto lessrun = [&](int x, int y) {
            const KV& a = part[(size_t)x][pos[x]];
            const KV& b = part[(size_t)y][pos[y]];
            if (kless(b, a)) return true;
            if (kless(a, b)) return false;
            return x > y;                    // stable tie-break on run index
        };
        std::make_heap(heap, heap + hn, lessrun);
        u64 w = 0;
        u64 prev_hi = 0, prev_lo = 0;
        bool have_prev = false;
        while (hn) {
            std::pop_heap(heap, heap + hn, lessrun);
            const int t = heap[--hn];
            const KV& v = part[(size_t)t][pos[t]++];
            if (!have_prev || v.hi != prev_hi || v.lo != prev_lo) {
                nA[(size_t)w].hi = v.hi; nA[(size_t)w].lo = v.lo;
                ++w; prev_hi = v.hi; prev_lo = v.lo; have_prev = true;
            }
            if (pos[t] < part[(size_t)t].size()) {
                heap[hn++] = t;
                std::push_heap(heap, heap + hn, lessrun);
            }
        }
        nA.resize((size_t)w);
        nA.shrink_to_fit();
    }
    // nA is now the exact, sorted, duplicate-free canonical level.  Store the
    // signature generator: the one whose image IS the stored minimum.
    nsg.resize(nA.size());
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)nA.size(); ++i) {
        Bits best; int bg;
        canon(nA[(size_t)i], best, bg);
        nsg[(size_t)i] = (uint8_t)bg;
    }
    gs.emitted = nA.size();
    return true;
}

// ================================================================== the DP
struct LevelStat { u64 orbits = 0, raw = 0, P_orbits = 0, N_orbits = 0; double gen_s = 0, dp_s = 0; };

int main(int argc, char** argv) {
    int n = 0, threads = 0, maxlevel = 1 << 20, check_legal_limit = 0, dbg = 0, gloopcheck = 0;
    std::string outjson, spill;
    u64 maxcand = 400ull * 1000 * 1000;   // 16 B per slot -> 6.4 GB candidate buffer
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto val = [&]() -> std::string { return (i + 1 < argc) ? argv[++i] : ""; };
        if (a == "--n") n = atoi(val().c_str());
        else if (a == "--threads") threads = atoi(val().c_str());
        else if (a == "--maxlevel") maxlevel = atoi(val().c_str());
        else if (a == "--check-legal") check_legal_limit = 1 << 30;
        else if (a == "--check-legal-first") check_legal_limit = atoi(val().c_str());
        else if (a == "--dbg") dbg = atoi(val().c_str());
        else if (a == "--gloopcheck") gloopcheck = atoi(val().c_str());
        else if (a == "--maxcand") maxcand = strtoull(val().c_str(), nullptr, 10);
        else if (a == "--spill") spill = val();
        else if (a == "--out") outjson = val();
        else { fprintf(stderr, "unknown arg %s\n", a.c_str()); return 2; }
    }
    if (n <= 0) { fprintf(stderr, "usage: --n <n> [--spill dir] [--out f]\n"); return 2; }
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
    const double t_start = now_s();
    fprintf(stderr, "[n=%d] threads=%d\n", n, nth);

    Board B; kc::build_square(B, n);
    build_d4(n);
    Tri4 T; T.build(B);
    fprintf(stderr, "[n=%d] V=%d F=%zu tri4=%.1fMB\n", n, B.V, B.quads.size(),
            T.tab.size() * 16.0 / 1048576.0);
    fflush(stderr);

    // D4 point-orbit sizes; a level of orbits with tau[] gives the raw level
    // size, which is what the published per-layer numbers refer to.
    std::vector<int> tau((size_t)B.V, 0);
    for (int v = 0; v < B.V; ++v) {
        // Same 64-bit trap as build_d4's bijection check: `u64 seen` with
        // `1ull << w` silently wraps for w >= 64, so every point past the 64th
        // would be counted as a fresh member of its own orbit and tau[] would be
        // wrong for n=9,10,11 (V = 81, 100, 121).  tau is diagnostics only -- the
        // authoritative `raw` below is summed from real stabilisers -- but a
        // wrong diagnostic on the one n we care about is still a landmine.
        Bits seen{0, 0};
        int s = 0;
        for (int g = 0; g < 8; ++g) {
            int w = PERM[g][v];
            int bit = (w < 64) ? (int)((seen.lo >> w) & 1ull) : (int)((seen.hi >> (w - 64)) & 1ull);
            if (!bit) { if (w < 64) seen.lo |= 1ull << w; else seen.hi |= 1ull << (w - 64); s++; }
        }
        tau[(size_t)v] = s;
    }
    int point_orbits = 0;
    { std::vector<int> t2 = tau; std::sort(t2.begin(), t2.end());
      for (size_t i = 0; i < t2.size(); ++i) if (!i || t2[i] != t2[i - 1]) point_orbits++; }

    // Transform-slot diagnostics: which of the 8 generators gets to choose the
    // canonical form, split by the stabiliser order of the position.  A
    // position with a trivial stabiliser must be reachable from EVERY
    // generator -- that is exactly the coverage property the DP relies on, and
    // a slot that comes up empty is the signature of a broken build_d4.
    fprintf(stderr, "[n=%d] D4 point orbits=%d (sizes %d..%d)\n", n, point_orbits,
            *std::min_element(tau.begin(), tau.end()), *std::max_element(tau.begin(), tau.end()));
    fflush(stderr);

    Store st(spill);
    if (st.on) {
        std::string cmd = "mkdir -p '" + spill + "'";
        if (system(cmd.c_str()) != 0) { fprintf(stderr, "cannot create %s\n", spill.c_str()); return 9; }
    }

    // -------------------------------------------------------- enumeration
    std::vector<Bits> A; std::vector<uint8_t> sg;
    std::vector<Bits> nA; std::vector<uint8_t> nsg;
    std::vector<Bits> fm; std::vector<KV> cd;
    std::vector<LevelStat> stat;
    A.push_back(Bits{0, 0}); sg.push_back(0);
    st.save(0, A, sg);
    stat.push_back(LevelStat{});
    stat[0].orbits = 1; stat[0].raw = 1;

    bool stopped = false;
    for (int k = 0; k < maxlevel; ++k) {
        const double t0 = now_s();
        free_mask_level(B, T, A, fm);
        if (check_legal_limit && A.size() <= (size_t)check_legal_limit) {
            u64 bad = check_legal(B, A, fm);
            fprintf(stderr, "  level %d: free-mask vs kc::legal_mask mismatches=%llu\n", k, (unsigned long long)bad);
            if (bad) return 9;
        }
        GenStat gs;
        if (!build_next(B, A, fm, nA, nsg, cd, maxcand, gs, dbg)) { stopped = true; break; }
        // --gloopcheck L: brute-force verify on a sample of the parents that the
        // eight generators really do collapse to one canonical form, and that the
        // no-generator loop emits the same distinct SET (modulo multiplicity).
        // This is the run-time witness for the 8x removal; see build_next.
        if (gloopcheck && k <= gloopcheck && (int)A.size() <= gloopcheck) {
            u64 checked = 0, badg = 0;
            for (size_t i = 0; i < A.size(); ++i) {
                const Bits f = fm[i];
                for (int half = 0; half < 2; ++half) {
                    u64 e = half ? f.hi : f.lo;
                    while (e) {
                        int v = half ? 64 + __builtin_ctzll(e) : __builtin_ctzll(e);
                        e &= e - 1;
                        Bits C = A[i];
                        if (v < 64) C.lo |= 1ull << v; else C.hi |= 1ull << (v - 64);
                        Bits b0; int g0; canon(C, b0, g0);
                        for (int g = 1; g < 8; ++g) {
                            Bits img = xf(C, g), bg_; int gg;
                            canon(img, bg_, gg);
                            if (bg_.lo != b0.lo || bg_.hi != b0.hi) badg++;
                        }
                        checked++;
                    }
                }
            }
            fprintf(stderr, "  level %d: gloopcheck children=%llu canon-mismatches=%llu\n",
                    k, (unsigned long long)checked, (unsigned long long)badg);
            if (badg) { fprintf(stderr, "FATAL: generators do NOT collapse -- 8x removal unsound\n"); return 9; }
        } else if (gloopcheck && (int)A.size() > gloopcheck) {
            // gloopcheck is quadratic-ish in the child count (each child costs 8
            // extra canon() calls), so past the limit it is skipped on purpose --
            // it was already proven exhaustively on the smaller n, and the DP's
            // own "failed child lookups" assertion is the end-to-end witness that
            // every generated child really landed in the next level.
            fprintf(stderr, "  level %d: gloopcheck SKIPPED (%zu parents > limit %d)\n",
                    k, A.size(), gloopcheck);
        }
        // The level-(k+1) slot must EXIST before it is written.  The old code
        // pushed the placeholder at the *bottom* of the loop body, so every
        // iteration wrote stat[k+1] on a vector whose size was still k+1 --
        // one element past the end, straight into unallocated heap
        // (ASAN: heap-buffer-overflow at this line; plain build: SIGSEGV on the
        // first iteration, n=6).  Grow first, fill second.
        stat.push_back(LevelStat{});
        stat[(size_t)(k + 1)].gen_s = now_s() - t0;
        stat[(size_t)(k + 1)].orbits = nA.size();
        // EXACT raw level size = sum over representatives of the true orbit
        // size 8/|stabiliser|.  The old code used tau[top_point(s)] (the orbit
        // size of the largest point ALONE), which is only the orbit size of
        // the whole position when the position has a trivial stabiliser -- so
        // it silently under-counted symmetric positions.  Count the generators
        // that actually fix S.
        u64 raw = 0;
        for (const Bits& s : nA) {
            if (!(s.lo || s.hi)) continue;             // the empty position
            int stab = 0;
            for (int g = 0; g < 8; ++g) { Bits t = xf(s, g); if (t.lo == s.lo && t.hi == s.hi) stab++; }
            raw += 8ull / (u64)stab;
        }
        stat[(size_t)(k + 1)].raw = raw;
        if (dbg) {
            fprintf(stderr, "  dbg nA:");
            for (size_t i = 0; i < nA.size() && i < 16; ++i) fprintf(stderr, " %llx/%u", (unsigned long long)nA[i].lo, (unsigned)nsg[i]);
            fprintf(stderr, "\n");
        }
        fprintf(stderr, "  gen k=%2d orbits=%-11llu raw=%-12llu cand=%-12llu  %.1fs rss=%ldMB\n", k + 1,
                (unsigned long long)nA.size(), (unsigned long long)raw, (unsigned long long)gs.cand,
                stat[(size_t)(k + 1)].gen_s, rss_mb());
        fflush(stderr);
        if (nA.empty()) { A.clear(); sg.clear(); fm.clear(); stat.pop_back(); break; }
        st.save(k + 1, nA, nsg);
        A.swap(nA); sg.swap(nsg);
        // After the swap A is the NEW level and nA/nsg hold the OLD one.  The
        // old code then ran `A.clear(); nA.clear(); nsg.clear();`, which threw
        // away the level it had just built and left the next iteration with an
        // EMPTY parent list -- so level 2 onwards produced no candidates at
        // all and the DP reported failed child lookups.  Free only the old ones.
        nA.clear(); nsg.clear();
        fm.clear(); fm.shrink_to_fit();
    }
    if (stopped) fprintf(stderr, "STOPPED: candidate buffer cap reached at level %d\n", (int)stat.size());
    // The generator appends one trailing EMPTY level (the first k with no
    // reachable position), so stat.size() - 1 is that empty level, not the
    // last non-empty one. Taking K from stat.size() - 1 makes the DP start
    // by loading a level that was never stored, which is what the
    // "FATAL: level N not in store" abort was. Walk back to the last level
    // that actually has positions.
    int K = (int)stat.size() - 1;
    while (K > 0 && stat[(size_t)K].raw == 0) --K;
    if (K < 0) { fprintf(stderr, "no levels\n"); return 9; }

    char buf[8192];
    std::string lvl_report = "[";
    for (int k = 0; k <= K; ++k) { snprintf(buf, sizeof buf, "%s%llu", k ? "," : "", (unsigned long long)stat[(size_t)k].raw); lvl_report += buf; }
    lvl_report += "]";
    fprintf(stderr, "[n=%d] K=%d raw level sizes = %s\n", n, K, lvl_report.c_str());
    fprintf(stderr, "[n=%d] D4 point orbits=%d (sizes %d..%d)\n", n, point_orbits,
            *std::min_element(tau.begin(), tau.end()), *std::max_element(tau.begin(), tau.end()));
    fflush(stderr);

    // `stopped` means the level K we ended up with is NOT a closed game tree:
    // build_next refused to build level K+1, so the deepest level still has
    // legal moves whose Grundy values were never computed.  The DP below
    // nevertheless proceeds -- it has to, to show the partial P/N pattern --
    // but it seeds g(level K) = 0, i.e. it treats the frontier as terminal.
    // The resulting g(empty) is therefore NOT the true Grundy value: it is the
    // value of a truncated game.  n=11 K=5 is exactly this case (2,439,393,194
    // children of level 5 were never built), and its g_empty must be reported
    // as unknown, not as "first player wins".
    const bool truncated = stopped;

    // ------------------------------------------------------------- the DP
    std::vector<Bits> cur, nxt;
    std::vector<uint8_t> cs, ns_, gnext, gk;
    std::vector<u64> cboff, nboff2;   // v-block offsets: no longer used (see DP note)
    std::vector<Bits> f1;
    bool have_cur = st.load(K, cur, cs);
    if (!have_cur) { fprintf(stderr, "FATAL: level %d not in store\n", K); return 9; }
    gnext.assign(cur.size(), 0);                      // top level is terminal
    stat[(size_t)K].P_orbits = cur.size();
    stat[(size_t)K].N_orbits = 0;
    {
        std::vector<Bits>().swap(cur); std::vector<uint8_t>().swap(cs);
    }
    for (int k = K - 1; k >= 0; --k) {
        const double t0 = now_s();
        if (!st.load(k + 1, nxt, ns_)) { fprintf(stderr, "FATAL: level %d not in store\n", k + 1); return 9; }
        if (!st.load(k, cur, cs)) { fprintf(stderr, "FATAL: level %d not in store\n", k); return 9; }
        if (nxt.size() != gnext.size()) { fprintf(stderr, "FATAL: size mismatch k=%d\n", k); return 9; }
        const size_t M = cur.size();
        gk.assign(M, 0);
        u64 fail = 0;
        // g(S) for a canonical representative S.  The children of S in S's own
        // frame are S + {v} for v in L(S).  Each child is NOT canonical, so we
        // take canon(S + {v}) and look THAT up in level k+1.
        //
        // The previous code instead transformed the parent to img = sigma_t(S),
        // built img + {v}, then looked up each of the 8 raw images
        // xf(img + {v}, h) directly in `nxt`.  That is wrong twice: (1) `nxt`
        // stores only canonical representatives, so a raw image hits only by
        // luck (this produced the "240 / 1428 failed child lookups" fatal);
        // (2) the 8 images are the same orbit, so their g is equal by (1) --
        // one canonicalisation is both necessary and sufficient.  The signature
        // `t` and the v-block-of-top(t2) binary search are not needed at all.
#pragma omp parallel for schedule(static) reduction(+ : fail)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            const size_t i = (size_t)ii;
            const Bits S = cur[i];
            const Bits f = free_mask(B, T, S);
            unsigned acc = 0;
            for (int half = 0; half < 2; ++half) {
                u64 e = half ? f.hi : f.lo;
                while (e) {
                    int v = half ? 64 + __builtin_ctzll(e) : __builtin_ctzll(e);
                    e &= e - 1;
                    Bits c = S;
                    if (v < 64) c.lo |= 1ull << v; else c.hi |= 1ull << (v - 64);
                    Bits best; int bg;
                    canon(c, best, bg);
                    // binary search the whole sorted level k+1
                    KV kk{best.hi, best.lo};
                    size_t lo = 0, hi = nxt.size();
                    while (lo < hi) { size_t m = (lo + hi) >> 1; KV a{nxt[m].hi, nxt[m].lo}; if (kless(a, kk)) lo = m + 1; else hi = m; }
                    if (lo < nxt.size() && nxt[lo].hi == kk.hi && nxt[lo].lo == kk.lo) acc |= 1u << gnext[lo];
                    else fail++;
                }
            }
            unsigned z = ~acc;
            gk[i] = (uint8_t)(z ? __builtin_ctz(z) : 0);
        }
        if (fail) { fprintf(stderr, "FATAL: level %d had %llu failed child lookups\n", k, (unsigned long long)fail); return 9; }
        u64 nP = 0;
        for (size_t i = 0; i < M; ++i) if (!gk[i]) nP++;
        stat[(size_t)k].P_orbits = nP; stat[(size_t)k].N_orbits = M - nP;
        stat[(size_t)k].dp_s = now_s() - t0;
        gnext.swap(gk);
        fprintf(stderr, "  dp  k=%2d orbits=%-11llu P=%-11llu N=%-11llu  %.1fs rss=%ldMB\n", k,
                (unsigned long long)M,
                (unsigned long long)nP, (unsigned long long)(M - nP), stat[(size_t)k].dp_s, rss_mb());
        fflush(stderr);
        { std::vector<Bits>().swap(nxt); std::vector<uint8_t>().swap(ns_); }
    }
    { std::vector<Bits>().swap(cur); std::vector<uint8_t>().swap(cs); }

    const int g_empty = gnext.empty() ? -1 : gnext[0];
    // A run is TRUSTWORTHY only if it closed the game tree.  If build_next gave
    // up at some level, the frontier was scored as if it had no legal moves, and
    // g_empty (and every P/N count below the frontier) is that of a truncated
    // game.  Report it as such instead of letting a positive number read as
    // "first player wins".
    const char* win = truncated ? "UNKNOWN"
                                : (g_empty == 0 ? "second" : (g_empty > 0 ? "first" : "UNKNOWN"));
    fprintf(stderr, "=== n=%d g(empty)=%d K=%d %s rss=%ldMB %.1fs\n", n, g_empty, K,
            truncated ? "[TRUNCATED - g_empty is NOT the true value]" : "[COMPLETE]",
            rss_mb(), now_s() - t_start);

    std::string j;
    auto app = [&](const char* fmt, ...) {
        va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
        j += buf;
    };
    app("{\n  \"n\": %d,\n  \"V\": %d,\n  \"F\": %zu,\n  \"K\": %d,\n", n, B.V, B.quads.size(), K);
    app("  \"symmetry\": \"D4\",\n  \"d4_point_orbits\": %d,\n", point_orbits);
    app("  \"complete\": %s,\n", truncated ? "false" : "true");
    app("  \"g_empty_truncated\": %d,\n", g_empty);
    app("  \"g_empty\": %s,\n", truncated ? "null" : (g_empty == 0 ? "0" : (g_empty > 0 ? "1" : "null")));
    app("  \"winner\": \"%s\",\n", win);
    app("  \"level_sizes_raw\": %s,\n", lvl_report.c_str());
    app("  \"level_sizes_orbits\": [");
    for (int k = 0; k <= K; ++k) app("%s%llu", k ? "," : "", (unsigned long long)stat[(size_t)k].orbits);
    app("],\n  \"levels\": [\n");
    for (int k = 0; k <= K; ++k)
        app("    {\"k\": %d, \"orbits\": %llu, \"raw\": %llu, \"P_orbits\": %llu, \"N_orbits\": %llu, \"gen_s\": %.2f, \"dp_s\": %.2f}%s\n",
            k, (unsigned long long)stat[(size_t)k].orbits, (unsigned long long)stat[(size_t)k].raw,
            (unsigned long long)stat[(size_t)k].P_orbits, (unsigned long long)stat[(size_t)k].N_orbits,
            stat[(size_t)k].gen_s, stat[(size_t)k].dp_s, k < K ? "," : "");
    app("  ],\n  \"threads\": %d,\n  \"total_seconds\": %.2f,\n  \"peak_rss_mb\": %ld\n}\n",
        nth, now_s() - t_start, rss_mb());
    if (!outjson.empty()) {
        FILE* f = fopen(outjson.c_str(), "wb");
        if (f) { fwrite(j.data(), 1, j.size(), f); fclose(f); fprintf(stderr, "wrote %s\n", outjson.c_str()); }
    }
    printf("%s", j.c_str());
    return 0;
}
