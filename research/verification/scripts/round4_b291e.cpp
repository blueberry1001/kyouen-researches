// Round4 (batch b291-b360): B295 and B300 only, n=4.  Same logic as
// round4_b291.cpp sections B and C, split out so the two results do not wait
// behind the expensive n=5 game solve in section A.
//
//   B295 [existence]  Positions that agree on the *distribution of sizes of
//          maximal safe extensions* can still have different outcomes.  The
//          layer key is (k, the histogram of |M| over all maximal safe
//          supersets M of S) -- the literal reading of the hypothesis.
//   B300 [existence-bold]  No fixed-depth local information decides the
//          outcome.  The layer key is the canonical signature of the whole
//          depth-d legal-move tree: every internal node is the sorted
//          multiset of its children's signatures, every leaf is |L(S)|.
#include "kc_core.h"
#include <bits/stdc++.h>
using namespace std;
using kc::u64;

struct Game {
    const kc::Board* b = nullptr;
    int V = 0;
    std::vector<u64> states;
    std::unordered_map<u64, int> idx;
    std::vector<int> g;
    std::vector<u64> legal;
    void build(const kc::Board& bb) {
        b = &bb; V = b->V;
        states.clear(); idx.clear();
        std::vector<u64> cur{0}, nxt;
        for (int k = 0; k <= V; ++k) {
            for (u64 s : cur) states.push_back(s);
            nxt.clear();
            for (u64 s : cur) { u64 lm = kc::legal_mask(*b, s);
                for (u64 t = lm; t; t &= t - 1) nxt.push_back(s | (t & -t)); }
            cur.swap(nxt);
            if (cur.empty()) break;
        }
        idx.reserve(states.size() * 2 + 16);
        for (size_t i = 0; i < states.size(); ++i) idx[states[i]] = (int)i;
        g.assign(states.size(), -1);
        legal.assign(states.size(), 0);
    }
    int grundy(u64 s) {
        auto it = idx.find(s);
        if (it == idx.end()) return -1;
        int i = it->second;
        if (g[i] >= 0) return g[i];
        u64 lm = kc::legal_mask(*b, s); legal[i] = lm;
        if (!lm) { g[i] = 0; return 0; }
        u64 seen = 0;
        for (u64 t = lm; t; t &= t - 1) {
            int cg = grundy(s | (t & -t));
            if (cg >= 0) seen |= 1ULL << cg;
        }
        int x = 0; while (seen & (1ULL << x)) ++x;
        g[i] = x; return x;
    }
    int pop(u64 s) { return __builtin_popcountll(s); }
    int nL(u64 s) { return __builtin_popcountll(legal[idx.at(s)]); }
};

static std::string N(long long v) { return std::to_string(v); }
static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}
struct TreeSig {
    Game& gm;
    std::map<std::pair<long long,int>, std::string> memo;
    explicit TreeSig(Game& g) : gm(g) {}
    std::string rec(u64 s, int d) {
        auto key = std::make_pair((long long)s, d);
        auto it = memo.find(key); if (it != memo.end()) return it->second;
        if (d == 0) return "L" + N(gm.nL(s));
        std::vector<std::string> kids;
        u64 lm = gm.legal[gm.idx.at(s)];
        for (u64 t = lm; t; t &= t - 1) kids.push_back(rec(s | (t & -t), d - 1));
        std::sort(kids.begin(), kids.end());
        std::string r = "("; for (auto& k : kids) r += k + ","; r += ")";
        memo[key] = r; return r;
    }
};
static void enum_maximal(const kc::Board& b, std::vector<u64>& out, long long cap) {
    // A plain DFS pushes the same maximal set once per legal ordering, so the
    // raw output is full of duplicates.  Deduplicate, and cross-check the
    // count against the authoritative dump research/verification/data/
    // maximal_n<k>.bin.
    std::set<u64> uniq;
    std::function<void(u64)> f = [&](u64 s) {
        u64 lm = kc::legal_mask(b, s);
        if (!lm) { uniq.insert(s); return; }
        for (u64 t = lm; t; t &= t - 1) f(s | (t & -t));
    };
    f(0);
    out.assign(uniq.begin(), uniq.end());
    if ((long long)out.size() > cap) out.resize(cap);
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

int main(int argc, char** argv) {
    std::string outp = argc > 1 ? argv[1] : "";
    std::ofstream fout;
    if (!outp.empty()) fout.open(outp);
    std::ostream& o = outp.empty() ? std::cout : (std::ostream&)fout;
    o << "{\n";
    double T0 = now_s();

    kc::Board b; kc::build_square(b, 4);
    Game gm; gm.build(b); gm.grundy(0);
    fprintf(stderr, "n=4 states=%zu g_empty=%d\n", gm.states.size(), gm.grundy(0));
    fflush(stderr);

    // ---------------------------------------------------------- B300
    o << "  \"B300_depth_trees_n4\": [\n";
    {
        TreeSig ts(gm);
        auto xs = [&](u64 s) { std::string o2 = "["; bool g = true;
            for (int p = 0; p < 16; ++p) if (s & (u64(1)<<p)) { if (!g) o2 += ","; g = false;
                o2 += N(p) + "=(" + N(p%4) + "," + N(p/4) + ")"; } return o2 + "]"; };
        for (int d = 1; d <= 2; ++d) {
            std::map<std::string, std::vector<u64>> layers;
            for (u64 s : gm.states) {
                if (gm.pop(s) < 3) continue;
                layers[ts.rec(s, d)].push_back(s);
            }
            long long nsplit = 0, ntot = 0, np = 0, nn = 0;
            std::string w1 = "null", w2 = "null";
            for (auto& kv : layers) {
                bool hasP = false, hasN = false; u64 ps = 0, ns = 0;
                for (u64 s : kv.second) { if (gm.grundy(s) == 0) { hasP = true; ps = s; ++np; }
                                         else { hasN = true; ns = s; ++nn; } }
                ++ntot;
                if (hasP && hasN) { ++nsplit;
                    if (w1 == "null") w1 = "{\"P\":" + xs(ps) + ",\"g_P\":0,\"N\":" + xs(ns)
                        + ",\"gN\":" + N(gm.grundy(ns)) + ",\"n_same_layer\":" + N((long long)kv.second.size()) + "}";
                    if (w2 == "null") w2 = "{\"P\":" + xs(ps) + ",\"N\":" + xs(ns) + "}"; }
            }
            o << "    {\"d\": " << N(d) + ", \"n_layers\": " + N(ntot)
              + ", \"n_split_layers\": " + N(nsplit)
              + ", \"n_P_states\": " + N(np) + ", \"n_N_states\": " + N(nn)
              + ", \"first_witness\": " + w1 + "}" << (d < 2 ? ",\n" : "\n");
            fprintf(stderr, "[B300] d=%d layers=%lld split=%lld\n", d, ntot, nsplit);
            fflush(stderr);
        }
        o << "  ],\n";
    }

    // ---------------------------------------------------------- B295
    o << "  \"B295_maximal_cover_n4\": ";
    {
        double t0 = now_s();
        std::vector<u64> maxs; enum_maximal(b, maxs, 200000);
        {   // cross-check against the authoritative dump
            auto ref = load_bin("/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/"
                                "research/verification/data/maximal_n4.bin");
            std::set<u64> a(maxs.begin(), maxs.end()), r(ref.begin(), ref.end());
            fprintf(stderr, "[B295] enumerated=%zu  reference=%zu  same=%d\n",
                    a.size(), r.size(), (int)(a == r));
            fflush(stderr);
        }
        fprintf(stderr, "[B295] maximal sets = %zu\n", maxs.size()); fflush(stderr);
        std::map<std::string, long long> hits;
        std::map<std::string, std::vector<u64>> ppos, npos;   // one P and one N each
        long long nstates = 0;
        for (u64 s : gm.states) {
            int k = gm.pop(s);
            if (k < 2) continue;
            ++nstates;
            std::map<int, long long> h;
            for (u64 M : maxs) if ((M & s) == s) h[gm.pop(M)]++;
            std::string key = N(k) + "|";
            for (auto& kv : h) key += N(kv.first) + ":" + N(kv.second) + ",";
            int gv = gm.grundy(s);
            auto it = hits.find(key);
            if (it == hits.end()) hits[key] = 1;
            else hits[key]++;
            if (gv == 0) { if (ppos[key].empty()) ppos[key].push_back(s); }
            else         { if (npos[key].empty()) npos[key].push_back(s); }
        }
        long long nsplit = 0;
        std::string wits = "[";
        bool fw = true;
        auto xs = [&](u64 s) { std::string t = "["; bool g = true;
            for (int p = 0; p < 16; ++p) if (s & (u64(1)<<p)) { if (!g) t += ","; g = false;
                t += N(p); } return t + "]"; };
        for (auto& kv : hits) {
            if (ppos[kv.first].empty() || npos[kv.first].empty()) continue;
            ++nsplit;
            if (nsplit > 3) continue;
            if (!fw) wits += ", "; fw = false;
            u64 P = ppos[kv.first][0], Nn = npos[kv.first][0];
            wits += "{\"key\": \"" + kv.first + "\", \"n_positions\": " + N(kv.second)
                  + ", \"P\": {\"S\": " + xs(P) + ", \"g\": " + N(gm.grundy(P))
                  + ", \"k\": " + N(gm.pop(P)) + ", \"L\": " + N(gm.nL(P)) + "}"
                  + ", \"N\": {\"S\": " + xs(Nn) + ", \"g\": " + N(gm.grundy(Nn))
                  + ", \"k\": " + N(gm.pop(Nn)) + ", \"L\": " + N(gm.nL(Nn)) + "}}";
        }
        wits += "]";
        o << "{\"n_maximal_sets\": " << N((long long)maxs.size())
          << ", \"n_states_scanned\": " << N(nstates)
          << ", \"n_layers\": " << N((long long)hits.size())
          << ", \"n_split_layers\": " << N(nsplit)
          << ", \"witnesses\": " << wits
          << ", \"seconds\": " << N((long long)(now_s()-t0)) << "}";
        fprintf(stderr, "[B295] layers=%zu split=%lld\n", hits.size(), nsplit);
        fflush(stderr);
    }
    o << "\n}\n";
    o.flush();
    fprintf(stderr, "TOTAL %.1fs\n", now_s()-T0);
    return 0;
}
