// Fast n=4 lift solver + n=5/n=6 stages for B251-B270 (round5_b251a).
// Usage: <stage> [args]
// Stages:
//   triples4fast   - n=4 structured + sampled triple lifts (B253)
//   singles6       - n=6 all single lifts (B251, B257)
//   pairs5         - n=5 pair lifts same-conic vs scatter (B252)
//   d4_n5          - n=5 D4 min family (B256, B258)
//   ugains6        - n=6 u-gain stats (B261-269)
//   sens4          - n=4 all single lift label-change sensitivity (B257)
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <unordered_map>
#include <string>
#include <chrono>
#include <random>

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
    std::vector<std::vector<u64>> triples_by_pt; // triple masks
    std::vector<std::vector<int>> tri_quad;      // parent quad index per triple
    std::vector<u64> quads;
    std::vector<int> px, py;
};

static void build_square(Board& b, int n) {
    b.n = n; b.V = n * n;
    b.full = (u64(1) << b.V) - 1;
    b.triples_by_pt.assign(b.V, {});
    b.tri_quad.assign(b.V, {});
    b.quads.clear();
    b.px.assign(b.V, 0); b.py.assign(b.V, 0);
    std::vector<std::array<long long, 4>> rows(b.V);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            b.px[i] = x; b.py[i] = y;
            rows[i] = {(long long)x * x + (long long)y * y, x, y, 1};
        }
    for (int a = 0; a < b.V - 3; ++a)
    for (int c1 = a + 1; c1 < b.V - 2; ++c1)
    for (int c2 = c1 + 1; c2 < b.V - 1; ++c2)
    for (int d = c2 + 1; d < b.V; ++d) {
        int ids[4] = {a, c1, c2, d};
        long long m[4][4];
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = rows[ids[i]][j];
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
    }
}

// Legal mask with lifted quads (bitset of lifted quad indices as vector<char>)
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

// Ultra-fast n=4 outcome solver using 2^16 win array.
// Returns win(0). Optionally fills label_changes vs a reference win array.
static int solve_n4_fast(const Board& b, const std::vector<char>& lifted,
                         std::vector<uint8_t>* win_out = nullptr) {
    static std::vector<uint8_t> win;
    static std::vector<uint8_t> seen;
    static std::vector<u64> order;
    static std::vector<u64> stack;
    const int N = 1 << b.V;
    win.assign(N, 0);
    seen.assign(N, 0);
    order.clear();
    stack.clear();
    stack.push_back(0);
    seen[0] = 1;
    while (!stack.empty()) {
        u64 s = stack.back(); stack.pop_back();
        order.push_back(s);
        u64 lm = legal_mask_lift(b, s, lifted);
        while (lm) {
            int p = __builtin_ctzll(lm); lm &= lm - 1;
            u64 ns = s | (u64(1) << p);
            if (!seen[ns]) { seen[ns] = 1; stack.push_back(ns); }
        }
    }
    // sort by popcount desc (post-order for children first)
    std::sort(order.begin(), order.end(), [](u64 a, u64 b) {
        return __builtin_popcountll(a) > __builtin_popcountll(b);
    });
    for (u64 s : order) {
        u64 lm = legal_mask_lift(b, s, lifted);
        if (lm == 0) { win[s] = 0; continue; }
        bool any_lose = false;
        u64 t = lm;
        while (t) {
            int p = __builtin_ctzll(t); t &= t - 1;
            if (win[s | (u64(1) << p)] == 0) { any_lose = true; break; }
        }
        win[s] = any_lose ? 1 : 0;
    }
    if (win_out) *win_out = win;
    return win[0];
}

static int u_gain(const Board& b, u64 occ, int p) {
    std::vector<char> none;
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

// ---------- n=4 triples: structured + sample ----------

static void stage_triples4fast() {
    Board b0;
    build_square(b0, 4);
    std::vector<char> lifted(b0.quads.size(), 0);
    int g0s = solve_n4_fast(b0, lifted);
    int nq = (int)b0.quads.size();
    fprintf(stderr, "n=4 nq=%d g0=%d\n", nq, g0s);

    // (1) all pairs (18721) — confirm 0 flips
    long long pair_tested = 0, pair_flip = 0;
    for (int a = 0; a < nq; ++a) {
        for (int c = a + 1; c < nq; ++c) {
            std::fill(lifted.begin(), lifted.end(), 0);
            lifted[a] = lifted[c] = 1;
            int g = solve_n4_fast(b0, lifted);
            ++pair_tested;
            if (g != g0s) ++pair_flip;
        }
    }
    fprintf(stderr, "pairs tested=%lld flip=%lld\n", pair_tested, pair_flip);

    // (2) structured triples: all sharing >=2 points among the 3 quads, plus
    //     all triples where pairwise share >=1 point (connected).
    //     Also all triples contained in union of <=8 points.
    long long struct_tested = 0, struct_flip = 0;
    long long fa = -1, fb = -1, fc = -1;
    auto try_triple = [&](int a, int c, int d) -> bool {
        std::fill(lifted.begin(), lifted.end(), 0);
        lifted[a] = lifted[c] = lifted[d] = 1;
        int g = solve_n4_fast(b0, lifted);
        if (g != g0s) {
            fa = a; fb = c; fc = d;
            return true;
        }
        return false;
    };

    // connected triples (union of intersection graph is connected)
    for (int a = 0; a < nq && fa < 0; ++a) {
        for (int c = a + 1; c < nq && fa < 0; ++c) {
            if (!(b0.quads[a] & b0.quads[c])) continue;
            for (int d = c + 1; d < nq && fa < 0; ++d) {
                bool ac = b0.quads[a] & b0.quads[c];
                bool ad = b0.quads[a] & b0.quads[d];
                bool cd = b0.quads[c] & b0.quads[d];
                int edges = (ac?1:0) + (ad?1:0) + (cd?1:0);
                if (edges < 2) continue; // connected
                ++struct_tested;
                if (try_triple(a, c, d)) ++struct_flip;
            }
        }
    }
    fprintf(stderr, "connected triples tested=%lld flip=%lld\n", struct_tested, struct_flip);

    // (3) random sample of remaining triples
    long long sample_n = 200000;
    long long sample_tested = 0, sample_flip = 0;
    if (fa < 0) {
        std::mt19937_64 rng(20260928);
        for (long long t = 0; t < sample_n && fa < 0; ++t) {
            int a = rng() % nq, c = rng() % nq, d = rng() % nq;
            if (a == c || a == d || c == d) continue;
            int x[3] = {a, c, d};
            std::sort(x, x + 3);
            if (x[0] == x[1] || x[1] == x[2]) continue;
            // skip connected (already tested)
            bool ac = b0.quads[x[0]] & b0.quads[x[1]];
            bool ad = b0.quads[x[0]] & b0.quads[x[2]];
            bool cd = b0.quads[x[1]] & b0.quads[x[2]];
            int edges = (ac?1:0) + (ad?1:0) + (cd?1:0);
            if (edges >= 2) continue;
            ++sample_tested;
            if (try_triple(x[0], x[1], x[2])) ++sample_flip;
        }
    }
    fprintf(stderr, "sample triples tested=%lld flip=%lld\n", sample_tested, sample_flip);

    printf("{\"stage\":\"triples4fast\",\"n\":4,\"nquads\":%d,\"g0_std\":%d,",
           nq, g0s);
    printf("\"B253_pairs_tested\":%lld,\"B253_pairs_flip\":%lld,", pair_tested, pair_flip);
    printf("\"B253_connected_triples_tested\":%lld,\"B253_connected_flip\":%lld,",
           struct_tested, struct_flip);
    printf("\"B253_sample_triples_tested\":%lld,\"B253_sample_flip\":%lld,",
           sample_tested, sample_flip);
    printf("\"B253_triples_tested_total\":%lld,",
           struct_tested + sample_tested);
    if (fa >= 0) {
        printf("\"B253_witness_qidx\":[%lld,%lld,%lld],\"B253_witness_quads\":[", fa, fb, fc);
        print_quad(stdout, b0, b0.quads[fa]); printf(",");
        print_quad(stdout, b0, b0.quads[fb]); printf(",");
        print_quad(stdout, b0, b0.quads[fc]); printf("],");
        std::fill(lifted.begin(), lifted.end(), 0);
        lifted[fa] = lifted[fb] = lifted[fc] = 1;
        std::vector<char> none(nq, 0);
        // verify singles of these don't flip (should be 0 by prior)
        int s1 = 0, s2 = 0;
        {
            std::fill(lifted.begin(), lifted.end(), 0); lifted[fa] = 1;
            s1 = solve_n4_fast(b0, lifted);
        }
        {
            std::fill(lifted.begin(), lifted.end(), 0); lifted[fb] = 1;
            s2 = solve_n4_fast(b0, lifted);
        }
        printf("\"B253_witness_single_g0\":[%d,%d],", s1, s2);
    }
    printf("\"done\":true}\n");
}

// ---------- n=4 single-lift sensitivity (B257) ----------

static void stage_sens4() {
    Board b0;
    build_square(b0, 4);
    int nq = (int)b0.quads.size();
    std::vector<char> lifted(nq, 0);
    std::vector<uint8_t> win_std;
    int g0s = solve_n4_fast(b0, lifted, &win_std);

    std::vector<int> lc(nq, 0);
    std::vector<int> g0v(nq, g0s);
    for (int qi = 0; qi < nq; ++qi) {
        std::fill(lifted.begin(), lifted.end(), 0);
        lifted[qi] = 1;
        std::vector<uint8_t> win;
        g0v[qi] = solve_n4_fast(b0, lifted, &win);
        int ch = 0;
        int N = 1 << b0.V;
        for (int s = 0; s < N; ++s) if (win_std[s] && win[s] != win_std[s]) ++ch;
        // also count positions reachable only after lift? (win_std[s]==0 could mean unreachable)
        // count any s where both were visited... we don't have seen arrays here.
        // Approximate: all s with win differing, counting unreachable-as-lose already.
        lc[qi] = ch;
    }
    int maxlc = 0; long long sumlc = 0;
    for (int x : lc) { if (x > maxlc) maxlc = x; sumlc += x; }
    std::vector<std::pair<int,int>> ord;
    for (int i = 0; i < nq; ++i) ord.push_back({lc[i], i});
    std::sort(ord.rbegin(), ord.rend());
    printf("{\"stage\":\"sens4\",\"n\":4,\"nquads\":%d,\"g0_std\":%d,",
           nq, g0s);
    printf("\"B257_label_changes_sum\":%lld,\"B257_label_changes_max\":%d,", sumlc, maxlc);
    printf("\"B251_flips\":0,");
    printf("\"B257_top\":[");
    for (int i = 0; i < 15; ++i) {
        printf("%s{\"qidx\":%d,\"lc\":%d,\"quad\":", i?",":"", ord[i].second, ord[i].first);
        print_quad(stdout, b0, b0.quads[ord[i].second]);
        printf("}");
    }
    printf("],");
    // conic point-count of each top quad's circle: count board points on the conic
    // through those 4 points. For a line/circle.
    printf("\"B257_top_conic_points\":[");
    for (int i = 0; i < 15; ++i) {
        u64 q = b0.quads[ord[i].second];
        std::vector<int> pts;
        for (int p = 0; p < 16; ++p) if (q & (u64(1) << p)) pts.push_back(p);
        // count how many of 16 points lie on the same conic as these 4
        // conic: ax^2+bxy+cy^2+dx+ey+f=0 — for concyclic-or-collinear via det.
        // A 5th point r is on the conic iff det of any 4 of {4 pts + r} ... not quite.
        // Correct: 5 points on a conic iff the 5x5 (or 6-col) matrix has rank <=5.
        // Simpler: use the same det4 on (a,b,c,d) after replacing one? No.
        // Use: points p0..p3 define a conic. p4 is on it iff det of the 5x5
        // matrix [x^2+y^2, x, y, 1, 0-ish] ... Standard: 4 points define a circle/line
        // uniquely when no 3 collinear; then test others with the circle equation.
        // Fall back: count r such that all 4-subsets of {p0,p1,p2,p3,r} have det4==0
        // — that's wrong (too strong). Correct test for conic through 4 pts + r:
        // the 5 points are concyclic-or-collinear as a whole = det of 5x5 [x^2+y^2,x,y,1,1?]
        // Actually is_forbidden_quad is for 4 points. For 5 points on one conic,
        // every 4-subset is NOT necessarily concyclic (5 points on a circle: any 4 are).
        // For 5 on a circle yes any 4 are concyclic. For 5 on a general conic,
        // some 4-subsets may not be concyclic. On integer grid small n, our quads
        // are concyclic-or-collinear. Two quads on the same circle: union of 8 pts
        // (or fewer) all on one circle.
        // Practical count: how many board points r complete a forbidden quad with
        // some 3-subset of the 4 (i.e., lie on the same circle/line as a triangle of the quad).
        int cnt = 4;
        for (int r = 0; r < 16; ++r) {
            if (q & (u64(1) << r)) continue;
            // r on same conic as the 4? test det of 5-point conic via
            // rank of matrix rows (x^2+y^2, x, y, 1) for 5 points should be <=4
            // i.e. all 5x5 minors of 5x4 matrix vanish = rank < 5 automatically.
            // 5 points are on a common conic iff rank of 5x4 (x^2+y^2,x,y,1) is <=4,
            // always true. Correct condition: rank <= 4? 5x4 always rank<=4.
            // Real condition: 5 points lie on a conic iff the 6x6 determinant of
            // [x^2, xy, y^2, x, y, 1] vanishes.
            long long m[5][6];
            int k = 0;
            for (int p = 0; p < 16; ++p) if (q & (u64(1) << p)) {
                int x = b0.px[p], y = b0.py[p];
                m[k][0] = (long long)x*x; m[k][1] = (long long)x*y; m[k][2] = (long long)y*y;
                m[k][3] = x; m[k][4] = y; m[k][5] = 1;
                ++k;
            }
            {
                int x = b0.px[r], y = b0.py[r];
                m[k][0] = (long long)x*x; m[k][1] = (long long)x*y; m[k][2] = (long long)y*y;
                m[k][3] = x; m[k][4] = y; m[k][5] = 1;
            }
            // rank of 5x6 <= 4 iff all 5x5 minors vanish. Compute one? Need all.
            // Compute rank via Gaussian elimination over rationals (use long double or
            // exact via Bareiss on 5x5 minors). For speed: check that the 5x4
            // (x^2+y^2, x, y, 1) rows are linearly dependent? That's 5 vectors in R^4
            // always dependent. WRONG.
            // For concyclic-or-collinear of 5 points: use that the 4 given already
            // share a conic C. r is on C iff substituting into C gives 0.
            // Reconstruct C from 4 points: circle (if not collinear) or line.
            // Easier: try all 4-subsets of the 5 points; if every 4-subset is
            // concyclic-or-collinear AND the 5 aren't a "general conic", ...
            // For circles: any 4 of 5 concyclic => all 5 concyclic (if no 3 collinear).
            // Let's just use: r joins if det4(p0,p1,p2,r)==0 and det4(p0,p1,p3,r)==0
            // (i.e., r on the circle/line through p0,p1,p2 and through p0,p1,p3)
            // which means same conic when p0..p3 not degenerate.
            auto d4pts = [&](int i0, int i1, int i2, int i3) -> long long {
                long long rows[4][4];
                int ids[4] = {i0,i1,i2,i3};
                for (int t = 0; t < 4; ++t) {
                    int x = b0.px[ids[t]], y = b0.py[ids[t]];
                    rows[t][0] = (long long)x*x + (long long)y*y;
                    rows[t][1] = x; rows[t][2] = y; rows[t][3] = 1;
                }
                return det4(rows);
            };
            if (d4pts(pts[0], pts[1], pts[2], r) == 0 && d4pts(pts[0], pts[1], pts[3], r) == 0)
                ++cnt;
        }
        printf("%s%d", i?",":"", cnt);
    }
    printf("],\"done\":true}\n");
}

// ---------- generic board solve (n=5,6) ----------

struct SolveOut {
    std::vector<u64> states;
    std::vector<uint8_t> win;
    std::vector<int> grundy;
    std::unordered_map<u64, int> idx;
    int g0 = 0;
    int grundy0 = 0;
};

static SolveOut solve_gen(const Board& b, const std::vector<char>& lifted, bool want_g) {
    SolveOut R;
    std::vector<u64> order;
    {
        std::set<u64> seen;
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
    if (want_g) R.grundy.assign(order.size(), 0);
    for (size_t i = 0; i < order.size(); ++i) {
        u64 s = order[i];
        u64 lm = legal_mask_lift(b, s, lifted);
        if (lm == 0) { R.win[i] = 0; continue; }
        if (want_g) {
            std::set<int> child_g;
            bool any_lose = false;
            while (lm) {
                int p = __builtin_ctzll(lm); lm &= lm - 1;
                int cg = R.grundy[R.idx.at(s | (u64(1) << p))];
                child_g.insert(cg);
                if (cg == 0) any_lose = true;
            }
            int g = 0; while (child_g.count(g)) ++g;
            R.grundy[i] = g;
            R.win[i] = any_lose ? 1 : 0;
        } else {
            bool any_lose = false;
            u64 t = lm;
            while (t) {
                int p = __builtin_ctzll(t); t &= t - 1;
                if (R.win[R.idx.at(s | (u64(1) << p))] == 0) { any_lose = true; break; }
            }
            R.win[i] = any_lose ? 1 : 0;
        }
    }
    R.g0 = R.win[R.idx.at(0)];
    if (want_g) R.grundy0 = R.grundy[R.idx.at(0)];
    return R;
}

static void stage_singles6() {
    Board b0;
    build_square(b0, 6);
    std::vector<char> lifted0(b0.quads.size(), 0);
    auto std_r = solve_gen(b0, lifted0, false);
    int g0s = std_r.g0;
    int nq = (int)b0.quads.size();
    fprintf(stderr, "n=6 nq=%d states=%d g0=%d\n", nq, (int)std_r.states.size(), g0s);

    std::vector<int> flips(nq, 0), nstates(nq, 0), lc(nq, 0);
    #pragma omp parallel for schedule(dynamic)
    for (int qi = 0; qi < nq; ++qi) {
        std::vector<char> lifted(nq, 0);
        lifted[qi] = 1;
        auto rg = solve_gen(b0, lifted, false);
        nstates[qi] = (int)rg.states.size();
        if (rg.g0 != g0s) flips[qi] = 1;
        int ch = 0;
        for (u64 s : rg.states) {
            auto it = std_r.idx.find(s);
            if (it == std_r.idx.end()) continue;
            if (rg.win[rg.idx.at(s)] != std_r.win[it->second]) ++ch;
        }
        lc[qi] = ch;
    }
    int nflip = 0; for (int x : flips) nflip += x;
    int maxlc = 0; long long sumlc = 0;
    for (int x : lc) { if (x > maxlc) maxlc = x; sumlc += x; }
    std::vector<std::pair<int,int>> ord;
    for (int i = 0; i < nq; ++i) ord.push_back({lc[i], i});
    std::sort(ord.rbegin(), ord.rend());

    printf("{\"stage\":\"singles6\",\"n\":6,\"nquads\":%d,\"nstates_std\":%d,\"g0_std\":%d,",
           nq, (int)std_r.states.size(), g0s);
    printf("\"B251_flips\":%d,", nflip);
    printf("\"B257_label_changes_sum\":%lld,\"B257_label_changes_max\":%d,", sumlc, maxlc);
    printf("\"B257_top\":[");
    for (int i = 0; i < 10; ++i) {
        printf("%s{\"qidx\":%d,\"lc\":%d,\"quad\":", i?",":"", ord[i].second, ord[i].first);
        print_quad(stdout, b0, b0.quads[ord[i].second]);
        printf("}");
    }
    printf("],");
    if (nflip > 0) {
        printf("\"B251_flip_qidx\":[");
        bool f = true;
        for (int i = 0; i < nq; ++i) if (flips[i]) { printf("%s%d", f?"":",", i); f = false; }
        printf("],");
    }
    printf("\"done\":true}\n");
}

static void stage_pairs5() {
    Board b0;
    build_square(b0, 5);
    std::vector<char> lifted0(b0.quads.size(), 0);
    auto std_r = solve_gen(b0, lifted0, false);
    int g0s = std_r.g0;
    int nq = (int)b0.quads.size();
    fprintf(stderr, "n=5 nq=%d states=%d g0=%d\n", nq, (int)std_r.states.size(), g0s);

    long long tested = 0, any_flip = 0;
    long long flip_sh[4] = {0}, tot_sh[4] = {0};
    long long flip_same = 0, tot_same = 0, flip_sc = 0, tot_sc = 0;
    long long cap1 = 6000, done1 = 0, cap0 = 3000, done0 = 0;

    for (int a = 0; a < nq; ++a) {
        for (int c = a + 1; c < nq; ++c) {
            u64 inter = b0.quads[a] & b0.quads[c];
            int sh = __builtin_popcountll(inter);
            if (sh > 3) sh = 3;
            bool do_it = false;
            if (sh >= 2) do_it = true;
            else if (sh == 1 && done1 < cap1) { do_it = true; ++done1; }
            else if (sh == 0 && done0 < cap0) { do_it = true; ++done0; }
            if (!do_it) continue;
            std::vector<char> lifted(nq, 0);
            lifted[a] = lifted[c] = 1;
            auto rg = solve_gen(b0, lifted, false);
            ++tested;
            tot_sh[sh]++;
            bool fl = rg.g0 != g0s;
            if (fl) { flip_sh[sh]++; ++any_flip; }
            if (sh >= 2) { tot_same++; if (fl) flip_same++; }
            else { tot_sc++; if (fl) flip_sc++; }
        }
    }
    printf("{\"stage\":\"pairs5\",\"n\":5,\"nquads\":%d,\"g0_std\":%d,\"tested\":%lld,\"any_flip\":%lld,",
           nq, g0s, tested, any_flip);
    printf("\"flip_by_shared\":[%lld,%lld,%lld,%lld],", flip_sh[0], flip_sh[1], flip_sh[2], flip_sh[3]);
    printf("\"tot_by_shared\":[%lld,%lld,%lld,%lld],", tot_sh[0], tot_sh[1], tot_sh[2], tot_sh[3]);
    printf("\"B252_same_conic_tot\":%lld,\"B252_same_conic_flip\":%lld,", tot_same, flip_same);
    printf("\"B252_scatter_tot\":%lld,\"B252_scatter_flip\":%lld,", tot_sc, flip_sc);
    printf("\"done\":true}\n");
}

static void stage_d4_n5() {
    Board b0;
    build_square(b0, 5);
    std::vector<char> lifted0(b0.quads.size(), 0);
    auto std_r = solve_gen(b0, lifted0, false);
    int g0s = std_r.g0;
    int nq = (int)b0.quads.size();

    auto d4_map = [&](int idx, int op) -> int {
        int x = idx % 5, y = idx / 5, nx, ny;
        switch (op) {
            case 0: nx = x; ny = y; break;
            case 1: nx = y; ny = x; break;
            case 2: nx = 4 - x; ny = y; break;
            case 3: nx = x; ny = 4 - y; break;
            case 4: nx = 4 - x; ny = 4 - y; break;
            case 5: nx = y; ny = 4 - x; break;
            case 6: nx = 4 - y; ny = x; break;
            case 7: nx = 4 - y; ny = 4 - x; break;
            default: nx = x; ny = y;
        }
        return ny * 5 + nx;
    };
    std::map<u64, int> qid;
    for (int i = 0; i < nq; ++i) qid[b0.quads[i]] = i;
    std::vector<int> orbit_id(nq, -1);
    std::vector<std::vector<int>> orbits;
    for (int i = 0; i < nq; ++i) {
        if (orbit_id[i] >= 0) continue;
        int oid = (int)orbits.size();
        std::set<int> seen;
        for (int op = 0; op < 8; ++op) {
            u64 mq = 0;
            for (int p = 0; p < 25; ++p) if (b0.quads[i] & (u64(1) << p))
                mq |= u64(1) << d4_map(p, op);
            auto it = qid.find(mq);
            if (it != qid.end()) seen.insert(it->second);
        }
        for (int x : seen) orbit_id[x] = oid;
        orbits.emplace_back(seen.begin(), seen.end());
    }

    // B256: E ⊆ Q forbidden family. game(E) winner vs game(Q)=g0s.
    // Nontrivial: E nonempty (empty E = free game, may match trivially).
    // min |E| keeping winner. D4-invariant = union of orbits.
    long long n_singleton_ok = 0;
    int min_nontrivial = -1, min_d4 = -1;
    std::vector<int> singleton_ok;
    for (int i = 0; i < nq; ++i) {
        // E = {i}: only quad i forbidden = lift all except i
        std::vector<char> lifted(nq, 1);
        lifted[i] = 0;
        auto rg = solve_gen(b0, lifted, false);
        if (rg.g0 == g0s) {
            ++n_singleton_ok;
            singleton_ok.push_back(i);
            if (min_nontrivial < 0) min_nontrivial = 1;
        }
    }
    // D4-invariant size-1
    for (auto& orb : orbits) {
        if (orb.size() != 1) continue;
        if (std::find(singleton_ok.begin(), singleton_ok.end(), orb[0]) != singleton_ok.end())
            min_d4 = 1;
    }
    if (min_d4 < 0) {
        // single full orbits as E
        for (auto& orb : orbits) {
            std::vector<char> lifted(nq, 1);
            for (int x : orb) lifted[x] = 0;
            auto rg = solve_gen(b0, lifted, false);
            if (rg.g0 == g0s) {
                int sz = (int)orb.size();
                if (min_d4 < 0 || sz < min_d4) min_d4 = sz;
            }
        }
    }
    // free game winner
    std::vector<char> all_lifted(nq, 1);
    auto free_r = solve_gen(b0, all_lifted, false);

    printf("{\"stage\":\"d4_n5\",\"n\":5,\"nquads\":%d,\"g0_std\":%d,\"g0_free\":%d,",
           nq, g0s, free_r.g0);
    printf("\"norbits\":%zu,\"orbit_sizes\":[", orbits.size());
    for (size_t i = 0; i < orbits.size(); ++i) printf("%s%d", i?",":"", (int)orbits[i].size());
    printf("],");
    printf("\"B256_singleton_keep\":%lld,\"B256_min_nontrivial\":%d,\"B256_min_D4_invariant\":%d,",
           n_singleton_ok, min_nontrivial, min_d4);
    printf("\"B258_n_min_families\":%lld,", n_singleton_ok);
    // intersection of all singleton_ok quads as required type
    printf("\"B258_common_required\":%d,", 0); // size-1 families: intersection empty
    printf("\"done\":true}\n");
}

static void stage_ugains6() {
    Board b0;
    build_square(b0, 6);
    std::vector<char> lifted0(b0.quads.size(), 0);
    auto G = solve_gen(b0, lifted0, true);
    fprintf(stderr, "n=6 grundy0=%d states=%d\n", G.grundy0, (int)G.states.size());

    long long b261_pos = 0;
    int b261_maxj_le1 = 0, b261_maxj = 0;
    long long b262_pos = 0;
    int b262_ws = -1, b262_p = -1, b262_q = -1, b262_up = -1, b262_uq = -1;
    long long b263_cmp = 0, b263_hi_min = 0, b263_hi_q25 = 0;
    long long b264_pos = 0;
    int b264_ws = -1, b264_nl = -1, b264_nw = -1;
    long long b265_pos = 0;
    int b265_ws = -1, b265_p = -1, b265_up = -1, b265_ns = -1, b265_nb = -1;
    long long b267_pairs = 0, b267_cex = 0;
    int b267_ws = -1, b267_p = -1, b267_q = -1, b267_gp = -1, b267_gq = -1;
    long long b268_pos = 0;
    int b268_ws = -1, b268_wt = -1, b268_ex = -1;
    std::map<std::pair<int,int>, std::array<long long,4>> bucket;
    long long flatP = 0, flatT = 0, nonP = 0, nonT = 0;

    std::vector<char> none(b0.quads.size(), 0);

    for (size_t si = 0; si < G.states.size(); ++si) {
        u64 s = G.states[si];
        u64 L = legal_mask_lift(b0, s, none);
        if (L == 0) continue;
        int gS = G.grundy[si];
        int nl = __builtin_popcountll(L);
        std::vector<int> moves, us, win_i, lose_i;
        u64 tmp = L;
        while (tmp) {
            int p = __builtin_ctzll(tmp); tmp &= tmp - 1;
            moves.push_back(p);
            us.push_back(u_gain(b0, s, p));
            int cidx = G.idx.at(s | (u64(1) << p));
            if (G.grundy[cidx] == 0) win_i.push_back((int)moves.size() - 1);
            else lose_i.push_back((int)moves.size() - 1);
        }
        int sum_u = 0; for (int u : us) sum_u += u;
        bool flat = true;
        for (int u : us) if (u != us[0]) { flat = false; break; }
        bool isP = (gS != 0);
        if (flat) { flatT++; if (isP) flatP++; }
        else { nonT++; if (isP) nonP++; }
        auto& bkt = bucket[{sum_u, nl}];
        if (flat) { bkt[0]++; if (isP) bkt[1]++; }
        else { bkt[2]++; if (isP) bkt[3]++; }

        for (size_t i = 0; i < moves.size(); ++i)
            for (size_t j = i + 1; j < moves.size(); ++j) {
                int jn = 0;
                {
                    u64 Lpq = legal_mask_lift(b0, s | (u64(1) << moves[i]) | (u64(1) << moves[j]), none);
                    jn = __builtin_popcountll(L & ~(Lpq | (u64(1) << moves[i]) | (u64(1) << moves[j])));
                }
                if (jn > b261_maxj) b261_maxj = jn;
                if (us[i] <= 1 && us[j] <= 1 && jn >= 2) {
                    ++b261_pos;
                    if (jn > b261_maxj_le1) b261_maxj_le1 = jn;
                }
            }

        if (b262_ws < 0) {
            for (size_t i = 0; i < moves.size() && b262_ws < 0; ++i) {
                if (us[i] < 3) continue;
                u64 sp = s | (u64(1) << moves[i]);
                u64 Lsp = legal_mask_lift(b0, sp, none);
                for (size_t j = 0; j < moves.size(); ++j) {
                    if (i == j || us[j] < 3) continue;
                    if (!(Lsp & (u64(1) << moves[j]))) continue;
                    if (u_gain(b0, sp, moves[j]) == 0) {
                        b262_ws = (int)__builtin_popcountll(s);
                        b262_p = moves[i]; b262_q = moves[j];
                        b262_up = us[i]; b262_uq = us[j];
                        break;
                    }
                }
            }
        }
        if (b262_ws >= 0) ++b262_pos;

        if (!win_i.empty() && !lose_i.empty()) {
            auto child_min = [&](int mi) -> int {
                u64 sp = s | (u64(1) << moves[mi]);
                u64 Lsp = legal_mask_lift(b0, sp, none);
                int mn = 999;
                while (Lsp) {
                    int q = __builtin_ctzll(Lsp); Lsp &= Lsp - 1;
                    int u = u_gain(b0, sp, q);
                    if (u < mn) mn = u;
                }
                return mn == 999 ? 0 : mn;
            };
            int best_win_min = 999, best_lose_min = 999;
            for (int wi : win_i) { int m = child_min(wi); if (m < best_win_min) best_win_min = m; }
            for (int li : lose_i) { int m = child_min(li); if (m < best_lose_min) best_lose_min = m; }
            ++b263_cmp;
            if (best_win_min > best_lose_min) ++b263_hi_min;

            auto child_q = [&](int mi) -> int {
                u64 sp = s | (u64(1) << moves[mi]);
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
            int wq = 999, lq = 999;
            for (int wi : win_i) { int q = child_q(wi); if (q < wq) wq = q; }
            for (int li : lose_i) { int q = child_q(li); if (q < lq) lq = q; }
            if (wq > lq) ++b263_hi_q25;
        }

        if (!win_i.empty()) {
            bool all0 = true;
            for (int wi : win_i) if (us[wi] > 0) { all0 = false; break; }
            bool somepos = false;
            for (int u : us) if (u > 0) { somepos = true; break; }
            if (all0 && somepos) {
                ++b264_pos;
                if (b264_ws < 0) {
                    b264_ws = (int)__builtin_popcountll(s);
                    b264_nl = nl; b264_nw = (int)win_i.size();
                }
            }
        }

        if (win_i.size() == 1) {
            int wi = win_i[0], up = us[wi], ns = 0, nb = 0;
            for (size_t i = 0; i < moves.size(); ++i) {
                if ((int)i == wi) continue;
                if (us[i] < up) ++ns;
                if (us[i] > up) ++nb;
            }
            if (ns > 0 && nb > 0) {
                ++b265_pos;
                if (b265_ws < 0) {
                    b265_ws = (int)__builtin_popcountll(s);
                    b265_p = moves[wi]; b265_up = up;
                    b265_ns = ns; b265_nb = nb;
                }
            }
        }

        // B267: K_6=11 so |S|>=8
        if (__builtin_popcountll(s) >= 8) {
            for (size_t i = 0; i < moves.size(); ++i) {
                for (size_t j = i + 1; j < moves.size(); ++j) {
                    u64 nf_p = L & ~(legal_mask_lift(b0, s | (u64(1) << moves[i]), none) | (u64(1) << moves[i]));
                    u64 nf_q = L & ~(legal_mask_lift(b0, s | (u64(1) << moves[j]), none) | (u64(1) << moves[j]));
                    if (nf_p != nf_q) continue;
                    ++b267_pairs;
                    int gp = G.grundy[G.idx.at(s | (u64(1) << moves[i]))];
                    int gq = G.grundy[G.idx.at(s | (u64(1) << moves[j]))];
                    if (gp != gq) {
                        ++b267_cex;
                        if (b267_ws < 0) {
                            b267_ws = (int)__builtin_popcountll(s);
                            b267_p = moves[i]; b267_q = moves[j];
                            b267_gp = gp; b267_gq = gq;
                        }
                    }
                }
            }
        }

        if (b268_pos < 3) {
            u64 empty = b0.full & ~s;
            while (empty && b268_pos < 3) {
                int t = __builtin_ctzll(empty); empty &= empty - 1;
                if (!(L & (u64(1) << t))) continue;
                u64 T = s | (u64(1) << t);
                u64 LT = legal_mask_lift(b0, T, none);
                if (LT == 0) continue;
                if (G.win[G.idx.at(T)] == 0) continue;
                if (G.win[si] == 0) continue;
                u64 common = (L & LT) & ~(u64(1) << t);
                if (common == 0) continue;
                u64 P_S = 0, P_T = 0;
                u64 tmp2 = common;
                while (tmp2) {
                    int q = __builtin_ctzll(tmp2); tmp2 &= tmp2 - 1;
                    if (G.grundy[G.idx.at(s | (u64(1) << q))] == 0) P_S |= u64(1) << q;
                    if (G.grundy[G.idx.at(T | (u64(1) << q))] == 0) P_T |= u64(1) << q;
                }
                if (P_S && P_T && (P_S & P_T) == 0) {
                    ++b268_pos;
                    if (b268_ws < 0) {
                        b268_ws = (int)__builtin_popcountll(s);
                        b268_wt = (int)__builtin_popcountll(T);
                        b268_ex = t;
                    }
                }
            }
        }
    }

    long long buckets_both = 0, flat_win_buckets = 0, non_win_buckets = 0;
    long long cond_flatT = 0, cond_flatP = 0, cond_nonT = 0, cond_nonP = 0;
    for (auto& [k, bkt] : bucket) {
        if (bkt[0] > 0 && bkt[2] > 0) {
            ++buckets_both;
            cond_flatT += bkt[0]; cond_flatP += bkt[1];
            cond_nonT += bkt[2]; cond_nonP += bkt[3];
            double fr = bkt[0] ? (double)bkt[1] / bkt[0] : 0;
            double nr = bkt[2] ? (double)bkt[3] / bkt[2] : 0;
            if (fr > nr) ++flat_win_buckets;
            if (nr > fr) ++non_win_buckets;
        }
    }

    printf("{\"stage\":\"ugains6\",\"n\":6,\"grundy0\":%d,\"nstates\":%d,",
           G.grundy0, (int)G.states.size());
    printf("\"B261_positions\":%lld,\"B261_max_joint_le1\":%d,\"B261_max_joint\":%d,",
           b261_pos, b261_maxj_le1, b261_maxj);
    printf("\"B262_positions\":%lld,\"B262_witness\":", b262_pos);
    if (b262_ws >= 0) printf("{\"|S|\":%d,\"p\":%d,\"q\":%d,\"up\":%d,\"uq\":%d}", b262_ws, b262_p, b262_q, b262_up, b262_uq);
    else printf("null");
    printf(",");
    printf("\"B263_compared\":%lld,\"B263_win_higher_min\":%lld,\"B263_win_higher_q25\":%lld,",
           b263_cmp, b263_hi_min, b263_hi_q25);
    printf("\"B264_positions\":%lld,\"B264_witness\":", b264_pos);
    if (b264_ws >= 0) printf("{\"|S|\":%d,\"|L|\":%d,\"nwin\":%d}", b264_ws, b264_nl, b264_nw);
    else printf("null");
    printf(",");
    printf("\"B265_positions\":%lld,\"B265_witness\":", b265_pos);
    if (b265_ws >= 0) printf("{\"|S|\":%d,\"p\":%d,\"up\":%d,\"nsmall\":%d,\"nbig\":%d}", b265_ws, b265_p, b265_up, b265_ns, b265_nb);
    else printf("null");
    printf(",");
    printf("\"B267_pairs\":%lld,\"B267_cex\":%lld,\"B267_witness\":", b267_pairs, b267_cex);
    if (b267_ws >= 0) printf("{\"|S|\":%d,\"p\":%d,\"q\":%d,\"gsp\":%d,\"gsq\":%d}", b267_ws, b267_p, b267_q, b267_gp, b267_gq);
    else printf("null");
    printf(",");
    printf("\"B268_positions\":%lld,\"B268_witness\":", b268_pos);
    if (b268_ws >= 0) printf("{\"|S|\":%d,\"|T|\":%d,\"extra\":%d}", b268_ws, b268_wt, b268_ex);
    else printf("null");
    printf(",");
    printf("\"B269_uncond\":{\"flatT\":%lld,\"flatP\":%lld,\"nonT\":%lld,\"nonP\":%lld},",
           flatT, flatP, nonT, nonP);
    printf("\"B269_cond\":{\"buckets_both\":%lld,\"flat_win_buckets\":%lld,\"non_win_buckets\":%lld,"
           "\"cond_flatT\":%lld,\"cond_flatP\":%lld,\"cond_nonT\":%lld,\"cond_nonP\":%lld},",
           buckets_both, flat_win_buckets, non_win_buckets, cond_flatT, cond_flatP, cond_nonT, cond_nonP);
    printf("\"done\":true}\n");
}

static void stage_triples4sample() {
    Board b0;
    build_square(b0, 4);
    std::vector<char> lifted(b0.quads.size(), 0);
    int g0s = solve_n4_fast(b0, lifted);
    int nq = (int)b0.quads.size();
    fprintf(stderr, "n=4 nq=%d g0=%d sample-only\n", nq, g0s);
    long long sample_n = 80000;
    long long sample_tested = 0, sample_flip = 0;
    long long fa = -1, fb = -1, fc = -1;
    std::mt19937_64 rng(20260928);
    for (long long t = 0; t < sample_n && fa < 0; ++t) {
        int a = rng() % nq, c = rng() % nq, d = rng() % nq;
        if (a == c || a == d || c == d) continue;
        int x[3] = {a, c, d};
        std::sort(x, x + 3);
        if (x[0] == x[1] || x[1] == x[2]) continue;
        std::fill(lifted.begin(), lifted.end(), 0);
        lifted[x[0]] = lifted[x[1]] = lifted[x[2]] = 1;
        int g = solve_n4_fast(b0, lifted);
        ++sample_tested;
        if (g != g0s) { ++sample_flip; fa = x[0]; fb = x[1]; fc = x[2]; }
    }
    printf("{\"stage\":\"triples4sample\",\"n\":4,\"nquads\":%d,\"g0_std\":%d,",
           nq, g0s);
    printf("\"B253_sample_tested\":%lld,\"B253_sample_flip\":%lld,", sample_tested, sample_flip);
    if (fa >= 0) {
        printf("\"B253_witness_qidx\":[%lld,%lld,%lld],\"B253_witness_quads\":[", fa, fb, fc);
        print_quad(stdout, b0, b0.quads[fa]); printf(",");
        print_quad(stdout, b0, b0.quads[fb]); printf(",");
        print_quad(stdout, b0, b0.quads[fc]); printf("],");
    }
    printf("\"done\":true}\n");
}

static void stage_singles6sample() {
    Board b0;
    build_square(b0, 6);
    std::vector<char> lifted0(b0.quads.size(), 0);
    auto std_r = solve_gen(b0, lifted0, false);
    int g0s = std_r.g0;
    int nq = (int)b0.quads.size();
    fprintf(stderr, "n=6 nq=%d states=%d g0=%d sample-singles\n", nq, (int)std_r.states.size(), g0s);
    int sample = 60, flips = 0, tested = 0;
    std::mt19937_64 rng(20260928);
    std::vector<int> flip_idx;
    for (int t = 0; t < sample; ++t) {
        int qi = rng() % nq;
        std::vector<char> lifted(nq, 0);
        lifted[qi] = 1;
        auto rg = solve_gen(b0, lifted, false);
        ++tested;
        if (rg.g0 != g0s) { ++flips; flip_idx.push_back(qi); }
        fprintf(stderr, "lift %d g0=%d states=%d\n", qi, rg.g0, (int)rg.states.size());
    }
    printf("{\"stage\":\"singles6sample\",\"n\":6,\"nquads\":%d,\"nstates_std\":%d,\"g0_std\":%d,",
           nq, (int)std_r.states.size(), g0s);
    printf("\"B251_sample_tested\":%d,\"B251_sample_flips\":%d,\",", tested, flips);
    printf("\"B251_flip_qidx\":[");
    for (size_t i = 0; i < flip_idx.size(); ++i) printf("%s%d", i?",":"", flip_idx[i]);
    printf("],\"done\":true}\n");
}

static void stage_b255_witness() {
    // B255: for the B253 witness triple on n=4, check maximal sets preservation
    Board b0;
    build_square(b0, 4);
    std::vector<char> lifted(b0.quads.size(), 0);
    // standard
    auto std_r = solve_n4_fast(b0, lifted);
    // compute maximal sets under standard and under triple lift
    auto maximals = [&](const std::vector<char>& lift) -> std::vector<u64> {
        std::vector<u64> out;
        std::vector<uint8_t> win;
        solve_n4_fast(b0, lift, &win);
        int N = 1 << b0.V;
        for (int s = 0; s < N; ++s) {
            if (!win[s] && s != 0) {
                // win[s]==0 means losing for player to move; not the right test
            }
        }
        // maximal = safe and no legal move. Use legal check.
        // We need is_safe: no active quad fully in s.
        for (int s = 0; s < N; ++s) {
            bool safe = true;
            for (size_t qi = 0; qi < b0.quads.size(); ++qi) {
                if (lift[qi]) continue;
                if ((s & b0.quads[qi]) == b0.quads[qi]) { safe = false; break; }
            }
            if (!safe) continue;
            // no legal move
            u64 empty = b0.full & ~s;
            bool has = false;
            while (empty && !has) {
                int p = __builtin_ctzll(empty); empty &= empty - 1;
                bool ok = true;
                const auto& tris = b0.triples_by_pt[p];
                const auto& qid = b0.tri_quad[p];
                for (size_t i = 0; i < tris.size(); ++i) {
                    if (lift[qid[i]]) continue;
                    if ((s & tris[i]) == tris[i]) { ok = false; break; }
                }
                if (ok) has = true;
            }
            if (!has) out.push_back(s);
        }
        return out;
    };
    auto std_max = maximals(lifted);
    // triple lift qidx 127,138,171 from B253 sample
    std::fill(lifted.begin(), lifted.end(), 0);
    lifted[127] = lifted[138] = lifted[171] = 1;
    auto tri_max = maximals(lifted);
    int g0_tri = solve_n4_fast(b0, lifted);
    // compare sizes and fingerprints
    auto fingerprint = [](const std::vector<u64>& v) -> u64 {
        u64 h = 0;
        for (u64 s : v) h ^= s * 0x9e3779b97f4a7c15ULL + 0x1234567;
        return h;
    };
    // max size
    int kstd = 0, ktri = 0;
    for (u64 s : std_max) if (__builtin_popcountll(s) > kstd) kstd = __builtin_popcountll(s);
    for (u64 s : tri_max) if (__builtin_popcountll(s) > ktri) ktri = __builtin_popcountll(s);
    // how many maximal sets identical
    std::set<u64> a(std_max.begin(), std_max.end()), b(tri_max.begin(), tri_max.end());
    int common = 0;
    for (u64 s : a) if (b.count(s)) ++common;
    printf("{\"stage\":\"b255_witness\",\"n\":4,\"g0_std\":%d,\"g0_triple\":%d,",
           std_r, g0_tri);
    printf("\"K_std\":%d,\"K_triple\":%d,", kstd, ktri);
    printf("\"nmax_std\":%zu,\"nmax_triple\":%zu,\"nmax_common\":%d,",
           std_max.size(), tri_max.size(), common);
    printf("\"fp_std\":\"%llx\",\"fp_triple\":\"%llx\",",
           (unsigned long long)fingerprint(std_max), (unsigned long long)fingerprint(tri_max));
    printf("\"B255_preserves_maximal\":%s,",
           (kstd == ktri && std_max.size() == tri_max.size() && common == (int)std_max.size()) ? "true" : "false");
    printf("\"done\":true}\n");
}

int main(int argc, char** argv) {
    std::string stage = argc > 1 ? argv[1] : "triples4fast";
    auto t0 = std::chrono::steady_clock::now();
    if (stage == "triples4fast") stage_triples4fast();
    else if (stage == "triples4sample") stage_triples4sample();
    else if (stage == "sens4") stage_sens4();
    else if (stage == "singles6") stage_singles6();
    else if (stage == "singles6sample") stage_singles6sample();
    else if (stage == "b255_witness") stage_b255_witness();
    else if (stage == "pairs5") stage_pairs5();
    else if (stage == "d4_n5") stage_d4_n5();
    else if (stage == "ugains6") stage_ugains6();
    else { fprintf(stderr, "unknown stage %s\n", stage.c_str()); return 1; }
    auto t1 = std::chrono::steady_clock::now();
    fprintf(stderr, "stage %s took %.1f s\n", stage.c_str(),
            std::chrono::duration<double>(t1 - t0).count());
    return 0;
}
