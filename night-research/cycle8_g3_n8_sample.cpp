// Cycle 8 package G3: sample distinct K-stone safe sets on n x n
// (primary target: n=8, K=15). Not a complete enumeration.
//
// Strategies:
//   1. seed + D4 orbit of a known witness (via --seed-pts or hardcoded n=8)
//   2. randomized exact-target DFS with per-trial cell-order randomization
//   3. randomized greedy fill (any superset of size>=K yields C(size,K) subsets)
//   4. 1-swap / limited 2-swap safe reconfiguration expansion
//   5. constrained first-search under --force/--forbid diversity (optional)
//
// Output: JSON stats on stdout + optional binary masks file (--out).
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <random>
#include <set>
#include <string>
#include <utility>
#include <vector>

using u64 = std::uint64_t;

static int N, V, TARGET;
static std::vector<std::vector<u64>> triples_by_pt;
static int n_quads_total = 0;
static std::vector<std::array<int, 8>> d4_perm; // [8][V] but V<=100
static std::mt19937_64 rng;

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
}

static void build_d4() {
    d4_perm.assign(8, {});
    for (int m = 0; m < 8; m++) {
        bool fx = m & 1, fy = m & 2, tr = m & 4;
        for (int y = 0; y < N; y++) {
            for (int x = 0; x < N; x++) {
                int sx = fx ? (N - 1 - x) : x;
                int sy = fy ? (N - 1 - y) : y;
                int nx = tr ? sy : sx;
                int ny = tr ? sx : sy;
                d4_perm[m][y * N + x] = ny * N + nx;
            }
        }
    }
}

static inline int popc(u64 m) { return __builtin_popcountll(m); }

static u64 apply_d4(u64 mask, int m) {
    u64 o = 0;
    u64 w = mask;
    while (w) {
        u64 b = w & -w;
        int i = __builtin_ctzll(w);
        w ^= b;
        o |= 1ULL << d4_perm[m][i];
    }
    return o;
}

static u64 d4_canon(u64 mask) {
    u64 best = ~0ULL;
    for (int m = 0; m < 8; m++) best = std::min(best, apply_d4(mask, m));
    return best;
}

static bool safe_add(u64 mask, int u) {
    for (u64 o : triples_by_pt[u])
        if ((o & mask) == o) return false;
    return true;
}

static bool is_safe_mask(u64 mask) {
    u64 w = mask;
    while (w) {
        int u = __builtin_ctzll(w);
        w &= w - 1;
        for (u64 o : triples_by_pt[u])
            if ((o & mask) == o) return false;
    }
    return true;
}

static bool safe_swap(u64 mask, int r, int v) {
    // r in mask, v not in mask. Check no forbidden quad fully in mask-r+v.
    // Any such quad must contain v.
    u64 m2 = (mask & ~(1ULL << r)) | (1ULL << v);
    for (u64 o : triples_by_pt[v])
        if ((o & m2) == o) return false;
    return true;
}

// ---- collection ----
static std::set<u64> found;
static std::set<u64> found_canon;
static long long dfs_nodes = 0;
static long long dfs_node_budget = 0;
static long long dfs_solutions = 0;
static long long greedy_hits = 0;
static long long greedy_trials = 0;
static int max_sets_cap = 500;
static bool node_limit_hit = false;

static void record(u64 mask) {
    if (popc(mask) != TARGET) return;
    if (!is_safe_mask(mask)) return;
    if ((int)found.size() >= max_sets_cap) return;
    if (found.count(mask)) return;
    found.insert(mask);
    found_canon.insert(d4_canon(mask));
}

// Constrained-propagating randomized DFS targeting exact TARGET size.
// Propagation mirrors cycle8_b_maxsafe.cpp (blocker ccount).
struct DfsState {
    u64 chosen = 0;
    int ccount[128];
};

static void dfs_rand(u64 chosen, u64 cand, int count, std::vector<u64> &undo_unused,
                     int *ccount) {
    if (node_limit_hit) return;
    if (dfs_node_budget > 0 && ++dfs_nodes > dfs_node_budget) {
        node_limit_hit = true;
        return;
    }
    if ((int)found.size() >= max_sets_cap) return;
    if (count > TARGET) return;
    if (count + popc(cand) < TARGET) return;
    if (count == TARGET) {
        dfs_solutions++;
        record(chosen);
        return;
    }

    // Collect remaining candidates, shuffle, try take/skip in random order.
    std::vector<int> cs;
    u64 w = cand;
    while (w) {
        cs.push_back(__builtin_ctzll(w));
        w &= w - 1;
    }
    if (cs.empty()) return;
    std::shuffle(cs.begin(), cs.end(), rng);

    for (int u : cs) {
        if (node_limit_hit) return;
        if ((int)found.size() >= max_sets_cap) return;
        u64 newcand = cand & ~(1ULL << u);
        bool ok = true;
        std::vector<int> undo;
        for (u64 o : triples_by_pt[u]) {
            if ((o & chosen) == o) {
                ok = false;
                break;
            }
            int pc = popc(o & chosen);
            if (pc == 2) {
                u64 wm = o & ~chosen;
                if (wm == 0) {
                    ok = false;
                    break;
                }
                int v = __builtin_ctzll(wm);
                if ((chosen >> v) & 1ULL) continue;
                if (ccount[v] == 0) newcand &= ~(1ULL << v);
                ccount[v]++;
                undo.push_back(v);
            }
        }
        // randomize take-first vs skip-first
        bool take_first = (rng() & 1) != 0;
        auto do_take = [&]() {
            if (ok) {
                u64 nc = chosen | (1ULL << u);
                dfs_rand(nc, newcand, count + 1, undo_unused, ccount);
            }
        };
        auto do_skip = [&]() {
            u64 c2 = cand & ~(1ULL << u);
            if (count + popc(c2) >= TARGET) dfs_rand(chosen, c2, count, undo_unused, ccount);
        };
        if (take_first) {
            do_take();
            do_skip();
        } else {
            do_skip();
            do_take();
        }
        for (int v : undo) ccount[v]--;
        cand &= ~(1ULL << u);
        if (count + popc(cand) < TARGET) break;
        if (node_limit_hit) return;
        if ((int)found.size() >= max_sets_cap) return;
    }
}

static void run_dfs_trials(int trials, long long nodes_per) {
    int ccount[128];
    std::vector<u64> dummy;
    for (int t = 0; t < trials; t++) {
        if ((int)found.size() >= max_sets_cap) break;
        dfs_node_budget = nodes_per;
        dfs_nodes = 0;
        node_limit_hit = false;
        memset(ccount, 0, sizeof(ccount));
        u64 all = (V >= 64) ? ~0ULL : ((1ULL << V) - 1);
        dfs_rand(0, all, 0, dummy, ccount);
        node_limit_hit = false;
    }
}

static void run_greedy(int trials) {
    std::vector<int> order(V);
    for (int i = 0; i < V; i++) order[i] = i;
    for (int t = 0; t < trials; t++) {
        greedy_trials++;
        std::shuffle(order.begin(), order.end(), rng);
        u64 mask = 0;
        int cnt = 0;
        for (int u : order) {
            if (safe_add(mask, u)) {
                mask |= 1ULL << u;
                cnt++;
            }
        }
        if (cnt < TARGET) continue;
        greedy_hits++;
        if (cnt == TARGET) {
            record(mask);
        } else {
            // all TARGET-subsets of a safe set are safe; sample a few
            std::vector<int> pts;
            u64 w = mask;
            while (w) {
                pts.push_back(__builtin_ctzll(w));
                w &= w - 1;
            }
            for (int s = 0; s < 8; s++) {
                std::shuffle(pts.begin(), pts.end(), rng);
                u64 sub = 0;
                for (int i = 0; i < TARGET; i++) sub |= 1ULL << pts[i];
                record(sub);
            }
        }
        if ((int)found.size() >= max_sets_cap) break;
    }
}

static long long expand_swaps(int max_iters, int two_swap_budget_per_set) {
    long long added = 0;
    for (int it = 0; it < max_iters; it++) {
        std::vector<u64> cur(found.begin(), found.end());
        std::vector<u64> news;
        for (u64 s : cur) {
            std::vector<int> occ, emp;
            for (int p = 0; p < V; p++) {
                if ((s >> p) & 1ULL) occ.push_back(p);
                else emp.push_back(p);
            }
            for (int r : occ) {
                for (int v : emp) {
                    if (safe_swap(s, r, v)) {
                        u64 s2 = (s & ~(1ULL << r)) | (1ULL << v);
                        if (!found.count(s2)) news.push_back(s2);
                    }
                }
            }
            // limited 2-swap
            if (two_swap_budget_per_set > 0 && (int)occ.size() >= 2 &&
                (int)emp.size() >= 2) {
                int tries = 0;
                for (int i = 0; i < (int)occ.size() && tries < two_swap_budget_per_set; i++) {
                    for (int j = i + 1; j < (int)occ.size() && tries < two_swap_budget_per_set; j++) {
                        for (int a = 0; a < (int)emp.size() && tries < two_swap_budget_per_set; a++) {
                            for (int b = a + 1; b < (int)emp.size() && tries < two_swap_budget_per_set; b++) {
                                tries++;
                                u64 s2 = s & ~(1ULL << occ[i]) & ~(1ULL << occ[j]);
                                s2 |= 1ULL << emp[a];
                                s2 |= 1ULL << emp[b];
                                if (found.count(s2)) continue;
                                if (is_safe_mask(s2)) news.push_back(s2);
                            }
                        }
                    }
                }
            }
            if ((int)found.size() + (int)news.size() >= max_sets_cap * 2) break;
        }
        long long before = (long long)found.size();
        for (u64 s : news) record(s);
        long long after = (long long)found.size();
        added += after - before;
        if (after == before) break;
        if ((int)found.size() >= max_sets_cap) break;
    }
    return added;
}

// Constrained diversity: forbid/force random cells, run short DFS.
static void run_constrained_diversity(int rounds, long long nodes_per) {
    if (found.empty()) return;
    std::vector<u64> pool(found.begin(), found.end());
    int ccount[128];
    std::vector<u64> dummy;
    for (int r = 0; r < rounds; r++) {
        if ((int)found.size() >= max_sets_cap) break;
        u64 base = pool[rng() % pool.size()];
        std::vector<int> occ, emp;
        for (int p = 0; p < V; p++) {
            if ((base >> p) & 1ULL) occ.push_back(p);
            else emp.push_back(p);
        }
        // force 2-4 stones from base, forbid 2-5 empty cells
        u64 force = 0, forbid = 0;
        std::shuffle(occ.begin(), occ.end(), rng);
        std::shuffle(emp.begin(), emp.end(), rng);
        int nf = 2 + (int)(rng() % 3);
        int nb = 2 + (int)(rng() % 4);
        for (int i = 0; i < nf && i < (int)occ.size(); i++) force |= 1ULL << occ[i];
        for (int i = 0; i < nb && i < (int)emp.size(); i++) forbid |= 1ULL << emp[i];
        if (force & forbid) continue;
        if (!is_safe_mask(force)) continue;

        dfs_node_budget = nodes_per;
        dfs_nodes = 0;
        node_limit_hit = false;
        memset(ccount, 0, sizeof(ccount));
        u64 all = (V >= 64) ? ~0ULL : ((1ULL << V) - 1);
        u64 cand = all & ~forbid;
        u64 f = force;
        bool ok = true;
        u64 chosen = 0;
        while (f) {
            int u = __builtin_ctzll(f);
            f &= f - 1;
            cand &= ~(1ULL << u);
            for (u64 o : triples_by_pt[u]) {
                if ((o & chosen) == o) {
                    ok = false;
                    break;
                }
                int pc = popc(o & chosen);
                if (pc == 2) {
                    u64 wm = o & ~chosen;
                    if (wm == 0) {
                        ok = false;
                        break;
                    }
                    int v = __builtin_ctzll(wm);
                    if ((force >> v) & 1ULL) {
                        ok = false;
                        break;
                    }
                    if (ccount[v] == 0) cand &= ~(1ULL << v);
                    ccount[v]++;
                }
            }
            chosen |= 1ULL << u;
            if (!ok) break;
        }
        if (!ok) continue;
        cand &= ~chosen;
        cand &= ~forbid;
        dfs_rand(chosen, cand, popc(chosen), dummy, ccount);
        node_limit_hit = false;
    }
}

static u64 pts_to_mask(const std::vector<std::pair<int, int>> &pts) {
    u64 m = 0;
    for (auto &p : pts) m |= 1ULL << (p.second * N + p.first);
    return m;
}

int main(int argc, char **argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    setvbuf(stderr, nullptr, _IONBF, 0);
    if (argc < 3) {
        fprintf(stderr,
                "usage: %s N K [options]\n"
                "  --trials T --nodes-per M --greedy G --expand-iters I\n"
                "  --two-swap B --constrained R --seed S --max-sets M\n"
                "  --out PATH --witness-bin PATH (append known masks)\n",
                argv[0]);
        return 2;
    }
    N = atoi(argv[1]);
    TARGET = atoi(argv[2]);
    if (N <= 0 || N > 10 || TARGET <= 0) {
        fprintf(stderr, "bad N/K\n");
        return 2;
    }

    int trials = 80;
    long long nodes_per = 80000;
    int greedy = 2000;
    int expand_iters = 6;
    int two_swap = 40;
    int constrained = 40;
    unsigned long long seed = 20260919ULL;
    max_sets_cap = 400;
    std::string out_path;
    std::string witness_bin;

    for (int i = 3; i < argc; i++) {
        std::string a = argv[i];
        auto need = [&](int k) {
            if (i + k >= argc) {
                fprintf(stderr, "missing arg after %s\n", a.c_str());
                exit(2);
            }
        };
        if (a == "--trials") {
            need(1);
            trials = atoi(argv[++i]);
        } else if (a == "--nodes-per") {
            need(1);
            nodes_per = atoll(argv[++i]);
        } else if (a == "--greedy") {
            need(1);
            greedy = atoi(argv[++i]);
        } else if (a == "--expand-iters") {
            need(1);
            expand_iters = atoi(argv[++i]);
        } else if (a == "--two-swap") {
            need(1);
            two_swap = atoi(argv[++i]);
        } else if (a == "--constrained") {
            need(1);
            constrained = atoi(argv[++i]);
        } else if (a == "--seed") {
            need(1);
            seed = strtoull(argv[++i], nullptr, 10);
        } else if (a == "--max-sets") {
            need(1);
            max_sets_cap = atoi(argv[++i]);
        } else if (a == "--out") {
            need(1);
            out_path = argv[++i];
        } else if (a == "--witness-bin") {
            need(1);
            witness_bin = argv[++i];
        } else {
            fprintf(stderr, "unknown arg %s\n", a.c_str());
            return 2;
        }
    }

    rng.seed(seed);
    build_geometry();
    build_d4();

    // Hardcoded known n=8 witness from cycle6-maxsafeset-n8-15.json
    if (N == 8 && TARGET == 15) {
        std::vector<std::pair<int, int>> wit = {
            {0,0},{1,0},{2,0},{1,1},{7,1},{3,2},{7,2},{5,3},
            {0,4},{2,5},{4,5},{5,6},{0,7},{4,7},{5,7}};
        u64 wmask = pts_to_mask(wit);
        if (popc(wmask) == TARGET && is_safe_mask(wmask)) {
            for (int m = 0; m < 8; m++) record(apply_d4(wmask, m));
        }
    }

    if (!witness_bin.empty()) {
        FILE *fp = fopen(witness_bin.c_str(), "rb");
        if (fp) {
            u64 m;
            while (fread(&m, 8, 1, fp) == 1) {
                if (popc(m) == TARGET && m < (V >= 64 ? ~0ULL : (1ULL << V)) &&
                    is_safe_mask(m))
                    for (int k = 0; k < 8; k++) record(apply_d4(m, k));
            }
            fclose(fp);
        }
    }

    long long after_d4 = (long long)found.size();
    run_dfs_trials(trials, nodes_per);
    long long after_dfs = (long long)found.size();
    run_greedy(greedy);
    long long after_greedy = (long long)found.size();
    long long swap_added = expand_swaps(expand_iters, two_swap);
    long long after_swap = (long long)found.size();
    run_constrained_diversity(constrained, nodes_per / 4 + 1000);
    // final swap pass
    swap_added += expand_swaps(3, two_swap / 2 + 10);
    long long after_all = (long long)found.size();

    std::vector<u64> sets(found.begin(), found.end());
    if (!out_path.empty()) {
        FILE *fp = fopen(out_path.c_str(), "wb");
        if (fp) {
            for (u64 s : sets) fwrite(&s, 8, 1, fp);
            fclose(fp);
        }
    }

    printf("{\n");
    printf("  \"package\": \"G3-sampler\",\n");
    printf("  \"evidence\": \"SAMPLE\",\n");
    printf("  \"n\": %d,\n", N);
    printf("  \"K\": %d,\n", TARGET);
    printf("  \"quads\": %d,\n", n_quads_total);
    printf("  \"seed\": %llu,\n", seed);
    printf("  \"after_d4\": %lld,\n", after_d4);
    printf("  \"after_dfs\": %lld,\n", after_dfs);
    printf("  \"after_greedy\": %lld,\n", after_greedy);
    printf("  \"after_swap\": %lld,\n", after_swap);
    printf("  \"after_all\": %lld,\n", after_all);
    printf("  \"swap_added\": %lld,\n", swap_added);
    printf("  \"d4_canon_classes\": %zu,\n", found_canon.size());
    printf("  \"dfs_solutions\": %lld,\n", dfs_solutions);
    printf("  \"greedy_trials\": %lld,\n", greedy_trials);
    printf("  \"greedy_hits_ge_K\": %lld,\n", greedy_hits);
    printf("  \"max_sets_cap\": %d,\n", max_sets_cap);
    printf("  \"out\": \"%s\",\n", out_path.c_str());
    printf("  \"n_sets_written\": %zu\n", sets.size());
    printf("}\n");
    return 0;
}
