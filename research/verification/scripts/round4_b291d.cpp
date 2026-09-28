// Round4 (batch b291-b360): B365 and B366 only.
//
// B365 [stat]  Among maximum-size sets with matched (n, K_n) and matched mean
//              b, higher rho must mean a smaller 1-stone-move degree.
//              deg(S) = #{ single-stone relocations u->v, u in S, v not in S,
//              such that S - {u} + {v} is still a safe set of the same size }.
// B366 [structure] The fault tolerance of each empty point p is the
//              transversal number tau(F_p) of a linear 3-uniform family on k
//              vertices with b_S(p) edges.  B366 claims the geometric family
//              always admits a *smaller* transversal than an arbitrary linear
//              3-uniform family with the same (k, b).  We therefore compute
//              max tau over the geometric families and max tau over randomly
//              sampled arbitrary linear families with the same (k, b).
#include "kc_core.h"
#include <bits/stdc++.h>
using namespace std;
using kc::u64;

static std::string J(long long v) { return std::to_string(v); }
static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}
static std::vector<int> bits(u64 m) {
    std::vector<int> v;
    while (m) { u64 b = m & (~m + 1); v.push_back(__builtin_ctzll(m)); m ^= b; }
    return v;
}
static u64 full_low(int k) { return k >= 64 ? ~u64(0) : ((u64(1) << k) - 1); }
static std::string hstr(const std::map<int, long long>& h) {
    std::string s = "{", f = "";
    for (auto& kv : h) { s += f + "\"" + J(kv.first) + "\": " + J(kv.second); f = ", "; }
    return s + "}";
}
static std::string dstr(const std::map<int, long long>& h) {
    std::string s = "{", f = "";
    for (auto& kv : h) { s += f + "\"" + J(kv.first) + "\": " + J(kv.second); f = ", "; }
    return s + "}";
}
static std::vector<u64> load_bin(const std::string& path) {
    std::vector<u64> v;
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) { fprintf(stderr, "MISSING %s\n", path.c_str()); return v; }
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    v.resize(sz / 8);
    if (sz) { size_t rd = fread(v.data(), 1, sz, f); (void)rd; }
    fclose(f);
    return v;
}
// exact transversal number of a 3-uniform family (k-bit masks), cap 4
static int tau_exact(const std::vector<u64>& H, int k, int cap) {
    if (H.empty()) return 0;
    u64 inter = full_low(k);
    for (u64 t : H) { inter &= t; if (!inter) break; }
    if (inter) return 1;
    if (cap < 2) return 2;
    u64 e1 = H[0];
    for (int w = 0; w < k; ++w) if (e1 >> w & 1) {
        u64 i2 = full_low(k);
        for (u64 t : H) if (!((t >> w) & 1)) { i2 &= t; if (!i2) break; }
        if (i2) return 2;
    }
    if (cap < 3) return 3;
    for (int a = 0; a < k; ++a) if (e1 >> a & 1) {
        std::vector<u64> Ha;
        for (u64 t : H) if (!((t >> a) & 1)) Ha.push_back(t);
        if (Ha.empty()) return 1;
        u64 e2 = Ha[0];
        for (int x = 0; x < k; ++x) if (e2 >> x & 1) {
            u64 i3 = full_low(k);
            for (u64 t : Ha) if (!((t >> x) & 1)) { i3 &= t; if (!i3) break; }
            if (i3) return 3;
        }
    }
    if (cap < 4) return 4;
    // tau = 4 : need a 4-transversal.  Search pairs (a,b) with a in e1
    for (int a = 0; a < k; ++a) if (e1 >> a & 1) {
        std::vector<u64> Ha;
        for (u64 t : H) if (!((t >> a) & 1)) Ha.push_back(t);
        if (Ha.empty()) return 1;
        for (int b = 0; b < k; ++b) {
            u64 i2 = full_low(k);
            for (u64 t : Ha) if (!((t >> b) & 1)) { i2 &= t; if (!i2) break; }
            if (!i2) continue;
            u64 e2 = i2;
            for (int x = 0; x < k; ++x) if (e2 >> x & 1) {
                u64 i3 = full_low(k);
                for (u64 t : Ha) if (!((t >> x) & 1)) { i3 &= t; if (!i3) break; }
                if (!i3) continue;
                u64 e3 = i3;
                for (int y = 0; y < k; ++y) if (e3 >> y & 1) {
                    u64 i4 = full_low(k);
                    for (u64 t : Ha) if (!((t >> y) & 1)) { i4 &= t; if (!i4) break; }
                    if (i4) return 4;
                }
            }
        }
    }
    return 5;
}

int main(int argc, char** argv) {
    std::string outp = argc > 1 ? argv[1] : "";
    std::ostream& o = outp.empty() ? std::cout : *(new std::ofstream(outp));
    o << "{\n";
    const std::string REPO = "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches";
    const std::string root = REPO + "/research/verification/data/";
    const std::string night = REPO + "/night-research/";

    std::vector<int> NS = {3, 4, 5, 6, 7};
    // n=6 has 349,596 maximal sets; only a deterministic prefix is used so the
    // B365/B366 cells stay tractable.  n<=5 is exhaustive.
    const long long SET_CAP = (getenv("R4D_CAP") ? atoll(getenv("R4D_CAP"))
                                                 : 40000LL);

    // ---- B366: geometric tau vs the best tau of a random linear family -----
    // For each (k, b) cell we record max_tau_geometric and, for many random
    // linear 3-uniform families with the same (k, b), max_tau_random.  B366
    // predicts max_tau_geometric < max_tau_random in every cell.
    o << "  \"B366_tau_vs_arbitrary_linear\": [\n";
    std::mt19937_64 rng(20260927);
    bool f1 = true;
    for (int n : NS) {
        std::string p = n == 7 ? night + "maxsafe_n7_K14.bin"
                              : root + "maximal_n" + J(n) + ".bin";
        auto sets = load_bin(p);
        if (sets.empty()) continue;
        if ((long long)sets.size() > SET_CAP) sets.resize(SET_CAP);
        double t0 = now_s();
        kc::Board B; kc::build_square(B, n);
        // tc[p] : 3-point masks T with T u {p} forbidden
        std::vector<std::vector<u64>> tc(B.V);
        for (u64 q : B.quads) {
            int ids[4], j = 0;
            for (int i = 0; i < B.V; ++i) if (q >> i & 1) ids[j++] = i;
            for (int t = 0; t < 4; ++t) {
                u64 o2 = 0;
                for (int s = 0; s < 4; ++s) if (s != t) o2 |= u64(1) << ids[s];
                tc[ids[t]].push_back(o2);
            }
        }
        // (k,b) -> max geometric tau ; (k,b) -> max random tau
        std::map<std::pair<int,long long>, long long> gmax, rmax;
        std::map<std::pair<int,long long>, long long> gcount;
        std::vector<u64> fam;
        long long nrand = 0;
        for (u64 S : sets) {
            std::vector<int> Sv = bits(S);
            int k = (int)Sv.size();
            // index map point -> position
            std::vector<int> pos(B.V, -1);
            for (int i = 0; i < k; ++i) pos[Sv[i]] = i;
            for (int q = 0; q < B.V; ++q) if (pos[q] < 0) {
                fam.clear();
                for (u64 t : tc[q]) {
                    int idx[3], c = 0;
                    for (int i = 0; i < k; ++i) if (t >> Sv[i] & 1) idx[c++] = i;
                    if (c != 3) continue;
                    fam.push_back((u64(1) << idx[0]) | (u64(1) << idx[1]) | (u64(1) << idx[2]));
                }
                if (fam.empty()) continue;
                long long b = (long long)fam.size();
                int tg = tau_exact(fam, k, 4);
                auto key = std::make_pair(k, b);
                gcount[key]++;
                if (tg > gmax[key]) gmax[key] = tg;
                // random linear family with the same (k, b): greedily add
                // triples that share <= 1 vertex with everything so far.
                for (int rep = 0; rep < 8; ++rep) {
                    std::vector<u64> H;
                    std::vector<std::vector<std::pair<int,int>>> byv(k);
                    std::mt19937_64 rr(rng());
                    int guard = 0;
                    while ((long long)H.size() < b && guard++ < 200000) {
                        int a = (int)(rr() % k);
                        int bb = -1, cc = -1;
                        // pick b,c avoiding the two-pairs already used at a
                        int tries = 0;
                        while (tries++ < 60) {
                            int y = (int)(rr() % k); if (y == a) continue;
                            bool ok = true;
                            for (auto& pr : byv[a]) if (pr.first == y || pr.second == y) { ok = false; break; }
                            if (ok) { bb = y; break; }
                        }
                        if (bb < 0) break;
                        tries = 0;
                        while (tries++ < 60) {
                            int z = (int)(rr() % k); if (z == a || z == bb) continue;
                            bool ok = true;
                            for (auto& pr : byv[a]) if (pr.first == z || pr.second == z) { ok = false; break; }
                            if (ok) for (auto& pr : byv[bb]) if (pr.first == z || pr.second == z) { ok = false; break; }
                            if (ok) { cc = z; break; }
                        }
                        if (cc < 0) break;
                        H.push_back((u64(1) << a) | (u64(1) << bb) | (u64(1) << cc));
                        byv[a].push_back({bb, cc});
                        byv[bb].push_back({a, cc});
                        byv[cc].push_back({a, bb});
                    }
                    if ((long long)H.size() < b) continue;   // could not reach b
                    int tr = tau_exact(H, k, 4);
                    nrand++;
                    if (tr > rmax[key]) rmax[key] = tr;
                }
            }
        }
        // merge
        std::string cells = "{", cf = "";
        for (auto& kv : gmax) {
            cells += cf + "\"" + J(kv.first.first) + "_" + J(kv.first.second) + "\": "
                   + "{\"n_geom_families\": " + J(gcount[kv.first])
                   + ", \"max_tau_geom\": " + J(kv.second)
                   + ", \"max_tau_rand\": " + J(rmax.count(kv.first) ? rmax[kv.first] : -1LL)
                   + ", \"n_rand_families\": 8}";
            cf = ", ";
        }
        cells += "}";
        // count violations of B366
        long long nviol = 0, ncells = 0, nstrict = 0;
        for (auto& kv : gmax) {
            long long rg = rmax.count(kv.first) ? rmax[kv.first] : -1;
            if (rg < 0) continue;
            ++ncells;
            if (kv.second >= rg) ++nviol;
            if (kv.second < rg) ++nstrict;
        }
        if (!f1) o << ",\n"; f1 = false;
        o << "    {\"n\": " << J(n) << ", \"n_maximal_sets\": " << J((long long)sets.size())
          << ", \"n_cells\": " << J(ncells)
          << ", \"n_cells_geom_lt_rand\": " << J(nstrict)
          << ", \"n_cells_geom_ge_rand\": " << J(nviol)
          << ", \"n_random_families_tried\": " << J(nrand)
          << ", \"cells\": " << cells
          << ", \"seconds\": " << J((long long)(now_s()-t0)) << "}";
        fprintf(stderr, "[B366] n=%d cells=%d viol=%d %.0fs\n", n, ncells, nviol, now_s()-t0);
        fflush(stderr);
    }
    o << "\n  ],\n";

    // ------------------------------- B365: 1-stone degree vs rho, mean b matched
    o << "  \"B365_one_stone_degree\": [\n";
    f1 = true;
    for (int n : NS) {
        std::string p = n == 7 ? night + "maxsafe_n7_K14.bin"
                              : root + "maximal_n" + J(n) + ".bin";
        auto sets = load_bin(p);
        if (sets.empty()) continue;
        if ((long long)sets.size() > SET_CAP) sets.resize(SET_CAP);
        double t0 = now_s();
        kc::Board B; kc::build_square(B, n);
        std::vector<std::vector<u64>> tc(B.V);
        for (u64 q : B.quads) {
            int ids[4], j = 0;
            for (int i = 0; i < B.V; ++i) if (q >> i & 1) ids[j++] = i;
            for (int t = 0; t < 4; ++t) {
                u64 o2 = 0;
                for (int s = 0; s < 4; ++s) if (s != t) o2 |= u64(1) << ids[s];
                tc[ids[t]].push_back(o2);
            }
        }
        // group the maximal sets of this board by (k, mean b over empty pts)
        // and report, per cell, the mean 1-stone degree for rho=1 and rho>=2.
        // mean b is bucketed exactly as (sum_b, n_empty) -> we key on k and
        // on the exact integer floor of 100*mean_b to stay in integers.
        std::map<std::pair<int,int>, std::array<long long,3>> acc;  // deg sum, cnt, rho flag
        std::map<std::pair<int,int>, std::map<int,long long>> accr;
        std::vector<u64> fam;
        long long nsamp = 0;
        for (u64 S : sets) {
            std::vector<int> Sv = bits(S);
            int k = (int)Sv.size();
            // rho of this set
            int rho = 5;
            for (int q = 0; q < B.V && rho > 1; ++q) if (!((S >> q) & 1)) {
                fam.clear();
                for (u64 t : tc[q]) {
                    int idx[3], c = 0;
                    for (int i = 0; i < k; ++i) if (t >> Sv[i] & 1) idx[c++] = i;
                    if (c != 3) continue;
                    fam.push_back((u64(1) << idx[0]) | (u64(1) << idx[1]) | (u64(1) << idx[2]));
                }
                if (fam.empty()) { rho = 0; break; }
                int t = tau_exact(fam, k, 2);
                if (t < rho) rho = t;
            }
            if (rho > 3) rho = 4;
            // mean b over ALL empty points (zeros included)
            long long sumb = 0; int nempty = 0;
            for (int q = 0; q < B.V; ++q) if (!((S >> q) & 1)) {
                int c = 0;
                for (u64 t : tc[q]) if ((S & t) == t) ++c;
                sumb += c; ++nempty;
            }
            if (nempty == 0) continue;
            int mb = (int)(100 * sumb / nempty);      // exact integer bucket
            // 1-stone relocation degree
            long long deg = 0;
            for (int i = 0; i < k; ++i) {
                u64 S1 = S & ~(u64(1) << Sv[i]);
                for (int v = 0; v < B.V; ++v) if (!((S >> v) & 1)) {
                    if (kc::can_add(B, S1, v)) ++deg;
                }
            }
            auto key = std::make_pair(k, mb);
            accr[key][rho]++;
            if (rho >= 2) { acc[key][0] += deg; acc[key][1]++; }
            else          { acc[key][2] += deg; }
            ++nsamp;
        }
        std::string cells = "{", cf = "";
        long long ncells = 0, n_support = 0, n_anti = 0;
        for (auto& kv : accr) {
            if (kv.second.size() < 2) continue;         // need both rho classes
            long long c1 = 0, c2 = 0, s1 = 0, s2 = 0;
            auto& a = acc[kv.first];
            c2 = a[1]; s2 = a[0];
            c1 = kv.second.count(1) ? kv.second.at(1) : 0;
            s1 = a[2];
            if (!c1 || !c2) continue;
            ++ncells;
            bool support = (s2 / c2) < (s1 / c1);       // high rho -> low degree
            if (support) ++n_support; else ++n_anti;
            cells += cf + "{\"k\": " + J(kv.first.first)
                  + ", \"mean_b_x100\": " + J(kv.first.second)
                  + ", \"n_rho1\": " + J(c1) + ", \"mean_deg_rho1\": " + J(s1 / c1)
                  + ", \"n_rho_ge2\": " + J(c2) + ", \"mean_deg_rho_ge2\": " + J(s2 / c2)
                  + ", " + (support ? "\"direction\": \"supported\"" : "\"direction\": \"anti\"")
                  + "}";
            cf = ", ";
        }
        cells += "}";
        if (!f1) o << ",\n"; f1 = false;
        o << "    {\"n\": " << J(n) << ", \"n_maximal_sets\": " << J((long long)sets.size())
          << ", \"n_cells_with_both_rho_classes\": " << J(ncells)
          << ", \"n_cells_high_rho_has_lower_degree\": " << J(n_support)
          << ", \"n_cells_high_rho_has_higher_degree\": " << J(n_anti)
          << ", \"cells\": " << cells
          << ", \"seconds\": " << J((long long)(now_s()-t0)) << "}";
        fprintf(stderr, "[B365] n=%d cells=%d sup=%d anti=%d %.0fs\n",
                n, ncells, n_support, n_anti, now_s()-t0);
        fflush(stderr);
    }
    o << "\n  ]\n}\n";
    return 0;
}
