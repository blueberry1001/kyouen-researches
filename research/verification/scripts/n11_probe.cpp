// Measure the n=11 state space exactly, layer by layer.
//
// For the 11x11 board we need to know, before designing the solver, how large
// the reachable state space actually is. The v-max partition generates each
// level already sorted and deduplicated (see round5_prand_stream.cpp), so the
// count is exact and needs no sort of the edge list.
//
//   build: 4-point forbidden sets from the integer determinant
//   level k+1 = { S | {u} : S in level k, u in L(S) } deduplicated
//
// Levels spill to disk so the peak RAM stays proportional to one level.
//
// Usage: n11_probe --enum 11 --spill=/tmp/n11 [--maxlevel K]
#include "kc_core.h"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>

#ifdef _OPENMP
#include <omp.h>
#endif

using kc::u64;
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

// ------------------------------------------------------------ level storage
struct Spill {
    std::string dir;
    bool on = false;
    explicit Spill(std::string d) : dir(std::move(d)) { on = !dir.empty(); }
    std::string path(int k) const {
        return dir + "/level_" + std::to_string(k) + ".occ";
    }
    void write(int k, const std::vector<u64>& v) const {
        if (!on) return;
        std::string p = path(k);
        FILE* f = fopen(p.c_str(), "wb");
        if (!f) { fprintf(stderr, "spill open failed %s\n", p.c_str()); exit(9); }
        if (!v.empty() && fwrite(v.data(), 8, v.size(), f) != v.size()) {
            fprintf(stderr, "spill write short\n"); exit(9);
        }
        fclose(f);
    }
    std::vector<u64> read(int k) const {
        std::vector<u64> v;
        if (!on) return v;
        std::string p = path(k);
        FILE* f = fopen(p.c_str(), "rb");
        if (!f) return v;
        fseek(f, 0, SEEK_END);
        long n = ftell(f) / 8;
        fseek(f, 0, SEEK_SET);
        v.resize((size_t)n);
        if (n && fread(v.data(), 8, (size_t)n, f) != (size_t)n) {
            fprintf(stderr, "spill read short\n"); exit(9);
        }
        fclose(f);
        return v;
    }
};

// Legal moves for every state in a level, given the forbidden-4-set list.
// Same O(F) pass the other solvers use; the legal mask is NOT monotone along
// an edge, so this pass cannot be skipped.
static std::vector<u64> legal_level(const Board& B,
                                    const std::vector<std::vector<u64>>& tpp,
                                    const std::vector<u64>& A) {
    std::vector<u64> out(A.size());
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)A.size(); ++i) {
        u64 occ = A[(size_t)i], lm = 0;
        u64 e = B.full & ~occ;
        while (e) {
            int p = __builtin_ctzll(e);
            e &= e - 1;
            bool ok = true;
            for (u64 t : tpp[p]) if ((occ & t) == t) { ok = false; break; }
            if (ok) lm |= u64(1) << p;
        }
        out[(size_t)i] = lm;
    }
    return out;
}

int main(int argc, char** argv) {
    int n = 0, maxlevel = 1 << 30;
    std::string spill;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--enum") { if (i + 1 < argc) n = atoi(argv[++i]); }
        else if (a.rfind("--spill=", 0) == 0) spill = a.substr(8);
        else if (a == "--spill") spill = argv[++i];
        else if (a.rfind("--maxlevel=", 0) == 0) maxlevel = atoi(a.c_str() + 11);
        else if (a == "--maxlevel") maxlevel = atoi(argv[++i]);
    }
    if (n <= 0) { fprintf(stderr, "usage: --enum <n> [--spill=dir] [--maxlevel K]\n"); return 2; }

    double t0 = now_s();
    Board B;
    kc::build_square(B, n);
    std::vector<std::vector<u64>> tpp((size_t)B.V);
    for (u64 q : B.quads)
        for (int p = 0; p < B.V; ++p)
            if (q & (u64(1) << p)) tpp[(size_t)p].push_back(q & ~(u64(1) << p));
    fprintf(stderr, "[n=%d] V=%d F=%zu build %.1fs rss=%ldMB\n",
            n, B.V, B.quads.size(), now_s() - t0, rss_mb());
    fflush(stderr);

    if (!spill.empty()) { char c[512]; snprintf(c, sizeof c, "mkdir -p %s", spill.c_str());
                           if (system(c) != 0) { fprintf(stderr, "mkdir failed\n"); return 9; } }
    Spill sp(spill);

    // level 0
    std::vector<u64> cur{0};
    std::vector<u64> curLM = legal_level(B, tpp, cur);
    sp.write(0, cur);
    std::vector<size_t> sizes{1};
    u64 total = 1;
    fprintf(stderr, "  level 0: %zu states (%.1fs)\n", cur.size(), now_s() - t0);
    fflush(stderr);

    for (int k = 0; k < maxlevel && !cur.empty(); ++k) {
        double tk = now_s();
        std::vector<u64> nxt;
        // v-max partition: for each v, the children whose top bit is v come
        // from parents with bit v clear. Concatenating v in ascending order
        // yields a sorted, duplicate-free list, so no sort is needed.
        // Within a fixed v the parents are visited in their stored order, and
        // cur[i] | bit is monotone in cur[i], so each v-block is sorted iff
        // the level is. Sorting each block defensively is cheap next to the
        // full sort, and makes the v-block property hold even if a level
        // arrived unsorted from an earlier fallback.
        nxt.reserve(cur.size() * 2);
        for (int v = 0; v < B.V; ++v) {
            u64 bit = u64(1) << v;
            size_t begin = nxt.size();
            for (size_t i = 0; i < cur.size(); ++i) {
                // v must be the TOP bit of the child, so the parent carries no
                // bit at or above v: cur[i] >> v == 0, i.e. cur[i] < bit.
                // Testing only `cur[i] & bit` is wrong: a parent with a higher
                // bit would re-emit the same child at that higher v, and the
                // level would come out both unsorted and duplicated.
                if (cur[i] >= bit) continue;
                if (!(curLM[i] & bit)) continue;
                nxt.push_back(cur[i] | bit);
            }
            if (nxt.size() - begin > 1 && !std::is_sorted(nxt.begin() + (long)begin, nxt.end()))
                std::sort(nxt.begin() + (long)begin, nxt.end());
        }
        // Safety: the construction above must already be sorted and unique.
        if (!std::is_sorted(nxt.begin(), nxt.end())) {
            fprintf(stderr, "  level %d NOT SORTED -- falling back to sort\n", k + 1);
            std::sort(nxt.begin(), nxt.end());
        }
        std::vector<u64> nxtLM = legal_level(B, tpp, nxt);
        sp.write(k + 1, nxt);
        sizes.push_back(nxt.size());
        total += nxt.size();
        fprintf(stderr, "  level %d: %zu states  edges~%zu  rss=%ldMB  %.1fs\n",
                k + 1, nxt.size(), [&]{ size_t e = 0; for (u64 m : curLM) e += __builtin_popcountll(m); return e; }(),
                rss_mb(), now_s() - tk);
        fflush(stderr);
        cur.swap(nxt);
        curLM.swap(nxtLM);
    }

    size_t widest = *std::max_element(sizes.begin(), sizes.end());
    int wk = (int)(std::max_element(sizes.begin(), sizes.end()) - sizes.begin());
    printf("{\n  \"n\": %d,\n  \"V\": %d,\n  \"F\": %zu,\n", n, B.V, B.quads.size());
    printf("  \"K\": %zu,\n  \"n_safe_subsets\": %llu,\n", sizes.size() - 1,
           (unsigned long long)total);
    printf("  \"level_sizes\": [");
    for (size_t i = 0; i < sizes.size(); ++i) printf("%s%zu", i ? "," : "", sizes[i]);
    printf("],\n");
    printf("  \"widest_level\": %d,\n  \"widest_size\": %zu,\n", wk, widest);
    printf("  \"bytes_8B_per_state\": %llu,\n", (unsigned long long)widest * 8ull);
    printf("  \"peak_rss_mb\": %ld,\n", rss_mb());
    printf("  \"enum_seconds\": %.1f\n}\n", now_s() - t0);
    return 0;
}
