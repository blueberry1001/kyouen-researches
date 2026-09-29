// B267-focused + optimized n=5 singles.
// B267 interpretation: K_n - |S| <= 3  (endgame by max-safe-size).
// Also B266 joint histogram.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <chrono>
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
    std::vector<u64> quads;
    std::vector<int> px, py;
};

static void build_square(Board& b, int n) {
    b.n = n; b.V = n * n;
    b.full = (u64(1) << b.V) - 1;
    b.triples_by_pt.assign(b.V, {});
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
        b.quads.push_back(q);
        for (int t = 0; t < 4; ++t) {
            u64 o = 0;
            for (int s = 0; s < 4; ++s) if (s != t) o |= u64(1) << ids[s];
            b.triples_by_pt[ids[t]].push_back(o);
        }
    }
}

static inline u64 legal_mask(const Board& b, u64 occ) {
    u64 out = 0;
    u64 empty = b.full & ~occ;
    while (empty) {
        int p = __builtin_ctzll(empty);
        empty &= empty - 1;
        bool ok = true;
        for (u64 t : b.triples_by_pt[p]) {
            if ((occ & t) == t) { ok = false; break; }
        }
        if (ok) out |= u64(1) << p;
    }
    return out;
}

struct GameResult {
    std::map<u64, int> grundy;
    int g0 = 0;
    std::vector<u64> states;
};

static GameResult solve_game(const Board& b, bool grundy = true) {
    GameResult R;
    std::vector<u64> order;
    std::set<u64> seen;
    std::vector<u64> stack = {0};
    seen.insert(0);
    while (!stack.empty()) {
        u64 s = stack.back(); stack.pop_back();
        order.push_back(s);
        u64 lm = legal_mask(b, s);
        while (lm) {
            int p = __builtin_ctzll(lm);
            lm &= lm - 1;
            u64 ns = s | (u64(1) << p);
            if (!seen.count(ns)) { seen.insert(ns); stack.push_back(ns); }
        }
    }
    std::sort(order.begin(), order.end(), [](u64 a, u64 b) {
        return __builtin_popcountll(a) > __builtin_popcountll(b);
    });
    R.states = order;
    for (u64 s : order) {
        u64 lm = legal_mask(b, s);
        if (lm == 0) { R.grundy[s] = 0; continue; }
        if (grundy) {
            std::set<int> cg;
            u64 t = lm;
            while (t) {
                int p = __builtin_ctzll(t); t &= t - 1;
                cg.insert(R.grundy[s | (u64(1) << p)]);
            }
            int mex = 0;
            while (cg.count(mex)) ++mex;
            R.grundy[s] = mex;
        } else {
            bool any_lose = false;
            u64 t = lm;
            while (t) {
                int p = __builtin_ctzll(t); t &= t - 1;
                if (R.grundy[s | (u64(1) << p)] == 0) any_lose = true;
            }
            R.grundy[s] = any_lose ? 1 : 0;
        }
    }
    R.g0 = R.grundy[0];
    return R;
}

static void rebuild_without(Board& b, const Board& src, const std::vector<int>& rm) {
    b.n = src.n; b.V = src.V; b.full = src.full;
    b.px = src.px; b.py = src.py;
    b.triples_by_pt.assign(b.V, {});
    b.quads.clear();
    std::set<int> rset(rm.begin(), rm.end());
    for (size_t qi = 0; qi < src.quads.size(); ++qi) {
        if (rset.count((int)qi)) continue;
        u64 q = src.quads[qi];
        b.quads.push_back(q);
        for (int t = 0; t < b.V; ++t)
            if (q & (u64(1) << t))
                b.triples_by_pt[t].push_back(q & ~(u64(1) << t));
    }
}

static int u_gain(const Board& b, u64 occ, int p) {
    u64 L = legal_mask(b, occ);
    u64 Lp = legal_mask(b, occ | (u64(1) << p));
    return __builtin_popcountll(L & ~(Lp | (u64(1) << p)));
}

// ---- B267 with K_n - |S| <= 3 ----
static void run_b267(int n) {
    Board b0;
    build_square(b0, n);
    GameResult G = solve_game(b0, true);
    // K_n known: n=4 → 7, n=5 → 9, n=6 → 11
    int Kn = (n == 4) ? 7 : (n == 5) ? 9 : (n == 6) ? 11 : 0;
    // Also compute max safe size if unknown
    if (Kn == 0) {
        int best = 0;
        for (u64 s : G.states) best = std::max(best, (int)__builtin_popcountll(s));
        Kn = best;
    }
    int pairs = 0, cex = 0;
    int ws = -1, wp = -1, wq = -1, wga = -1, wgc = -1;
    int nstates_cond = 0;
    // also B266 joint histogram
    std::map<int, int> joint_hist;

    for (u64 s : G.states) {
        int k = (int)__builtin_popcountll(s);
        u64 L = legal_mask(b0, s);
        if (L == 0) continue;

        // B266 joint hist (all states)
        {
            std::vector<int> moves;
            u64 t = L;
            while (t) { int p = __builtin_ctzll(t); t &= t - 1; moves.push_back(p); }
            for (size_t i = 0; i < moves.size(); ++i)
                for (size_t j = i + 1; j < moves.size(); ++j) {
                    u64 Lpq = legal_mask(b0, s | (u64(1) << moves[i]) | (u64(1) << moves[j]));
                    int jn = __builtin_popcountll(L & ~(Lpq | (u64(1) << moves[i]) | (u64(1) << moves[j])));
                    joint_hist[jn]++;
                }
        }

        // B267 condition
        if (Kn - k > 3) continue;
        ++nstates_cond;
        std::map<u64, std::vector<int>> nf;
        std::vector<int> moves;
        u64 t = L;
        while (t) {
            int p = __builtin_ctzll(t); t &= t - 1;
            moves.push_back(p);
            u64 Lp = legal_mask(b0, s | (u64(1) << p));
            u64 newly = L & ~(Lp | (u64(1) << p));
            nf[newly].push_back((int)moves.size() - 1);
        }
        for (auto& kv : nf) {
            auto& v = kv.second;
            for (size_t a = 0; a < v.size(); ++a)
                for (size_t c = a + 1; c < v.size(); ++c) {
                    ++pairs;
                    int ga = G.grundy.at(s | (u64(1) << moves[v[a]]));
                    int gc = G.grundy.at(s | (u64(1) << moves[v[c]]));
                    if (ga != gc) {
                        ++cex;
                        if (ws < 0) {
                            ws = k; wp = moves[v[a]]; wq = moves[v[c]];
                            wga = ga; wgc = gc;
                        }
                    }
                }
        }
    }

    fprintf(stdout, "{\"n\":%d,\"K_n\":%d,\"nstates\":%d,\"nstates_endgame\":%d,",
            n, Kn, (int)G.states.size(), nstates_cond);
    fprintf(stdout, "\"B267_pairs_tested\":%d,\"B267_counterexamples\":%d,",
            pairs, cex);
    fprintf(stdout, "\"B267_witness\":{\"|S|\":%d,\"p\":%d,\"q\":%d,\"ga\":%d,\"gc\":%d},",
            ws, wp, wq, wga, wgc);
    fprintf(stdout, "\"B266_joint_hist\":{");
    bool first = true;
    for (auto& kv : joint_hist) {
        fprintf(stdout, "%s\"%d\":%d", first ? "" : ",", kv.first, kv.second);
        first = false;
    }
    fprintf(stdout, "}}\n");
}

// ---- optimized n=5 singles with OpenMP ----
static void run_singles(int n) {
    Board b0;
    build_square(b0, n);
    GameResult G = solve_game(b0, false);
    int g0s = G.g0;
    int nq = (int)b0.quads.size();
    fprintf(stdout, "{\"n\":%d,\"nquads\":%d,\"nstates\":%d,\"g0_std\":%d,",
            n, nq, (int)G.states.size(), g0s);

    std::vector<int> flips(nq, 0);
    std::vector<int> g0s_after(nq, g0s);

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 4)
#endif
    for (int qi = 0; qi < nq; ++qi) {
        Board bm;
        rebuild_without(bm, b0, {qi});
        GameResult rg = solve_game(bm, false);
        g0s_after[qi] = rg.g0;
        flips[qi] = (rg.g0 != g0s) ? 1 : 0;
    }

    int nflips = 0;
    std::vector<int> fidx;
    for (int i = 0; i < nq; ++i) if (flips[i]) { ++nflips; fidx.push_back(i); }
    fprintf(stdout, "\"B251_singles\":%d,\"B251_flips\":%d,", nq, nflips);
    if (!fidx.empty()) {
        fprintf(stdout, "\"B251_flip_qidx\":[");
        for (size_t i = 0; i < fidx.size(); ++i)
            fprintf(stdout, "%s%d", i ? "," : "", fidx[i]);
        fprintf(stdout, "],\"B251_first_quad\":");
        u64 q = b0.quads[fidx[0]];
        fprintf(stdout, "[");
        bool first = true;
        for (int p = 0; p < b0.V; ++p) if (q & (1ull << p)) {
            fprintf(stdout, "%s[%d,%d]", first ? "" : ",", b0.px[p], b0.py[p]);
            first = false;
        }
        fprintf(stdout, "],");
    }
    fprintf(stdout, "\"done\":true}\n");
}

int main(int argc, char** argv) {
    std::string mode = argc > 1 ? argv[1] : "b267";
    int n = argc > 2 ? atoi(argv[2]) : 4;
    if (mode == "b267") run_b267(n);
    else if (mode == "singles") run_singles(n);
    else if (mode == "singles_n5") run_singles(5);
    return 0;
}
