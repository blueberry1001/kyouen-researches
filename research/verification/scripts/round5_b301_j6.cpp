// Round5 B301-B400: compute J_6 (first-move response graph for 6x6).
// J_n: vertices = board points; edge {p,q} iff g({p,q}) == 0 (2-stone P-position).
// Also extracts one-stone grundy, full two-stone spectrum, bridges/articulation
// points of the non-isolated part, perfect matching existence, D4 types.
//
// Build: g++ -O2 -std=c++20 -o /tmp/j6 round5_b301_j6.cpp
// Self-check: n=4 must give E=84, PM count from known 112212 (we only test
// existence + a few structural invariants), n=5 two-stone spectrum from known.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <unordered_map>
#include <map>
#include <set>
#include <queue>
#include <stack>
#include <chrono>

#include "kc_core.h"

using u64 = uint64_t;
using namespace kc;

static int popcount(u64 x) { return __builtin_popcountll(x); }

// ---------------------------------------------------------------- Grundy
// Memoized DFS. Terminal (no legal moves) => g=0.
struct Solver {
    const Board& b;
    std::unordered_map<u64, int> memo;
    long long nodes = 0;

    explicit Solver(const Board& bb) : b(bb) {}

    int grundy(u64 occ) {
        auto it = memo.find(occ);
        if (it != memo.end()) return it->second;
        u64 L = legal_mask(b, occ);
        if (L == 0) {
            memo[occ] = 0;
            return 0;
        }
        // collect child grundy values
        // max stones on 6x6 is ~10, so mex is small
        int seen[64];
        memset(seen, 0, sizeof(seen));
        u64 m = L;
        while (m) {
            int p = __builtin_ctzll(m);
            m &= m - 1;
            int g = grundy(occ | (u64(1) << p));
            if (g < 64) seen[g] = 1;
        }
        int g = 0;
        while (g < 64 && seen[g]) ++g;
        memo[occ] = g;
        ++nodes;
        return g;
    }
};

// ---------------------------------------------------------------- graphs
struct Graph {
    int V;
    std::vector<std::set<int>> adj;  // undirected, no self-loops
    explicit Graph(int v) : V(v), adj(v) {}
    void add(int a, int c) {
        if (a == c) return;
        adj[a].insert(c);
        adj[c].insert(a);
    }
    int n_edges() const {
        int e = 0;
        for (int i = 0; i < V; ++i) e += (int)adj[i].size();
        return e / 2;
    }
    std::vector<int> nonisolated() const {
        std::vector<int> r;
        for (int i = 0; i < V; ++i)
            if (!adj[i].empty()) r.push_back(i);
        return r;
    }
};

static void bridges_arts(const Graph& g, std::vector<std::pair<int, int>>& bridges,
                         std::vector<int>& arts) {
    int V = g.V;
    std::vector<int> disc(V, -1), low(V, -1), parent(V, -1);
    bridges.clear();
    arts.clear();
    int timer = 0;
    for (int root = 0; root < V; ++root) {
        if (disc[root] >= 0 || g.adj[root].empty()) continue;
        // iterative DFS
        std::vector<int> st;
        std::vector<int> it(V, 0);
        st.push_back(root);
        disc[root] = low[root] = timer++;
        int children = 0;
        parent[root] = -1;
        while (!st.empty()) {
            int u = st.back();
            // iterate neighbors via a snapshot list
            // rebuild neighbor vector once per u visit
            if (it[u] == 0) {
                // first time expanding u: store neighbor list in a side map
            }
            bool adv = false;
            // We need ordered neighbor iteration. Convert set to vector on the fly.
            std::vector<int> nbrs(g.adj[u].begin(), g.adj[u].end());
            while (it[u] < (int)nbrs.size()) {
                int v = nbrs[it[u]++];
                if (disc[v] < 0) {
                    parent[v] = u;
                    if (u == root) ++children;
                    disc[v] = low[v] = timer++;
                    st.push_back(v);
                    adv = true;
                    break;
                } else if (parent[u] != v) {
                    low[u] = std::min(low[u], disc[v]);
                }
            }
            if (!adv) {
                st.pop_back();
                int pu = parent[u];
                if (pu >= 0) {
                    low[pu] = std::min(low[pu], low[u]);
                    if (low[u] > disc[pu]) bridges.push_back({std::min(pu, u), std::max(pu, u)});
                    if (low[u] >= disc[pu] && pu != root) arts.push_back(pu);
                } else if (children > 1) {
                    arts.push_back(u);
                }
            }
        }
    }
    std::sort(arts.begin(), arts.end());
    arts.erase(std::unique(arts.begin(), arts.end()), arts.end());
    std::sort(bridges.begin(), bridges.end());
}

// Hopcroft-Karp style / simple augmenting path perfect matching on general graph.
// For |V|<=36 this is fine with recursive Kuhn on a general graph via Edmonds
// blossom is hard; we use a simple DFS matching that works for bipartite, and
// for general graphs we use a randomized/exhaustive augmenting path on general
// graphs via Edmonds' blossom simplified for small n: recursive search.
// For J_n (dense enough) we use a simple greedy + augmenting (blossom-free)
// via "matching via recursive backtracking" on V<=36 which can be slow.
// Better: use a bitmask DP for perfect matching existence on V<=36? 2^36 too big.
// Use Edmonds blossom (CP-algorithms style, O(V^3)).
struct Blossom {
    int n;
    std::vector<std::vector<int>> a;
    std::vector<int> match, p, base;
    std::vector<bool> used, blossom;
    std::queue<int> q;
    Blossom(int n) : n(n), a(n), match(n, -1), p(n), base(n), used(n), blossom(n) {}
    void addEdge(int u, int v) {
        if (u == v) return;
        a[u].push_back(v);
        a[v].push_back(u);
    }
    int lca(int u, int v) {
        std::vector<bool> used_lca(n, false);
        for (;;) {
            u = base[u];
            used_lca[u] = true;
            if (match[u] == -1) break;
            u = p[match[u]];
        }
        for (;;) {
            v = base[v];
            if (used_lca[v]) return v;
            v = p[match[v]];
        }
    }
    void markPath(int v, int b, int children) {
        while (base[v] != b) {
            blossom[base[v]] = blossom[base[match[v]]] = true;
            p[v] = children;
            children = match[v];
            v = p[match[v]];
        }
    }
    int findPath(int root) {
        used.assign(n, false);
        p.assign(n, -1);
        for (int i = 0; i < n; ++i) base[i] = i;
        used[root] = true;
        q = std::queue<int>();
        q.push(root);
        while (!q.empty()) {
            int v = q.front();
            q.pop();
            for (int u : a[v]) {
                if (base[v] == base[u] || match[v] == u) continue;
                if (u == root || (match[u] != -1 && p[match[u]] != -1)) {
                    int curbase = lca(v, u);
                    blossom.assign(n, false);
                    markPath(v, curbase, u);
                    markPath(u, curbase, v);
                    for (int i = 0; i < n; ++i)
                        if (blossom[base[i]]) {
                            base[i] = curbase;
                            if (!used[i]) {
                                used[i] = true;
                                q.push(i);
                            }
                        }
                } else if (p[u] == -1) {
                    p[u] = v;
                    if (match[u] == -1) return u;
                    u = match[u];
                    used[u] = true;
                    q.push(u);
                }
            }
        }
        return -1;
    }
    int maxMatching() {
        for (int i = 0; i < n; ++i) {
            if (match[i] == -1) {
                int v = findPath(i);
                while (v != -1) {
                    int pv = p[v], ppv = match[pv];
                    match[v] = pv;
                    match[pv] = v;
                    v = ppv;
                }
            }
        }
        int c = 0;
        for (int i = 0; i < n; ++i)
            if (match[i] >= 0) ++c;
        return c / 2;
    }
    bool hasPerfect() {
        if (n % 2) return false;
        return maxMatching() * 2 == n;
    }
    bool hasNearPerfect() {
        return maxMatching() * 2 == n - 1;
    }
};

// ---------------------------------------------------------------- D4
static void d4_maps(int n, std::vector<std::vector<int>>& maps) {
    auto pt = [n](int x, int y) { return y * n + x; };
    auto inv = [n](int i, int& x, int& y) { x = i % n; y = i / n; };
    using F = void (*)(int, int, int, int&, int&);
    // 8 dihedral maps
    struct M {
        int kind;
    };
    maps.assign(8, std::vector<int>(n * n));
    for (int i = 0; i < n * n; ++i) {
        int x, y;
        inv(i, x, y);
        int X[8], Y[8];
        X[0] = x; Y[0] = y;
        X[1] = y; Y[1] = n - 1 - x;
        X[2] = n - 1 - x; Y[2] = n - 1 - y;
        X[3] = n - 1 - y; Y[3] = x;
        X[4] = n - 1 - x; Y[4] = y;
        X[5] = x; Y[5] = n - 1 - y;
        X[6] = y; Y[6] = x;
        X[7] = n - 1 - y; Y[7] = n - 1 - x;
        for (int t = 0; t < 8; ++t) maps[t][i] = pt(X[t], Y[t]);
    }
}

// ---------------------------------------------------------------- analysis
struct JResult {
    int n = 0;
    int V = 0;
    int E = 0;
    int n_iso = 0;
    int n_bridges = 0;
    int n_arts = 0;
    bool has_pm = false;
    bool has_near_pm = false;
    int n_P_pairs = 0;
    int two_g_hist[32];
    int one_g_hist[32];
    int g_empty = -1;
    long long states = 0;
    long long nodes = 0;
    int n_d4_types_P = 0;
    int n_d4_types_TD = 0;
    int n_TD_pairs = 0;
    bool all_TD_are_P = true;
    int max_degree = 0;
    int min_degree_noniso = 999;
    int n_components_noniso = 0;
};

static int count_components(const Graph& g) {
    int V = g.V;
    std::vector<bool> seen(V, false);
    int c = 0;
    for (int s = 0; s < V; ++s) {
        if (seen[s] || g.adj[s].empty()) continue;
        ++c;
        std::queue<int> q;
        q.push(s);
        seen[s] = true;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : g.adj[u])
                if (!seen[v]) {
                    seen[v] = true;
                    q.push(v);
                }
        }
    }
    return c;
}

// total-dominating pair: the pair {a,b} such that every vertex of J is adjacent
// (in J) to at least one of a,b. (For B312.)
static int count_total_dom_pairs(const Graph& g) {
    int V = g.V;
    int cnt = 0;
    for (int a = 0; a < V; ++a)
        for (int c = a + 1; c < V; ++c) {
            bool ok = true;
            for (int v = 0; v < V && ok; ++v) {
                if (v == a || v == c) {
                    // v must be adjacent to the other one (or itself covered)
                    // total domination: every vertex has a neighbor in the set
                    // For v=a: need a adjacent to c (or some member)
                    bool covered = (g.adj[a].count(c) || g.adj[c].count(a));
                    // also a could be covered by... only members are a,c
                    // so a must be adjacent to c (since a not adjacent to itself)
                    if (!covered) ok = false;
                } else {
                    if (!g.adj[v].count(a) && !g.adj[v].count(c)) ok = false;
                }
            }
            if (ok) ++cnt;
        }
    return cnt;
}

static void run_one(int n, JResult& R, bool dump_j) {
    auto t0 = std::chrono::steady_clock::now();
    Board b;
    build_square(b, n);
    Solver sol(b);
    int g_empty = sol.grundy(0);
    R.n = n;
    R.V = b.V;
    R.g_empty = g_empty;
    R.states = (long long)sol.memo.size();
    R.nodes = sol.nodes;
    memset(R.two_g_hist, 0, sizeof(R.two_g_hist));
    memset(R.one_g_hist, 0, sizeof(R.one_g_hist));

    Graph J(b.V);
    int E = 0;
    for (int a = 0; a < b.V; ++a) {
        int g1 = sol.grundy(u64(1) << a);
        if (g1 >= 0 && g1 < 32) R.one_g_hist[g1]++;
        for (int c = a + 1; c < b.V; ++c) {
            u64 occ = (u64(1) << a) | (u64(1) << c);
            // only safe pairs matter; if unsafe, skip (not a real position)
            if (legal_mask(b, occ) == 0 && !/* still could be terminal */ false) {
                // even if no legal moves it is a P-position (g=0) if safe
            }
            // check safety: occ is safe iff no quad fully inside
            bool safe = true;
            for (u64 q : b.quads) {
                if ((occ & q) == q) {
                    safe = false;
                    break;
                }
            }
            if (!safe) continue;
            int g = sol.grundy(occ);
            if (g >= 0 && g < 32) R.two_g_hist[g]++;
            if (g == 0) {
                J.add(a, c);
                ++E;
            }
        }
    }
    R.E = E;
    R.n_P_pairs = E;

    // degrees
    R.max_degree = 0;
    R.min_degree_noniso = 999;
    for (int i = 0; i < b.V; ++i) {
        int d = (int)J.adj[i].size();
        if (d > R.max_degree) R.max_degree = d;
        if (d > 0 && d < R.min_degree_noniso) R.min_degree_noniso = d;
        if (d == 0) R.n_iso++;
    }

    // bridges / arts on the whole J (isolated vertices contribute nothing)
    std::vector<std::pair<int, int>> br;
    std::vector<int> arts;
    bridges_arts(J, br, arts);
    R.n_bridges = (int)br.size();
    R.n_arts = (int)arts.size();
    R.n_components_noniso = count_components(J);

    // perfect matching on non-isolated part? Use full J including isolates.
    // Isolates block perfect matching. Report both.
    Blossom bl(b.V);
    for (int i = 0; i < b.V; ++i)
        for (int v : J.adj[i])
            if (i < v) bl.addEdge(i, v);
    int mm = bl.maxMatching();
    R.has_pm = (mm * 2 == b.V);
    R.has_near_pm = (mm * 2 == b.V - 1);

    // D4 types of P-pairs
    {
        std::vector<std::vector<int>> maps;
        d4_maps(n, maps);
        std::set<std::pair<int, int>> pset;
        for (int a = 0; a < b.V; ++a)
            for (int c = a + 1; c < b.V; ++c)
                if (J.adj[a].count(c)) pset.insert({a, c});
        std::set<std::pair<int, int>> done;
        int types = 0;
        for (auto& pr : pset) {
            if (done.count(pr)) continue;
            // orbit
            std::set<std::pair<int, int>> orb;
            for (auto& mp : maps) {
                int u = mp[pr.first], v = mp[pr.second];
                if (u > v) std::swap(u, v);
                orb.insert({u, v});
            }
            for (auto& o : orb) done.insert(o);
            ++types;
        }
        R.n_d4_types_P = types;
    }

    // total-dominating pairs in J
    R.n_TD_pairs = count_total_dom_pairs(J);
    // check all TD are P: by construction TD pairs are pairs of vertices; a TD
    // pair is automatically a pair of board points. "All TD are P" means every
    // TD pair is an edge of J. (That is the B312 claim.)
    {
        int bad = 0;
        int V = b.V;
        for (int a = 0; a < V; ++a)
            for (int c = a + 1; c < V; ++c) {
                bool ok = true;
                for (int v = 0; v < V && ok; ++v) {
                    if (v == a || v == c) {
                        bool covered = J.adj[a].count(c) || J.adj[c].count(a);
                        if (!covered) ok = false;
                    } else {
                        if (!J.adj[v].count(a) && !J.adj[v].count(c)) ok = false;
                    }
                }
                if (ok && !J.adj[a].count(c)) ++bad;
            }
        R.all_TD_are_P = (bad == 0);
    }

    // D4 types of TD pairs
    {
        std::vector<std::vector<int>> maps;
        d4_maps(n, maps);
        std::set<std::pair<int, int>> td;
        int V = b.V;
        for (int a = 0; a < V; ++a)
            for (int c = a + 1; c < V; ++c) {
                bool ok = true;
                for (int v = 0; v < V && ok; ++v) {
                    if (v == a || v == c) {
                        bool covered = J.adj[a].count(c) || J.adj[c].count(a);
                        if (!covered) ok = false;
                    } else {
                        if (!J.adj[v].count(a) && !J.adj[v].count(c)) ok = false;
                    }
                }
                if (ok) td.insert({a, c});
            }
        std::set<std::pair<int, int>> done;
        int types = 0;
        for (auto& pr : td) {
            if (done.count(pr)) continue;
            std::set<std::pair<int, int>> orb;
            for (auto& mp : maps) {
                int u = mp[pr.first], v = mp[pr.second];
                if (u > v) std::swap(u, v);
                orb.insert({u, v});
            }
            for (auto& o : orb) done.insert(o);
            ++types;
        }
        R.n_d4_types_TD = types;
    }

    auto t1 = std::chrono::steady_clock::now();
    double sec = std::chrono::duration<double>(t1 - t0).count();

    printf("=== n=%d ===\n", n);
    printf("V=%d E=%d iso=%d g_empty=%d states=%lld nodes=%lld\n", R.V, R.E, R.n_iso,
           R.g_empty, R.states, R.nodes);
    printf("bridges=%d arts=%d comps_noniso=%d maxdeg=%d mindeg_noniso=%d\n",
           R.n_bridges, R.n_arts, R.n_components_noniso, R.max_degree,
           R.min_degree_noniso);
    printf("PM=%d nearPM=%d matching_size=%d\n", (int)R.has_pm, (int)R.has_near_pm, mm);
    printf("two_g_hist:");
    for (int i = 0; i < 32; ++i)
        if (R.two_g_hist[i]) printf(" %d:%d", i, R.two_g_hist[i]);
    printf("\n");
    printf("one_g_hist:");
    for (int i = 0; i < 32; ++i)
        if (R.one_g_hist[i]) printf(" %d:%d", i, R.one_g_hist[i]);
    printf("\n");
    printf("TD_pairs=%d all_TD_are_P=%d TD_d4_types=%d P_d4_types=%d\n", R.n_TD_pairs,
           (int)R.all_TD_are_P, R.n_d4_types_TD, R.n_d4_types_P);
    printf("time=%.2fs\n", sec);
    fflush(stdout);

    if (dump_j) {
        // dump J as edge list + two-stone grundy
        char path[256];
        snprintf(path, sizeof(path), "round5_b301_j%d.txt", n);
        FILE* f = fopen(path, "w");
        if (f) {
            fprintf(f, "n=%d V=%d E=%d g_empty=%d states=%lld\n", n, R.V, R.E, R.g_empty,
                    R.states);
            fprintf(f, "two_g\n");
            for (int a = 0; a < b.V; ++a)
                for (int c = a + 1; c < b.V; ++c) {
                    u64 occ = (u64(1) << a) | (u64(1) << c);
                    bool safe = true;
                    for (u64 q : b.quads)
                        if ((occ & q) == q) {
                            safe = false;
                            break;
                        }
                    if (!safe) continue;
                    int g = sol.grundy(occ);
                    fprintf(f, "%d %d %d\n", a, c, g);
                }
            fprintf(f, "one_g\n");
            for (int a = 0; a < b.V; ++a) fprintf(f, "%d %d\n", a, sol.grundy(u64(1) << a));
            fclose(f);
        }
    }
}

int main(int argc, char** argv) {
    int nmax = 6;
    if (argc > 1) nmax = atoi(argv[1]);
    for (int n = 2; n <= nmax; ++n) {
        JResult R;
        run_one(n, R, /*dump_j=*/n >= 5);
    }
    return 0;
}
