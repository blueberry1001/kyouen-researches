// Cycle 8 package B: conditional maximum safe-set sizes under orbit /
// occupancy constraints. Independent of cycle8_lib.max_safe_under().
//
// Modes:
//   count N K [constraints]   -> # of safe K-sets under constraints
//   first N K [constraints]   -> one safe K-set mask (hex) + count
//   max   N [constraints]     -> maximum size under constraints
//   occ   N K [constraints]   -> occupancy histogram at size K
//
// Constraints:
//   --force P / --forbid P / --forbid-orbit X,Y / --require-orbit X,Y
//   --corners C / --seed S / --known-upper U / --max-nodes M / --limit M
//
// Output: one JSON object on stdout. complete=false iff node-limit hit.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <utility>
#include <vector>

using u64 = std::uint64_t;

static int N, V;
static std::vector<std::vector<u64>> triples_by_pt;
static int n_quads_total = 0;
static u64 corner_mask = 0;
static std::vector<int> g_undo_stack;

static void build_geometry() {
    V = N * N;
    std::vector<long long> rowr(V), rowx(V), rowy(V);
    for (int y = 0; y < N; y++) {
        for (int x = 0; x < N; x++) {
            int id = y * N + x;
            rowr[id] = (long long)x * x + (long long)y * y;
            rowx[id] = x;
            rowy[id] = y;
        }
    }
    triples_by_pt.assign(V, {});
    n_quads_total = 0;
    for (int a = 0; a < V - 3; a++)
    for (int b = a + 1; b < V - 2; b++)
    for (int c = b + 1; c < V - 1; c++)
    for (int d = c + 1; d < V; d++) {
        long long m[4][4];
        int ids[4] = {a, b, c, d};
        for (int i = 0; i < 4; i++) {
            m[i][0] = rowr[ids[i]];
            m[i][1] = rowx[ids[i]];
            m[i][2] = rowy[ids[i]];
            m[i][3] = 1;
        }
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
                mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1]) -
                mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0]) +
                mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]);
            det += (i % 2 == 0 ? 1 : -1) * m[i][0] * det3;
        }
        if (det == 0) {
            n_quads_total++;
            for (int t = 0; t < 4; t++) {
                u64 o = 0;
                for (int s = 0; s < 4; s++)
                    if (s != t) o |= 1ULL << ids[s];
                triples_by_pt[ids[t]].push_back(o);
            }
        }
    }
    if (N == 1) corner_mask = 1;
    else {
        corner_mask = (1ULL << 0) | (1ULL << (N - 1)) |
                      (1ULL << ((N - 1) * N)) | (1ULL << (N * N - 1));
    }
}

static void cell_key(int x, int y, int *kx, int *ky) {
    int n = N;
    int xs[8] = {x, n - 1 - x, x, n - 1 - x, y, n - 1 - y, y, n - 1 - y};
    int ys[8] = {y, y, n - 1 - y, n - 1 - y, x, x, n - 1 - x, n - 1 - x};
    int bx = xs[0], by = ys[0];
    for (int i = 1; i < 8; i++) {
        if (xs[i] < bx || (xs[i] == bx && ys[i] < by)) {
            bx = xs[i];
            by = ys[i];
        }
    }
    *kx = bx;
    *ky = by;
}

static u64 orbit_mask_of(int ox, int oy) {
    u64 m = 0;
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++) {
            int kx, ky;
            cell_key(x, y, &kx, &ky);
            if (kx == ox && ky == oy) m |= 1ULL << (y * N + x);
        }
    return m;
}

struct Constraints {
    u64 force = 0;
    u64 forbid = 0;
    std::vector<u64> require_orbits;
    int corners_exact = -1;
};

struct Ctx {
    u64 forced = 0;
    u64 forbidden = 0;
    std::vector<u64> req_orbits;
    int corners_exact = -1;
    u64 corner_mask = 0;
    int target = 0;
    long long max_nodes = 2000000000LL;
    long long nodes = 0;
    bool node_limit_hit = false;
    long long n_found = 0;
    u64 first_mask = 0;
    int best = 0;
    u64 best_mask = 0;
    long long n_at_best = 0;
    int ccount[64];
    u64 chosen = 0;
    int mode = 0; // 0=count/first, 1=max, 2=occ
    std::map<std::string, long long> *hist = nullptr;
    long long total_seen = 0;
};

static inline int popc(u64 m) { return __builtin_popcountll(m); }

static bool constraints_possible(const Ctx &S, u64 cand) {
    if (S.corners_exact >= 0) {
        int ch = popc(S.chosen & S.corner_mask);
        if (ch > S.corners_exact) return false;
        if (ch + popc(cand & S.corner_mask) < S.corners_exact) return false;
    }
    if ((S.forced & ~S.chosen & ~cand) != 0) return false;
    for (u64 ro : S.req_orbits)
        if ((S.chosen & ro) == 0 && (cand & ro) == 0) return false;
    return true;
}

static bool constraints_satisfied(const Ctx &S, int count) {
    if (S.corners_exact >= 0 && popc(S.chosen & S.corner_mask) != S.corners_exact)
        return false;
    if ((S.forced & ~S.chosen) != 0) return false;
    if ((S.chosen & S.forbidden) != 0) return false;
    for (u64 ro : S.req_orbits)
        if ((S.chosen & ro) == 0) return false;
    if (S.mode != 1 && S.target >= 0 && count != S.target) return false;
    return true;
}

static void record_leaf(Ctx &S, int count) {
    if (!constraints_satisfied(S, count)) return;
    if (S.mode == 1) {
        if (count > S.best) {
            S.best = count;
            S.best_mask = S.chosen;
            S.n_at_best = 1;
        } else if (count == S.best) {
            S.n_at_best++;
        }
    } else if (S.mode == 0) {
        if (S.n_found == 0) S.first_mask = S.chosen;
        S.n_found++;
    } else {
        S.total_seen++;
        if (S.hist) {
            std::map<std::pair<int, int>, int> occ;
            for (int y = 0; y < N; y++) {
                for (int x = 0; x < N; x++) {
                    int kx, ky;
                    cell_key(x, y, &kx, &ky);
                    auto key = std::make_pair(kx, ky);
                    if (!occ.count(key)) occ[key] = 0;
                    if ((S.chosen >> (y * N + x)) & 1ULL) occ[key]++;
                }
            }
            std::string key;
            char buf[32];
            for (auto &kv : occ) {
                snprintf(buf, sizeof(buf), "%d,%d:%d;", kv.first.first, kv.first.second,
                         kv.second);
                key += buf;
            }
            (*S.hist)[key]++;
        }
    }
}

// Enum-style DFS: at each node try taking each remaining candidate in order.
// Also evaluates the current set (needed for max of any size / exact counts).
static void dfs(Ctx &S, u64 cand, int count) {
    if (S.node_limit_hit) return;
    if (++S.nodes > S.max_nodes) {
        S.node_limit_hit = true;
        return;
    }
    if (!constraints_possible(S, cand)) return;

    if (S.mode == 1) {
        int room = count + popc(cand);
        if (room < S.best) return;
        // current partial set is a valid safe set of this size
        if (count >= S.best) record_leaf(S, count);
        if (S.node_limit_hit) return;
    } else if (S.mode == 0 || S.mode == 2) {
        if (count > S.target) return;
        if (count + popc(cand) < S.target) return;
        if (count == S.target) {
            record_leaf(S, count);
            return;
        }
    }

    while (cand) {
        if (S.node_limit_hit) return;
        int u = __builtin_ctzll(cand);
        // skip u permanently in this loop; take-branch below
        u64 newcand = cand & ~(1ULL << u);
        size_t mark = g_undo_stack.size();
        bool ok = true;
        for (u64 o : triples_by_pt[u]) {
            if ((o & S.chosen) == o) {
                ok = false;
                break;
            }
            int pc = popc(o & S.chosen);
            if (pc == 2) {
                u64 wmask = o & ~S.chosen;
                if (wmask == 0) {
                    ok = false;
                    break;
                }
                int w = __builtin_ctzll(wmask);
                if ((S.chosen >> w) & 1ULL) continue;
                if (S.ccount[w] == 0) newcand &= ~(1ULL << w);
                S.ccount[w]++;
                g_undo_stack.push_back(w);
            }
        }
        if (ok) {
            S.chosen |= 1ULL << u;
            dfs(S, newcand, count + 1);
            S.chosen &= ~(1ULL << u);
        }
        while (g_undo_stack.size() > mark) {
            S.ccount[g_undo_stack.back()]--;
            g_undo_stack.pop_back();
        }
        cand &= ~(1ULL << u);
        if (S.mode == 1) {
            if (count + popc(cand) < S.best) return;
        } else {
            if (count + popc(cand) < S.target) return;
        }
    }
}

static bool parse_pair(const char *s, int *x, int *y) {
    return sscanf(s, "%d,%d", x, y) == 2;
}

int main(int argc, char **argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    setvbuf(stderr, nullptr, _IONBF, 0);
    if (argc < 3) {
        fprintf(stderr,
                "usage: %s count|first|max|occ N [K] [options]\n"
                "  --force P --forbid P --forbid-orbit X,Y --require-orbit X,Y\n"
                "  --corners C --seed S --known-upper U --max-nodes M --limit M\n",
                argv[0]);
        return 2;
    }
    std::string mode = argv[1];
    N = atoi(argv[2]);
    if (N <= 0 || N > 10) {
        fprintf(stderr, "bad N\n");
        return 2;
    }
    build_geometry();

    int K = 0;
    bool have_K = false;
    Constraints cons;
    int seed = 0;
    int known_upper = 14;
    long long max_nodes = 2000000000LL;
    int occ_limit = 200000;
    bool have_seed = false;

    for (int i = 3; i < argc; i++) {
        std::string a = argv[i];
        if (a.rfind("--", 0) == 0) {
            auto need = [&](int k) {
                if (i + k >= argc) {
                    fprintf(stderr, "missing arg after %s\n", a.c_str());
                    exit(2);
                }
            };
            if (a == "--force") {
                need(1);
                int p = atoi(argv[++i]);
                if (p < 0 || p >= N * N) {
                    fprintf(stderr, "force pid oob\n");
                    return 2;
                }
                cons.force |= 1ULL << p;
            } else if (a == "--forbid") {
                need(1);
                int p = atoi(argv[++i]);
                if (p < 0 || p >= N * N) {
                    fprintf(stderr, "forbid pid oob\n");
                    return 2;
                }
                cons.forbid |= 1ULL << p;
            } else if (a == "--forbid-orbit") {
                need(1);
                int x, y;
                if (!parse_pair(argv[++i], &x, &y)) {
                    fprintf(stderr, "bad orbit\n");
                    return 2;
                }
                cons.forbid |= orbit_mask_of(x, y);
            } else if (a == "--require-orbit") {
                need(1);
                int x, y;
                if (!parse_pair(argv[++i], &x, &y)) {
                    fprintf(stderr, "bad orbit\n");
                    return 2;
                }
                cons.require_orbits.push_back(orbit_mask_of(x, y));
            } else if (a == "--corners") {
                need(1);
                cons.corners_exact = atoi(argv[++i]);
            } else if (a == "--seed") {
                need(1);
                seed = atoi(argv[++i]);
                have_seed = true;
            } else if (a == "--known-upper") {
                need(1);
                known_upper = atoi(argv[++i]);
            } else if (a == "--max-nodes") {
                need(1);
                max_nodes = atoll(argv[++i]);
            } else if (a == "--limit") {
                need(1);
                occ_limit = atoi(argv[++i]);
            } else {
                fprintf(stderr, "unknown arg %s\n", a.c_str());
                return 2;
            }
        } else if (!have_K) {
            K = atoi(a.c_str());
            have_K = true;
        } else {
            fprintf(stderr, "unexpected arg %s\n", a.c_str());
            return 2;
        }
    }

    if (mode != "max" && !have_K) {
        fprintf(stderr, "mode %s requires K\n", mode.c_str());
        return 2;
    }
    if (cons.force & cons.forbid) {
        printf("{\"mode\":\"%s\",\"n\":%d,\"K\":%d,\"error\":\"force/forbid conflict\","
               "\"complete\":true,\"max_size\":-1,\"count\":0}\n",
               mode.c_str(), N, K);
        return 0;
    }

    // forced set must not already complete a forbidden quad
    {
        u64 f = cons.force;
        bool force_unsafe = false;
        u64 f2 = f;
        while (f2 && !force_unsafe) {
            int u = __builtin_ctzll(f2);
            f2 &= f2 - 1;
            for (u64 o : triples_by_pt[u]) {
                if ((o & f) == o) {
                    force_unsafe = true;
                    break;
                }
            }
        }
        if (force_unsafe) {
            printf("{\"mode\":\"%s\",\"n\":%d,\"K\":%d,\"error\":\"forced set unsafe\","
                   "\"complete\":true,\"max_size\":-1,\"count\":0}\n",
                   mode.c_str(), N, K);
            return 0;
        }
    }

    Ctx S{};
    S.forced = cons.force;
    S.forbidden = cons.forbid;
    S.req_orbits = cons.require_orbits;
    S.corners_exact = cons.corners_exact;
    S.corner_mask = corner_mask;
    S.target = K;
    S.max_nodes = max_nodes;
    S.best = have_seed ? seed : 0;
    memset(S.ccount, 0, sizeof(S.ccount));

    if (mode == "count" || mode == "first") S.mode = 0;
    else if (mode == "max") S.mode = 1;
    else if (mode == "occ") S.mode = 2;
    else {
        fprintf(stderr, "unknown mode %s\n", mode.c_str());
        return 2;
    }

    // place forced stones first
    u64 all = (V >= 64) ? ~0ULL : ((1ULL << V) - 1);
    u64 cand = all & ~cons.forbid;
    {
        u64 f = cons.force;
        bool ok = true;
        while (f) {
            int u = __builtin_ctzll(f);
            f &= f - 1;
            cand &= ~(1ULL << u);
            for (u64 o : triples_by_pt[u]) {
                if ((o & S.chosen) == o) {
                    ok = false;
                    break;
                }
                int pc = popc(o & S.chosen);
                if (pc == 2) {
                    u64 wmask2 = o & ~S.chosen;
                    if (wmask2 == 0) {
                        ok = false;
                        break;
                    }
                    int w = __builtin_ctzll(wmask2);
                    if ((cons.force >> w) & 1ULL) {
                        ok = false;
                        break;
                    }
                    if (S.ccount[w] == 0) cand &= ~(1ULL << w);
                    S.ccount[w]++;
                }
            }
            S.chosen |= 1ULL << u;
            if (!ok) break;
        }
        if (!ok) {
            printf("{\"mode\":\"%s\",\"n\":%d,\"K\":%d,\"error\":\"forced conflict\","
                   "\"complete\":true,\"max_size\":-1,\"count\":0}\n",
                   mode.c_str(), N, K);
            return 0;
        }
        cand &= ~S.chosen;
        cand &= ~cons.forbid;
    }

    int start_count = popc(S.chosen);
    std::map<std::string, long long> hist;
    if (S.mode == 2) S.hist = &hist;

    // For max mode: also record current forced-prefix as a candidate set
    dfs(S, cand, start_count);

    printf("{\"mode\":\"%s\",\"n\":%d,\"K\":%d,", mode.c_str(), N, K);
    if (S.mode == 1) {
        printf("\"max_size\":%d,\"nodes\":%lld,\"complete\":%s,\"n_at_best\":%lld,\"first\":",
               S.best, S.nodes, S.node_limit_hit ? "false" : "true", S.n_at_best);
        if (S.best > 0 && S.best_mask) printf("\"%llx\"", (unsigned long long)S.best_mask);
        else printf("null");
        printf(",\"seed\":%d,\"known_upper\":%d,", have_seed ? seed : 0, known_upper);
    } else if (S.mode == 0) {
        printf("\"target\":%d,\"count\":%lld,\"nodes\":%lld,\"complete\":%s,\"first\":",
               K, S.n_found, S.nodes, S.node_limit_hit ? "false" : "true");
        if (S.n_found > 0) printf("\"%llx\"", (unsigned long long)S.first_mask);
        else printf("null");
        printf(",");
    } else {
        printf("\"target\":%d,\"total_seen\":%lld,\"n_patterns\":%zu,\"nodes\":%lld,"
               "\"complete\":%s,\"patterns\":[",
               K, S.total_seen, hist.size(), S.nodes,
               S.node_limit_hit ? "false" : "true");
        bool firstp = true;
        for (auto &kv : hist) {
            printf("%s{\"occ\":\"%s\",\"count\":%lld}", firstp ? "" : ",",
                   kv.first.c_str(), kv.second);
            firstp = false;
        }
        printf("],");
    }
    printf("\"quads\":%d,\"force\":\"%llx\",\"forbid\":\"%llx\",\"corners\":%d,"
           "\"require_orbits\":%zu}\n",
           n_quads_total, (unsigned long long)cons.force, (unsigned long long)cons.forbid,
           cons.corners_exact, cons.require_orbits.size());
    return 0;
}
