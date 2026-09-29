// Streaming p_rand DP solver for n=8.
// Memory-efficient: 5 B/state DP values (grundy u8 + p_rand u32 fixed-point),
// child-level state masks via mmap (OS pages), parent level streamed in chunks.
//
// Usage: stream_solve <n> --spill=dir [--out=f.json]
// Reads level_*.occ files produced by round5_prand_stream.cpp --enum.
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
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#ifdef _OPENMP
#include <omp.h>
#endif
#include "kc_core.h"

using kc::u64;
using u32 = std::uint32_t;

static double now_s() {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}
static double rss_cur_gb() {
    FILE* f = fopen("/proc/self/status", "r"); if (!f) return -1;
    char line[256]; double v = 0;
    while (fgets(line, sizeof line, f))
        if (strncmp(line, "VmRSS:", 6) == 0) { long long x; sscanf(line+6, "%lld", &x); v = x/1048576.0; break; }
    fclose(f); return v;
}
static double rss_peak_gb() {
    FILE* f = fopen("/proc/self/status", "r"); if (!f) return -1;
    char line[256]; long long v = -1;
    while (fgets(line, sizeof line, f))
        if (strncmp(line, "VmHWM:", 6) == 0) { sscanf(line+6, "%lld", &v); break; }
    fclose(f); return v/1048576.0;
}

static constexpr u32 SCALE = 1u << 30;

// ============================================================ context
struct Ctx {
    kc::Board board;
    int n = 0, V = 0;
    std::vector<u64> quads;
    u64 FULL = 0;
    u64 triple_blk[64][64][64] = {};
};
static void build_ctx(Ctx& ctx, int n) {
    kc::build_square(ctx.board, n);
    ctx.n = n; ctx.V = ctx.board.V; ctx.FULL = ctx.board.full;
    ctx.quads = ctx.board.quads;
    std::sort(ctx.quads.begin(), ctx.quads.end());
    memset(ctx.triple_blk, 0, sizeof(ctx.triple_blk));
    for (u64 q : ctx.quads) {
        int p[4], cnt = 0; u64 t = q;
        while (t) { p[cnt++] = __builtin_ctzll(t); t &= t-1; }
        if (cnt != 4) continue;
        ctx.triple_blk[p[0]][p[1]][p[2]] |= (u64(1)<<p[3]);
        ctx.triple_blk[p[0]][p[1]][p[3]] |= (u64(1)<<p[2]);
        ctx.triple_blk[p[0]][p[2]][p[3]] |= (u64(1)<<p[1]);
        ctx.triple_blk[p[1]][p[2]][p[3]] |= (u64(1)<<p[0]);
    }
}
static inline u64 legal_one(const Ctx& ctx, u64 occ) {
    u64 empty = ctx.FULL & ~occ, blocked = 0;
    u64 o1 = occ;
    while (o1) {
        int p1 = __builtin_ctzll(o1); o1 &= o1-1;
        u64 o2 = o1;
        while (o2) {
            int p2 = __builtin_ctzll(o2); o2 &= o2-1;
            u64 o3 = o2;
            while (o3) {
                int p3 = __builtin_ctzll(o3); o3 &= o3-1;
                blocked |= ctx.triple_blk[p1][p2][p3];
            }
        }
    }
    return empty & ~blocked;
}
static inline int hib(u64 x) { return x ? (63 - __builtin_clzll(x)) : -1; }

// ============================================================ DP value
struct __attribute__((packed)) DPVal {
    int8_t g;
    u32 p;    // fixed-point [0, SCALE]
};

// ============================================================ file helpers
static size_t file_states(const std::string& path) {
    struct stat st;
    if (stat(path.c_str(), &st) != 0) return 0;
    return (size_t)(st.st_size / 8);
}

static std::string dp_path(const std::string& dir, int k) {
    return dir + "/dp_" + std::to_string(k) + ".bin";
}

// Write DP values to disk (binary, 5 bytes per state: int8 g + u32 p)
static void save_dp(const std::string& path, const DPVal* vals, size_t n) {
    FILE* f = fopen(path.c_str(), "wb");
    if (!f) { fprintf(stderr, "cannot write %s\n", path.c_str()); exit(7); }
    fwrite(vals, sizeof(DPVal), n, f);
    fclose(f);
}

// Load DP values from disk
static void load_dp(const std::string& path, std::vector<DPVal>& vals, size_t n) {
    vals.resize(n);
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) { fprintf(stderr, "cannot read %s\n", path.c_str()); exit(7); }
    size_t got = fread(vals.data(), sizeof(DPVal), n, f);
    if (got != n) { fprintf(stderr, "short DP read %s: %zu/%zu\n", path.c_str(), got, n); exit(7); }
    fclose(f);
}

// ============================================================ mmap level
struct MappedLevel {
    int fd = -1;
    const u64* data = nullptr;
    size_t n = 0;
    void open(const std::string& path) {
        fd = ::open(path.c_str(), O_RDONLY);
        if (fd < 0) { fprintf(stderr, "cannot open %s\n", path.c_str()); exit(7); }
        struct stat st; fstat(fd, &st);
        n = (size_t)(st.st_size / 8);
        data = (const u64*)mmap(nullptr, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
        if (data == MAP_FAILED) { fprintf(stderr, "mmap fail %s\n", path.c_str()); exit(7); }
    }
    void close() {
        if (data && data != MAP_FAILED) munmap((void*)data, n * 8);
        if (fd >= 0) ::close(fd);
        data = nullptr; fd = -1; n = 0;
    }
    ~MappedLevel() { close(); }
};

int main(int argc, char** argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <n> --spill=dir [--out=f.json] [--chunk=N]\n", argv[0]);
        return 2;
    }
    int n = atoi(argv[1]);
    std::string spill, outpath;
    size_t CHUNK = 2000000;  // 2M states per chunk = 16 MB of masks
    for (int i = 2; i < argc; ++i) {
        std::string a = argv[i];
        if (a.rfind("--spill=", 0) == 0) spill = a.substr(8);
        else if (a.rfind("--out=", 0) == 0) outpath = a.substr(6);
        else if (a.rfind("--chunk=", 0) == 0) CHUNK = (size_t)atol(a.c_str() + 8);
    }
    if (spill.empty()) { fprintf(stderr, "need --spill=dir\n"); return 2; }

    Ctx ctx; build_ctx(ctx, n);
    fprintf(stderr, "[solve n=%d] V=%d F=%zu spill=%s\n", n, ctx.V, ctx.quads.size(), spill.c_str());
    fflush(stderr);

    // Discover levels
    std::vector<size_t> lsizes;
    for (int k = 0; k <= ctx.V + 2; ++k) {
        std::string p = spill + "/level_" + std::to_string(k) + ".occ";
        size_t sz = file_states(p);
        if (sz == 0) break;
        lsizes.push_back(sz);
    }
    if (lsizes.empty()) {
        fprintf(stderr, "no level files found in %s\n", spill.c_str());
        return 3;
    }
    int K = (int)lsizes.size() - 1;
    fprintf(stderr, "  K=%d level_sizes=[", K);
    for (int k = 0; k <= K; ++k) fprintf(stderr, "%s%zu", k ? "," : "", lsizes[k]);
    fprintf(stderr, "]\n");
    fprintf(stderr, "  total_states=%zu\n", std::accumulate(lsizes.begin(), lsizes.end(), (size_t)0));
    fflush(stderr);

    // Terminal level K: all p=0, g=0
    std::vector<DPVal> dp_next(lsizes[K]);
    for (auto& d : dp_next) { d.g = 0; d.p = 0; }

    double t0 = now_s();

    // Descending DP
    for (int k = K - 1; k >= 0; --k) {
        double tk = now_s();
        size_t Mk = lsizes[k], Mk1 = lsizes[k + 1];

        // mmap child level (k+1) state masks for binary search
        MappedLevel child_lvl;
        child_lvl.open(spill + "/level_" + std::to_string(k + 1) + ".occ");
        if (child_lvl.n != Mk1) {
            fprintf(stderr, "child size mismatch k=%d: %zu vs %zu\n", k, child_lvl.n, Mk1);
            exit(6);
        }

        // dp_next already holds level k+1's DP values (from previous iteration)
        // For the first iteration (k=K-1), these are all zeros (terminal).
        if (dp_next.size() != Mk1) {
            fprintf(stderr, "dp_next size mismatch k=%d: %zu vs %zu\n", k, dp_next.size(), Mk1);
            exit(6);
        }

        // Output DP for level k
        std::vector<DPVal> dp_k(Mk);

        // Stream level k in chunks
        std::vector<u64> buf(CHUNK);
        int fd_k = open((spill + "/level_" + std::to_string(k) + ".occ").c_str(), O_RDONLY);
        if (fd_k < 0) { fprintf(stderr, "cannot open level %d\n", k); exit(7); }

        long long nP = 0, nN = 0;
        double best_val = 0.0; size_t best_pos = 0; long long best_count = 0;
        size_t edges_total = 0;

        for (size_t done = 0; done < Mk; ) {
            size_t want = std::min(CHUNK, Mk - done);
            ssize_t got = 0, want_b = (ssize_t)(want * 8);
            char* dst = (char*)buf.data();
            while (got < want_b) {
                ssize_t r = read(fd_k, dst + got, (size_t)(want_b - got));
                if (r <= 0) { fprintf(stderr, "short read level %d\n", k); exit(7); }
                got += r;
            }

            // Process chunk
#pragma omp parallel for schedule(dynamic, 256) reduction(+:nP,nN,edges_total)
            for (long long ii = 0; ii < (long long)want; ++ii) {
                size_t i = (size_t)ii;
                u64 S = buf[i];
                u64 lm = legal_one(ctx, S);
                int deg = __builtin_popcountll(lm);
                edges_total += deg;
                DPVal out = {0, 0};
                if (deg == 0) {
                    // terminal: g=0, p=0
                } else {
                    u64 gm = 0;
                    u64 psum = 0;
                    while (lm) {
                        int v = __builtin_ctzll(lm); lm &= lm - 1;
                        u64 child = S | (u64(1) << v);
                        // binary search in child_lvl
                        size_t lo = 0, hi = child_lvl.n;
                        while (lo < hi) {
                            size_t mid = (lo + hi) / 2;
                            if (child_lvl.data[mid] < child) lo = mid + 1;
                            else hi = mid;
                        }
                        if (lo >= child_lvl.n || child_lvl.data[lo] != child) {
#pragma omp critical
                            { fprintf(stderr, "CHILD NOT FOUND k=%d S=%#llx child=%#llx\n",
                                      k, (unsigned long long)S, (unsigned long long)child); exit(4); }
                        }
                        const DPVal& cv = dp_next[lo];
                        gm |= (1ULL << cv.g);
                        psum += cv.p;
                    }
                    out.g = (int8_t)__builtin_ctzll((~gm) & (gm + 1));
                    u64 mean = psum / (u64)deg;
                    u64 pv = (u64)SCALE - (mean > SCALE ? (u64)SCALE : mean);
                    out.p = (u32)pv;
                }
                dp_k[done + i] = out;
                if (out.g == 0 && deg > 0) {
                    // P-position tracking (need serial section for best)
                }
            }
            done += want;
        }
        close(fd_k);
        child_lvl.close();

        // Count P/N and find best (serial pass over dp_k)
        for (size_t i = 0; i < Mk; ++i) {
            if (dp_k[i].g != 0) { ++nN; continue; }
            ++nP;
            double fv = (double)dp_k[i].p / (double)SCALE;
            if (fv > best_val) { best_val = fv; best_pos = i; best_count = 1; }
            else if (fv == best_val && fv > 0) ++best_count;
        }

        // Save DP values for this level (next iteration will use as dp_next)
        save_dp(dp_path(spill, k), dp_k.data(), Mk);
        dp_next = std::move(dp_k);

        fprintf(stderr, "  k=%2d M=%12zu E=%12zu P=%9lld N=%9lld best=%.12f x%lld  %.1fs rss=%.2fGB peak=%.2fGB\n",
                k, Mk, edges_total, nP, nN, best_val, best_count, now_s() - tk,
                rss_cur_gb(), rss_peak_gb());
        fflush(stderr);
    }
    double total_s = now_s() - t0;

    // Scan all DP files to find the global max p_rand among P-positions
    double global_best = 0.0;
    int global_best_k = -1;
    long long global_best_count = 0;
    size_t total_P = 0, total_N = 0;
    long long cnt_gt_1_2 = 0, cnt_gt_2_3 = 0, cnt_gt_3_4 = 0;
    // For 1/2: p > SCALE/2; for 2/3: 3*p > 2*SCALE; for 3/4: 4*p > 3*SCALE
    const u32 half = SCALE / 2;

    for (int k = 0; k <= K; ++k) {
        std::vector<DPVal> dp;
        load_dp(dp_path(spill, k), dp, lsizes[k]);
        long long np = 0, nn = 0;
        for (size_t i = 0; i < lsizes[k]; ++i) {
            if (dp[i].g != 0) { ++nn; continue; }
            ++np;
            u32 p = dp[i].p;
            if (p > half) ++cnt_gt_1_2;
            if ((u64)p * 3 > (u64)SCALE * 2) ++cnt_gt_2_3;
            if ((u64)p * 4 > (u64)SCALE * 3) ++cnt_gt_3_4;
            double fv = (double)p / (double)SCALE;
            if (fv > global_best) { global_best = fv; global_best_k = k; global_best_count = 1; }
            else if (fv == global_best && fv > 0) ++global_best_count;
        }
        total_P += np; total_N += nn;
    }

    fprintf(stderr, "\n=== n=%d p_rand SUMMARY ===\n", n);
    fprintf(stderr, "  total P=%zu N=%zu\n", total_P, total_N);
    fprintf(stderr, "  P_max ≈ %.12f at level %d x%lld\n", global_best, global_best_k, global_best_count);
    fprintf(stderr, "  P>1/2: %lld  P>2/3: %lld  P>3/4: %lld\n", cnt_gt_1_2, cnt_gt_2_3, cnt_gt_3_4);
    fprintf(stderr, "  solve time: %.1fs\n", total_s);
    fprintf(stderr, "  peak RSS: %.2f GB\n", rss_peak_gb());

    // Output JSON
    std::string o = "{\n";
    o += "  \"n\": " + std::to_string(n) + ",\n";
    o += "  \"V\": " + std::to_string(ctx.V) + ",\n";
    o += "  \"F\": " + std::to_string(ctx.quads.size()) + ",\n";
    o += "  \"method\": \"streaming DP: grundy(u8)+p_rand(u32 fixed-point) 5B/state, "
         "child masks via mmap, parent streamed in chunks, legal_one via 3-subset table\",\n";
    size_t total_states = std::accumulate(lsizes.begin(), lsizes.end(), (size_t)0);
    o += "  \"n_safe_subsets\": " + std::to_string(total_states) + ",\n";
    o += "  \"level_sizes\": [";
    for (int k = 0; k <= K; ++k) o += (k ? "," : "") + std::to_string(lsizes[k]);
    o += "],\n";
    o += "  \"max_safe_size\": " + std::to_string(K) + ",\n";
    o += "  \"n_P\": " + std::to_string(total_P) + ",\n";
    o += "  \"n_N\": " + std::to_string(total_N) + ",\n";
    char b[256];
    snprintf(b, sizeof b, "  \"P_max_filter_value\": \"%.12f\",\n", global_best); o += b;
    o += "  \"P_max_level\": " + std::to_string(global_best_k) + ",\n";
    snprintf(b, sizeof b, "  \"P_max_n_attaining\": %lld,\n", global_best_count); o += b;
    snprintf(b, sizeof b, "  \"P_gt_1_2\": %lld,\n", cnt_gt_1_2); o += b;
    snprintf(b, sizeof b, "  \"P_gt_2_3\": %lld,\n", cnt_gt_2_3); o += b;
    snprintf(b, sizeof b, "  \"P_gt_3_4\": %lld,\n", cnt_gt_3_4); o += b;
    snprintf(b, sizeof b, "  \"solve_seconds\": %.1f,\n", total_s); o += b;
    snprintf(b, sizeof b, "  \"peak_rss_gb\": %.3f\n", rss_peak_gb()); o += b;
    o += "}\n";

    printf("%s", o.c_str());
    if (!outpath.empty()) {
        FILE* f = fopen(outpath.c_str(), "w");
        if (f) { fputs(o.c_str(), f); fclose(f); fprintf(stderr, "wrote %s\n", outpath.c_str()); }
    }
    return 0;
}
