// Cycle 6 (shallow): find sigma_7 by computing Grundy numbers of ALL
// reachable safe k-stone positions on 7x7 for small k, using memoized DFS
// with a global Grundy memo shared across all positions.
//
// We enumerate all safe k-subsets (k = 1, 2, 3, ...), compute g(S) for each,
// and report the layer max. As soon as max == K - k (with K = 14), we have
// found sigma_7.
//
// Usage: saturation_n7_shallow.exe [memo_power] [max_layer]
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <unordered_map>
#include <vector>

static constexpr int N = 7, V = 49;
static std::vector<std::vector<uint64_t>> quads_by_pt;

static void build_geometry() {
    std::vector<std::array<long long, 4>> rows(V);
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++)
            rows[y * N + x] = {(long long)x * x + (long long)y * y, x, y, 1};
    quads_by_pt.assign(V, {});
    for (int a = 0; a < V - 3; a++)
        for (int b = a + 1; b < V - 2; b++)
            for (int c = b + 1; c < V - 1; c++)
                for (int d = c + 1; d < V; d++) {
                    long long m[4][4];
                    int ids[4] = {a, b, c, d};
                    for (int i = 0; i < 4; i++)
                        for (int j = 0; j < 4; j++)
                            m[i][j] = rows[ids[i]][j];
                    long long det = 0;
                    for (int i = 0; i < 4; i++) {
                        long long mm[3][3];
                        int ri = 0;
                        for (int r2 = 0; r2 < 4; r2++) {
                            if (r2 == i) continue;
                            int ci = 0;
                            for (int c2 = 1; c2 < 4; c2++) mm[ri][ci++] = m[r2][c2];
                            ri++;
                        }
                        long long det3 =
                            mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
                            - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
                            + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]);
                        det += (i % 2 == 0 ? 1 : -1) * m[i][0] * det3;
                    }
                    if (det == 0) {
                        uint64_t mask = (1ULL << a) | (1ULL << b) | (1ULL << c) | (1ULL << d);
                        quads_by_pt[a].push_back(mask);
                        quads_by_pt[b].push_back(mask);
                        quads_by_pt[c].push_back(mask);
                        quads_by_pt[d].push_back(mask);
                    }
                }
    int cnt = 0;
    for (int i = 0; i < V; i++) cnt += (int)quads_by_pt[i].size();
    fprintf(stderr, "n=7 V=49 forbidden quads built (sum per-point=%d)\n", cnt / 4);
}

static inline bool legal(uint64_t occ, int v) {
    uint64_t mask = occ | (1ULL << v);
    for (uint64_t q : quads_by_pt[v])
        if ((q & mask) == q) return false;
    return true;
}

// ---- memoized Grundy ----
struct Memo {
    std::vector<uint64_t> keys;
    std::vector<uint8_t> vals;
    size_t mask;
    size_t used = 0;
    explicit Memo(unsigned power)
        : keys(size_t{1} << power, 0), vals(size_t{1} << power, 255),
          mask((size_t{1} << power) - 1) {}
    static inline uint64_t mix(uint64_t x) {
        x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27; x *= 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    inline int get(uint64_t k) const {
        size_t i = mix(k) & mask;
        while (vals[i] != 255) {
            if (keys[i] == k) return vals[i];
            i = (i + 1) & mask;
        }
        return -1;
    }
    inline void put(uint64_t k, uint8_t v) {
        size_t i = mix(k) & mask;
        while (vals[i] != 255) {
            if (keys[i] == k) { vals[i] = v; return; }
            i = (i + 1) & mask;
        }
        keys[i] = k; vals[i] = v; ++used;
        if (used * 10 > keys.size() * 8) { fprintf(stderr, "memo overflow\n"); exit(1); }
    }
};

static Memo* memo;

static int grundy(uint64_t root) {
    std::vector<uint64_t> st_occ, st_rem, st_seen;
    st_occ.push_back(root);
    st_rem.push_back(~0ULL);
    st_seen.push_back(0);
    while (!st_occ.empty()) {
        uint64_t cur = st_occ.back();
        if (st_rem.back() == ~0ULL) {
            int cached = memo->get(cur);
            if (cached >= 0) {
                st_occ.pop_back(); st_rem.pop_back(); st_seen.pop_back();
                if (!st_occ.empty() && cached < 64)
                    st_seen.back() |= (1ULL << cached);
                continue;
            }
            st_rem.back() = ((1ULL << V) - 1) ^ cur;
        }
        uint64_t& rem = st_rem.back();
        bool pushed = false;
        while (rem) {
            int v = __builtin_ctzll(rem);
            rem &= rem - 1;
            if (!legal(cur, v)) continue;
            uint64_t child = cur | (1ULL << v);
            int cg = memo->get(child);
            if (cg >= 0) {
                if (cg < 64) st_seen.back() |= (1ULL << cg);
            } else {
                st_occ.push_back(child);
                st_rem.push_back(~0ULL);
                st_seen.push_back(0);
                pushed = true;
                break;
            }
        }
        if (pushed) continue;
        uint64_t seen = st_seen.back();
        int g = 0;
        while (g < 64 && ((seen >> g) & 1)) g++;
        memo->put(cur, (uint8_t)g);
        st_occ.pop_back(); st_rem.pop_back(); st_seen.pop_back();
        if (!st_occ.empty() && g < 64)
            st_seen.back() |= (1ULL << g);
    }
    return memo->get(root);
}


int main(int argc, char** argv) {
    unsigned memo_pow = argc > 1 ? (unsigned)atoi(argv[1]) : 27;
    int max_layer = argc > 2 ? atoi(argv[2]) : 4;
    const int K = 14;
    build_geometry();
    memo = new Memo(memo_pow);
    auto t0 = std::chrono::steady_clock::now();

    printf("{\"n\": 7, \"K\": %d, \"layers\": [\n", K);
    bool first = true;
    for (int k = 1; k <= max_layer; k++) {
        // enumerate all safe k-subsets via DFS from empty
        std::vector<uint64_t> layer_positions;
        std::vector<uint64_t> st_occ, st_rem;
        st_occ.push_back(0);
        st_rem.push_back((1ULL << V) - 1);
        while (!st_occ.empty()) {
            uint64_t cur = st_occ.back();
            uint64_t& rem = st_rem.back();
            int pc = __builtin_popcountll(cur);
            if (pc == k) {
                layer_positions.push_back(cur);
                st_occ.pop_back(); st_rem.pop_back();
                continue;
            }
            bool pushed = false;
            while (rem) {
                int v = __builtin_ctzll(rem);
                rem &= rem - 1;
                if (!legal(cur, v)) continue;
                st_occ.push_back(cur | (1ULL << v));
                st_rem.push_back((1ULL << V) - 1);
                pushed = true;
                break;
            }
            if (!pushed) { st_occ.pop_back(); st_rem.pop_back(); }
        }
        // compute Grundy for each
        int max_g = -1;
        long long sum_g = 0;
        std::vector<int> hist(64, 0);
        for (uint64_t pos : layer_positions) {
            int g = grundy(pos);
            if (g > max_g) max_g = g;
            sum_g += g;
            if (g < 64) hist[g]++;
        }
        auto t1 = std::chrono::steady_clock::now();
        double sec = std::chrono::duration<double>(t1 - t0).count();
        int ceiling = K - k;
        bool saturated = (max_g == ceiling);
        printf("%s{\"k\": %d, \"count\": %zu, \"max_g\": %d, \"ceiling\": %d, "
               "\"saturated\": %s, \"mean_g\": %.3f, \"memo_used\": %zu, \"seconds\": %.1f}",
               first ? "" : ",\n", k, layer_positions.size(), max_g, ceiling,
               saturated ? "true" : "false", (double)sum_g / layer_positions.size(),
               memo->used, sec);
        fprintf(stderr, "k=%d: %zu positions, max_g=%d, ceiling=%d, saturated=%d (%.1fs)\n",
                k, layer_positions.size(), max_g, ceiling, (int)saturated, sec);
        first = false;
        if (saturated) {
            fprintf(stderr, ">>> sigma_7 = %d found <<<\n", k);
            break;
        }
    }
    printf("\n]}\n");
    return 0;
}

