// Round4 (batch b291-b360, remaining IDs): exact rho / tau for every maximal
// safe set, plus the b-vector (cover multiplicity) statistics.
//
//   B357  [universal-bold] for every eps>0 the number of empty points with
//         b_S(p) >= eps*k^2 is bounded by a k-independent constant.
//   B361  [universal-bold] every S attaining s_n has rho(S)=1
//   B362  [existence] a maximal S with rho(S) >= 2
//   B364  [universal-bold] rho <= 3 on standard boards
//   B365  [stat] within matched (n, K, mean b), high rho => small 1-swap degree
//   B366  [structure] per-point fault tolerance = transversal number of a
//         linear 3-uniform family, compared against arbitrary linear
//         3-uniform families with the same (k, b).
//
// Integer / bitmask only.  rho(S) = min over empty p of tau(F_p), where
// F_p = {T subset S : |T| = 3, T u {p} is a forbidden 4-set}.  The removal
// positions themselves are never counted (they are the transversal).
#include "kc_core.h"
#include <bits/stdc++.h>
using namespace std;
using kc::u64;

// ------------------------------------------------------------------ helpers
static std::string J(long long v) { return std::to_string(v); }
static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}
static std::string hstr(const std::map<int, long long>& h) {
    std::string s = "{";
    bool f = true;
    for (auto& kv : h) { if (!f) s += ", "; f = false;
        s += "\"" + J(kv.first) + "\": " + J(kv.second); }
    return s + "}";
}
static std::vector<int> bits(u64 m) {
    std::vector<int> v;
    while (m) { u64 b = m & (~m + 1); v.push_back(__builtin_ctzll(m)); m ^= b; }
    return v;
}
static u64 full_low(int k) { return k >= 64 ? ~u64(0) : ((u64(1) << k) - 1); }

// exact transversal number of a 3-uniform family given as k-bit triple
// masks.  Returns the value if <= cap, else cap+1.
static int tau_exact(const std::vector<u64>& H, int k, int cap) {
    if (H.empty()) return 0;
    u64 inter = full_low(k);
    for (u64 t : H) { inter &= t; if (!inter) break; }
    if (inter) return 1;                     // a single stone hits every triple
    if (cap < 2) return 2;
    u64 e1 = H[0];
    for (int w = 0; w < k; ++w) if (e1 >> w & 1) {
        u64 i2 = full_low(k);
        for (u64 t : H) if (!((t >> w) & 1)) { i2 &= t; if (!i2) break; }
        if (i2) return 2;
    }
    if (cap < 3) return 3;
    for (int a = 0; a < k; ++a) if (e1 >> a & 1) {
        std::vector<u64> Ha; Ha.reserve(H.size());
        for (u64 t : H) if (!((t >> a) & 1)) Ha.push_back(t);
        if (Ha.empty()) return 1;            // impossible here, but safe
        u64 e2 = Ha[0];
        for (int x = 0; x < k; ++x) if (e2 >> x & 1) {
            u64 i3 = full_low(k);
            for (u64 t : Ha) if (!((t >> x) & 1)) { i3 &= t; if (!i3) break; }
            if (i3) return 3;
        }
    }
    return cap + 1;
}

struct Board2 {
    kc::Board B;
    int n = 0, V = 0;
    // tc[p] : set of 3-point masks T (over V bits) with T u {p} forbidden
    std::vector<std::vector<u64>> tc;
    // pairs[p] : for every unordered pair {a,b} of points, the number of
    // forbidden 4-sets through p, a, b.  Used only as a cross-check.
    void build(int nn) {
        kc::build_square(B, nn); n = nn; V = B.V;
        tc.assign(V, {});
        for (u64 q : B.quads) {
            int ids[4]; int j = 0;
            for (int i = 0; i < V; ++i) if (q >> i & 1) ids[j++] = i;
            for (int t = 0; t < 4; ++t) {
                u64 o = 0;
                for (int s = 0; s < 4; ++s) if (s != t) o |= u64(1) << ids[s];
                tc[ids[t]].push_back(o);
            }
        }
    }
    // family F_p of S, as k-bit masks over the *positions inside S*
    void family_of(const std::vector<int>& S, int p,
                   std::vector<u64>& out) {
        out.clear();
        int k = (int)S.size();
        for (u64 t : tc[p]) {
            int idx[3], c = 0;
            for (int i = 0; i < k; ++i) if (t >> S[i] & 1) idx[c++] = i;
            if (c != 3) continue;
            u64 m = (u64(1) << idx[0]) | (u64(1) << idx[1]) | (u64(1) << idx[2]);
            out.push_back(m);
        }
    }
    // b_S(p) = |F_p| for every empty p
    void bvec(const std::vector<int>& S, std::vector<std::pair<int,int>>& bv) {
        bv.clear();
        u64 occ = 0; for (int v : S) occ |= u64(1) << v;
        for (int p = 0; p < V; ++p) if (!(occ >> p & 1)) {
            int c = 0;
            for (u64 t : tc[p]) if ((occ & t) == t) ++c;
            if (c) bv.push_back({p, c});
        }
    }
};

static std::vector<u64> load_bin(const std::string& path) {
    std::vector<u64> v;
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) { fprintf(stderr, "MISSING %s\n", path.c_str()); return v; }
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    v.resize(sz / 8);
    size_t rd = fread(v.data(), 1, sz, f);
    (void)rd; fclose(f);
    return v;
}

int main(int argc, char** argv) {
    std::string outp = argc > 1 ? argv[1] : "";
    std::ofstream fout;
    if (!outp.empty()) fout.open(outp);
    std::ostream& o = outp.empty() ? std::cout : (std::ostream&)fout;
    o << "{\n";
    double T0 = now_s();

    const std::string REPO = "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches";
    std::string root = REPO + "/research/verification/data/";
    std::string night = REPO + "/night-research/";

    std::vector<int> NS = {2, 3, 4, 5, 6, 7};
    std::vector<std::vector<u64>> MAXS(NS.size());
    std::vector<int> SN(NS.size());
    for (size_t i = 0; i < NS.size(); ++i) {
        SN[i] = NS[i];
        std::string p = root + "maximal_n" + J(NS[i]) + ".bin";
        if (NS[i] == 7) p = night + "maxsafe_n7_K14.bin";
        MAXS[i] = load_bin(p);
        fprintf(stderr, "[load] n=%d sets=%zu\n", NS[i], MAXS[i].size());
    }

    // =============================== A : exact rho for every maximal set
    o << "  \"A_rho_exact\": [\n";
    for (size_t i = 0; i < NS.size(); ++i) {
        int n = SN[i]; auto& sets = MAXS[i];
        if (sets.empty()) { o << (i ? ",\n" : ""); o << "    null"; continue; }
        double t0 = now_s();
        Board2 B2; B2.build(n);
        std::map<int, std::map<int, long long>> rhist;      // k -> rho -> count
        std::map<int, long long> rhist_all;                 // rho -> count
        long long s_n = -1; std::map<int, long long> sn_rho;
        int maxrho = -1;
        std::string wit_rho2 = "null", wit_rho1_sn = "null", wit_rho_ge3 = "null";
        long long nlin_viol = 0;                            // B366 linearity
        std::vector<u64> fam;
        for (size_t si = 0; si < sets.size(); ++si) {
            std::vector<int> S = bits(sets[si]);
            int k = (int)S.size();
            int rho = 1 << 20;
            for (int p = 0; p < B2.V; ++p) if (!((sets[si] >> p) & 1)) {
                B2.family_of(S, p, fam);
                if (fam.empty()) { rho = 0; break; }        // not maximal
                int t = tau_exact(fam, k, 3);
                // linearity check (B071): two distinct triples share <= 1 vertex
                for (size_t z = 0; z < fam.size(); ++z)
                    for (size_t w = z + 1; w < fam.size(); ++w)
                        if (__builtin_popcountll(fam[z] & fam[w]) > 1) ++nlin_viol;
                if (t < rho) rho = t;
                if (rho == 1) break;
            }
            if (rho > 3) rho = 4;                            // cap marker
            rhist[k][rho]++; rhist_all[rho]++;
            if (s_n < 0 || k < s_n) { s_n = k; sn_rho.clear(); }
            if (k == s_n) { sn_rho[rho]++;
                if (rho == 1 && wit_rho1_sn == "null") {
                    std::string w = "["; for (int v : S) w += J(v) + ",";
                    wit_rho1_sn = w + "]";
                } }
            if (rho > maxrho) maxrho = rho;
            if (rho == 2 && wit_rho2 == "null") {
                std::string w = "["; for (int v : S) w += J(v) + ",";
                wit_rho2 = w + "]";
            }
            if (rho >= 3 && wit_rho_ge3 == "null") {
                std::string w = "["; for (int v : S) w += J(v) + ",";
                wit_rho_ge3 = w + "]";
            }
            if (si % 40000 == 0) { fprintf(stderr, "[A] n=%d %zu/%zu %.0fs\n",
                n, si, sets.size(), now_s()-t0); fflush(stderr); }
        }
        std::string byk = "{";
        bool f = true;
        for (auto& kv : rhist) { if (!f) byk += ", "; f = false;
            byk += "\"" + J(kv.first) + "\": " + hstr(kv.second); }
        byk += "}";
        o << (i ? ",\n" : "")
          << "    {\"n\": " << J(n) << ", \"n_maximal_sets\": " << J((long long)sets.size())
          << ", \"rho_hist_all\": " << hstr(rhist_all)
          << ", \"rho_hist_by_k\": " << byk
          << ", \"s_n\": " << J(s_n) << ", \"s_n_rho_hist\": " << hstr(sn_rho)
          << ", \"s_n_witness_rho1\": " << wit_rho1_sn
          << ", \"max_rho_observed\": " << J(maxrho)
          << ", \"first_rho2_witness\": " << wit_rho2
          << ", \"first_rho_ge3_witness\": " << wit_rho_ge3
          << ", \"linearity_violations_Fp\": " << J(nlin_viol)
          << ", \"seconds\": " << J((long long)(now_s()-t0)) << "}";
        fprintf(stderr, "[A] n=%d done rho_all=%s max=%d %.0fs\n", n,
                hstr(rhist_all).c_str(), maxrho, now_s()-t0);
    }
    o << "\n  ],\n";

    // =========================== B : B357 cover multiplicity of empty points
    // For every maximal safe set, compute the b-vector b_S(p) over the empty
    // points, then record, for a grid of rational eps, the largest number of
    // empty points with b_S(p) >= eps*k^2 over all S.  B357 claims that grid
    // maximum is bounded by a k-independent constant.
    o << "  \"B357_cover_multiplicity\": [\n";
    for (size_t i = 0; i < NS.size(); ++i) {
        int n = SN[i]; auto& sets = MAXS[i];
        if (sets.empty()) { o << (i ? ",\n" : ""); o << "    null"; continue; }
        double t0 = now_s();
        Board2 B2; B2.build(n);
        // eps as integer numerator over a fixed denominator, so the
        // comparison b >= eps*k^2 stays in exact integers.
        const long long DEN = 1000;
        const std::vector<long long> EPS = {50, 100, 150, 200, 300, 500};
        std::map<long long, std::map<int, long long>> gmax;  // eps -> k -> max count
        std::map<int, long long> kcount;                     // k -> #sets
        std::map<int, long long> gmax_b1;                    // k -> max b (top 1)
        std::map<int, long long> gmax_b2;                    // k -> 2nd largest b
        std::string wit = "null";
        std::vector<std::pair<int,int>> bv;
        for (size_t si = 0; si < sets.size(); ++si) {
            std::vector<int> S = bits(sets[si]);
            int k = (int)S.size();
            B2.bvec(S, bv);
            kcount[k]++;
            // top-two b values
            long long b1 = -1, b2 = -1;
            for (auto& e : bv) {
                if (e.second > b1) { b2 = b1; b1 = e.second; }
                else if (e.second > b2) b2 = e.second;
            }
            if (b1 > gmax_b1[k]) gmax_b1[k] = b1;
            if (b2 > gmax_b2[k]) gmax_b2[k] = b2;
            long long k2 = (long long)k * k;
            for (long long en : EPS) {
                if (k2 == 0) continue;
                long long cnt = 0;
                for (auto& e : bv) if (e.second * DEN >= en * k2) ++cnt;
                long long& g = gmax[en][k];
                if (cnt > g) {
                    g = cnt;
                    if (cnt >= 3 && wit == "null") {
                        std::string w = "{\"n\": " + J(n) + ", \"k\": " + J(k)
                          + ", \"eps_num_over_1000\": " + J(en)
                          + ", \"n_pts\": " + J(cnt) + ", \"S\": [";
                        for (int v : S) w += J(v) + ",";
                        w += "], \"b_sorted\": [";
                        std::vector<int> bs;
                        for (auto& e : bv) bs.push_back(e.second);
                        std::sort(bs.rbegin(), bs.rend());
                        for (int z = 0; z < (int)bs.size(); ++z)
                            w += J(bs[z]) + (z + 1 < (int)bs.size() ? "," : "");
                        w += "]}";
                        wit = w;
                    }
                }
            }
            if (si % 40000 == 0) { fprintf(stderr, "[B] n=%d %zu/%zu %.0fs\n",
                n, si, sets.size(), now_s()-t0); fflush(stderr); }
        }
        auto dump = [&](const std::map<int, long long>& m) {
            std::string s = "{"; bool f = true;
            for (auto& kv : m) { if (!f) s += ", "; f = false;
                s += "\"" + J(kv.first) + "\": " + J(kv.second); }
            return s + "}";
        };
        std::string epsj = "{";
        { bool f = true;
          for (long long en : EPS) {
            if (!f) epsj += ", "; f = false;
            epsj += "\"" + J(en) + "\": " + dump(gmax[en]);
          } }
        epsj += "}";
        o << (i ? ",\n" : "")
          << "    {\"n\": " << J(n) << ", \"n_maximal_sets\": " << J((long long)sets.size())
          << ", \"k_hist\": " << dump(kcount)
          << ", \"max_top1_b_by_k\": " << dump(gmax_b1)
          << ", \"max_top2_b_by_k\": " << dump(gmax_b2)
          << ", \"max_n_pts_ge_eps_k2_by_eps_and_k\": " << epsj
          << ", \"witness_at_least_3_pts\": " << wit
          << ", \"seconds\": " << J((long long)(now_s()-t0)) << "}";
        fprintf(stderr, "[B] n=%d done %.0fs\n", n, now_s()-t0);
    }
    o << "\n  ]\n}\n";
    o.flush();
    return 0;
}
