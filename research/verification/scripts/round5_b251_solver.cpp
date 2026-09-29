// Round5 B251-B272 solver (fast, staged).
// Usage: solver <stage>  stage in {singles, pairs, ugains, corr, all}
// Output JSON per stage to stdout.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <string>
#include <chrono>
#include <functional>

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
        for (int t = 0; t < b.V; ++t) {
            if (!(q & (u64(1) << t))) continue;
            b.triples_by_pt[t].push_back(q & ~(u64(1) << t));
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

// Fast outcome-only solve (win/lose). Slightly cheaper than full grundy.
struct GameResult {
    std::map<u64, int> grundy;
    std::map<u64, int> win;  // 1 if player to move wins
    int g0 = 0;
    std::vector<u64> states;
};

static GameResult solve_game(const Board& b, bool want_grundy = true) {
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
        if (lm == 0) { R.grundy[s] = 0; R.win[s] = 0; continue; }
        if (want_grundy) {
            std::set<int> child_g;
            bool any_lose = false;
            while (lm) {
                int p = __builtin_ctzll(lm);
                lm &= lm - 1;
                u64 ns = s | (u64(1) << p);
                child_g.insert(R.grundy[ns]);
                if (R.grundy[ns] == 0) any_lose = true;
            }
            int mex = 0;
            while (child_g.count(mex)) ++mex;
            R.grundy[s] = mex;
            R.win[s] = any_lose ? 1 : 0;
        } else {
            bool any_lose = false;
            u64 t = lm;
            while (t) {
                int p = __builtin_ctzll(t); t &= t - 1;
                if (R.grundy[s | (u64(1) << p)] == 0) any_lose = true;
            }
            R.grundy[s] = any_lose ? 1 : 0;  // store win in grundy if !want_grundy
            R.win[s] = any_lose ? 1 : 0;
        }
    }
    R.g0 = R.grundy[0];
    return R;
}

static int u_gain(const Board& b, u64 occ, int p) {
    u64 L = legal_mask(b, occ);
    u64 Lp = legal_mask(b, occ | (u64(1) << p));
    return __builtin_popcountll(L & ~(Lp | (u64(1) << p)));
}

static int joint_new(const Board& b, u64 occ, int p, int q) {
    u64 L = legal_mask(b, occ);
    u64 Lpq = legal_mask(b, occ | (u64(1) << p) | (u64(1) << q));
    return __builtin_popcountll(L & ~(Lpq | (u64(1) << p) | (u64(1) << q)));
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

// ============ stages ============

static void stage_singles(int n) {
    Board b0;
    build_square(b0, n);
    GameResult std_g = solve_game(b0, true);
    int g0s = std_g.g0;
    int nq = (int)b0.quads.size();
    fprintf(stdout, "{\"n\":%d,\"V\":%d,\"nquads\":%d,\"nstates\":%d,\"g0_std\":%d,",
            n, b0.V, nq, (int)std_g.states.size(), g0s);
    fprintf(stdout, "\"B251_singles\":%d,", nq);
    int flips = 0;
    std::vector<int> fidx;
    int g0_after = g0s;
    for (int qi = 0; qi < nq; ++qi) {
        Board bm;
        rebuild_without(bm, b0, {qi});
        // outcome only is enough for B251 (P/N flip = g0 zero/nonzero flip)
        GameResult rg = solve_game(bm, false);
        if (rg.g0 != g0s) {
            ++flips;
            fidx.push_back(qi);
            g0_after = rg.g0;
        }
    }
    fprintf(stdout, "\"B251_flips\":%d,\"B251_g0_after_flip\":%d,", flips, g0_after);
    if (!fidx.empty()) {
        fprintf(stdout, "\"B251_flip_qidx\":[");
        for (size_t i = 0; i < fidx.size(); ++i) fprintf(stdout, "%s%d", i ? "," : "", fidx[i]);
        fprintf(stdout, "],\"B251_first_witness_quad\":");
        print_quad(stdout, b0, b0.quads[fidx[0]]);
        fprintf(stdout, ",");
    }
    // pair removals: for n=4 all pairs (but outcome-only should be ~30s);
    // for n=5, only pairs sharing a point, capped.
    int tested = 0, pflip = 0, b253 = 0, b255 = 0;
    int fa = -1, fb = -1;
    // maximal fingerprint of standard
    u64 std_mfp = 0;
    for (u64 s : std_g.states) {
        if (legal_mask(b0, s) == 0)
            std_mfp ^= (u64)__builtin_popcountll(s) * 0x9e3779b97f4a7c15ULL + s;
    }
    int cap = (n == 4) ? 1000000 : 8000;
    for (int a = 0; a < nq && tested < cap; ++a) {
        for (int c = a + 1; c < nq && tested < cap; ++c) {
            if (n != 4 && !(b0.quads[a] & b0.quads[c])) continue;
            Board bm;
            rebuild_without(bm, b0, {a, c});
            GameResult rg = solve_game(bm, false);
            ++tested;
            if (rg.g0 != g0s) {
                ++pflip;
                bool sa = false, sb = false;
                for (int x : fidx) { if (x == a) sa = true; if (x == c) sb = true; }
                if (!sa && !sb) {
                    ++b253;
                    if (fa < 0) { fa = a; fb = c; }
                }
                // B255 check needs maximal sets — only when want_grundy; skip cheap check
            }
        }
    }
    fprintf(stdout, "\"B252_pairs_tested\":%d,\"B252_pairs_flip\":%d,", tested, pflip);
    fprintf(stdout, "\"B253_pair_flip_no_single\":%d,", b253);
    if (fa >= 0) fprintf(stdout, "\"B253_first_pair_qidx\":[%d,%d],", fa, fb);
    fprintf(stdout, "\"done\":true}\n");
}

static void stage_ugains(int n) {
    Board b0;
    build_square(b0, n);
    GameResult G = solve_game(b0, true);
    int b261_pos = 0, b261_maxj_le1 = 0, b261_maxj = 0;
    int b262_pos = 0, b262_ws = -1, b262_p = -1, b262_q = -1, b262_up = -1, b262_uq = -1;
    int b263_cmp = 0, b263_hi = 0;
    int b264_pos = 0, b264_ws = -1, b264_nl = -1, b264_nw = -1;
    int b265_pos = 0, b265_ws = -1, b265_p = -1, b265_up = -1, b265_ns = -1, b265_nb = -1;
    int b267_pairs = 0, b267_cex = 0, b267_ws = -1, b267_p = -1, b267_q = -1;
    int b268_pos = 0, b268_ws = -1, b268_wt = -1, b268_ex = -1;
    int flatP = 0, flatT = 0, nonP = 0, nonT = 0;

    for (u64 s : G.states) {
        u64 L = legal_mask(b0, s);
        if (L == 0) continue;
        int gS = G.grundy.at(s);
        int nl = __builtin_popcountll(L);
        std::vector<int> moves, us, win_i, lose_i;
        u64 tmp = L;
        while (tmp) {
            int p = __builtin_ctzll(tmp); tmp &= tmp - 1;
            moves.push_back(p);
            us.push_back(u_gain(b0, s, p));
            int cg = G.grundy.at(s | (u64(1) << p));
            if (cg == 0) win_i.push_back((int)moves.size() - 1);
            else lose_i.push_back((int)moves.size() - 1);
        }

        // B261
        for (size_t i = 0; i < moves.size(); ++i)
            for (size_t j = i + 1; j < moves.size(); ++j) {
                int jn = joint_new(b0, s, moves[i], moves[j]);
                if (jn > b261_maxj) b261_maxj = jn;
                if (us[i] <= 1 && us[j] <= 1 && jn >= 2) {
                    ++b261_pos;
                    if (jn > b261_maxj_le1) b261_maxj_le1 = jn;
                }
            }

        // B262
        if (b262_ws < 0) {
            for (size_t i = 0; i < moves.size() && b262_ws < 0; ++i) {
                if (us[i] < 3) continue;
                u64 sp = s | (u64(1) << moves[i]);
                u64 Lsp = legal_mask(b0, sp);
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

        // B264
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

        // B265
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

        // B263
        if (!win_i.empty() && !lose_i.empty()) {
            auto cmin = [&](int mi) {
                u64 ns2 = s | (u64(1) << moves[mi]);
                u64 L2 = legal_mask(b0, ns2);
                if (!L2) return 99;
                int mn = 99;
                u64 t2 = L2;
                while (t2) {
                    int p2 = __builtin_ctzll(t2); t2 &= t2 - 1;
                    mn = std::min(mn, u_gain(b0, ns2, p2));
                }
                return mn;
            };
            int wmin = 99, lmin = 99;
            for (int wi : win_i) wmin = std::min(wmin, cmin(wi));
            for (int li : lose_i) lmin = std::min(lmin, cmin(li));
            ++b263_cmp;
            if (wmin > lmin) ++b263_hi;
        }

        // B267
        {
            int K = b0.V - (int)__builtin_popcountll(s);
            if (K - (int)__builtin_popcountll(s) <= 3) {
                std::map<u64, std::vector<int>> nf;
                for (size_t i = 0; i < moves.size(); ++i) {
                    u64 Lp = legal_mask(b0, s | (u64(1) << moves[i]));
                    nf[L & ~(Lp | (u64(1) << moves[i]))].push_back((int)i);
                }
                for (auto& kv : nf) {
                    auto& v = kv.second;
                    for (size_t a = 0; a < v.size(); ++a)
                        for (size_t c = a + 1; c < v.size(); ++c) {
                            ++b267_pairs;
                            int ga = G.grundy.at(s | (u64(1) << moves[v[a]]));
                            int gc = G.grundy.at(s | (u64(1) << moves[v[c]]));
                            if (ga != gc) {
                                ++b267_cex;
                                if (b267_ws < 0) {
                                    b267_ws = (int)__builtin_popcountll(s);
                                    b267_p = moves[v[a]]; b267_q = moves[v[c]];
                                }
                            }
                        }
                }
            }
        }

        // B269
        {
            int umin = 99, umax = -1;
            for (int u : us) { umin = std::min(umin, u); umax = std::max(umax, u); }
            bool isP = (gS == 0);
            if (umin == umax) { flatT++; if (isP) flatP++; }
            else { nonT++; if (isP) nonP++; }
        }
    }

    // B268
    for (u64 s : G.states) {
        int gS = G.grundy.at(s);
        if (gS == 0) continue;
        for (int p = 0; p < b0.V; ++p) {
            if (s & (u64(1) << p)) continue;
            u64 t = s | (u64(1) << p);
            auto it = G.grundy.find(t);
            if (it == G.grundy.end() || it->second == 0) continue;
            u64 common = legal_mask(b0, s) & legal_mask(b0, t);
            if (!common) continue;
            u64 winS = 0, winT = 0;
            u64 cm = common;
            while (cm) {
                int m = __builtin_ctzll(cm); cm &= cm - 1;
                if (G.grundy.at(s | (u64(1) << m)) == 0) winS |= u64(1) << m;
                if (G.grundy.at(t | (u64(1) << m)) == 0) winT |= u64(1) << m;
            }
            if (winS && winT && (winS & winT) == 0) {
                ++b268_pos;
                if (b268_ws < 0) {
                    b268_ws = (int)__builtin_popcountll(s);
                    b268_wt = (int)__builtin_popcountll(t);
                    b268_ex = p;
                }
            }
        }
    }

    fprintf(stdout, "{\"n\":%d,\"g0\":%d,\"nstates\":%d,", n, G.g0, (int)G.states.size());
    fprintf(stdout, "\"B261_positions_two_small_u_big_joint\":%d,\"B261_max_joint_observed\":%d,\"B261_max_joint_with_both_u_le_1\":%d,",
            b261_pos, b261_maxj, b261_maxj_le1);
    fprintf(stdout, "\"B262_positions\":%d,\"B262_witness\":{\"|S|\":%d,\"p\":%d,\"q\":%d,\"up\":%d,\"uq\":%d},",
            b262_pos, b262_ws, b262_p, b262_q, b262_up, b262_uq);
    fprintf(stdout, "\"B263_positions_compared\":%d,\"B263_win_move_higher_min_child_u\":%d,", b263_cmp, b263_hi);
    fprintf(stdout, "\"B264_positions\":%d,\"B264_witness\":{\"|S|\":%d,\"|L|\":%d,\"nwin\":%d},",
            b264_pos, b264_ws, b264_nl, b264_nw);
    fprintf(stdout, "\"B265_positions\":%d,\"B265_witness\":{\"|S|\":%d,\"p\":%d,\"up\":%d,\"nsmall\":%d,\"nbig\":%d},",
            b265_pos, b265_ws, b265_p, b265_up, b265_ns, b265_nb);
    fprintf(stdout, "\"B267_pairs_tested\":%d,\"B267_counterexamples\":%d,\"B267_witness\":{\"|S|\":%d,\"p\":%d,\"q\":%d},",
            b267_pairs, b267_cex, b267_ws, b267_p, b267_q);
    fprintf(stdout, "\"B268_positions\":%d,\"B268_witness\":{\"|S|\":%d,\"|T|\":%d,\"extra\":%d},",
            b268_pos, b268_ws, b268_wt, b268_ex);
    fprintf(stdout, "\"B269_flat_u_P\":%d,\"B269_flat_u_positions\":%d,\"B269_nonflat_u_P\":%d,\"B269_nonflat_u_positions\":%d",
            flatP, flatT, nonP, nonT);
    fprintf(stdout, "}\n");
}

static void stage_corr(int n) {
    Board b0;
    build_square(b0, n);
    int V = b0.V;
    // enumerate all safe sets
    std::vector<std::vector<u64>> byk(V + 1);
    std::function<void(u64, int, u64)> dfs = [&](u64 occ, int start, u64 cand) {
        byk[__builtin_popcountll(occ)].push_back(occ);
        u64 c = cand;
        while (c) {
            int p = __builtin_ctzll(c); c &= c - 1;
            if (p < start) continue;
            u64 b = u64(1) << p;
            bool ok = true;
            for (u64 t : b0.triples_by_pt[p])
                if ((occ & t) == t) { ok = false; break; }
            if (!ok) continue;
            u64 higher = cand & ~((u64(1) << (p + 1)) - 1);
            u64 nc = 0, h = higher;
            while (h) {
                int q = __builtin_ctzll(h); h &= h - 1;
                bool ok2 = true;
                for (u64 t : b0.triples_by_pt[q])
                    if (((occ | b) & t) == t) { ok2 = false; break; }
                if (ok2) nc |= u64(1) << q;
            }
            dfs(occ | b, p + 1, nc);
        }
    };
    dfs(0, 0, b0.full);

    std::vector<long long> Zk(V + 1, 0);
    long long total = 0;
    for (int k = 0; k <= V; ++k) { Zk[k] = (long long)byk[k].size(); total += Zk[k]; }
    int maxk = 0;
    for (int k = 0; k <= V; ++k) if (Zk[k]) maxk = k;

    fprintf(stdout, "{\"n\":%d,\"V\":%d,\"n_safe_total\":%lld,\"max_safe_k\":%d,",
            n, V, total, maxk);
    fprintf(stdout, "\"level_counts\":[");
    for (int k = 0; k <= V; ++k) fprintf(stdout, "%s%lld", k ? "," : "", Zk[k]);
    fprintf(stdout, "],");

    if (V <= 25) {
        std::vector<std::vector<long long>> W1k(V, std::vector<long long>(V + 1, 0));
        std::vector<std::vector<long long>> W2k(V * V, std::vector<long long>(V + 1, 0));
        for (int k = 0; k <= V; ++k) {
            for (u64 s : byk[k]) {
                u64 t = s;
                while (t) {
                    int p = __builtin_ctzll(t); t &= t - 1;
                    W1k[p][k]++;
                    u64 t2 = t;
                    while (t2) {
                        int q = __builtin_ctzll(t2); t2 &= t2 - 1;
                        W2k[p * V + q][k]++;
                    }
                }
            }
        }
        auto eval = [&](const std::vector<long long>& coef, long long lam) -> __int128 {
            __int128 acc = 0;
            for (int k = V; k >= 0; --k) acc = acc * lam + coef[k];
            return acc;
        };
        long long lams[] = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597};
        int nflip = 0, posL = 0, negL = 0, zeroL = 0;
        int qpairs = 0, qpos = 0, qneg = 0, qflip = 0;
        std::vector<std::array<int, 2>> fex, qex;
        // precompute pair-in-quad
        std::vector<char> inq(V * V, 0);
        for (u64 q : b0.quads) {
            for (int p = 0; p < V; ++p) if (q & (1ull << p))
                for (int r = p + 1; r < V; ++r) if (q & (1ull << r))
                    inq[p * V + r] = inq[r * V + p] = 1;
        }
        for (int p = 0; p < V; ++p) for (int q = p + 1; q < V; ++q) {
            int first = 0, flipped = 0;
            for (long long lam : lams) {
                __int128 Zv = eval(Zk, lam);
                __int128 W2 = eval(W2k[p * V + q], lam);
                __int128 Wp = eval(W1k[p], lam);
                __int128 Wq = eval(W1k[q], lam);
                __int128 num = W2 * Zv - Wp * Wq;
                int sg = (num > 0) - (num < 0);
                if (first == 0 && sg != 0) first = sg;
                if (first != 0 && sg != 0 && sg != first) flipped = 1;
                if (lam == 1597) {
                    if (num > 0) ++posL; else if (num < 0) ++negL; else ++zeroL;
                    if (inq[p * V + q]) {
                        ++qpairs;
                        if (num > 0) { ++qpos; if ((int)qex.size() < 5) qex.push_back({p, q}); }
                        else if (num < 0) ++qneg;
                    }
                }
            }
            if (flipped) {
                ++nflip;
                if ((int)fex.size() < 8) fex.push_back({p, q});
            }
            if (inq[p * V + q] && flipped) ++qflip;
        }
        fprintf(stdout, "\"B271_pairs_total\":%d,\"B271_pairs_in_some_quad\":%d,",
                V * (V - 1) / 2, (int)qpairs);
        fprintf(stdout, "\"B271_cov_sign_flips\":%d,\"B271_pos_at_lambda_1597\":%d,"
                        "\"B271_neg_at_lambda_1597\":%d,\"B271_zero_at_lambda_1597\":%d,",
                nflip, posL, negL, zeroL);
        if (!fex.empty()) {
            fprintf(stdout, "\"B271_flip_examples\":[");
            for (size_t i = 0; i < fex.size(); ++i) {
                int p = fex[i][0], q = fex[i][1];
                fprintf(stdout, "%s[%d,%d,%d,%d]", i ? "," : "", b0.px[p], b0.py[p], b0.px[q], b0.py[q]);
            }
            fprintf(stdout, "],");
        }
        fprintf(stdout, "\"B272_quad_pairs_pos_at_large_lambda\":%d,"
                        "\"B272_quad_pairs_neg_at_large_lambda\":%d,"
                        "\"B272_quad_pairs_sign_flips\":%d,",
                qpos, qneg, qflip);
        if (!qex.empty()) {
            fprintf(stdout, "\"B272_pos_examples\":[");
            for (size_t i = 0; i < qex.size(); ++i) {
                int p = qex[i][0], q = qex[i][1];
                fprintf(stdout, "%s[%d,%d,%d,%d]", i ? "," : "", b0.px[p], b0.py[p], b0.px[q], b0.py[q]);
            }
            fprintf(stdout, "],");
        }
    }
    fprintf(stdout, "\"done\":true}\n");
}

int main(int argc, char** argv) {
    std::string stage = (argc > 1) ? argv[1] : "all";
    int n = (argc > 2) ? atoi(argv[2]) : 4;
    if (stage == "singles") stage_singles(n);
    else if (stage == "ugains") stage_ugains(n);
    else if (stage == "corr") stage_corr(n);
    else {
        // default: ugains + corr for given n
        stage_ugains(n);
        stage_corr(n);
    }
    return 0;
}
