// round4_b591b.cpp -- Round4, second pass for B591,B592,B593,B596,B597,B598,B599
//
// New stages on top of round4_b591_dmax.cpp:
//   layercount <n> <k> <cap> <tcap>     exact/capped count of ALL safe k-sets
//   bfs        <n> <K> <maxbin> <floor> <cap> <tcap> [outjson]
//         enumerate the COMPLETE safe (K-1) and (K-floor) layers, BFS from the
//         maximum sets, and report for every (K-1)-set the exact shortest path
//         length to a maximum set inside G_{K-floor}.  Also cross-tabulates with
//         the A/B phase split (center in/out) used by B594/B595/B596.
//   cert       <n> <K> <coords>          saturation (circle/line capacity)
//         certificate for the inapproximability of one S.
//   climb      <n> <k> <K> <iters> <seed>  hill-climb max exact d_max at n=8
//
// Geometry = kc::det4 from the shared verified core. 128-bit occupancy.
// Integer only.

#include "kc_core.h"

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>
#include <chrono>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>

typedef unsigned __int128 u128;
typedef uint64_t u64;

static double now() {
    return std::chrono::duration<double>(
               std::chrono::steady_clock::now().time_since_epoch()).count();
}
static int popc(u128 m) {
    return __builtin_popcountll((u64)m) + __builtin_popcountll((u64)(m >> 64));
}
static inline bool has(u128 M, u128 t) { return (M & t) == t; }
static inline int bitid(u128 m) {
    u64 lo = (u64)m;
    return lo ? __builtin_ctzll(lo) : 64 + __builtin_ctzll((u64)(m >> 64));
}
static u128 rand_r_u128(unsigned* s) {
    u64 a = *s ? *s : 0x9E3779B97F4A7C15ULL, b = a;
    a ^= a << 13; a ^= a >> 7; a ^= a << 17;
    *s = (unsigned)a;
    return ((u128)a << 64) | (u128)b;
}

// ------------------------------------------------------------------ engine
struct Engine {
    int n = 0, V = 0;
    long long F = 0;
    std::vector<u128> quads;
    std::vector<int> pid, pos;
    std::vector<std::vector<u128>> qef, qea;
    std::vector<int> sufS;
    std::vector<int> pt_of_bit;  // bit index -> point id
};

static void build_geom(Engine& e, int n, const std::vector<int>& order) {
    e.n = n; e.V = n * n; e.F = 0;
    e.quads.clear();
    std::vector<std::array<long long, 4>> rows(e.V);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            rows[i] = {(long long)x * x + (long long)y * y, x, y, 1};
        }
    for (int a = 0; a < e.V - 3; ++a)
    for (int b = a + 1; b < e.V - 2; ++b)
    for (int c = b + 1; c < e.V - 1; ++c)
    for (int d = c + 1; d < e.V; ++d) {
        int ids[4] = {a, b, c, d};
        long long m[4][4];
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = rows[ids[i]][j];
        if (kc::det4(m) != 0) continue;
        u128 q = 0;
        for (int i = 0; i < 4; ++i) q |= (u128)1 << ids[i];
        e.quads.push_back(q);
        ++e.F;
    }
    e.pid = order;
    e.pos.assign(e.V, 0);
    for (int p = 0; p < e.V; ++p) e.pos[e.pid[p]] = p;
    e.qef.assign(e.V, {});
    e.qea.assign(e.V, {});
    for (u128 q : e.quads) {
        int ids[4]; int c = 0; u128 t = q;
        while (t) { ids[c++] = bitid(t); t &= t - 1; }
        for (int i = 0; i < 4; ++i) {
            int p = ids[i];
            u128 rest = q & ~((u128)1 << p);
            e.qea[e.pos[p]].push_back(rest);
            bool earlier = true;
            for (int j = 0; j < 4; ++j)
                if (ids[j] != p && e.pos[ids[j]] > e.pos[p]) earlier = false;
            if (earlier) e.qef[e.pos[p]].push_back(rest);
        }
    }
}
static inline bool conflicts_f(const Engine& e, int pos, u128 M) {
    for (u128 t : e.qef[pos]) if (has(M, t)) return true;
    return false;
}
static inline bool conflicts_a(const Engine& e, int pos, u128 M) {
    for (u128 t : e.qea[pos]) if (has(M, t)) return true;
    return false;
}
static inline bool has_legal_from(const Engine& e, int from, u128 M) {
    for (int p = from; p < e.V; ++p)
        if (!conflicts_f(e, p, M)) return true;
    return false;
}
static bool is_maximal(const Engine& e, u128 M) {
    for (int p = 0; p < e.V; ++p) {
        if (M & ((u128)1 << e.pid[p])) continue;
        if (!conflicts_a(e, p, M)) return false;
    }
    return true;
}
static bool is_safe(const Engine& e, u128 M) {
    for (u128 q : e.quads) if (has(M, q)) return false;
    return true;
}
static u128 parse_coords(const std::string& s, int n) {
    u128 M = 0;
    std::vector<int> d;
    for (size_t i = 0; i <= s.size(); ++i) {
        char ch = (i < s.size()) ? s[i] : ';';
        if (ch >= '0' && ch <= '9') { d.push_back(ch - '0'); continue; }
        if (ch == ',' || ch == ' ') continue;
        if (d.size() == 2) M |= (u128)1 << (d[1] * n + d[0]);
        d.clear();
    }
    return M;
}
static std::string coords(u128 S, int n) {
    std::string s = "[";
    bool f = true;
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x)
            if ((S >> (y * n + x)) & 1) {
                char b[32]; std::snprintf(b, sizeof b, "%s(%d,%d)", f ? "" : ",", x, y);
                s += b; f = false;
            }
    return s + "]";
}
static u128 d4(u128 S, int n, int t) {
    u128 out = 0;
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int id = y * n + x;
            if (!((S >> id) & 1)) continue;
            int nx = x, ny = y;
            switch (t) {
                case 0: nx = x; ny = y; break;
                case 1: nx = y; ny = n - 1 - x; break;
                case 2: nx = n - 1 - x; ny = n - 1 - y; break;
                case 3: nx = n - 1 - y; ny = x; break;
                case 4: nx = n - 1 - x; ny = y; break;
                case 5: nx = y; ny = y; break;
                case 6: nx = x; ny = n - 1 - y; break;
                case 7: nx = n - 1 - y; ny = n - 1 - x; break;
            }
            out |= (u128)1 << (ny * n + nx);
        }
    return out;
}
static int d4_orbit(u128 S, int n) {
    u128 o[8]; int c = 0;
    for (int t = 0; t < 8; ++t) {
        u128 v = d4(S, n, t);
        bool dup = false;
        for (int i = 0; i < c; ++i) if (o[i] == v) dup = true;
        if (!dup) o[c++] = v;
    }
    return c;
}

// ------------------------------------------------------------ layer enumer.
struct LayCtx {
    const Engine* e = nullptr;
    u128 M = 0;
    int k = 0;
    long long leaves = 0, nodes = 0, cap = 0;
    double t0 = 0, tcap = 0;
    bool stop = false;
    int dscan = 2;
    std::vector<u128>* out = nullptr;
    std::unordered_set<u64>* uset = nullptr;
};
static void dfs_lay(LayCtx& c, int start, int sz) {
    const Engine& e = *c.e;
    ++c.nodes;
    if ((c.nodes & 0xFFFFFFLL) == 0 && now() - c.t0 > c.tcap) { c.stop = true; return; }
    if (c.nodes > c.cap) { c.stop = true; return; }
    if (sz == c.k) {
        ++c.leaves;
        if (c.out) c.out->push_back(c.M);
        if (c.uset) c.uset->insert((u64)c.M | ((u64)(c.M >> 64) << 0) * 0u);
        return;
    }
    bool deep = (c.dscan == 0) || (c.dscan == 1 && sz >= c.k - 2) || (c.dscan == 2 && sz >= c.k - 3);
    for (int p = start; p < e.V; ++p) {
        if (sz + (e.V - p) < c.k) break;
        if (deep && p > start && !has_legal_from(e, p, c.M)) break;
        if (conflicts_f(e, p, c.M)) continue;
        u128 prev = c.M;
        c.M |= (u128)1 << e.pid[p];
        dfs_lay(c, p + 1, sz + 1);
        c.M = prev;
        if (c.stop) return;
    }
}

// ---------------------------------------------------------------- d_max BB
struct DmCtx {
    const Engine* e = nullptr;
    u128 S = 0, M = 0;
    int K = 0, best = 0;
    long long nodes = 0, cap = 0;
    double t0 = 0, tcap = 0;
    bool stop = false;
};
static void dfs_alpha(DmCtx& c, int start, int sz, int cnt) {
    const Engine& e = *c.e;
    ++c.nodes;
    if ((c.nodes & 0xFFFFFFLL) == 0 && now() - c.t0 > c.tcap) { c.stop = true; return; }
    if (c.nodes > c.cap) { c.stop = true; return; }
    if (sz == c.K) { if (cnt > c.best) c.best = cnt; return; }
    if (e.V - start < c.K - sz) return;
    if (cnt + std::min(c.K - sz, e.sufS[start]) <= c.best) return;
    for (int p = start; p < e.V; ++p) {
        if (c.K - sz > e.V - p) break;
        if (cnt + e.sufS[p] <= c.best) break;
        if (p > start && !has_legal_from(e, p, c.M)) break;
        if (conflicts_f(e, p, c.M)) continue;
        int id = e.pid[p];
        u128 prev = c.M;
        c.M |= (u128)1 << id;
        dfs_alpha(c, p + 1, sz + 1, cnt + (int)((c.S >> id) & 1));
        c.M = prev;
        if (c.stop) return;
    }
}
static int greedy_alpha(const Engine& e, u128 S, int K, unsigned seed = 12345u) {
    int bestOv = -1;
    std::vector<int> order(e.V);
    for (int trial = 0; trial < 40; ++trial) {
        for (int p = 0; p < e.V; ++p) order[p] = p;
        if (trial >= 8) {
            for (int p = e.V - 1; p > 0; --p) {
                int r = (int)(rand_r_u128(&seed) % (u128)(p + 1));
                std::swap(order[p], order[r]);
            }
        } else {
            int rot = trial, rev = (trial & 1);
            int idx = 0;
            for (int pass = 0; pass < 2; ++pass)
                for (int j = 0; j < e.V; ++j) {
                    int p = rev ? (e.V - 1 - j) : j;
                    p = (p + rot * 3) % e.V;
                    int id = e.pid[p];
                    bool inS = ((S >> id) & 1) != 0;
                    if (pass == 0 ? inS : !inS) order[idx++] = p;
                }
        }
        u128 M = 0;
        int sz = 0;
        for (int i = 0; i < e.V && sz < K; ++i) {
            int p = order[i];
            if (conflicts_a(e, p, M)) continue;
            M |= (u128)1 << e.pid[p];
            ++sz;
        }
        if (sz == K) { int ov = popc(S & M); if (ov > bestOv) bestOv = ov; }
    }
    return bestOv;
}
static int exact_dmax(Engine& e, u128 S, int K, long long cap, double tcap,
                      long long* nodes, bool* complete) {
    std::vector<int> order;
    for (int p = 0; p < e.V; ++p) if ((S >> e.pid[p]) & 1) order.push_back(e.pid[p]);
    for (int p = 0; p < e.V; ++p) if (!((S >> e.pid[p]) & 1)) order.push_back(e.pid[p]);
    build_geom(e, e.n, order);
    e.sufS.assign(e.V + 1, 0);
    for (int p = e.V - 1; p >= 0; --p)
        e.sufS[p] = e.sufS[p + 1] + (int)((S >> e.pid[p]) & 1);
    DmCtx c;
    c.e = &e; c.S = S; c.K = K; c.cap = cap; c.t0 = now(); c.tcap = tcap;
    c.best = greedy_alpha(e, S, K);
    if (c.best < 0) c.best = 0;
    dfs_alpha(c, 0, 0, 0);
    *nodes = c.nodes;
    *complete = !c.stop;
    if (!*complete) return -1;
    return popc(S) - c.best;
}

// ------------------------------------------------------------------ helpers
static std::vector<u64> read_bin8(const char* path, long long* bytes) {
    FILE* f = std::fopen(path, "rb");
    if (!f) { std::printf("cannot open %s\n", path); std::exit(2); }
    std::fseek(f, 0, SEEK_END);
    long long b = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    long long nrec = b / 8;
    std::vector<u64> v(nrec);
    if (std::fread(v.data(), 1, (size_t)b, f) != (size_t)b) std::exit(2);
    std::fclose(f);
    if (bytes) *bytes = b;
    return v;
}
// neighbours of a safe set inside the graph on sizes {k, k+1, ...}
static void neighbours(const Engine& e, u128 S, int k, int K, std::vector<u128>& out) {
    out.clear();
    // up: add one point
    for (int p = 0; p < e.V; ++p) {
        if (S & ((u128)1 << e.pid[p])) continue;
        if (k >= K) break;
        if (!conflicts_a(e, p, S)) out.push_back(S | ((u128)1 << e.pid[p]));
    }
    // down: remove one point
    if (k - 1 >= 1) {
        u128 t = S;
        while (t) {
            int p = bitid(t);
            t &= t - 1;
            out.push_back(S & ~((u128)1 << p));
        }
    }
}

// ============================================================================
int main(int argc, char** argv) {
    if (argc < 2) { std::printf("no stage\n"); return 1; }
    std::string stage = argv[1];

    // ------------------------------------------------------------ layercount
    if (stage == "layercount") {
        int n = std::atoi(argv[2]), k = std::atoi(argv[3]);
        long long cap = std::atoll(argv[4]);
        double tcap = std::atof(argv[5]);
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        Engine e; build_geom(e, n, o);
        LayCtx c; c.e = &e; c.k = k; c.cap = cap; c.t0 = now(); c.tcap = tcap;
        double t = now();
        dfs_lay(c, 0, 0);
        std::printf("{\"stage\":\"layercount\",\"n\":%d,\"k\":%d,\"F_n\":%lld,"
                    "\"count\":%lld,\"nodes\":%lld,\"sec\":%.2f,\"complete\":%s}\n",
                    n, k, e.F, c.leaves, c.nodes, now() - t, c.stop ? "false" : "true");
        return 0;
    }

    // ------------------------------------------------------------------- bfs
    if (stage == "bfs") {
        int n = std::atoi(argv[2]), K = std::atoi(argv[3]);
        const char* maxbin = argv[4];
        int floorK = std::atoi(argv[5]);
        long long cap = std::atoll(argv[6]);
        double tcap = std::atof(argv[7]);
        const char* outjson = (argc > 8) ? argv[8] : nullptr;
        double T0 = now();
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        Engine e; build_geom(e, n, o);
        double gsec = now() - T0;
        long long maxbytes = 0;
        std::vector<u64> mx = read_bin8(maxbin, &maxbytes);
        int center = (n / 2) * n + (n / 2);
        int nA = 0, nB = 0;
        for (u64 m : mx) { if (m & (1ULL << center)) ++nA; else ++nB; }

        // BFS from the maximum sets.  neighbours() only ever emits SAFE sets
        // (additions are filtered by conflicts_a), so no set-membership test is
        // needed and the BFS is exact and complete inside the size window.
        std::unordered_map<u64, int> dist;
        dist.reserve(1u << 20);
        std::vector<u128> qf;
        std::vector<u64> q;
        for (u64 m : mx) { dist[m] = 0; q.push_back(m); }
        long long edges = 0, reached = 0, skipped = 0, capsz = 0;
        double tb = now();
        for (size_t qi = 0; qi < q.size(); ++qi) {
            u64 cur = q[qi];
            int cc = __builtin_popcountll(cur);
            if (cc < floorK) continue;
            neighbours(e, (u128)cur, cc, K, qf);
            for (u128 nb : qf) {
                ++edges;
                int nc = popc(nb);
                if (nc < floorK || nc > K) continue;
                u64 lo = (u64)nb;
                if (dist.count(lo)) continue;
                if (q.size() >= (size_t)cap) { ++capsz; continue; }
                dist[lo] = dist[cur] + 1;
                q.push_back(lo);
                ++reached;
            }
        }
        double bfssec = now() - tb;
        long long nod1 = (long long)q.size() + edges;

        // per (K-1)-set report; split max sets into A (center in) / B (center out)
        long long tot = 0, reach = 0, unreach = 0;
        long long cls[3] = {0, 0, 0};            // 0: dA<dB, 1: dA>dB, 2: equal
        long long clsreach[3] = {0, 0, 0};
        long long sumd[3] = {0, 0, 0};
        long long dmaxclass[3] = {0, 0, 0};
        long long hist[64]; for (int i = 0; i < 64; ++i) hist[i] = 0;
        long long maximalcnt = 0, maximalreach = 0;
        long long worst_dA = -1, worst_dB = -1, worst_eq = -1;
        std::vector<u64> onlyK1; onlyK1.reserve(dist.size());
        for (auto& kv : dist)
            if (__builtin_popcountll(kv.first) == K - 1) onlyK1.push_back(kv.first);
        // The K-1 layer itself is small enough to enumerate exhaustively, so we
        // can report the true layer total and the sets the BFS never reaches.
        std::vector<u128> layK1;
        LayCtx cl; cl.e = &e; cl.cap = cap; cl.t0 = now(); cl.tcap = tcap; cl.out = &layK1; cl.k = K - 1;
        dfs_lay(cl, 0, 0);
        bool laycomplete = !cl.stop;
        long long layerK1_total = cl.leaves;
        long long unreachK1 = 0, layK1_reached = 0;
        for (u128 s : layK1) { if (dist.count((u64)s)) ++layK1_reached; else ++unreachK1; }
        for (u64 s : onlyK1) {
            int dA = 1 << 20, dB = 1 << 20;
            for (u64 m : mx) {
                int d = popc((u128)(s & ~m));
                if (m & (1ULL << center)) { if (d < dA) dA = d; }
                else { if (d < dB) dB = d; }
            }
            int cls_i = (dA < dB) ? 0 : (dA > dB) ? 1 : 2;
            ++cls[cls_i];
            if (dA > worst_dA) worst_dA = dA;
            if (dB > worst_dB) worst_dB = dB;
            if (dA == dB && dA > worst_eq) worst_eq = dA;
            ++tot;
            if (dmaxclass[cls_i] < dA) dmaxclass[cls_i] = dA;
            auto it = dist.find(s);
            if (it != dist.end()) {
                ++reach; ++clsreach[cls_i]; sumd[cls_i] += it->second;
                if (it->second < 64) hist[it->second]++;
            } else ++unreach;
            if (is_maximal(e, (u128)s)) {
                ++maximalcnt;
                if (it != dist.end()) ++maximalreach;
            }
        }
        // also: do the extreme equidistant sets reach?
        long long worsteq_unreach = 0, worsteq_total = 0;
        for (u64 s : onlyK1) {
            int dA = 1 << 20, dB = 1 << 20;
            for (u64 m : mx) {
                int d = popc((u128)(s & ~m));
                if (m & (1ULL << center)) { if (d < dA) dA = d; }
                else { if (d < dB) dB = d; }
            }
            if (dA == worst_eq) { ++worsteq_total; if (!dist.count(s)) ++worsteq_unreach; }
        }
        long long layerK1 = 0;
        for (auto& kv : dist) if (__builtin_popcountll(kv.first) == K - 1) ++layerK1;
        (void)layerK1; (void)tot; (void)reach; (void)unreach;
        std::printf("{\n  \"stage\": \"bfs\",\n  \"n\": %d, \"K\": %d, \"floorK\": %d,\n",
                    n, K, floorK);
        std::printf("  \"F_n\": %lld, \"geom_sec\": %.2f,\n", e.F, gsec);
        std::printf("  \"max_sets\": %zu, \"nA\": %d, \"nB\": %d,\n", mx.size(), nA, nB);
        std::printf("  \"bfs_sec\": %.2f, \"edges\": %lld, \"nodes_total\": %lld, "
                    "\"capped_out\": %ld, \"bfs_complete\": %s,\n",
                    bfssec, edges, nod1, capsz, capsz ? "false" : "true");
        std::printf("  \"layer_K-1_total\": %lld, \"layer_K-1_enum_complete\": %s,\n",
                    layerK1_total, laycomplete ? "true" : "false");
        std::printf("  \"layer_K-1_reached\": %lld, \"layer_K-1_unreached\": %lld,\n",
                    layK1_reached, unreachK1);
        std::printf("  \"dist_hist\": {");
        { bool f = true; for (int i = 0; i < 64; ++i) if (hist[i]) {
            std::printf("%s\"%d\": %lld", f ? "" : ", ", i, hist[i]); f = false; } }
        std::printf("},\n");
        std::printf("  \"maximal_Kminus1\": %lld, \"maximal_reachable\": %lld,\n",
                    maximalcnt, maximalreach);
        std::printf("  \"phase_classes\": {\"dA_lt_dB\": %ld, \"dA_gt_dB\": %ld, \"dA_eq_dB\": %ld},\n",
                    cls[0], cls[1], cls[2]);
        std::printf("  \"per_class_reachable\": [%ld, %ld, %ld],\n",
                    clsreach[0], clsreach[1], clsreach[2]);
        std::printf("  \"per_class_mean_dist_of_reached_hundredths\": [");
        for (int i = 0; i < 3; ++i)
            std::printf("%s%s", i ? ", " : "", clsreach[i] ?
                        std::to_string((long long)((100 * sumd[i]) / clsreach[i])).c_str() : "null");
        std::printf("],\n");
        std::printf("  \"per_class_max_dA\": [%ld, %ld, %ld],\n", dmaxclass[0], dmaxclass[1], dmaxclass[2]);
        std::printf("  \"worst_dA\": %ld, \"worst_dB\": %ld, \"worst_equidistant\": %ld,\n",
                    worst_dA, worst_dB, worst_eq);
        std::printf("  \"worst_equidistant_sets\": %ld, \"worst_equidistant_unreachable\": %ld,\n",
                    worsteq_total, worsteq_unreach);
        std::printf("  \"total_sec\": %.2f\n}\n", now() - T0);
        return 0;
    }

    // ------------------------------------------------------------------ cert
    // Saturation / circle-line capacity certificate.
    // cl(T) = smallest SAFE superset of T = fixpoint of "any forbidden quad with
    // 3 points in the set gains its 4th".  A forbidden quad is exactly 4 points
    // on one line or one circle, so this is literally a line/circle occupancy
    // saturation argument.  If |cl(T)| > K for every |T| = t, then no maximum
    // set contains t points of S, i.e. alpha(S) <= t-1 and d_max >= |S|-t+1.
    if (stage == "cert") {
        int n = std::atoi(argv[2]), K = std::atoi(argv[3]);
        u128 S = parse_coords(argv[4], n);
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        Engine e; build_geom(e, n, o);
        int ssize = popc(S);
        int center = (n / 2) * n + (n / 2);
        // index quads by their triple for fast closure
        // closure: repeat until fixpoint
        auto closure = [&](u128 T) {
            u128 C = T;
            bool ch = true;
            int rounds = 0;
            while (ch) {
                ch = false; ++rounds;
                for (u128 q : e.quads) {
                    if (has(C, q)) continue;
                    int inter = popc(C & q);
                    if (inter == 3) { C |= q; ch = true; }
                }
            }
            return std::make_pair(C, rounds);
        };
        // min over |T| = t of |cl(T)|, t = 1..ssize
        std::printf("{\n  \"stage\": \"cert\",\n  \"n\": %d, \"K\": %d, \"size_S\": %d,\n",
                    n, K, ssize);
        std::printf("  \"S_safe\": %s, \"S_maximal\": %s, \"S_d4_orbit\": %d,\n",
                    is_safe(e, S) ? "true" : "false",
                    is_maximal(e, S) ? "true" : "false", d4_orbit(S, n));
        std::printf("  \"coords\": \"%s\",\n", coords(S, n).c_str());
        std::vector<int> pts;
        { u128 t = S; while (t) { pts.push_back(bitid(t)); t &= t - 1; } }
        std::printf("  \"saturation_profile\": [\n");
        int global_min_over = -1;
        for (int t = 1; t <= ssize; ++t) {
            int best = 1 << 20; u128 bestT = 0;
            // enumerate all t-subsets
            std::vector<int> idx(t);
            for (int i = 0; i < t; ++i) idx[i] = i;
            long long cnt = 0;
            while (true) {
                u128 T = 0;
                for (int i = 0; i < t; ++i) T |= (u128)1 << pts[idx[i]];
                auto cl = closure(T);
                ++cnt;
                if (popc(cl.first) < best) { best = popc(cl.first); bestT = T; }
                int i = t - 1;
                while (i >= 0 && idx[i] == pts.size() - t + i) --i;
                if (i < 0) break;
                ++idx[i];
                for (int j = i + 1; j < t; ++j) idx[j] = idx[j - 1] + 1;
            }
            if (t == 1) global_min_over = best;
            std::printf("    {\"t\": %d, \"subsets\": %lld, \"min_closure\": %d, "
                        "\"argmin\": \"%s\"}%s\n",
                        t, cnt, best, coords(bestT, n).c_str(), t == ssize ? "" : ",");
        }
        std::printf("  ]\n}\n");
        return 0;
    }

    // ---------------------------------------------------------------- extend
    // For the (K-1) layer: how many sets are actually CONTAINED in a maximum
    // set (t(S) >= 1), and what is the multiplicity distribution t(S)?
    // This separates the true "neighbourhood of the maximum configurations"
    // from the bulk of the layer, which is what B597/B598 ratios measure.
    if (stage == "extend") {
        int n = std::atoi(argv[2]), K = std::atoi(argv[3]);
        const char* maxbin = argv[4];
        long long cap = std::atoll(argv[5]);
        double tcap = std::atof(argv[6]);
        const char* laybin = (argc > 7) ? argv[7] : nullptr;
        long long maxbytes = 0;
        std::vector<u64> mx = read_bin8(maxbin, &maxbytes);
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        Engine e; build_geom(e, n, o);
        // t(S) for every (K-1) subset of every maximum set
        std::vector<u128> layK1;
        if (laybin) {
            long long lb = 0;
            std::vector<u64> raw = read_bin8(laybin, &lb);
            for (u64 v : raw) if (__builtin_popcountll(v) == K - 1) layK1.push_back((u128)v);
        } else {
            LayCtx cl; cl.e = &e; cl.cap = cap; cl.t0 = now(); cl.tcap = tcap;
            cl.out = &layK1; cl.k = K - 1;
            dfs_lay(cl, 0, 0);
        }
        std::unordered_map<u64, int> t_of;
        t_of.reserve(layK1.size() * 2 + 16);
        for (u128 s : layK1) t_of[(u64)s] = 0;
        long long paircount = 0, missing = 0;
        for (u64 m : mx) {
            u128 t = (u128)m;
            while (t) {
                int p = bitid(t);
                t &= t - 1;
                u128 S = (u128)m & ~((u128)1 << p);
                auto it = t_of.find((u64)S);
                if (it == t_of.end()) { ++missing; continue; }
                ++it->second; ++paircount;
            }
        }
        long long n_ext = 0; long long hist[64]; for (int i = 0; i < 64; ++i) hist[i] = 0;
        long long sumt = 0;
        for (auto& kv : t_of) {
            if (kv.second >= 1) ++n_ext;
            if (kv.second < 64) hist[kv.second]++;
            sumt += kv.second;
        }
        int Km1 = K - 1;
        // exhaustive: the (K-1)-subsets of a maximum set are always safe
        std::printf("{\n  \"stage\": \"extend\",\n  \"n\": %d, \"K\": %d,\n", n, K);
        std::printf("  \"max_sets\": %zu, \"layer_K-1\": %zu, \"layer_complete\": %s,\n",
                    mx.size(), layK1.size(),
                    (laybin || layK1.size() > 0) ? "true" : "false");
        std::printf("  \"subsets_not_in_layer\": %ld,\n", missing);
        std::printf("  \"expected_pairs_A0_times_K\": %lld, \"actual_pairs\": %lld,\n",
                    (long long)mx.size() * K, paircount);
        std::printf("  \"contained_in_a_max_set\": %ld, \"not_contained\": %ld,\n",
                    n_ext, (long long)layK1.size() - n_ext);
        std::printf("  \"multiplicity_hist\": {");
        { bool f = true; for (int i = 0; i < 64; ++i) if (hist[i]) {
            std::printf("%s\"%d\": %lld", f ? "" : ", ", i, hist[i]); f = false; } }
        std::printf("},\n");
        // local neighbourhood ratio: N_ext / |M_n|  (vs the bulk ratio layer/|M_n|)
        std::printf("  \"bulk_ratio\": \"%lld/%zu\",\n", (long long)layK1.size(), mx.size());
        std::printf("  \"local_ratio_Next_over_A0\": \"%ld/%zu\",\n", n_ext, mx.size());
        std::printf("  \"local_ratio_numer\": %ld, \"local_ratio_denom\": %zu,\n", n_ext, mx.size());
        std::printf("  \"bulk_over_local\": %lld,\n",
                    n_ext ? (long long)layK1.size() / n_ext : -1);
        std::printf("  \"K_minus_1\": %d, \"sec\": %.2f\n}\n", Km1, 0.0);
        return 0;
    }

    // ---------------------------------------------------------------- cert2
    // How much of the d_max lower bound is explained PURELY by circle/line
    // saturation?  For every t-subset T of S:
    //   * closure:  |cl(T)| -- the smallest SAFE superset of T.  A forbidden
    //     quad is exactly 4 points on one line or one circle, so cl(T) > K
    //     certifies "no maximum set contains T" by a capacity argument alone.
    //   * inmax:    T is contained in at least one of the |M_n| maximum sets
    //     (the combinatorial truth, computed against the full pool).
    // Comparing the two counts measures how much the saturation argument
    // actually buys.
    if (stage == "cert2") {
        int n = std::atoi(argv[2]), K = std::atoi(argv[3]);
        u128 S = parse_coords(argv[4], n);
        const char* maxbin = argv[5];
        long long cap = std::atoll(argv[6]);
        double tcap = std::atof(argv[7]);
        long long maxbytes = 0;
        std::vector<u64> mx = read_bin8(maxbin, &maxbytes);
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        Engine e; build_geom(e, n, o);
        int ssize = popc(S);
        // number of forbidden quads = lines' quads + circles' quads, per quad
        // identify the carrier: the unique line or circle through the 4 points.
        // Count distinct carriers, and for the winning T list the carrier chain.
        std::printf("{\n  \"stage\": \"cert2\",\n  \"n\": %d, \"K\": %d, \"size_S\": %d, "
                    "\"max_sets\": %zu,\n", n, K, ssize, mx.size());
        std::printf("  \"coords\": \"%s\",\n", coords(S, n).c_str());
        std::vector<int> pts;
        { u128 t = S; while (t) { pts.push_back(bitid(t)); t &= t - 1; } }
        int exact_alpha = 0;
        for (u64 m : mx) { int a = popc((u128)m & S); if (a > exact_alpha) exact_alpha = a; }
        // precompute the closure of every subset of S is 2^13 = 8192 -- cheap
        int tot = 1 << ssize;
        std::vector<int> closz(tot, -1);
        std::vector<int> clop(tot, -1);   // closure rounds
        for (int msk = 0; msk < tot; ++msk) {
            u128 T = 0;
            for (int i = 0; i < ssize; ++i) if (msk >> i & 1) T |= (u128)1 << pts[i];
            u128 C = T; bool ch = true; int rounds = 0;
            while (ch) {
                ch = false; ++rounds;
                for (u128 q : e.quads)
                    if (!has(C, q) && popc(C & q) == 3) { C |= q; ch = true; }
            }
            closz[msk] = popc(C);
            clop[msk] = rounds;
        }
        // t-bucketed counts
        std::printf("  \"exact_alpha_over_maxpool\": %d, \"exact_d_max\": %d,\n",
                    exact_alpha, ssize - exact_alpha);
        std::printf("  \"buckets\": [\n");
        int cert_alpha = 0;
        for (int t = 1; t <= ssize; ++t) {
            long long nsub = 0, inmax = 0, blocked_by_closure = 0;
            int minclos = 1 << 20, maxclos = 0, maxrounds = 0;
            int best_inmax = -1;
            for (int msk = 0; msk < tot; ++msk) {
                if (__builtin_popcount((unsigned)msk) != t) continue;
                ++nsub;
                if (closz[msk] < minclos) minclos = closz[msk];
                if (closz[msk] > maxclos) maxclos = closz[msk];
                if (clop[msk] > maxrounds) maxrounds = clop[msk];
                u128 T = 0;
                for (int i = 0; i < ssize; ++i) if (msk >> i & 1) T |= (u128)1 << pts[i];
                bool in = false;
                for (u64 m : mx) if (((u128)m & T) == T) { in = true; break; }
                if (in) { ++inmax; best_inmax = t; }
                else if (closz[msk] > K) ++blocked_by_closure;
            }
            if (best_inmax > cert_alpha) cert_alpha = best_inmax;
            std::printf("    {\"t\": %d, \"subsets\": %lld, \"min_closure\": %d, "
                        "\"max_closure\": %d, \"max_closure_rounds\": %d, "
                        "\"in_a_max_set\": %lld, \"not_in_max_and_closure_over_K\": %lld}%s\n",
                        t, nsub, minclos, maxclos, maxrounds, inmax,
                        blocked_by_closure, t == ssize ? "" : ",");
        }
        std::printf("  ],\n");
        std::printf("  \"alpha_proved_by_closure_alone\": %d, \"alpha_true\": %d,\n",
                    cert_alpha, exact_alpha);
        std::printf("  \"closure_suffices\": %s,\n", cert_alpha == exact_alpha ? "true" : "false");
        std::printf("  \"sec\": %.2f\n}\n", now());
        return 0;
    }

    // ----------------------------------------------------------------- carriers
    // Identify, for every forbidden quad, its carrier: a LINE (det of the 3x3
    // coordinate matrix = 0) or a CIRCLE.  Canonical integer keys, no floats.
    //   line   ax+by+c=0  -> key (a,b,c) primitive, a>0 or (a==0 and b>0)
    //   circle x^2+y^2+Dx+Ey+F=0 -> key (D,E,F) primitive, D>0 or (D==0 and E>0)
    // Then trace which carriers the saturation closure of the blocking subset
    // actually uses, and how many forced-addition rounds they drive.
    if (stage == "carriers") {
        int n = std::atoi(argv[2]), K = std::atoi(argv[3]);
        u128 S = parse_coords(argv[4], n);
        const char* maxbin = argv[5];
        long long maxbytes = 0;
        std::vector<u64> mx = read_bin8(maxbin, &maxbytes);
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        Engine e; build_geom(e, n, o);
        auto gcd3 = [](long long a, long long b) {
            while (b) { long long t = a % b; a = b; b = t; } return a < 0 ? -a : a; };
        std::unordered_map<std::string, int> carrier_id;
        std::vector<std::string> carrier_name;
        std::vector<u128> q_carrier(e.quads.size(), 0);
        long long nline = 0, ncirc = 0;
        std::vector<int> quad_pts(e.quads.size());
        for (size_t qi = 0; qi < e.quads.size(); ++qi) {
            u128 q = e.quads[qi];
            int ids[4]; int c = 0; u128 t = q;
            while (t) { ids[c++] = bitid(t); t &= t - 1; }
            quad_pts[qi] = ids[0];
            long long x[4], y[4];
            for (int i = 0; i < 4; ++i) { x[i] = ids[i] % n; y[i] = ids[i] / n; }
            // line test
            long long a1 = y[1] - y[0], b1 = x[0] - x[1];
            long long a2 = y[2] - y[0], b2 = x[0] - x[2];
            long long a3 = y[3] - y[0], b3 = x[0] - x[3];
            long long cr1 = a1 * b2 - a2 * b1, cr2 = a1 * b3 - a3 * b1;
            std::string key; bool isline = (cr1 == 0 && cr2 == 0);
            char buf[128];
            if (isline) {
                long long a = a1, b = b1, cc = -(a * x[0] + b * y[0]);
                long long g = gcd3(gcd3(a < 0 ? -a : a, b < 0 ? -b : b), cc < 0 ? -cc : cc);
                if (g) { a /= g; b /= g; cc /= g; }
                if (a < 0 || (a == 0 && b < 0)) { a = -a; b = -b; cc = -cc; }
                std::snprintf(buf, sizeof buf, "L(%lld,%lld,%lld)", a, b, cc);
                key = buf; ++nline;
            } else {
                // circle: x^2+y^2 + D x + E y + F = 0 through the 4 points
                // solve the 3x3 system from points 0,1,2
                long long A[3][3];
                for (int r = 0; r < 3; ++r) {
                    A[r][0] = x[r]; A[r][1] = y[r]; A[r][2] = 1;
                }
                long long R[3] = {-(x[0] * x[0] + y[0] * y[0]),
                                  -(x[1] * x[1] + y[1] * y[1]),
                                  -(x[2] * x[2] + y[2] * y[2])};
                long long det = A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
                              - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
                              + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]);
                long long Dv = 0, Ev = 0, Fv = 0;
                if (det != 0) {
                    long long Dd = R[0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
                                 - A[0][1] * (R[1] * A[2][2] - A[1][2] * R[2])
                                 + A[0][2] * (R[1] * A[2][1] - A[1][1] * R[2]);
                    long long De = A[0][0] * (R[1] * A[2][2] - A[1][2] * R[2])
                                 - R[0] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
                                 + A[0][2] * (A[1][0] * R[2] - R[1] * A[2][0]);
                    long long Df = A[0][0] * (A[1][1] * R[2] - R[1] * A[2][1])
                                 - A[0][1] * (A[1][0] * R[2] - R[1] * A[2][0])
                                 + R[0] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]);
                    Dv = Dd / det; Ev = De / det; Fv = Df / det;
                }
                long long g = gcd3(gcd3(Dv < 0 ? -Dv : Dv, Ev < 0 ? -Ev : Ev), Fv < 0 ? -Fv : Fv);
                if (g) { Dv /= g; Ev /= g; Fv /= g; }
                if (Dv < 0 || (Dv == 0 && Ev < 0)) { Dv = -Dv; Ev = -Ev; Fv = -Fv; }
                std::snprintf(buf, sizeof buf, "C(%lld,%lld,%lld)", Dv, Ev, Fv);
                key = buf; ++ncirc;
            }
            auto it = carrier_id.find(key);
            int id;
            if (it == carrier_id.end()) { id = (int)carrier_id.size(); carrier_id[key] = id; carrier_name.push_back(key); }
            else id = it->second;
            q_carrier[qi] = (u128)id << 64;
        }
        // global carrier census on S
        std::unordered_map<int, int> onS;   // carrier -> #quads with 3 pts in S
        for (size_t qi = 0; qi < e.quads.size(); ++qi) {
            int inter = popc(e.quads[qi] & S);
            if (inter == 3) onS[(int)(q_carrier[qi] >> 64)]++;
        }
        // trace the closure of the smallest blocking subset (t minimal with closure>K)
        std::vector<int> pts;
        { u128 t = S; while (t) { pts.push_back(bitid(t)); t &= t - 1; } }
        int ssize = popc(S);
        int bestT = -1; u128 bestmask = 0;
        for (int t = 1; t <= ssize && bestT < 0; ++t) {
            std::vector<int> idx(t);
            for (int i = 0; i < t; ++i) idx[i] = i;
            while (true) {
                u128 T = 0;
                for (int i = 0; i < t; ++i) T |= (u128)1 << pts[idx[i]];
                u128 C = T; bool ch = true;
                while (ch) { ch = false;
                    for (u128 q : e.quads) if (!has(C, q) && popc(C & q) == 3) { C |= q; ch = true; } }
                if (popc(C) > K) { bestT = t; bestmask = T; break; }
                int i = t - 1;
                while (i >= 0 && idx[i] == (int)pts.size() - t + i) --i;
                if (i < 0) break;
                ++idx[i];
                for (int j = i + 1; j < t; ++j) idx[j] = idx[j - 1] + 1;
            }
        }
        // count distinct carriers used in the closure chain
        std::unordered_map<int, int> used;
        long long chainq = 0;
        if (bestT > 0) {
            u128 C = bestmask; bool ch = true; int rounds = 0;
            while (ch) { ch = false; ++rounds;
                for (size_t qi = 0; qi < e.quads.size(); ++qi) {
                    u128 q = e.quads[qi];
                    if (!has(C, q) && popc(C & q) == 3) { C |= q; ch = true; ++chainq; used[(int)(q_carrier[qi] >> 64)]++; }
                }
            }
        }
        long long nlinesUsed = 0, ncircsUsed = 0;
        for (auto& kv : used) {
            if (carrier_name[kv.first][0] == 'L') ++nlinesUsed; else ++ncircsUsed;
        }
        long long nAllL = 0, nAllC = 0;
        for (auto& kv : carrier_id) { if (kv.first[0] == 'L') ++nAllL; else ++nAllC; }
        std::printf("{\n  \"stage\": \"carriers\",\n  \"n\": %d, \"K\": %d, \"F_n\": %lld,\n", n, K, e.F);
        std::printf("  \"quads_total\": %zu, \"quads_on_line\": %lld, \"quads_on_circle\": %lld,\n",
                    e.quads.size(), nline, ncirc);
        std::printf("  \"distinct_carriers\": %zu, \"distinct_lines\": %lld, \"distinct_circles\": %lld,\n",
                    carrier_id.size(), nAllL, nAllC);
        std::printf("  \"carriers_with_3pts_in_S\": %zu,\n", onS.size());
        std::printf("  \"smallest_blocking_T_size\": %d, \"blocking_T\": \"%s\",\n",
                    bestT, coords(bestmask, n).c_str());
        std::printf("  \"carriers_used_in_closure\": %zu, \"lines_used\": %lld, \"circles_used\": %lld,\n",
                    used.size(), nlinesUsed, ncircsUsed);
        std::printf("  \"quads_fired_in_closure\": %lld\n}\n", chainq);
        return 0;
    }

    // ----------------------------------------------------------------- climb
    // hill-climb toward a large exact d_max on the (K-1) layer
    if (stage == "climb") {
        int n = std::atoi(argv[2]), k = std::atoi(argv[3]), K = std::atoi(argv[4]);
        long long iters = std::atoll(argv[5]);
        unsigned seed = (unsigned)std::atoi(argv[6]);
        double tcap = (argc > 7) ? std::atof(argv[7]) : 600.0;
        Engine e;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        build_geom(e, n, o);
        unsigned rs = seed;
        auto rnd = [&]() { return (u64)(rand_r_u128(&rs) & 0xFFFFFFFFFFFFULL); };
        double t0 = now();
        int best = -1; u128 bestS = 0;
        long long tried = 0, accepted = 0, exact = 0;
        for (long long it = 0; it < iters; ++it) {
            if (now() - t0 > tcap) break;
            u128 S = 0;
            // random greedy start of size k
            {
                int sz = 0;
                while (sz < k) {
                    int cand = (int)(rnd() % (u64)e.V);
                    if (S & ((u128)1 << e.pid[cand])) continue;
                    if (conflicts_a(e, cand, S)) continue;
                    S |= (u128)1 << e.pid[cand]; ++sz;
                }
            }
            int cur = 0; long long cn = 0; bool comp = false;
            int dm = exact_dmax(e, S, K, 3000000LL, 8.0, &cn, &comp);
            if (!comp) continue;
            ++exact; ++tried;
            cur = dm;
            // hill climb: try swaps
            for (int step = 0; step < 40; ++step) {
                u128 t = S; int rp = bitid(t); t &= t - 1;
                int add = (int)(rnd() % (u64)e.V);
                if (t & ((u128)1 << e.pid[add])) continue;
                u128 T = t | ((u128)1 << e.pid[add]);
                if (!is_safe(e, T)) continue;
                long long nn = 0; bool cc2 = false;
                int d2 = exact_dmax(e, T, K, 3000000LL, 8.0, &nn, &cc2);
                if (!cc2) continue;
                ++tried;
                if (d2 >= cur) { if (d2 > cur) ++accepted; cur = d2; S = T; }
            }
            if (cur > best) {
                best = cur; bestS = S;
                std::fprintf(stderr, "  climb best d_max=%d  t=%.1f\n", best, now() - t0);
                std::fflush(stderr);
            }
        }
        long long cn = 0; bool comp = false;
        int dm = (bestS ? exact_dmax(e, bestS, K, 400000000LL, 300.0, &cn, &comp) : -1);
        std::printf("{\n  \"stage\": \"climb\",\n  \"n\": %d, \"k\": %d, \"K\": %d,\n"
                    "  \"iters\": %lld, \"exact_evals\": %lld, \"improvements\": %lld,\n"
                    "  \"best_dmax_observed\": %d, \"d4_orbit\": %d,\n"
                    "  \"final_dmax_certified\": %d, \"complete\": %s, \"nodes\": %lld,\n"
                    "  \"coords\": \"%s\", \"sec\": %.2f\n}\n",
                    n, k, K, iters, tried, accepted, best,
                    bestS ? d4_orbit(bestS, n) : 0, dm, comp ? "true" : "false", cn,
                    coords(bestS, n).c_str(), now() - t0);
        return 0;
    }

    std::printf("unknown stage %s\n", stage.c_str());
    return 1;
}
