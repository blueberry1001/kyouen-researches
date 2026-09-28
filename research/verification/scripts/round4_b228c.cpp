// Round4, batch B228-B290, pass 2.
//
//   sec_lp     : conic-capacity LP, exact rational optimum (int128 rational
//                simplex) + explicit dual certificate  -> B288 / B289 / B290
//   sec_graph  : residual-graph R(S) realisation census -> B232 / B233
//   sec_corr   : proof size vs repeated isomorphic components of R(S) (n=4)
//                -> B245
//   sec_ng     : n=4,5 grundy + minimal AND/OR proof size by legal-count level
//                (g=1 focus) -> B249 pass 2 / B247 supporting data
//   sec_relax  : |det| <= t relaxed rule, D4 orbit structure of maximal sets
//                -> B229
//
// Integer arithmetic only; every rational value is printed as exact "p/q".
#include "kc_core.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>
#include <map>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

using namespace kc;
typedef __int128 i128;

static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

// ---------------------------------------------------------- exact rational -
struct Q {
    i128 n = 0, d = 1;
    Q() {}
    Q(i128 a) : n(a), d(1) {}                       // integer, already normalised
    Q(i128 a, i128 b) : n(a), d(b) { norm(); }       // always normalises
    void norm() {
        if (d == 0) { d = 1; return; }
        if (d < 0) { n = -n; d = -d; }
        if (n == 0) { d = 1; return; }
        i128 a = n < 0 ? -n : n, b = d;
        while (b) { i128 t = a % b; a = b; b = t; }
        if (a == 0) { n = 0; d = 1; return; }
        n /= a; d /= a;
    }
    friend Q operator+(const Q& a, const Q& b) { return Q(a.n * b.d + b.n * a.d, a.d * b.d); }
    friend Q operator-(const Q& a, const Q& b) { return Q(a.n * b.d - b.n * a.d, a.d * b.d); }
    friend Q operator*(const Q& a, const Q& b) { return Q(a.n * b.n, a.d * b.d); }
    friend Q operator/(const Q& a, const Q& b) { return Q(a.n * b.d, a.d * b.n); }
    bool operator<(const Q& o) const { return n * o.d < o.n * d; }
    bool operator==(const Q& o) const { return n == o.n && d == o.d; }
    bool is_zero() const { return n == 0; }
};
// integer construction (d == 1, already normalised)
static inline Q Qi(i128 a) { Q q; q.n = a; q.d = 1; return q; }
static std::string qs(const Q& q) {
    char buf[128];
    long long a = (long long)q.n, b = (long long)q.d;
    snprintf(buf, sizeof buf, "%lld/%lld", a, b);
    return std::string(buf);
}

// ---------------------------------------------------------------- conics ---
static std::array<long long, 6> conic4(int x1, int y1, int x2, int y2,
                                        int x3, int y3, int x4, int y4) {
    long long M[4][6];
    const int xs[4] = {x1, x2, x3, x4};
    const int ys[4] = {y1, y2, y3, y4};
    for (int i = 0; i < 4; i++) {
        M[i][0] = (long long)xs[i] * xs[i];
        M[i][1] = (long long)xs[i] * ys[i];
        M[i][2] = (long long)ys[i] * ys[i];
        M[i][3] = xs[i];
        M[i][4] = ys[i];
        M[i][5] = 1;
    }
    std::array<long long, 6> v{};
    for (int j = 0; j < 6; j++) {
        // cofactor of M[0][j]: drop row 0 and column j, then sign (-1)^j
        long long r[3][3];
        int ri = 0;
        for (int i = 1; i < 4; i++) {
            int ci = 0;
            for (int j2 = 0; j2 < 6; j2++) {
                if (j2 == j) continue;
                r[ri][ci++] = M[i][j2];
            }
            ri++;
        }
        long long d = r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
                   - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
                   + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]);
        v[j] = (j % 2 == 0) ? d : -d;
    }
    long long g = 0;
    for (int j = 0; j < 6; j++) { long long a = v[j] < 0 ? -v[j] : v[j]; while (a) { long long t = g % a; g = a; a = t; } }
    if (g == 0) g = 1;
    for (int j = 0; j < 6; j++) v[j] /= g;
    for (int j = 0; j < 6; j++)
        if (v[j] != 0) { if (v[j] < 0) for (int k = 0; k < 6; k++) v[k] = -v[k]; break; }
    return v;
}

struct ConicInfo { std::array<long long, 6> c; u64 pts = 0; int nb = 0; bool is_line = false; };

static void build_conics(const Board& b, std::vector<ConicInfo>& out) {
    std::map<std::array<long long, 6>, u64> m;
    for (u64 q : b.quads) {
        int id[4], k = 0;
        u64 t = q;
        while (t) { id[k++] = __builtin_ctzll(t); t &= t - 1; }
        auto c = conic4(b.pt_x[id[0]], b.pt_y[id[0]], b.pt_x[id[1]], b.pt_y[id[1]],
                        b.pt_x[id[2]], b.pt_y[id[2]], b.pt_x[id[3]], b.pt_y[id[3]]);
        m[c] |= q;
    }
    for (auto& kv : m) {
        ConicInfo ci;
        ci.c = kv.first;
        ci.is_line = (kv.first[0] == 0 && kv.first[1] == 0 && kv.first[2] == 0);
        for (int p = 0; p < b.V; p++) {
            i128 x = b.pt_x[p], y = b.pt_y[p];
            const long long* c = ci.c.data();
            i128 val = (i128)c[0] * x * x + (i128)c[1] * x * y + (i128)c[2] * y * y
                     + (i128)c[3] * x + (i128)c[4] * y + (i128)c[5];
            if (val == 0) ci.pts |= u64(1) << p;
        }
        ci.nb = __builtin_popcountll(ci.pts);
        out.push_back(ci);
    }
}

// ------------------------------------------------------------ exact LP -----
// maximise sum x_p over  A x <= b, 0 <= x <= 1.  Exact rational simplex,
// returns the optimal objective value and a dual certificate y >= 0 with
// A^T y = 1, b^T y = opt  (i.e. the row combination proving the bound).
struct LPResult { bool ok = false; Q opt; std::vector<Q> dual; Q dual_value; long long pivots = 0; };

static LPResult lp_max(const std::vector<std::vector<long long>>& A,
                       const std::vector<long long>& b,
                       const std::vector<long long>& obj, long long max_pivots) {
    LPResult R;
    int m = (int)b.size(), n = (int)obj.size(), N = n + m;
    for (int i = 0; i < m; i++) if (b[i] < 0) return R;
    std::vector<int> B(m);
    std::vector<char> isN(N, 1);
    for (int i = 0; i < m; i++) { B[i] = n + i; isN[n + i] = 0; }
    std::vector<std::vector<Q>> T(m, std::vector<Q>(N + 1));
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) T[i][j] = Q(A[i][j]);
        T[i][N] = Q(b[i]);
    }
    long long iters = 0;
    while (true) {
        if (++iters > max_pivots) return R;
        int piv = -1;
        for (int v = 0; v < N && piv < 0; v++) {
            if (!isN[v]) continue;
            // z_v = c_v - sum_i c_{B_i} * T_iv     (slack columns have c = 0)
            Q z = Qi((i128)obj[v]);
            for (int i = 0; i < m; i++) {
                if (B[i] >= n) continue;
                if (T[i][v].is_zero()) continue;
                z = z - Q((i128)obj[B[i]]) * T[i][v];
            }
            if (z.n > 0) piv = v;
        }
        if (piv < 0) break;
        int r = -1; Q best;
        for (int i = 0; i < m; i++) {
            if (T[i][piv].n <= 0) continue;
            Q cand = T[i][N] / T[i][piv];
            if (r < 0 || cand < best || (cand == best && B[i] < B[r])) { r = i; best = cand; }
        }
        if (r < 0) return R;   // unbounded (impossible for a covering LP)
        Q p = T[r][piv];
        for (int j = 0; j <= N; j++) T[r][j] = T[r][j] / p;
        for (int i = 0; i < m; i++) {
            if (i == r || T[i][piv].is_zero()) continue;
            Q f = T[i][piv];
            for (int j = 0; j <= N; j++) T[i][j] = T[i][j] - f * T[r][j];
        }
        isN[B[r]] = 1; isN[piv] = 0; B[r] = piv;
    }
    R.pivots = iters;
    // primal objective
    Q opt(0);
    for (int i = 0; i < m; i++)
        if (B[i] < n && !T[i][N].is_zero()) opt = opt + Q((i128)obj[B[i]]) * T[i][N];
    // Certificate: y := sum_i lam_i A_i, keeping y <= obj.  Then for any
    // feasible x >= 0, sum_j obj_j x_j >= sum_j y_j x_j = sum_i lam_i (A x)_i
    // <= sum_i lam_i b_i, so sum_i lam_i b_i is a self-contained upper bound.
    std::vector<Q> lam(m, Q(0));
    std::vector<Q> resid(n, Q(0));
    for (int j = 0; j < n; j++) resid[j] = Qi((i128)obj[j]);
    Q bound(0);
    for (int step = 0; step <= n + 1; step++) {
        int best = -1; Q alpha; bool have = false;
        for (int i = 0; i < m; i++) {
            if (!lam[i].is_zero()) continue;
            Q a; bool first = true;
            for (int j = 0; j < n; j++) {
                if (A[i][j] <= 0 || resid[j].n <= 0) continue;
                Q cand = resid[j] / Qi((i128)A[i][j]);
                if (first || cand < a) { a = cand; first = false; }
            }
            if (first) continue;
            if (!have || a < alpha) { alpha = a; best = i; have = true; }
        }
        if (!have || alpha.n == 0) break;
        lam[best] = alpha;
        for (int j = 0; j < n; j++)
            if (A[best][j] != 0)
                resid[j] = resid[j] - Q(alpha.n * (i128)A[best][j], alpha.d);
        bound = bound + Q(alpha.n * (i128)b[best], alpha.d);
    }
    R.ok = true;
    R.opt = opt;
    R.dual = lam;
    R.dual_value = bound;
    return R;
}

// -------------------------------------------------------------- sec_lp -----
static void sec_lp() {
    printf("  \"lp\": {\n");
    const int Kknown[8] = {0, 0, 3, 5, 7, 9, 11, 14};
    for (int n : {3, 4, 5, 6, 7}) {
        Board b; build_square(b, n);
        std::vector<ConicInfo> cons; build_conics(b, cons);
        int by4 = 0, by5 = 0, by6 = 0, by7p = 0, lines = 0, circs = 0, minnb = 99;
        for (auto& ci : cons) {
            minnb = std::min(minnb, ci.nb);
            if (ci.nb == 4) by4++;
            else if (ci.nb == 5) by5++;
            else if (ci.nb == 6) by6++;
            else if (ci.nb >= 7) by7p++;
            if (ci.is_line) lines++; else circs++;
        }
        printf("  \"n%d\": {\"V\": %d, \"quads\": %d, \"conics\": %d, \"lines\": %d, "
               "\"circles\": %d, \"conic_nb4\": %d, \"conic_nb5\": %d, \"conic_nb6\": %d, "
               "\"conic_nb_ge7\": %d, \"conic_min_nb\": %d, ",
               n, b.V, (int)b.quads.size(), (int)cons.size(), lines, circs,
               by4, by5, by6, by7p, minnb);

        std::vector<std::vector<long long>> A;
        std::vector<long long> bb, cc(b.V, 1);
        std::vector<std::string> tag;
        for (int i = 0; i < b.V; i++) {
            std::vector<long long> row(b.V, 0); row[i] = 1;
            A.push_back(row); bb.push_back(1); tag.push_back("unit");
        }
        int nconic = 0;
        for (int i = 0; i < (int)cons.size(); i++) if (cons[i].nb >= 5) {
            std::vector<long long> row(b.V, 0);
            u64 t = cons[i].pts;
            while (t) { int p = __builtin_ctzll(t); t &= t - 1; row[p] = 1; }
            A.push_back(row); bb.push_back(3); tag.push_back("conic"); nconic++;
        }
        LPResult r1 = lp_max(A, bb, cc, 20000);
        int nnz1 = 0; for (auto& l : r1.dual) if (!l.is_zero()) nnz1++;
        printf("\"lp_rows\": %d, \"conic_rows\": %d, \"pivots\": %lld, \"lp_ok\": %s, ",
               (int)A.size(), nconic, r1.pivots, r1.ok ? "true" : "false");
        if (r1.ok)
            printf("\"lp_opt\": \"%s\", \"cert_bound\": \"%s\", \"cert_support\": %d, ",
                   qs(r1.opt).c_str(), qs(r1.dual_value).c_str(), nnz1);
        printf("\"K_known\": %d, ", Kknown[n]);

        // strengthening family (B290): conic-pencil cuts.  Only conics with
        // >= 5 board points can form a useful pair cut (the base rows already
        // carry the nb==4 ones), which keeps n=6,7 tractable.
        int npair = 0, ntri = 0;
        std::vector<std::vector<long long>> A2 = A;
        std::vector<long long> b2 = bb;
        std::vector<std::string> t2 = tag;
        for (int i = 0; i < (int)cons.size(); i++) {
            if (cons[i].nb < 5) continue;
            for (int j = i + 1; j < (int)cons.size(); j++) {
                if (cons[j].nb < 5) continue;
                u64 inter = cons[i].pts & cons[j].pts;
                if (__builtin_popcountll(inter) > 4) continue;
                u64 uni = cons[i].pts | cons[j].pts;
                if (__builtin_popcountll(uni) < 7) continue;
                std::vector<long long> row(b.V, 0);
                u64 z = uni; while (z) { int p = __builtin_ctzll(z); z &= z - 1; row[p] = 1; }
                z = inter; while (z) { int p = __builtin_ctzll(z); z &= z - 1; row[p] = 2; }
                A2.push_back(row); b2.push_back(6); t2.push_back("pair"); npair++;
            }
        }
        for (int i = 0; i < (int)cons.size() && ntri < 2000; i++) {
            if (cons[i].nb < 5) continue;
            for (int j = i + 1; j < (int)cons.size() && ntri < 2000; j++) {
                if (cons[j].nb < 5) continue;
                u64 T = cons[i].pts & cons[j].pts;
                if (__builtin_popcountll(T) != 4) continue;
                for (int k = j + 1; k < (int)cons.size() && ntri < 2000; k++) {
                    if (cons[k].nb < 5) continue;
                    if ((cons[k].pts & T) != T) continue;
                    if ((cons[k].pts & cons[i].pts) != T) continue;
                    if ((cons[k].pts & cons[j].pts) != T) continue;
                    u64 U = cons[i].pts | cons[j].pts | cons[k].pts;
                    std::vector<long long> row(b.V, 0);
                    u64 z = U; while (z) { int p = __builtin_ctzll(z); z &= z - 1; row[p] = 1; }
                    z = T; while (z) { int p = __builtin_ctzll(z); z &= z - 1; row[p] = 3; }
                    A2.push_back(row); b2.push_back(9); t2.push_back("triple"); ntri++;
                }
            }
        }
        printf("\"cut_pair\": %d, \"cut_triple\": %d, ", npair, ntri);
        LPResult r2 = lp_max(A2, b2, cc, 20000);
        if (r2.ok) {
            int nnz2 = 0, nc = 0, np = 0, nt = 0, nu = 0;
            for (size_t i = 0; i < r2.dual.size(); i++) {
                if (r2.dual[i].is_zero()) continue;
                nnz2++;
                if (t2[i] == "conic") nc++;
                else if (t2[i] == "pair") np++;
                else if (t2[i] == "triple") nt++;
                else nu++;
            }
            printf("\"lp_cut_opt\": \"%s\", \"cut_cert_bound\": \"%s\", \"cut_cert_support\": %d, "
                   "\"cert_types_unit\": %d, \"cert_types_conic\": %d, "
                   "\"cert_types_pair\": %d, \"cert_types_triple\": %d, ",
                   qs(r2.opt).c_str(), qs(r2.dual_value).c_str(), nnz2, nu, nc, np, nt);
        } else printf("\"lp_cut_opt\": null, ");
        printf("},\n");
        fflush(stdout);
    }
    printf("  },\n");
}

// ---------------------------------------------------------- sec_graph -----
static std::string rooted_code(int v, int par, const std::vector<std::vector<int>>& g) {
    std::vector<std::string> kids;
    for (int w : g[v]) if (w != par) kids.push_back(rooted_code(w, v, g));
    std::sort(kids.begin(), kids.end());
    std::string s = "(";
    for (auto& k : kids) s += k;
    return s + ")";
}
static std::string tree_code(const std::vector<std::vector<int>>& g) {
    if (g.empty()) return "EMPTY";
    std::string best;
    for (size_t v = 0; v < g.size(); v++) {
        std::string s = rooted_code((int)v, -1, g);
        if (best.empty() || s < best) best = s;
    }
    return best;
}
static int nedges(const std::vector<std::vector<int>>& g) {
    int e = 0; for (auto& v : g) e += (int)v.size(); return e / 2;
}
static std::string graph_code_small(const std::vector<std::vector<int>>& g) {
    int k = (int)g.size();
    if (k == 0) return "EMPTY";
    if (k == 1) return "SINGLE";
    if (k == 2) return g[0][0] ? "EDGE" : "TWONONEDGE";
    if (k == 3) return nedges(g) == 3 ? "TRI" : (nedges(g) == 2 ? "PATH3" : "NONEDGE3");
    if (k == 4) {
        int e = nedges(g);
        if (e == 0) return "4IND";
        if (e == 1) return "EDGE+2IND";
        if (e == 2) return "PATHD+IND";
        if (e == 3) {  // star vs path
            int mx = 0; for (auto& v : g) mx = std::max(mx, (int)v.size());
            return mx == 3 ? "STAR4" : "PATH4";
        }
        if (e == 4) return "C4";
        return "TRI+ISO";
    }
    return "BIG" + std::to_string(k) + "_" + std::to_string(nedges(g));
}
static void decode_prufer(std::vector<int>& code, std::vector<std::vector<int>>& g) {
    int n = (int)code.size() + 2;
    g.assign(n, {});
    std::vector<int> deg(n, 1);
    for (int v : code) deg[v]++;
    std::vector<int> used(n, 0);
    for (int v : code) {
        int l = -1;
        for (int i = 0; i < n; i++) if (!used[i] && deg[i] == 1) { l = i; break; }
        g[l].push_back(v); g[v].push_back(l);
        used[l] = 1; deg[l]--; deg[v]--;
    }
    int u = -1, w = -1;
    for (int i = 0; i < n; i++) if (!used[i]) { if (u < 0) u = i; else w = i; }
    g[u].push_back(w); g[w].push_back(u);
    for (auto& r : g) std::sort(r.begin(), r.end());
}
static std::vector<std::string> all_tree_codes(int n) {
    std::vector<std::string> out;
    if (n == 1) { out.push_back("()"); return out; }
    std::vector<int> code(n - 2, 0);
    long long total = 1; for (int i = 0; i < n - 2; i++) total *= n;
    for (long long v = 0; v < total; v++) {
        long long t = v;
        for (int i = 0; i < n - 2; i++) { code[i] = (int)(t % n); t /= n; }
        std::vector<std::vector<int>> g;
        decode_prufer(code, g);
        out.push_back(tree_code(g));
    }
    std::sort(out.begin(), out.end());
    out.erase(std::unique(out.begin(), out.end()), out.end());
    return out;
}
static void residual_graph(const Board& b, u64 S, u64 legal, std::vector<std::vector<int>>& g) {
    std::vector<int> idx; idx.reserve(b.V);
    u64 t = legal; while (t) { idx.push_back(__builtin_ctzll(t)); t &= t - 1; }
    g.assign(idx.size(), {});
    std::map<int, int> loc;
    for (size_t i = 0; i < idx.size(); i++) loc[idx[i]] = (int)i;
    for (u64 q : b.quads) {
        if (__builtin_popcountll(q & S) != 2) continue;
        u64 rest = q & legal;
        if (__builtin_popcountll(rest) != 2) continue;
        int a = __builtin_ctzll(rest); rest &= rest - 1;
        int c = __builtin_ctzll(rest);
        g[loc[a]].push_back(loc[c]); g[loc[c]].push_back(loc[a]);
    }
    for (auto& v : g) std::sort(v.begin(), v.end());
}
static bool is_tree(const std::vector<std::vector<int>>& g) {
    int V = (int)g.size(); if (V == 0) return false;
    if (nedges(g) != V - 1) return false;
    std::vector<int> seen(V, 0); std::vector<int> st{0}; seen[0] = 1; int c = 0;
    while (!st.empty()) { int v = st.back(); st.pop_back(); c++; for (int w : g[v]) if (!seen[w]) { seen[w] = 1; st.push_back(w); } }
    return c == V;
}
static void sec_graph() {
    printf("  \"graph\": {\n");
    std::vector<std::set<std::string>> trees(9);
    for (int k = 1; k <= 7; k++) for (auto& s : all_tree_codes(k)) trees[k].insert(s);
    printf("  \"n_trees\": {");
    for (int k = 1; k <= 7; k++) printf("\"%d\": %d, ", k, (int)trees[k].size());
    printf("},\n");
    for (int n : {3, 4, 5}) {
        Board b; build_square(b, n);
        long long cap = (n == 5) ? 3000000ull : 0;   // 0 = unlimited
        std::map<int, long long> nsafe_by_L;
        std::map<int, std::set<std::string>> treefound;
        std::set<std::string> gtypes[9];
        long long total = 0, visited = 0;
        double t0 = now_s();
        std::vector<std::pair<u64, u64>> stack;
        stack.push_back({0, b.full});
        while (!stack.empty()) {
            auto cur = stack.back(); stack.pop_back();
            u64 S = cur.first, legal = cur.second;
            visited++; total++;
            if (cap && visited > cap) break;
            int nl = __builtin_popcountll(legal);
            if (nl >= 1 && nl <= 6) {
                nsafe_by_L[nl]++;
                std::vector<std::vector<int>> g;
                residual_graph(b, S, legal, g);
                if (is_tree(g)) treefound[nl].insert(tree_code(g));
                if (nl <= 6) gtypes[nl].insert(graph_code_small(g));
            }
            if (n == 5 && __builtin_popcountll(S) >= 5) continue;
            u64 t = legal;
            while (t) {
                int p = __builtin_ctzll(t); t &= t - 1;
                u64 nf = 0;
                for (u64 q : b.quads) {
                    if (!(q & (u64(1) << p))) continue;
                    if ((q & ~(u64(1) << p) & ~S) != 0) continue;
                    nf |= q & ~(u64(1) << p);
                }
                stack.push_back({S | (u64(1) << p), legal & ~(u64(1) << p) & ~nf});
            }
        }
        printf("  \"n%d\": {\"quads\": %d, \"safe_sets_visited\": %lld, \"secs\": %.1f, ",
               n, (int)b.quads.size(), total, now_s() - t0);
        printf("\"safe_by_legal_count\": {");
        for (auto& kv : nsafe_by_L) printf("\"%d\": %lld, ", kv.first, kv.second);
        printf("}, \"trees\": [");
        for (int k = 1; k <= 6; k++) {
            int miss = 0;
            for (auto& s : trees[k]) if (!treefound[k].count(s)) miss++;
            printf("%s{\"k\": %d, \"found\": %d, \"total_trees\": %d, \"missing\": %d}",
                   k == 1 ? "" : ", ", k, (int)treefound[k].size(), (int)trees[k].size(), miss);
        }
        printf("], \"distinct_graph_types\": {");
        for (int k = 1; k <= 6; k++) printf("\"%d\": %d, ", k, (int)gtypes[k].size());
        printf("}, \"graph_types_by_k\": {");
        for (int k = 1; k <= 4; k++) {
            printf("\"%d\": [", k);
            bool f = true;
            for (auto& s : gtypes[k]) { printf("%s\"%s\"", f ? "" : ", ", s.c_str()); f = false; }
            printf("], ");
        }
        printf("}}},\n");
        fflush(stdout);
    }
    printf("  },\n");
}

// --------------------------------------------------------- sec_corr -------
static void sec_corr() {
    int n = 4;
    Board b; build_square(b, n);
    std::vector<u64> states{0};
    for (size_t i = 0; i < states.size(); i++) {
        u64 S = states[i], legal = legal_mask(b, S);
        u64 t = legal;
        while (t) { int p = __builtin_ctzll(t); t &= t - 1; states.push_back(S | (u64(1) << p)); }
    }
    std::sort(states.begin(), states.end(), [](u64 a, u64 c) {
        int pa = __builtin_popcountll(a), pc = __builtin_popcountll(c);
        return pa != pc ? pa < pc : a < c; });
    std::unordered_map<u64, int> G, PS;
    for (int i = (int)states.size() - 1; i >= 0; i--) {
        u64 S = states[i];
        u64 legal = legal_mask(b, S);
        if (legal == 0) { G[S] = 0; PS[S] = 0; continue; }
        int ps = 1 << 28;
        std::set<int> vs;
        for (u64 t = legal; t;) { int p = __builtin_ctzll(t); t &= t - 1; u64 nS = S | (u64(1) << p);
            ps = std::min(ps, 1 + PS[nS]); vs.insert(G[nS]); }
        PS[S] = ps;
        int g = 0; while (vs.count(g)) g++;
        G[S] = g;
    }
    // contingency (nwin, repeat-isomorphic-components) -> (count, sum proof)
    std::map<std::pair<int, int>, std::pair<long long, long long>> tab;
    int wit = -1, wit_rep = -1, wit_proof = -1, wit_nwin = -1;
    for (u64 S : states) {
        if (G[S] == 0) continue;
        u64 legal = legal_mask(b, S);
        int nwin = 0;
        for (u64 t = legal; t;) { int p = __builtin_ctzll(t); t &= t - 1; if (G[S | (u64(1) << p)] == 0) nwin++; }
        if (nwin == 0) continue;
        std::vector<std::vector<int>> g;
        residual_graph(b, S, legal, g);
        int V = (int)g.size(); std::vector<int> seen(V, 0);
        std::vector<std::string> codes;
        for (int v = 0; v < V; v++) if (!seen[v]) {
            std::vector<int> comp, st{v}; seen[v] = 1;
            while (!st.empty()) { int x = st.back(); st.pop_back(); comp.push_back(x);
                for (int y : g[x]) if (!seen[y]) { seen[y] = 1; st.push_back(y); } }
            std::vector<std::vector<int>> sub(comp.size());
            std::map<int, int> loc; for (size_t i = 0; i < comp.size(); i++) loc[comp[i]] = (int)i;
            for (size_t i = 0; i < comp.size(); i++) for (int y : g[comp[i]]) sub[loc[y]].push_back(y);
            for (auto& s : sub) std::sort(s.begin(), s.end());
            codes.push_back(graph_code_small(sub));
        }
        std::map<std::string, int> cnt; for (auto& c : codes) cnt[c]++;
        int rep = 0; for (auto& kv : cnt) rep += kv.second - 1;
        auto& e = tab[{nwin, rep}];
        e.first++; e.second += PS[S];
        if (rep >= 2 && wit < 0) { wit = (int)S; wit_rep = rep; wit_proof = PS[S]; wit_nwin = nwin; }
    }
    printf("  \"corr\": {\"n\": 4, \"states\": %d, \"table\": [", (int)states.size());
    bool first = true;
    for (auto& kv : tab)
        printf("%s{\"nwin\": %d, \"repeat_comp\": %d, \"count\": %lld, \"sum_proof\": %lld, \"mean_proof\": \"%lld/%lld\"}",
               first ? "" : ", ", kv.first.first, kv.first.second, kv.second.first,
               kv.second.second, kv.second.second, (long long)kv.second.first), first = false;
    printf("], \"witness_S\": %d, \"witness_nwin\": %d, \"witness_repeat\": %d, \"witness_proof\": %d},\n",
           wit, wit_nwin, wit_rep, wit_proof);
}

// ---------------------------------------------------------- sec_ng --------
static void sec_ng() {
    printf("  \"ng\": {\n");
    for (int n : {4, 5}) {
        Board b; build_square(b, n);
        std::vector<u64> states{0};
        for (size_t i = 0; i < states.size(); i++) {
            u64 S = states[i], legal = legal_mask(b, S);
            u64 t = legal;
            while (t) { int p = __builtin_ctzll(t); t &= t - 1; states.push_back(S | (u64(1) << p)); }
        }
        std::sort(states.begin(), states.end());
        std::unordered_map<u64, int> G, PS;
        for (int i = (int)states.size() - 1; i >= 0; i--) {
            u64 S = states[i];
            u64 legal = legal_mask(b, S);
            if (legal == 0) { G[S] = 0; PS[S] = 0; continue; }
            int ps = 1 << 28; std::set<int> vs;
            for (u64 t = legal; t;) { int p = __builtin_ctzll(t); t &= t - 1; u64 nS = S | (u64(1) << p);
                ps = std::min(ps, 1 + PS[nS]); vs.insert(G[nS]); }
            PS[S] = ps;
            int g = 0; while (vs.count(g)) g++;
            G[S] = g;
        }
        std::map<int, std::array<long long, 3>> lvl;
        long long ng1 = 0, maxlegal1 = 0, maxproof1 = 0, maxg = 0, maxgS = -1;
        for (u64 S : states) {
            if (G[S] > maxg) { maxg = G[S]; maxgS = (long long)S; }
            if (G[S] != 1) continue;
            ng1++;
            int d = __builtin_popcountll(legal_mask(b, S));
            maxlegal1 = std::max<long long>(maxlegal1, d);
            maxproof1 = std::max<long long>(maxproof1, PS[S]);
            auto& a = lvl[d];
            a[0]++; a[1] += PS[S]; a[2] = std::max(a[2], (long long)PS[S]);
        }
        printf("  \"n%d\": {\"states\": %d, \"max_g\": %d, \"max_g_stones\": %lld, "
               "\"g1_positions\": %lld, \"g1_max_legal\": %lld, \"g1_max_proof\": %lld, \"g1_by_legal\": [",
               n, (int)states.size(), maxg, (long long)__builtin_popcountll((u64)maxgS), ng1, maxlegal1, maxproof1);
        bool f = true;
        for (auto& kv : lvl)
            printf("%s{\"legal\": %d, \"count\": %lld, \"sum_proof\": %lld, \"max_proof\": %lld}",
                   f ? "" : ", ", kv.first, kv.second[0], kv.second[1], kv.second[2]);
        printf("]},\n");
        fflush(stdout);
    }
    printf("  },\n");
}

// -------------------------------------------------------- sec_relax --------
static void sec_relax() {
    printf("  \"relax\": {\n");
    int n = 4;
    Board b; build_square(b, n);
    std::vector<std::pair<long long, u64>> all;
    for (int a = 0; a < b.V; a++) for (int c1 = a + 1; c1 < b.V; c1++)
        for (int c2 = c1 + 1; c2 < b.V; c2++) for (int d = c2 + 1; d < b.V; d++) {
            int id[4] = {a, c1, c2, d};
            long long m[4][4];
            for (int i = 0; i < 4; i++)
                for (int j = 0; j < 4; j++)
                    m[i][j] = (j == 0) ? (long long)b.pt_x[id[i]] * b.pt_x[id[i]] + (long long)b.pt_y[id[i]] * b.pt_y[id[i]]
                           : (j == 1) ? b.pt_x[id[i]] : (j == 2) ? b.pt_y[id[i]] : 1;
            u64 q = 0; for (int i = 0; i < 4; i++) q |= u64(1) << id[i];
            long long dv = det4(m);
            all.push_back({dv < 0 ? -dv : dv, q});
        }
    long long maxd = 0; for (auto& p : all) maxd = std::max(maxd, p.first);
    std::map<long long, int> hist;
    for (auto& p : all) hist[p.first]++;
    printf("  \"n%d\": {\"max_abs_det\": %lld, \"det_histogram\": [", n, maxd);
    {
        bool f = true; int shown = 0;
        for (auto& kv : hist) {
            if (shown++ > 25) { printf("..."); break; }
            printf("%s{\"absdet\": %lld, \"count\": %d}", f ? "" : ", ", kv.first, kv.second);
            f = false;
        }
    }
    printf("], \"rows\": [");
    for (long long t = 0; t <= 3; t++) {
        Board r; r.n = n; r.V = b.V; r.full = b.full;
        r.pt_x = b.pt_x; r.pt_y = b.pt_y;
        r.triples_by_pt.assign(b.V, {});
        r.quads.clear();
        for (auto& p : all) if (p.first <= t) {
            r.quads.push_back(p.second);
            u64 q = p.second;
            for (int s = 0; s < 4; s++) {
                int id = __builtin_ctzll(q); q &= q - 1;
                u64 o = 0, tt = p.second & ~(u64(1) << id);
                while (tt) { int z = __builtin_ctzll(tt); tt &= tt - 1; o |= u64(1) << z; }
                r.triples_by_pt[id].push_back(o);
            }
        }
        std::vector<u64> states{0};
        for (size_t i = 0; i < states.size(); i++) {
            u64 S = states[i], legal = legal_mask(r, S);
            u64 tt = legal; while (tt) { int p = __builtin_ctzll(tt); tt &= tt - 1; states.push_back(S | (u64(1) << p)); }
        }
        std::unordered_map<u64, int> G;
        std::sort(states.begin(), states.end(), [](u64 a, u64 c) {
            int pa = __builtin_popcountll(a), pc = __builtin_popcountll(c);
            return pa != pc ? pa < pc : a < c; });
        for (int i = (int)states.size() - 1; i >= 0; i--) {
            u64 S = states[i]; std::set<int> vs; u64 tt = legal_mask(r, S);
            while (tt) { int p = __builtin_ctzll(tt); tt &= tt - 1; vs.insert(G[S | (u64(1) << p)]); }
            int g = 0; while (vs.count(g)) g++; G[S] = g;
        }
        long long nmax = 0; int K = 0; long long nmax_k = 0;
        int m1 = n - 1;
        std::set<u64> orbits, orbits_maxsize;
        for (u64 S : states) if (legal_mask(r, S) == 0) {
            nmax++; int s = __builtin_popcountll(S);
            K = std::max(K, s);
            u64 canon = S; bool first = true;
            for (int k = 0; k < 8; k++) {
                u64 d = 0;
                for (int p = 0; p < b.V; p++) if (S & (u64(1) << p)) {
                    int x = b.pt_x[p], y = b.pt_y[p], X, Y;
                    switch (k) {
                        case 0: X = x; Y = y; break;
                        case 1: X = m1 - x; Y = y; break;
                        case 2: X = x; Y = m1 - y; break;
                        case 3: X = m1 - x; Y = m1 - y; break;
                        case 4: X = y; Y = x; break;
                        case 5: X = m1 - y; Y = x; break;
                        case 6: X = y; Y = m1 - x; break;
                        default: X = m1 - y; Y = m1 - x; break;
                    }
                    d |= u64(1) << (Y * n + X);
                }
                if (first || d < canon) { canon = d; first = false; }
            }
            orbits.insert(canon);
            if (s == K) { orbits_maxsize.insert(canon); if (K > 0) nmax_k++; }
        }
        printf("%s{\"t\": %lld, \"quads\": %d, \"states\": %d, \"g0\": %d, \"K\": %d, "
               "\"maximal\": %lld, \"D4_orbits_of_maximal\": %d, \"D4_orbits_of_maxsize\": %d}",
               t ? ", " : "", t, (int)r.quads.size(), (int)states.size(), G[0], K, nmax,
               (int)orbits.size(), (int)orbits_maxsize.size());
    }
    printf("]}\n  },\n");
    fflush(stdout);
}

int main() {
    setvbuf(stdout, nullptr, _IOFBF, 1 << 22);
    printf("{\n");
    printf("  \"worker\": \"round4_b228c\",\n");
    double t0 = now_s();
    sec_lp();
    printf("  \"stage_lp_done\": %.2f\n", now_s());
    sec_relax();
    printf("  \"stage_relax_done\": %.2f\n", now_s());
    sec_corr();
    printf("  \"stage_corr_done\": %.2f\n", now_s());
    sec_ng();
    printf("  \"stage_ng_done\": %.2f\n", now_s());
    sec_graph();
    printf("  \"stage_graph_done\": %.2f\n", now_s());
    printf("  \"total_secs\": %.2f\n", now_s() - t0);
    printf("}\n");
    return 0;
}
