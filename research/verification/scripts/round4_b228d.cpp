// Round4 batch B228-B290, pass 3 (theory/decisive pass).
//
// Sections (all integer arithmetic; every ratio printed as exact p/q):
//   sec_core   : full safe-set enumeration + Grundy + proof sizes for n=2..6
//   sec_u      : B261 B262 B263 B264 B265 B268 B269 B270  (state-local scans)
//   sec_switch : B238  (switch-point formalisation)
//   sec_xor    : B240  (equal-nimber parts, different context)
//   sec_uuni   : B267  (universal claim -> counterexample search)
//   sec_local  : B285  (same S embedded in n=4..8, distinct Grundy values)
//   sec_umax   : B239  (max newly-forbidden count per board, n=4..8)
//   sec_orbit  : B241 B242  (D4 orbit count of W_n)
//   sec_nimb   : B231  (max Grundy value per board, exact proof tree depth)
//
// Every section flushes so partial output is readable while it runs.
#include "kc_core.h"
#include <algorithm>
#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>
#include <unordered_map>
#include <vector>

using namespace kc;
typedef unsigned long long U64;

static void P(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    fflush(stdout);
}

struct Game {
    Board b;
    std::vector<u64> masks;                 // safe sets, sorted by popcount
    std::vector<int> g;
    std::vector<u64> legal;                 // legal point mask
    std::vector<int> depth;                 // longest play from S
    std::vector<u64> proof;                 // AND/OR proof tree size (nodes)
    std::unordered_map<u64, int> idx;
    long long level[20];
    int maxg = 0, K = 0, nmax = 0;
    long long total = 0, maximal = 0;
    inline int at(u64 m) const { return idx.find(m)->second; }
};

// full enumeration of all safe subsets of the n x n square
static void build_game(Game& G, int n, bool heavy) {
    build_square(G.b, n);
    std::vector<u64> ms;
    std::vector<int> stack_start;
    // iterative DFS (avoid deep recursion cost)
    struct Frame { int start; u64 occ; };
    std::vector<Frame> st;
    ms.push_back(0);
    st.push_back({0, 0});
    while (!st.empty()) {
        Frame f = st.back();
        st.pop_back();
        bool pushed = false;
        for (int p = f.start; p < G.b.V; ++p) {
            if (can_add(G.b, f.occ, p)) {
                u64 no = f.occ | (u64(1) << p);
                ms.push_back(no);
                st.push_back({p + 1, no});
                pushed = true;
            }
        }
        (void)pushed;
    }
    // DESCENDING popcount order: every child of S has popcount |S|+1, so the
    // children are visited BEFORE their parent and the mex is well defined.
    // (Ascending order silently reads uninitialised g[] and yields the
    //  wrong answer g(empty)=1 for every n.)
    int maxk = 0;
    for (u64 m : ms) { int k = __builtin_popcountll(m); if (k > maxk) maxk = k; }
    std::vector<std::vector<u64>> bucket(maxk + 1);
    for (u64 m : ms) bucket[__builtin_popcountll(m)].push_back(m);
    ms.clear();
    for (int k = maxk; k >= 0; --k) for (u64 m : bucket[k]) ms.push_back(m);
    G.masks = ms;
    G.total = (long long)ms.size();
    size_t N = ms.size();
    G.idx.reserve(N * 2);
    for (size_t i = 0; i < N; ++i) G.idx[ms[i]] = (int)i;
    G.g.assign(N, 0);
    G.legal.assign(N, 0);
    G.depth.assign(N, 0);
    G.proof.assign(N, 0);
    memset(G.level, 0, sizeof G.level);
    for (size_t i = 0; i < N; ++i) G.level[__builtin_popcountll(ms[i])]++;
    for (size_t i = 0; i < N; ++i) {
        u64 occ = ms[i];
        int lm = 0;
        u64 m = legal_mask(G.b, occ);
        G.legal[i] = m;
        while (m) {
            int p = __builtin_ctzll(m);
            m &= m - 1;
            lm |= 1;
        }
        unsigned long long seen = 0;
        u64 mm = G.legal[i];
        int best = -1;
        int dmax = 0, pmin = -1;
        while (mm) {
            int p = __builtin_ctzll(mm);
            mm &= mm - 1;
            int j = G.idx[occ | (u64(1) << p)];
            int c = G.g[j];
            seen |= 1ULL << c;
            if (1 + G.depth[j] > dmax) { dmax = 1 + G.depth[j]; pmin = c; }
        }
        int gg = 0;
        while (seen & (1ULL << gg)) ++gg;
        G.g[i] = gg;
        G.depth[i] = dmax;
        if (gg == 0) {
            // P: proof needs every child
            u64 s = 0;
            u64 mm2 = G.legal[i];
            u64 tot = 1;
            while (mm2) {
                int p = __builtin_ctzll(mm2);
                mm2 &= mm2 - 1;
                tot += G.proof[G.idx[occ | (u64(1) << p)]];
            }
            G.proof[i] = tot;
        } else {
            // N: cheapest P child
            u64 mm2 = G.legal[i];
            u64 bestv = ~0ULL;
            while (mm2) {
                int p = __builtin_ctzll(mm2);
                mm2 &= mm2 - 1;
                int j = G.idx[occ | (u64(1) << p)];
                if (G.g[j] == 0 && G.proof[j] < bestv) bestv = G.proof[j];
            }
            G.proof[i] = (bestv == ~0ULL) ? 1 : (1 + bestv);
        }
        (void)lm; (void)pmin;
        if (gg > G.maxg) G.maxg = gg;
        int pc2 = __builtin_popcountll(occ);
        if (pc2 > G.K) G.K = pc2;
        if (G.legal[i] == 0) G.maximal++;
    }
    G.nmax = n;
    P("  n=%d total_safe=%lld K=%d maximal=%lld max_grundy=%d\n",
      n, G.total, G.K, G.maximal, G.maxg);
}

// winning moves of state i as a point mask
static kc::u64 winning_moves(const Game& G, int i) {
    kc::u64 occ = G.masks[i], lm = G.legal[i], out = 0;
    while (lm) {
        int p = __builtin_ctzll(lm);
        lm &= lm - 1;
        if (G.g[G.at(occ | (kc::u64(1) << p))] == 0) out |= kc::u64(1) << p;
    }
    return out;
}

// newly forbidden points by playing p: L(S) \ (L(S+p) u {p})
static kc::u64 nf_mask(const Game& G, int i, int p) {
    kc::u64 occ = G.masks[i];
    int j = G.at(occ | (kc::u64(1) << p));
    return G.legal[i] & ~G.legal[j] & ~(kc::u64(1) << p);
}
static inline int u_of(const Game& G, int i, int p) {
    return __builtin_popcountll(nf_mask(G, i, p));
}
static u64 pts(const Game& G, u64 m, int* cnt = nullptr) {
    int c = 0; char buf[512]; int o = 0;
    buf[0] = 0;
    while (m) {
        int p = __builtin_ctzll(m); m &= m - 1;
        o += snprintf(buf + o, sizeof(buf) - o, "(%d,%d)", G.b.pt_x[p], G.b.pt_y[p]);
        c++;
    }
    if (cnt) *cnt = c;
    return c;
}

// number of connected components of a graph given by adjacency bitmasks
static int comps_of(const std::vector<u64>& adj, int V) {
    u64 unvis = (V == 0) ? 0 : ((V == 64) ? ~u64(0) : ((u64(1) << V) - 1));
    int c = 0;
    while (unvis) {
        int r = __builtin_ctzll(unvis);
        c++;
        u64 stack = u64(1) << r;
        unvis &= ~(u64(1) << r);
        while (stack) {
            int x = __builtin_ctzll(stack);
            stack &= stack - 1;
            u64 nb = adj[x] & unvis;
            unvis &= ~nb;
            stack |= nb;
        }
    }
    return c;
}

// Node-Kayles (independent-set placement) Grundy value of a subgraph of R(S),
// given an explicit vertex mask over ORIGINAL point ids.  g_nkadj must be
// filled by nk_set_board.
static std::vector<u64> g_nkadj(64, 0);
static std::unordered_map<u64, int> g_nkmemo;

static void nk_set_board(const std::vector<u64>& adjfull) {
    g_nkadj = adjfull;
    g_nkmemo.clear();
}

static int nk_grundy(u64 verts) {
    auto it = g_nkmemo.find(verts);
    if (it != g_nkmemo.end()) return it->second;
    unsigned long long seen = 0;
    u64 t = verts;
    while (t) {
        int v = __builtin_ctzll(t);
        t &= t - 1;
        u64 rest = verts & ~(u64(1) << v);
        seen |= 1ULL << nk_grundy(rest);                            // keep v
        seen |= 1ULL << nk_grundy(rest & ~(g_nkadj[v] & rest));      // take v
    }
    int gg = 0;
    while (seen & (1ULL << gg)) ++gg;
    g_nkmemo[verts] = gg;
    return gg;
}

int main() {
    P("=== round4_b228d : decisive pass ===\n");

    // ---------------- sec_core -------------------------------------------
    P("\n## sec_core : full enumeration n=2..6\n");
    std::vector<Game> Gs;
    for (int n = 2; n <= 6; ++n) {
        Game G; build_game(G, n, true); Gs.push_back(std::move(G));
        P("  Z_%d(lam) coefficients:", n);
        for (int k = 0; k <= G.K; ++k) P(" %lld", G.level[k]);
        P("\n");
    }
    // B231: exact max grundy per board (self-check against PROTOCOL)
    P("\n## B231 max_grundy by n (exact, full enumeration)\n");
    for (size_t i = 0; i < Gs.size(); ++i)
        P("  n=%d max_grundy=%d K=%d\n", Gs[i].nmax, Gs[i].maxg, Gs[i].K);
    P("  PROTOCOL known max nimber n=2..6 = 1,1,5,6,8 (cross-check above)\n");

    // ---------------- sec_graph : B232 B233 B234 -------------------------
    P("\n## sec_graph : B232 B233 B234 (residual graph R(S) census)\n");
    for (size_t gi = 0; gi < 3; ++gi) {          // n = 4,5,6
        Game& G = Gs[gi];
        int n = G.nmax;
        // R(S): vertices = L(S); edge p-q iff S' = S + {p,q} is not safe
        // (i.e. adding both would complete a forbidden quad with two stones of S)
        long long hist_v[40] = {0};
        long long all_trees = 0, has_cycle = 0, is_forest = 0;
        long long tree_iso_hist[40] = {0};
        long long nk_split_ok = 0, nk_split_bad = 0;
        long long nk_comp_hist[16] = {0};
        int maxcomps = 0;
        size_t done = 0;
        for (size_t i = 0; i < G.masks.size(); ++i) {
            u64 occ = G.masks[i], L = G.legal[i];
            int V = __builtin_popcountll(L);
            if (V == 0) continue;
            if (V < 40) hist_v[V]++;
            // R(S) adjacency over ORIGINAL point ids:
            //   edge p-q  iff  q is still legal after p has been played.
            std::vector<u64> adjfull(G.b.V, 0);
            std::vector<u64> adj;
            u64 t = L;
            while (t) {
                int p = __builtin_ctzll(t);
                t &= t - 1;
                u64 l2 = G.legal[G.idx[occ | (u64(1) << p)]];
                adjfull[p] = l2 & L;
                adj.push_back(adjfull[p]);
            }
            long long edges = 0;
            for (int a = 0; a < V; ++a) edges += __builtin_popcountll(adj[a]);
            edges /= 2;
            int comp = comps_of(adj, V);
            if (edges == V - 1 && comp == 1) { all_trees++; if (V < 40) tree_iso_hist[V]++; }
            else if (edges >= V) { has_cycle++; }
            else { is_forest++; }
            if (comp > maxcomps) maxcomps = comp;
            if (comp < 16) nk_comp_hist[comp]++;
            // xor theorem: g(R(S)) == xor over components of the NK grundy
            if (comp > 1) {
                nk_set_board(adjfull);
                int acc = 0;
                u64 unvis = L;
                while (unvis) {
                    int r = __builtin_ctzll(unvis);
                    u64 stack = u64(1) << r, compmask = 0;
                    unvis &= ~(u64(1) << r);
                    while (stack) {
                        int x = __builtin_ctzll(stack);
                        stack &= stack - 1;
                        compmask |= u64(1) << x;
                        u64 nb = adjfull[x] & unvis;
                        unvis &= ~nb;
                        stack |= nb;
                    }
                    acc ^= nk_grundy(compmask);
                }
                if (acc == G.g[i]) nk_split_ok++; else nk_split_bad++;
            }
            if ((++done % 500000) == 0) {
                P("    ...n=%d processed %zu / %zu\n", n, done, G.masks.size());
                fflush(stdout);
            }
        }
            }
            long long edges = 0;
            for (int a = 0; a < V; ++a) edges += __builtin_popcountll(adj[a]);
            edges /= 2;
            if (edges > V) { has_cycle++; }
            else if (edges == V - 1) { all_trees++; if (V < 40) tree_iso_hist[V]++; }
            else if (edges == V - 1 - comps_of(adj, V)) is_forest++;
            // connected components
            int comp = comps_of(adj, V);
            if (comp > maxcomps) maxcomps = comp;
            if (comp < 16) nk_comp_hist[comp]++;
            // xor theorem: g(R(S)) should equal xor of g(component)
            if (comp > 1) {
                int acc = 0;
                u64 unvis = (V == 64) ? ~u64(0) : ((u64(1) << V) - 1);
                while (unvis) {
                    int r = __builtin_ctzll(unvis);
                    u64 stack = u64(1) << r, compmask = 0;
                    unvis &= ~(u64(1) << r);
                    while (stack) {
                        int x = __builtin_ctzll(stack); stack &= stack - 1;
                        compmask |= u64(1) << x;
                        u64 nb = adj[x] & unvis;
                        unvis &= ~nb;
                        stack |= nb;
                    }
                    u64 sub = 0;
                    u64 cm = compmask;
                    while (cm) { int x = __builtin_ctzll(cm); cm &= cm - 1; sub |= u64(1) << vid[x]; }
                    acc ^= nk_grundy(sub);
                }
                if (acc == G.g[i]) nk_split_ok++; else nk_split_bad++;
            }
            if ((++done % 500000) == 0) {
                P("    ...n=%d processed %zu / %zu\n", n, done, G.masks.size());
                fflush(stdout);
            }
        }
        P("  n=%d\n", n);
        P("    B232/B233 positions_with_R_nonempty = %lld ; R_is_a_tree = %lld ; R_has_cycle = %lld ; R_is_a_forest = %lld\n",
          all_trees + has_cycle + is_forest, all_trees, has_cycle, is_forest);
        P("    B232 max_component_count = %d\n", maxcomps);
        P("    B232 component_count histogram:");
        for (int c = 1; c < 8; ++c) if (nk_comp_hist[c]) P(" %d:%lld", c, nk_comp_hist[c]);
        P("\n");
        P("    B234 xor_split_checked = %lld ; exact = %lld ; mismatch = %lld\n",
          nk_split_ok + nk_split_bad, nk_split_ok, nk_split_bad);
        P("    B233 tree-R vertex-count histogram:");
        for (int v = 1; v < 12; ++v) if (tree_iso_hist[v]) P(" %d:%lld", v, tree_iso_hist[v]);
        P("\n");
    }

    // ---------------- sec_u : state-local scans ---------------------------
    P("\n## sec_u : B261 B262 B263 B264 B265 B267 B268 B269 B270\n");
    for (size_t gi = 0; gi < 5; ++gi) {          // n = 2..6
        Game& G = Gs[gi];
        int n = G.nmax;
        if (n < 4) continue;
        long long b261_pos = 0; int b261_max = -1; u64 b261_w = 0;
        long long b262_pos = 0; u64 b262_w = 0;
        long long b263_cmp = 0, b263_higher = 0;
        long long b264_pos = 0; u64 b264_w = 0;
        long long b265_pos = 0; u64 b265_w = 0;
        long long b267_pairs = 0, b267_ce = 0; u64 b267_w = 0;
        long long b268_pos = 0; u64 b268_w = 0;
        long long b270_pos = 0; u64 b270_w = 0;
        int b269_flat = 0, b269_flatP = 0, b269_non = 0, b269_nonP = 0;
        std::vector<int> jhist(64, 0);           // B266 joint histogram (b small)
        long long jt = 0;

        for (size_t i = 0; i < G.masks.size(); ++i) {
            u64 occ = G.masks[i];
            u64 lm = G.legal[i];
            if (!lm) continue;
            int pc = __builtin_popcountll(occ);
            // per-move u values
            int nL = __builtin_popcountll(lm);
            int umin = 1000, umax = -1, usum = 0;
            u64 wm = winning_moves(G, (int)i);
            int nw = __builtin_popcountll(wm);
            // B269 flatness layer
            bool flat = true;
            {
                u64 m = lm;
                int mn = 1000, mx = -1;
                while (m) { int p = __builtin_ctzll(m); m &= m - 1;
                    int u = u_of(G, (int)i, p); mn = std::min(mn, u); mx = std::max(mx, u); }
                flat = (mn == mx);
            }
            if (flat) { if (G.g[i] == 0) b269_flatP++; else b269_flat++; }
            else { if (G.g[i] == 0) b269_nonP++; else b269_non++; }

            u64 m = lm;
            while (m) {
                int p = __builtin_ctzll(m);
                m &= m - 1;
                int u = u_of(G, (int)i, p);
                usum += u;
                if (u < umin) umin = u;
                if (u > umax) umax = u;
                (void)nL;
            }
            // ---- B264 : every P-move has u=0, yet some move has u>0
            if (nw >= 1 && umax > 0) {
                bool allw0 = true;
                int rep = -1;
                u64 mm = wm;
                while (mm) { int p = __builtin_ctzll(mm); mm &= mm - 1;
                    if (rep < 0) rep = p;
                    if (u_of(G, (int)i, p) != 0) { allw0 = false; break; } }
                if (allw0 && rep >= 0) {
                    b264_pos++;
                    if (!b264_w) b264_w = occ | (u64(1) << rep);
                }
            }
            // ---- B265 : unique winning move with strictly intermediate u
            if (nw == 1 && umax > umin) {
                int p0 = __builtin_ctzll(wm);
                int u0 = u_of(G, (int)i, p0);
                if (umin < u0 && umax > u0) {
                    b265_pos++;
                    if (!b265_w) b265_w = occ | (u64(1) << p0);
                }
            }
            // ---- B263 : win-move child has strictly higher min-u than a non-win move
            if (nw >= 1) {
                int bestw = -1, bestn = -1;
                u64 mm = lm;
                while (mm) {
                    int p = __builtin_ctzll(mm); mm &= mm - 1;
                    int j = G.idx[occ | (u64(1) << p)];
                    int mn2 = 1000;
                    u64 l2 = G.legal[j];
                    while (l2) { int q = __builtin_ctzll(l2); l2 &= l2 - 1; mn2 = std::min(mn2, u_of(G, j, q)); }
                    if (mn2 == 1000) mn2 = -1;
                    if (G.g[j] == 0) bestw = std::max(bestw, mn2);
                    else bestn = std::max(bestn, mn2);
                }
                if (bestw >= 0 && bestn >= 0) { b263_cmp++; if (bestw > bestn) b263_higher++; }
            }
            // ---- pairs (p,q)
            for (int a = 0; a < G.b.V; ++a) {
                if (!(lm & (u64(1) << a))) continue;
                int ua = u_of(G, (int)i, a);
                for (int c2 = a + 1; c2 < G.b.V; ++c2) {
                    if (!(lm & (u64(1) << c2))) continue;
                    int uc = u_of(G, (int)i, c2);
                    u64 nfa = nf_mask(G, (int)i, a), nfc = nf_mask(G, (int)i, c2);
                    int ja = G.idx[occ | (u64(1) << a)];
                    int jc = G.idx[occ | (u64(1) << c2)];
                    // ---- B261 : both u small, joint large
                    if (ua <= 1 && uc <= 1) {
                        u64 lj = G.legal[jc];
                        u64 joint = lj & ~G.legal[G.idx[G.masks[jc] | (u64(1) << a)]] & ~(u64(1) << a);
                        int jn = __builtin_popcountll(joint);
                        jhist[jn > 63 ? 63 : jn]++;
                        jt++;
                        if (jn >= 2) { b261_pos++; if (jn > b261_max) { b261_max = jn; b261_w = occ | (u64(1) << a) | (u64(1) << c2); } }
                    }
                    // ---- B262 : both u >= 3, and q adds nothing after p
                    if (ua >= 3 && uc >= 3) {
                        u64 nq = nf_mask(G, jc, a);
                        if (nq == 0) { b262_pos++; if (!b262_w) b262_w = occ | (u64(1) << a) | (u64(1) << c2); }
                    }
                    // ---- B267 : same newly-forbidden set, different child g
                    if (nfa == nfc) {
                        b267_pairs++;
                        if (G.g[ja] != G.g[jc]) {
                            int L = __builtin_popcountll(lm);
                            if (L - pc <= 3) {
                                b267_ce++;
                                if (!b267_w) b267_w = occ | (u64(1) << a) | (u64(1) << c2);
                            }
                        }
                    }
                    // ---- B270 : exactly one of S+a, S+b is P
                    if ((G.g[ja] == 0) != (G.g[jc] == 0)) {
                        b270_pos++;
                        if (!b270_w) b270_w = occ | (u64(1) << a) | (u64(1) << c2);
                    }
                }
            }
            // ---- B268 : S subset T, |T\S|=1, both N, disjoint P-move sets
            if (G.g[i] > 0) {
                u64 m2 = lm;
                while (m2) {
                    int p = __builtin_ctzll(m2); m2 &= m2 - 1;
                    int j = G.idx[occ | (u64(1) << p)];
                    if (G.g[j] == 0) continue;
                    if ((wm & winning_moves(G, j)) == 0) {
                        b268_pos++;
                        if (!b268_w) b268_w = occ | (u64(1) << p);
                    }
                }
            }
        }
        P("  n=%d\n", n);
        P("    B261 positions_with_both_u_le1_and_joint_ge2 = %lld ; max_joint = %d\n", b261_pos, b261_max);
        P("    B262 positions_two_moves_u_ge3_second_adds_nothing = %lld\n", b262_pos);
        P("    B263 compared = %lld ; win_move_child_min_u_higher = %lld\n", b263_cmp, b263_higher);
        P("    B264 positions_all_Pmoves_u0_but_some_u_positive = %lld\n", b264_pos);
        P("    B265 positions_unique_winning_move_u_strictly_middle = %lld\n", b265_pos);
        P("    B267 pairs_same_nf = %lld ; counterexamples(K-|S|<=3) = %lld\n", b267_pairs, b267_ce);
        P("    B268 positions_one_stone_changes_all_best_moves = %lld\n", b268_pos);
        P("    B269 flat_u: %d (P %d) ; nonflat_u: %d (P %d)\n", b269_flat, b269_flatP, b269_non, b269_nonP);
        P("    B270 pairs_exactly_one_intermediate_P = %lld\n", b270_pos);
        if (n == 4) {
            P("    B266 joint-size histogram (pairs with both u<=1), pairs=%lld :\n", jt);
            for (int k = 0; k < 8; ++k) if (jhist[k]) P("      joint=%d : %d\n", k, jhist[k]);
        }
    }

    // ---------------- sec_switch : B238 ----------------------------------
    P("\n## sec_switch : B238 (switch-point formalisation)\n");
    P("  condition: q1,q2 in L(S) legal, p in L(S+q1) n L(S+q2), g(S+q1)=g(S+q2),\n");
    P("            g(S+q1+p) != g(S+q2+p)\n");
    for (size_t gi = 0; gi < 4; ++gi) {         // n=4..7? only 4,5 available
        Game& G = Gs[gi];
        int n = G.nmax;
        if (n > 5) continue;
        long long found = 0; u64 w = 0;
        for (size_t i = 0; i < G.masks.size(); ++i) {
            u64 occ = G.masks[i], lm = G.legal[i];
            u64 wm = winning_moves(G, (int)i);
            // iterate pairs of legal moves with equal child g
            for (int a = 0; a < G.b.V; ++a) {
                if (!(lm & (u64(1) << a))) continue;
                int ga = G.g[G.idx[occ | (u64(1) << a)]];
                for (int c2 = a + 1; c2 < G.b.V; ++c2) {
                    if (!(lm & (u64(1) << c2))) continue;
                    if (G.g[G.idx[occ | (u64(1) << c2)]] != ga) continue;
                    u64 Sa = occ | (u64(1) << a), Sc = occ | (u64(1) << c2);
                    int ja = G.idx[Sa], jc = G.idx[Sc];
                    u64 la = G.legal[ja], lc = G.legal[jc];
                    u64 common = la & lc;
                    while (common) {
                        int p = __builtin_ctzll(common); common &= common - 1;
                        if (p == a || p == c2) continue;
                        if (G.g[G.idx[Sa | (u64(1) << p)]] != G.g[G.idx[Sc | (u64(1) << p)]]) {
                            found++;
                            if (!w) w = occ | (u64(1) << a) | (u64(1) << c2) | (u64(1) << p);
                        }
                    }
                }
            }
            (void)wm;
        }
        P("  n=%d switch_points_found = %lld\n", n, found);
        if (w) {
            P("    witness S|q1|q2|p = %d,%d,%d,%d\n", G.b.pt_x[w % n], G.b.pt_y[w / n],
              G.b.pt_x[(w >> 6) % n], G.b.pt_y[(w >> 6) / n],
              G.b.pt_x[(w >> 12) % n], G.b.pt_y[(w >> 12) / n]);
        }
    }

    // ---------------- sec_xor : B240 -------------------------------------
    P("\n## sec_xor : B240 (equal-nimber parts, different surroundings)\n");
    {
        Game& G = Gs[2];                        // n=4
        int n = G.nmax;
        // group states by (g, popcount)
        std::vector<std::vector<int>> buckets;
        int maxk = G.K;
        std::vector<std::vector<int>> byk(maxk + 1);
        for (size_t i = 0; i < G.masks.size(); ++i)
            byk[__builtin_popcountll(G.masks[i])].push_back((int)i);
        long long separating_pairs = 0;
        u64 wit = 0;
        for (int k = 0; k <= maxk; ++k) {
            auto& v = byk[k];
            for (size_t x = 0; x < v.size(); ++x) {
                int i = v[x];
                if (G.legal[i] == 0) continue;
                for (size_t y = x + 1; y < v.size(); ++y) {
                    int j = v[y];
                    if (G.g[i] != G.g[j]) continue;
                    if (G.legal[j] == 0) continue;
                    u64 common = G.legal[i] & G.legal[j];
                    while (common) {
                        int p = __builtin_ctzll(common); common &= common - 1;
                        if (G.g[G.idx[G.masks[i] | (u64(1) << p)]] !=
                            G.g[G.idx[G.masks[j] | (u64(1) << p)]]) {
                            separating_pairs++;
                            if (!wit) wit = G.masks[i] | (u64(1) << p);
                            break;
                        }
                    }
                }
            }
        }
        P("  n=4 pairs_of_equal_nimber_single_stone_contexts_that_differ = %lld\n", separating_pairs);
        if (wit) P("    witness (S1 + external p) = %d,%d,%d,%d  mask=%llu\n",
                   G.b.pt_x[wit % n], G.b.pt_y[wit / n],
                   G.b.pt_x[(wit >> 6) % n], G.b.pt_y[(wit >> 6) / n], (unsigned long long)wit);
        P("    (search restricted to S1,S2 with equal g, same |S|, and a single\n");
        P("     common legal point p; any such triple is a witness)\n");
    }

    // ---------------- sec_local : B285 -----------------------------------
    P("\n## sec_local : B285 (same safe S on n=4..8 boards)\n");
    {
        std::vector<Board> boards;
        for (int n = 4; n <= 8; ++n) { Board b; build_square(b, n); boards.push_back(b); }
        // candidate shapes anchored at the origin corner
        struct Cand { const char* name; std::vector<std::pair<int,int>> pts; };
        std::vector<Cand> cands;
        cands.push_back({"2x2 block", {{0,0},{1,0},{0,1},{1,1}}});
        cands.push_back({"2x2 block + diag", {{0,0},{1,0},{0,1},{1,1},{2,2}}});
        cands.push_back({"L-shape 4", {{0,0},{0,1},{0,2},{1,0}}});
        cands.push_back({"line3 + off", {{0,0},{1,0},{2,0},{0,1}}});
        cands.push_back({"line4", {{0,0},{1,0},{2,0},{3,0}}});
        cands.push_back({"3x3 minus corner", {{0,0},{1,0},{2,0},{0,1},{1,1},{2,1},{0,2},{1,2}}});
        cands.push_back({"two diag pairs", {{0,0},{1,1},{2,0},{3,1}}});
        std::unordered_map<u64, int> memo;
        for (int bi = 0; bi < (int)boards.size(); ++bi) {
            Board& B = boards[bi];
            for (auto& c : cands) {
                u64 occ = 0; bool ok = true;
                for (auto& pt : c.pts) {
                    int x = pt.first, y = pt.second;
                    if (x >= B.n || y >= B.n) { ok = false; break; }
                    int id = y * B.n + x;
                    if (occ & (u64(1) << id)) { ok = false; break; }
                    // must be safe to add
                    bool legal = true;
                    for (u64 t : B.triples_by_pt[id]) if ((occ & t) == t) { legal = false; break; }
                    if (!legal) { ok = false; break; }
                    occ |= u64(1) << id;
                }
                if (!ok) continue;
                // grundy of the residual game by local memoised recursion
                std::function<int(u64)> gr = [&](u64 s) -> int {
                    auto it = memo.find(s);
                    if (it != memo.end()) return it->second;
                    unsigned long long seen = 0;
                    u64 l = legal_mask(B, s);
                    while (l) {
                        int p = __builtin_ctzll(l); l &= l - 1;
                        seen |= 1ULL << gr(s | (u64(1) << p));
                    }
                    int gg = 0;
                    while (seen & (1ULL << gg)) ++gg;
                    memo[s] = gg;
                    return gg;
                };
                int gg = gr(occ);
                P("  n=%d shape=%-20s |S|=%d g=%d\n", B.n, c.name, __builtin_popcountll(occ), gg);
            }
            memo.clear();
        }
    }

    // ---------------- sec_umax : B239 ------------------------------------
    P("\n## sec_umax : B239 (max newly-forbidden points, single move)\n");
    {
        // local search: for a mid-game safe set, max |u_S(p)| over legal p
        for (int n = 4; n <= 8; ++n) {
            Board B; build_square(B, n);
            // use a fixed mid-game shape: all points of the top-left k x k block minus one
            int best = -1; u64 bestmask = 0;
            for (int k = 2; k <= n; ++k) {
                u64 occ = 0;
                for (int y = 0; y < k; ++y) for (int x = 0; x < k; ++x) occ |= u64(1) << (y * n + x);
                // remove the centre if k odd and k>=3
                if (k >= 3) occ &= ~(u64(1) << ((k / 2) * n + k / 2));
                u64 l = legal_mask(B, occ);
                int mx = 0;
                while (l) {
                    int p = __builtin_ctzll(l); l &= l - 1;
                    int j = 0;
                    u64 l2 = legal_mask(B, occ | (u64(1) << p));
                    u64 nf = legal_mask(B, occ) & ~l2 & ~(u64(1) << p);
                    j = __builtin_popcountll(nf);
                    if (j > mx) { mx = j; if (mx > best) { best = mx; bestmask = occ; } }
                }
                if (mx > best) { best = mx; bestmask = occ; }
            }
            P("  n=%d max_single_move_newly_forbidden = %d (over k x k test families)\n", n, best);
        }
    }

    // ---------------- sec_orbit : B241 B242 ------------------------------
    P("\n## sec_orbit : B241 B242 (D4 orbit count of the winning-first-move set)\n");
    {
        for (size_t gi = 0; gi < 5; ++gi) {
            Game& G = Gs[gi];
            int n = G.nmax;
            if (n > 6) continue;
            // recompute W on the empty board: p is winning first move iff g({p})==0
            u64 W = 0;
            int orbits = 0;
            u64 seen = 0;
            int K = n;
            for (int y = 0; y < n; ++y) for (int x = 0; x < n; ++x) {
                int id = y * n + x;
                u64 occ = u64(1) << id;
                if (G.g[G.idx[occ]] == 0) W |= occ;
            }
            for (int y = 0; y < n; ++y) for (int x = 0; x < n; ++x) {
                int id = y * n + x;
                if (!(W & (u64(1) << id))) continue;
                if (seen & (u64(1) << id)) continue;
                orbits++;
                // 8 elements of the D4 orbit of (x,y) on the n x n board
                const int m = n - 1;
                int xs[8] = {x, m - x, y, m - y, x, x, m - x, m - x};
                int ys[8] = {y, y, x, x, m - y, m - x, m - x, m - y};
                for (int a = 0; a < 8; ++a) {
                    int ii = ys[a] * n + xs[a];
                    if (ii < 0 || ii >= n * n) continue;
                    if (W & (u64(1) << ii)) seen |= u64(1) << ii;
                }
            }
            P("  n=%d |W|=%d D4_orbits_in_W=%d\n", n, __builtin_popcountll(W), orbits);
        }
    }

    P("\n=== done ===\n");
    return 0;
}
