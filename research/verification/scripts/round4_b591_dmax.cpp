// round4_b591_dmax.cpp  --  Round4 solver for B591/B592/B593/B596/B597/B598/B599
//
// d_max(S) = min_{M in M_n} |S \ M| = |S| - max_{M in M_n} |S ^ M|,
//   where M_n = family of MAXIMUM (size K_n) safe sets, |M| = K_n.
// d_max(S) = 0 iff S is contained in some maximum set.
//
// 128-bit occupancy (unsigned __int128) so n = 9 (81 points) works.
// Geometry uses kc::det4 from the shared verified core kc_core.h.
//
// Stages (argv[1]):
//   selfcheck                 F_n for n=2..9, cross-check n<=8 vs kc::build_square
//   profile <n> <k0> <k1>     count safe k-sets for k in [k0,k1] (capped)
//   count   <n> <k> <dscan> <cap> <tcap> [out]   count + dump maximal-at-k sets
//   dmax    <n> <K> <"x,y;x,y;...">              exact d_max of one set
//   dmaxfile<n> <K> <file>    exact d_max of each line of file
//   sweep   <n> <k> <K> <infile> <cap> <tcap>    exact d_max over many sets
//
// JSON objects are printed to stdout (one per stage).

#include "kc_core.h"

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>
#include <chrono>
#include <algorithm>

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
// xorshift128 for reproducible pseudo-randomness (no floats, no libstdc++ RNG)
static u128 rand_r_u128(unsigned* s) {
    u64 a = *s ? *s : 0x9E3779B97F4A7C15ULL, b = a;
    a ^= a << 13; a ^= a >> 7; a ^= a << 17;
    *s = (unsigned)a;
    return ((u128)a << 64) | (u128)b;
}

// ---------------------------------------------------------------- engine
struct Engine {
    int n = 0, V = 0;
    long long F = 0;
    std::vector<u128> quads;          // forbidden 4-point masks
    std::vector<int> pid;             // position -> point id
    std::vector<int> pos;             // point id -> position
    std::vector<std::vector<u128>> qef;  // quads whose other 3 pts are earlier
    std::vector<std::vector<u128>> qea;  // all quads (arbitrary tests)
    std::vector<int> sufS;            // suffix count of a given S (per dmax call)
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
    const std::vector<u128>& v = e.qef[pos];
    for (size_t i = 0; i < v.size(); ++i)
        if (has(M, v[i])) return true;
    return false;
}
static inline bool conflicts_a(const Engine& e, int pos, u128 M) {
    const std::vector<u128>& v = e.qea[pos];
    for (size_t i = 0; i < v.size(); ++i)
        if (has(M, v[i])) return true;
    return false;
}
// M's points are all at positions < from, so position-filtered lists are valid.
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
    for (u128 q : e.quads)
        if (has(M, q)) return false;
    return true;
}

// ---------------------------------------------------------------- D4
static u128 d4(u128 S, int n, int t) {
    u128 out = 0;
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int id = y * n + x;
            if (!((S >> id) & 1)) continue;
            int nx = x, ny = y;
            switch (t) {
                case 0: nx = x;         ny = y;         break;
                case 1: nx = y;         ny = n - 1 - x; break;
                case 2: nx = n - 1 - x; ny = n - 1 - y; break;
                case 3: nx = n - 1 - y; ny = x;         break;
                case 4: nx = n - 1 - x; ny = y;         break;
                case 5: nx = y;         ny = y;         break;
                case 6: nx = x;         ny = n - 1 - y; break;
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

// ---------------------------------------------------------------- counting
struct CountCtx {
    const Engine* e = nullptr;
    u128 M = 0;
    int k = 0;
    long long leaves = 0, nodes = 0, cap = 0;
    double t0 = 0, tcap = 0;
    bool stop = false;
    int dscan = 0;                   // 0 always, 1 when sz>=k-2, 2 when sz>=k-3
    std::vector<u128>* out = nullptr;
    long long maxfound = 0;
};

static void dfs_count(CountCtx& c, int start, int sz) {
    const Engine& e = *c.e;
    ++c.nodes;
    if ((c.nodes & 0xFFFFFFLL) == 0) {
        if (now() - c.t0 > c.tcap) { c.stop = true; return; }
    }
    if (c.nodes > c.cap) { c.stop = true; return; }
    if (sz == c.k) {
        ++c.leaves;
        if (c.out && is_maximal(e, c.M)) c.out->push_back(c.M);
        return;
    }
    bool deep = (c.dscan == 0) || (c.dscan == 1 && sz >= c.k - 2) ||
                (c.dscan == 2 && sz >= c.k - 3);
    for (int p = start; p < e.V; ++p) {
        if (sz + (e.V - p) < c.k) break;
        if (deep && p > start && !has_legal_from(e, p, c.M)) break;
        if (conflicts_f(e, p, c.M)) continue;
        u128 prev = c.M;
        c.M |= (u128)1 << e.pid[p];
        dfs_count(c, p + 1, sz + 1);
        c.M = prev;
        if (c.stop) return;
    }
}

// ---------------------------------------------------------------- d_max B&B
// alpha(S) = max_{M safe, |M|=K} |S & M|   (complete branch and bound)
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

// Valid lower bound for alpha: overlap of a *safe set of size exactly K*.
// Returns -1 if no K-set was produced (then the B&B has no seed bound).
static int greedy_alpha(const Engine& e, u128 S, int K, unsigned seed = 12345u) {
    int bestOv = -1;
    std::vector<int> order(e.V);
    for (int p = 0; p < e.V; ++p) order[p] = p;
    // try S-first, then S-first under 8 dihedral transforms, then random orders
    for (int trial = 0; trial < 40; ++trial) {
        for (int p = 0; p < e.V; ++p) order[p] = p;
        if (trial >= 8) {
            for (int p = e.V - 1; p > 0; --p) {
                int r = (int)((u128)rand_r_u128(&seed) % (u128)(p + 1));
                std::swap(order[p], order[r]);
            }
        } else {
            // stable partition: S points first, in a rotated / reversed order
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
        if (sz == K) {
            int ov = popc(S & M);
            if (ov > bestOv) bestOv = ov;
        }
    }
    return bestOv;
}

static void setup_suf(Engine& e, u128 S) {
    e.sufS.assign(e.V + 1, 0);
    for (int p = e.V - 1; p >= 0; --p)
        e.sufS[p] = e.sufS[p + 1] + (int)((S >> e.pid[p]) & 1);
}

// exact d_max; returns |S| - alpha, or -1 if the B&B hit a cap (incomplete)
static int exact_dmax(Engine& e, u128 S, int K, long long cap, double tcap,
                      long long* nodes, bool* complete) {
    std::vector<int> order;
    for (int p = 0; p < e.V; ++p) if ((S >> e.pid[p]) & 1) order.push_back(e.pid[p]);
    for (int p = 0; p < e.V; ++p) if (!((S >> e.pid[p]) & 1)) order.push_back(e.pid[p]);
    build_geom(e, e.n, order);
    setup_suf(e, S);
    DmCtx c;
    c.e = &e; c.S = S; c.K = K; c.cap = cap; c.t0 = now(); c.tcap = tcap;
    c.best = greedy_alpha(e, S, K);
    if (c.best < 0) c.best = 0;   // 0 is always a valid lower bound for alpha
    dfs_alpha(c, 0, 0, 0);
    *nodes = c.nodes;
    *complete = !c.stop;
    if (!*complete) return -1;
    return popc(S) - c.best;
}

// ---------------------------------------------------------------- helpers
static u128 parse_coords(const std::string& s, int n) {
    u128 M = 0;
    std::vector<int> digits;
    for (size_t i = 0; i <= s.size(); ++i) {
        char ch = (i < s.size()) ? s[i] : ';';
        if (ch >= '0' && ch <= '9') { digits.push_back(ch - '0'); continue; }
        if (ch == ',' || ch == ' ') continue;
        if (digits.size() == 2) M |= (u128)1 << (digits[1] * n + digits[0]);
        digits.clear();
    }
    return M;
}
static std::string hex128(u128 v) {
    char b[64];
    std::snprintf(b, sizeof b, "%016llx%016llx", (unsigned long long)(v >> 64),
                  (unsigned long long)(u64)v);
    return std::string(b);
}

// ---------------------------------------------------------------- main
int main(int argc, char** argv) {
    if (argc < 2) { std::printf("no stage\n"); return 1; }
    std::string stage = argv[1];
    std::vector<int> order_nat;

    if (stage == "selfcheck") {
        std::printf("{\n  \"stage\": \"selfcheck\",\n  \"items\": [\n");
        bool first = true;
        for (int n = 2; n <= 9; ++n) {
            std::vector<int> o;
            for (int p = 0; p < n * n; ++p) o.push_back(p);
            double t = now();
            Engine e; build_geom(e, n, o);
            double g = now() - t;
            int kcF = -1;
            if (n <= 8) {
                kc::Board b; kc::build_square(b, n);
                kcF = (int)b.quads.size();
            }
            std::printf("%s    {\"n\": %d, \"F_128\": %lld, \"F_kccore\": %d, \"agree\": %s, \"build_sec\": %.2f}",
                        first ? "" : ",\n", n, e.F, kcF,
                        (kcF < 0 ? "na" : (kcF == e.F ? "true" : "FALSE")), g);
            first = false;
        }
        std::printf("\n  ]\n}\n");
        return 0;
    }

    if (stage == "profile") {
        int n = std::atoi(argv[2]);
        int k0 = std::atoi(argv[3]), k1 = std::atoi(argv[4]);
        long long cap = (argc > 5) ? std::atoll(argv[5]) : 2000000000LL;
        double tcap = (argc > 6) ? std::atof(argv[6]) : 120.0;
        int dscan = (argc > 7) ? std::atoi(argv[7]) : 0;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        double tb = now();
        Engine e; build_geom(e, n, o);
        double gsec = now() - tb;
        std::printf("{\n  \"stage\": \"profile\",\n  \"n\": %d, \"F_n\": %lld, \"geom_sec\": %.2f,\n  \"rows\": [\n",
                    n, e.F, gsec);
        for (int k = k0; k <= k1; ++k) {
            CountCtx c;
            c.e = &e; c.k = k; c.cap = cap; c.t0 = now(); c.tcap = tcap; c.dscan = dscan;
            dfs_count(c, 0, 0);
            std::printf("    {\"k\": %d, \"count\": %lld, \"nodes\": %lld, \"sec\": %.2f, \"complete\": %s}%s\n",
                        k, c.leaves, c.nodes, now() - c.t0, c.stop ? "false" : "true",
                        k == k1 ? "" : ",");
            c.M = 0;
            c.leaves = 0; c.nodes = 0; c.stop = false;
            std::fflush(stdout);
        }
        std::printf("  ]\n}\n");
        return 0;
    }

    if (stage == "count") {
        int n = std::atoi(argv[2]);
        int k = std::atoi(argv[3]);
        int dscan = std::atoi(argv[4]);
        long long cap = std::atoll(argv[5]);
        double tcap = std::atof(argv[6]);
        const char* outfile = (argc > 7) ? argv[7] : nullptr;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        double tb = now();
        Engine e; build_geom(e, n, o);
        double gsec = now() - tb;
        std::vector<u128> out;
        CountCtx c;
        c.e = &e; c.k = k; c.cap = cap; c.t0 = now(); c.tcap = tcap; c.dscan = dscan;
        c.out = outfile ? &out : nullptr;
        dfs_count(c, 0, 0);
        double sec = now() - c.t0;
        c.e = nullptr;
        if (outfile) {
            FILE* f = std::fopen(outfile, "w");
            for (u128 m : out) std::fprintf(f, "%s\n", hex128(m).c_str());
            std::fclose(f);
        }
        std::printf("{\n  \"stage\": \"count\",\n  \"n\": %d, \"k\": %d, \"F_n\": %lld,\n"
                    "  \"safe_count\": %lld, \"maximal_count\": %zu,\n"
                    "  \"nodes\": %lld, \"sec\": %.2f, \"geom_sec\": %.2f, \"complete\": %s,\n"
                    "  \"dscan\": %d, \"out\": \"%s\"\n}\n",
                    n, k, e.F, c.leaves, out.size(), c.nodes, sec, gsec,
                    c.stop ? "false" : "true", dscan, outfile ? outfile : "");
        return 0;
    }

    if (stage == "dmax") {
        int n = std::atoi(argv[2]);
        int K = std::atoi(argv[3]);
        u128 S = parse_coords(argv[4], n);
        Engine e;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        build_geom(e, n, o);
        bool safe = is_safe(e, S);
        bool mx = is_maximal(e, S);
        long long nodes = 0; bool complete = true;
        double t = now();
        int dm = exact_dmax(e, S, K, 200000000LL, 600.0, &nodes, &complete);
        double sec = now() - t;
        std::printf("{\n  \"stage\": \"dmax\",\n  \"n\": %d, \"K\": %d, \"size\": %d,\n"
                    "  \"safe\": %s, \"maximal\": %s,\n  \"d_max\": %d, \"complete\": %s,\n"
                    "  \"nodes\": %lld, \"sec\": %.2f,\n  \"coords\": \"%s\",\n"
                    "  \"d4_orbit\": %d\n}\n",
                    n, K, popc(S), safe ? "true" : "false", mx ? "true" : "false",
                    dm, complete ? "true" : "false", nodes, sec,
                    coords(S, n).c_str(), d4_orbit(S, n));
        return 0;
    }

    if (stage == "sweep") {
        // sweep <n> <k> <K> <infile> <cap> <tcap> [outjson]
        int n = std::atoi(argv[2]);
        int k = std::atoi(argv[3]);
        int K = std::atoi(argv[4]);
        const char* infile = argv[5];
        long long cap = std::atoll(argv[6]);
        double tcap = std::atof(argv[7]);
        FILE* f = std::fopen(infile, "r");
        if (!f) { std::printf("cannot open %s\n", infile); return 1; }
        char line[128];
        std::vector<u128> sets;
        while (std::fgets(line, sizeof line, f)) {
            if (std::strlen(line) < 5) continue;
            u128 v = 0;
            for (int i = 0; i < 32; ++i) {
                char c = line[i];
                if (c == '\n' || c == '\r' || c == 0) break;
                int d = (c >= '0' && c <= '9') ? c - '0' : (c >= 'a' && c <= 'f') ? c - 'a' + 10 : -1;
                if (d < 0) break;
                v = (v << 4) | (u128)d;
            }
            if (popc(v) != k) continue;
            sets.push_back(v);
        }
        std::fclose(f);
        Engine e;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        build_geom(e, n, o);
        std::vector<long long> hist(k + 1, 0);
        int best = -1; u128 bestS = 0;
        long long nodes = 0, inc = 0, total = 0;
        double t0 = now();
        int done = 0;
        for (u128 S : sets) {
            if (now() - t0 > tcap) break;
            long long nd = 0; bool comp = true;
            int dm = exact_dmax(e, S, K, cap, tcap - (now() - t0), &nd, &comp);
            total += nd; nodes += nd;
            if (dm < 0) { ++inc; continue; }
            ++done;
            ++hist[dm];
            if (dm > best) { best = dm; bestS = S; }
            if ((done & 0x3FF) == 0) { std::fflush(stdout); std::fprintf(stderr, "  done %d/%d best %d t=%.1f\n", done, (int)sets.size(), best, now() - t0); }
        }
        double sec = now() - t0;
        std::printf("{\n  \"stage\": \"sweep\",\n  \"n\": %d, \"k\": %d, \"K\": %d,\n"
                    "  \"input_sets\": %d, \"evaluated\": %d, \"incomplete\": %ld,\n"
                    "  \"hist\": {", n, k, K, (int)sets.size(), done, inc);
        for (int i = 0; i <= k; ++i)
            if (hist[i]) std::printf("%s\"%d\": %lld", i ? ", " : "", i, hist[i]);
        std::printf("},\n  \"max_dmax\": %d, \"max_sec\": %.2f, \"nodes\": %lld,\n"
                    "  \"best_coords\": \"%s\", \"best_d4_orbit\": %d,\n"
                    "  \"maxratio\": \"%d/%d\"\n}\n",
                    best, sec, nodes, coords(bestS, n).c_str(),
                    bestS ? d4_orbit(bestS, n) : 0, best, k);
        return 0;
    }

    if (stage == "neighbors") {
        // dump near-maximal sets built from maximum sets: M minus two, plus one
        // neighbors <n> <K> <poolfile> <k> <nsamp> <seed>
        int n = std::atoi(argv[2]);
        int K = std::atoi(argv[3]);
        const char* poolfile = argv[4];
        int k = std::atoi(argv[5]);
        long long nsamp = std::atoll(argv[6]);
        unsigned seed = (unsigned)std::atoi(argv[7]);
        const char* outfile = argv[8];
        FILE* f = std::fopen(poolfile, "rb");
        if (!f) { std::printf("cannot open pool\n"); return 1; }
        std::fseek(f, 0, SEEK_END);
        long long bytes = std::ftell(f);
        std::fseek(f, 0, SEEK_SET);
        long long nrec = bytes / 8;
        std::vector<u64> pool(nrec);
        if (std::fread(pool.data(), 1, (size_t)bytes, f) != (size_t)bytes) return 1;
        std::fclose(f);
        Engine e;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        build_geom(e, n, o);
        std::srand(seed);
        FILE* g = std::fopen(outfile, "w");
        long long tried = 0, made = 0, maxok = 0;
        for (long long t = 0; t < nsamp; ++t) {
            ++tried;
            u64 M = pool[(size_t)((long long)std::rand() * rand() % nrec)];
            // remove two random bits, add one random point not in M
            u64 T = M;
            int r1 = std::rand() % n * n, r2 = std::rand() % n * n;
            T &= ~((u64)1 << r1);
            T &= ~((u64)1 << r2);
            int add = std::rand() % (n * n);
            if ((T >> add) & 1) continue;
            u128 S = (u128)(T | ((u64)1 << add));
            if (popc(S) != k) continue;
            if (!is_safe(e, S)) continue;
            if (!is_maximal(e, S)) continue;
            std::fprintf(g, "%s\n", hex128(S).c_str());
            ++made; if (is_maximal(e, S)) ++maxok;
        }
        std::fclose(g);
        std::printf("{\n  \"stage\": \"neighbors\",\n  \"n\": %d, \"K\": %d, \"k\": %d,\n"
                    "  \"pool\": %lld, \"tried\": %lld, \"maximal_sets_written\": %lld,\n"
                    "  \"out\": \"%s\"\n}\n", n, K, k, nrec, tried, made, outfile);
        return 0;
    }

    if (stage == "poolgrow") {
        // randomized local search for maximum sets, dedup, grows a pool
        // poolgrow <n> <K> <iters> <outfile> <seed>
        int n = std::atoi(argv[2]);
        int K = std::atoi(argv[3]);
        long long iters = std::atoll(argv[4]);
        const char* outfile = argv[5];
        unsigned seed = (unsigned)std::atoi(argv[6]);
        Engine e;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        build_geom(e, n, o);
        std::srand(seed);
        FILE* g = std::fopen(outfile, "w");
        long long found = 0;
        for (long long t = 0; t < iters; ++t) {
            u128 M = 0;
            int sz = 0;
            // random greedy to size K
            while (sz < K) {
                int start = std::rand() % e.V, p = start, adv = -1, cnt = 0;
                for (int q = 0; q < e.V; ++q) {
                    int cand = (start + q) % e.V;
                    if (M & ((u128)1 << e.pid[cand])) continue;
                    if (conflicts_a(e, cand, M)) continue;
                    adv = cand; ++cnt;
                    if (cnt > 1 && std::rand() % 3 == 0) break;
                }
                if (adv < 0) break;
                M |= (u128)1 << e.pid[adv]; ++sz;
            }
            if (sz != K) continue;
            if (!is_safe(e, M)) continue;
            if (is_maximal(e, M)) {
                std::fprintf(g, "%s\n", hex128(M).c_str());
                ++found;
            }
        }
        std::fclose(g);
        std::printf("{\n  \"stage\": \"poolgrow\",\n  \"n\": %d, \"K\": %d,\n"
                    "  \"iters\": %lld, \"maximal_found\": %lld, \"out\": \"%s\"\n}\n",
                    n, K, iters, found, outfile);
        return 0;
    }

    if (stage == "diag") {
        // diag <n> <K> <coords>  : greedy-extend S to size K many ways, verify each
        int n = std::atoi(argv[2]);
        int K = std::atoi(argv[3]);
        u128 S = parse_coords(argv[4], n);
        Engine e;
        std::vector<int> o;
        for (int p = 0; p < n * n; ++p) o.push_back(p);
        build_geom(e, n, o);
        std::printf("{\n  \"stage\": \"diag\",\n  \"n\": %d, \"K\": %d, \"size_S\": %d,\n",
                    n, K, popc(S));
        std::printf("  \"S_safe\": %s,\n", is_safe(e, S) ? "true" : "false");
        std::printf("  \"qea_sizes\": [");
        for (int p = 0; p < e.V; ++p) std::printf("%s%zu", p ? ", " : "", e.qea[p].size());
        std::printf("],\n  \"qef_sizes\": [");
        for (int p = 0; p < e.V; ++p) std::printf("%s%zu", p ? ", " : "", e.qef[p].size());
        std::printf("],\n  \"sum_qea\": %zu,\n", [&]{ size_t t=0; for (auto&v:e.qea) t+=v.size(); return t; }());
        // greedy with the shared helper
        int g = greedy_alpha(e, S, K);
        std::printf("  \"greedy_alpha\": %d,\n", g);
        // brute: extend S by single points, test safety of the union
        int bestov = 0; u128 bestM = 0;
        for (int p = 0; p < e.V; ++p) {
            u128 M = S | ((u128)1 << p);
            if (popc(M) != K) continue;
            if (!is_safe(e, M)) continue;
            int ov = popc(M & S);
            if (ov > bestov) { bestov = ov; bestM = M; }
        }
        std::printf("  \"one_point_extend_max_overlap\": %d,\n", bestov);
        std::printf("  \"one_point_extend_coords\": \"%s\",\n", coords(bestM, n).c_str());
        std::printf("  \"one_point_extend_is_maximal\": %s,\n", bestM ? (is_maximal(e, bestM) ? "true" : "false") : "na");
        long long nodes = 0; bool comp = true;
        int dm = exact_dmax(e, S, K, 200000000LL, 300.0, &nodes, &comp);
        std::printf("  \"bb_dmax\": %d, \"bb_nodes\": %lld\n}\n", dm, nodes);
        return 0;
    }

    std::printf("unknown stage %s\n", stage.c_str());
    return 1;
}
