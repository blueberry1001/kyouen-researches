// Round5 n=8 memory experiment: STREAMING (disk-spilled) layer enumerator and
// p_rand DP.
//
// Purpose: answer "can n=8 fit in a 19 GB box?", i.e. separate the two costs that
// round4-n8-feasibility.md conflated:
//    (a) holding one layer of state masks      -> 8 B/state
//    (b) holding ALL layers at once             -> 8 B/state x sum_k |L_k|
// and (c) the sort/dedup working memory, which the old code paid 9x over.
//
// ---------------------------------------------------------------------------
// 1. THE SORT-FREE LEVEL GENERATION  (this is the main structural change)
// ---------------------------------------------------------------------------
// round5_b501_prand8.cpp builds the next level by
//     nxt.reserve(total_edges);  for every state, for every legal move, push;
//     sort(nxt); unique(nxt);
// so it needs  8 B x (number of EDGES)  = 8 B x ~9 x |L_{k+1}|  (n=7: 3.97 GB for
// level 9) plus a full sort of that array.
//
// Partition the children by the ADDED vertex and require that the added vertex is
// the maximum vertex of the child:
//     C'_v = { S | (1<<v) : S in L_k, v in L(S), S < 2^v }
// Then
//   (i)  the C'_v are DISJOINT  (max bit of the child is exactly v, unique), and
//   (ii) every T in L_{k+1} is produced exactly once, by v = max bit of T, because
//        S = T \ {v} is in L_k and v is legal for S (T and S are both safe), and
//   (iii) concatenating C'_0, C'_1, ... C'_63 in increasing v yields a SORTED
//        array, because every element of C'_v is < 2^(v+1) <= every element of
//        C'_{v+1}; and inside one C'_v, S -> S|(1<<v) is order preserving
//        (S < 2^v, so the bit-v pattern is constant).
// So level k+1 is produced ALREADY SORTED, with no sort, no unique, and an output
// array of exactly |L_{k+1}| elements.  Cost: 2 passes over L_k, O(|L_k| + E_k)
// time, 8 B x (|L_k| + |L_{k+1}|) RAM, or ~300 MB RAM when the output is pw'ed
// straight to a file.
// (This is the same partition used in round4_b371.cpp; it is re-derived here
//  because it is what makes the spill version cheap.)
//
// ---------------------------------------------------------------------------
// 2. MODES
// ---------------------------------------------------------------------------
//   --enum  <n> [--spill[=dir]] [--maxlevel K]
//        forward enumeration only; prints level_sizes, per-level seconds, peak
//        RSS, and the spill file sizes.  This is the n=8 measurement.
//   --solve <n> [--spill=dir] [--out f.json] [--kcap K]
//        the round5 CRT DP (numerator mod 2^61-1, 8 B/state, + u32 fixed-point
//        filter) with a 2-layer rolling window that is loaded from the spill
//        files, so no layer is ever held longer than its own iteration pair.
//
// Reproduces n=6 and n=7 of round4_b501_prand_n7.json exactly (level_sizes,
// edge_total, n_P, per-level max, P_max).
//
// Usage (WSL):
//   g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/stream round5_prand_stream.cpp
//   /tmp/stream --enum 7
//   /tmp/stream --enum 8 --spill=/tmp/l8
//   /tmp/stream --solve 7 --spill=/tmp/l7 --out /tmp/n7.json
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
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
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
static double rss_cur_gb() {
    FILE* f = fopen("/proc/self/status", "r");
    if (!f) return -1;
    char line[256];
    double v = 0;
    while (fgets(line, sizeof line, f))
        if (strncmp(line, "VmRSS:", 6) == 0) { long long x; sscanf(line + 6, "%lld", &x); v = x / 1048576.0; break; }
    fclose(f);
    return v;
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
static constexpr u64 P1 = (1ULL << 61) - 1;
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
static inline u64 madd(u64 x, u64 y) { u64 s = x + y; if (s < x || s >= P1) s -= P1; return s; }
static inline u64 msub(u64 x, u64 y) { return x >= y ? x - y : x + (P1 - y); }
static u64 mpow(u64 a, u64 e) {
    u64 r = 1;
    while (e) { if (e & 1) r = mmul(r, a); a = mmul(a, a); e >>= 1; }
    return r;
}
static u64 g_invc1[65];
static void invc_init() { for (int c = 1; c <= 64; ++c) g_invc1[c] = mpow((u64)c, P1 - 2); }
static constexpr u32 SCALE = 1u << 30;

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
static void legal_level(const Ctx& ctx, const u64* A, size_t M, u64* out) {
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)M; ++i) out[i] = legal_one(ctx, A[i]);
}
// highest set bit, -1 for 0
static inline int hib(u64 x) { return x ? (63 - __builtin_clzll(x)) : -1; }

// =========================================================================
// SORT-FREE next-level generation, in RAM.
//   A    : level k, sorted, M elements
//   LMA  : legal mask of each element of A
//   nxt  : output, receives |L_{k+1}| elements, sorted
// Returns |L_{k+1}|.  No sort, no unique, no edge-sized buffer.
// =========================================================================
static size_t gen_next_inram(const Ctx& ctx, const u64* A, const u64* LMA, size_t M, u64* nxt) {
    const int V = ctx.V;
    size_t pcnt[64] = {0}, off[65] = {0};
    // pass 1: counts per bucket (64 counters, fit in L1)
    for (size_t i = 0; i < M; ++i) {
        u64 S = A[i], lm = LMA[i];
        if (!lm) continue;
        int hb = hib(S);
        while (lm) { int v = __builtin_ctzll(lm); lm &= lm - 1; if (v > hb) ++pcnt[v]; }
    }
    for (int v = 0; v < V; ++v) off[v + 1] = off[v] + pcnt[v];
    size_t tot = off[V];
    // pass 2: write, bucket v ascending in S => ascending in value
    size_t cur[64];
    for (int v = 0; v < V; ++v) cur[v] = off[v];
    for (size_t i = 0; i < M; ++i) {
        u64 S = A[i], lm = LMA[i];
        if (!lm) continue;
        int hb = hib(S);
        while (lm) { int v = __builtin_ctzll(lm); lm &= lm - 1; if (v > hb) nxt[cur[v]++] = S | (u64(1) << v); }
    }
    return tot;
}

// =========================================================================
// SORT-FREE next-level generation, SPILLED.  A is a sorted u64 file of M*8
// bytes; the output goes to a new file of tot*8 bytes, written with 64
// independent pwrite cursors, so RAM is just the 64 user-space write buffers.
// Peak RAM here is independent of the layer size -- that is the point.
// =========================================================================
struct Spiller {
    std::string dir;
    std::vector<size_t> sizes;
    std::vector<size_t> edges;
    Spiller(const std::string& d) : dir(d) {
        if (!dir.empty()) { std::string c = "mkdir -p '" + dir + "'"; if (system(c.c_str())) {} }
    }
    std::string path(int k) const { return dir + "/level_" + std::to_string(k) + ".occ"; }
};

static size_t gen_next_spill(const Ctx& ctx, const std::string& inpath, size_t M,
                             const std::string& outpath, size_t* out_bytes) {
    const int V = ctx.V;
    const size_t CHUNK = 1u << 20;                  // 1M states = 8 MB per read
    const size_t WBUF  = 1u << 19;                  // 512 K states = 4 MB per write stream
    int fd_in = open(inpath.c_str(), O_RDONLY);
    if (fd_in < 0) { fprintf(stderr, "cannot open %s\n", inpath.c_str()); exit(7); }
    std::vector<u64> rin(CHUNK), lmin(CHUNK);
    std::vector<size_t> pcnt(64, 0);
    // ---- pass 1: count buckets by streaming A ----
    for (size_t done = 0; done < M; ) {
        size_t want = std::min(CHUNK, M - done);
        ssize_t got = 0, want_b = (ssize_t)(want * 8);
        char* dst = (char*)rin.data();
        while (got < want_b) {
            ssize_t r = read(fd_in, dst + got, (size_t)(want_b - got));
            if (r <= 0) { fprintf(stderr, "short read on %s\n", inpath.c_str()); exit(7); }
            got += r;
        }
        legal_level(ctx, rin.data(), want, lmin.data());
        for (size_t i = 0; i < want; ++i) {
            u64 S = rin[i], lm = lmin[i];
            if (!lm) continue;
            int hb = hib(S);
            while (lm) { int v = __builtin_ctzll(lm); lm &= lm - 1; if (v > hb) ++pcnt[v]; }
        }
        done += want;
    }
    std::vector<size_t> off(65, 0);
    for (int v = 0; v < V; ++v) off[v + 1] = off[v] + pcnt[v];
    size_t tot = off[V];
    *out_bytes = tot * 8;
    if (tot == 0) { close(fd_in); return 0; }
    // ---- pass 2: rewind, write each child at its bucket offset ----
    if (lseek(fd_in, 0, SEEK_SET) < 0) { fprintf(stderr, "lseek fail\n"); exit(7); }
    int fd_out = open(outpath.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd_out < 0) { fprintf(stderr, "cannot create %s\n", outpath.c_str()); exit(7); }
    if (ftruncate(fd_out, (off_t)(tot * 8)) < 0) { fprintf(stderr, "ftruncate fail\n"); exit(7); }
    std::vector<u64> wbuf(64 * WBUF);
    std::vector<size_t> wpos(64, 0);   // states currently buffered per bucket
    std::vector<off_t> wcur(64);       // next file offset per bucket
    for (int v = 0; v < V; ++v) wcur[v] = (off_t)(off[v] * 8);
    auto flush = [&](int v) {
        if (!wpos[v]) return;
        const char* p = (const char*)(wbuf.data() + (size_t)v * WBUF);
        size_t nb = wpos[v] * 8, off_b = 0;
        while (nb) {
            ssize_t w = pwrite(fd_out, p + off_b, nb, wcur[v] + (off_t)off_b);
            if (w <= 0) { fprintf(stderr, "pwrite fail on %s\n", outpath.c_str()); exit(7); }
            off_b += (size_t)w; nb -= (size_t)w;
        }
        wcur[v] += (off_t)(wpos[v] * 8);
        wpos[v] = 0;
    };
    for (size_t done = 0; done < M; ) {
        size_t want = std::min(CHUNK, M - done);
        ssize_t got = 0, want_b = (ssize_t)(want * 8);
        char* dst = (char*)rin.data();
        while (got < want_b) {
            ssize_t r = read(fd_in, dst + got, (size_t)(want_b - got));
            if (r <= 0) { fprintf(stderr, "short read pass2\n"); exit(7); }
            got += r;
        }
        legal_level(ctx, rin.data(), want, lmin.data());
        for (size_t i = 0; i < want; ++i) {
            u64 S = rin[i], lm = lmin[i];
            if (!lm) continue;
            int hb = hib(S);
            while (lm) {
                int v = __builtin_ctzll(lm); lm &= lm - 1;
                if (v <= hb) continue;
                wbuf[(size_t)v * WBUF + wpos[v]++] = S | (u64(1) << v);
                if (wpos[v] == WBUF) flush(v);
            }
        }
        done += want;
    }
    for (int v = 0; v < V; ++v) flush(v);
    // verify every byte of the file was written
    for (int v = 0; v < V; ++v)
        if ((size_t)(wcur[v] - (off_t)(off[v] * 8)) != pcnt[v] * 8) {
            fprintf(stderr, "SPILL SHORT WRITE bucket %d\n", v); exit(7);
        }
    close(fd_in);
    close(fd_out);
    return tot;
}

// ==================================================================== stats
struct LevelStat {
    size_t size = 0, edges = 0;
    long long nP = 0, nN = 0;
    double Dbits = 0.0;
    u64 Dmod = 1;
    bool thr_exact = false;
    u64 best = 0; long long best_count = 0;
    double best_val = 0.0, runner_up = 0.0;
    double secs = 0;
};

// read a whole sorted level file into RAM
static void load_level(const std::string& p, std::vector<u64>& v) {
    int fd = open(p.c_str(), O_RDONLY);
    if (fd < 0) { fprintf(stderr, "cannot open %s\n", p.c_str()); exit(7); }
    off_t sz = lseek(fd, 0, SEEK_END);
    lseek(fd, 0, SEEK_SET);
    v.resize((size_t)(sz / 8));
    ssize_t got = 0; char* dst = (char*)v.data(); size_t nb = v.size() * 8;
    while (got < (ssize_t)nb) {
        ssize_t r = read(fd, dst + got, (size_t)(nb - got));
        if (r <= 0) { fprintf(stderr, "short load %s\n", p.c_str()); exit(7); }
        got += r;
    }
    close(fd);
}

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s --enum <n> [--spill=dir] [--maxlevel K]\n"
                        "       %s --solve <n> [--spill=dir] [--out f.json]\n",
                argv[0], argv[0]);
        return 2;
    }
    bool do_solve = std::string(argv[1]) == "--solve";
    bool do_enum  = std::string(argv[1]) == "--enum";
    if (!do_solve && !do_enum) { fprintf(stderr, "bad mode %s\n", argv[1]); return 2; }
    int n = atoi(argv[2]);
    std::string spill; int maxlevel = 1 << 30; const char* outpath = nullptr;
    bool resume = false;
    for (int i = 3; i < argc; ++i) {
        std::string a = argv[i];
        if (a.rfind("--spill=", 0) == 0) spill = a.substr(8);
        else if (a == "--spill") spill = "/tmp/lvl" + std::to_string(n);
        else if (a.rfind("--maxlevel=", 0) == 0) maxlevel = atoi(a.c_str() + 11);
        else if (a == "--maxlevel") maxlevel = atoi(argv[++i]);
        else if (a.rfind("--out=", 0) == 0) outpath = a.c_str() + 6;
        else if (a == "--out") outpath = argv[++i];
        else if (a == "--resume") resume = true;
    }
    invc_init();
    Ctx ctx; build_ctx(ctx, n);
    fprintf(stderr, "[n=%d] V=%d F=%zu build %.2fs  spill=%s\n", n, ctx.V,
            ctx.quads.size(), ctx.build_s, spill.empty() ? "(in-RAM)" : spill.c_str());
    fflush(stderr);
    Spiller sp(spill);

    // ================================================== forward enumeration
    double t_all = now_s();
    std::vector<size_t> lsizes, ledges;
    size_t total_states = 0;
    lsizes.push_back(1); ledges.push_back(ctx.V); total_states = 1;
    double t_enum = now_s();

    // --resume: adopt spill files that already exist, so a run killed mid-level
    // restarts at the first missing level instead of redoing hours of work.  A
    // level file is only trusted if its size is a multiple of 8 and does not
    // exceed the previous level's size (levels grow until the peak, so a larger
    // file means the run died partway through writing it).
    if (resume) {
        std::vector<size_t> szs;
        for (int k = 0; k <= ctx.V + 2; ++k) {
            struct stat stb;
            if (stat(sp.path(k).c_str(), &stb) != 0) break;
            if (stb.st_size <= 0 || (stb.st_size % 8) != 0) break;
            size_t sz = (size_t)(stb.st_size / 8);
            if (!szs.empty() && sz > szs.back()) break;   // partial file
            szs.push_back(sz);
        }
        if (!szs.empty()) {
            total_states = 0;
            for (size_t s : szs) total_states += s;
            lsizes = szs;
            ledges.assign(szs.size(), 0);
            double secs = 0;
            const char* rs = getenv("RESUME_SECS");
            if (rs) sscanf(rs, "%lf", &secs);
            t_enum = now_s() - secs;
            fprintf(stderr, "    [resume] adopted levels 0..%d, %zu states, %.0fs accounted\n",
                    (int)lsizes.size() - 1, total_states, secs);
        }
    }

    if (!spill.empty()) {
        // level 0
        std::vector<u64> a0(1, 0u);
        int fd = open(sp.path(0).c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) { fprintf(stderr, "cannot write %s\n", sp.path(0).c_str()); exit(7); }
        ssize_t w = write(fd, a0.data(), 8); (void)w; close(fd);
        for (int step = 0; step <= ctx.V && (int)lsizes.size() - 1 < maxlevel; ++step) {
            double t0 = now_s();
            size_t M = lsizes.back();
            std::vector<u64> A; load_level(sp.path(step), A);
            if (A.size() != M) { fprintf(stderr, "size mismatch level %d\n", step); exit(7); }
            std::vector<u64> LM(M);
            legal_level(ctx, A.data(), M, LM.data());
            size_t E = 0;
            for (size_t i = 0; i < M; ++i) E += __builtin_popcountll(LM[i]);
            ledges[step] = E;
            std::vector<u64>().swap(A); std::vector<u64>().swap(LM);
            if (E == 0) break;
            size_t bytes = 0;
            size_t ns = gen_next_spill(ctx, sp.path(step), M, sp.path(step + 1), &bytes);
            total_states += ns; lsizes.push_back(ns); ledges.push_back(0);
            fprintf(stderr, "    level %2d: %12zu states  out=%6.2f GB  edges=%12zu  "
                    "rss=%.2fGB peak=%.2fGB  %.1fs\n",
                    step + 1, ns, bytes / 1073741824.0, E, rss_cur_gb(), rss_peak_gb(), now_s() - t0);
            fflush(stderr);
        }
    } else {
        std::vector<u64> A(1, 0u), LM(1, ctx.FULL);
        for (int step = 0; step <= ctx.V && (int)lsizes.size() - 1 < maxlevel; ++step) {
            double t0 = now_s();
            size_t M = A.size();
            size_t E = 0;
            for (size_t i = 0; i < M; ++i) E += __builtin_popcountll(LM[i]);
            if (step) { ledges[step] = E; if (E == 0) break; }
            size_t pcnt[64] = {0};
            for (size_t i = 0; i < M; ++i) {
                u64 S = A[i], lm = LM[i];
                if (!lm) continue;
                int hb = hib(S);
                while (lm) { int v = __builtin_ctzll(lm); lm &= lm - 1; if (v > hb) ++pcnt[v]; }
            }
            size_t tot = 0;
            for (int v = 0; v < ctx.V; ++v) tot += pcnt[v];
            if (tot == 0) break;
            std::vector<u64> nxt(tot);
            size_t got = gen_next_inram(ctx, A.data(), LM.data(), M, nxt.data());
            if (got != tot) { fprintf(stderr, "gen mismatch %zu %zu\n", got, tot); exit(7); }
            total_states += tot; lsizes.push_back(tot); ledges.push_back(0);
            // verify sorted
            for (size_t i = 1; i < tot; ++i)
                if (nxt[i] <= nxt[i - 1]) { fprintf(stderr, "NOT SORTED at %zu\n", i); exit(7); }
            std::vector<u64> nlm(tot);
            legal_level(ctx, nxt.data(), tot, nlm.data());
            A.swap(nxt); LM.swap(nlm);
            fprintf(stderr, "    level %2d: %12zu states  edges=%12zu  rss=%.2fGB peak=%.2fGB  %.1fs\n",
                    step + 1, tot, E, rss_cur_gb(), rss_peak_gb(), now_s() - t0);
            fflush(stderr);
        }
    }
    double enum_s = now_s() - t_enum;
    int K = (int)lsizes.size() - 1;
    fprintf(stderr, "[n=%d] safe subsets=%zu K=%d enum %.2fs rss=%.2fGB peak=%.2fGB\n",
            n, total_states, K, enum_s, rss_cur_gb(), rss_peak_gb());
    {
        std::string s = "[";
        char b[32];
        for (int k = 0; k <= K; ++k) { snprintf(b, sizeof b, "%s%zu", k ? "," : "", lsizes[k]); s += b; }
        fprintf(stderr, "    level_sizes = %s]\n", s.c_str());
    }
    {
        // widest pair, and the RAM that 2 adjacent levels cost
        int arg = 0;
        for (int k = 1; k <= K; ++k) if (lsizes[k] > lsizes[arg]) arg = k;
        double two = (lsizes[arg] + (arg > 0 ? lsizes[arg - 1] : 0)) * 8.0 / 1073741824.0;
        double one = lsizes[arg] * 8.0 / 1073741824.0;
        double dp21 = (lsizes[arg] + (arg > 0 ? lsizes[arg - 1] : 0)) * 21.0 / 1073741824.0;
        fprintf(stderr, "    widest level = %d with %zu states\n", arg, lsizes[arg]);
        fprintf(stderr, "    8B x widest                      = %.2f GB\n", one);
        fprintf(stderr, "    8B x (widest + predecessor)      = %.2f GB\n", two);
        fprintf(stderr, "    21B x (widest + predecessor) [DP] = %.2f GB\n", dp21);
    }
    if (do_enum) {
        printf("{\n  \"n\": %d, \"V\": %d, \"F\": %zu,\n  \"n_safe_subsets\": %zu,\n",
               n, ctx.V, ctx.quads.size(), total_states);
        printf("  \"K\": %d,\n  \"level_sizes\": [", K);
        for (int k = 0; k <= K; ++k) printf("%s%zu", k ? "," : "", lsizes[k]);
        printf("],\n  \"level_edges\": [");
        for (int k = 0; k <= K; ++k) printf("%s%zu", k ? "," : "", ledges[k]);
        printf("],\n");
        printf("  \"peak_rss_gb\": %.3f,\n  \"enum_seconds\": %.2f\n}\n", rss_peak_gb(), enum_s);
        return 0;
    }

    // ========================================================== reverse DP
    // Level j is read by iteration j (as the parent A) and by iteration j-1
    // (as the child N).  The loop runs DESCENDING, so the LAST consumer of
    // level j is iteration j-1.  Therefore level k+1 is released at the top of
    // body k (after the edge pass), and the resident window is exactly
    // {levels[k], levels[k+1]}.  (This is the off-by-one the draft had.)
    std::vector<LevelStat> st(K + 1);
    size_t edge_total = 0;
    long long n_P = (long long)lsizes[K], n_N = 0;
    st[K].size = lsizes[K];
    st[K].nP = (long long)lsizes[K];

    double Dlog2 = 0.0;
    u64 Dmod = 1;

    // The child-value buffers must SURVIVE the iteration that fills them: they
    // hold level k+1's DP values and are read as the children in iteration k-1.
    // Declaring them inside the loop body zeroes them every iteration, which
    // silently collapses every value to 0 (this is the "best=0, n_P wrong"
    // symptom; the sizes and edge counts stay correct, which is why it hides).
    std::vector<u64>   num_next;    // numerator mod P1, indexed by position in L_{k+1}
    std::vector<int8_t> g_next;     // grundy of L_{k+1}
    std::vector<u32>   p_next;     // fixed-point p_rand of L_{k+1}
    // SEED for the terminal level K.  Every maximal set has no legal move, so
    // p_rand = 0 and grundy = 0, but the vector's value-initialisation is
    // (num=0, g=0, p=0) which is exactly right -- and it must be EXPLICIT,
    // because iteration K-1 reads these before anything writes them.  Getting
    // this wrong makes every grundy read as 0, i.e. every state looks like a
    // P position, and the n_P counts blow up while all values stay 0.
    num_next.assign(lsizes[K], 0u);
    g_next.assign(lsizes[K], (int8_t)0);
    p_next.assign(lsizes[K], 0u);

    double t_solve = now_s();
    for (int k = K - 1; k >= 0; --k) {
        double t_k = now_s();
        std::vector<u64> A, N;
        if (spill.empty()) {
            fprintf(stderr, "  --solve needs --spill (levels are not kept in RAM)\n");
            return 3;
        }
        load_level(sp.path(k), A);
        load_level(sp.path(k + 1), N);
        if (A.size() != lsizes[k] || N.size() != lsizes[k + 1]) {
            fprintf(stderr, "LEVEL %d SIZE MISMATCH\n", k); exit(6);
        }
        size_t M = A.size();
        std::vector<u64> LMA(M);
        legal_level(ctx, A.data(), M, LMA.data());

        // NOTE: num_next / g_next / p_next are declared OUTSIDE the loop, above.
        // Re-declaring them here would shadow them, so the swap below would
        // write into the shadow and the edge pass would read the stale outer
        // copy -- which reproduces exactly the "every value is 0" failure.
        std::vector<uint8_t> cnt(M, 0);
        std::vector<int8_t> gk(M, 0);
#pragma omp parallel for schedule(static)
        for (long long i = 0; i < (long long)M; ++i)
            cnt[(size_t)i] = (uint8_t)__builtin_popcountll(LMA[(size_t)i]);

        // L_k = lcm of the counts present, as a product of prime powers
        u64 Lk1 = 1;
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
                Llog2 += (double)e * log2((double)p);
            }
        }
        const u64 Dprev1 = Dmod;
        Dlog2 += Llog2;
        Dmod = mmul_s(Dmod, Lk1);

        const u64* NN = num_next.data();
        const int8_t* GN = g_next.data();
        const u32* PN = p_next.data();
        const u64* Np = N.data();
        const size_t Nsz = N.size();

        std::vector<u64> numk(M, 0u);
        std::vector<u64> psum(M, 0u);
        std::vector<u32> pk(M, 0u);
        if (getenv("STREAMDBG") && k >= atoi(getenv("STREAMDBG"))) {
            size_t nn = std::min<size_t>(6, Nsz);
            fprintf(stderr, "   [pre k=%d] M=%zu Nsz=%zu num_next[0..%zu]=", k, M, Nsz, nn ? nn - 1 : 0);
            for (size_t t = 0; t < nn; ++t) fprintf(stderr, "%llu ", (unsigned long long)num_next[t]);
            fprintf(stderr, " g_next=");
            for (size_t t = 0; t < nn; ++t) fprintf(stderr, "%d ", (int)g_next[t]);
            fprintf(stderr, " p_next=");
            for (size_t t = 0; t < nn; ++t) fprintf(stderr, "%u ", p_next[t]);
            fprintf(stderr, "\n   [pre k=%d] N[0..%zu]=", k, nn ? nn - 1 : 0);
            for (size_t t = 0; t < nn; ++t) fprintf(stderr, "%llu ", (unsigned long long)N[t]);
            fprintf(stderr, "\n");
        }
        double t_edge = now_s();
#pragma omp parallel for schedule(static)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            size_t i = (size_t)ii;
            u64 lm = LMA[(size_t)i];
            if (!lm) { numk[i] = 0; psum[i] = 0; gk[i] = 0; continue; }
            u64 a = A[(size_t)i];
            u64 s1 = 0, ps = 0;
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
                ps += PN[pos];
                ga |= (1ULL << GN[pos]);
            }
            numk[i] = s1; psum[i] = ps; gk[i] = (int8_t)__builtin_ctzll((~ga) & (ga + 1));
        }
        double t_e = now_s() - t_edge;
        // N dies here; A survives only for this iteration.
        std::vector<u64>().swap(N);

        LevelStat& s = st[k];
        s.size = M;
        for (size_t i = 0; i < M; ++i) s.edges += cnt[i];
        edge_total += s.edges;
        s.Dbits = Dlog2;
        s.Dmod = Dmod;
        s.thr_exact = (2.0 * Dlog2 < 61.0);

        long long nP = 0, nN = 0;
        double lbest_val = 0.0, lrunner = 0.0;
#pragma omp parallel for schedule(static) reduction(+ : nP, nN) reduction(max : lbest_val, lrunner)
        for (long long ii = 0; ii < (long long)M; ++ii) {
            size_t i = (size_t)ii;
            uint32_t c = cnt[i];
            if (!c) { pk[i] = 0u; numk[i] = 0; }
            else {
                u64 mean = psum[i] / c;
                u64 pv = (u64)SCALE - (mean > SCALE ? (u64)SCALE : mean);
                pk[i] = (u32)pv;
                u64 t1 = msub(mmul_s(Dprev1, c), numk[i]);
                numk[i] = mmul_s(mmul_s(t1, Lk1), g_invc1[c]);
            }
            if (gk[i] != 0) { ++nN; continue; }
            ++nP;
            double fv = (double)pk[i] / (double)SCALE;
            if (fv > lbest_val) { lrunner = lbest_val; lbest_val = fv; }
            else if (fv > lrunner) lrunner = fv;
        }
        u64 lbest = 0; bool have = false; long long lcount = 0;
        for (size_t i = 0; i < M; ++i) {
            if (gk[i] != 0 || cnt[i] == 0) continue;
            u64 n1 = numk[i];
            if (n1 == 0) continue;
            if (!have) { lbest = n1; have = true; lcount = 1; }
            else if (n1 > lbest) { lbest = n1; lcount = 1; }
            else if (n1 == lbest) ++lcount;
        }
        s.nP = nP; s.nN = nN; s.best = lbest; s.best_count = lcount;
        s.best_val = lbest_val; s.runner_up = lrunner;
        n_P += nP; n_N += nN;

        // roll level k+1 -> k
        num_next.swap(numk);
        g_next.swap(gk);
        p_next.swap(pk);
        if (num_next.size() != M || g_next.size() != M || p_next.size() != M) {
            fprintf(stderr, "BUFFER LENGTH BUG at k=%d: num=%zu g=%zu p=%zu want %zu\n",
                    k, num_next.size(), g_next.size(), p_next.size(), M);
            exit(9);
        }
        psum.clear(); psum.shrink_to_fit();
        cnt.clear(); cnt.shrink_to_fit();
        // release the parent level: it is only needed by THIS iteration
        A.clear(); A.shrink_to_fit();

        s.secs = now_s() - t_k;
        fprintf(stderr, "    k=%2d M=%12zu E=%12zu P=%9lld N=%9lld Dbits=%6.1f "
                "best=%.12f x%lld edge=%.2fs tot=%.2fs rss=%.2fGB peak=%.2fGB\n",
                k, M, s.edges, s.nP, s.nN, Dlog2, lbest_val, lcount, t_e, s.secs,
                rss_cur_gb(), rss_peak_gb());
        fflush(stderr);
    }
    double solve_s = now_s() - t_solve;
    double tot_s = now_s() - t_all;

    std::string o;
    char b[2048];
    o += "{\n  \"n\": " + std::to_string(n) + ",\n";
    o += "  \"V\": " + std::to_string(ctx.V) + ",\n";
    o += "  \"F\": " + std::to_string(ctx.quads.size()) + ",\n";
    o += "  \"method\": \"sort-free v-max partition (no sort, no edge-sized buffer); "
         "levels spilled to disk; 2-layer rolling window; num mod 2^61-1 (8B) + "
         "u32 fixed point (4B) + grundy (1B); lower_bound child index\",\n";
    o += "  \"n_safe_subsets\": " + std::to_string(total_states) + ",\n";
    o += "  \"level_sizes\": [";
    for (int k = 0; k <= K; ++k) { snprintf(b, sizeof b, "%s%zu", k ? "," : "", lsizes[k]); o += b; }
    o += "],\n";
    o += "  \"max_safe_size\": " + std::to_string(K) + ",\n";
    o += "  \"edge_total\": " + std::to_string(edge_total) + ",\n";
    o += "  \"n_P\": " + std::to_string(n_P) + ",\n";
    o += "  \"n_N\": " + std::to_string(n_N) + ",\n";
    int gmax_level = -1; double gmax_val = 0;
    for (int k = 0; k <= K; ++k) if (st[k].best_count > 0 && st[k].best_val > gmax_val) {
        gmax_val = st[k].best_val; gmax_level = k;
    }
    o += "  \"P_max_level\": " + std::to_string(gmax_level) + ",\n";
    o += "  \"P_max_filter_value\": \"" + std::to_string(gmax_val) + "\",\n";
    o += "  \"thresholds_exact_all_levels\": ";
    { bool ok = true; for (int k = 0; k <= K; ++k) if (!st[k].thr_exact) ok = false; o += (ok ? "true" : "false"); }
    o += ",\n  \"levels\": [\n";
    for (int k = 0; k <= K; ++k) {
        char frac[160] = "0";
        if (st[k].Dbits < 61.0 && st[k].best_count > 0) {
            u64 iv = mpow(st[k].Dmod, P1 - 2);
            snprintf(frac, sizeof frac, "%llu/%llu", (unsigned long long)mmul(st[k].best, iv),
                     (unsigned long long)st[k].Dmod);
        }
        snprintf(b, sizeof b,
                 "    {\"k\": %d, \"size\": %zu, \"edges\": %zu, \"n_P\": %lld, \"n_N\": %lld, "
                 "\"D_bits\": %.2f, \"thresholds_exact\": %s, \"best_frac_exact\": \"%s\", "
                 "\"best_count\": %lld, \"best_filter\": %.17g, \"secs\": %.2f}",
                 k, st[k].size, st[k].edges, st[k].nP, st[k].nN, st[k].Dbits,
                 st[k].thr_exact ? "true" : "false", frac, st[k].best_count, st[k].best_val, st[k].secs);
        o += b;
        if (k < K) o += ",";
        o += "\n";
    }
    o += "  ],\n";
    snprintf(b, sizeof b, "  \"timing_s\": {\"build\": %.2f, \"enumerate\": %.2f, \"solve\": %.2f, \"total\": %.2f},\n",
             ctx.build_s, enum_s, solve_s, tot_s);
    o += b;
    snprintf(b, sizeof b, "  \"peak_rss_gb\": %.3f\n}\n", rss_peak_gb());
    o += b;
    printf("%s", o.c_str());
    if (outpath) {
        FILE* f = fopen(outpath, "w");
        if (f) { fputs(o.c_str(), f); fclose(f); fprintf(stderr, "wrote %s\n", outpath); }
    }
    return 0;
}
