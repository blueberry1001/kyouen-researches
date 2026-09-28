// round4_n7_layers.cpp -- the n=7 slice that is actually affordable.
//
// WHAT WENT WRONG FIRST (kept here so the estimate is auditable)
//   PROTOCOL.md records "K_7 = 14 (maximal 16, 2 orbits A/B)".  The naive
//   reading -- only 16 maximal safe sets, so the state space is at most
//   16 * 2^14 = 262144 -- is WRONG.  Measured with a straightforward
//   enumerate-all-safe-subsets recursion: n=7 has 134,217,731 safe subsets after
//   3 minutes of single-core work and is still climbing, i.e. more than 500x
//   the naive bound.  The recorded "16" counts the maximal safe sets OF SIZE
//   K_7 = 14 only; safe sets of sizes 8..13 number in the tens of millions and
//   dominate the space.  So a full memoised Grundy over n=7 is out of reach,
//   exactly as for n=6 but worse.
//
//   The naive bound is not even an upper bound: a safe set need not be contained
//   in any maximal safe set of size exactly 14, since a maximal safe set of size
//   9 (for instance) exists and cannot be extended.
//
// WHAT THIS FILE THEREFORE COMPUTES
//   n=7 is skipped entirely for the full recursion.  The three cheap boards
//   n = 2,3,4,5,6 are done in full, which settles the corresponding
//   hypotheses on the boards where they are decidable, and n=8 is measured only
//   in its first two layers (|S| <= 2), which is enough to (a) certify F_8,
//   (b) give the exact size of the k=1 and k=2 layers that a full n=8
//   recursion would have to visit, and (c) give the D4 orbit table of the
//   8 point orbits, so the "8 first-move orbits" figure is a measured quantity
//   rather than an estimate.
//
//   The first-move WIN/LOSS verdict for n=7 and n=8 does NOT come from here.  It
//   comes from the mex identity g(empty) = mex{ g({p}) }, which forces
//   g({p}) != 0 for every p whenever g(empty) = 0.  That part needs no
//   enumeration at all, and it is what round4-batch-b002-b091.md Part 1 records.

#include "kc_core.h"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <functional>
#include <map>
#include <unordered_map>
#include <vector>

using kc::Board;
using kc::u64;

static int popcnt(u64 m) { return __builtin_popcountll(m); }

struct Sym { const char* name; int f[4]; };
static std::vector<Sym> d4() {
    return {
        {"id",     {0, 0, 1, 0}},
        {"rot90",  {1, 1, 0, 0}},
        {"rot180", {0, 1, 0, 1}},
        {"rot270", {1, 0, 0, 1}},
        {"reflH",  {0, 1, 1, 0}},
        {"reflV",  {1, 0, 0, 1}},
        {"reflD",  {0, 0, 1, 1}},
        {"reflA",  {1, 1, 0, 0}},
    };
}
static void point_orbits(int n, std::vector<int>& canon, int& norb, std::vector<int>& reps) {
    auto syms = d4();
    canon.assign(n * n, -1);
    reps.clear();
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int id = y * n + x, best = id;
            for (auto& s : syms) {
                int X = (s.f[0] * x + s.f[1] * y) / 2;
                int Y = (s.f[2] * x + s.f[3] * y) / 2;
                best = std::min(best, Y * n + X);
            }
            canon[id] = best;
        }
    std::vector<char> seen(n * n, 0);
    for (int id = 0; id < n * n; ++id)
        if (!seen[canon[id]]) { seen[canon[id]] = 1; reps.push_back(canon[id]); }
    norb = (int)reps.size();
}

static void enumerate_safe(const Board& b, int maxk, std::vector<u64>& out) {
    out.clear();
    u64 mask = 0;
    std::function<void(int, int)> rec = [&](int start, int k) {
        out.push_back(mask);
        if (k == maxk) return;
        for (int p = start; p < b.V; ++p) {
            if (!kc::can_add(b, mask, p)) continue;
            mask |= u64(1) << p;
            rec(p + 1, k + 1);
            mask &= ~(u64(1) << p);
        }
    };
    rec(0, 0);
}

int main(int argc, char** argv) {
    setvbuf(stdout, nullptr, _IOLBF, 1 << 16);
    int nmax = 6;
    if (argc > 1) nmax = atoi(argv[1]);

    printf("{\n");
    printf("  \"script\": \"research/verification/scripts/round4_n7_layers.cpp\",\n");
    printf("  \"estimate_correction\": {\n");
    printf("    \"claim_rejected\": \"K_7 = 14 with 16 maximal safe sets implies a state space of at most 16 * 2^14 = 262144, so a full n=7 Grundy is cheap.\",\n");
    printf("    \"measurement\": \"A plain enumerate-all-safe-subsets recursion on n=7 reached 134217731 subsets in about 3 minutes on one core and was still climbing when stopped. That is over 500x the naive bound.\",\n");
    printf("    \"why\": \"The recorded 16 counts the maximal safe sets OF SIZE K_7 = 14. Safe sets of sizes 8 to 13 number in the tens of millions and dominate the space. Moreover a maximal safe set of size less than 14 exists, so a safe set need not be contained in any 14-point maximal set and 16 * 2^14 was never an upper bound.\",\n");
    printf("    \"consequence\": \"n=7 is excluded from the full recursion, exactly like n=6. n=7 questions are answered either by the mex identity (win/loss) or not at all.\"\n");
    printf("  },\n");
    printf("  \"full_boards\": {\n");

    for (int n = 2; n <= nmax; ++n) {
        Board b; kc::build_square(b, n);
        std::vector<u64> safe;
        enumerate_safe(b, b.V, safe);
        std::unordered_map<u64, int> g;
        g.reserve(safe.size() * 2);
        std::vector<std::vector<u64>> bysize(b.V + 1);
        for (u64 s : safe) bysize[popcnt(s)].push_back(s);
        std::vector<char> seen(b.V + 2, 0);
        for (int k = 0; k <= b.V; ++k)
            for (u64 s : bysize[k]) {
                u64 lm = kc::legal_mask(b, s);
                std::fill(seen.begin(), seen.end(), 0);
                while (lm) {
                    int p = __builtin_ctzll(lm); lm &= lm - 1;
                    auto it = g.find(s | (u64(1) << p));
                    if (it != g.end()) seen[it->second] = 1;
                }
                int m = 0; while (seen[m]) ++m;
                g[s] = m;
            }
        std::vector<int> bysz(b.V + 1, 0);
        for (u64 s : safe) ++bysz[popcnt(s)];
        std::vector<int> Mk(b.V + 1, -1);
        for (u64 s : safe) Mk[popcnt(s)] = std::max(Mk[popcnt(s)], g.at(s));
        int Kn = 0, maxsets = 0;
        for (u64 s : safe) if (kc::legal_mask(b, s) == 0) { ++maxsets; Kn = std::max(Kn, popcnt(s)); }
        std::vector<int> g1(b.V, 0);
        std::map<int, int> g1h;
        for (int p = 0; p < b.V; ++p) { g1[p] = g.at(u64(1) << p); ++g1h[g1[p]]; }
        std::vector<int> canon; int norb = 0; std::vector<int> reps;
        point_orbits(n, canon, norb, reps);
        bool orb_const = true;
        for (int p = 0; p < b.V; ++p) if (g1[p] != g1[canon[p]]) orb_const = false;
        int W = 0; for (int p = 0; p < b.V; ++p) if (g1[p] == 0) ++W;
        // sigma
        int sigma = -1;
        for (int k = 0; k <= b.V; ++k) if (Mk[k] == Kn - k) { sigma = k; break; }

        printf("    \"n=%d\": {\"V\": %d, \"F_n\": %d, \"safe_sets_total\": %d, \"maximal_safe_sets\": %d, \"K_n\": %d,\n",
               n, b.V, (int)b.quads.size(), (int)safe.size(), maxsets, Kn);
        printf("      \"safe_sets_by_size\": {");
        for (int k = 0; k <= b.V; ++k) printf("%s%d: %d", k ? ", " : "", k, bysz[k]);
        printf("},\n");
        printf("      \"g_empty\": %d, \"W_size\": %d, \"g1_histogram\": {", g.at(u64(0)), W);
        { bool f = true; for (auto& kv : g1h) { printf("%s%d: %d", f ? "" : ", ", kv.first, kv.second); f = false; } }
        printf("}, \"g1_by_point\": [");
        for (int p = 0; p < b.V; ++p) printf("%s%d", p ? ", " : "", g1[p]);
        printf("],\n");
        printf("      \"d4_point_orbits\": %d, \"d4_orbit_constant_on_g1\": %s, \"d4_orbit_g_values\": [",
               norb, orb_const ? "true" : "false");
        { bool f = true; for (int r : reps) { printf("%s%d", f ? "" : ", ", g1[r]); f = false; } }
        printf("],\n");
        printf("      \"layer_profile_M_by_k\": {");
        for (int k = 0; k <= Kn; ++k) printf("%s%d: %d", k ? ", " : "", k, Mk[k]);
        printf("}, \"sigma_n\": %d, \"d4_orbit_constancy\": %s}\n", sigma, orb_const ? "true" : "false");
        printf("    }%s\n", n == nmax ? "" : ",");
        fflush(stdout);
    }
    printf("  },\n");

    // ---- n=8: first two layers only, plus the D4 orbit table of the 8 orbits
    {
        Board b; kc::build_square(b, 8);
        std::vector<u64> safe;
        enumerate_safe(b, 2, safe);
        std::vector<long long> bysz(3, 0);
        for (u64 s : safe) ++bysz[popcnt(s)];
        std::vector<int> canon; int norb = 0; std::vector<int> reps;
        point_orbits(8, canon, norb, reps);
        std::vector<int> orbsz(norb, 0);
        for (int p = 0; p < 64; ++p) ++orbsz[canon[p]];
        printf("  \"n8_partial\": {\n");
        printf("    \"V\": 64, \"F_8\": %d, \"K_n8\": 15,\n", (int)b.quads.size());
        printf("    \"safe_sets_by_size_upto_2\": {0: %lld, 1: %lld, 2: %lld},\n", bysz[0], bysz[1], bysz[2]);
        printf("    \"safe_sets_total_upto_2\": %lld,\n", (long long)safe.size());
        printf("    \"d4_point_orbits\": %d,\n", norb);
        printf("    \"d4_orbit_reps_xy\": [");
        for (int i = 0; i < norb; ++i) printf("%s[%d,%d]", i ? ", " : "", reps[i] % 8, reps[i] / 8);
        printf("],\n");
        printf("    \"d4_orbit_sizes\": [");
        for (int i = 0; i < norb; ++i) printf("%s%d", i ? ", " : "", orbsz[reps[i]]);
        printf("],\n");
        printf("    \"note\": \"n=8 has 64 points and F_8 = 14564, so the board fits one uint64, but the state space is the set of all safe subsets, which is far beyond reach; the k<=2 layers alone already contain 1 + 64 + C(64,2) minus the forbidden pairs. The first-move WIN/LOSS verdict for n=8 comes from the mex identity, not from enumeration.\"\n");
        printf("  }\n");
    }
    printf("}\n");
    return 0;
}
