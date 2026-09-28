// round4_b291.cpp -- round4 verification solver for chunk B291-B360 (WSL g++ 13.3).
// Exact integers / exact rationals only.  JSON -> research/verification/round4_b291.json
//
//   A  J_n response graph  n=2..5  : B312 B313 B314 B315 B317 B318 B319 B320
//   B  depth-d local move trees n=4 : B300
//   C  literal maximal-set cover    : B295
//   D  max-b witness inversion       : B355 B358 B359
//   E  lattice b_max hill-climb     : B353 B354
#include "kc_core.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

using kc::u64;
using kc::Board;

static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}
static std::string N(long long v) { return std::to_string(v); }
static std::string F2(double v) { char b[64]; snprintf(b, 64, "%.6f", v); return b; }

// ======================================================================= Rat
struct Rat {
    long long n = 0, d = 1;
};
static Rat mk(long long n, long long d) {
    if (d == 0) return {0, 1};
    if (d < 0) { n = -n; d = -d; }
    long long g = std::gcd(n < 0 ? -n : n, d); if (g == 0) g = 1;
    return {n / g, d / g};
}
static Rat radd(const Rat& a, const Rat& b) { return mk(a.n * b.d + b.n * a.d, a.d * b.d); }
static Rat rsub(const Rat& a, const Rat& b) { return mk(a.n * b.d - b.n * a.d, a.d * b.d); }
static Rat rmul(const Rat& a, const Rat& b) { return mk(a.n * b.n, a.d * b.d); }
static std::string rs(const Rat& r) { return N(r.n) + "/" + N(r.d); }

// ======================================================================= Game
struct Game {
    const Board* b = nullptr;
    int V = 0;
    std::vector<u64> states;
    std::unordered_map<u64, int> idx;
    std::vector<int> g;
    std::vector<u64> legal;
    void build(const Board& bb) {
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
        if (it == idx.end()) return -1;     // not a reachable safe state
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
    int gempty() { return grundy(0); }
};

// ========================================================================= JN
struct JN {
    int W = 0, H = 0, V = 0;
    std::vector<std::set<int>> adj;
    // J_n edge = two-stone P-pair.  Parity locking (n=2,3) means every
    // two-stone position has the same parity outcome, so J_2 and J_3 are
    // empty (E=0) and J_4..J_5 carry all the structure.
    void build(int ww, int hh, Game& gm) {
        W = ww; H = hh; V = W * H; adj.assign(V, {});
        for (int a = 0; a < V; ++a) for (int b = a + 1; b < V; ++b)
            if (gm.grundy((1ULL << a) | (1ULL << b)) == 0) { adj[a].insert(b); adj[b].insert(a); }
    }
    int E() const { int e = 0; for (auto& s : adj) e += (int)s.size(); return e / 2; }
    long long n_bridges() const {
        std::vector<int> tin(V, -1), low(V); int t = 0; std::set<std::pair<int,int>> br;
        std::function<void(int,int)> dfs = [&](int v, int pe) {
            tin[v] = low[v] = t++;
            for (int w : adj[v]) { if (w == pe) continue;
                if (tin[w] != -1) { low[v] = std::min(low[v], tin[w]); continue; }
                dfs(w, v); low[v] = std::min(low[v], low[w]);
                if (low[w] > tin[v]) br.insert({std::min(v,w), std::max(v,w)}); }
        };
        for (int v = 0; v < V; ++v) if (!adj[v].empty() && tin[v] == -1) dfs(v, -1);
        return (long long)br.size();
    }
    std::vector<int> arts() const {
        std::vector<int> tin(V, -1), low(V), ia(V, 0); int t = 0;
        std::function<void(int,int)> dfs = [&](int v, int pe) {
            tin[v] = low[v] = t++; int ch = 0;
            for (int w : adj[v]) { if (w == pe) continue;
                if (tin[w] != -1) { low[v] = std::min(low[v], tin[w]); continue; }
                ch++; dfs(w, v); low[v] = std::min(low[v], low[w]);
                if (pe != -1 && low[w] >= tin[v]) ia[v] = 1; }
            if (pe == -1 && ch > 1) ia[v] = 1;
        };
        for (int v = 0; v < V; ++v) if (!adj[v].empty() && tin[v] == -1) dfs(v, -1);
        std::vector<int> a; for (int v = 0; v < V; ++v) if (ia[v]) a.push_back(v); return a;
    }
    long long count_pm() const {
        if (V > 24) return -1;   // flat DP over 2^V needs V <= 24
        size_t SZ = (size_t)1 << V;
        std::vector<long long> memo(SZ, -1);
        std::function<long long(u64)> f = [&](u64 fm) -> long long {
            if (!fm) return 1;
            long long& m = memo[fm];
            if (m >= 0) return m;
            int v = __builtin_ctzll(fm); long long s = 0;
            for (int w : adj[v]) if (fm & (1ULL << w)) s += f(fm & ~(1ULL << v) & ~(1ULL << w));
            m = s; return s; };
        return f((1ULL << V) - 1);
    }
    std::vector<std::vector<int>> enum_pm(int cap) {
        std::vector<std::vector<int>> out; std::vector<int> cur;
        std::function<void(u64)> f = [&](u64 fm) {
            if ((int)out.size() >= cap) return;
            if (!fm) { out.push_back(cur); return; }
            int v = __builtin_ctzll(fm);
            for (int w : adj[v]) if (fm & (1ULL << w)) {
                cur.push_back(std::min(v,w)); cur.push_back(std::max(v,w));
                f(fm & ~(1ULL << v) & ~(1ULL << w));
                cur.pop_back(); cur.pop_back(); }
        };
        f((1ULL << V) - 1); return out;
    }
    // near-perfect matching: instead of exhaustive backtracking, restrict the
    // search to a single skipped vertex at a time and use the same memoised
    // DP as count_pm on the remaining V-1 vertices (V-1 <= 24).
    bool has_near_pm() const {
        for (int skip = 0; skip < V; ++skip) {
            // build the induced graph on V\{skip}
            std::vector<int> verts;
            for (int i = 0; i < V; ++i) if (i != skip) verts.push_back(i);
            int m = (int)verts.size();
            if (m % 2 != 0) continue;
            if (m > 24) return false;   // not attempted
            size_t SZ = (size_t)1 << m;
            std::vector<char> memo(SZ, -1);
            std::function<bool(int, u64)> f = [&](int vi, u64 fm) -> bool {
                if (vi >= m) return fm == 0;
                if (memo[fm] >= 0) return memo[fm];
                int v = verts[vi];
                bool r = false;
                for (int w : adj[v]) if (fm & (1ULL << w)) {
                    int wi = -1;
                    for (int t = 0; t < m; ++t) if (verts[t] == w) { wi = t; break; }
                    if (wi >= 0 && f(vi + 1, fm & ~(1ULL << vi) & ~(1ULL << wi))) { r = true; break; }
                }
                if (!r) r = f(vi + 1, fm & ~(1ULL << vi));   // skip v (only valid if odd left)
                memo[fm] = r ? 1 : 0;
                return r; };
            if (f(0, (1ULL << m) - 1)) return true;
        }
        return false;
    }
    std::string d4_type(int a, int b) const {
        int ax = a % W, ay = a / W, bx = b % W, by = b / W;
        std::vector<std::string> c;
        auto nm = [&](int x1, int y1, int x2, int y2) {
            int rx = std::min(x1,x2), ry = std::min(y1,y2);
            int sx = (x1 < x2) ? 1 : -1, sy = (y1 < y2) ? 1 : -1;
            return std::to_string(rx) + "," + std::to_string(ry) + "," +
                   std::to_string(std::abs(sx)) + "x" + std::to_string(std::abs(sy));
        };
        if (W == H) { int M = W;
            c.push_back(nm(ax,ay,bx,by));
            c.push_back(nm(M-1-ay,ax,M-1-by,bx));
            c.push_back(nm(M-1-ax,M-1-ay,M-1-bx,M-1-by));
            c.push_back(nm(ay,M-1-ax,by,M-1-bx));
            c.push_back(nm(M-1-ax,ay,M-1-bx,by));
            c.push_back(nm(ax,M-1-ay,bx,M-1-by));
            c.push_back(nm(ay,ax,by,bx));
            c.push_back(nm(M-1-ay,M-1-ax,M-1-by,M-1-bx));
        } else {
            c.push_back(nm(ax,ay,bx,by));
            c.push_back(nm(W-1-ax,ay,W-1-bx,by));
            c.push_back(nm(ax,H-1-ay,bx,H-1-by));
            c.push_back(nm(W-1-ax,H-1-ay,W-1-bx,H-1-by));
        }
        std::sort(c.begin(), c.end()); return c[0];
    }
    std::pair<int, std::map<int,int>> complement() const {
        std::vector<int> comp(V, -1); int nc = 0;
        for (int v = 0; v < V; ++v) if (comp[v] < 0) {
            std::vector<int> st{v}; comp[v] = nc;
            while (!st.empty()) { int a = st.back(); st.pop_back();
                for (int b = 0; b < V; ++b) if (b != a && !adj[a].count(b) && comp[b] < 0) { comp[b] = nc; st.push_back(b); } }
            nc++;
        }
        std::map<int,int> h; for (int v = 0; v < V; ++v) h[(int)adj[v].size()]++;
        return {nc, h};
    }
    static std::string hist_s(const std::map<int,int>& h) {
        std::string s = "{"; bool f = true;
        for (auto& kv : h) { if (!f) s += ","; f = false; s += "\"" + N(kv.first) + "\":" + N(kv.second); }
        return s + "}";
    }
};

// =============================================================== B317 breaker
static int b317_break(const Board& b, const std::vector<int>& M, int V) {
    std::vector<int> mate(V, -1);
    for (size_t i = 0; i + 1 < M.size(); i += 2) { mate[M[i]] = M[i+1]; mate[M[i+1]] = M[i]; }
    int nb = 0;
    for (int p = 0; p < V; ++p) {
        if (!kc::can_add(b, 0, p)) continue;
        u64 o1 = 1ULL << p;
        for (int q = 0; q < V; ++q) {
            if (q == p) continue;
            if (!kc::can_add(b, o1, q)) continue;
            int r = mate[q]; if (r < 0) continue;
            if (o1 & (1ULL << r)) { ++nb; continue; }
            u64 four = o1 | (1ULL << q) | (1ULL << r);
            for (u64 qq : b.quads) if ((qq & four) == qq) { ++nb; break; }
        }
    }
    return nb;
}

// ============================================================== B300 trees
struct TreeSig {
    Game& gm;
    std::map<std::pair<int,int>, std::string> memo;
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

// ======================================================== B295 maximal sets
static void enum_maximal(const Board& b, std::vector<u64>& out, long long cap) {
    out.clear();
    std::function<void(u64)> f = [&](u64 s) {
        if ((long long)out.size() >= cap) return;
        u64 lm = kc::legal_mask(b, s);
        if (!lm) { out.push_back(s); return; }
        for (u64 t = lm; t; t &= t - 1) f(s | (t & -t));
    };
    f(0);
}

// ===================================================== geometry for cover
struct Pt {
    long long x, y;
    bool operator<(const Pt& o) const { return std::tie(x,y) < std::tie(o.x,o.y); }
    bool operator==(const Pt& o) const { return x == o.x && y == o.y; }
};
static bool circle_key(Pt p, Pt a, Pt b, long long& ux, long long& uy, long long& d) {
    d = 2 * (a.x * (b.y - p.y) + b.x * (p.y - a.y) + p.x * (a.y - b.y));
    if (d == 0) return false;
    ux = ((a.x*a.x + a.y*a.y) * (b.y - p.y) + (b.x*b.x + b.y*b.y) * (p.y - a.y)
        + (p.x*p.x + p.y*p.y) * (a.y - b.y));
    uy = ((a.x*a.x + a.y*a.y) * (p.x - b.x) + (b.x*b.x + b.y*b.y) * (a.x - p.x)
        + (p.x*p.x + p.y*p.y) * (b.x - a.x));
    long long g = std::gcd(std::gcd(std::llabs(ux), std::llabs(uy)), std::llabs(d));
    if (g == 0) g = 1;
    ux /= g; uy /= g; d /= g; return true;
}
using CKey = std::array<long long,3>;
static int b_from_pairs(Pt p, const std::vector<Pt>& S,
                       std::map<CKey, std::set<int>>* groups) {
    std::map<CKey, std::set<int>> g;
    for (size_t i = 0; i < S.size(); ++i) for (size_t j = i+1; j < S.size(); ++j) {
        long long ux, uy, d;
        if (!circle_key(p, S[i], S[j], ux, uy, d)) continue;
        g[{ux,uy,d}].insert((int)i); g[{ux,uy,d}].insert((int)j);
    }
    int tot = 0;
    for (auto& kv : g) { int t = (int)kv.second.size();
        if (t >= 3) tot += t * (t-1) * (t-2) / 6; }
    if (groups) *groups = g;
    return tot;
}
struct RatP { Rat x, y; };
static bool invert_pt(Pt q, RatP& r) {
    long long n = q.x * q.x + q.y * q.y;
    if (n == 0) return false;
    r.x = mk(q.x, n); r.y = mk(q.y, n); return true;
}
static std::vector<std::pair<int,int>> monomials(int deg) {
    std::vector<std::pair<int,int>> m;
    for (int a = 0; a <= deg; ++a) for (int b = 0; a + b <= deg; ++b) m.push_back({a,b});
    return m;
}
static int vander_rank(const std::vector<RatP>& pts, int deg) {
    auto monos = monomials(deg);
    int m = (int)pts.size(), Nn = (int)monos.size();
    std::vector<std::vector<Rat>> A(m, std::vector<Rat>(Nn, {0,1}));
    for (int r = 0; r < m; ++r)
        for (int c = 0; c < Nn; ++c) {
            int a = monos[c].first, b = monos[c].second;
            Rat v{1,1};
            for (int i = 0; i < a; ++i) v = rmul(v, pts[r].x);
            for (int i = 0; i < b; ++i) v = rmul(v, pts[r].y);
            A[r][c] = v;
        }
    int rank = 0;
    for (int col = 0; col < Nn && rank < m; ++col) {
        int sel = -1;
        for (int r = rank; r < m; ++r) if (A[r][col].n != 0) { sel = r; break; }
        if (sel < 0) continue;
        std::swap(A[rank], A[sel]);
        Rat pv = A[rank][col];
        for (int c = 0; c < Nn; ++c) A[rank][c] = mk(A[rank][c].n * pv.d, A[rank][c].d * pv.n);
        for (int r = 0; r < m; ++r) if (r != rank && A[r][col].n != 0) {
            Rat f = A[r][col];
            for (int c = 0; c < Nn; ++c) A[r][c] = rsub(A[r][c], rmul(f, A[rank][c]));
        }
        rank++;
    }
    return rank;
}
struct LKey { long long a, b, c;
    bool operator<(const LKey& o) const { return std::tie(a,b,c) < std::tie(o.a,o.b,o.c); } };
static std::vector<std::pair<LKey, std::vector<int>>> ordinary_lines(const std::vector<RatP>& P) {
    int n = (int)P.size();
    std::map<LKey, std::set<int>> lines;
    for (int i = 0; i < n; ++i) for (int j = i+1; j < n; ++j) {
        Rat a = rsub(P[j].y, P[i].y);
        Rat b = rsub(P[i].x, P[j].x);
        Rat c = mk(-radd(rmul(a, P[i].x), rmul(b, P[i].y)).n,
                   radd(rmul(a, P[i].x), rmul(b, P[i].y)).d);
        long long A = a.n * b.d * c.d, B = b.n * a.d * c.d, C = c.n * a.d * b.d;
        long long g = std::gcd(std::gcd(std::llabs(A), std::llabs(B)), std::llabs(C));
        if (g == 0) g = 1; A /= g; B /= g; C /= g;
        if (std::make_tuple(-A,-B,-C) < std::make_tuple(A,B,C)) { A = -A; B = -B; C = -C; }
        lines[{A,B,C}].insert(i); lines[{A,B,C}].insert(j);
    }
    std::vector<std::pair<LKey, std::vector<int>>> out;
    for (auto& kv : lines) { std::vector<int> m(kv.second.begin(), kv.second.end());
        if (m.size() == 3) out.push_back({kv.first, m}); }
    return out;
}
static int count_collinear(const std::vector<Pt>& S) {
    int c = 0;
    for (size_t a = 0; a < S.size(); ++a) for (size_t b = a+1; b < S.size(); ++b)
    for (size_t d = b+1; d < S.size(); ++d) {
        long long A = S[b].y - S[a].y, B = S[a].x - S[b].x;
        long long C = -(A * S[a].x + B * S[a].y);
        if (A * S[d].x + B * S[d].y + C == 0) ++c;
    }
    return c;
}

// ================================================================== writer
struct Out {
    std::ofstream f; std::ostream* o = &std::cout;
    explicit Out(const std::string& path) { if (!path.empty()) { f.open(path); o = &f; } }
    bool first = true;
    void top(const std::string& k) { if (!first) (*o) << ",\n"; first = false; (*o) << "  \"" << k << "\": "; }
    void done() { (*o) << "\n}\n"; }
};

// ==================================================================== main
int main(int argc, char** argv) {
    std::string outp = argc > 1 ? argv[1] : "";
    Out O(outp);
    *O.o << "{\n";
    double T0 = now_s();

    // ------------------------------------------------------------ A: J_n
    O.top("A_Jn_squares");
    *O.o << "[\n";
    {
        std::vector<std::string> rows;
        for (int n = 2; n <= 5; ++n) {
            double t0 = now_s();
            fprintf(stderr, "[stage A] n=%d start\n", n); fflush(stderr);
            Board b; build_square(b, n);
            Game gm; gm.build(b); gm.grundy(0);
            JN J; J.build(n, n, gm);
            fprintf(stderr, "[stage A] n=%d J built V=%d E=%d states=%zu\n",
                    n, J.V, J.E(), gm.states.size()); fflush(stderr);
            long long pm = J.count_pm();
            fprintf(stderr, "[stage A] n=%d pm=%lld\n", n, pm); fflush(stderr);
            long long nbr = J.n_bridges();
            auto ap = J.arts();
            fprintf(stderr, "[stage A] n=%d bridges=%lld arts=%zu\n", n, nbr, ap.size()); fflush(stderr);
            std::map<int,int> oh, th; int nWin = 0;
            for (int p = 0; p < J.V; ++p) { int gv = gm.grundy(1ULL<<p); oh[gv]++; if (!gv) nWin++; }
            long long nP = 0;
            for (int a = 0; a < J.V; ++a) for (int c = a+1; c < J.V; ++c) {
                int gv = gm.grundy((1ULL<<a)|(1ULL<<c)); th[gv]++; if (!gv) nP++; }
            fprintf(stderr, "[stage A] n=%d two-stone done nP=%lld\n", n, nP); fflush(stderr);
            std::map<std::string,int> porb;
            for (int a = 0; a < J.V; ++a) for (int c = a+1; c < J.V; ++c)
                if (gm.grundy((1ULL<<a)|(1ULL<<c)) == 0) porb[J.d4_type(a,c)]++;
            fprintf(stderr, "[stage A] n=%d d4 done types=%zu\n", n, porb.size()); fflush(stderr);
            bool npm = J.has_near_pm();
            fprintf(stderr, "[stage A] n=%d near_pm=%d\n", n, (int)npm); fflush(stderr);
            auto cc = J.complement();
            std::string comp = "{\"n_components\":" + N(cc.first) + ",\"deg_hist\":" + JN::hist_s(cc.second) + "}";
            // total domination (n<=4 only, exponential but tiny)
            std::string td = "null";
            if (n <= 4) {
                std::vector<std::pair<int,int>> ed;
                for (int a = 0; a < J.V; ++a) for (int c : J.adj[a]) if (a < c) ed.push_back({a,c});
                int E = (int)ed.size();
                std::set<std::pair<int,int>> bestset; int best = 99; long long nmin = 0;
                for (int t = 1; t <= 3 && t < best && t <= E; ++t) {
                    std::vector<std::set<int>> combos;
                    std::function<void(int,int,std::set<int>&)> rec = [&](int s2, int left, std::set<int>& cur) {
                        if (left == 0) { combos.push_back(cur); return; }
                        for (int i = s2; i <= E - left; ++i) {
                            cur.insert(ed[i].first); cur.insert(ed[i].second);
                            rec(i+1, left-1, cur);
                            cur.erase(ed[i].first); cur.erase(ed[i].second); }
                    };
                    std::set<int> cur; rec(0, t, cur);
                    long long cnt = 0;
                    for (auto& S : combos) {
                        bool ok = true;
                        for (auto& e : ed) if (!S.count(e.first) && !S.count(e.second)) { ok = false; break; }
                        if (!ok) continue;
                        std::set<std::pair<int,int>> D;
                        for (auto& s : S) for (auto& e : ed) if (s == e.first || s == e.second) D.insert(e);
                        cnt++;
                        if (best == 99) best = t;
                        if (bestset.empty() || (int)D.size() < (int)bestset.size()) bestset = D;
                    }
                    if (cnt) { nmin = cnt; break; }
                }
                std::set<std::pair<int,int>> P(ed.begin(), ed.end());
                std::map<std::string,int> tdorb;
                for (auto& e : bestset) tdorb[J.d4_type(e.first,e.second)]++;
                bool allP = std::includes(bestset.begin(), bestset.end(), P.begin(), P.end());
                td = std::string("{\"gamma\":") + N(best) + ",\"num_min_sets\":" + N(nmin)
                   + ",\"num_TD_pairs\":" + N((long long)bestset.size())
                   + ",\"all_TD_are_P\":" + (allP ? "true" : "false")
                   + ",\"num_P_pairs\":" + N((long long)P.size())
                   + ",\"n_d4_types_of_TD\":" + N((long long)tdorb.size()) + "}";
            }
            std::string b317 = "null";
            if (pm > 0 && pm <= 200000) {
                fprintf(stderr, "[stage A] n=%d enumerating PMs\n", n); fflush(stderr);
                auto pms = J.enum_pm(200000);
                fprintf(stderr, "[stage A] n=%d %zu PMs, testing breaks\n", n, pms.size()); fflush(stderr);
                int nP = (int)pms.size();
                std::vector<int> nbs(nP, 0);
                #pragma omp parallel for schedule(dynamic)
                for (int pi = 0; pi < nP; ++pi) nbs[pi] = b317_break(b, pms[pi], J.V);
                int nbc = 0, mn = 1<<30, mx = 0;
                for (int v : nbs) { if (v > 0) nbc++; mn = std::min(mn, v); mx = std::max(mx, v); }
                b317 = std::string("{\"n_pm_total\":") + N((long long)pms.size())
                     + ",\"n_pm_breakable\":" + N(nbc)
                     + ",\"all_pm_breakable\":" + (nbc == (long long)pms.size() ? "true" : "false")
                     + ",\"min_breaks\":" + N(mn) + ",\"max_breaks\":" + N(mx) + "}";
            }
            std::string r = "  {\"board\": \"" + N(n) + "x" + N(n)
              + "\", \"V\": " + N(J.V) + ", \"E\": " + N(J.E())
              + ", \"n_states\": " + N((long long)gm.states.size())
              + ", \"g_empty\": " + N(gm.gempty())
              + ", \"n_bridges\": " + N(nbr)
              + ", \"n_articulation_points\": " + N((long long)ap.size())
              + ", \"one_stone_hist\": " + JN::hist_s(oh)
              + ", \"n_one_stone_types\": " + N((long long)oh.size())
              + ", \"two_stone_hist\": " + JN::hist_s(th)
              + ", \"n_P_pairs\": " + N(nP)
              + ", \"n_P_pair_d4_types\": " + N((long long)porb.size())
              + ", \"num_perfect_matchings\": " + N(pm)
              + ", \"has_perfect_matching\": " + (pm > 0 ? "true" : "false")
              + ", \"has_near_perfect_matching\": " + (J.has_near_pm() ? "true" : "false")
              + ", \"n_winning_firsts\": " + N(nWin)
              + ", \"total_domination\": " + td
              + ", \"complement_graph\": " + comp
              + ", \"B317\": " + b317
              + ", \"seconds\": " + F2(now_s() - t0) + "}";
            rows.push_back(r);
            fprintf(stderr, "[stage A] n=%d done in %.1fs\n", n, now_s() - t0); fflush(stderr);
        }
        for (size_t i = 0; i < rows.size(); ++i) *O.o << rows[i] << (i+1 < rows.size() ? ",\n" : "\n");
    }
    *O.o << "]";

    // ----------------------------------------------------- B: B300 trees
    O.top("B300_depth_trees_n4");
    *O.o << "[";
    {
        double t0 = now_s();
        fprintf(stderr, "[stage B] B300 n=4 depth trees\n"); fflush(stderr);
        Board b; build_square(b, 4);
        Game gm; gm.build(b); gm.grundy(0);
        TreeSig ts(gm);
        auto xs = [&](u64 s) { std::string o = "["; bool g = true;
            for (int p = 0; p < 16; ++p) if (s & (1ULL<<p)) { if (!g) o += ","; g = false;
                o += N(p) + "=(" + N(p%4) + "," + N(p/4) + ")"; } return o + "]"; };
        bool f = true;
        for (int d = 1; d <= 2; ++d) {
            std::map<std::string, std::vector<u64>> layers;
            for (u64 s : gm.states) {
                if (gm.pop(s) < 3) continue;
                layers[ts.rec(s, d)].push_back(s);
            }
            long long nsplit = 0, ntot = 0; std::string wit;
            for (auto& kv : layers) {
                bool hasP = false, hasN = false; u64 ps = 0, ns = 0;
                for (u64 s : kv.second) { if (gm.grundy(s) == 0) { hasP = true; ps = s; } else { hasN = true; ns = s; } }
                ++ntot;
                if (hasP && hasN) { ++nsplit;
                    if (wit.empty()) wit = "{\"P\":" + xs(ps) + ",\"g_P\":0,\"N\":" + xs(ns)
                                          + ",\"gN\":" + N(gm.grundy(ns)) + "}"; }
            }
            if (!f) *O.o << ","; f = false;
            *O.o << "\n    {\"d\": " + N(d) + ", \"n_states\": " + N((long long)gm.states.size())
                 + ", \"n_layers\": " + N(ntot) + ", \"n_split_layers\": " + N(nsplit)
                 + ", \"first_witness\": " + (wit.empty() ? "null" : wit) + "}";
        }
        *O.o << "\n  ],\n";
        O.first = true;  // re-set for the standalone section below
        (void)t0;
    }

    // --------------------------------------------- C: B295 literal cover
    {
        O.top("B295_maximal_cover_n4");
        double t0 = now_s();
        fprintf(stderr, "[stage C] B295 maximal cover n=4\n"); fflush(stderr);
        Board b; build_square(b, 4);
        Game gm; gm.build(b); gm.grundy(0);
        std::vector<u64> maxs; enum_maximal(b, maxs, 200000);
        // profile: for each state S with k>=2, the count of t-element maximal
        // supersets for t=0..K.  Layer key = (k, profile).
        std::map<u64, std::vector<u64>> supers;  // S -> maximal supersets
        std::map<std::string, long long> hits;
        std::map<std::string, std::pair<int,int>> wit;
        long long nstates = 0;
        for (u64 s : gm.states) {
            int k = gm.pop(s);
            if (k < 2) continue;
            ++nstates;
            std::map<int, long long> h;
            for (u64 M : maxs) if ((M & s) == s) h[gm.pop(M)]++;
            std::string key = std::to_string(k) + "|";
            for (auto& kv : h) key += std::to_string(kv.first) + ":" + std::to_string(kv.second) + ",";
            int gv = gm.grundy(s);
            auto it = hits.find(key);
            if (it == hits.end()) { hits[key] = 1; wit[key] = {gv, gv}; }
            else { hits[key]++; if (wit[key].first != gv) wit[key].first = 0; }
        }
        long long nsplit = 0;
        for (auto& kv : hits) { if (kv.second > 1 && wit[kv.first].first == 0) ++nsplit; }
        *O.o << "{\"n_maximal_sets\": " << N((long long)maxs.size())
             << ", \"n_states_scanned\": " << N(nstates)
             << ", \"n_layers\": " << N((long long)hits.size())
             << ", \"n_split_layers\": " << N(nsplit)
             << ", \"seconds\": " << F2(now_s() - t0) << "}";
    }

    // ------------------------------------- D: max-b witness inversion
    O.top("D_inversion_maxb_witnesses");
    *O.o << "[";
    {
        // witnesses taken verbatim from round3_chunk6_cover.json max_b_arg
        struct W { int n, k, b, p; std::vector<int> S; };
        std::vector<W> Ws = {
            {5,6,4,3,{0,1,2,5,9,11}},
            {5,7,5,8,{0,1,2,5,11,19,22}},
            {5,8,6,3,{0,1,2,6,10,14,15,23}},
            {5,9,6,18,{0,1,2,9,11,13,15,22,24}},
            {6,8,7,3,{0,1,2,10,12,16,27,33}},
            {6,9,9,3,{0,1,4,9,10,13,18,21,33}},
            {6,10,11,3,{0,1,4,9,10,13,17,18,21,33}},
        };
        bool f = true;
        for (auto& w : Ws) {
            Pt p{w.p % w.n, w.p / w.n};
            std::vector<Pt> S;
            for (int v : w.S) S.push_back({v % w.n, v / w.n});
            std::vector<Pt> all; all.push_back(p); for (auto& s : S) all.push_back(s);
            std::vector<RatP> inv;
            bool okall = true;
            for (auto& q : all) { RatP r; if (!invert_pt(q, r)) okall = false; else inv.push_back(r); }
            int r1 = vander_rank(inv, 1), r2 = vander_rank(inv, 2), r3 = vander_rank(inv, 3);
            int nc = (int)monomials(1).size(), nc2 = (int)monomials(2).size(), nc3 = (int)monomials(3).size();
            auto ol = ordinary_lines(inv);
            std::map<CKey, std::set<int>> groups;
            int bre = b_from_pairs(p, S, &groups);
            std::map<int,int> chist; int ncirc = 0;
            for (auto& kv : groups) { int t = (int)kv.second.size();
                if (t >= 2) { ++ncirc; chist[t]++; } }
            int cheb = 0;
            for (auto& s : S) cheb = std::max(cheb, (int)std::max(std::llabs(s.x - p.x), std::llabs(s.y - p.y)));
            int nc_orig = count_collinear(S);
            if (!f) *O.o << ","; f = false;
            *O.o << "\n    {\"n\": " << N(w.n) << ", \"k\": " << N(w.k) << ", \"b\": " << N(w.b)
                 << ", \"p_xy\": [" << N(p.x) << "," << N(p.y) << "]"
                 << ", \"recomputed_b\": " << N(bre)
                 << ", \"rank_inv_deg1\": " << N(r1) << ", \"ncols_deg1\": " << N(nc)
                 << ", \"rank_inv_deg2\": " << N(r2) << ", \"ncols_deg2\": " << N(nc2)
                 << ", \"rank_inv_deg3\": " << N(r3) << ", \"ncols_deg3\": " << N(nc3)
                 << ", \"n_points\": " << N((long long)all.size())
                 << ", \"n_ordinary_lines_inverted\": " << N((long long)ol.size())
                 << ", \"n_collinear_triples_original\": " << N(nc_orig)
                 << ", \"n_circles_through_p_2plus\": " << N(ncirc)
                 << ", \"circle_size_hist\": " << JN::hist_s(chist)
                 << ", \"chebyshev_p_to_S\": " << N(cheb)
                 << ", \"all_points_invertible\": " << (okall ? "true" : "false") << "}";
        }
        *O.o << "\n  ]";
    }

    // ----------------------------------- E: lattice b_max hill-climb
    O.top("E_lattice_bmax");
    *O.o << "[";
    {
        bool f = true;
        std::mt19937_64 rng(20260927);
        for (int k = 4; k <= 12; ++k) {
            int box = 4 + k / 2;
            int bestb = -1; std::vector<Pt> bestS;
            int restarts = 60;
            for (int r = 0; r < restarts; ++r) {
                std::set<std::pair<long long,long long>> S;
                while ((int)S.size() < k) {
                    long long x = (long long)(rng() % (2*box+1)) - box;
                    long long y = (long long)(rng() % (2*box+1)) - box;
                    if (x == 0 && y == 0) continue;
                    S.insert(std::make_pair(x,y));
                }
                std::vector<Pt> cur;
                for (auto& pr : S) cur.push_back(Pt{pr.first, pr.second});
                int cb = b_from_pairs({0,0}, cur, nullptr);
                bool improved = true;
                while (improved) { improved = false;
                    for (size_t i = 0; i < cur.size(); ++i) {
                        for (int dx = -2; dx <= 2; ++dx) for (int dy = -2; dy <= 2; ++dy) {
                            if (!dx && !dy) continue;
                            long long nx = cur[i].x + dx, ny = cur[i].y + dy;
                            if (nx == 0 && ny == 0) continue;
                            std::vector<Pt> nw = cur;
                            nw[i] = {nx, ny};
                            std::sort(nw.begin(), nw.end());
                            nw.erase(std::unique(nw.begin(), nw.end(),
                                [](const Pt&a, const Pt&b){ return a.x==b.x && a.y==b.y; }), nw.end());
                            if ((int)nw.size() != k) continue;
                            int v = b_from_pairs({0,0}, nw, nullptr);
                            if (v > cb) { cur = nw; cb = v; improved = true; }
                        } } }
                if (cb > bestb) { bestb = cb; bestS = cur; }
            }
            long long Ck2 = (long long)k * (k - 1) / 2;
            long long delta = Ck2 - 3LL * bestb;
            long long t3 = (long long)k * (k - 3) / 6 + 1;
            if (!f) *O.o << ","; f = false;
            *O.o << "\n    {\"k\": " << N(k) << ", \"box\": " << N(box)
                 << ", \"b_max_found\": " << N(bestb) << ", \"delta\": " << N(delta)
                 << ", \"delta_over_k\": " << F2((double)delta / k)
                 << ", \"delta_over_k2\": " << F2((double)delta / ((double)k*k))
                 << ", \"b_over_k2\": " << F2((double)bestb / ((double)k*k))
                 << ", \"real_orchard_t3\": " << N(t3)
                 << ", \"gap_to_real\": " << N(t3 - bestb) << "}";
        }
        *O.o << "\n  ]";
    }
    O.done();
    return 0;
}
