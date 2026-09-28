// round4_firstmoves.cpp -- Round4 chunk b002-b091, Part 1 (the decisive part).
//
// PURPOSE
//   The single open question in this chunk was: for the two known *second-player
//   win* square boards n=7 and n=8, are the winning first moves W_n = {p :
//   g({p}) = 0} empty, or is there a mix of winning / losing first moves?
//
//   Two things are computed here, with exact integer arithmetic only.
//
//   (A) LOGICAL CLOSURE.  g(empty) = mex { g({p}) : p legal }.  If g(empty)=0
//       then 0 is not in the set of option values, hence g({p}) != 0 for EVERY
//       p, hence W_n = {} -- with *no* enumeration needed.  So for a
//       second-player-win board the first-move table is fully determined: 0
//       winning first moves, all n^2 first moves are losing.  We record the
//       proof obligation, not just the conclusion.
//
//   (B) THE NIMBER VALUES.  Knowing g({p}) != 0 is cheap; knowing *which* non-zero
//       nimber occurs at each point is the real content, and it is what feeds
//       B010 / B016 / B020 / B021.  For n=7 this is completely tractable: the
//       protocol records K_7 = 14 with only 16 maximal safe sets, so the whole
//       reachable state space is the union of 16 power sets of size 2^14, i.e.
//       <= 262144 positions.  We do a *full* memoised Grundy over every safe
//       set, which simultaneously yields
//         * g({p}) for all 49 points of n=7 (and a D4 orbit-constancy check),
//         * J_7, the P-pair graph (B016) -- previously unreachable,
//         * the layer profile M_7(k) and sigma_7 (B021) -- previously unreachable,
//         * the maximal-safe-set count (cross-check against the recorded 16).
//       n=8 is NOT tractable: it has 64 points, K_8=15, and its safe sets are
//       far too numerous (we measure the exact count per size to quantify this).
//       For n=8 we therefore measure the state-space size exactly, and the
//       first-move verdict comes from (A).
//
//   Everything is one uint64 mask per position; no floating point is used.
//   Note the board itself is a fixed n x n lattice, so "maximal safe set" and
//   "reachable position" coincide: a safe subset S is reachable by adding its
//   points in any order (every intermediate set is a subset of S, hence safe).
//
// USAGE
//   g++ -O2 -std=c++20 -o /tmp/fm round4_firstmoves.cpp
//   /tmp/fm [maxk_n8]        (default 6; 7 is much slower)
//
// OUTPUT: JSON on stdout (redirect to research/verification/round4_firstmoves.json)

#include "kc_core.h"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <functional>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

using kc::Board;
using kc::u64;

// ---------------------------------------------------------------- utilities

static int popcnt(u64 m) { return __builtin_popcountll(m); }

// The 8 elements of the dihedral group D4, as coordinate maps (x,y) -> (X,Y).
// Used only to *report* the orbit decomposition of the 1-stone layer and to
// cross-check that the computed g({p}) really is constant on orbits.
struct Sym { const char* name; int f[8]; };  // f: 0..7 -> 0..3, encoding 2X = f[2k], 2Y = f[2k+1]

static std::vector<Sym> d4() {
    return {
        {"id",     {0, 0, 1, 0}},
        {"rot90",  {1, 1, 0, 0}},
        {"rot180", {0, 1, 0, 1}},
        {"rot270", {1, 0, 0, 1}},
        {"reflH",  {0, 1, 1, 0}},
        {"reflV",  {1, 0, 0, 1}},
        {"reflD",  {0, 0, 1, 1}},   // x <-> y
        {"reflA",  {1, 1, 0, 0}},   // anti-diagonal
    };
}

static void apply_sym(const Sym& s, int x, int y, int n, int& X, int& Y) {
    X = (s.f[0] * x + s.f[1] * y) / 2;
    Y = (s.f[2] * x + s.f[3] * y) / 2;
    (void)n;
}

// Orbits of single points under D4, plus a canonical representative (smallest
// point id) for each orbit.
static void point_orbits(int n, std::vector<int>& rep_of, int& n_orbits,
                         std::vector<int>& reps) {
    auto syms = d4();
    std::vector<int> canon(n * n, -1);
    rep_of.assign(n * n, -1);
    reps.clear();
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int id = y * n + x;
            int best = id;
            for (auto& s : syms) {
                int X, Y;
                apply_sym(s, x, y, n, X, Y);
                best = std::min(best, Y * n + X);
            }
            canon[id] = best;
        }
    std::vector<char> seen(n * n, 0);
    for (int id = 0; id < n * n; ++id) {
        int c = canon[id];
        if (!seen[c]) { seen[c] = 1; reps.push_back(c); }
    }
    n_orbits = (int)reps.size();
    for (int id = 0; id < n * n; ++id) rep_of[id] = canon[id];
}

// ------------------------------------------------- enumerate all safe subsets

// Progress goes to stderr: stdout carries the JSON.
static void prog(const char* what, long long done) {
    fprintf(stderr, "[%lld] %s: %lld found\n", (long long)time(nullptr), what, done);
}

static void enumerate_safe(const Board& b, int maxk, std::vector<u64>& out) {
    out.clear();
    u64 mask = 0;
    long long last = (long long)time(nullptr);
    std::function<void(int, int)> rec = [&](int start, int k) {
        out.push_back(mask);
        if (k == maxk) return;
        for (int p = start; p < b.V; ++p) {
            if (!kc::can_add(b, mask, p)) continue;
            mask |= u64(1) << p;
            rec(p + 1, k + 1);
            mask &= ~(u64(1) << p);
        }
        if ((long long)time(nullptr) != last) {
            last = (long long)time(nullptr);
            prog("enumerate", (long long)out.size());
        }
    };
    rec(0, 0);
}

// ------------------------------------------------------ full Grundy (n<=7)

// g(S) for every safe S, by increasing |S|.  Only |S| < n^2 can have a legal
// move, but we simply try every point; for a maximal set legal_mask == 0 and
// g(S) = mex({}) = 0, which is correct.
static void full_grundy(const Board& b, const std::vector<u64>& safe,
                        std::unordered_map<u64, int>& g) {
    const int V = b.V;
    std::vector<std::vector<u64>> bysize(V + 1);
    for (u64 s : safe) bysize[popcnt(s)].push_back(s);
    g.clear();
    g.reserve(safe.size() * 2);
    g[0] = 0;  // will be recomputed in order below
    std::vector<char> seen(V + 2, 0);
    for (int k = 0; k <= V; ++k) {
        for (u64 s : bysize[k]) {
            u64 lm = kc::legal_mask(b, s);
            std::fill(seen.begin(), seen.end(), 0);
            int mx = 0;
            while (lm) {
                int p = __builtin_ctzll(lm);
                lm &= lm - 1;
                u64 t = s | (u64(1) << p);
                auto it = g.find(t);
                if (it != g.end()) {
                    int v = it->second;
                    seen[v] = 1;
                    if (v > mx) mx = v;
                }
            }
            int m = 0;
            while (seen[m]) ++m;
            g[s] = m;
        }
    }
}

// ----------------------------------------------------------------- reporting

static std::string jbool(bool b) { return b ? "true" : "false"; }

int main(int argc, char** argv) {
    int n8_maxk = 6;
    if (argc > 1) n8_maxk = atoi(argv[1]);
    if (n8_maxk < 0 || n8_maxk > 8) n8_maxk = 6;
    // Line-buffer stdout: the n=7 full Grundy is the long pole, and we want its
    // numbers on disk as soon as they exist rather than only at exit.
    setvbuf(stdout, nullptr, _IOLBF, 1 << 16);

    printf("{\n");
    printf("  \"script\": \"research/verification/scripts/round4_firstmoves.cpp\",\n");
    printf("  \"arithmetic\": \"exact integers only (det4 == 0 for forbidden 4-sets); no floating point\",\n");

    // =====================================================================
    // PART 1 -- the logical closure that settles the first-move question.
    // =====================================================================
    printf("  \"firstmove_question\": {\n");
    printf("    \"statement\": \"g(empty)=mex{g({p})}. So g(empty)=0 forces g({p})!=0 for every p, i.e. W_n = {} and all n^2 first moves lose.\",\n");
    printf("    \"consequence\": \"A second-player-win square board has ZERO winning first moves; the mixed case (some losing first moves) is impossible for it.\",\n");
    printf("    \"empty_winner_n1_to_10\": [\"F\",\"F\",\"F\",\"S\",\"F\",\"F\",\"S\",\"S\",\"F\",\"S\"],\n");
    printf("    \"board_winner_table\": {\n");
    const int w10[11] = {0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0};  // 1 = first player wins
    for (int n = 1; n <= 10; ++n) {
        const char* cls = (n == 7 || n == 8)
            ? "all_first_moves_lose (0 winning, n^2 losing)"
            : (w10[n] ? "all_first_moves_win (n^2 winning, 0 losing)" : "all_first_moves_lose (0 winning, n^2 losing)");
        printf("      \"n=%d\": {\"winner\": \"%s\", \"class\": \"%s\", \"W_size\": %d, \"n_squared\": %d}%s\n",
               n, w10[n] ? "first" : "second", cls, w10[n] ? n * n : 0, n * n,
               n == 10 ? "" : ",");
    }
    printf("    },\n");
    printf("    \"n7_verdict\": \"SUPPORTED-BY-CONSTRUCTION: W_7 = {} ; all 49 first moves lose. No enumeration required.\",\n");
    printf("    \"n8_verdict\": \"SUPPORTED-BY-CONSTRUCTION: W_8 = {} ; all 64 first moves lose. No enumeration required.\",\n");
    printf("    \"caveat\": \"This settles the WIN/LOSS classification, not the nimber values. The nimber multiset {g({p})} is a strictly finer datum and is what Part 2 computes for n=7.\"\n");
    printf("  },\n");

    // =====================================================================
    // PART 2 -- full Grundy for n=7 (all 49 first moves, J_7, sigma_7).
    // =====================================================================
    {
        Board b; kc::build_square(b, 7);
        std::vector<u64> safe;
        enumerate_safe(b, b.V, safe);
        std::vector<int> bysz(b.V + 1, 0);
        for (u64 s : safe) ++bysz[popcnt(s)];

        std::unordered_map<u64, int> g;
        full_grundy(b, safe, g);

        int g0 = g.at(u64(0));

        // --- 1-stone layer -----------------------------------------------
        std::vector<int> g1(b.V, 0);
        std::map<int, int> g1_hist;
        int W = 0;
        for (int p = 0; p < b.V; ++p) {
            g1[p] = g.at(u64(1) << p);
            ++g1_hist[g1[p]];
            if (g1[p] == 0) ++W;
        }
        std::vector<int> rep_of; int norb = 0; std::vector<int> reps;
        point_orbits(7, rep_of, norb, reps);
        bool orb_const = true;
        for (int p = 0; p < b.V; ++p)
            if (g1[p] != g1[rep_of[p]]) orb_const = false;
        // sum over orbits of orbit size * g  (as a cheap checksum)
        int orb_sum = 0;
        for (int r : reps) orb_sum += g1[r];

        // --- J_7: the P-pair graph ---------------------------------------
        int edges = 0, noniso = 0, bip = 1;
        std::map<int, int> deghist;
        std::vector<int> deg(b.V, 0);
        std::vector<std::pair<int, int>> E;
        for (int a = 0; a < b.V; ++a)
            for (int c = a + 1; c < b.V; ++c) {
                int gg = g.at((u64(1) << a) | (u64(1) << c));
                if (gg == 0) { E.emplace_back(a, c); ++deg[a]; ++deg[c]; ++edges; }
            }
        for (int p = 0; p < b.V; ++p) { if (deg[p]) ++noniso; ++deghist[deg[p]]; }
        {   // components (union-find) + bipartite check (BFS)
            std::vector<int> par(b.V);
            for (int i = 0; i < b.V; ++i) par[i] = i;
            std::function<int(int)> find = [&](int v) { while (par[v] != v) { par[v] = par[par[v]]; v = par[v]; } return v; };
            for (auto& e : E) { int ra = find(e.first), rc = find(e.second); if (ra != rc) par[ra] = rc; }
            std::map<int, int> compsize;
            for (int i = 0; i < b.V; ++i) compsize[find(i)]++;
            std::vector<std::vector<int>> adj(b.V);
            for (auto& e : E) { adj[e.first].push_back(e.second); adj[e.second].push_back(e.first); }
            std::vector<int> col(b.V, -1);
            for (int s = 0; s < b.V; ++s) {
                if (col[s] != -1 || adj[s].empty()) continue;
                std::vector<int> q{s}; col[s] = 0;
                for (size_t h = 0; h < q.size(); ++h) {
                    int v = q[h];
                    for (int w : adj[v]) {
                        if (col[w] == -1) { col[w] = col[v] ^ 1; q.push_back(w); }
                        else if (col[w] == col[v]) bip = 0;
                    }
                }
            }
            printf("  \"n7_full\": {\n");
            printf("    \"V\": 49, \"F_7\": %d,\n", (int)b.quads.size());
            printf("    \"safe_sets_total\": %d,\n", (int)safe.size());
            printf("    \"safe_sets_by_size\": {");
            for (int k = 0; k <= b.V; ++k) printf("%s%d: %d", k ? ", " : "", k, bysz[k]);
            printf("},\n");
            printf("    \"g_empty\": %d,\n", g0);
            printf("    \"g1_by_point\": [");
            for (int p = 0; p < b.V; ++p) printf("%s%d", p ? ", " : "", g1[p]);
            printf("],\n");
            printf("    \"g1_histogram\": {");
            { bool f = true; for (auto& kv : g1_hist) { printf("%s%d: %d", f ? "" : ", ", kv.first, kv.second); f = false; } }
            printf("},\n");
            printf("    \"W7_size\": %d, \"W7\": \"empty (all 49 first moves lose)\",\n", W);
            printf("    \"d4_point_orbits\": %d, \"d4_orbit_constant_on_g1\": %s, \"d4_orbit_g_values\": [",
                   norb, jbool(orb_const).c_str());
            { bool f = true; for (int r : reps) { printf("%s%d", f ? "" : ", ", g1[r]); f = false; } }
            printf("], \"d4_orbit_reps_xy\": [");
            { bool f = true; for (int r : reps) { printf("%s[%d,%d]", f ? "" : ", ", r % 7, r / 7); f = false; } }
            printf("], \"d4_checksum_sum_of_g1\": %d,\n", orb_sum);
            int ncomp_noniso = 0, largest = 0;
            for (auto& kv : compsize) { if (kv.second > 1) ++ncomp_noniso; largest = std::max(largest, kv.second); }
            printf("    \"J7\": {\"edges\": %d, \"nonisolated\": %d, \"degree_histogram\": {", edges, noniso);
            { bool f = true; for (auto& kv : deghist) { printf("%s%d: %d", f ? "" : ", ", kv.first, kv.second); f = false; } }
            printf("}, \"components_all\": %d, \"components_nonisolated\": %d, \"bipartite\": %s, \"largest_component\": %d},\n",
                   (int)compsize.size(), ncomp_noniso, jbool(bip == 1).c_str(), largest);
        }
        // layer profile + sigma
        {
            std::vector<int> Mk(b.V + 1, -1), cntM(b.V + 1, 0);
            std::map<int,int> gall;
            for (u64 s : safe) { int k = popcnt(s); int v = g.at(s); ++gall[v]; if (v > Mk[k]) Mk[k] = v; }
            for (u64 s : safe) { int k = popcnt(s); if (g.at(s) == Mk[k]) ++cntM[k]; }
            int sigma = -1;
            for (int k = 0; k <= b.V; ++k) if (Mk[k] == 14 - k) { sigma = k; break; }
            printf("    \"K_n7\": 14,\n");
            printf("    \"max_nimber_M_n7\": %d,\n", Mk[0]);
            printf("    \"layer_profile_M_by_k\": {");
            for (int k = 0; k <= 14; ++k) printf("%s%d: %d", k ? ", " : "", k, Mk[k]);
            printf("},\n");
            printf("    \"layer_count_at_M\": {");
            for (int k = 0; k <= 14; ++k) printf("%s%d: %d", k ? ", " : "", k, cntM[k]);
            printf("},\n");
            printf("    \"sigma_n7\": %d,\n", sigma);
            printf("    \"grundy_value_histogram_all_positions\": {");
            { bool f = true; for (auto& kv : gall) { printf("%s%d: %d", f ? "" : ", ", kv.first, kv.second); f = false; } }
            printf("}\n  },\n");
        }
        // maximal safe sets cross-check
        {
            int maxsets = 0;
            for (u64 s : safe) if (kc::legal_mask(b, s) == 0) ++maxsets;
            printf("  \"n7_maximal_safe_sets\": %d,\n", maxsets);
        }
        printf("  \"n7_crosschecks\": {\n");
        printf("    \"F_7_expected_14564\": %s,\n", jbool((int)b.quads.size() == 14564).c_str());
        printf("    \"g_empty_expected_0\": %s,\n", jbool(g0 == 0).c_str());
        printf("    \"W7_empty_expected\": %s,\n", jbool(W == 0).c_str());
        printf("    \"d4_orbit_constancy\": %s\n", jbool(orb_const).c_str());
        printf("  },\n");
    }

    // =====================================================================
    // PART 3 -- n=8: exact state-space measurement (why full Grundy is out of
    // reach there) and the D4 orbit table of the 1-stone layer.
    // =====================================================================
    {
        Board b; kc::build_square(b, 8);
        std::vector<u64> safe;
        enumerate_safe(b, n8_maxk, safe);
        std::vector<long long> bysz(n8_maxk + 1, 0);
        for (u64 s : safe) ++bysz[popcnt(s)];

        std::vector<int> rep_of; int norb = 0; std::vector<int> reps;
        point_orbits(8, rep_of, norb, reps);
        std::vector<int> orbsz(norb, 0);
        for (int p = 0; p < 64; ++p) ++orbsz[rep_of[p]];

        printf("  \"n8_measurement\": {\n");
        printf("    \"V\": 64, \"F_8\": %d, \"K_n8\": 15,\n", (int)b.quads.size());
        printf("    \"max_size_enumerated\": %d,\n", n8_maxk);
        printf("    \"safe_sets_by_size\": {");
        for (int k = 0; k <= n8_maxk; ++k) printf("%s%d: %lld", k ? ", " : "", k, bysz[k]);
        printf("},\n");
        printf("    \"safe_sets_total_to_%d\": %lld,\n", n8_maxk, (long long)safe.size());
        printf("    \"d4_point_orbits\": %d,\n", norb);
        printf("    \"d4_orbit_reps_xy\": [");
        for (int i = 0; i < norb; ++i) printf("%s[%d,%d]", i ? ", " : "", reps[i] % 8, reps[i] / 8);
        printf("],\n");
        printf("    \"d4_orbit_sizes\": [");
        for (int i = 0; i < norb; ++i) printf("%s%d", i ? ", " : "", orbsz[reps[i]]);
        printf("],\n");
        printf("    \"note\": \"Any safe subset is reachable (add its points in any order), so |state space| = |safe subsets|. Measured growth above plus K_8=15 shows the full n=8 Grundy recursion is out of reach; the n=8 first-move verdict therefore comes from the mex identity, not from enumeration.\"\n");
        printf("  }\n");
    }

    printf("}\n");
    return 0;
}
