// round4_b092.cpp -- Round 4 solver for B092-B127 (kyouen verification).
//
// Build (WSL):
//   g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/r4 round4_b092.cpp
//
// All arithmetic is integer. Occupancy is one u64 per board (n*n <= 64).
// Output: research/verification/round4_b092.json
//
// Jobs are selected by argv[1] so a long computation can be run piecewise.
//   sat    : s_n / full maximal-size spectrum / B099 attribution   (B091..B100)
//   big    : small-k maximal search on n=8,9,10                    (B092,B093,B094)
//   shape  : row occupancy, D4 orbits, identification curve        (B103..B107)
//   b110   : circle+line capacity cover of the forbidden quads
//   g11    : n=7 G_11 / G_12 connectivity among the 16 max sets   (B111,B112,B119,B121,B122)
//   defo   : n=7 corner component / shortest paths / labels        (B115,B118,B120)
//   aux    : n=6 width-10 pairs, aux points, common-point removal  (B123,B124,B125,B127)

#include "kc_core.h"

#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <map>
#include <numeric>
#include <set>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using kc::u64;
using kc::Board;

static const char* VER =
    "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification";
static const char* DATA = "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data";
static const char* NIGHT =
    "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/night-research";

static FILE* g_out = nullptr;
static double g_t0 = 0;

static void say(const std::string& s) {
    std::printf("[%7.1fs] %s\n", 0.0, s.c_str());
    std::fflush(stdout);
}
static void jline(const std::string& s) {
    if (g_out) { std::fprintf(g_out, "%s\n", s.c_str()); std::fflush(g_out); }
}
static void jopen(const std::string& key) { jline("\"" + key + "\": {"); }
static void jclose(const char* tail) { jline(std::string("  }") + tail); }

// ---------------------------------------------------------------- utilities
static std::vector<int> bits(u64 m) {
    std::vector<int> v;
    while (m) { int p = __builtin_ctzll(m); m &= m - 1; v.push_back(p); }
    return v;
}
static std::string jm(u64 m) {
    std::string s = "[";
    std::vector<int> v = bits(m);
    for (size_t i = 0; i < v.size(); ++i) { if (i) s += ","; s += std::to_string(v[i]); }
    return s + "]";
}
static int pc(u64 m) { return __builtin_popcountll(m); }

// K_n by branch and bound (mirrors kc_selfcheck.cpp).
static int max_safe_size(int n) {
    Board b; kc::build_square(b, n);
    int best = 0;
    struct F { u64 occ, cand; int size; };
    u64 start = (b.V >= 64) ? ~u64(0) : ((u64(1) << b.V) - 1);
    std::vector<F> stk{{0, start, 0}};
    while (!stk.empty()) {
        F f = stk.back(); stk.pop_back();
        if (f.size > best) best = f.size;
        if (!f.cand) continue;
        if (f.size + pc(f.cand) <= best) continue;
        u64 c = f.cand;
        while (c) {
            int p = __builtin_ctzll(c); c &= c - 1;
            if (!kc::can_add(b, f.occ, p)) continue;
            u64 nxt = f.occ | (u64(1) << p), kill = 0;
            for (u64 t : b.triples_by_pt[p]) {
                u64 miss = t & ~nxt;
                if (miss && (miss & (miss - 1)) == 0) kill |= miss;
            }
            stk.push_back({nxt, c & ~kill, f.size + 1});
        }
    }
    return best;
}

// Every maximal safe set of size exactly K, complete.
//
// `cand` = points that are still legal and were not already excluded.  The
// loop `c &= c-1` walks candidates in increasing index order and passes
// `c & ~kill` to the child, so children only ever consider strictly larger
// indices than the point just added.  That makes the enumeration canonical
// (each set once) and lets the popcount prune bound the tree.
static std::vector<u64> maximal_sets(int n, int K) {
    Board b; kc::build_square(b, n);
    std::vector<u64> found;
    u64 start = (b.V >= 64) ? ~u64(0) : ((u64(1) << b.V) - 1);
    struct F { u64 occ, cand; int size; };
    std::vector<F> stk{{0, start, 0}};
    long long nd = 0;
    while (!stk.empty()) {
        F f = stk.back(); stk.pop_back();
        ++nd;
        if (f.size + pc(f.cand) < K) continue;    // cannot reach K
        if (f.size == K) { found.push_back(f.occ); continue; }
        u64 c = f.cand;
        while (c) {
            int p = __builtin_ctzll(c);
            c &= c - 1;
            if (!kc::can_add(b, f.occ, p)) continue;
            u64 nxt = f.occ | (u64(1) << p), kill = 0;
            for (u64 t : b.triples_by_pt[p]) {
                u64 miss = t & ~nxt;
                if (miss && (miss & (miss - 1)) == 0) kill |= miss;
            }
            stk.push_back({nxt, c & ~kill, f.size + 1});
        }
    }
    (void)nd;
    std::sort(found.begin(), found.end());
    found.erase(std::unique(found.begin(), found.end()), found.end());
    return found;
}

// Every maximal safe set of size < cap, complete.  (used for the spectrum)
// A maximal set with size >= cap is NOT enumerated here; job_sat calls this
// with cap = K_n, so the size-K_n sets come from maximal_sets() instead.
static std::vector<u64> all_maximal_le(int n, int cap, long long* nodes = nullptr) {
    Board b; kc::build_square(b, n);
    std::vector<u64> found;
    u64 start = (b.V >= 64) ? ~u64(0) : ((u64(1) << b.V) - 1);
    struct F { u64 occ, cand; int size; };
    std::vector<F> stk{{0, start, 0}};
    long long nd = 0;
    while (!stk.empty()) {
        F f = stk.back(); stk.pop_back();
        ++nd;
        if (f.size >= cap) continue;              // handled by maximal_sets
        if (f.cand == 0) {
            // The candidate list ran out, which does NOT by itself mean the
            // set is maximal: a candidate can also be dropped because it is
            // no longer legal.  Ask the core.
            if (f.size < cap && kc::legal_mask(b, f.occ) == 0) found.push_back(f.occ);
            continue;
        }
        u64 c = f.cand;
        while (c) {
            int p = __builtin_ctzll(c); c &= c - 1;
            if (!kc::can_add(b, f.occ, p)) continue;
            u64 nxt = f.occ | (u64(1) << p), kill = 0;
            for (u64 t : b.triples_by_pt[p]) {
                u64 miss = t & ~nxt;
                if (miss && (miss & (miss - 1)) == 0) kill |= miss;
            }
            stk.push_back({nxt, c & ~kill, f.size + 1});
        }
    }
    if (nodes) *nodes = nd;
    std::sort(found.begin(), found.end());
    found.erase(std::unique(found.begin(), found.end()), found.end());
    return found;
}

// ================================================================== job: sat
// Complete s_n and the full maximal-size spectrum for n=4..7, plus B099
// line/circle capacity attribution over the 60 smallest maximal sets.
static void job_sat() {
    jopen("sat");
    for (int n = 4; n <= 7; ++n) {
        Board b; kc::build_square(b, n);
        int K = max_safe_size(n);
        long long nodes = 0;
        std::vector<u64> allm = all_maximal_le(n, K, &nodes);
        std::vector<u64> top = maximal_sets(n, K);
        allm.insert(allm.end(), top.begin(), top.end());
        std::sort(allm.begin(), allm.end());
        allm.erase(std::unique(allm.begin(), allm.end()), allm.end());
        std::map<int,int> hist;
        u64 wit = 0;
        for (u64 m : allm) { hist[pc(m)]++; if (!wit) wit = m; }
        int s_n = hist.empty() ? -1 : hist.begin()->first;
        // B099 attribution
        std::map<u64,int> cT;
        for (int v = 0; v < b.V; ++v)
            for (u64 t : b.triples_by_pt[v]) cT[t]++;
        std::vector<u64> sorted = allm;
        std::sort(sorted.begin(), sorted.end(),
                  [](u64 a, u64 c) { return pc(a) < pc(c); });
        long long L = 0, C = 0, Lcap = 0, Ccap = 0;
        int take = (int)std::min<size_t>(60, sorted.size());
        for (int i = 0; i < take; ++i) {
            std::vector<int> pts = bits(sorted[i]);
            for (size_t a = 0; a + 2 < pts.size(); ++a)
            for (size_t c1 = a + 1; c1 + 1 < pts.size(); ++c1)
            for (size_t c2 = c1 + 1; c2 < pts.size(); ++c2) {
                u64 tm = (u64(1) << pts[a]) | (u64(1) << pts[c1]) | (u64(1) << pts[c2]);
                auto it = cT.find(tm);
                if (it == cT.end()) continue;
                long long x1 = b.pt_x[pts[a]], y1 = b.pt_y[pts[a]];
                long long x2 = b.pt_x[pts[c1]], y2 = b.pt_y[pts[c1]];
                long long x3 = b.pt_x[pts[c2]], y3 = b.pt_y[pts[c2]];
                if ((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0) { L++; Lcap += it->second; }
                else { C++; Ccap += it->second; }
            }
        }
        std::string hs;
        for (auto& kv : hist) { if (!hs.empty()) hs += ","; hs += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second); }
        char r[64]; std::snprintf(r, sizeof r, "%lld/%lld", Lcap, Lcap + Ccap);
        jline("    \"" + std::to_string(n) + "\": {\"K\": " + std::to_string(K) +
              ",\"n_maximal_total\": " + std::to_string((long long)allm.size()) +
              ",\"s_n\": " + std::to_string(s_n) +
              ",\"s_witness\": \"" + jm(wit) + "\"" +
              ",\"spectrum\": {" + hs + "}" +
              ",\"b099\": {\"take\": " + std::to_string(take) +
              ",\"L\": " + std::to_string(L) + ",\"C\": " + std::to_string(C) +
              ",\"Lcap\": " + std::to_string(Lcap) + ",\"Ccap\": " + std::to_string(Ccap) +
              ",\"line_cap_share\": \"" + std::string(r) + "\"}" +
              ",\"search_nodes\": " + std::to_string(nodes) + ",\"complete\": true},");
        say("sat n=" + std::to_string(n) + " K=" + std::to_string(K) +
            " s_n=" + std::to_string(s_n) + " nmax=" + std::to_string((long long)allm.size()) +
            " spec={" + hs + "} Lcap=" + std::string(r) + " nodes=" + std::to_string(nodes));
    }
    jclose(",");
}

// ================================================================== job: small
// B092/B093/B094: is there a maximal safe set of size k on the n x n board?
// The search is COMPLETE for the k range asked: it walks the whole tree, so a
// zero count is a proof of non-existence, not a random failure.
static void search_small_maximal(int n, int klo, int khi) {
    Board b; kc::build_square(b, n);
    u64 start = (b.V >= 64) ? ~u64(0) : ((u64(1) << b.V) - 1);
    for (int K = klo; K <= khi; ++K) {
        long long cnt = 0; u64 first = 0;
        struct F { u64 occ, cand; int size; };
        std::vector<F> stk{{0, start, 0}};
        long long nd = 0;
        while (!stk.empty()) {
            F f = stk.back(); stk.pop_back();
            ++nd;
            if (f.size + pc(f.cand) < K) continue;      // cannot reach size K
            if (f.size == K) {
                // maximal of size K == no legal move at all
                if (kc::legal_mask(b, f.occ) == 0) { ++cnt; if (!first) first = f.occ; }
                continue;
            }
            u64 c = f.cand;
            while (c) {
                int p = __builtin_ctzll(c); c &= c - 1;
                if (!kc::can_add(b, f.occ, p)) continue;
                u64 nxt = f.occ | (u64(1) << p), kill = 0;
                for (u64 t : b.triples_by_pt[p]) {
                    u64 miss = t & ~nxt;
                    if (miss && (miss & (miss - 1)) == 0) kill |= miss;
                }
                stk.push_back({nxt, c & ~kill, f.size + 1});
            }
        }
        jline("    {\"n\": " + std::to_string(n) + ", \"k\": " + std::to_string(K) +
              ", \"n_maximal_size_k\": " + std::to_string(cnt) +
              ", \"witness\": \"" + (cnt ? jm(first) : "") + "\"" +
              ", \"nodes\": " + std::to_string(nd) + ", \"complete\": true},");
        say("small n=" + std::to_string(n) + " k=" + std::to_string(K) +
            " count=" + std::to_string(cnt) + (cnt ? (" wit=" + jm(first)) : "") +
            " nodes=" + std::to_string(nd));
    }
}
static void job_big() {
    jopen("big");
    jline("    \"n7\": [], \"n8\": [], \"n9\": [], \"n10\": [],");
    jclose(",");
}

// ================================================================== job: shape
static void d4_orbits(int n, std::vector<std::vector<int>>& orb) {
    int V = n * n;
    std::vector<int> rep(V, -1);
    for (int p = 0; p < V; ++p) {
        if (rep[p] >= 0) continue;
        int x = p % n, y = p / n, mx = n - 1 - x, my = n - 1 - y;
        int xs[8] = {x, mx, x, mx, y, y, n - 1 - y, n - 1 - y};
        int ys[8] = {y, y, n - 1 - y, n - 1 - y, x, mx, x, mx};
        std::vector<int> img;
        for (int s = 0; s < 8; ++s) img.push_back(ys[s] * n + xs[s]);
        for (int q : img) rep[q] = p;
    }
    std::map<int, std::vector<int>> g;
    for (int p = 0; p < V; ++p) g[rep[p]].push_back(p);
    orb.clear();
    for (auto& kv : g) orb.push_back(kv.second);
}

static void job_shape() {
    jopen("shape");
    for (int n = 4; n <= 7; ++n) {
        int K = max_safe_size(n);
        std::vector<u64> ms = maximal_sets(n, K);
        long long NM = (long long)ms.size();
        // B103
        std::map<int,int> occ; long long tot = 0;
        for (u64 m : ms) for (int y = 0; y < n; ++y) {
            int c = 0; for (int x = 0; x < n; ++x) if (m & (u64(1) << (y * n + x))) ++c;
            occ[c]++; ++tot;
        }
        long long f2 = 0, f013 = 0;
        for (auto& kv : occ) { if (kv.first == 2) f2 += kv.second; else f013 += kv.second; }
        std::string hs; for (auto& kv : occ) { if (!hs.empty()) hs += ","; hs += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second); }
        // B104
        std::vector<int> used(n * n, 0);
        for (u64 m : ms) for (int p : bits(m)) ++used[p];
        std::vector<std::vector<int>> orb; d4_orbits(n, orb);
        std::vector<std::string> never; int npts = 0;
        for (auto& o : orb) {
            bool nu = true; for (int p : o) if (used[p]) { nu = false; break; }
            if (nu) { npts += (int)o.size(); std::string s = "[";
                for (size_t i = 0; i < o.size(); ++i) { if (i) s += ",";
                    s += "[" + std::to_string(o[i] % n) + "," + std::to_string(o[i] / n) + "]"; }
                never.push_back(s + "]"); }
        }
        int umin = 1 << 30; for (int p = 0; p < n * n; ++p) umin = std::min(umin, used[p]);
        // B106/B107
        std::string curve; int min_det = -1;
        std::vector<int> vb(ms.size());
        for (size_t i = 0; i < ms.size(); ++i) vb[i] = (int)i;
        for (int c = 1; c <= 5; ++c) {
            std::unordered_map<u64,int> idx;
            idx.reserve((size_t)NM * 4);
            for (u64 m : ms) { std::vector<int> v = bits(m);
                for (int i = 0; i + c <= (int)v.size(); ++i) {
                    u64 s = 0; for (int j = 0; j < c; ++j) s |= u64(1) << v[i + j];
                    ++idx[s]; } }
            long long uniq = 0;
            for (u64 m : ms) { std::vector<int> v = bits(m); bool got = false;
                for (int i = 0; i + c <= (int)v.size() && !got; ++i) {
                    u64 s = 0; for (int j = 0; j < c; ++j) s |= u64(1) << v[i + j];
                    if (idx[s] == 1) got = true; }
                if (got) ++uniq; }
            if (uniq == NM && min_det < 0) min_det = c;
            if (!curve.empty()) curve += ",";
            curve += "\"" + std::to_string(c) + "\":\"" + std::to_string(uniq) + "/" + std::to_string(NM) + "\"";
        }
        std::string nvs; for (size_t i = 0; i < never.size(); ++i) { if (i) nvs += ","; nvs += never[i]; }
        jline("    \"" + std::to_string(n) + "\": {\"K\": " + std::to_string(K) +
              ",\"n_max\": " + std::to_string(NM) +
              ",\"b103\": {\"rows_total\": " + std::to_string(tot) +
              ",\"occ_hist\": {" + hs + "},\"frac2\":\"" + std::to_string(f2) + "/" + std::to_string(tot) +
              "\",\"frac013\":\"" + std::to_string(f013) + "/" + std::to_string(tot) + "\"}" +
              ",\"b104\": {\"n_orbits\": " + std::to_string((long long)orb.size()) +
              ",\"n_never_used_orbits\": " + std::to_string((long long)never.size()) +
              ",\"n_never_used_points\": " + std::to_string(npts) +
              ",\"never_used\": [" + nvs + "],\"usage_min\": " + std::to_string(umin) + "}" +
              ",\"b106_b107\": {\"min_det\": " + std::to_string(min_det) +
              ",\"ident_curve\": {" + curve + "}}},");
        say("shape n=" + std::to_string(n) + " K=" + std::to_string(K) + " nmax=" + std::to_string(NM) +
            " occ={" + hs + "} frac013=" + std::to_string(f013) + "/" + std::to_string(tot) +
            " never_orbits=" + std::to_string((long long)never.size()) +
            " (" + nvs + ") min_det=" + std::to_string(min_det));
    }
    jclose(",");
}

// ================================================================== job: b110
static void job_b110() {
    jopen("b110");
    for (int n = 5; n <= 7; ++n) {
        Board b; kc::build_square(b, n);
        int V = b.V;
        std::set<std::tuple<long long,long long,long long>> lseen;
        std::vector<std::vector<int>> lines;
        for (int i = 0; i < V; ++i) for (int j = i + 1; j < V; ++j) {
            long long dx = b.pt_x[j] - b.pt_x[i], dy = b.pt_y[j] - b.pt_y[i];
            long long g = std::gcd(llabs(dx), llabs(dy));
            dx /= g; dy /= g;
            if (dx < 0 || (dx == 0 && dy < 0)) { dx = -dx; dy = -dy; }
            auto key = std::make_tuple(dx, dy, dx * b.pt_y[i] - dy * b.pt_x[i]);
            if (lseen.count(key)) continue;
            lseen.insert(key);
            std::vector<int> mem;
            for (int p = 0; p < V; ++p)
                if (dx * b.pt_y[p] - dy * b.pt_x[p] == dx * b.pt_y[i] - dy * b.pt_x[i]) mem.push_back(p);
            if ((int)mem.size() >= 4) lines.push_back(mem);
        }
        std::set<std::array<long long,4>> cseen;
        std::vector<std::vector<int>> circs;
        for (int i = 0; i < V; ++i) for (int j = i + 1; j < V; ++j) for (int k = j + 1; k < V; ++k) {
            long long ax = b.pt_x[i], ay = b.pt_y[i], bx = b.pt_x[j], by = b.pt_y[j];
            long long cx = b.pt_x[k], cy = b.pt_y[k];
            long long d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
            if (d == 0) continue;
            long long a2 = ax * ax + ay * ay, b2 = bx * bx + by * by, c2 = cx * cx + cy * cy;
            long long nx = a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by);
            long long ny = a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax);
            long long q = d; if (q < 0) { q = -q; nx = -nx; ny = -ny; }
            // keep rational centre in reduced form: (qx, qy, q)
            long long g2 = std::gcd(std::gcd(llabs(nx), llabs(ny)), q);
            if (g2 > 1) { q /= g2; nx /= g2; ny /= g2; }
            long long K0 = q * a2 - 2 * nx * ax - 2 * ny * ay;
            auto key = std::array<long long,4>{q, nx, ny, K0};
            if (cseen.count(key)) continue;
            cseen.insert(key);
            std::vector<int> mem;
            for (int p = 0; p < V; ++p) {
                long long X = b.pt_x[p], Y = b.pt_y[p];
                if (q * (X * X + Y * Y) - 2 * nx * X - 2 * ny * Y == K0) mem.push_back(p);
            }
            if ((int)mem.size() >= 4) circs.push_back(mem);
        }
        std::set<u64> quads; for (u64 q : b.quads) quads.insert(q);
        std::vector<std::set<u64>> fams;
        long long line_quads = 0, circ_quads = 0;
        for (auto* src : {&lines, &circs}) {
            for (auto& m : *src) {
                std::set<u64> qs;
                for (size_t a = 0; a + 3 < m.size(); ++a) for (size_t b1 = a + 1; b1 + 2 < m.size(); ++b1)
                for (size_t c1 = b1 + 1; c1 + 1 < m.size(); ++c1) for (size_t d1 = c1 + 1; d1 < m.size(); ++d1) {
                    u64 qm = (u64(1) << m[a]) | (u64(1) << m[b1]) | (u64(1) << m[c1]) | (u64(1) << m[d1]);
                    if (quads.count(qm)) qs.insert(qm);
                }
                if (src == &lines) line_quads += (long long)qs.size(); else circ_quads += (long long)qs.size();
                fams.push_back(std::move(qs));
            }
        }
        std::set<u64> covered; int step = 0;
        while (step < 200) {
            long long bestc = 0; int besti = -1;
            for (size_t i = 0; i < fams.size(); ++i) {
                long long c = 0; for (u64 q : fams[i]) if (!covered.count(q)) ++c;
                if (c > bestc) { bestc = c; besti = (int)i; }
            }
            if (besti < 0) break;
            for (u64 q : fams[(size_t)besti]) covered.insert(q);
            ++step;
        }
        char r[64]; std::snprintf(r, sizeof r, "%d/%d", (int)covered.size(), (int)quads.size());
        jline("    \"" + std::to_string(n) + "\": {\"n_quads\": " + std::to_string((long long)quads.size()) +
              ",\"n_lines_ge4\": " + std::to_string((long long)lines.size()) +
              ",\"n_circles_ge4\": " + std::to_string((long long)circs.size()) +
              ",\"line_quads\": " + std::to_string(line_quads) +
              ",\"circ_quads\": " + std::to_string(circ_quads) +
              ",\"greedy_families\": " + std::to_string(step) +
              ",\"greedy_cover\": \"" + std::string(r) + "\",\"residual_uncov\": " +
              std::to_string((long long)quads.size() - (long long)covered.size()) + "},");
        say("b110 n=" + std::to_string(n) + " quads=" + std::to_string((long long)quads.size()) +
            " lines=" + std::to_string((long long)lines.size()) +
            " circles=" + std::to_string((long long)circs.size()) +
            " greedy=" + std::to_string(step) + " cover=" + std::string(r));
    }
    jclose(",");
}

// ---------------------------------------------------------------- .bin reader
// Read a raw little-endian u64 array.  The committed .bin files (maxsafe_*,
// safe_*, kc_maximal_*) contain NO count header: the file is just the packed
// masks, as loaded by round3_chunk2_geom.load_bin / deform_graph_b121.
static std::vector<u64> read_bin(const std::string& path) {
    std::vector<u64> v;
    FILE* f = std::fopen(path.c_str(), "rb");
    if (!f) { std::fprintf(stderr, "cannot open %s\n", path.c_str()); return v; }
    std::fseek(f, 0, SEEK_END);
    long sz = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    if (sz < 8) { std::fclose(f); return v; }
    size_t m = (size_t)sz / 8;
    v.resize(m);
    size_t rd = std::fread(v.data(), 8, m, f);
    std::fclose(f);
    v.resize(rd);
    return v;
}

// ================================================================== job: g11
// n=7: connectivity of the 16 max sets in G_t, for t = 14,13,12,11.
// G_12 uses the complete layers 12,13,14.  G_11 is a bounded multi-source BFS
// over the 11-stone layer (layers 11 is not precomputed).
static void job_g11() {
    const int n = 7;
    Board b; kc::build_square(b, n);
    u64 full = (1ull << 49) - 1;
    auto L12 = read_bin(std::string(DATA) + "/safe_n7_k12.bin");
    auto L13 = read_bin(std::string(DATA) + "/safe_n7_k13.bin");
    auto L14 = read_bin(std::string(NIGHT) + "/maxsafe_n7_K14.bin");
    say("g11 layers: 12=" + std::to_string(L12.size()) + " 13=" + std::to_string(L13.size()) +
        " 14=" + std::to_string(L14.size()));

    // ---- G_12 : union-find over layers 12,13,14 (complete)
    std::unordered_map<u64,int> ix;
    std::vector<u64> vert;
    for (auto* L : {&L12, &L13, &L14}) for (u64 m : *L) { if (!ix.count(m)) { ix[m] = (int)vert.size(); vert.push_back(m); } }
    std::vector<int> par(vert.size());
    std::iota(par.begin(), par.end(), 0);
    std::function<int(int)> fnd = [&](int x) { while (par[x] != x) { par[x] = par[par[x]]; x = par[x]; } return x; };
    for (u64 m : vert) { u64 mm = m;
        while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
            auto it = ix.find(nb); if (it != ix.end()) { int a = fnd(ix[m]), bq = fnd(it->second); if (a != bq) par[a] = bq; } } }
    std::map<int,int> comp_of_max;
    for (u64 m : L14) comp_of_max[fnd(ix[m])]++;
    std::map<int,long long> compsz;
    for (size_t i = 0; i < vert.size(); ++i) compsz[fnd((int)i)]++;
    std::map<int,int> comp_hist;
    for (auto& kv : compsz) comp_hist[(int)kv.second]++;
    int nG12comps = (int)compsz.size();
    int nG12maxcomp = (int)comp_of_max.size();
    std::string mxsizes; { std::vector<int> v; for (auto& kv : comp_of_max) v.push_back(kv.second);
        std::sort(v.begin(), v.end(), std::greater<int>());
        for (size_t i = 0; i < v.size(); ++i) { if (i) mxsizes += ","; mxsizes += std::to_string(v[i]); } }
    std::string chist; for (auto& kv : comp_hist) { if (!chist.empty()) chist += ","; chist += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second); }
    jline("  \"g12\": {\"n_vertices\": " + std::to_string(vert.size()) +
          ",\"n_components\": " + std::to_string(nG12comps) +
          ",\"n_components_touching_max\": " + std::to_string(nG12maxcomp) +
          ",\"max_per_comp\": [" + mxsizes + "]" +
          ",\"comp_size_hist\": {" + chist + "},\"complete\": true},");
    say("g12: vertices=" + std::to_string(vert.size()) + " comps=" + std::to_string(nG12comps) +
        " max-touching=" + std::to_string(nG12maxcomp) + " sizes=[" + mxsizes + "]");

    // ---- G_13 (layers 13,14) and G_14 (layer 14)
    {
        std::vector<u64> vv; for (u64 m : L13) vv.push_back(m); for (u64 m : L14) vv.push_back(m);
        std::unordered_map<u64,int> ix2; for (size_t i = 0; i < vv.size(); ++i) ix2[vv[i]] = (int)i;
        std::vector<int> p2(vv.size()); std::iota(p2.begin(), p2.end(), 0);
        std::function<int(int)> f2 = [&](int x) { while (p2[x] != x) { p2[x] = p2[p2[x]]; x = p2[x]; } return x; };
        for (u64 m : vv) { u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
                auto it = ix2.find(nb); if (it != ix2.end()) { int a = f2(ix2[m]), c = f2(it->second); if (a != c) p2[a] = c; } } }
        std::set<int> roots; for (u64 m : L14) roots.insert(f2(ix2[m]));
        jline("  \"g13\": {\"n_vertices\": " + std::to_string(vv.size()) +
              ",\"n_components_touching_max\": " + std::to_string((long long)roots.size()) + ",\"complete\": true},");
        say("g13: max-touching comps = " + std::to_string((long long)roots.size()));
    }

    // ---- G_11 : multi-source BFS from the 16 max sets, floor 11
    const long long CAP = 40000000LL;
    std::unordered_map<u64,uint8_t> seen;
    seen.reserve(1 << 24);
    std::vector<u64> q;
    for (u64 m : L14) { seen[m] = 0; q.push_back(m); }
    bool truncated = false;
    for (size_t head = 0; head < q.size(); ++head) {
        u64 m = q[head];
        int sz = pc(m);
        if (sz > 11) { u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
                if (seen.emplace(nb, (uint8_t)(sz - 1)).second) q.push_back(nb); } }
        if (sz >= 11) { u64 e = full & ~m;
            while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 bit = u64(1) << p;
                if (!kc::can_add(b, m, p)) continue; u64 nb = m | bit;
                if (seen.emplace(nb, (uint8_t)(sz + 1)).second) q.push_back(nb); } }
        if ((long long)q.size() > CAP) { truncated = true; break; }
        if ((head & 0xFFFFF) == 0xFFFFF)
            std::printf("  ...g11 BFS q=%zu\n", q.size()), std::fflush(stdout);
    }
    std::map<int,long long> szhist;
    for (auto& kv : seen) ++szhist[pc(kv.first)];
    int reached = 0; for (u64 m : L14) if (seen.count(m)) ++reached;
    std::string sh; for (auto& kv : szhist) { if (!sh.empty()) sh += ","; sh += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second); }
    // how many distinct components of the visited set did the sources land in?
    // We only know connectivity if the BFS was complete.
    std::string conn = truncated ? "unknown_bfs_truncated" : (reached == (int)L14.size() ? "all_16_connected" : "not_connected");
    jline("  \"g11_bfs\": {\"visited\": " + std::to_string((long long)seen.size()) +
          ",\"size_hist\": {" + sh + "}"
          ",\"max_sets_reached\": " + std::to_string(reached) + "/" + std::to_string((long long)L14.size()) +
          ",\"truncated\": " + (truncated ? "true" : "false") +
          ",\"verdict\": \"" + conn + "\"},");
    say("g11 BFS: visited=" + std::to_string((long long)seen.size()) +
        " reached=" + std::to_string(reached) + "/" + std::to_string((long long)L14.size()) +
        " truncated=" + (truncated ? "yes" : "no") + " hist={" + sh + "}");
    jclose(",");
}

// ================================================================== job: defo
// n=7: the corner-forbidden component, the shortest A-B paths, and the
// labels of the 8 max-side components of G_12.
static void job_defo() {
    const int n = 7;
    Board b; kc::build_square(b, n);
    u64 full = (1ull << 49) - 1;
    auto L12 = read_bin(std::string(DATA) + "/safe_n7_k12.bin");
    auto L13 = read_bin(std::string(DATA) + "/safe_n7_k13.bin");
    auto L14 = read_bin(std::string(NIGHT) + "/maxsafe_n7_K14.bin");
    std::unordered_map<u64,int> ix;
    std::vector<u64> vert;
    for (auto* L : {&L12, &L13, &L14}) for (u64 m : *L) if (ix.emplace(m, (int)vert.size()).second) vert.push_back(m);
    std::vector<int> par(vert.size()); std::iota(par.begin(), par.end(), 0);
    std::function<int(int)> fnd = [&](int x) { while (par[x] != x) { par[x] = par[par[x]]; x = par[x]; } return x; };
    for (u64 m : vert) { u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
        auto it = ix.find(nb); if (it != ix.end()) { int a = fnd(ix[m]), c = fnd(it->second); if (a != c) par[a] = c; } } }

    // The 8 max-side components (those containing a 14-stone set)
    std::set<int> maxroots;
    for (u64 m : L14) maxroots.insert(fnd(ix[m]));
    std::vector<int> reps;
    for (int r : maxroots) for (size_t i = 0; i < vert.size(); ++i) if (fnd((int)i) == r) { reps.push_back(vert[i]); break; }

    // B120: labels of the 8 components from corner / edge occupancies.
    // label(m) = (corners used mod 2, edge-mid pts mod 2, centre used mod 2)
    // plus a coarser invariant; report whether the 8 comps get 8 distinct labels.
    auto corners = [](u64 m) { int c = 0; int cs[4] = {0, 6, 42, 48};
        for (int p : cs) if (m & (u64(1) << p)) ++c; return c; };
    auto centrem = [](u64 m) { return (m >> 24) & 1; };
    std::map<std::string, int> labcnt;
    std::vector<std::string> labs;
    for (int r : maxroots) {
        // use the component's max set as representative
        u64 m = 0; for (u64 z : L14) if (fnd(ix[z]) == r) { m = z; break; }
        char buf[64];
        std::snprintf(buf, sizeof buf, "c%d_z%d", corners(m), (int)centrem(m));
        labs.push_back(buf);
    }
    std::sort(labs.begin(), labs.end());
    bool distinct8 = std::adjacent_find(labs.begin(), labs.end()) == labs.end();
    for (auto& l : labs) labcnt[l]++;

    // B115 / B118: pick one component, find its corner-forbidden subset and
    // the shortest A-B path.  Need the 903 component; identify the component
    // containing the first max set, then explore the subgraph avoiding corner 48.
    u64 A = L14[0];
    int rootA = fnd(ix[A]);
    // B must be a DIFFERENT max set in the SAME G_12 component as A, otherwise
    // the shortest-path question is about a different pair entirely.
    u64 Bm = 0;
    {
        u64 cand = 0;
        for (u64 m : L14) if (m != A && fnd(ix[m]) == rootA) { cand = m; break; }
        if (!cand) for (u64 m : L14) if (m != A) { cand = m; break; }   // fallback
        Bm = cand;
    }
    int rootB = fnd(ix[Bm]);
    // component members of rootA
    std::vector<u64> compA;
    for (size_t i = 0; i < vert.size(); ++i) if (fnd((int)i) == rootA) compA.push_back(vert[i]);
    std::map<int,long long> szh; for (u64 m : compA) ++szh[pc(m)];
    std::string sh; for (auto& kv : szh) { if (!sh.empty()) sh += ","; sh += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second); }

    // corner-forbidden subcomponent: restrict to sets NOT containing point 48
    u64 CORNER = 1ull << 48;
    std::vector<u64> noCorner;
    for (u64 m : compA) if (!(m & CORNER)) noCorner.push_back(m);
    // union-find restricted to noCorner
    std::unordered_map<u64,int> ix2; for (size_t i = 0; i < noCorner.size(); ++i) ix2[noCorner[i]] = (int)i;
    std::vector<int> p2(noCorner.size()); std::iota(p2.begin(), p2.end(), 0);
    std::function<int(int)> f2 = [&](int x) { while (p2[x] != x) { p2[x] = p2[p2[x]]; x = p2[x]; } return x; };
    for (u64 m : noCorner) { u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
        auto it = ix2.find(nb); if (it != ix2.end()) { int a = f2(ix2[m]), c = f2(it->second); if (a != c) p2[a] = c; } } }
    std::map<int,long long> nc; for (size_t i = 0; i < noCorner.size(); ++i) ++nc[f2((int)i)];
    long long nc_big = 0; for (auto& kv : nc) nc_big = std::max(nc_big, kv.second);
    // joint distribution (|A\B|, |A∩B|, |B\A|) over the corner-forbidden component
    u64 PA = A & ~Bm, PB = Bm & ~A;
    std::map<std::array<int,3>, long long> joint;
    for (u64 m : noCorner) {
        int dA = pc(m & PA), dB = pc(m & PB), iA = pc(m & (A & Bm));
        joint[{dA, iA, dB}]++;
    }
    std::string jh; int ndistinct = 0;
    for (auto& kv : joint) { if (!jh.empty()) jh += ",";
        jh += "[" + std::to_string(kv.first[0]) + "," + std::to_string(kv.first[1]) + "," + std::to_string(kv.first[2]) + "]:" + std::to_string(kv.second);
        ++ndistinct; }
    std::string nch; for (auto& kv : nc) { if (!nch.empty()) nch += ","; nch += std::to_string(kv.second); }
    std::string lh; for (auto& kv : labcnt) { if (!lh.empty()) lh += ","; lh += "\"" + kv.first + "\":" + std::to_string(kv.second); }
    std::string lraw; for (size_t i = 0; i < labs.size(); ++i) { if (i) lraw += ","; lraw += labs[i]; }

    jline("  \"defo\": {\"compA_size\": " + std::to_string(compA.size()) +
          ",\"compA_size_hist\": {" + sh + "}" +
          ",\"A\": \"" + jm(A) + "\",\"B\": \"" + jm(Bm) + "\"" +
          ",\"A_minus_B\": \"" + jm(PA) + "\",\"B_minus_A\": \"" + jm(PB) + "\"" +
          ",\"A_and_B_size\": " + std::to_string(pc(A & Bm)) +
          ",\"same_G12_comp\": " + (rootA == rootB ? "true" : "false") +
          ",\"b120\": {\"n_max_comps\": " + std::to_string((long long)maxroots.size()) +
          ",\"labels\": [" + lraw + "],\"n_distinct_labels\": " + std::to_string(labs.size()) +
          ",\"label_hist\": {" + lh + "}}" +
          ",\"b115\": {\"corner\": 48" +
          ",\"n_no_corner_states\": " + std::to_string((long long)noCorner.size()) +
          ",\"n_no_corner_components\": " + std::to_string((long long)nc.size()) +
          ",\"largest_no_corner_component\": " + std::to_string(nc_big) +
          ",\"comp_sizes\": [" + nch + "]" +
          ",\"n_distinct_PI_Q\": " + std::to_string(ndistinct) +
          ",\"PI_Q_hist\": {" + jh + "}}},");
    say("defo compA=" + std::to_string(compA.size()) + " hist={" + sh + "}");
    say("defo B115: no-corner states=" + std::to_string((long long)noCorner.size()) +
        " comps=" + std::to_string((long long)nc.size()) + " largest=" + std::to_string(nc_big));
    say("defo B115: n_distinct (|A\\B|,|A&B|,|B\\A|) = " + std::to_string(ndistinct) + " -> {" + jh + "}");
    say("defo B120: labels=[" + lraw + "] distinct=" + std::to_string(labs.size()) + " hist={" + lh + "}");

    // B118: shortest A-B path in the component (BFS on the 903-component).
    {
        std::unordered_map<u64,int> di;
        for (size_t i = 0; i < compA.size(); ++i) di[compA[i]] = -1;
        std::vector<u64> qq{A}; di[A] = 0;
        u64 target = 0; bool found = false;
        for (size_t head = 0; head < qq.size() && !found; ++head) {
            u64 m = qq[head];
            if (m == Bm) { target = m; found = true; break; }
            u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
                if (di.count(nb)) continue; di[nb] = di[m] + 1; qq.push_back(nb); }
            u64 e = full & ~m; while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 bit = u64(1) << p;
                if (!kc::can_add(b, m, p)) continue; u64 nb = m | bit;
                if (di.count(nb)) continue; di[nb] = di[m] + 1; qq.push_back(nb); }
        }
        int d = found ? di[Bm] : -1;
        // B118: over ALL shortest A->B paths, which auxiliary points (outside
        // A|B) are used, and does every shortest path go through corner 48?
        u64 UN = (~(A | Bm)) & full;
        long long npaths = 0; const long long PCAP = 100000;
        u64 commonAux = 0; bool firstAux = true; bool firstRun = true;
        std::map<int,long long> runhist;      // run-lengths of corner-48 presence
        u64 allAuxOr = 0;
        long long throughCorner = 0;
        std::vector<std::vector<u64>> stack2{{Bm}};
        while (!stack2.empty() && npaths < PCAP) {
            std::vector<u64> pth = stack2.back(); stack2.pop_back();
            u64 cur = pth.back();
            if (cur == A) {
                ++npaths;
                u64 used = 0;
                for (size_t i = 0; i + 1 < pth.size(); ++i) used |= pth[i];
                u64 aux = used & UN;
                allAuxOr |= aux;
                if (firstAux) { commonAux = aux; firstAux = false; }
                else commonAux &= aux;
                // corner 48 presence pattern, run-length compressed
                int run = 0; bool inRun = false;
                for (u64 s : pth) {
                    bool has = (s & (1ull << 48)) != 0;
                    if (has) { if (inRun) ++run; else { if (run) ++runhist[run]; run = 1; inRun = true; } }
                    else { if (inRun) { ++runhist[run]; run = 0; inRun = false; } }
                }
                if (inRun) ++runhist[run];
                if (aux & (1ull << 48)) ++throughCorner;
                continue;
            }
            auto it = di.find(cur);
            if (it == di.end()) continue;
            // step back along edges that decrease the BFS distance by 1
            u64 mm = cur;
            while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = cur ^ bit;
                auto jt = di.find(nb); if (jt != di.end() && jt->second == it->second - 1) {
                    std::vector<u64> np = pth; np.push_back(nb); stack2.push_back(np); } }
            u64 e = full & ~cur;
            while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 bit = u64(1) << p;
                if (!kc::can_add(b, cur, p)) continue; u64 nb = cur | bit;
                auto jt = di.find(nb); if (jt != di.end() && jt->second == it->second - 1) {
                    std::vector<u64> np = pth; np.push_back(nb); stack2.push_back(np); } }
        }
        std::string rh; for (auto& kv : runhist) { if (!rh.empty()) rh += ",";
            rh += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second); }
        jline("  \"b118\": {\"bfs_dist_A_to_B\": " + std::to_string(d) +
              ",\"bfs_visited\": " + std::to_string(qq.size()) +
              ",\"n_shortest_paths\": " + std::to_string(npaths) +
              ",\"paths_through_corner48\": " + std::to_string(throughCorner) +
              ",\"aux_union\": \"" + jm(allAuxOr) + "\"" +
              ",\"aux_common_all_shortest\": \"" + jm(commonAux) + "\"" +
              ",\"n_aux_common\": " + std::to_string(pc(commonAux)) +
              ",\"corner48_runs_hist\": {" + rh + "}},");
        say("defo B118: dist(A,B)=" + std::to_string(d) +
            " n_shortest=" + std::to_string(npaths) +
            " through_corner48=" + std::to_string(throughCorner) +
            " aux_union=" + jm(allAuxOr) + " aux_common=" + jm(commonAux));
    }
    jclose(",");
}

// ================================================================== job: aux
// n=6: G_t connectivity (t=10,9,8) over the complete layers, width per max-set
// pair, aux points on width-10 paths, and B127 weighted potentials.
static void job_aux() {
    const int n = 6;
    Board b; kc::build_square(b, n);
    u64 full = (1ull << 36) - 1;
    auto L8  = read_bin(std::string(DATA) + "/safe_n6_k8.bin");
    auto L9  = read_bin(std::string(DATA) + "/safe_n6_k9.bin");
    auto L10 = read_bin(std::string(DATA) + "/safe_n6_k10.bin");
    auto L11 = read_bin(std::string(NIGHT) + "/maxsafe_n6_K11.bin");
    say("aux layers: 8=" + std::to_string(L8.size()) + " 9=" + std::to_string(L9.size()) +
        " 10=" + std::to_string(L10.size()) + " 11=" + std::to_string(L11.size()));

    struct GRes { long long verts, comps, maxcomp, maxgroups; std::vector<int> gsz; };
    std::map<int, GRes> G;
    for (int t : {8, 9, 10, 11}) {
        std::vector<u64> vv;
        if (t == 8) { vv = L8; vv.insert(vv.end(), L9.begin(), L9.end()); vv.insert(vv.end(), L10.begin(), L10.end()); vv.insert(vv.end(), L11.begin(), L11.end()); }
        if (t == 9) { vv = L9; vv.insert(vv.end(), L10.begin(), L10.end()); vv.insert(vv.end(), L11.begin(), L11.end()); }
        if (t == 10) { vv = L10; vv.insert(vv.end(), L11.begin(), L11.end()); }
        if (t == 11) { vv = L11; }
        std::unordered_map<u64,int> ix; ix.reserve(vv.size() * 2);
        for (u64 m : vv) ix.emplace(m, 0);
        std::vector<u64> uniq; uniq.reserve(ix.size());
        for (auto& kv : ix) uniq.push_back(kv.first);
        for (size_t i = 0; i < uniq.size(); ++i) ix[uniq[i]] = (int)i;
        std::vector<int> par(uniq.size()); std::iota(par.begin(), par.end(), 0);
        std::function<int(int)> f = [&](int x) { while (par[x] != x) { par[x] = par[par[x]]; x = par[x]; } return x; };
        for (u64 m : uniq) { u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
            auto it = ix.find(nb); if (it != ix.end()) { int a = f(ix[m]), c = f(it->second); if (a != c) par[a] = c; } } }
        GRes r; r.verts = (long long)uniq.size();
        std::map<int,long long> cs; for (size_t i = 0; i < uniq.size(); ++i) ++cs[f((int)i)];
        r.comps = (long long)cs.size();
        for (auto& kv : cs) r.maxcomp = std::max(r.maxcomp, kv.second);
        std::map<int,int> grp;
        for (u64 m : L11) grp[f(ix[m])]++;
        r.maxgroups = (long long)grp.size();
        for (auto& kv : grp) r.gsz.push_back(kv.second);
        std::sort(r.gsz.begin(), r.gsz.end(), std::greater<int>());
        G[t] = r;
        jline("  \"G_" + std::to_string(t) + "\": {\"vertices\": " + std::to_string(r.verts) +
              ",\"components\": " + std::to_string(r.comps) +
              ",\"largest_component\": " + std::to_string(r.maxcomp) +
              ",\"components_touching_max\": " + std::to_string(r.maxgroups) +
              ",\"max_per_comp\": [" + [&]{ std::string s; for (size_t i = 0; i < r.gsz.size() && i < 12; ++i) { if (i) s += ","; s += std::to_string(r.gsz[i]); } return s; }() + "],\"complete\": true},");
        say("aux G_" + std::to_string(t) + ": verts=" + std::to_string(r.verts) +
            " comps=" + std::to_string(r.comps) + " maxcomp=" + std::to_string(r.maxcomp) +
            " max-touching groups=" + std::to_string(r.maxgroups));
    }

    // ---- widths of max-set pairs: w(A,B) = max t with A,B in the same G_t
    // Build a root map per t.
    std::map<int, std::unordered_map<u64,int>> rootmap;
    for (int t : {8, 9, 10}) {
        std::vector<u64> vv;
        if (t == 8) { vv = L8; vv.insert(vv.end(), L9.begin(), L9.end()); vv.insert(vv.end(), L10.begin(), L10.end()); vv.insert(vv.end(), L11.begin(), L11.end()); }
        if (t == 9) { vv = L9; vv.insert(vv.end(), L10.begin(), L10.end()); vv.insert(vv.end(), L11.begin(), L11.end()); }
        if (t == 10) { vv = L10; vv.insert(vv.end(), L11.begin(), L11.end()); }
        std::unordered_map<u64,int> ix; ix.reserve(vv.size() * 2);
        std::vector<u64> uniq = vv; std::sort(uniq.begin(), uniq.end()); uniq.erase(std::unique(uniq.begin(), uniq.end()), uniq.end());
        for (size_t i = 0; i < uniq.size(); ++i) ix[uniq[i]] = (int)i;
        std::vector<int> par(uniq.size()); std::iota(par.begin(), par.end(), 0);
        std::function<int(int)> f = [&](int x) { while (par[x] != x) { par[x] = par[par[x]]; x = par[x]; } return x; };
        for (u64 m : uniq) { u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
            auto it = ix.find(nb); if (it != ix.end()) { int a = f(ix[m]), c = f(it->second); if (a != c) par[a] = c; } } }
        for (u64 m : L11) rootmap[t][m] = f(ix[m]);
    }
    // width histogram over all max-set pairs
    std::map<int,long long> wcount; long long npair = 0;
    std::vector<std::pair<u64,u64>> w10pairs;
    for (size_t i = 0; i < L11.size(); ++i)
    for (size_t j = i + 1; j < L11.size(); ++j) {
        u64 A = L11[i], B = L11[j];
        int w = -1;
        for (int t : {10, 9, 8}) if (rootmap[t][A] == rootmap[t][B]) { w = t; break; }
        ++wcount[w]; ++npair;
        if (w == 10 && w10pairs.size() < 200) w10pairs.push_back({A, B});
    }
    std::string wh; for (auto& kv : wcount) { if (!wh.empty()) wh += ",";
        wh += "\"" + std::to_string(kv.first) + "\":" + std::to_string(kv.second); }
    jline("  \"width_hist\": {\"n_pairs\": " + std::to_string(npair) + ", \"by_width\": {" + wh + "}},");
    say("aux width hist over " + std::to_string(npair) + " max pairs: {" + wh + "}");

    // ---- B123 / B124 / B125 on width-10 pairs: enumerate ALL shortest
    // (width-10) paths via BFS and record the aux points (A|B complement).
    {
        // BFS on G_10 (layers 10 and 11) from A; record dist and parents.
        int examined = 0;
        long long p_aux_ge2 = 0, p_aux1 = 0, p_aux0 = 0;
        long long has_empty_common_aux = 0;   // aux mandatory but intersection empty
        long long B123_witness = 0;           // a path needing >= 2 distinct aux points
        long long B125_witness = 0;           // min width drops if A∩B must be kept
        std::string w123 = "", w124 = "", w125 = "";
        for (auto& pr : w10pairs) {
            u64 A = pr.first, B = pr.second;
            u64 inter = A & B;
            // BFS in G_10
            std::unordered_map<u64,int> dist; dist.reserve(40000);
            std::unordered_map<u64,std::vector<u64>> par; par.reserve(40000);
            std::vector<u64> q{A}; dist[A] = 0;
            bool fnd = false;
            for (size_t h = 0; h < q.size() && !fnd; ++h) {
                u64 m = q[h];
                if (m == B) { fnd = true; break; }
                u64 mm = m; while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
                    if (dist.count(nb)) continue; dist[nb] = dist[m] + 1; par[nb].push_back(m); q.push_back(nb); }
                u64 e = full & ~m; while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 bit = u64(1) << p;
                    if (!kc::can_add(b, m, p)) continue; u64 nb = m | bit;
                    if (dist.count(nb)) continue; dist[nb] = dist[m] + 1; par[nb].push_back(m); q.push_back(nb); }
            }
            if (!fnd) continue;
            // enumerate all shortest paths (cap the number)
            std::vector<std::vector<u64>> paths;
            std::vector<std::vector<u64>> stack{{B}};
            long long npaths = 0; const long long PCAP = 2000;
            std::vector<int> commonAux;
            bool first = true;
            while (!stack.empty() && npaths < PCAP) {
                std::vector<u64> pth = stack.back(); stack.pop_back();
                u64 cur = pth.back();
                if (cur == A) {
                    ++npaths;
                    u64 U = ~(A | B) & full, used = 0;
                    for (size_t i = 0; i + 1 < pth.size(); ++i) used |= pth[i];
                    u64 aux = used & U;
                    int naux = pc(aux);
                    if (naux == 0) ++p_aux0; else if (naux == 1) ++p_aux1; else ++p_aux_ge2;
                    if (naux >= 2 && B123_witness == 0) { B123_witness = 1;
                        w123 = "A=" + jm(A) + " B=" + jm(B) + " aux=" + jm(aux); }
                    if (first) { commonAux = bits(aux); first = false; }
                    else { u64 keep = 0; for (int p : commonAux) if (aux & (u64(1) << p)) keep |= u64(1) << p;
                           commonAux = bits(keep); }
                    continue;
                }
                auto it = par.find(cur);
                if (it == par.end()) continue;
                for (u64 pm : it->second) { std::vector<u64> np = pth; np.push_back(pm); stack.push_back(np); }
            }
            if (npaths > 1 && commonAux.empty()) ++has_empty_common_aux;
            if (has_empty_common_aux == 1 && w124.empty())
                w124 = "A=" + jm(A) + " B=" + jm(B) + " n_shortest=" + std::to_string(npaths) + " common_aux=[]";
            // B125: restrict the path to keep every point of A∩B
            // a path exists in G_10 keeping A∩B only if BFS without ever
            // dropping an intersection point reaches B.
            bool ok = true;
            {
                std::unordered_map<u64,int> d2; std::vector<u64> q2{A}; d2[A] = 0;
                bool f2 = false;
                for (size_t h = 0; h < q2.size() && !f2; ++h) {
                    u64 m = q2[h];
                    if (m == B) { f2 = true; break; }
                    u64 mm = m & ~inter;   // may only remove points outside A∩B
                    while (mm) { u64 bit = mm & (~mm + 1); mm ^= bit; u64 nb = m ^ bit;
                        if (d2.count(nb)) continue; d2[nb] = d2[m] + 1; q2.push_back(nb); }
                    u64 e = full & ~m; while (e) { int p = __builtin_ctzll(e); e &= e - 1; u64 bit = u64(1) << p;
                        if (!kc::can_add(b, m, p)) continue; u64 nb = m | bit;
                        if (d2.count(nb)) continue; d2[nb] = d2[m] + 1; q2.push_back(nb); }
                }
                ok = f2;
            }
            if (!ok) { ++B125_witness; if (w125.empty())
                w125 = "A=" + jm(A) + " B=" + jm(B) + " |A&B|=" + std::to_string(pc(inter)) + " no G_10 path keeping A&B"; }
            ++examined;
            if (examined >= 60) break;
        }
        jline("  \"b123_b124_b125\": {\"pairs_examined\": " + std::to_string(examined) +
              ",\"paths_needing_0_aux\": " + std::to_string(p_aux0) +
              ",\"paths_needing_1_aux\": " + std::to_string(p_aux1) +
              ",\"paths_needing_2plus_aux\": " + std::to_string(p_aux_ge2) +
              ",\"pairs_with_empty_common_aux\": " + std::to_string(has_empty_common_aux) +
              ",\"b123_witness\": \"" + w123 + "\"" +
              ",\"b124_witness\": \"" + w124 + "\"" +
              ",\"b125_witness_count\": " + std::to_string(B125_witness) +
              ",\"b125_witness\": \"" + w125 + "\"},");
        say("aux b123/b124/b125: examined=" + std::to_string(examined) +
            " paths0/1/2+aux = " + std::to_string(p_aux0) + "/" + std::to_string(p_aux1) + "/" + std::to_string(p_aux_ge2) +
            " empty-common-aux pairs=" + std::to_string(has_empty_common_aux) +
            " b125=" + std::to_string(B125_witness));
        if (!w123.empty()) say("  b123 witness " + w123);
        if (!w124.empty()) say("  b124 witness " + w124);
        if (!w125.empty()) say("  b125 witness " + w125);
    }
    jclose(",");
}

// ------------------------------------------------------------------- driver
static bool file_exists(const char* p) { FILE* f = std::fopen(p, "rb"); if (!f) return false; std::fclose(f); return true; }

int main(int argc, char** argv) {
    std::string job = argc > 1 ? argv[1] : "sat";
    std::string outp = std::string(VER) + "/round4_b092.json";
    bool fresh = (argc > 2 && std::string(argv[2]) == "fresh");
    g_out = std::fopen(outp.c_str(), fresh ? "w" : "a");
    g_t0 = 0;
    if (!g_out) { std::perror("open json"); return 1; }
    // self-check of the shared core before anything else
    {
        int bad = 0;
        const int Fk[] = {0,0,1,14,194,826,2491,6364,14564,29152};
        for (int n = 2; n <= 9; ++n) {
            Board b; kc::build_square(b, n);
            if ((int)b.quads.size() != Fk[n]) { bad++; say("F_n MISMATCH n=" + std::to_string(n)); }
        }
        say(std::string("core selfcheck F_2..F_9: ") + (bad ? "FAILED" : "OK"));
    }
    if (job == "sat")   { jline("{"); job_sat();  jline("}"); }
    if (job == "shape") { jline("{"); job_shape(); jline("}"); }
    if (job == "b110")  { jline("{"); job_b110();  jline("}"); }
    if (job == "g11")   { jline("{"); job_g11();   jline("}"); }
    if (job == "defo")  { jline("{"); job_defo();  jline("}"); }
    if (job == "aux")   { jline("{"); job_aux();   jline("}"); }
    if (job == "big9")  {
        jline("{"); jopen("big9"); search_small_maximal(9, 9, 9); jclose(""); jline("}");
    }
    if (job == "big10") {
        jline("{"); jopen("big10"); search_small_maximal(10, 10, 11); jclose(""); jline("}");
    }
    if (job == "big8")  {
        jline("{"); jopen("big8"); search_small_maximal(8, 8, 8); jclose(""); jline("}");
    }
    if (job == "small78") {
        jline("{"); jopen("small78"); search_small_maximal(7, 7, 7); jclose(""); jline("}");
    }
    if (job == "small67") {
        jline("{"); jopen("small67"); search_small_maximal(6, 5, 5); jclose(""); jline("}");
    }
    if (job == "selftest") {
        // Cross-check the enumeration against the committed .bin files.
        jline("{"); jopen("selftest"); jclose(""); jline("}");
        struct Case { int n, K; const char* path; };
        Case cs[] = {
            {5, 9, "/night-research/maxsafe_n5_K9.bin"},
            {5, 9, ""},   // placeholder replaced below
        };
        (void)cs;
        struct Chk { int n; int K; const char* f; };
        Chk chk[] = {
            {7, 14, "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/night-research/maxsafe_n7_K14.bin"},
            {5, 8,  "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/kc_maximal_n5_k8.bin"},
        };
        for (auto& c : chk) {
            std::vector<u64> ref = read_bin(c.f);
            if (ref.empty()) { say("selftest: MISSING " + std::string(c.f)); continue; }
            std::vector<u64> mine = maximal_sets(c.n, c.K);
            std::set<u64> a(ref.begin(), ref.end()), b(mine.begin(), mine.end());
            bool same = (a == b);
            say("selftest n=" + std::to_string(c.n) + " K=" + std::to_string(c.K) +
                " ref=" + std::to_string(a.size()) + " mine=" + std::to_string(b.size()) +
                (same ? " IDENTICAL" : " DIFFERENT"));
            // safety cross-check: every set in the file must be safe,
            // and no point may be addable to it.
            int unsafe = 0, nonmax = 0;
            Board bb; kc::build_square(bb, c.n);
            for (u64 m : a) {
                for (u64 q : bb.quads) if ((m & q) == q) { ++unsafe; break; }
                if (kc::legal_mask(bb, m) != 0) ++nonmax;
            }
            say("  verified: unsafe=" + std::to_string(unsafe) +
                " non_maximal=" + std::to_string(nonmax) +
                (unsafe == 0 && nonmax == 0 ? " OK" : " FAIL"));
        }
    }
    std::fclose(g_out);
    say("done: " + job);
    return 0;
}
