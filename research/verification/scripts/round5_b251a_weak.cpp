// Weak-version stages for B251-B270 follow-up (round5_b251a_weak).
// Usage: <stage>
// Stages:
//   pairs4sens  - n=4 all pair lifts, label-change strength, same-conic vs scatter (B252)
//   singles5sens - n=5 all single lifts, flips + label-change sensitivity (B251/B260)
//   b261bound   - n=4 joint unlock counts + |joint|<=u(p)+u(q)+|S| check (B261)
//   b263n5      - n=5 child min-u / q25 stats for winning vs losing moves (B263)
//   b254n5      - n=5 maximal safe sets + sensitivity-lift effect (B254)
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <chrono>
#include <cmath>
#include <functional>

#ifdef _OPENMP
#include <omp.h>
#endif

using u64 = uint64_t;

static long long det4(const long long r[4][4]) {
    long long total = 0;
    for (int i = 0; i < 4; ++i) {
        long long mm[3][3];
        int ri = 0;
        for (int r2 = 0; r2 < 4; ++r2) {
            if (r2 == i) continue;
            int ci = 0;
            for (int c2 = 1; c2 < 4; ++c2) mm[ri][ci++] = r[r2][c2];
            ++ri;
        }
        long long d3 = mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
                     - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
                     + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]);
        total += (i % 2 == 0 ? 1 : -1) * r[i][0] * d3;
    }
    return total;
}

struct Board {
    int n = 0, V = 0;
    u64 full = 0;
    std::vector<std::vector<u64>> triples_by_pt;
    std::vector<std::vector<int>> tri_quad;
    std::vector<u64> quads;
    std::vector<int> px, py;
    std::vector<u64> conic_support; // all board points on the quad's circle/line
};

static void build_square(Board& b, int n) {
    b.n = n; b.V = n * n;
    b.full = (u64(1) << b.V) - 1;
    b.triples_by_pt.assign(b.V, {});
    b.tri_quad.assign(b.V, {});
    b.quads.clear();
    b.conic_support.clear();
    b.px.assign(b.V, 0); b.py.assign(b.V, 0);
    std::vector<std::array<long long, 4>> rows(b.V);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            b.px[i] = x; b.py[i] = y;
            rows[i] = {(long long)x * x + (long long)y * y, x, y, 1};
        }
    auto row_of = [&](int i) { return rows[i]; };
    for (int a = 0; a < b.V - 3; ++a)
    for (int c1 = a + 1; c1 < b.V - 2; ++c1)
    for (int c2 = c1 + 1; c2 < b.V - 1; ++c2)
    for (int d = c2 + 1; d < b.V; ++d) {
        int ids[4] = {a, c1, c2, d};
        long long m[4][4];
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = row_of(ids[i])[j];
        if (det4(m) != 0) continue;
        u64 q = 0;
        for (int i = 0; i < 4; ++i) q |= u64(1) << ids[i];
        int qi = (int)b.quads.size();
        b.quads.push_back(q);
        for (int t = 0; t < 4; ++t) {
            u64 o = 0;
            for (int s = 0; s < 4; ++s) if (s != t) o |= u64(1) << ids[s];
            b.triples_by_pt[ids[t]].push_back(o);
            b.tri_quad[ids[t]].push_back(qi);
        }
        // conic support: all board points on the same circle/line as these 4
        u64 sup = q;
        // take first 3 points of the quad; a point p is on the conic iff det(p0,p1,p2,p)=0
        int i0 = ids[0], i1 = ids[1], i2 = ids[2];
        for (int p = 0; p < b.V; ++p) {
            if (p == i0 || p == i1 || p == i2 || p == ids[3]) continue;
            long long mp[4][4];
            long long r0[4] = {rows[i0][0], rows[i0][1], rows[i0][2], rows[i0][3]};
            long long r1[4] = {rows[i1][0], rows[i1][1], rows[i1][2], rows[i1][3]};
            long long r2[4] = {rows[i2][0], rows[i2][1], rows[i2][2], rows[i2][3]};
            long long r3[4] = {rows[p][0], rows[p][1], rows[p][2], rows[p][3]};
            for (int j = 0; j < 4; ++j) {
                mp[0][j] = r0[j]; mp[1][j] = r1[j]; mp[2][j] = r2[j]; mp[3][j] = r3[j];
            }
            if (det4(mp) == 0) sup |= u64(1) << p;
        }
        b.conic_support.push_back(sup);
    }
}

static inline u64 legal_mask_lift(const Board& b, u64 occ, const std::vector<char>& lifted) {
    u64 out = 0;
    u64 empty = b.full & ~occ;
    while (empty) {
        int p = __builtin_ctzll(empty);
        empty &= empty - 1;
        bool ok = true;
        const auto& tris = b.triples_by_pt[p];
        const auto& qid = b.tri_quad[p];
        for (size_t i = 0; i < tris.size(); ++i) {
            if (lifted[qid[i]]) continue;
            if ((occ & tris[i]) == tris[i]) { ok = false; break; }
        }
        if (ok) out |= u64(1) << p;
    }
    return out;
}

static int u_gain(const Board& b, u64 occ, int p) {
    std::vector<char> none(b.quads.size(), 0);
    u64 L = legal_mask_lift(b, occ, none);
    u64 Lp = legal_mask_lift(b, occ | (u64(1) << p), none);
    return __builtin_popcountll(L & ~(Lp | (u64(1) << p)));
}

static void print_quad(FILE* f, const Board& b, u64 q) {
    fputc('[', f);
    bool first = true;
    for (int p = 0; p < b.V; ++p) if (q & (u64(1) << p)) {
        fprintf(f, "%s[%d,%d]", first ? "" : ",", b.px[p], b.py[p]);
        first = false;
    }
    fputc(']', f);
}

// Generic outcome solver (win only, optional label-change vs reference)
struct SolveOut {
    std::vector<u64> states;
    std::vector<uint8_t> win;
    std::unordered_map<u64, int> idx;
    int g0 = 0;
};

static SolveOut solve_gen(const Board& b, const std::vector<char>& lifted) {
    SolveOut R;
    std::vector<u64> order;
    {
        std::unordered_set<u64> seen;
        seen.reserve(1 << 20);
        std::vector<u64> stack = {0};
        seen.insert(0);
        while (!stack.empty()) {
            u64 s = stack.back(); stack.pop_back();
            order.push_back(s);
            u64 lm = legal_mask_lift(b, s, lifted);
            while (lm) {
                int p = __builtin_ctzll(lm); lm &= lm - 1;
                u64 ns = s | (u64(1) << p);
                if (seen.insert(ns).second) stack.push_back(ns);
            }
        }
    }
    std::sort(order.begin(), order.end(), [](u64 a, u64 b) {
        return __builtin_popcountll(a) > __builtin_popcountll(b);
    });
    R.states = order;
    R.idx.reserve(order.size() * 2);
    for (size_t i = 0; i < order.size(); ++i) R.idx[order[i]] = (int)i;
    R.win.assign(order.size(), 0);
    for (size_t i = 0; i < order.size(); ++i) {
        u64 s = order[i];
        u64 lm = legal_mask_lift(b, s, lifted);
        if (lm == 0) { R.win[i] = 0; continue; }
        bool any_lose = false;
        u64 t = lm;
        while (t) {
            int p = __builtin_ctzll(t); t &= t - 1;
            if (R.win[R.idx.at(s | (u64(1) << p))] == 0) { any_lose = true; break; }
        }
        R.win[i] = any_lose ? 1 : 0;
    }
    R.g0 = R.win[R.idx.at(0)];
    return R;
}

static int label_changes(const SolveOut& a, const SolveOut& b) {
    // count states present in both where win differs; use smaller idx map
    const SolveOut* small = a.states.size() <= b.states.size() ? &a : &b;
    const SolveOut* large = a.states.size() <= b.states.size() ? &b : &a;
    int ch = 0;
    for (size_t i = 0; i < small->states.size(); ++i) {
        auto it = large->idx.find(small->states[i]);
        if (it == large->idx.end()) continue;
        if (small->win[i] != large->win[it->second]) ++ch;
    }
    return ch;
}

// ---------- n=4 all pair lifts: same-conic vs scatter strength (B252) ----------
static void stage_pairs4sens() {
    Board b0;
    build_square(b0, 4);
    std::vector<char> lifted0(b0.quads.size(), 0);
    auto std_r = solve_gen(b0, lifted0);
    int g0s = std_r.g0;
    int nq = (int)b0.quads.size();
    fprintf(stderr, "n=4 nq=%d states=%d g0=%d\n", nq, (int)std_r.states.size(), g0s);

    // classify pairs
    long long n_same = 0, n_scatter = 0, n_touch = 0; // touch = share 1 pt, different conic
    long long sum_same = 0, sum_scatter = 0, sum_touch = 0;
    long long flip_same = 0, flip_scatter = 0, flip_touch = 0, flip_all = 0;
    int max_same = 0, max_scatter = 0, max_touch = 0;
    // also by shared-point count
    long long sum_sh[4] = {0}, n_sh[4] = {0}, flip_sh[4] = {0};
    int max_sh[4] = {0};

    for (int a = 0; a < nq; ++a) {
        for (int c = a + 1; c < nq; ++c) {
            std::vector<char> lifted(nq, 0);
            lifted[a] = lifted[c] = 1;
            auto rg = solve_gen(b0, lifted);
            int lc = label_changes(std_r, rg);
            bool fl = rg.g0 != g0s;
            if (fl) ++flip_all;
            u64 inter = b0.quads[a] & b0.quads[c];
            int sh = __builtin_popcountll(inter);
            if (sh > 3) sh = 3;
            sum_sh[sh] += lc; n_sh[sh]++; if (lc > max_sh[sh]) max_sh[sh] = lc;
            if (fl) flip_sh[sh]++;
            bool same = (b0.conic_support[a] == b0.conic_support[c]) && __builtin_popcountll(b0.conic_support[a]) >= 5;
            // also same-conic if one quad sits entirely on the other's conic
            if (!same) {
                if ((b0.quads[a] & b0.conic_support[c]) == b0.quads[a] && __builtin_popcountll(b0.conic_support[c]) >= 5) same = true;
                if ((b0.quads[c] & b0.conic_support[a]) == b0.quads[c] && __builtin_popcountll(b0.conic_support[a]) >= 5) same = true;
            }
            if (same) {
                ++n_same; sum_same += lc;
                if (lc > max_same) max_same = lc;
                if (fl) ++flip_same;
            } else if (sh == 0) {
                ++n_scatter; sum_scatter += lc;
                if (lc > max_scatter) max_scatter = lc;
                if (fl) ++flip_scatter;
            } else {
                ++n_touch; sum_touch += lc;
                if (lc > max_touch) max_touch = lc;
                if (fl) ++flip_touch;
            }
        }
    }
    printf("{\"stage\":\"pairs4sens\",\"n\":4,\"nquads\":%d,\"g0_std\":%d,", nq, g0s);
    printf("\"B251_pair_flips\":%lld,", flip_all);
    printf("\"B252_same_conic\":{\"n\":%lld,\"sum_lc\":%lld,\"max_lc\":%d,\"flips\":%lld},",
           n_same, sum_same, max_same, flip_same);
    printf("\"B252_scatter\":{\"n\":%lld,\"sum_lc\":%lld,\"max_lc\":%d,\"flips\":%lld},",
           n_scatter, sum_scatter, max_scatter, flip_scatter);
    printf("\"B252_touch1\":{\"n\":%lld,\"sum_lc\":%lld,\"max_lc\":%d,\"flips\":%lld},",
           n_touch, sum_touch, max_touch, flip_touch);
    printf("\"by_shared\":[");
    for (int i = 0; i < 4; ++i) {
        printf("%s{\"sh\":%d,\"n\":%lld,\"sum_lc\":%lld,\"max_lc\":%d,\"flips\":%lld}",
               i ? "," : "", i, n_sh[i], sum_sh[i], max_sh[i], flip_sh[i]);
    }
    printf("],\"done\":true}\n");
}

// ---------- n=5 all single lifts (B251 flips + B260 sensitivity) ----------
static void stage_singles5sens() {
    Board b0;
    build_square(b0, 5);
    std::vector<char> lifted0(b0.quads.size(), 0);
    auto std_r = solve_gen(b0, lifted0);
    int g0s = std_r.g0;
    int nq = (int)b0.quads.size();
    fprintf(stderr, "n=5 nq=%d states=%d g0=%d\n", nq, (int)std_r.states.size(), g0s);

    // n=5 W = winning first moves from empty (standard rules)
    std::vector<int> W;
    {
        u64 lm = legal_mask_lift(b0, 0, lifted0);
        while (lm) {
            int p = __builtin_ctzll(lm); lm &= lm - 1;
            auto it = std_r.idx.at(0 | (u64(1) << p));
            if (std_r.win[it] == 0) W.push_back(p); // child is losing => this move wins
        }
    }
    fprintf(stderr, "W size=%d\n", (int)W.size());

    std::vector<int> flips(nq, 0), lc(nq, 0);
    // shared-point degree of each quad (how "clustered" its points are is not needed;
    // instead: max conic support size, and whether any pair of its points is in W)
    #pragma omp parallel for schedule(dynamic)
    for (int qi = 0; qi < nq; ++qi) {
        std::vector<char> lifted(nq, 0);
        lifted[qi] = 1;
        auto rg = solve_gen(b0, lifted);
        if (rg.g0 != g0s) flips[qi] = 1;
        lc[qi] = label_changes(std_r, rg);
    }
    int nflip = 0; for (int x : flips) nflip += x;
    long long sumlc = 0; int maxlc = 0;
    for (int x : lc) { sumlc += x; if (x > maxlc) maxlc = x; }

    // sensitivity ranking vs W: among top-k by lc, how many quads contain a W point
    std::vector<int> ord(nq);
    for (int i = 0; i < nq; ++i) ord[i] = i;
    std::sort(ord.begin(), ord.end(), [&](int a, int b) { return lc[a] > lc[b]; });

    auto containsW = [&](int qi) -> int {
        u64 q = b0.quads[qi];
        int c = 0;
        for (int p : W) if (q & (u64(1) << p)) ++c;
        return c;
    };
    // expected: random quad contains how many W points? W has 9 of 25 points.
    int top10_W = 0, top20_W = 0, top50_W = 0, all_W = 0;
    for (int i = 0; i < nq; ++i) {
        int c = containsW(ord[i]);
        all_W += c;
        if (i < 10) top10_W += c;
        if (i < 20) top20_W += c;
        if (i < 50) top50_W += c;
    }
    // hypergeometric-ish baseline: each quad has 4 points, P(point in W)=9/25
    double exp_per_quad = 4.0 * 9.0 / 25.0;

    printf("{\"stage\":\"singles5sens\",\"n\":5,\"nquads\":%d,\"states_std\":%d,\"g0_std\":%d,",
           nq, (int)std_r.states.size(), g0s);
    printf("\"W\":[");
    for (size_t i = 0; i < W.size(); ++i) printf("%s%d", i ? "," : "", W[i]);
    printf("],\"W_coords\":[");
    for (size_t i = 0; i < W.size(); ++i) {
        printf("%s[%d,%d]", i ? "," : "", b0.px[W[i]], b0.py[W[i]]);
    }
    printf("],");
    printf("\"B251_flips\":%d,", nflip);
    printf("\"B257_label_changes_sum\":%lld,\"B257_label_changes_max\":%d,", sumlc, maxlc);
    printf("\"B260_top10_Wpts\":%d,\"B260_top20_Wpts\":%d,\"B260_top50_Wpts\":%d,",
           top10_W, top20_W, top50_W);
    printf("\"B260_all_quad_Wpts\":%d,\"B260_exp_per_quad\":%.4f,", all_W, exp_per_quad);
    printf("\"B257_top\":[");
    for (int i = 0; i < 15; ++i) {
        int qi = ord[i];
        printf("%s{\"qidx\":%d,\"lc\":%d,\"wpts\":%d,\"sup\":%d,\"quad\":",
               i ? "," : "", qi, lc[qi], containsW(qi), __builtin_popcountll(b0.conic_support[qi]));
        print_quad(stdout, b0, b0.quads[qi]);
        printf("}");
    }
    printf("],\"done\":true}\n");
}

// ---------- n=4 joint unlock bound + u<=1 counts (B261) ----------
// Rebuild all safe-reachable states via solve_gen, then check
// |joint| <= u(p)+u(q)+|S| and count u<=1 both with joint>=2.
static void stage_b261bound() {
    Board b0;
    build_square(b0, 4);
    std::vector<char> none(b0.quads.size(), 0);
    auto G = solve_gen(b0, none);
    fprintf(stderr, "n=4 states=%d g0=%d\n", (int)G.states.size(), G.g0);

    long long pos_with_pair = 0;
    long long cnt_le1_jointge2 = 0;
    int max_joint = 0, max_joint_le1 = 0;
    long long bound_violations = 0;
    long long pairs_checked = 0;
    int max_joint_witness_S = -1, max_joint_p = -1, max_joint_q = -1;

    for (u64 s : G.states) {
        u64 L = legal_mask_lift(b0, s, none);
        if (L == 0) continue;
        std::vector<int> moves, us;
        u64 tmp = L;
        while (tmp) {
            int p = __builtin_ctzll(tmp); tmp &= tmp - 1;
            moves.push_back(p);
            us.push_back(u_gain(b0, s, p));
        }
        if (moves.size() < 2) continue;
        ++pos_with_pair;
        int nsz = __builtin_popcountll(s);
        for (size_t i = 0; i < moves.size(); ++i) {
            for (size_t j = i + 1; j < moves.size(); ++j) {
                u64 Lpq = legal_mask_lift(b0, s | (u64(1) << moves[i]) | (u64(1) << moves[j]), none);
                int jn = __builtin_popcountll(L & ~(Lpq | (u64(1) << moves[i]) | (u64(1) << moves[j])));
                ++pairs_checked;
                if (jn > max_joint) {
                    max_joint = jn;
                    max_joint_witness_S = nsz; max_joint_p = moves[i]; max_joint_q = moves[j];
                }
                int ub = us[i] + us[j] + nsz;
                if (jn > ub) ++bound_violations;
                if (us[i] <= 1 && us[j] <= 1 && jn >= 2) {
                    ++cnt_le1_jointge2;
                    if (jn > max_joint_le1) max_joint_le1 = jn;
                }
            }
        }
    }
    printf("{\"stage\":\"b261bound\",\"n\":4,\"states\":%d,\"g0\":%d,",
           (int)G.states.size(), G.g0);
    printf("\"pairs_checked\":%lld,\"positions_with_pair\":%lld,", pairs_checked, pos_with_pair);
    printf("\"B261_cnt_u_le1_joint_ge2\":%lld,\"B261_max_joint_le1\":%d,",
           cnt_le1_jointge2, max_joint_le1);
    printf("\"B261_max_joint\":%d,\"B261_bound_violations\":%lld,",
           max_joint, bound_violations);
    printf("\"B261_max_joint_witness\":{\"|S|\":%d,\"p\":%d,\"q\":%d},",
           max_joint_witness_S, max_joint_p, max_joint_q);
    printf("\"done\":true}\n");
}

// ---------- n=5 child min-u / q25 (B263) ----------
static void stage_b263n5() {
    Board b0;
    build_square(b0, 5);
    std::vector<char> none(b0.quads.size(), 0);
    // need win labels only
    auto G = solve_gen(b0, none);
    fprintf(stderr, "n=5 states=%d g0=%d\n", (int)G.states.size(), G.g0);

    long long cmp = 0, hi_min = 0, hi_q25 = 0;
    long long sum_win_min = 0, sum_lose_min = 0;
    long long n_win_min = 0, n_lose_min = 0;
    // stratify by |S|
    std::map<int, std::array<long long, 2>> byS; // |S| -> [cmp, hi_min]
    std::map<int, std::array<long long, 2>> byL; // |L| -> [cmp, hi_min]

    for (size_t si = 0; si < G.states.size(); ++si) {
        u64 s = G.states[si];
        u64 L = legal_mask_lift(b0, s, none);
        if (L == 0) continue;
        std::vector<int> moves, win_i, lose_i;
        u64 tmp = L;
        while (tmp) {
            int p = __builtin_ctzll(tmp); tmp &= tmp - 1;
            moves.push_back(p);
            int cidx = G.idx.at(s | (u64(1) << p));
            if (G.win[cidx] == 0) win_i.push_back((int)moves.size() - 1);
            else lose_i.push_back((int)moves.size() - 1);
        }
        if (win_i.empty() || lose_i.empty()) continue;

        auto child_min = [&](int p) -> int {
            u64 sp = s | (u64(1) << p);
            u64 Lsp = legal_mask_lift(b0, sp, none);
            int mn = 999;
            while (Lsp) {
                int q = __builtin_ctzll(Lsp); Lsp &= Lsp - 1;
                int u = u_gain(b0, sp, q);
                if (u < mn) mn = u;
            }
            return mn == 999 ? 0 : mn;
        };
        auto child_q = [&](int p) -> int {
            u64 sp = s | (u64(1) << p);
            u64 Lsp = legal_mask_lift(b0, sp, none);
            std::vector<int> v;
            while (Lsp) {
                int q = __builtin_ctzll(Lsp); Lsp &= Lsp - 1;
                v.push_back(u_gain(b0, sp, q));
            }
            if (v.empty()) return 0;
            std::sort(v.begin(), v.end());
            return v[v.size() / 4];
        };

        int best_win_min = 999, best_lose_min = 999;
        for (int mi : win_i) { int m = child_min(moves[mi]); if (m < best_win_min) best_win_min = m; }
        for (int mi : lose_i) { int m = child_min(moves[mi]); if (m < best_lose_min) best_lose_min = m; }
        ++cmp;
        sum_win_min += best_win_min; n_win_min++;
        sum_lose_min += best_lose_min; n_lose_min++;
        if (best_win_min > best_lose_min) ++hi_min;
        int nsz = __builtin_popcountll(s);
        int nl = __builtin_popcountll(L);
        byS[nsz][0]++; if (best_win_min > best_lose_min) byS[nsz][1]++;
        byL[nl][0]++; if (best_win_min > best_lose_min) byL[nl][1]++;

        int wq = 999, lq = 999;
        for (int mi : win_i) { int q = child_q(moves[mi]); if (q < wq) wq = q; }
        for (int mi : lose_i) { int q = child_q(moves[mi]); if (q < lq) lq = q; }
        if (wq > lq) ++hi_q25;
    }
    printf("{\"stage\":\"b263n5\",\"n\":5,\"states\":%d,\"g0\":%d,", (int)G.states.size(), G.g0);
    printf("\"cmp\":%lld,\"hi_min\":%lld,\"hi_q25\":%lld,", cmp, hi_min, hi_q25);
    printf("\"avg_win_min\":%.4f,\"avg_lose_min\":%.4f,",
           n_win_min ? sum_win_min / (double)n_win_min : 0.0,
           n_lose_min ? sum_lose_min / (double)n_lose_min : 0.0);
    printf("\"by_S\":{");
    bool f = true;
    for (auto& kv : byS) {
        printf("%s\"%d\":[%lld,%lld]", f ? "" : ",", kv.first, kv.second[0], kv.second[1]);
        f = false;
    }
    printf("},\"by_L\":{");
    f = true;
    for (auto& kv : byL) {
        printf("%s\"%d\":[%lld,%lld]", f ? "" : ",", kv.first, kv.second[0], kv.second[1]);
        f = false;
    }
    printf("},\"done\":true}\n");
}

// ---------- n=5 maximal safe sets + lift-sensitivity effect (B254) ----------
// Enumerate all maximal safe sets by DFS. n=5 is small enough.
static void stage_b254n5() {
    Board b0;
    build_square(b0, 5);
    int nq = (int)b0.quads.size();
    std::vector<u64> maximals;

    // DFS over points in order, branch include/exclude, prune unsafe
    std::function<void(u64, int)> dfs = [&](u64 occ, int next) {
        // try to extend
        bool extended = false;
        for (int p = next; p < b0.V; ++p) {
            u64 bit = u64(1) << p;
            if (occ & bit) continue;
            u64 nxt = occ | bit;
            // safe check
            bool ok = true;
            for (u64 q : b0.quads) {
                if ((nxt & q) == q) { ok = false; break; }
            }
            if (!ok) continue;
            extended = true;
            dfs(nxt, p + 1);
        }
        if (!extended) {
            // maximal if no legal add (already true if no extension from next)
            // but points before `next` that were skipped may now be addable? No: we always
            // consider include/exclude in order; if we skipped a point earlier it stays empty.
            // Need: no empty point can be added. Check all empty points.
            bool can_add = false;
            for (int p = 0; p < b0.V; ++p) {
                u64 bit = u64(1) << p;
                if (occ & bit) continue;
                u64 nxt = occ | bit;
                bool ok = true;
                for (u64 q : b0.quads) {
                    if ((nxt & q) == q) { ok = false; break; }
                }
                if (ok) { can_add = true; break; }
            }
            if (!can_add) maximals.push_back(occ);
        }
    };
    // Better enumeration: only recurse on candidates that keep safety; standard Bron-style
    maximals.clear();
    std::function<void(u64, u64)> enum_max = [&](u64 occ, u64 cand) {
        // cand = still-considerable points (those that can be added keeping safety)
        // recompute legal candidates among cand
        u64 legal = 0;
        u64 tmp = cand;
        while (tmp) {
            int p = __builtin_ctzll(tmp); tmp &= tmp - 1;
            u64 nxt = occ | (u64(1) << p);
            bool ok = true;
            for (u64 q : b0.quads) {
                if ((nxt & q) == q) { ok = false; break; }
            }
            if (ok) legal |= u64(1) << p;
        }
        if (legal == 0) {
            maximals.push_back(occ);
            return;
        }
        while (legal) {
            int p = __builtin_ctzll(legal); legal &= legal - 1;
            u64 bit = u64(1) << p;
            // remaining candidates: those > p to keep order, or simply all still in cand
            u64 remain = 0;
            u64 t2 = cand;
            while (t2) {
                int q = __builtin_ctzll(t2); t2 &= t2 - 1;
                if (q > p) remain |= u64(1) << q;
            }
            enum_max(occ | bit, remain);
        }
    };
    enum_max(0, b0.full);
    // dedupe (shouldn't be needed)
    std::sort(maximals.begin(), maximals.end());
    maximals.erase(std::unique(maximals.begin(), maximals.end()), maximals.end());

    // size histogram
    std::map<int,int> hist;
    int K = 0;
    for (u64 m : maximals) {
        int sz = __builtin_popcountll(m);
        hist[sz]++;
        if (sz > K) K = sz;
    }

    // 1-swap graph on maximals: edge if symmetric difference of 2 points (one out one in)
    // count components among K-sized only? And overall.
    // Also: lift each quad and recount how many maximals remain safe under lifted rules
    // (i.e., maximals that use the lifted quad are now legal too - they become non-maximal
    // or the family changes). Measure |maximal family change| per lift.
    std::vector<char> none(nq, 0);
    // index maximals
    std::unordered_map<u64,int> midx;
    for (size_t i = 0; i < maximals.size(); ++i) midx[maximals[i]] = (int)i;

    auto still_maximal_under_lift = [&](u64 occ, int qi) -> bool {
        // under lifted rules, occ must still be safe (yes if it was) and unextendable
        for (int p = 0; p < b0.V; ++p) {
            if (occ & (u64(1) << p)) continue;
            u64 nxt = occ | (u64(1) << p);
            bool ok = true;
            for (size_t k = 0; k < b0.quads.size(); ++k) {
                if ((int)k == qi) continue;
                if ((nxt & b0.quads[k]) == b0.quads[k]) { ok = false; break; }
            }
            if (ok) return false;
        }
        return true;
    };

    // For each lift, how many of the old maximals stay maximal, and do NEW maximals appear?
    // Full recount per lift is expensive (826 × enum). Instead:
    //  (a) among existing maximals, count those invalidated as maximal (can now be extended)
    //  (b) sample: 20 highest-conic-support lifts get a full re-enum
    std::vector<int> qorder(nq);
    for (int i = 0; i < nq; ++i) qorder[i] = i;
    std::sort(qorder.begin(), qorder.end(), [&](int a, int b) {
        return __builtin_popcountll(b0.conic_support[a]) > __builtin_popcountll(b0.conic_support[b]);
    });

    // cheap: lost_maximals[qi] = number of current maximals that can be extended when qi is lifted
    std::vector<int> lost(nq, 0);
    for (int qi = 0; qi < nq; ++qi) {
        int c = 0;
        for (u64 m : maximals) {
            if (!still_maximal_under_lift(m, qi)) ++c;
        }
        lost[qi] = c;
    }

    // full re-enum for top 8 lifts by lost count (and top 4 by conic support)
    std::vector<int> spotlight;
    std::vector<int> by_lost = qorder;
    std::sort(by_lost.begin(), by_lost.end(), [&](int a, int b) { return lost[a] > lost[b]; });
    for (int i = 0; i < 8 && i < nq; ++i) spotlight.push_back(by_lost[i]);
    for (int i = 0; i < 4 && i < nq; ++i) {
        if (std::find(spotlight.begin(), spotlight.end(), qorder[i]) == spotlight.end())
            spotlight.push_back(qorder[i]);
    }

    printf("{\"stage\":\"b254n5\",\"n\":5,\"nquads\":%d,\"n_maximals\":%d,\"K\":%d,",
           nq, (int)maximals.size(), K);
    printf("\"size_hist\":{");
    bool f = true;
    for (auto& kv : hist) {
        printf("%s\"%d\":%d", f ? "" : ",", kv.first, kv.second);
        f = false;
    }
    printf("},\"lost_maximals_top\":[");
    for (int i = 0; i < 10 && i < nq; ++i) {
        int qi = by_lost[i];
        printf("%s{\"qidx\":%d,\"lost\":%d,\"sup\":%d,\"quad\":",
               i ? "," : "", qi, lost[qi], __builtin_popcountll(b0.conic_support[qi]));
        print_quad(stdout, b0, b0.quads[qi]);
        printf("}");
    }
    printf("],\"spotlight\":{");
    f = true;
    for (int qi : spotlight) {
        // re-enumerate maximals under this lift
        std::vector<u64> mx2;
        std::function<void(u64, u64)> em2 = [&](u64 occ, u64 cand) {
            u64 legal = 0;
            u64 tmp = cand;
            while (tmp) {
                int p = __builtin_ctzll(tmp); tmp &= tmp - 1;
                u64 nxt = occ | (u64(1) << p);
                bool ok = true;
                for (size_t k = 0; k < b0.quads.size(); ++k) {
                    if ((int)k == qi) continue;
                    if ((nxt & b0.quads[k]) == b0.quads[k]) { ok = false; break; }
                }
                if (ok) legal |= u64(1) << p;
            }
            if (legal == 0) { mx2.push_back(occ); return; }
            while (legal) {
                int p = __builtin_ctzll(legal); legal &= legal - 1;
                u64 remain = 0;
                u64 t2 = cand;
                while (t2) {
                    int q = __builtin_ctzll(t2); t2 &= t2 - 1;
                    if (q > p) remain |= u64(1) << q;
                }
                em2(occ | (u64(1) << p), remain);
            }
        };
        mx2.clear();
        em2(0, b0.full);
        std::sort(mx2.begin(), mx2.end());
        mx2.erase(std::unique(mx2.begin(), mx2.end()), mx2.end());
        std::map<int,int> h2; int K2 = 0;
        for (u64 m : mx2) {
            int sz = __builtin_popcountll(m);
            h2[sz]++;
            if (sz > K2) K2 = sz;
        }
        printf("%s\"%d\":{\"n_max\":%d,\"K\":%d,\"lost\":%d,\"hist\":{",
               f ? "" : ",", qi, (int)mx2.size(), K2, lost[qi]);
        bool f2 = true;
        for (auto& kv : h2) {
            printf("%s\"%d\":%d", f2 ? "" : ",", kv.first, kv.second);
            f2 = false;
        }
        printf("}}");
        f = false;
    }
    printf("},\"done\":true}\n");
}

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <stage>\n", argv[0]);
        return 1;
    }
    std::string st = argv[1];
    auto t0 = std::chrono::steady_clock::now();
    if (st == "pairs4sens") stage_pairs4sens();
    else if (st == "singles5sens") stage_singles5sens();
    else if (st == "b261bound") stage_b261bound();
    else if (st == "b263n5") stage_b263n5();
    else if (st == "b254n5") stage_b254n5();
    else {
        fprintf(stderr, "unknown stage %s\n", st.c_str());
        return 1;
    }
    auto t1 = std::chrono::steady_clock::now();
    fprintf(stderr, "stage %s took %.1f s\n", st.c_str(),
            std::chrono::duration<double>(t1 - t0).count());
    return 0;
}
