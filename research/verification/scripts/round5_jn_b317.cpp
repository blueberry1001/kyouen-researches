// Round5 J_n batch: B317 full perfect-matching breakability on J_4 (112,212 PMs).
// Also: B312 geometric classification of TD vs non-TD P pairs.
//
// Build: g++ -O2 -std=c++20 -o /tmp/jn_b317 round5_jn_b317.cpp
// ASan variant: g++ -O1 -g -fsanitize=address,undefined -std=c++20 ...
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <chrono>
#include <unordered_map>

#include "kc_core.h"

using u64 = uint64_t;
using namespace kc;

static int popcount(u64 x) { return __builtin_popcountll(x); }

// ---- Grundy for small boards (n<=6) ----
struct Solver {
    const Board& b;
    std::unordered_map<u64, int> memo;
    long long nodes = 0;
    explicit Solver(const Board& bb) : b(bb) {}
    int grundy(u64 occ) {
        auto it = memo.find(occ);
        if (it != memo.end()) return it->second;
        u64 L = legal_mask(b, occ);
        if (L == 0) { memo[occ] = 0; return 0; }
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

// ---- D4 orbit of an unordered pair on n x n ----
// point id = y*n + x
static void d4_image(int n, int p, int op, int& out) {
    int x = p % n, y = p / n;
    int rx, ry;
    switch (op) {
        case 0: rx = x; ry = y; break;             // id
        case 1: rx = n-1-x; ry = y; break;         // rot90? actually reflect x
        case 2: rx = x; ry = n-1-y; break;         // reflect y
        case 3: rx = n-1-x; ry = n-1-y; break;     // rot180
        case 4: rx = y; ry = x; break;             // transpose
        case 5: rx = n-1-y; ry = x; break;
        case 6: rx = y; ry = n-1-x; break;
        case 7: rx = n-1-y; ry = n-1-x; break;
        default: rx = x; ry = y; break;
    }
    out = ry * n + rx;
}
// 8 dihedral ops as permutations (the 4 rotations * 2 reflections).
// Simpler: generate the 8 images of (x,y) under D4.
static void d4_pair_orbit(int n, int a, int b, std::set<std::pair<int,int>>& orb) {
    int ax = a % n, ay = a / n, bx = b % n, by = b / n;
    int ops[8][4] = {
        // (x,y) -> (A*x + B*y + C, D*x + E*y + F) roughly; do explicit 8
        {0,0,0,0},{0,0,0,0},{0,0,0,0},{0,0,0,0},
        {0,0,0,0},{0,0,0,0},{0,0,0,0},{0,0,0,0}
    };
    (void)ops;
    int xs[8][2] = {
        {ax, ay}, {n-1-ax, ay}, {ax, n-1-ay}, {n-1-ax, n-1-ay},
        {ay, ax}, {n-1-ay, ax}, {ay, n-1-ax}, {n-1-ay, n-1-ax}
    };
    int ys[8][2] = {
        {bx, by}, {n-1-bx, by}, {bx, n-1-by}, {n-1-bx, n-1-by},
        {by, bx}, {n-1-by, bx}, {by, n-1-bx}, {n-1-by, n-1-bx}
    };
    for (int i = 0; i < 8; ++i) {
        int p = xs[i][1] * n + xs[i][0];
        int q = ys[i][1] * n + ys[i][0];
        if (p > q) std::swap(p, q);
        orb.insert({p, q});
    }
}

// ---- perfect matching enumeration ----
// vertices 0..V-1, adj as bitmasks
static void enum_pms(int V, const std::vector<u64>& adj, u64 matched,
                     std::vector<int>& pair_to, std::vector<std::array<int, 8>>& out,
                     std::array<int, 8>& cur, int depth) {
    if (matched == ((u64(1) << V) - 1)) {
        out.push_back(cur);
        return;
    }
    // pick smallest unmatched
    int i = 0;
    while ((matched >> i) & 1) ++i;
    u64 cand = adj[i] & ~matched;
    while (cand) {
        int j = __builtin_ctzll(cand);
        cand &= cand - 1;
        cur[depth] = i;
        // store partner in a parallel array — use pair encoding: cur as flat
        // We'll store edges as (i,j) pairs packed later. For simplicity store j in pair_to.
        pair_to[i] = j;
        pair_to[j] = i;
        enum_pms(V, adj, matched | (u64(1) << i) | (u64(1) << j), pair_to, out, cur, depth + 1);
    }
}

// Better: store PM as int partner[16]
static void enum_pms2(int V, const std::vector<u64>& adj, u64 matched,
                      std::vector<std::array<signed char, 64>>& out,
                      std::array<signed char, 64>& cur) {
    if (out.size() >= 200000) return; // safety, expected 112212
    if (matched == ((u64(1) << V) - 1)) {
        out.push_back(cur);
        return;
    }
    int i = 0;
    while ((matched >> i) & 1) ++i;
    u64 cand = adj[i] & ~matched;
    while (cand) {
        int j = __builtin_ctzll(cand);
        cand &= cand - 1;
        cur[i] = (signed char)j;
        cur[j] = (signed char)i;
        enum_pms2(V, adj, matched | (u64(1) << i) | (u64(1) << j), out, cur);
        // no need to reset cur[i]/cur[j]; they'll be overwritten
    }
}

int main(int argc, char** argv) {
    int n = 4;
    if (argc > 1) n = atoi(argv[1]);
    printf("B317/B312 checker n=%d\n", n);
    Board b;
    build_square(b, n);
    int V = b.V;
    printf("V=%d quads=%zu\n", V, b.quads.size());

    Solver sol(b);
    auto t0 = std::chrono::steady_clock::now();
    int g_empty = sol.grundy(0);
    auto t1 = std::chrono::steady_clock::now();
    printf("g_empty=%d nodes=%lld time=%.2fs\n", g_empty, sol.nodes,
           std::chrono::duration<double>(t1 - t0).count());

    // two-stone grundy -> J edges
    std::vector<u64> adj(V, 0);
    std::vector<std::pair<int,int>> p_pairs, nonp_pairs;
    for (int i = 0; i < V; ++i)
        for (int j = i + 1; j < V; ++j) {
            int g = sol.grundy((u64(1) << i) | (u64(1) << j));
            if (g == 0) {
                adj[i] |= u64(1) << j;
                adj[j] |= u64(1) << i;
                p_pairs.push_back({i, j});
            } else {
                nonp_pairs.push_back({i, j});
            }
        }
    int E = (int)p_pairs.size();
    printf("P_pairs=%d nonP=%d\n", E, (int)nonp_pairs.size());

    // ---- B312: total domination pairs vs P pairs ----
    // A pair {a,b} totally dominates if every vertex v has a neighbor in {a,b}
    // (including possibly v itself? No: total domination requires N[v] ∩ S ≠ ∅
    // for all v, and typically S independent... The prior analysis used:
    // every board point can be answered by at least one of the two points
    // as a winning reply — i.e. for every first move p, some s in S\{p?}
    // Actually from prior: "盤のどの点にも、その二点の少なくとも一つが別の点として必勝応答になる"
    // For every point p, there exists s in S with s ≠ p and edge {p,s} in J
    // (s is a winning response to first move p). That's total domination in J.
    std::vector<std::pair<int,int>> td_pairs;
    for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b) {
            u64 Sa = u64(1) << a, Sb = u64(1) << b;
            bool ok = true;
            for (int v = 0; v < V && ok; ++v) {
                u64 Nv = adj[v] | (u64(1) << v); // closed? open neighborhood
                // total dom: N(v) ∩ {a,b} ≠ ∅  (open neighborhood)
                u64 openN = adj[v];
                if (((openN & (Sa | Sb)) == 0)) ok = false;
            }
            if (ok) td_pairs.push_back({a, b});
        }
    printf("TD_pairs=%zu\n", td_pairs.size());

    int td_are_p = 0;
    for (auto& pr : td_pairs) {
        if (std::binary_search(p_pairs.begin(), p_pairs.end(), pr)) ++td_are_p;
    }
    printf("TD_are_P=%d/%zu\n", td_are_p, td_pairs.size());

    // D4 orbits of P pairs and TD pairs
    std::set<std::pair<int,int>> remaining_p(p_pairs.begin(), p_pairs.end());
    std::map<int, int> p_orbit_sizes;
    while (!remaining_p.empty()) {
        auto pr = *remaining_p.begin();
        std::set<std::pair<int,int>> orb;
        d4_pair_orbit(n, pr.first, pr.second, orb);
        int sz = 0;
        for (auto& e : orb) {
            if (remaining_p.erase(e)) ++sz;
        }
        // orbit size as full D4 image count
        p_orbit_sizes[(int)orb.size()]++;
    }
    std::set<std::pair<int,int>> remaining_td(td_pairs.begin(), td_pairs.end());
    std::map<int, int> td_orbit_sizes;
    std::map<std::pair<int,int>, int> pair_to_type;
    int type_id = 0;
    std::vector<std::vector<std::pair<int,int>>> type_members;
    // recompute orbit partition of P pairs with type ids
    {
        std::set<std::pair<int,int>> rem(p_pairs.begin(), p_pairs.end());
        while (!rem.empty()) {
            auto pr = *rem.begin();
            std::set<std::pair<int,int>> orb;
            d4_pair_orbit(n, pr.first, pr.second, orb);
            std::vector<std::pair<int,int>> members;
            for (auto& e : orb) {
                if (rem.erase(e)) {
                    pair_to_type[e] = type_id;
                    members.push_back(e);
                }
            }
            type_members.push_back(members);
            ++type_id;
        }
    }
    int num_p_types = type_id;
    int num_td_types = 0;
    std::set<int> td_type_ids;
    for (auto& pr : td_pairs) td_type_ids.insert(pair_to_type[pr]);
    num_td_types = (int)td_type_ids.size();
    printf("P_d4_types=%d TD_d4_types=%d\n", num_p_types, num_td_types);

    // geometric features: distance^2, manhattan, L_inf, is_corner_involved
    auto dist2 = [&](int a, int b) {
        int ax = a % n, ay = a / n, bx = b % n, by = b / n;
        int dx = ax - bx, dy = ay - by;
        return dx * dx + dy * dy;
    };
    auto linf = [&](int a, int b) {
        int ax = a % n, ay = a / n, bx = b % n, by = b / n;
        return std::max(std::abs(ax - bx), std::abs(ay - by));
    };
    auto is_corner = [&](int p) {
        int x = p % n, y = p / n;
        return (x == 0 || x == n - 1) && (y == 0 || y == n - 1);
    };
    std::map<int, int> td_d2_hist, nontd_d2_hist;
    std::map<int, int> td_linf_hist, nontd_linf_hist;
    int td_corner = 0, nontd_corner = 0;
    for (auto& pr : td_pairs) {
        td_d2_hist[dist2(pr.first, pr.second)]++;
        td_linf_hist[linf(pr.first, pr.second)]++;
        if (is_corner(pr.first) || is_corner(pr.second)) ++td_corner;
    }
    std::set<std::pair<int,int>> td_set(td_pairs.begin(), td_pairs.end());
    for (auto& pr : p_pairs) {
        if (td_set.count(pr)) continue;
        nontd_d2_hist[dist2(pr.first, pr.second)]++;
        nontd_linf_hist[linf(pr.first, pr.second)]++;
        if (is_corner(pr.first) || is_corner(pr.second)) ++nontd_corner;
    }
    printf("TD_d2_hist:");
    for (auto& kv : td_d2_hist) printf(" %d:%d", kv.first, kv.second);
    printf("\nnonTD_d2_hist:");
    for (auto& kv : nontd_d2_hist) printf(" %d:%d", kv.first, kv.second);
    printf("\nTD_linf:");
    for (auto& kv : td_linf_hist) printf(" %d:%d", kv.first, kv.second);
    printf("\nnonTD_linf:");
    for (auto& kv : nontd_linf_hist) printf(" %d:%d", kv.first, kv.second);
    printf("\nTD_corner=%d nonTD_corner=%d\n", td_corner, nontd_corner);

    // ---- B317: enumerate all PMs of J ----
    if (E == 0) {
        printf("B317: J is empty, no PMs\n");
        return 0;
    }
    std::vector<std::array<signed char, 64>> pms;
    std::array<signed char, 64> cur;
    cur.fill(-1);
    auto t2 = std::chrono::steady_clock::now();
    enum_pms2(V, adj, 0, pms, cur);
    auto t3 = std::chrono::steady_clock::now();
    printf("num_PMs=%zu time=%.2fs\n", pms.size(),
           std::chrono::duration<double>(t3 - t2).count());

    // breakability
    int unbreakable = 0;
    int min_breaks = 1 << 30, max_breaks = 0;
    long long total_breaks = 0;
    std::vector<int> unbreakable_ids;
    for (size_t pi = 0; pi < pms.size(); ++pi) {
        auto& M = pms[pi];
        int breaks = 0;
        for (int p = 0; p < V; ++p) {
            int m = M[p];
            u64 occ2 = (u64(1) << p) | (u64(1) << m);
            u64 L = legal_mask(b, occ2);
            u64 qmask = L;
            while (qmask) {
                int q = __builtin_ctzll(qmask);
                qmask &= qmask - 1;
                int mq = M[q];
                if (occ2 & (u64(1) << mq)) {
                    ++breaks;
                } else if (!can_add(b, occ2 | (u64(1) << q), mq)) {
                    ++breaks;
                }
            }
        }
        total_breaks += breaks;
        if (breaks < min_breaks) min_breaks = breaks;
        if (breaks > max_breaks) max_breaks = breaks;
        if (breaks == 0) {
            ++unbreakable;
            if (unbreakable_ids.size() < 10) unbreakable_ids.push_back((int)pi);
        }
    }
    printf("B317: unbreakable=%d min_breaks=%d max_breaks=%lld avg=%.2f\n",
           unbreakable, min_breaks, (long long)max_breaks,
           pms.empty() ? 0.0 : (double)total_breaks / (double)pms.size());
    printf("sample_unbreakable_ids:");
    for (int id : unbreakable_ids) printf(" %d", id);
    printf("\n");

    // ---- deep check: is the pairing strategy a winning strategy for P2? ----
    // DFS: P1 chooses any legal q; P2 must answer M(q). Fail if M(q) occupied/illegal.
    // Win for P2 if every line ends with P1 unable to move.
    struct PairWin {
        const Board& b;
        const signed char* M;
        long long nodes = 0;
        bool wins(u64 occ) {
            ++nodes;
            u64 L = legal_mask(b, occ);
            if (L == 0) return true;  // P1 to move and stuck => P2 wins
            u64 m = L;
            while (m) {
                int q = __builtin_ctzll(m);
                m &= m - 1;
                int mq = M[q];
                if (mq < 0) return false;
                if (occ & (u64(1) << mq)) return false;
                if (!can_add(b, occ | (u64(1) << q), mq)) return false;
                if (!wins(occ | (u64(1) << q) | (u64(1) << mq))) return false;
            }
            return true;
        }
    };
    int pair_win = 0;
    int pair_win_among_unbreakable = 0;
    std::vector<int> pair_win_ids;
    // First: all unbreakable PMs (expected few thousand)
    // Also sample breakable ones? Check ALL PMs — 112k * small tree is OK.
    long long total_pair_nodes = 0;
    for (size_t pi = 0; pi < pms.size(); ++pi) {
        PairWin pw{b, pms[pi].data(), 0};
        if (pw.wins(0)) {
            ++pair_win;
            total_pair_nodes += pw.nodes;
            if (pair_win_ids.size() < 8) pair_win_ids.push_back((int)pi);
            // is this PM also unbreakable at first-pair stage?
            // recompute breaks==0 quickly
            auto& M = pms[pi];
            int breaks = 0;
            for (int p = 0; p < V && breaks == 0; ++p) {
                int m = M[p];
                u64 occ2 = (u64(1) << p) | (u64(1) << m);
                u64 L = legal_mask(b, occ2);
                u64 qmask = L;
                while (qmask) {
                    int q = __builtin_ctzll(qmask);
                    qmask &= qmask - 1;
                    int mq = M[q];
                    if (occ2 & (u64(1) << mq)) { ++breaks; break; }
                    if (!can_add(b, occ2 | (u64(1) << q), mq)) { ++breaks; break; }
                }
            }
            if (breaks == 0) ++pair_win_among_unbreakable;
        }
    }
    printf("pairing_strategy_wins=%d  (of those, first-pair-unbreakable=%d)\n",
           pair_win, pair_win_among_unbreakable);
    printf("sample_pair_win_ids:");
    for (int id : pair_win_ids) printf(" %d", id);
    printf("\n");
    printf("total_pair_dfs_nodes=%lld\n", total_pair_nodes);

    // self-check
    if (n == 4) {
        printf("SELF_CHECK n=4: E==84? %s  PM==112212? %s  TD==40? %s\n",
               E == 84 ? "YES" : "NO",
               pms.size() == 112212 ? "YES" : "NO",
               td_pairs.size() == 40 ? "YES" : "NO");
    }

    // write compact JSON
    FILE* f = fopen("/tmp/jn_b317_out.json", "w");
    if (f) {
        fprintf(f, "{\n");
        fprintf(f, "  \"n\": %d,\n", n);
        fprintf(f, "  \"g_empty\": %d,\n", g_empty);
        fprintf(f, "  \"V\": %d,\n", V);
        fprintf(f, "  \"E\": %d,\n", E);
        fprintf(f, "  \"num_PMs\": %zu,\n", pms.size());
        fprintf(f, "  \"TD_pairs\": %zu,\n", td_pairs.size());
        fprintf(f, "  \"TD_are_P\": %d,\n", td_are_p);
        fprintf(f, "  \"P_d4_types\": %d,\n", num_p_types);
        fprintf(f, "  \"TD_d4_types\": %d,\n", num_td_types);
        fprintf(f, "  \"B317_unbreakable\": %d,\n", unbreakable);
        fprintf(f, "  \"B317_min_breaks\": %d,\n", min_breaks);
        fprintf(f, "  \"B317_max_breaks\": %d,\n", max_breaks);
        fprintf(f, "  \"B317_total_breaks\": %lld,\n", total_breaks);
        fprintf(f, "  \"B317_pairing_wins\": %d,\n", pair_win);
        fprintf(f, "  \"B317_pairing_wins_unbreakable\": %d,\n", pair_win_among_unbreakable);
        fprintf(f, "  \"TD_d2_hist\": {");
        bool first = true;
        for (auto& kv : td_d2_hist) {
            fprintf(f, "%s\"%d\": %d", first ? "" : ", ", kv.first, kv.second);
            first = false;
        }
        fprintf(f, "},\n");
        fprintf(f, "  \"nonTD_d2_hist\": {");
        first = true;
        for (auto& kv : nontd_d2_hist) {
            fprintf(f, "%s\"%d\": %d", first ? "" : ", ", kv.first, kv.second);
            first = false;
        }
        fprintf(f, "},\n");
        fprintf(f, "  \"TD_corner\": %d,\n", td_corner);
        fprintf(f, "  \"nonTD_corner\": %d\n", nontd_corner);
        fprintf(f, "}\n");
        fclose(f);
        printf("wrote /tmp/jn_b317_out.json\n");
    }
    return 0;
}
