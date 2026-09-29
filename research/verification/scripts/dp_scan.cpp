// Fast DP file scanner: compute p_rand summary from dp_*.bin files.
// Usage: dp_scan <spilldir> <n> --out=f.json
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#ifdef _OPENMP
#include <omp.h>
#endif

using u32 = std::uint32_t;
using u64 = std::uint64_t;
static constexpr u32 SCALE = 1u << 30;

struct __attribute__((packed)) DPVal { int8_t g; u32 p; };

int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s <spill> <n> [--out=f]\n", argv[0]); return 2; }
    std::string spill = argv[1];
    int n = atoi(argv[2]);
    std::string outpath;
    for (int i = 3; i < argc; ++i) {
        std::string a = argv[i];
        if (a.rfind("--out=", 0) == 0) outpath = a.substr(6);
    }

    // Discover DP files
    std::vector<size_t> sizes;
    for (int k = 0; k <= 80; ++k) {
        std::string p = spill + "/dp_" + std::to_string(k) + ".bin";
        struct stat st;
        if (stat(p.c_str(), &st) != 0) break;
        sizes.push_back((size_t)(st.st_size / sizeof(DPVal)));
    }
    int K = (int)sizes.size() - 1;
    if (K < 0) { fprintf(stderr, "no dp files\n"); return 3; }
    fprintf(stderr, "K=%d levels=%d total_states=", K, K + 1);
    size_t total = 0;
    for (size_t s : sizes) total += s;
    fprintf(stderr, "%zu\n", total);

    long long total_P = 0, total_N = 0;
    long long cnt_1_2 = 0, cnt_2_3 = 0, cnt_3_4 = 0;
    double global_best = 0; int global_best_k = -1; long long global_best_cnt = 0;

    std::string per_level_json = "[";

    for (int k = 0; k <= K; ++k) {
        std::string p = spill + "/dp_" + std::to_string(k) + ".bin";
        int fd = open(p.c_str(), O_RDONLY);
        if (fd < 0) { fprintf(stderr, "cannot open %s\n", p.c_str()); exit(7); }
        size_t ns = sizes[k];
        size_t CHUNK = 20000000; // 20M states = 100MB per chunk
        std::vector<DPVal> buf(CHUNK);
        long long np = 0, nn = 0;
        double best = 0; long long best_cnt = 0;
        long long l12 = 0, l23 = 0, l34 = 0;

        for (size_t done = 0; done < ns; ) {
            size_t want = std::min(CHUNK, ns - done);
            ssize_t got = 0, want_b = (ssize_t)(want * sizeof(DPVal));
            char* dst = (char*)buf.data();
            while (got < want_b) {
                ssize_t r = read(fd, dst + got, (size_t)(want_b - got));
                if (r <= 0) { fprintf(stderr, "short read\n"); exit(7); }
                got += r;
            }
#pragma omp parallel for reduction(+:np,nn,l12,l23,l34)
            for (long long i = 0; i < (long long)want; ++i) {
                const DPVal& d = buf[i];
                if (d.g != 0) { ++nn; continue; }
                ++np;
                u32 pv = d.p;
                if (pv > SCALE / 2) ++l12;
                if ((u64)pv * 3 > (u64)SCALE * 2) ++l23;
                if ((u64)pv * 4 > (u64)SCALE * 3) ++l34;
            }
            // serial best tracking
            for (size_t i = 0; i < want; ++i) {
                if (buf[i].g != 0) continue;
                double fv = (double)buf[i].p / (double)SCALE;
                if (fv > best) { best = fv; best_cnt = 1; }
                else if (fv == best && fv > 0) ++best_cnt;
            }
            done += want;
        }
        close(fd);
        total_P += np; total_N += nn;
        cnt_1_2 += l12; cnt_2_3 += l23; cnt_3_4 += l34;
        if (best > global_best) { global_best = best; global_best_k = k; global_best_cnt = best_cnt; }
        else if (best == global_best && best > 0) global_best_cnt += best_cnt;

        char b[512];
        snprintf(b, sizeof b, "%s{\"k\":%d,\"size\":%zu,\"n_P\":%lld,\"n_N\":%lld,"
                 "\"best_filter\":%.12f,\"best_count\":%lld}",
                 k ? "," : "", k, ns, np, nn, best, best_cnt);
        per_level_json += b;

        fprintf(stderr, "  k=%2d size=%12zu P=%10lld N=%10lld best=%.12f x%lld\n",
                k, ns, np, nn, best, best_cnt);
        fflush(stderr);
    }
    per_level_json += "]";

    fprintf(stderr, "\n=== n=%d p_rand SUMMARY ===\n", n);
    fprintf(stderr, "  total P=%lld N=%lld\n", total_P, total_N);
    fprintf(stderr, "  P_max ≈ %.12f at level %d x%lld\n", global_best, global_best_k, global_best_cnt);
    fprintf(stderr, "  P>1/2: %lld  P>2/3: %lld  P>3/4: %lld\n", cnt_1_2, cnt_2_3, cnt_3_4);

    char hdr[2048];
    snprintf(hdr, sizeof hdr,
        "{\n  \"n\": %d,\n  \"V\": 64,\n  \"F\": 14564,\n"
        "  \"method\": \"streaming DP grundy+p_rand 5B/state, 3-subset legal_one, mmap child masks\",\n"
        "  \"n_safe_subsets\": %zu,\n  \"max_safe_size\": %d,\n"
        "  \"n_P\": %lld,\n  \"n_N\": %lld,\n"
        "  \"P_max_filter_value\": \"%.12f\",\n  \"P_max_level\": %d,\n  \"P_max_n_attaining\": %lld,\n"
        "  \"P_gt_1_2\": %lld,\n  \"P_gt_2_3\": %lld,\n  \"P_gt_3_4\": %lld,\n",
        n, total, K, total_P, total_N,
        global_best, global_best_k, global_best_cnt,
        cnt_1_2, cnt_2_3, cnt_3_4);
    std::string o = std::string(hdr) + "  \"levels\": " + per_level_json + "\n}\n";
    printf("%s", o.c_str());
    if (!outpath.empty()) {
        FILE* f = fopen(outpath.c_str(), "w");
        if (f) { fputs(o.c_str(), f); fclose(f); fprintf(stderr, "wrote %s\n", outpath.c_str()); }
    }
    return 0;
}
