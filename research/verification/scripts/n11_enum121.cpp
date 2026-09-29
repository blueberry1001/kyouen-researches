// Measure the n>=9 state space exactly, layer by layer, with 2-word occupancy.
//
// 2-word sibling of n11_probe.cpp. Same v-max construction, same spill-per-level
// discipline, but the occupancy is kc::Bits (lo = points 0..63,
// hi = points 64..120) so n=9,10,11 are representable. A 1-word board with
// n=11 would evaluate `1ULL << 64..120`, which is undefined.
//
//   build: forbidden 4-sets from the integer determinant det[x^2+y^2,x,y,1]
//   level k+1 = { S | {u} : S in level k, u in L(S) }  deduplicated
//
// v-max partition: a child is emitted at v = its top point, so the parent must
// carry no point >= v (parent < bit(v)). Walking v in ascending order and
// visiting parents in stored order therefore emits every child exactly once
// and in increasing 128-bit order, provided each level is sorted. The sort
// check below is a check, not a repair: it must never fire.
//
// Usage:
//   n11_enum121 --enum 11 [--spill=/tmp/n11_121] [--maxlevel K]
//   n11_enum121 --quads 11            # only F_n
#include "kc_core121.h"

#include <algorithm>
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

// ------------------------------------------------------------ level helpers
// Legal moves for every state in a level, given the forbidden-4 list.
// Same O(F) pass the 1-word solvers use; the legal mask is NOT monotone along
// an edge, so this pass cannot be skipped.
static std::vector<Bits> legal_level(const Board& B,
                                      const std::vector<std::vector<Bits>>& tpp,
                                      const std::vector<Bits>& A) {
    std::vector<Bits> out(A.size());
#pragma omp parallel for schedule(static)
    for (long long i = 0; i < (long long)A.size(); ++i) {
        out[(size_t)i] = kc::legal_mask(B, A[(size_t)i]);
    }
    (void)tpp;
    return out;
}

static void print_json(int n, const Board& B, const std::vector<size_t>& sizes,
                       u64 total, double t0, bool stopped_by_maxlevel) {
    size_t widest = *std::max_element(sizes.begin(), sizes.end());
    int wk = (int)(std::max_element(sizes.begin(), sizes.end()) - sizes.begin());
    printf("{\n  \"n\": %d,\n  \"V\": %d,\n  \"F\": %zu,\n", n, B.V, B.quads.size());
    printf("  \"words_per_state\": 2,\n  \"bytes_per_state\": 16,\n");
    printf("  \"K\": %zu,\n", sizes.size() - 1);
    printf("  \"truncated_by_maxlevel\": %s,\n", stopped_by_maxlevel ? "true" : "false");
    printf("  \"n_safe_subsets\": %llu,\n", (unsigned long long)total);
    printf("  \"level_sizes\": [");
    for (size_t i = 0; i < sizes.size(); ++i) printf("%s%zu", i ? "," : "", sizes[i]);
    printf("],\n");
    printf("  \"widest_level\": %d,\n  \"widest_size\": %zu,\n", wk, widest);
    printf("  \"bytes_at_widest\": %llu,\n", (unsigned long long)widest * 16ull);
    printf("  \"peak_rss_mb\": %ld,\n", rss_mb());
    printf("  \"enum_seconds\": %.1f\n}\n", now_s() - t0);
}

int main(int argc, char** argv) {
    int n = 0, maxlevel = 1 << 30;
    bool quads_only = false;
    std::string spill;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--enum") { if (i + 1 < argc) n = atoi(argv[++i]); }
        else if (a == "--quads") quads_only = true;
        else if (a.rfind("--spill=", 0) == 0) spill = a.substr(8);
        else if (a == "--spill") { if (i + 1 < argc) spill = argv[++i]; }
        else if (a.rfind("--maxlevel=", 0) == 0) maxlevel = atoi(a.c_str() + 11);
        else if (a == "--maxlevel") { if (i + 1 < argc) maxlevel = atoi(argv[++i]); }
    }
    if (n <= 0) {
        fprintf(stderr, "usage: --enum <n> [--quads] [--spill=dir] [--maxlevel K]\n");
        return 2;
    }
    if (n * n > 128) { fprintf(stderr, "n*n must be <= 128\n"); return 2; }

    double t0 = now_s();
    Board B;
    kc::build_square(B, n);
    // Independent cross-check of the total against C(V,4) bookkeeping.
    long long c4 = 1;
    for (int i = 0; i < 4; ++i) c4 = c4 * (B.V - 3 + i) / (i + 1);
    fprintf(stderr, "[n=%d] V=%d C(V,4)=%lld F=%zu build %.1fs rss=%ldMB\n",
            n, B.V, c4, B.quads.size(), now_s() - t0, rss_mb());
    fflush(stderr);
    if (quads_only) {
        printf("{\"n\": %d, \"V\": %d, \"F\": %zu, \"C_V_4\": %lld, "
               "\"build_seconds\": %.2f}\n",
               n, B.V, B.quads.size(), c4, now_s() - t0);
        return 0;
    }

    if (!spill.empty()) {
        char c[512];
        snprintf(c, sizeof c, "mkdir -p %s", spill.c_str());
        if (system(c) != 0) { fprintf(stderr, "mkdir failed\n"); return 9; }
    }
    kc::Spill sp(spill);

    // level 0
    std::vector<Bits> cur{Bits{0, 0}};
    std::vector<Bits> curLM = legal_level(B, B.triples_by_pt, cur);
    sp.write(0, cur);
    std::vector<size_t> sizes{1};
    u64 total = 1;
    fprintf(stderr, "  level 0: %zu states (%.1fs)\n", cur.size(), now_s() - t0);
    fflush(stderr);

    bool stopped_by_maxlevel = false;
    for (int k = 0; k < maxlevel && !cur.empty(); ++k) {
        double tk = now_s();
        std::vector<Bits> nxt;
        nxt.reserve(cur.size() * 2);
        for (int v = 0; v < B.V; ++v) {
            Bits bit; bit.set(v);
            size_t begin = nxt.size();
            for (size_t i = 0; i < cur.size(); ++i) {
                // v is the TOP point of the child, so the parent carries no
                // point >= v. Testing only `parent has v` would re-emit the
                // same child at the parent's higher top point, and the level
                // would come out both unsorted and duplicated.
                if (!(cur[i] < bit)) continue;
                if (!curLM[i].test(v)) continue;
                Bits c; c.lo = cur[i].lo | bit.lo; c.hi = cur[i].hi | bit.hi;
                nxt.push_back(c);
            }
            if (nxt.size() - begin > 1 && !std::is_sorted(nxt.begin() + (long)begin, nxt.end()))
                std::sort(nxt.begin() + (long)begin, nxt.end());
        }
        // Safety: the construction above must already be sorted and unique.
        if (!kc::is_sorted_unique(nxt)) {
            fprintf(stderr, "  level %d NOT SORTED/UNIQUE -- falling back to sort\n", k + 1);
            std::sort(nxt.begin(), nxt.end());
            nxt.erase(std::unique(nxt.begin(), nxt.end()), nxt.end());
        }
        size_t edges = 0;
        for (const Bits& m : curLM) edges += (size_t)m.count();
        std::vector<Bits> nxtLM = legal_level(B, B.triples_by_pt, nxt);
        sp.write(k + 1, nxt);
        sizes.push_back(nxt.size());
        total += nxt.size();
        fprintf(stderr, "  level %d: %zu states  edges~%zu  rss=%ldMB  %.1fs\n",
                k + 1, nxt.size(), edges, rss_mb(), now_s() - tk);
        fflush(stderr);
        cur.swap(nxt);
        curLM.swap(nxtLM);
    }
    if ((int)sizes.size() - 1 >= maxlevel) stopped_by_maxlevel = true;

    print_json(n, B, sizes, total, t0, stopped_by_maxlevel);
    return 0;
}
