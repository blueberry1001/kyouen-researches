// Cycle 6: Grundy-ceiling saturation search on n=7.
//
// Two tasks:
//   A) Determine K_7 = max safe-set size reachable from the empty board.
//   B) Find the saturation onset sigma_7: the smallest layer k containing a
//      reachable position S with g(S) = K_7 - k.
//
// g(S) is computed by DFS with memo over the full game graph (no D4
// canonicalization). For task B we only need ONE witness per layer; we do a
// DFS from the empty board that, at each layer k, tries to prove
// g(S) = K_7 - k for the current S. The DFS explores children in an order
// that tries to cover child nimbers 0..m-1 quickly.
//
// Usage: saturation_cycle6.exe <n> [memo_power] [max_layers_to_scan]
// Prints JSON lines to stdout; progress to stderr.
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <unordered_map>
#include <vector>

static int N, V;
static std::vector<std::vector<uint64_t>> quads_by_pt;

static void build_geometry() {
    V = N * N;
    std::vector<std::array<long long, 4>> rows(V);
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++)
            rows[y * N + x] = {(long long)x * x + (long long)y * y, x, y, 1};
    quads_by_pt.assign(V, {});
    for (int a = 0; a < V - 3; a++)
        for (int b = a + 1; b < V - 2; b++)
            for (int c = b + 1; c < V - 1; c++)
                for (int d = c + 1; d < V; d++) {
                    // det of rows [x^2+y^2, x, y, 1] for a,b,c,d
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
    fprintf(stderr, "n=%d V=%d forbidden quads built\n", N, V);
}

static inline bool legal(uint64_t occ, int v) {
    uint64_t mask = occ | (1ULL << v);
    for (uint64_t q : quads_by_pt[v])
        if ((q & mask) == q) return false;
    return true;
}

// ---- Grundy solver with memo ----
struct Memo {
    std::vector<uint64_t> keys;
    std::vector<uint8_t> vals; // 255 = empty
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

// Grundy via explicit-stack DFS. Each frame: occ, remaining bits to scan,
// seen child-nimber bitmask. Frame states: fresh (rem==UNINIT) vs scanning.
static constexpr uint64_t UNINIT = ~0ULL;

static int grundy(uint64_t root) {
    std::vector<uint64_t> st_occ, st_rem, st_seen;
    st_occ.push_back(root);
    st_rem.push_back(UNINIT);
    st_seen.push_back(0);

    while (!st_occ.empty()) {
        uint64_t cur = st_occ.back();
        if (st_rem.back() == UNINIT) {
            int cached = memo->get(cur);
            if (cached >= 0) {
                st_occ.pop_back(); st_rem.pop_back(); st_seen.pop_back();
                if (!st_occ.empty() && cached < 64)
                    st_seen.back() |= (1ULL << cached);
                continue;
            }
            st_rem.back() = (V >= 64) ? ~cur : (((1ULL << V) - 1) ^ cur);
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
                st_rem.push_back(UNINIT);
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


// ---- Task A: find K_n (max reachable safe-set size) via memoized DFS ----
static std::unordered_map<uint64_t, int> maxsafe_memo;

static int max_safe_size(uint64_t occ) {
    auto it = maxsafe_memo.find(occ);
    if (it != maxsafe_memo.end()) return it->second;
    int pc = __builtin_popcountll(occ);
    int best = pc;
    uint64_t empty = (V >= 64) ? ~occ : (((1ULL << V) - 1) ^ occ);
    while (empty) {
        int v = __builtin_ctzll(empty);
        empty &= empty - 1;
        if (legal(occ, v)) {
            int sub = max_safe_size(occ | (1ULL << v));
            if (sub > best) best = sub;
            if (best == pc + (int)__builtin_popcountll(empty) + 1) break; // can't do better
        }
    }
    maxsafe_memo[occ] = best;
    return best;
}

// ---- Task B: saturation onset search ----
// For layer k (ascending), DFS over reachable k-stone positions; for each,
// compute g via memo and test g == K - k. Return first hit per layer.
// We cap the per-layer search by a node budget to stay cheap on large boards.
static uint64_t saturation_witness(int k, int K, long long budget, long long& visited) {
    // iterative DFS over subsets: walk from empty, at depth k test.
    std::vector<uint64_t> st_occ, st_rem;
    st_occ.push_back(0);
    st_rem.push_back((V >= 64) ? ~0ULL : ((1ULL << V) - 1));
    visited = 0;
    while (!st_occ.empty()) {
        uint64_t cur = st_occ.back();
        uint64_t& rem = st_rem.back();
        int pc = __builtin_popcountll(cur);
        if (pc == k) {
            ++visited;
            int g = grundy(cur);
            if (g == K - k) return cur;
            // do not descend deeper from a tested node
            st_occ.pop_back(); st_rem.pop_back();
            continue;
        }
        if (visited > budget) { return UINT64_MAX; } // budget exhausted
        bool pushed = false;
        while (rem) {
            int v = __builtin_ctzll(rem);
            rem &= rem - 1;
            if (!legal(cur, v)) continue;
            st_occ.push_back(cur | (1ULL << v));
            st_rem.push_back((V >= 64) ? ~0ULL : ((1ULL << V) - 1));
            pushed = true;
            break;
        }
        if (!pushed) { st_occ.pop_back(); st_rem.pop_back(); }
    }
    return 0; // not found
}

int main(int argc, char** argv) {
    N = argc > 1 ? atoi(argv[1]) : 7;
    unsigned memo_pow = argc > 2 ? (unsigned)atoi(argv[2]) : 27;
    long long budget = argc > 3 ? atoll(argv[3]) : 2000000;
    int K_given = argc > 4 ? atoi(argv[4]) : -1; // skip K computation if given
    build_geometry();
    memo = new Memo(memo_pow);
    auto t0 = std::chrono::steady_clock::now();

    int K;
    double secA;
    if (K_given > 0) {
        K = K_given;
        secA = 0.0;
        fprintf(stderr, "K_%d = %d (given, skipped)\n", N, K);
    } else {
        K = max_safe_size(0);
        auto t1 = std::chrono::steady_clock::now();
        secA = std::chrono::duration<double>(t1 - t0).count();
        fprintf(stderr, "K_%d = %d (%.1fs)\n", N, K, secA);
    }
    auto t1 = std::chrono::steady_clock::now();
    printf("{\"n\": %d, \"K\": %d, \"K_seconds\": %.2f,\n", N, K, secA);

    printf(" \"layers\": [");
    bool first = true;
    for (int k = 1; k <= K && k <= 6; k++) {
        long long visited = 0;
        uint64_t w = saturation_witness(k, K, budget, visited);
        auto t2 = std::chrono::steady_clock::now();
        double sec = std::chrono::duration<double>(t2 - t1).count();
        if (w != 0 && w != UINT64_MAX) {
            printf("%s{\"k\": %d, \"ceiling\": %d, \"found\": true, \"witness\": %llu, "
                   "\"visited\": %lld, \"seconds\": %.2f}",
                   first ? "" : ", ", k, K - k, (unsigned long long)w, visited, sec);
            fprintf(stderr, "layer %d: SATURATED (witness %llu, %lld visited, %.1fs)\n",
                    k, (unsigned long long)w, visited, sec);
            break; // onset found; deeper layers forced by theorem
        } else if (w == UINT64_MAX) {
            printf("%s{\"k\": %d, \"ceiling\": %d, \"found\": null, \"budget_exceeded\": true, "
                   "\"visited\": %lld, \"seconds\": %.2f}",
                   first ? "" : ", ", k, K - k, visited, sec);
            fprintf(stderr, "layer %d: budget exceeded after %lld (%.1fs)\n", k, visited, sec);
            break;
        } else {
            printf("%s{\"k\": %d, \"ceiling\": %d, \"found\": false, "
                   "\"visited\": %lld, \"seconds\": %.2f}",
                   first ? "" : ", ", k, K - k, visited, sec);
            fprintf(stderr, "layer %d: no ceiling position among %lld (%.1fs)\n", k, visited, sec);
        }
        first = false;
    }
    printf("], \"memo_used\": %zu}\n", memo->used);
    return 0;
}

