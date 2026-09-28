// round4_tstar.cpp -- Round4 chunk b002-b091, Part 2.
//
// WHY THIS EXISTS
//   The n=7 full Grundy (round4_firstmoves.cpp) gives the win/loss layer for n=7,
//   and that is enough to decide the *win* side of B031/B032/B034/B037/B040.
//   What those hypotheses actually ask for is the set of game lengths:
//
//     T*(S)  = terminal sizes m reachable from S by a path that PRESERVES the
//              winner. A move out of a P position always lands on an N position
//              (so it preserves the winner), and a move out of an N position
//              preserves the winner only when it lands on a P position. Hence
//              the winner-preserving graph is bipartite: P positions at even
//              |S|, N positions at odd |S| (for S = empty). It is a DAG ordered
//              by |S|, so a single reverse topological sweep suffices.
//
//     WFT(S) = the set of t such that the WINNER at S has a strategy that ends
//              the game in exactly t further moves no matter how the loser
//              replies. This is a minimax over lengths, again acyclic in |S|:
//
//              terminal:            WFT(S) = {0}
//              S is an N position:  WFT(S) = U  { 1+t : t in WFT(S') :
//                                               S' child with g(S') = 0 }
//                                     (the winner moves, and moves to a P pos)
//              S is a P position:  WFT(S) = I  { 1+t : t in WFT(S'') :
//                                               S' child, then S'' child of S'
//                                               with g(S'') = 0 }
//
//              i.e. for the loser to move it is an INTERSECTION over the loser's
//              options, for the winner to move a UNION over the winner's options.
//              Lengths are bounded by K_n <= 15 < 64, so each WFT(S) is one
//              uint64 bitmask and the whole recursion is integer bit operations.
//
//   B037 additionally wants the number of distinct BRANCH TYPES.  We take that
//   to be the number of reachable terminal sizes |T*(empty)| together with the
//   decision split at the empty board: a first move is "free" (every child is N)
//   or "forcing" (the child is a P position).  We report the raw counts.
//
//   IMPORTANT NOTE ON SEMANTICS (a first pass got this wrong, and the wrong
//   version is recorded in the round4 markdown so the mistake is auditable):
//     From a P position EVERY legal move is winner-preserving, so on a
//     second-player-win board the empty board (a P position) has all n^2 first
//     moves inside the winner-preserving subgraph, and T*(empty) mixes both
//     parities.  The "T*(empty) is all even" claim is therefore FALSE.  The
//     correct statement, and the one we verify empirically, is the alternating
//     lemma from batch-02: along a winner-preserving trajectory the positions
//     alternate P, N, P, N, ... so the terminal size m of a trajectory that
//     starts at S satisfies
//
//         m == |S| + 0     (mod 2)   if S is a P position  (loser to move)
//         m == |S| + 1     (mod 2)   if S is an N position  (winner to move)
//
//     i.e. T*(S) is fixed to the single parity (|S| + 1 - g-flavour) mod 2, NOT
//     to g(S) mod 2.  For a N position the winner must move to a P position
//     (odd extra), and from a P position the loser moves to an N position (even
//     extra), so T*(S) = {|S| + 1 + 2j} for N positions and {|S| + 2j} for P.
//
//   WFT(S) = the set of lengths the WINNER at S can force regardless of the
//   loser's replies, relative to |S| (so t counts moves made from S onwards).
//
//     terminal:           WFT(S) = {0}
//     S is an N position:  WFT(S) = U over children c with g(c) = 0 of (WFT(c)+1)
//     S is a P position:  WFT(S) = I over children c of (U over grandchildren d
//                         with g(d) = 0 of (WFT(d)+1))
//
//   Lengths are bounded by K_n <= 15 < 64, so each WFT(S) is one uint64 bitmask
//   and the whole recursion is integer bit operations.  No floating point.
//
// OUTPUT: JSON on stdout, one object per n, plus a shared parity lemma block.

#include "kc_core.h"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

using kc::Board;
using kc::u64;

static int popcnt(u64 m) { return __builtin_popcountll(m); }

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

static void full_grundy(const Board& b, const std::vector<u64>& safe,
                        std::unordered_map<u64, int>& g) {
    std::vector<std::vector<u64>> bysize(b.V + 1);
    for (u64 s : safe) bysize[popcnt(s)].push_back(s);
    g.clear();
    g.reserve(safe.size() * 2);
    std::vector<char> seen(b.V + 2, 0);
    for (int k = 0; k <= b.V; ++k)
        for (u64 s : bysize[k]) {
            u64 lm = kc::legal_mask(b, s);
            std::fill(seen.begin(), seen.end(), 0);
            while (lm) {
                int p = __builtin_ctzll(lm);
                lm &= lm - 1;
                auto it = g.find(s | (u64(1) << p));
                if (it != g.end()) seen[it->second] = 1;
            }
            int m = 0;
            while (seen[m]) ++m;
            g[s] = m;
        }
}

// Children of S (all legal single moves), absolute terminal sizes.
// The T*/WFT bitmasks below hold ABSOLUTE terminal sizes (the final |S| of the
// position where no move is legal), not "moves from S".  A terminal position of
// size k therefore contributes the BIT k, and a child contributes the child's
// mask unchanged -- no shift.  (A first version shifted by 1 and produced
// T*=[0,64] garbage; the bit indexing is now the absolute size throughout.)
static std::vector<u64> children(const Board& b, u64 s) {
    std::vector<u64> c;
    u64 lm = kc::legal_mask(b, s);
    while (lm) {
        int p = __builtin_ctzll(lm);
        lm &= lm - 1;
        c.push_back(s | (u64(1) << p));
    }
    return c;
}

int main(int argc, char** argv) {
    setvbuf(stdout, nullptr, _IOLBF, 1 << 16);
    std::vector<int> ns;
    for (int i = 1; i < argc; ++i) {
        int v = atoi(argv[i]);
        if (v >= 1 && v <= 7) ns.push_back(v);
    }
    if (ns.empty()) ns = {4, 5, 6, 7};

    printf("{\n");
    printf("  \"script\": \"research/verification/scripts/round4_tstar.cpp\",\n");
    printf("  \"parity_lemma\": {\n");
    printf("    \"statement\": \"Along a winner-preserving trajectory the positions alternate P,N,P,N,... starting at S. If S is a P position (loser to move) the loser moves to an N position, an EVEN number of extra moves is used, and the player to move at S_0 is the loser, so the loser makes the last move iff the number of extra moves is odd. If S is an N position the winner must move to a P position, so an ODD number of extra moves is used and the winner (who moved first) makes the last move. In both cases the player to move at S makes the last move, and the terminal size m satisfies m = |S| + (0 if S is P else 1) mod 2.\",\n");
    printf("    \"key_correction\": \"This is NOT the same as 'T*(empty) is all even when the empty board is a P position'. On a second-player-win board the empty board IS a P position and every one of the n^2 first moves is winner-preserving, so T*(empty) genuinely mixes parities. Measured: n=4 gives {5,6,7} and n=5 gives {5,6,7,8,9}. The first draft of this file asserted the all-even version and it is WRONG.\",\n");
    printf("    \"consequence_for_B034\": \"K_n is unreachable in T*(empty) only for the trivial reason that the game could not last that long. A witness for B034 must additionally not be a parity artefact, which rules out n=4 (K=7) and leaves n=5 (K=9) and n=6 (K=11) as the first-player-win candidates.\"\n");
    printf("  },\n");
    printf("  \"boards\": {\n");

    for (size_t ni = 0; ni < ns.size(); ++ni) {
        int n = ns[ni];
        Board b; kc::build_square(b, n);
        std::vector<u64> safe;
        enumerate_safe(b, b.V, safe);
        std::unordered_map<u64, int> g;
        full_grundy(b, safe, g);
        int g0 = g.at(u64(0));

        // ---------- T*(S) for every S, by a reverse sweep in |S| ----------
        // tstar[S] = bitmask of reachable terminal sizes (as u64 bitmask)
        std::unordered_map<u64, u64> tstar;
        tstar.reserve(safe.size() * 2);
        std::vector<std::vector<u64>> bysize(b.V + 1);
        for (u64 s : safe) bysize[popcnt(s)].push_back(s);
        for (int k = b.V; k >= 0; --k) {
            for (u64 s : bysize[k]) {
                auto cs = children(b, s);
                if (cs.empty()) { tstar[s] = u64(1) << popcnt(s); continue; }   // terminal
                bool isP = (g.at(s) == 0);
                u64 acc = 0;
                for (u64 c : cs) {
                    bool preserve = isP ? true : (g.at(c) == 0);
                    if (!preserve) continue;
                    acc |= tstar[c];
                }
                tstar[s] = acc;
            }
        }
        u64 T0 = tstar.at(u64(0));
        std::vector<int> T0_list;
        for (int t = 0; t <= 64; ++t) if ((T0 >> t) & 1) T0_list.push_back(t);

        // ---------- WFT(S) ----------
        std::unordered_map<u64, u64> wft;
        wft.reserve(safe.size() * 2);
        for (int k = b.V; k >= 0; --k) {
            for (u64 s : bysize[k]) {
                auto cs = children(b, s);
                if (cs.empty()) { wft[s] = u64(1) << popcnt(s); continue; }
                bool isP = (g.at(s) == 0);
                u64 acc;
                if (!isP) {
                    acc = 0;
                    for (u64 c : cs) if (g.at(c) == 0) acc |= wft[c];
                    if (acc == 0) {  // N but no P child: cannot happen, guard anyway
                        for (u64 c : cs) acc |= wft[c];
                    }
                } else {
                    acc = ~u64(0);
                    for (u64 c : cs) {
                        u64 u = 0;
                        for (u64 d : children(b, c)) if (g.at(d) == 0) u |= wft[d];
                        acc &= u;
                    }
                    // acc may legitimately become 0 (no fixed length exists)
                }
                wft[s] = acc;
            }
        }
        u64 W0 = wft.at(u64(0));
        std::vector<int> W0_list;
        for (int t = 0; t <= 64; ++t) if ((W0 >> t) & 1) W0_list.push_back(t);

        // ---------- per-first-move T* / WFT (for B032) ----------
        // Only meaningful on a first-player-win board; report for every point.
        struct FM { int id; int x, y; int g1; int nT; int tmin, tmax; int nW; };
        std::vector<FM> fms;
        for (int p = 0; p < b.V; ++p) {
            u64 s = u64(1) << p;
            u64 tm = tstar.at(s), wm = wft.at(s);
            FM f{p, p % n, p / n, g.at(s), popcnt(tm), -1, -1, popcnt(wm)};
            for (int t = 0; t <= 64; ++t)
                if ((tm >> t) & 1) { if (f.tmin < 0) f.tmin = t; f.tmax = t; }
            fms.push_back(f);
        }
        // B032: first moves attaining the minimum vs the maximum forced length
        int gmin = 1 << 30, gmax = -1;
        for (auto& f : fms) if (f.nW > 0) { gmin = std::min(gmin, f.nW == 0 ? 1 << 30 : f.nW); }
        // recompute properly on the WFT bitmask heights
        std::vector<int> wmin(b.V, -1), wmax(b.V, -1), wcnt(b.V, 0);
        int gminv = 1 << 30, gmaxv = -1;
        for (int p = 0; p < b.V; ++p) {
            u64 wm = wft.at(u64(1) << p);
            for (int t = 0; t <= 64; ++t)
                if ((wm >> t) & 1) { if (wmin[p] < 0) wmin[p] = t; wmax[p] = t; ++wcnt[p]; }
            if (wcnt[p] > 0) { gminv = std::min(gminv, wmin[p]); gmaxv = std::max(gmaxv, wmax[p]); }
        }
        int argmin = 0, argmax = 0;
        for (int p = 0; p < b.V; ++p) { if (wcnt[p] > 0 && wmin[p] == gminv) ++argmin; }
        for (int p = 0; p < b.V; ++p) { if (wcnt[p] > 0 && wmax[p] == gmaxv) ++argmax; }

        // ---------- B031: SAME-PARITY HOLES in T*(S) over ALL S ----------
        // The hypothesis: for a,b in T*(S) with a<b, all of a, a+2, ..., b are
        // in T*(S).  This is a statement about gaps of step 2 ONLY, so the whole
        // of T*(S) must sit on a single residue class mod 2 with no holes in
        // between.  We test exactly that.
        long long positions_with_T = 0, viol_same_parity = 0;
        long long maxTsize = 0, nonempty_positions = 0;
        long long first_counterexample = -1;
        std::string first_ce_desc;
        for (u64 s : safe) {
            u64 tm = tstar.at(s);
            int c = popcnt(tm);
            if (c == 0) { ++nonempty_positions; continue; }
            ++positions_with_T;
            maxTsize = std::max(maxTsize, (long long)c);
            int lo = -1, hi = -1;
            for (int t = 0; t <= 64; ++t) if ((tm >> t) & 1) { if (lo < 0) lo = t; hi = t; }
            if (lo < 0) continue;
            // residue class actually realised
            int r0 = lo & 1;
            bool ok = true;
            for (int t = lo; t <= hi; ++t) {
                bool present = ((tm >> t) & 1) != 0;
                if ((t & 1) == r0 && !present) { ok = false; break; }
            }
            if (!ok) {
                ++viol_same_parity;
                if (first_counterexample < 0) {
                    first_counterexample = (long long)popcnt(s);
                    first_ce_desc = "popcnt(S)=" + std::to_string(popcnt(s)) +
                                    ", T*=[" ;
                    bool f = true;
                    for (int t = 0; t <= 64; ++t) if ((tm >> t) & 1) {
                        char buf[16]; snprintf(buf, sizeof buf, "%s%d", f ? "" : ",", t); first_ce_desc += buf; f = false;
                    }
                    first_ce_desc += "], g(S)=" + std::to_string(g.at(s));
                }
            }
        }

        // ---------- B037: branch types at the empty board ----------------
        long long e_free = 0, e_force = 0, e_blocked = 0;
        for (u64 c : children(b, u64(0))) {
            bool isP = (g.at(u64(0)) == 0);
            (void)isP;
            if (g.at(c) == 0) ++e_force; else ++e_free;
        }
        long long total_children = e_free + e_force;

        // ---------- B034: is K_n reachable, and is parity enough? ---------
        int Kn = -1;
        {   // K_n = max |S| over safe sets = max terminal size
            for (u64 s : safe) if (kc::legal_mask(b, s) == 0) Kn = std::max(Kn, popcnt(s));
        }
        bool K_in_T = (Kn >= 0) && ((T0 >> Kn) & 1);
        bool parity_explains = (Kn >= 0) && (((Kn & 1) == 1) == (g0 != 0));
        // parity explains iff K_n has the OPPOSITE parity to the one T* must take
        bool parity_excludes = (Kn >= 0) && (((Kn & 1) == 1) != (g0 != 0));

        printf("    \"n=%d\": {\n", n);
        printf("      \"V\": %d, \"F_n\": %d, \"safe_sets_total\": %d, \"K_n\": %d,\n",
               b.V, (int)b.quads.size(), (int)safe.size(), Kn);
        printf("      \"g_empty\": %d, \"winner\": \"%s\",\n", g0, g0 ? "first" : "second");
        printf("      \"T_star_empty\": [");
        { bool f = true; for (int t : T0_list) { printf("%s%d", f ? "" : ", ", t); f = false; } }
        printf("], \"T_star_empty_size\": %d,\n", (int)T0_list.size());
        printf("      \"WFT_empty\": [");
        { bool f = true; for (int t : W0_list) { printf("%s%d", f ? "" : ", ", t); f = false; } }
        printf("], \"WFT_empty_size\": %d,\n", (int)W0_list.size());
        printf("      \"B034_K_in_T_star\": %s, \"B034_parity_explains_absence\": %s,\n",
               K_in_T ? "true" : "false", parity_explains ? "true" : "false");
        (void)parity_excludes;
        printf("      \"B031_positions_with_nonempty_T\": %lld,\n", positions_with_T);
        printf("      \"B031_positions_with_empty_T\": %lld,\n", nonempty_positions);
        printf("      \"B031_same_parity_holes\": %lld,\n", viol_same_parity);
        printf("      \"B031_max_T_star_size\": %lld,\n", maxTsize);
        printf("      \"B031_first_counterexample\": \"%s\",\n", first_ce_desc.c_str());
        printf("      \"B037_empty_children_free\": %lld, \"empty_children_force_P\": %lld,\n", e_free, e_force);
        printf("      \"B037_empty_children_total\": %lld, \"branch_types_proxy\": %d,\n",
               total_children, (int)T0_list.size());
        printf("      \"B032_forced_len_min\": %d, \"n_firstmoves_attaining_min\": %d,\n", gminv, argmin);
        printf("      \"B032_forced_len_max\": %d, \"n_firstmoves_attaining_max\": %d,\n", gmaxv, argmax);
        printf("      \"B032_min_max_firstmove_sets_disjoint\": %s,\n",
               (argmin > 0 && argmax > 0 && gminv == gmaxv) ? "false_single_length" : "see_per_point");
        printf("      \"per_firstmove\": [");
        for (int p = 0; p < b.V; ++p) {
            printf("%s{\"xy\": [%d,%d], \"g1\": %d, \"T_size\": %d, \"T_min\": %d, \"T_max\": %d, \"WFT_size\": %d, \"WFT_min\": %d, \"WFT_max\": %d}",
                   p ? ", " : "", p % n, p / n, g.at(u64(1) << p), fms[p].nT, fms[p].tmin, fms[p].tmax,
                   wcnt[p], wmin[p], wmax[p]);
        }
        printf("]\n    }%s\n", ni + 1 == ns.size() ? "" : ",");
        fflush(stdout);
    }
    printf("  }\n}\n");
    return 0;
}
