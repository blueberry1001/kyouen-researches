// Round4 verifier for B371, B372, B373, B374, B375, B378, B380.
//
// Subject: the complete family of *maximal safe 8-point sets on the 8x8 board*
// (the "8-stone maximals" of hypothesis-bank-round2 sec.38, B371-B380).
// All seven assigned hypotheses are universal/existential/statistical claims
// about exactly this family, so the enumeration is the whole job.
//
// Method
//  * Precompute, for every board triple T, the set comp(T) of board points p
//    with T u {p} concyclic-or-collinear (CSR table over C(V,3) triples).
//  * blocked(occ) = OR of comp(T) over all triples T of occ. A point p not in
//    occ is legal iff p is not in blocked(occ). This replaces kc::legal_mask
//    (which is O(F_n) per call) by O(C(k,3) * avg-completions) ~ 80 ops.
//  * DFS over increasing point indices with the standard "adding p kills the
//    candidates that would complete a quad" pruning; at depth K the leaf is
//    maximal iff blocked|occ == full. Top level is split over all C(V,2) pairs
//    so every 8-set is visited in exactly one task -> embarrassingly parallel.
//
// Usage: round4_b371 <n> <k> <outprefix>
//   writes <outprefix>.bin  (u64 count + masks)   [if count <= 40e6]
//   writes <outprefix>.json (all statistics)
#include "kc_core.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <chrono>
#include <functional>
#include <atomic>

#ifdef _OPENMP
#include <omp.h>
#endif

using kc::u64;
using kc::Board;

static int N = 0;      // board side
static int V = 0;      // points
static u64 FULL = 0;
static Board GB;
static int K = 8;
static std::chrono::steady_clock::time_point t_start;
static std::atomic<u64> g_seeds_done{0};

// ---------------------------------------------------------------- triple table
struct TriTable {
    int ntri = 0;
    std::vector<int> start;
    std::vector<int> list;
    // Combinatorial number system: rank of a<b<c is C(a,1)+C(b,2)+C(c,3),
    // a bijection onto [0, C(V,3)). Using (c-2) here would collide.
    int idx(int a, int b, int c) const {
        return a + b * (b - 1) / 2 + c * (c - 1) * (c - 2) / 6;
    }
};

static TriTable TT;

static void build_tritable(const Board& B, TriTable& T, const std::vector<u64>& quads) {
    T.ntri = B.V * (B.V - 1) * (B.V - 2) / 6;
    std::vector<int> cnt(T.ntri, 0);
    for (u64 q : quads) {
        int ids[4], t = 0;
        for (int i = 0; i < B.V; ++i) if ((q >> i) & 1ULL) ids[t++] = i;
        for (int s = 0; s < 4; ++s) {
            int o[3], m = 0;
            for (int r = 0; r < 4; ++r) if (r != s) o[m++] = ids[r];
            ++cnt[T.idx(o[0], o[1], o[2])];
        }
    }
    T.start.assign(T.ntri + 1, 0);
    int acc = 0;
    for (int i = 0; i < T.ntri; ++i) { T.start[i] = acc; acc += cnt[i]; }
    T.start[T.ntri] = acc;
    T.list.assign(acc, -1);
    std::vector<int> fill(T.start.begin(), T.start.end() - 1);
    for (u64 q : quads) {
        int ids[4], t = 0;
        for (int i = 0; i < B.V; ++i) if ((q >> i) & 1ULL) ids[t++] = i;
        for (int s = 0; s < 4; ++s) {
            int o[3], m = 0;
            for (int r = 0; r < 4; ++r) if (r != s) o[m++] = ids[r];
            int ti = T.idx(o[0], o[1], o[2]);
            T.list[fill[ti]++] = ids[s];
        }
    }
}

// A quad collection straight from the determinant, independent of the shared
// core's quad list, so a defect in kc_core.h's loop bounds cannot silently
// propagate into the triple-completion table.
static std::vector<u64> quads_direct(int n) {
    int VV = n * n;
    std::vector<std::array<long long, 4>> rows(VV);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            rows[i] = {(long long)x * x + (long long)y * y, x, y, 1};
        }
    std::vector<u64> out;
    for (int a = 0; a < VV; ++a)
        for (int b = a + 1; b < VV; ++b)
            for (int c = b + 1; c < VV; ++c)
                for (int d = c + 1; d < VV; ++d) {
                    int ids[4] = {a, b, c, d};
                    long long m[4][4];
                    for (int i = 0; i < 4; ++i)
                        for (int j = 0; j < 4; ++j) m[i][j] = rows[ids[i]][j];
                    if (kc::det4(m) == 0) {
                        u64 q = 0;
                        for (int i = 0; i < 4; ++i) q |= 1ULL << ids[i];
                        out.push_back(q);
                    }
                }
    return out;
}

// OR comp({a,b,c}) into blk.
static inline void add_blocked(int a, int b, int c, u64& blk) {
    int i = a, j = b, l = c;
    if (i > j) std::swap(i, j);
    if (j > l) std::swap(j, l);
    if (i > j) std::swap(i, j);
    int ti = TT.idx(i, j, l);
    for (int t = TT.start[ti], e = TT.start[ti + 1]; t < e; ++t)
        blk |= 1ULL << TT.list[t];
}

// ------------------------------------------------------------------- D4 tools
static int orb_id_of_pt[64];
static int n_orbits = 0;

static void build_orbits() {
    int m = (N + 1) / 2;
    std::map<std::pair<int, int>, int> key;
    for (int y = 0; y < N; ++y)
        for (int x = 0; x < N; ++x) {
            int a = std::min(x, N - 1 - x), b = std::min(y, N - 1 - y);
            if (a > b) std::swap(a, b);
            auto p = std::make_pair(a, b);
            if (!key.count(p)) key[p] = (int)key.size();
        }
    n_orbits = (int)key.size();
    for (int y = 0; y < N; ++y)
        for (int x = 0; x < N; ++x) {
            int a = std::min(x, N - 1 - x), b = std::min(y, N - 1 - y);
            if (a > b) std::swap(a, b);
            orb_id_of_pt[y * N + x] = key[std::make_pair(a, b)];
        }
    (void)m;
}

static int d4_img(int x, int y, int t) {
    int m = N - 1, nx, ny;
    switch (t) {
        case 0: nx = x;     ny = y;     break;
        case 1: nx = m - y; ny = x;     break;
        case 2: nx = m - x; ny = m - y; break;
        case 3: nx = y;     ny = m - x; break;
        case 4: nx = m - x; ny = y;     break;
        case 5: nx = x;     ny = m - y; break;
        case 6: nx = y;     ny = x;     break;
        default: nx = m - y; ny = m - x; break;
    }
    return ny * N + nx;
}

static u64 d4_apply(u64 occ, int t) {
    u64 out = 0;
    u64 c = occ;
    while (c) {
        int p = __builtin_ctzll(c);
        c &= c - 1;
        out |= 1ULL << d4_img(p % N, p / N, t);
    }
    return out;
}

static u64 d4_canon(u64 occ) {
    u64 best = occ;
    for (int t = 1; t < 8; ++t) {
        u64 im = d4_apply(occ, t);
        if (im < best) best = im;
    }
    return best;
}

// ------------------------------------------------------------- external radius
// r_ext(S): smallest Chebyshev distance from S's minimal axis-parallel bounding
// box to a point p that is *outside the board* and addable to S
// (p u T not concyclic/collinear for every triple T of S).
static int r_ext(const int* ch, int k) {
    int xs = 64, xb = -1, ys = 64, yb = -1;
    for (int i = 0; i < k; ++i) {
        int x = ch[i] % N, y = ch[i] / N;
        xs = std::min(xs, x); xb = std::max(xb, x);
        ys = std::min(ys, y); yb = std::max(yb, y);
    }
    long long rows[k][4];
    for (int i = 0; i < k; ++i) {
        int x = ch[i] % N, y = ch[i] / N;
        rows[i][0] = (long long)x * x + (long long)y * y;
        rows[i][1] = x; rows[i][2] = y; rows[i][3] = 1;
    }
    for (int r = 1; r <= 4; ++r) {
        for (int y = -r; y <= N - 1 + r; ++y)
            for (int x = -r; x <= N - 1 + r; ++x) {
                if (x >= 0 && x < N && y >= 0 && y < N) continue;  // outside board
                int dx = (x < xs) ? (xs - x) : (x > xb ? x - xb : 0);
                int dy = (y < ys) ? (ys - y) : (y > yb ? y - yb : 0);
                if (std::max(dx, dy) != r) continue;
                long long pr[4] = {(long long)x * x + (long long)y * y, x, y, 1};
                bool bad = false;
                for (int a = 0; a < k && !bad; ++a)
                    for (int b = a + 1; b < k && !bad; ++b)
                        for (int c = b + 1; c < k && !bad; ++c) {
                            long long m[4][4] = {{pr[0], pr[1], pr[2], pr[3]},
                                                {rows[a][0], rows[a][1], rows[a][2], rows[a][3]},
                                                {rows[b][0], rows[b][1], rows[b][2], rows[b][3]},
                                                {rows[c][0], rows[c][1], rows[c][2], rows[c][3]}};
                            if (kc::det4(m) == 0) bad = true;
                        }
                if (!bad) return r;
            }
    }
    return 5;  // > 4, capped
}

// -------------------------------------------------------------- leaf features
struct GroupStat {
    u64 cnt = 0;
    u64 edge_type = 0;      // all singly-covered points on the board boundary
    u64 interior_type = 0;  // all singly-covered points strictly interior
    u64 mixed = 0;
    u64 none = 0;
    int se_min = 1 << 20, se_max = -1;
    int si_min = 1 << 20, si_max = -1;
    std::vector<std::string> shapes;  // "e/i" pairs, capped
};

struct Acc {
    u64 n_sets = 0;
    std::map<int, u64> collinear_hist;   // #collinear triples -> count
    u64 no_collinear = 0;
    std::vector<u64> wit_no_collinear;
    std::map<int, u64> ndir_hist;       // #distinct directions -> count
    u64 dir_le1 = 0;
    std::vector<u64> wit_dir_le1;
    std::map<int, u64> nsides_hist;
    u64 sides_le1 = 0;
    std::vector<u64> wit_sides_le1;
    std::map<int, u64> ncorner_hist;
    u64 corners0 = 0;
    std::vector<u64> wit_corners0;
    std::map<std::string, u64> sig_hist;        // over all sets
    std::map<std::string, u64> sig_hist_canon;  // over D4 orbits
    std::map<int, u64> delmin_hist;
    u64 delmin1 = 0;
    std::vector<u64> wit_delmin1;
    std::map<int, GroupStat> sumb_group;
    std::map<int, u64> minb_hist, maxb_hist, rho_hist, sumb_hist, ntri_hist;
    std::map<int, u64> rext_hist;  // per D4 orbit
    u64 d4_orbits = 0;
    std::map<u64, u64> canon_seen;  // canon mask -> orbit weight
    u64 d4_not_stabilized = 0;     // sets whose D4 stabilizer is trivial
    std::map<int, u64> stab_hist;
    u64 leaves_checked = 0;
    u64 leaves_mismatch = 0;       // our maximality test vs kc::legal_mask
    std::vector<u64> masks;        // every accepted set, for the .bin dump
};

static std::string sig_string(const int* ch, int k) {
    std::vector<int> cnt(n_orbits, 0);
    std::vector<int> size(n_orbits, 0);
    for (int o = 0; o < n_orbits; ++o) {
        // orbit size: 4 if a==b else 8, recovered by scanning board once
        (void)o;
    }
    static std::vector<int> osz;
    if (osz.empty()) {
        osz.assign(n_orbits, 0);
        for (int p = 0; p < V; ++p) osz[orb_id_of_pt[p]]++;
    }
    for (int i = 0; i < k; ++i) cnt[orb_id_of_pt[ch[i]]]++;
    std::vector<std::pair<int, int>> v;
    for (int o = 0; o < n_orbits; ++o)
        if (cnt[o]) v.push_back({osz[o], cnt[o]});
    std::sort(v.begin(), v.end());
    std::string s;
    char buf[32];
    for (auto& p : v) {
        if (!s.empty()) s += "|";
        std::snprintf(buf, sizeof buf, "%d:%d", p.first, p.second);
        s += buf;
    }
    return s;
}

static int rho_of(const int* ch, int k, const int* bvals, int empty_idx) {
    // family of triples of ch that forbid ch-empty point `empty_idx`
    std::vector<u64> fam;
    u64 m = 1ULL << empty_idx;
    for (int a = 0; a < k; ++a)
        for (int b = a + 1; b < k; ++b)
            for (int c = b + 1; c < k; ++c) {
                int t3[3] = {ch[a], ch[b], ch[c]};
                std::sort(t3, t3 + 3);
                int ti = TT.idx(t3[0], t3[1], t3[2]);
                for (int t = TT.start[ti], e = TT.start[ti + 1]; t < e; ++t)
                    if (TT.list[t] == empty_idx) fam.push_back((u64(t3[0]) << 40) | (u64(t3[1]) << 20) | u64(t3[2]));
            }
    (void)bvals;
    if (fam.empty()) return 0;
    int full = (1 << k) - 1;
    for (int i = 0; i < (int)fam.size(); ++i) {
        u64 c1 = fam[i];
        int m1 = (1 << (c1 >> 40 & 31)) | (1 << (c1 >> 20 & 31)) | (1 << (c1 & 31));
        if (m1 == full) return 1;
    }
    for (int i = 0; i < (int)fam.size(); ++i)
        for (int j = i + 1; j < (int)fam.size(); ++j) {
            u64 c1 = fam[i], c2 = fam[j];
            int m2 = (1 << (c1 >> 40 & 31)) | (1 << (c1 >> 20 & 31)) | (1 << (c1 & 31)) |
                     (1 << (c2 >> 40 & 31)) | (1 << (c2 >> 20 & 31)) | (1 << (c2 & 31));
            if (m2 == full) return 2;
        }
    for (int i = 0; i < (int)fam.size(); ++i)
        for (int j = i + 1; j < (int)fam.size(); ++j)
            for (int l = j + 1; l < (int)fam.size(); ++l) {
                u64 m2 = 0;
                u64 f3[3] = {fam[i], fam[j], fam[l]};
                for (int q = 0; q < 3; ++q)
                    m2 |= (1 << (f3[q] >> 40 & 31)) | (1 << (f3[q] >> 20 & 31)) | (1 << (f3[q] & 31));
                if (m2 == full) return 3;
            }
    return 4;
}

static void leaf(Acc& A, const int* ch, int k, u64 occ) {
    A.masks.push_back(occ);
    A.n_sets++;
    int xs = 64, xb = -1, ys = 64, yb = -1;
    for (int i = 0; i < k; ++i) {
        int x = ch[i] % N, y = ch[i] / N;
        xs = std::min(xs, x); xb = std::max(xb, x);
        ys = std::min(ys, y); yb = std::max(yb, y);
    }
    // ---- collinear triples and their directions
    int ncol = 0;
    std::vector<std::pair<int, int>> dirs;
    for (int a = 0; a < k; ++a)
        for (int b = a + 1; b < k; ++b)
            for (int c = b + 1; c < k; ++c) {
                int x0 = ch[a] % N, y0 = ch[a] / N;
                int x1 = ch[b] % N, y1 = ch[b] / N;
                int x2 = ch[c] % N, y2 = ch[c] / N;
                long long dx1 = x1 - x0, dy1 = y1 - y0, dx2 = x2 - x0, dy2 = y2 - y0;
                if (dx1 * dy2 - dy1 * dx2 == 0) {
                    ++ncol;
                    // primitive undirected direction of the line through a,b
                    long long G = std::abs(dx1) ? std::abs(dx1) : std::abs(dy1);
                    {   long long aa = std::abs(dx1), bb2 = std::abs(dy1);
                        G = aa ? aa : bb2;
                        for (long long z = 2; z * z <= G; ++z) while (G % z == 0) G /= z;
                    }
                    if (G <= 0) G = 1;
                    long long ux = dx1 / G, uy = dy1 / G;
                    if (ux < 0 || (ux == 0 && uy < 0)) { ux = -ux; uy = -uy; }
                    dirs.push_back({(int)ux, (int)uy});
                }
            }
    std::sort(dirs.begin(), dirs.end());
    dirs.erase(std::unique(dirs.begin(), dirs.end()), dirs.end());
    int ndir = (int)dirs.size();
    A.n_sets++;
    A.collinear_hist[ncol]++;
    A.ndir_hist[ndir]++;
    if (ncol == 0) { A.no_collinear++; if (A.wit_no_collinear.size() < 4) A.wit_no_collinear.push_back(occ); }
    if (ndir <= 1) { A.dir_le1++; if (A.wit_dir_le1.size() < 4) A.wit_dir_le1.push_back(occ); }

    // ---- sides and corners
    int smask = 0;
    if (xs == 0) smask |= 1;      // L
    if (xb == N - 1) smask |= 2;  // R
    if (ys == 0) smask |= 4;      // B
    if (yb == N - 1) smask |= 8;  // T
    int nsides = __builtin_popcount(smask);
    A.nsides_hist[nsides]++;
    if (nsides <= 1) { A.sides_le1++; if (A.wit_sides_le1.size() < 4) A.wit_sides_le1.push_back(occ); }
    int ncorn = 0;
    for (int y = 0; y < N; y += N - 1)
        for (int x = 0; x < N; x += N - 1)
            if (occ & (1ULL << (y * N + x))) ++ncorn;
    A.ncorner_hist[ncorn]++;
    if (ncorn == 0) { A.corners0++; if (A.wit_corners0.size() < 4) A.wit_corners0.push_back(occ); }

    // ---- D4 signature / orbits
    std::string sg = sig_string(ch, k);
    A.sig_hist[sg]++;
    u64 can = d4_canon(occ);
    if (!A.canon_seen.count(can)) {
        A.canon_seen[can] = 1;
        A.sig_hist_canon[sg]++;
        A.rext_hist[r_ext(ch, k)]++;
        A.d4_orbits++;
    }
    int stab = 0;
    for (int t = 1; t < 8; ++t) if (d4_apply(occ, t) == occ) ++stab;
    A.stab_hist[stab]++;
    if (stab == 0) A.d4_not_stabilized++;

    // ---- covering multiplicity b(p) over the empty points
    int bval[64];
    std::memset(bval, 0, sizeof bval);
    for (int a = 0; a < k; ++a)
        for (int b = a + 1; b < k; ++b)
            for (int c = b + 1; c < k; ++c) {
                int t3[3] = {ch[a], ch[b], ch[c]};
                std::sort(t3, t3 + 3);
                int ti = TT.idx(t3[0], t3[1], t3[2]);
                for (int t = TT.start[ti], e = TT.start[ti + 1]; t < e; ++t) bval[TT.list[t]]++;
            }
    int sumb = 0, mb = 1 << 20, xbmax = 0, n_single = 0, se = 0, si = 0;
    u64 empt = FULL & ~occ;
    for (int p = 0; p < V; ++p) {
        if (!(empt & (1ULL << p))) continue;
        int b = bval[p];
        sumb += b;
        if (b < mb) mb = b;
        if (b > xbmax) xbmax = b;
        if (b == 1) {
            ++n_single;
            int x = p % N, y = p / N;
            if (x == 0 || x == N - 1 || y == 0 || y == N - 1) ++se; else ++si;
        }
    }
    A.sumb_hist[sumb]++;
    A.minb_hist[mb]++;
    A.maxb_hist[xbmax]++;
    A.ntri_hist[ncol]++;
    {
        GroupStat& g = A.sumb_group[sumb];
        g.cnt++;
        if (se == 0 && si == 0) g.none++;
        else if (si == 0) g.edge_type++;
        else if (se == 0) g.interior_type++;
        else g.mixed++;
        g.se_min = std::min(g.se_min, se); g.se_max = std::max(g.se_max, se);
        g.si_min = std::min(g.si_min, si); g.si_max = std::max(g.si_max, si);
        if (g.shapes.size() < 24) {
            char buf[32];
            std::snprintf(buf, sizeof buf, "%d/%d", se, si);
            g.shapes.push_back(buf);
        }
    }
    // rho (auxiliary)
    int rho = 1 << 20;
    for (int p = 0; p < V; ++p) {
        if (!(empt & (1ULL << p))) continue;
        if (bval[p] == 1) { rho = 1; break; }
    }
    if (rho != 1) {
        for (int p = 0; p < V && rho != 1; ++p) {
            if (!(empt & (1ULL << p))) continue;
            int r = rho_of(ch, k, bval, p);
            if (r < rho) rho = r;
            if (rho == 2) break;  // min_b >= 2 implies tau >= 2
        }
    }
    A.rho_hist[rho]++;

    // ---- B378: one-stone deletion, count of newly legal empty points
    int delmin = 1 << 20;
    for (int i = 0; i < k; ++i) {
        u64 blk2 = 0;
        for (int a = 0; a < k; ++a) {
            if (a == i) continue;
            for (int b = a + 1; b < k; ++b) {
                if (b == i) continue;
                for (int c = b + 1; c < k; ++c) {
                    if (c == i) continue;
                    int t3[3] = {ch[a], ch[b], ch[c]};
                    std::sort(t3, t3 + 3);
                    add_blocked(t3[0], t3[1], t3[2], blk2);
                }
            }
        }
            int cnt = 0;
        u64 em2 = empt;
        while (em2) {
            int p = __builtin_ctzll(em2);
            em2 &= em2 - 1;
            if (!((blk2 >> p) & 1)) ++cnt;
        }
        if (cnt < delmin) delmin = cnt;
    }
    A.delmin_hist[delmin]++;
    if (delmin == 1) { A.delmin1++; if (A.wit_delmin1.size() < 4) A.wit_delmin1.push_back(occ); }
}

// --------------------------------------------------------------------- driver
static void dfs(Acc& A, u64 occ, u64 blk, u64 cand, int size, int* ch) {
    if (size == K) {
        if ((blk | occ) == FULL) {
            // Cross-check our O(C(k,3)) maximality test against the shared
            // core's independent F_n-scan: they must agree on every leaf.
            A.leaves_checked++;
            if (kc::legal_mask(GB, occ) != 0) A.leaves_mismatch++;
            leaf(A, ch, K, occ);
        }
        return;
    }
    // Deliberately NOT using `cand` as the loop domain. The usual "killing"
    // prune (a candidate that would complete a quad can never be added later)
    // is unsound for *enumerating maximal sets*: a point p is blocked only
    // relative to the current occ, yet p itself may still be a legal final
    // state. Restricting the scan to `cand` therefore misses sets - the bound
    // test dbg_b371_bound.cpp shows 4x4/k=6 yielding 688 instead of 3,608.
    // We scan the full index range and pay for it in wasted branches, which
    // the pair-seed split and 16 cores absorb.
    for (int p = ch[size - 1] + 1; p < V; ++p) {
        u64 bit = 1ULL << p;
        if ((blk >> p) & 1) continue;   // p is forbidden: not a legal move
        u64 nb = blk;
        for (int i = 0; i < size; ++i)
            for (int j = i + 1; j < size; ++j) add_blocked(ch[i], ch[j], p, nb);
        ch[size] = p;
        dfs(A, occ | bit, nb, 0ULL, size + 1, ch);
    }
}

static void merge(Acc& dst, const Acc& src) {
    auto m = [](std::map<int, u64>& d, const std::map<int, u64>& s) {
        for (auto& p : s) d[p.first] += p.second;
    };
    auto ms = [](std::map<std::string, u64>& d, const std::map<std::string, u64>& s) {
        for (auto& p : s) d[p.first] += p.second;
    };
    dst.n_sets += src.n_sets;
    m(dst.collinear_hist, src.collinear_hist);
    m(dst.ndir_hist, src.ndir_hist);
    m(dst.nsides_hist, src.nsides_hist);
    m(dst.ncorner_hist, src.ncorner_hist);
    m(dst.delmin_hist, src.delmin_hist);
    m(dst.minb_hist, src.minb_hist);
    m(dst.maxb_hist, src.maxb_hist);
    m(dst.rho_hist, src.rho_hist);
    m(dst.sumb_hist, src.sumb_hist);
    m(dst.ntri_hist, src.ntri_hist);
    m(dst.rext_hist, src.rext_hist);
    m(dst.stab_hist, src.stab_hist);
    ms(dst.sig_hist, src.sig_hist);
    ms(dst.sig_hist_canon, src.sig_hist_canon);
    dst.no_collinear += src.no_collinear;
    dst.dir_le1 += src.dir_le1;
    dst.sides_le1 += src.sides_le1;
    dst.corners0 += src.corners0;
    dst.delmin1 += src.delmin1;
    dst.d4_orbits += src.d4_orbits;
    dst.d4_not_stabilized += src.d4_not_stabilized;
    dst.leaves_checked += src.leaves_checked;
    dst.leaves_mismatch += src.leaves_mismatch;
    dst.masks.insert(dst.masks.end(), src.masks.begin(), src.masks.end());
    for (auto& p : src.canon_seen) dst.canon_seen[p.first] += p.second;
    for (auto& p : src.sumb_group) {
        GroupStat& d = dst.sumb_group[p.first];
        const GroupStat& s = p.second;
        d.cnt += s.cnt;
        d.edge_type += s.edge_type; d.interior_type += s.interior_type;
        d.mixed += s.mixed; d.none += s.none;
        d.se_min = std::min(d.se_min, s.se_min); d.se_max = std::max(d.se_max, s.se_max);
        d.si_min = std::min(d.si_min, s.si_min); d.si_max = std::max(d.si_max, s.si_max);
        for (auto& q : s.shapes) if (d.shapes.size() < 24) d.shapes.push_back(q);
    }
    auto appw = [](std::vector<u64>& a, const std::vector<u64>& b) {
        for (u64 x : b) if (a.size() < 4) a.push_back(x);
    };
    appw(dst.wit_no_collinear, src.wit_no_collinear);
    appw(dst.wit_dir_le1, src.wit_dir_le1);
    appw(dst.wit_sides_le1, src.wit_sides_le1);
    appw(dst.wit_corners0, src.wit_corners0);
    appw(dst.wit_delmin1, src.wit_delmin1);
}

static std::string masks_json(const std::vector<u64>& v) {
    std::string s = "[";
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) s += ", ";
        char buf[64];
        std::snprintf(buf, sizeof buf, "%llu", (unsigned long long)v[i]);
        s += buf;
    }
    return s + "]";
}

int main(int argc, char** argv) {
    N = argc > 1 ? atoi(argv[1]) : 8;
    K = argc > 2 ? atoi(argv[2]) : 8;
    std::string out = argc > 3 ? argv[3] : "out";
    auto t0 = std::chrono::steady_clock::now();
    t_start = t0;
    kc::build_square(GB, N);
    V = GB.V;
    FULL = GB.full;
    // Self-computed quad list. PROTOCOL.md's F_n for n=2..8 is
    // 1, 14, 194, 826, 2491, 6364, 14564; we refuse to continue unless the
    // count matches, because everything downstream hangs off this table.
    std::vector<u64> quads = quads_direct(N);
    static const size_t kKnownF[] = {0, 0, 1, 14, 194, 826, 2491, 6364, 14564, 29152};
    std::fprintf(stderr, "n=%d V=%d F_direct=%zu F_core=%zu\n", N, V, quads.size(), GB.quads.size());
    if (N >= 2 && N <= 9 && quads.size() != kKnownF[N]) {
        std::fprintf(stderr, "FATAL: F_%d = %zu, expected %zu\n", N, quads.size(), kKnownF[N]);
        return 2;
    }
    build_tritable(GB, TT, quads);
    build_orbits();
    std::fprintf(stderr, "n=%d V=%d ntri=%d entries=%d\n", N, V, TT.ntri, (int)TT.list.size());

    // Top-level split: seed every index *pair* (a, b) with 0 <= a < b < V.
    // Every k-set has a unique such prefix, so it is handled exactly once. An
    // earlier version used b <= V-2, which silently dropped every maximal set
    // containing the last point.
    std::vector<std::pair<int, int>> seeds;
    for (int b = 1; b < V; ++b)
        for (int a = 0; a < b; ++a) seeds.push_back({a, b});
    std::fprintf(stderr, "seeds=%zu K=%d\n", seeds.size(), K);

    int nth = 1;
#ifdef _OPENMP
    #pragma omp parallel
    { nth = omp_get_num_threads(); }
#endif
    std::fprintf(stderr, "threads=%d\n", nth);

    Acc total;
    std::vector<std::vector<u64>> masks(nth);
    std::vector<Acc> loc(nth);
    u64 nodes = 0;

#ifdef _OPENMP
    #pragma omp parallel
#endif
    {
        int tid = 0;
#ifdef _OPENMP
        tid = omp_get_thread_num();
#endif
        int ch[16];
        Acc& A = loc[tid];
        std::vector<u64>& M = masks[tid];
        u64 local_nodes = 0;
#ifdef _OPENMP
        #pragma omp for schedule(dynamic, 1)
#endif
        for (long long t = 0; t < (long long)seeds.size(); ++t) {
            int a = seeds[t].first, b = seeds[t].second;
            ch[0] = a; ch[1] = b;
            dfs(A, (1ULL << a) | (1ULL << b), 0ULL, 0ULL, 2, ch);
            ++local_nodes;
            if ((local_nodes & 255) == 0) {
                u64 done = ++g_seeds_done;
                u64 emp = 0, ns = 0;
                for (int i = 0; i < nth; ++i) { emp += loc[i].leaves_checked; ns += loc[i].n_sets; }
                std::fprintf(stderr, "[progress] seeds %llu/%zu  accepted=%llu  (%.0fs)\n",
                             (unsigned long long)done, seeds.size(), (unsigned long long)ns,
                             std::chrono::duration<double>(std::chrono::steady_clock::now() - t_start).count());
            }
        }
        nodes += local_nodes;
#ifdef _OPENMP
    }
#else
    }
#endif

    u64 total_nodes = nodes;
    for (int i = 0; i < nth; ++i) merge(total, loc[i]);
    auto t1 = std::chrono::steady_clock::now();
    double secs = std::chrono::duration<double>(t1 - t0).count();

    // The per-thread `masks` vector is legacy; the accepted sets now live in
    // Acc::masks and are merged by merge() above.
    std::vector<u64>& all = total.masks;
    std::sort(all.begin(), all.end());
    all.erase(std::unique(all.begin(), all.end()), all.end());

    std::fprintf(stderr, "maximal size-%d sets on %dx%d: %zu  (%.1fs, seeds=%llu)\n", K, N, N,
                 all.size(), secs, (unsigned long long)total_nodes);

    if (all.size() <= 40000000ULL) {
        std::string path = out + ".bin";
        FILE* f = std::fopen(path.c_str(), "wb");
        if (f) {
            u64 c = (u64)all.size();
            std::fwrite(&c, sizeof c, 1, f);
            if (c) std::fwrite(all.data(), sizeof(u64), all.size(), f);
            std::fclose(f);
            std::fprintf(stderr, "wrote %s\n", path.c_str());
        }
    }

    // ------------------------------------------------------------------ JSON
    std::string J = "{\n";
    char buf[4096];
    auto add = [&](const std::string& s) { J += s; };
    std::snprintf(buf, sizeof buf,
                  "  \"meta\": {\"n\": %d, \"k\": %d, \"V\": %d, \"forbidden_quads\": %zu, "
                  "\"triples\": %d, \"triple_completion_entries\": %d, \"threads\": %d, "
                  "\"seconds\": %.3f, \"dfs_seeds\": %llu},\n",
                  N, K, V, quads.size(), TT.ntri, (int)TT.list.size(), nth, secs,
                  (unsigned long long)total_nodes);
    add(buf);
    std::snprintf(buf, sizeof buf, "  \"count_maximal\": %zu,\n", all.size());
    add(buf);

    auto hist = [&](const char* name, const std::map<int, u64>& h) {
        J += "  \"" + std::string(name) + "\": {";
        bool first = true;
        for (auto& p : h) {
            if (!first) J += ", ";
            first = false;
            char b2[64];
            std::snprintf(b2, sizeof b2, "\"%d\": %llu", p.first, (unsigned long long)p.second);
            J += b2;
        }
        J += "},\n";
    };
    auto shist = [&](const char* name, const std::map<std::string, u64>& h) {
        J += "  \"" + std::string(name) + "\": {";
        bool first = true;
        for (auto& p : h) {
            if (!first) J += ", ";
            first = false;
            char b2[256];
            std::snprintf(b2, sizeof b2, "\"%s\": %llu", p.first.c_str(), (unsigned long long)p.second);
            J += b2;
        }
        J += "},\n";
    };

    add("  \"b371\": {\n");
    hist("collinear_triple_count_hist", total.collinear_hist);
    std::snprintf(buf, sizeof buf,
                  "    \"sets_with_no_collinear_triple\": %llu, \"witness_masks\": %s\n",
                  (unsigned long long)total.no_collinear,
                  masks_json(total.wit_no_collinear).c_str());
    add(buf);
    add("  },\n");

    add("  \"b372\": {\n");
    hist("distinct_direction_hist", total.ndir_hist);
    std::snprintf(buf, sizeof buf,
                  "    \"sets_with_at_most_one_direction\": %llu, \"witness_masks\": %s\n",
                  (unsigned long long)total.dir_le1, masks_json(total.wit_dir_le1).c_str());
    add(buf);
    add("  },\n");

    add("  \"b373\": {\n");
    hist("sides_touched_hist", total.nsides_hist);
    std::snprintf(buf, sizeof buf,
                  "    \"sets_touching_at_most_one_side\": %llu, \"witness_masks\": %s\n",
                  (unsigned long long)total.sides_le1, masks_json(total.wit_sides_le1).c_str());
    add(buf);
    add("  },\n");

    add("  \"b374\": {\n");
    hist("corners_used_hist", total.ncorner_hist);
    std::snprintf(buf, sizeof buf,
                  "    \"sets_using_no_corner\": %llu, \"witness_masks\": %s\n",
                  (unsigned long long)total.corners0, masks_json(total.wit_corners0).c_str());
    add(buf);
    add("  },\n");

    add("  \"b375\": {\n");
    std::snprintf(buf, sizeof buf, "    \"d4_orbits_of_size_%d_maximal_sets\": %llu,\n", K,
                  (unsigned long long)total.d4_orbits);
    add(buf);
    shist("orbit_signature_hist_all_sets", total.sig_hist);
    shist("orbit_signature_hist_per_d4_orbit", total.sig_hist_canon);
    hist("d4_stabiliser_order_hist", total.stab_hist);
    std::snprintf(buf, sizeof buf, "    \"sets_with_trivial_d4_stabiliser\": %llu\n",
                  (unsigned long long)total.d4_not_stabilized);
    add(buf);
    add("  },\n");

    add("  \"b378\": {\n");
    hist("min_new_legal_after_one_deletion_hist", total.delmin_hist);
    std::snprintf(buf, sizeof buf,
                  "    \"sets_with_min_exactly_one\": %llu, \"witness_masks\": %s\n",
                  (unsigned long long)total.delmin1, masks_json(total.wit_delmin1).c_str());
    add(buf);
    add("  },\n");

    add("  \"b380\": {\n");
    hist("sum_b_hist", total.sumb_hist);
    J += "    \"by_sum_b\": {\n";
    bool first = true;
    for (auto& p : total.sumb_group) {
        if (!first) J += ",\n";
        first = false;
        const GroupStat& g = p.second;
        std::string sh;
        for (size_t i = 0; i < g.shapes.size(); ++i) {
            if (i) sh += " ";
            sh += g.shapes[i];
        }
        char b2[1024];
        std::snprintf(b2, sizeof b2,
                      "      \"%d\": {\"count\": %llu, \"edge_type\": %llu, \"interior_type\": %llu, "
                      "\"mixed\": %llu, \"no_single_covered\": %llu, \"se_range\": [%d,%d], "
                      "\"si_range\": [%d,%d], \"edge_and_interior_types_both_present\": %s, "
                      "\"sample_edge_interior_pairs\": \"%s\"}",
                      p.first, (unsigned long long)g.cnt, (unsigned long long)g.edge_type,
                      (unsigned long long)g.interior_type, (unsigned long long)g.mixed,
                      (unsigned long long)g.none, g.se_min, g.se_max, g.si_min, g.si_max,
                      (g.edge_type > 0 && g.interior_type > 0) ? "true" : "false", sh.c_str());
        J += b2;
    }
    J += "\n    }\n  },\n";

    add("  \"auxiliary\": {\n");
    std::snprintf(buf, sizeof buf,
                  "    \"leaves_checked_against_core\": %llu, \"maximality_disagreements\": %llu,\n",
                  (unsigned long long)total.leaves_checked,
                  (unsigned long long)total.leaves_mismatch);
    add(buf);
    hist("min_b_hist", total.minb_hist);
    hist("max_b_hist", total.maxb_hist);
    hist("rho_hist", total.rho_hist);
    hist("external_saturation_radius_hist_per_d4_orbit", total.rext_hist);
    add("    \"r_ext_definition\": \"smallest Chebyshev distance from the minimal axis-parallel "
        "bounding box of S to a point outside the board that is addable to S; 5 means >4\"\n");
    add("  }\n");
    J += "}\n";

    std::string jpath = out + ".json";
    FILE* jf = std::fopen(jpath.c_str(), "wb");
    if (jf) { std::fwrite(J.data(), 1, J.size(), jf); std::fclose(jf); std::fprintf(stderr, "wrote %s\n", jpath.c_str()); }
    return 0;
}
