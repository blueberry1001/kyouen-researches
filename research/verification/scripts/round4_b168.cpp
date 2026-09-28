// round4_b168.cpp -- Round4 verification solver for batch B168-B227 (WSL / g++ 13.3.0).
//
// Shared, already-verified geometry engine: kc_core.h (F_n matches known values).
// Integer-only. Probabilities are exact rationals p/q. No floating point anywhere.
//
// Jobs:
//   cnt      <n>                     enumerate safe sets of n x n (f-vector, K, counts)
//   cnt_rect <w> <m>                 same for a w x m rectangle
//   full     <n> [rand=0/1] [pass=0/1] [rule=0]   n x n, standard rule
//   rect     <w> <m> [rule=0] [rand=0/1] [pass=0/1]
//   q5       <n>                     n x n, forbidden 5-subsets (rank of lifted rows <= 3)
//   del1     <n> [rand=0/1]          every one-point deletion: K, winner, W
//   del2     <n> [rand=0/1]          every two-point deletion: K, winner, W
//   sub      <w> <h> [rand=0/1]      f-vector + g0 of a w x h sub-board (B177 search)
//   ext      <n> [rand=0/1]          n x n plus ONE external point (B208)
//   greedy   <n> <budget>            downward search: keep W_n while deleting quads (B224)
//   disagree <ruleA> <wA> <mA> <ruleB> <wB> <mB>  P/N disagreement rate over common safe sets
//   mod2     <n>                     mod-2 parity-invariant test for P/N (B168)
//   betti    <n> <maxdim>            GF(2) Betti numbers of Delta_n
//   circles  <nmax>                  circle / collinear static statistics n=2..nmax
//   mc       <n> <runs>              random-greedy Monte Carlo with extra logs
#include "kc_core.h"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <random>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

using kc::u64;
static inline int pc(u64 x) { return __builtin_popcountll(x); }

enum Rule { R_STD = 0, R_CIRC = 1, R_LINE = 2, R_Q5 = 3 };
static const u64 CAP_DEFAULT = 120000000ULL;   // safe-set enumeration cap

// ------------------------------------------------------------------ geometry
struct Geo {
  int V = 0;
  int rule = R_STD;
  u64 full = 0;
  std::vector<int> xs, ys;
  std::vector<u64> quads;               // 4-point masks
  std::vector<u64> q5sets;              // 5-point masks
  std::vector<u64> P2;                  // (p*V+a)*V+b -> r  : {p,a,b,r} forbidden
  std::vector<u64> P3;                  // (p*V+a)*V+b -> r  : {p,a,b,r} inside a 5-set
  std::vector<int> deg;                 // initial degree d(p)
};

static long long det4p(int x0, int y0, int x1, int y1, int x2, int y2, int x3, int y3) {
  long long m[4][4];
  int X[4] = {x0, x1, x2, x3}, Y[4] = {y0, y1, y2, y3};
  for (int i = 0; i < 4; ++i) {
    m[i][0] = (long long)X[i] * X[i] + (long long)Y[i] * Y[i];
    m[i][1] = X[i]; m[i][2] = Y[i]; m[i][3] = 1;
  }
  return kc::det4(m);
}
static bool colline(int x0, int y0, int x1, int y1, int x2, int y2, int x3, int y3) {
  long long a = (long long)(x1 - x0) * (y2 - y0) - (long long)(y1 - y0) * (x2 - x0);
  long long b = (long long)(x1 - x0) * (y3 - y0) - (long long)(y1 - y0) * (x3 - x0);
  return a == 0 && b == 0;
}

static void build_rect(Geo& g, int w, int h, int rule) {
  g.rule = rule;
  for (int y = 0; y < h; ++y)
    for (int x = 0; x < w; ++x) { g.xs.push_back(x); g.ys.push_back(y); }
  g.V = (int)g.xs.size();
  g.full = (g.V >= 64) ? ~u64(0) : ((u64(1) << g.V) - 1);
  g.P2.assign((size_t)g.V * g.V * g.V, 0);
  g.deg.assign(g.V, 0);
  if (rule == R_Q5) {
    g.P3.assign((size_t)g.V * g.V * g.V, 0);
    for (int a = 0; a < g.V - 4; ++a) for (int b = a + 1; b < g.V - 3; ++b)
    for (int c = b + 1; c < g.V - 2; ++c) for (int d = c + 1; d < g.V - 1; ++d)
    for (int e = d + 1; e < g.V; ++e) {
      int id[5] = {a, b, c, d, e};
      bool all = true;
      for (int om = 0; om < 5 && all; ++om) {
        int q4[4], t = 0;
        for (int u = 0; u < 5; ++u) if (u != om) q4[t++] = id[u];
        if (det4p(g.xs[q4[0]], g.ys[q4[0]], g.xs[q4[1]], g.ys[q4[1]],
                  g.xs[q4[2]], g.ys[q4[2]], g.xs[q4[3]], g.ys[q4[3]]) != 0) all = false;
      }
      if (!all) continue;
      u64 m = 0; for (int t = 0; t < 5; ++t) m |= u64(1) << id[t];
      g.q5sets.push_back(m);
      for (int t = 0; t < 5; ++t) {
        int p = id[t], o[4], k = 0;
        for (int u = 0; u < 5; ++u) if (u != t) o[k++] = id[u];
        for (int i = 0; i < 4; ++i) for (int j = i + 1; j < 4; ++j) {
          int r = -1;
          for (int u = 0; u < 4; ++u) if (u != i && u != j) r = o[u];
          g.P3[((size_t)p * g.V + o[i]) * g.V + o[j]] |= u64(1) << r;
        }
      }
    }
    for (u64 m : g.q5sets) { u64 t = m; while (t) { int p = __builtin_ctzll(t); t &= t - 1; g.deg[p]++; } }
    return;
  }
  for (int a = 0; a < g.V - 3; ++a) for (int b = a + 1; b < g.V - 2; ++b)
  for (int c = b + 1; c < g.V - 1; ++c) for (int d = c + 1; d < g.V; ++d) {
    long long D = det4p(g.xs[a], g.ys[a], g.xs[b], g.ys[b], g.xs[c], g.ys[c], g.xs[d], g.ys[d]);
    bool ok = false;
    if (D == 0) {
      bool iscol = colline(g.xs[a], g.ys[a], g.xs[b], g.ys[b], g.xs[c], g.ys[c], g.xs[d], g.ys[d]);
      ok = (rule == R_STD) ? true : (rule == R_CIRC ? !iscol : iscol);
    }
    if (!ok) continue;
    int id[4] = {a, b, c, d};
    g.quads.push_back((u64(1) << a) | (u64(1) << b) | (u64(1) << c) | (u64(1) << d));
    for (int t = 0; t < 4; ++t) {
      g.deg[id[t]]++;
      for (int i = 0; i < 4; ++i) for (int j = i + 1; j < 4; ++j) {
        if (i == t || j == t) continue;
        int p = id[t], A = id[i], B = id[j], r = -1;
        for (int u = 0; u < 4; ++u) if (u != t && u != i && u != j) r = id[u];
        g.P2[((size_t)p * g.V + A) * g.V + B] |= u64(1) << r;
      }
    }
  }
}

// -------------------------------------------------------------- enumeration
struct Levels {
  std::vector<std::vector<u64>> lev, lg;
  u64 total = 0;
  bool complete = true;
};

static bool enum_all(const Geo& g, Levels& L, u64 cap) {
  L.lev.clear(); L.lg.clear();
  L.lev.push_back({0}); L.lg.push_back({g.full});
  L.total = 1;
  const u64* PP = (g.rule == R_Q5) ? g.P3.data() : g.P2.data();
  int el[70];
  for (size_t k = 0; k < L.lev.size(); ++k) {
    if (L.lev[k].empty()) break;
    std::vector<u64> nk, nl;
    nk.reserve(L.lev[k].size() * 2); nl.reserve(L.lev[k].size() * 2);
    for (size_t idx = 0; idx < L.lev[k].size(); ++idx) {
      u64 S = L.lev[k][idx], L0 = L.lg[k][idx];
      int ne = 0;
      for (u64 t = S; t; t &= t - 1) el[ne++] = __builtin_ctzll(t);
      int mx = ne ? el[ne - 1] : -1;
      for (int p = mx + 1; p < g.V; ++p) {
        if (!((L0 >> p) & 1)) continue;
        u64 bl = 0;
        for (int i = 0; i < ne; ++i) for (int j = i + 1; j < ne; ++j)
          bl |= PP[((size_t)p * g.V + el[i]) * g.V + el[j]];
        nk.push_back(S | (u64(1) << p));
        nl.push_back((L0 & ~bl) & ~(u64(1) << p));
      }
    }
    L.total += nk.size();
    if (L.total > cap) { L.complete = false; return false; }
    L.lev.push_back(std::move(nk)); L.lg.push_back(std::move(nl));
  }
  // drop trailing empty levels so that K = #levels - 1
  while (L.lev.size() > 1 && L.lev.back().empty()) { L.lev.pop_back(); L.lg.pop_back(); }
  return true;
}

// ----------------------------------------------------------------- indexing
struct MIndex {
  bool direct = false;
  int B = 0;
  std::vector<int> tab;
  u64 hmask = 0;
  std::vector<u64> keys;
  std::vector<int32_t> val;
  std::vector<uint8_t> used;
  static inline u64 hf(u64 k) {
    k *= 0x9E3779B97F4A7C15ULL; k ^= k >> 29;
    k *= 0xBF58476D1CE4E5B9ULL; k ^= k >> 32; return k;
  }
  void init(int V, size_t cnt) {
    if (V <= 23) { direct = true; B = V; tab.assign((size_t)1 << B, -1); return; }
    size_t s = 16; while (s < cnt * 2 + 16) s <<= 1;
    keys.assign(s, 0); val.assign(s, -1); used.assign(s, 0); hmask = s - 1;
  }
  inline void put(u64 k, int32_t v) {
    if (direct) { tab[k] = (int)v; return; }
    u64 h = hf(k) & hmask;
    while (used[h] && keys[h] != k) h = (h + 1) & hmask;
    keys[h] = k; val[h] = v; used[h] = 1;
  }
  inline int32_t get(u64 k) const {
    if (direct) return tab[k];
    u64 h = hf(k) & hmask;
    while (used[h]) { if (keys[h] == k) return val[h]; h = (h + 1) & hmask; }
    return -1;
  }
};
static inline MIndex make_index(int V, const std::vector<u64>& v) {
  MIndex m; m.init(V, v.size() + 8);
  for (size_t i = 0; i < v.size(); ++i) m.put(v[i], (int32_t)i);
  return m;
}

// ------------------------------------------------------------- GF(2) system
struct GF2 {
  int nv = 0, nrows = 0;
  std::vector<u64> rows;
  std::vector<int> rhs;
  void init(int nvars) { nv = nvars; rows.assign(nvars, 0); rhs.assign(nvars, 0); nrows = 0; }
  void add(u64 mask, int r) {
    if (nrows > nv) return;
    int p = -1;
    for (int b = nv - 1; b >= 0; --b) if ((mask >> b) & 1) { p = b; break; }
    while (p >= 0) {
      if (rows[p] & ((u64)1 << p)) {
        mask ^= rows[p]; r ^= rhs[p];
        p = -1;
        for (int b = nv - 1; b >= 0; --b) if ((mask >> b) & 1) { p = b; break; }
      } else {
        rows[p] = mask; rhs[p] = r;
        if (p + 1 > nrows) nrows = p + 1;
        return;
      }
    }
    if (r) nrows = nv + 1;  // inconsistent
  }
  bool consistent() const { return nrows <= nv; }
  u64 solution() const { u64 v = 0; for (int b = 0; b < nv; ++b) if (rows[b]) v |= (u64)rhs[b] << b; return v; }
};

// ------------------------------------------------------------------ result
struct Res {
  int V = 0, K = -1;
  u64 nsets = 0;
  std::vector<u64> f, fP, fmaxnim;
  int g0 = 0, maxnim = 0, minKforMax = -1;
  u64 W = 0;
  int nmaximal = 0;
  long long nmaxset = 0;
  std::vector<int> nmaxlvl;
  std::vector<u64> nmaxlvl_c;
  std::vector<long long> deg;
  int misere0 = -1;                 // 1 = First wins under misere
  int pass0_both = -1, pass0_1p = -1;
  int pass_wit = 0, pw_g = 0, pw_k = 0; u64 pw_m1 = 0, pw_m2 = 0;
  std::vector<long long> med;
  u64 nP = 0, nN = 0;
  int rand_state = 0;               // 0 none, 1 exact, 2 overflow
  u64 mnA = 0, mnT = 0, mnM = 0; int mnk = -1;
  u64 mxA = 0, mxT = 0, mxM = 0; int mxk = -1;
  std::vector<std::vector<u64>> Pby; // per level: exact p-moments for 1/2/3/4-move completions
};

static void solve_full(const Geo& g, bool want_rand, bool want_pass, Res& R, u64 cap) {
  Levels L;
  enum_all(g, L, cap);
  R.V = g.V;
  R.nsets = L.total;
  size_t NL = L.lev.size();
  R.K = (int)NL - 1;
  if (R.K < 0) return;
  R.f.assign(NL, 0); R.fP.assign(NL, 0); R.fmaxnim.assign(NL, 0);
  R.nmaxlvl.assign(NL, 0);
  R.nmaxlvl_c.assign(NL, 0);
  for (size_t k = 0; k < NL; ++k) R.f[k] = L.lev[k].size();
  R.deg.assign(g.deg.begin(), g.deg.end());
  for (size_t k = 0; k < NL; ++k) {
    for (u64 m : L.lg[k]) if (m == 0) R.nmaxlvl[k]++;
    R.nmaxlvl_c[k] = (u64)R.nmaxlvl[k];
    R.nmaximal = std::max(R.nmaximal, R.nmaxlvl[k]);
  }
  R.nmaxset = (long long)L.lev[R.K].size();

  // ---- Grundy, computed TOP-DOWN.
  // The recursion is g(S) = mex{ g(S u {p}) : p legal } for non-terminal S, and
  // g(S) = 0 for terminal (maximal) S.  g(empty) is therefore NOT a free seed: it
  // is determined by the terminal layer.  Levels must be filled from k = K down
  // to k = 0; a bottom-up fill with a seeded g(empty) has a spurious fixed point
  // and misreports every winner.
  std::vector<size_t> lstart(NL + 1, 0);
  std::vector<int8_t> gval(L.total, 0);
  for (size_t k = 0; k < NL; ++k) lstart[k + 1] = lstart[k] + L.lev[k].size();
  {
    std::vector<int> g1(g.V, -1);
    // level K is terminal by construction (L.lev[K] is non-empty and has no successors)
    for (int ki = (int)NL - 2; ki >= 0; --ki) {
      size_t k = (size_t)ki;
      MIndex idxn = make_index(g.V, L.lev[k + 1]);
      const std::vector<u64>& lk = L.lev[k];
      int8_t seen[96];
      for (size_t i = 0; i < lk.size(); ++i) {
        u64 S = lk[i], lm = L.lg[k][i];
        std::memset(seen, 0, sizeof(seen));
        for (u64 t = lm; t; t &= t - 1) {
          int p = __builtin_ctzll(t);
          int32_t j = idxn.get(S | (u64(1) << p));
          if (j >= 0) seen[(int)gval[lstart[k + 1] + j]] = 1;
        }
        int m = 0; while (seen[m]) ++m;
        gval[lstart[k] + i] = (int8_t)m;
        if (k == 1) g1[__builtin_ctzll(S)] = m;
        if (k == 0) R.g0 = m;
      }
    }
    R.W = 0;
    for (int p = 0; p < g.V; ++p) if (g1[p] == 0) R.W |= u64(1) << p;
  }

  R.maxnim = 0; R.minKforMax = -1;
  for (size_t k = 0; k < NL; ++k) {
    int mx = 0; u64 np = 0;
    for (size_t i = 0; i < L.lev[k].size(); ++i) {
      int v = gval[lstart[k] + i];
      if (v > mx) mx = v;
      if (v == 0) np++;
    }
    R.fmaxnim[k] = mx; R.fP[k] = np;
    R.nP += np; R.nN += (L.lev[k].size() - np);
    if (mx > R.maxnim) { R.maxnim = mx; R.minKforMax = (int)k; }
  }

  // ---- misere (player making the last move loses) and the 2-pass variant
  {
    std::vector<uint8_t> mis(gval.size(), 0), pas(gval.size(), 0);
    for (size_t k = NL; k-- > 0;) {
      MIndex ni;
      if (k + 1 < NL) ni = make_index(g.V, L.lev[k + 1]);
      for (size_t i = 0; i < L.lev[k].size(); ++i) {
        u64 S = L.lev[k][i], lm = L.lg[k][i];
        uint8_t mv;
        if (lm == 0) mv = 1;
        else {
          mv = 0;
          for (u64 t = lm; t; t &= t - 1) {
            int p = __builtin_ctzll(t);
            int32_t j = ni.get(S | (u64(1) << p));
            if (j >= 0 && mis[lstart[k + 1] + j] == 0) { mv = 1; break; }
          }
        }
        mis[lstart[k] + i] = mv;

        // pass variant: mask m, bit0 = mover has a pass, bit1 = opponent has a pass.
        uint8_t v = 0;
        for (int m = 0; m < 4; ++m) {
          int win = 0;
          for (u64 t = lm; t && !win; t &= t - 1) {
            int p = __builtin_ctzll(t);
            int sm = ((m & 1) << 1) | ((m & 2) >> 1);
            int32_t j = ni.get(S | (u64(1) << p));
            if (j >= 0 && ((pas[lstart[k + 1] + j] >> sm) & 1) == 0) win = 1;
          }
          if (!win && (m & 1)) {
            int mp = (m & 2) >> 1;               // after the pass it is the opponent's turn
            if (m > mp && ((v >> mp) & 1) == 0) win = 1;
          }
          v |= (uint8_t)(win << m);
        }
        pas[lstart[k] + i] = v;
      }
    }
    R.misere0 = mis[lstart[0]];
    R.pass0_both = (pas[lstart[0]] >> 3) & 1;
    R.pass0_1p = (pas[lstart[0]] >> 1) & 1;
    if (want_pass) {
      for (size_t k = 0; k < NL && !R.pass_wit; ++k) {
        for (size_t i = 0; i < L.lev[k].size(); ++i) {
          size_t gi = lstart[k] + i;
          if (((pas[gi] >> 3) & 1) != 1) continue;         // need First-win under pass rules
          for (size_t k2 = k; k2 < NL && !R.pass_wit; ++k2) {
            for (size_t j = 0; j < L.lev[k2].size(); ++j) {
              size_t gj = lstart[k2] + j;
              if (gval[gj] != gval[gi]) continue;
              if (((pas[gj] >> 3) & 1) != 0) continue;     // different pass outcome, same normal g
              R.pass_wit = 1; R.pw_g = gval[gi];
              R.pw_k = (int)k;
              R.pw_m1 = L.lev[k][i]; R.pw_m2 = L.lev[k2][j];
              break;
            }
          }
        }
      }
    }
  }

  // ---- exact random-greedy win probability (rationals; 128-bit accumulation)
  if (want_rand) {
    std::vector<u64> Wc(gval.size(), 0), Tc(gval.size(), 0);
    bool ovf = false;
    for (size_t k = NL; k-- > 0;) {
      MIndex ni;
      if (k + 1 < NL) ni = make_index(g.V, L.lev[k + 1]);
      for (size_t i = 0; i < L.lev[k].size(); ++i) {
        u64 S = L.lev[k][i], lm = L.lg[k][i];
        if (lm == 0) { Tc[lstart[k] + i] = 1; continue; }
        unsigned __int128 sw = 0, st = 0;
        for (u64 t = lm; t; t &= t - 1) {
          int p = __builtin_ctzll(t);
          int32_t j = ni.get(S | (u64(1) << p));
          if (j < 0) continue;
          size_t gi = lstart[k + 1] + j;
          st += Tc[gi];
          sw += (Tc[gi] - Wc[gi]);
        }
        Wc[lstart[k] + i] = (u64)sw; Tc[lstart[k] + i] = (u64)st;
        if (st > (unsigned __int128)4000000000000000000ULL) ovf = true;
      }
    }
    R.rand_state = ovf ? 2 : 1;
    R.mnT = 0; R.mxT = 0;
    for (size_t k = 0; k < NL; ++k) for (size_t i = 0; i < L.lev[k].size(); ++i) {
      size_t gi = lstart[k] + i;
      u64 a = Wc[gi], t = Tc[gi];
      if (t == 0) continue;
      if (gval[gi] != 0) {
        if (R.mnT == 0 || (unsigned __int128)a * R.mnT < (unsigned __int128)R.mnA * t) {
          R.mnA = a; R.mnT = t; R.mnk = (int)k; R.mnM = L.lev[k][i];
        }
      } else {
        if (R.mxT == 0 || (unsigned __int128)a * R.mxT > (unsigned __int128)R.mxA * t) {
          R.mxA = a; R.mxT = t; R.mxk = (int)k; R.mxM = L.lev[k][i];
        }
      }
    }
  }

  // ---- mediation: how often p is a winning move over all safe S
  R.med.assign(g.V, 0);
  for (size_t k = 0; k + 1 < NL; ++k) {
    MIndex ni = make_index(g.V, L.lev[k + 1]);
    for (size_t i = 0; i < L.lev[k].size(); ++i) {
      u64 S = L.lev[k][i], lm = L.lg[k][i];
      for (u64 t = lm; t; t &= t - 1) {
        int p = __builtin_ctzll(t);
        int32_t j = ni.get(S | (u64(1) << p));
        if (j >= 0 && gval[lstart[k + 1] + j] == 0) R.med[p]++;
      }
    }
  }
}

// ------------------------------------------------------------------ output
static void jarr(const std::vector<u64>& a, const char* name) {
  printf("\"%s\":[", name);
  for (size_t i = 0; i < a.size(); ++i) printf("%s%llu", i ? "," : "", (unsigned long long)a[i]);
  printf("]");
}
static void jarr2(const std::vector<u64>& a, const std::vector<u64>& b, const char* name) {
  printf("\"%s\":[", name);
  for (size_t i = 0; i < a.size(); ++i)
    printf("%s[%llu,%llu]", i ? "," : "", (unsigned long long)a[i], (unsigned long long)b[i]);
  printf("]");
}
static void jarrl(const std::vector<long long>& a, const char* name) {
  printf("\"%s\":[", name);
  for (size_t i = 0; i < a.size(); ++i) printf("%s%lld", i ? "," : "", a[i]);
  printf("]");
}
static void jmask(u64 m, int V) {
  printf("[");
  bool f = true;
  for (int p = 0; p < V; ++p) if (m >> p & 1) { printf("%s%d", f ? "" : ",", p); f = false; }
  printf("]");
}
static void emit(const std::string& key, const Geo& g, const Res& R, bool wr, bool wp) {
  printf("{\"key\":\"%s\",\"V\":%d,\"nforb\":%zu,\"K\":%d,\"nsets\":%llu,", key.c_str(), g.V,
         g.rule == R_Q5 ? g.q5sets.size() : g.quads.size(), R.K, (unsigned long long)R.nsets);
  jarr(R.f, "f"); printf(",");
  jarr2(R.fP, R.f, "Pk"); printf(",");
  jarr(R.fmaxnim, "fmaxnim"); printf(",");
  jarr(R.nmaxlvl_c, "nmaxlvl"); printf(",");
  printf("\"g0\":%d,\"maxnim\":%d,\"minKforMax\":%d,", R.g0, R.maxnim, R.minKforMax);
  printf("\"W\":"); jmask(R.W, g.V); printf(",");
  printf("\"nmaximal\":%d,\"nmaxset\":%lld,", R.nmaximal, R.nmaxset);
  printf("\"nP\":%llu,\"nN\":%llu,", (unsigned long long)R.nP, (unsigned long long)R.nN);
  printf("\"misere0\":%d,", R.misere0);
  if (wp) printf("\"pass0_both\":%d,\"pass0_1p\":%d,", R.pass0_both, R.pass0_1p);
  jarrl(R.med, "med"); printf(","); jarrl(R.deg, "deg");
  if (wr && R.rand_state) {
    printf(",\"rand_min_N\":{\"num\":%llu,\"den\":%llu,\"k\":%d,\"occ\":", (unsigned long long)R.mnA,
           (unsigned long long)R.mnT, R.mnk);
    jmask(R.mnM, g.V);
    printf("},\"rand_max_P\":{\"num\":%llu,\"den\":%llu,\"k\":%d,\"occ\":", (unsigned long long)R.mxA,
           (unsigned long long)R.mxT, R.mxk);
    jmask(R.mxM, g.V); printf("}");
  }
  if (wp) {
    if (R.pass_wit) {
      printf(",\"pass_witness\":{\"g\":%d,\"k\":%d,\"occ1\":", R.pw_g, R.pw_k);
      jmask(R.pw_m1, g.V); printf(",\"occ2\":"); jmask(R.pw_m2, g.V); printf("}");
    } else printf(",\"pass_witness\":null");
  }
  printf("}\n"); fflush(stdout);
}

int main(int argc, char** argv) {
  if (argc < 2) { fprintf(stderr, "need job\n"); return 1; }
  std::string job = argv[1];
  u64 CAP = (argc > 1 && getenv("KC_CAP")) ? strtoull(getenv("KC_CAP"), nullptr, 10) : CAP_DEFAULT;
  if (argc > 6 && getenv("KC_CAP")) CAP = strtoull(getenv("KC_CAP"), nullptr, 10);

  // ---------- simple counting jobs
  if (job == "cnt" || job == "cnt_rect") {
    int a = atoi(argv[2]), b = (job == "cnt") ? a : atoi(argv[3]);
    Geo g; build_rect(g, a, b, R_STD);
    Levels L; enum_all(g, L, CAP);
    std::vector<u64> f; for (auto& v : L.lev) f.push_back(v.size());
    std::vector<long long> nm(L.lev.size(), 0);
    for (size_t k = 0; k < L.lev.size(); ++k) for (u64 m : L.lg[k]) if (m == 0) nm[k]++;
    printf("{\"key\":\"cnt_%dx%d\",\"V\":%d,\"nquads\":%zu,\"complete\":%d,\"nsets\":%llu,\"K\":%d,",
           a, b, g.V, g.quads.size(), L.complete ? 1 : 0, (unsigned long long)L.total, (int)L.lev.size() - 1);
    jarr(f, "f");
    printf(",\"nmaxset\":%lld,", f.empty() ? 0 : (long long)f.back());
    printf("\"nmaxlvl\":[");
    for (size_t k = 0; k < nm.size(); ++k) printf("%s%lld", k ? "," : "", nm[k]);
    printf("]}\n"); fflush(stdout);
    return 0;
  }

  // ---------- full solve on a rectangle
  if (job == "full" || job == "rect" || job == "q5") {
    int a = atoi(argv[2]), b = a;
    int rule = (job == "q5") ? R_Q5 : R_STD;
    bool wr = 1, wp = 1;
    if (job == "rect") {
      b = atoi(argv[3]);
      if (argc > 4) rule = atoi(argv[4]);
      if (argc > 5) wr = atoi(argv[5]);
      if (argc > 6) wp = atoi(argv[6]);
    } else if (job == "q5") {
      if (argc > 4) wr = atoi(argv[4]);
      if (argc > 5) wp = atoi(argv[5]);
    } else {
      if (argc > 3) wr = atoi(argv[3]);
      if (argc > 4) wp = atoi(argv[4]);
    }
    Geo g; build_rect(g, a, b, rule);
    Res R; solve_full(g, wr, wp, R, CAP);
    char key[128];
    snprintf(key, sizeof key, "%s_%dx%d_r%d", job.c_str(), a, b, rule);
    emit(key, g, R, wr, wp);
    return 0;
  }

  // ---------- one-point deletions
  if (job == "del1" || job == "del2") {
    int n = atoi(argv[2]);
    bool wr = (argc > 3) ? atoi(argv[3]) != 0 : false;
    bool wp = (argc > 4) ? atoi(argv[4]) != 0 : false;
    Geo full; build_rect(full, n, n, R_STD);
    int Kv = -1; u64 Wv = 0; int mis0 = -1; int pn0 = -1, pn1 = -1;
    { Res R0; solve_full(full, false, true, R0, CAP); Kv = R0.K; Wv = R0.W; mis0 = R0.misere0; pn0 = R0.pass0_both; pn1 = R0.pass0_1p; }
    std::vector<int> Ks; std::vector<int> win; std::vector<int> mis; std::vector<int> pw;
    std::vector<u64> Ws; std::vector<int> ids; std::vector<long long> meds;
    std::vector<std::vector<long long>> res;
    int delcount = (job == "del1") ? full.V : full.V * (full.V - 1) / 2;
    int done = 0;
    for (int a = 0; a < full.V; ++a) {
      for (int b = (job == "del1" ? a + 1 : a); b < full.V; ++b) {
        if (job == "del1" && b != a + 1) continue;
        Geo g; g.rule = R_STD;
        for (int p = 0; p < full.V; ++p) {
          if (p == a || (job == "del2" && p == b)) continue;
          g.xs.push_back(full.xs[p]); g.ys.push_back(full.ys[p]);
        }
        g.V = (int)g.xs.size();
        g.full = (u64(1) << g.V) - 1;
        // rebuild forbidden structure for the sub-board (quads need all 4 points)
        g.P2.assign((size_t)g.V * g.V * g.V, 0);
        g.deg.assign(g.V, 0);
        for (int i = 0; i < g.V - 3; ++i) for (int j = i + 1; j < g.V - 2; ++j)
        for (int k = j + 1; k < g.V - 1; ++k) for (int l = k + 1; l < g.V; ++l) {
          if (det4p(g.xs[i], g.ys[i], g.xs[j], g.ys[j], g.xs[k], g.ys[k], g.xs[l], g.ys[l]) != 0) continue;
          int id[4] = {i, j, k, l};
          g.quads.push_back((u64(1) << i) | (u64(1) << j) | (u64(1) << k) | (u64(1) << l));
          for (int t = 0; t < 4; ++t) {
            g.deg[id[t]]++;
            for (int u = 0; u < 4; ++u) for (int v = u + 1; v < 4; ++v) {
              if (u == t || v == t) continue;
              int p2 = id[t], A = id[u], B = id[v], r = -1;
              for (int z = 0; z < 4; ++z) if (z != t && z != u && z != v) r = id[z];
              g.P2[((size_t)p2 * g.V + A) * g.V + B] |= u64(1) << r;
            }
          }
        }
        Res R; solve_full(g, wr, wp, R, CAP);
        Ks.push_back(R.K); win.push_back(R.W == 0 ? 0 : 1); mis.push_back(R.misere0);
        pw.push_back(R.pass0_both); Ws.push_back(R.W);
        if (job == "del1") ids.push_back(a); else ids.push_back(a * 1000 + b);
        meds.push_back(R.med.empty() ? 0 : R.med[0]);
        done++;
      }
    }
    printf("{\"key\":\"%s_n%d\",\"base_K\":%d,\"base_W\":", job.c_str(), n, Kv);
    jmask(Wv, full.V);
    printf(",\"base_misere0\":%d,\"base_pass_both\":%d,\"base_pass_1p\":%d,\"count\":%d,\"K\":[", mis0, pn0, pn1, done);
    for (size_t i = 0; i < Ks.size(); ++i) printf("%s%d", i ? "," : "", Ks[i]);
    printf("],\"Wsize\":[");
    for (size_t i = 0; i < Ws.size(); ++i) printf("%s%d", i ? "," : "", pc(Ws[i]));
    printf("],\"misere0\":[");
    for (size_t i = 0; i < mis.size(); ++i) printf("%s%d", i ? "," : "", mis[i]);
    printf("],\"pass_both\":[");
    for (size_t i = 0; i < pw.size(); ++i) printf("%s%d", i ? "," : "", pw[i]);
    printf("],\"ids\":[");
    for (size_t i = 0; i < ids.size(); ++i) printf("%s%d", i ? "," : "", ids[i]);
    printf("],\"W\":[");
    for (size_t i = 0; i < Ws.size(); ++i) { jmask(Ws[i], full.V - (job == "del1" ? 1 : 2)); if (i + 1 < Ws.size()) printf(","); }
    printf("]}\n"); fflush(stdout);
    return 0;
  }

  // ---------- sub-board f-vector (B177)
  if (job == "sub") {
    int w = atoi(argv[2]), h = atoi(argv[3]);
    bool wr = (argc > 4) ? atoi(argv[4]) != 0 : false;
    Geo g; build_rect(g, w, h, R_STD);
    Res R; solve_full(g, wr, true, R, CAP);
    char key[64]; snprintf(key, sizeof key, "sub_%dx%d", w, h);
    emit(key, g, R, wr, true);
    return 0;
  }

  // ---------- n x n plus one external point (B208)
  if (job == "ext") {
    int n = atoi(argv[2]);
    bool wr = (argc > 3) ? atoi(argv[3]) != 0 : false;
    int nchanged = 0, ntot = 0, nnon = 0;
    std::vector<std::pair<int, int>> ch;
    for (int nside = 0; nside <= 2 * n; ++nside) {           // x = -1 .. 2n (outside 0..n-1)
      for (int ny = 0; ny < n; ++ny) {
        for (int side = 0; side < 2; ++side) {
          int ex = side ? (2 * n) : nside;
          if (ex >= 0 && ex < n) continue;
          int ey = ny;
          Geo g; g.rule = R_STD;
          for (int y = 0; y < n; ++y) for (int x = 0; x < n; ++x) { g.xs.push_back(x); g.ys.push_back(y); }
          g.xs.push_back(ex); g.ys.push_back(ey);
          g.V = (int)g.xs.size(); g.full = (u64(1) << g.V) - 1;
          g.P2.assign((size_t)g.V * g.V * g.V, 0); g.deg.assign(g.V, 0);
          for (int i = 0; i < g.V - 3; ++i) for (int j = i + 1; j < g.V - 2; ++j)
          for (int k = j + 1; k < g.V - 1; ++k) for (int l = k + 1; l < g.V; ++l) {
            if (det4p(g.xs[i], g.ys[i], g.xs[j], g.ys[j], g.xs[k], g.ys[k], g.xs[l], g.ys[l]) != 0) continue;
            int id[4] = {i, j, k, l};
            g.quads.push_back((u64(1) << i) | (u64(1) << j) | (u64(1) << k) | (u64(1) << l));
            for (int t = 0; t < 4; ++t) { g.deg[id[t]]++;
              for (int u = 0; u < 4; ++u) for (int v = u + 1; v < 4; ++v) {
                if (u == t || v == t) continue;
                int p2 = id[t], A = id[u], B = id[v], r = -1;
                for (int z = 0; z < 4; ++z) if (z != t && z != u && z != v) r = id[z];
                g.P2[((size_t)p2 * g.V + A) * g.V + B] |= u64(1) << r; } }
          }
          Res R; solve_full(g, false, true, R, CAP);
          ntot++;
          int base = -1;
          { Geo b0; build_rect(b0, n, n, R_STD); Res R0; solve_full(b0, false, true, R0, CAP); base = R0.W == 0 ? 0 : 1; }
          int cur = (R.W == 0) ? 0 : 1;
          if (cur != base) { nchanged++; ch.push_back({ex, ey}); }
          else if (R.W != 0) nnon++;
        }
      }
    }
    printf("{\"key\":\"ext_n%d\",\"n_external_positions\":%d,\"winner_changed\":%d,\"changed\":[", n, ntot, nchanged);
    for (size_t i = 0; i < ch.size(); ++i) printf("%s[%d,%d]", i ? "," : "", ch[i].first, ch[i].second);
    printf("]}\n"); fflush(stdout);
    return 0;
  }

  // ---------- downward greedy family search that keeps W (B224)
  if (job == "greedy") {
    int n = atoi(argv[2]);
    long long budget = atoll(argv[3]);
    Geo full; build_rect(full, n, n, R_STD);
    Res R0; solve_full(full, false, true, R0, CAP);
    u64 Wt = R0.W;
    long long F0 = (long long)full.quads.size();
    // order quads: try to remove a quad whose removal keeps W
    std::vector<u64> keep = full.quads;
    long long tried = 0;
    long long removed = 0;
    auto solve_with = [&](const std::vector<u64>& keep, Res& R) -> bool {
      Geo g; g.rule = R_STD;
      for (int y = 0; y < n; ++y) for (int x = 0; x < n; ++x) { g.xs.push_back(x); g.ys.push_back(y); }
      g.V = (int)g.xs.size(); g.full = (u64(1) << g.V) - 1;
      g.P2.assign((size_t)g.V * g.V * g.V, 0); g.deg.assign(g.V, 0);
      for (u64 q : keep) {
        int id[4], t = 0; for (u64 z = q; z; z &= z - 1) id[t++] = __builtin_ctzll(z);
        for (int t2 = 0; t2 < 4; ++t2) { g.deg[id[t2]]++;
          for (int u = 0; u < 4; ++u) for (int v = u + 1; v < 4; ++v) {
            if (u == t2 || v == t2) continue;
            int p2 = id[t2], A = id[u], B = id[v], r = -1;
            for (int z = 0; z < 4; ++z) if (z != t2 && z != u && z != v) r = id[z];
            g.P2[((size_t)p2 * g.V + A) * g.V + B] |= u64(1) << r; } }
      }
      solve_full(g, false, true, R, CAP);
      return R.W == Wt;
    };
    bool progress = true;
    while (progress && tried < budget && keep.size() > 1) {
      progress = false;
      for (size_t i = 0; i < keep.size() && tried < budget; ++i) {
        if (tried++ > budget) break;
        std::vector<u64> trial = keep;
        trial.erase(trial.begin() + i);
        Res R; solve_with(trial, R);
        if (R.W == Wt) { keep = trial; removed++; progress = true; break; }
      }
    }
    printf("{\"key\":\"greedy_n%d\",\"F_full\":%lld,\"F_kept\":%zu,\"tried\":%lld,\"removed\":%lld,\"W_target\":",
           n, F0, keep.size(), tried, removed);
    jmask(Wt, full.V);
    printf(",\"reproduced\":%d}\n", keep.empty() ? 0 : 1);
    fflush(stdout);
    return 0;
  }

  // ---------- P/N disagreement between two rules over the common safe sets
  if (job == "disagree") {
    int rA = atoi(argv[2]), wA = atoi(argv[3]), mA = atoi(argv[4]);
    int rB = atoi(argv[5]), wB = atoi(argv[6]), mB = atoi(argv[7]);
    // Common ground: the intersection of both forbidden families (a "coarser" rule set
    // that is a subset of both). Its safe sets are legal under both rules, so they are
    // the natural common population for a P/N disagreement statistic.
    Geo A, B, C;
    build_rect(A, wA, mA, rA);
    build_rect(B, wB, mB, rB);
    if (A.V != B.V) { printf("{\"error\":\"point sets differ\"}\n"); return 1; }
    C = A; C.quads.clear(); C.P2.assign((size_t)C.V * C.V * C.V, 0); C.deg.assign(C.V, 0);
    for (u64 q : A.quads) {
      bool inB = false;
      for (u64 q2 : B.quads) if (q2 == q) { inB = true; break; }
      if (!inB) continue;
      C.quads.push_back(q);
      int id[4], t = 0; for (u64 z = q; z; z &= z - 1) id[t++] = __builtin_ctzll(z);
      for (int t2 = 0; t2 < 4; ++t2) { C.deg[id[t2]]++;
        for (int u = 0; u < 4; ++u) for (int v = u + 1; v < 4; ++v) {
          if (u == t2 || v == t2) continue;
          int p2 = id[t2], AA = id[u], BB = id[v], r = -1;
          for (int z = 0; z < 4; ++z) if (z != t2 && z != u && z != v) r = id[z];
          C.P2[((size_t)p2 * C.V + AA) * C.V + BB] |= u64(1) << r; } }
    }
    // legal mask under A / under B for a given occupancy
    auto build_trip = [](const Geo& g) {
      std::vector<std::vector<u64>> trip(g.V);
      for (u64 q : g.quads) {
        int id[4], t = 0; for (u64 z = q; z; z &= z - 1) id[t++] = __builtin_ctzll(z);
        for (int z2 = 0; z2 < 4; ++z2) { u64 o = 0; for (int y2 = 0; y2 < 4; ++y2) if (y2 != z2) o |= u64(1) << id[y2]; trip[id[z2]].push_back(o); }
      }
      return trip;
    };
    auto triA = build_trip(A), triB = build_trip(B);
    Levels L; enum_all(C, L, CAP);
    size_t NL = L.lev.size();
    std::vector<u64> dis(NL, 0), tot(NL, 0);
    // Grundy under rule A and under rule B, both restricted to the common safe sets
    std::vector<int8_t> gA, gB;
    for (int which = 0; which < 2; ++which) {
      std::vector<int8_t>& cur = which == 0 ? gA : gB;
      const std::vector<std::vector<u64>>& tri = which == 0 ? triA : triB;
      std::vector<size_t> off(NL + 1, 0);
      for (size_t kk = 0; kk < NL; ++kk) off[kk + 1] = off[kk] + L.lev[kk].size();
      cur.assign(L.total, 0);
      for (int ki = (int)NL - 2; ki >= 0; --ki) {
        size_t kk = (size_t)ki;
        MIndex ip = make_index(C.V, L.lev[kk + 1]);
        for (size_t i = 0; i < L.lev[kk].size(); ++i) {
          u64 S = L.lev[kk][i];
          int8_t seen[96]; std::memset(seen, 0, sizeof(seen));
          u64 empty = C.full & ~S;
          while (empty) {
            int p = __builtin_ctzll(empty); empty &= empty - 1;
            bool ok = true;
            for (u64 t : tri[p]) if ((S & t) == t) { ok = false; break; }
            if (!ok) continue;
            int32_t j = ip.get(S | (u64(1) << p));
            if (j >= 0) seen[(int)cur[off[kk + 1] + j]] = 1;
          }
          int m = 0; while (seen[m]) ++m;
          cur[off[kk] + i] = (int8_t)m;
        }
      }
    }
    for (size_t k = 0; k < NL; ++k) {
      size_t off = 0;
      for (size_t kk = 0; kk < k; ++kk) off += L.lev[kk].size();
      for (size_t i = 0; i < L.lev[k].size(); ++i) {
        tot[k]++;
        if ((gA[off + i] == 0) != (gB[off + i] == 0)) dis[k]++;
      }
    }
    printf("{\"key\":\"disagree_r%d%dx%d_vs_r%d%dx%d\",\"common_nquads\":%zu,\"nsets\":%llu,\"disagree\":[",
           rA, wA, mA, rB, wB, mB, C.quads.size(), (unsigned long long)L.total);
    for (size_t k = 0; k < NL; ++k) printf("%s[%llu,%llu]", k ? "," : "", (unsigned long long)tot[k], (unsigned long long)dis[k]);
    printf("]}\n"); fflush(stdout);
    return 0;
  }

  // ---------- mod-2 parity invariant test (B168)
  if (job == "mod2") {
    int n = atoi(argv[2]);
    Geo g; build_rect(g, n, n, R_STD);
    Res R; solve_full(g, false, false, R, CAP);
    Levels L; enum_all(g, L, CAP);
    size_t NL = L.lev.size();
    // top-down Grundy, same order as solve_full
    std::vector<size_t> ls(NL + 1, 0);
    for (size_t k = 0; k < NL; ++k) ls[k + 1] = ls[k] + L.lev[k].size();
    std::vector<int8_t> gv(L.total, 0);
    for (int ki = (int)NL - 2; ki >= 0; --ki) {
      size_t k = (size_t)ki;
      MIndex ip = make_index(g.V, L.lev[k + 1]);
      int8_t seen[96];
      for (size_t i = 0; i < L.lev[k].size(); ++i) {
        u64 S = L.lev[k][i], lm = L.lg[k][i];
        std::memset(seen, 0, sizeof(seen));
        for (u64 t = lm; t; t &= t - 1) {
          int p = __builtin_ctzll(t);
          int32_t j = ip.get(S | (u64(1) << p));
          if (j >= 0) seen[(int)gv[ls[k + 1] + j]] = 1;
        }
        int m = 0; while (seen[m]) ++m;
        gv[ls[k] + i] = (int8_t)m;
      }
    }
    // (a) is there v in F_2^V with  XOR_{p in S} v_p = [g(S)==0]  for all safe S?
    GF2 s1; s1.init(g.V);
    for (size_t k = 0; k < NL; ++k) for (size_t i = 0; i < L.lev[k].size(); ++i)
      s1.add(L.lev[k][i], gv[ls[k] + i] == 0 ? 1 : 0);
    int ok1 = s1.consistent() ? 1 : 0;
    u64 v1 = s1.solution();
    // (b) is P/N a function of a mod-2 feature sum over a fixed feature set?
    const int NF = 10;
    std::vector<u64> feat(g.V, 0);
    for (int p = 0; p < g.V; ++p) {
      int x = g.xs[p], y = g.ys[p];
      u64 f = 0;
      f |= (u64)(x & 1) << 0;
      f |= (u64)(y & 1) << 1;
      f |= (u64)((x >> 1) & 1) << 2;
      f |= (u64)((y >> 1) & 1) << 3;
      f |= (u64)(g.deg[p] & 1) << 4;
      f |= (u64)((g.deg[p] >> 1) & 1) << 5;
      f |= (u64)((g.deg[p] >> 2) & 1) << 6;
      feat[p] = f;
    }
    std::vector<int> tab(1 << NF, -1);
    bool fok = true;
    int firstbad = -1;
    for (size_t k = 0; k < NL && fok; ++k) for (size_t i = 0; i < L.lev[k].size(); ++i) {
      u64 S = L.lev[k][i], sg = 0;
      for (u64 t = S; t; t &= t - 1) sg ^= feat[__builtin_ctzll(t)];
      int val = (gv[ls[k] + i] == 0) ? 1 : 0;
      if (tab[sg] < 0) tab[sg] = val;
      else if (tab[sg] != val) { fok = false; firstbad = (int)k; }
    }
    // (c) is W_n a union of the 4 coordinate-parity classes (x mod 2, y mod 2)?
    int chk = 0, ncls_used = 0;
    { std::vector<int> cls(4, -1);
      for (int p = 0; p < g.V; ++p) {
        int c = ((g.xs[p] & 1) << 1) | (g.ys[p] & 1);
        int inW = (R.W >> p & 1) ? 1 : 0;
        if (cls[c] < 0) { cls[c] = inW; ncls_used++; }
        else if (cls[c] != inW) chk++;
      } }
    printf("{\"key\":\"mod2_n%d\",\"linear_invariant_exists\":%d,\"v\":", n, ok1);
    jmask(v1, g.V);
    printf(",\"feat%d_determines_PN\":%d,\"feat_fail_first_at_k\":%d,", NF, fok ? 1 : 0, firstbad);
    printf("\"W_conflicts_with_4_parity_classes\":%d,\"Wsize\":%d,\"K\":%d,\"g0\":%d,\"nsets\":%llu}\n",
           chk, pc(R.W), R.K, R.g0, (unsigned long long)L.total);
    fflush(stdout);
    return 0;
  }

  // ---------- GF(2) Betti numbers
  if (job == "betti") {
    int n = atoi(argv[2]);
    long long maxdim = atoll(argv[3]);
    Geo g; build_rect(g, n, n, R_STD);
    Levels L; enum_all(g, L, CAP);
    size_t NL = L.lev.size();
    std::vector<u64> f; for (auto& v : L.lev) f.push_back(v.size());
    std::vector<long long> rankd(NL + 1, 0);
    for (size_t k = 0; k + 1 < NL; ++k) {
      long long rows = (long long)L.lev[k].size(), cols = (long long)L.lev[k + 1].size();
      if (rows > maxdim || cols > maxdim) { rankd[k] = -1; continue; }
      size_t nw = (cols + 63) / 64;
      std::vector<u64> basis(nw * rows, 0);
      std::vector<int> has((size_t)rows, 0);
      long long rank = 0;
      std::vector<u64> cv(nw);
      for (long long ci = 0; ci < cols; ++ci) {
        std::fill(cv.begin(), cv.end(), 0);
        u64 S = L.lev[k + 1][ci];
        for (u64 t = S; t; t &= t - 1) {
          u64 fm = S & ~(u64(1) << __builtin_ctzll(t));
          long long lo = 0, hi = rows - 1;
          while (lo <= hi) { long long mid = (lo + hi) / 2; if (L.lev[k][mid] < fm) lo = mid + 1; else hi = mid - 1; }
          if (lo < rows && L.lev[k][lo] == fm) cv[lo >> 6] ^= u64(1) << (lo & 63);
        }
        bool placed = false;
        for (size_t w = 0; w < nw && !placed; ++w) {
          while (cv[w]) {
            int bb = __builtin_ctzll(cv[w]);
            long long idx = (long long)(w * 64) + bb;
            if (has[idx]) {
              const u64* br = &basis[(size_t)idx * nw];
              for (size_t w2 = 0; w2 < nw; ++w2) cv[w2] ^= br[w2];
            } else {
              u64* br = &basis[(size_t)idx * nw];
              for (size_t w2 = 0; w2 < nw; ++w2) br[w2] = cv[w2];
              has[idx] = 1; rank++; placed = true; break;
            }
          }
        }
      }
      rankd[k] = rank;
    }
    std::vector<long long> b(NL + 1, 0);
    for (size_t k = 0; k < NL; ++k) {
      long long r1 = (k == 0) ? 0 : rankd[k - 1];
      long long r2 = (k + 1 <= NL - 1) ? rankd[k] : 0;
      b[k] = (r1 < 0 || r2 < 0) ? -1 : (long long)f[k] - r1 - r2;
    }
    printf("{\"key\":\"betti_n%d\",\"f\":[", n);
    for (size_t k = 0; k < NL; ++k) printf("%s%llu", k ? "," : "", (unsigned long long)f[k]);
    printf("],\"betti\":[");
    for (size_t k = 0; k < NL; ++k) printf("%s%lld", k ? "," : "", b[k]);
    printf("]}\n"); fflush(stdout);
    return 0;
  }

  // ---------- circle / collinear statistics (B170)
  if (job == "circles") {
    int nmax = (argc > 2) ? atoi(argv[2]) : 9;
    for (int n = 2; n <= nmax; ++n) {
      Geo g; build_rect(g, n, n, R_STD);
      int ncirc = 0, nline = 0;
      for (u64 q : g.quads) {
        int id[4], t = 0; for (u64 z = q; z; z &= z - 1) id[t++] = __builtin_ctzll(z);
        if (colline(g.xs[id[0]], g.ys[id[0]], g.xs[id[1]], g.ys[id[1]], g.xs[id[2]], g.ys[id[2]], g.xs[id[3]], g.ys[id[3]])) nline++;
        else ncirc++;
      }
      std::map<int, int> hist;
      std::set<u64> seen;
      for (int a = 0; a < g.V - 2; ++a) for (int b = a + 1; b < g.V - 1; ++b)
        for (int c = b + 1; c < g.V; ++c) {
          // a,b,c must be non-collinear for a genuine circle
          if ((long long)(g.xs[b] - g.xs[a]) * (g.ys[c] - g.ys[a]) -
              (long long)(g.ys[b] - g.ys[a]) * (g.xs[c] - g.xs[a]) == 0) continue;
          u64 circ = 0;
          for (int p = 0; p < g.V; ++p)
            if (det4p(g.xs[a], g.ys[a], g.xs[b], g.ys[b], g.xs[c], g.ys[c], g.xs[p], g.ys[p]) == 0)
              circ |= u64(1) << p;
          if (pc(circ) < 4) continue;
          if (__builtin_ctzll(circ) != a) continue;    // canonical: smallest point
          if (seen.count(circ)) continue;
          seen.insert(circ);
          hist[pc(circ)]++;
        }
      printf("{\"key\":\"circles_n%d\",\"F\":%zu,\"ncollinear\":%d,\"nconcyclic\":%d,\"circles_by_size\":{",
             n, g.quads.size(), nline, ncirc);
      bool f1 = true;
      for (auto& kv : hist) { printf("%s\"%d\":%d", f1 ? "" : ",", kv.first, kv.second); f1 = false; }
      printf("}}\n"); fflush(stdout);
    }
    return 0;
  }

  // ---------- random-greedy Monte Carlo
  if (job == "mc") {
    int n = atoi(argv[2]);
    long long runs = atoll(argv[3]);
    Geo g; build_rect(g, n, n, R_STD);
    long long K = 0;
    { Levels L; enum_all(g, L, CAP); K = (long long)L.lev.size() - 1; }
    std::vector<std::vector<u64>> trip(g.V);
    for (u64 q : g.quads) {
      int id[4], t = 0; for (u64 z = q; z; z &= z - 1) id[t++] = __builtin_ctzll(z);
      for (int z2 = 0; z2 < 4; ++z2) { u64 o = 0; for (int y2 = 0; y2 < 4; ++y2) if (y2 != z2) o |= u64(1) << id[y2]; trip[id[z2]].push_back(o); }
    }
    std::mt19937_64 rng(99991 + 17 * n);
    long long S1 = 0, S2 = 0, S3 = 0, S4 = 0;
    long long cnt[128] = {0};
    long long lastdeg[128] = {0};
    std::vector<long long> fsum(g.V, 0), f2(g.V, 0);
    long long fruns = (g.V <= 25) ? runs / 4 : runs / 16;
    if (fruns < 1) fruns = 1;
    for (long long r = 0; r < runs; ++r) {
      u64 occ = 0; long long X = 0; int lastp = -1;
      while (true) {
        u64 legal = 0, empty = g.full & ~occ;
        while (empty) {
          int p = __builtin_ctzll(empty); empty &= empty - 1;
          bool ok = true;
          for (u64 t : trip[p]) if ((occ & t) == t) { ok = false; break; }
          if (ok) legal |= u64(1) << p;
        }
        if (!legal) break;
        int nopt = pc(legal), pick = (int)(rng() % (u64)nopt), p = -1;
        for (u64 t = legal; t; t &= t - 1) { int q = __builtin_ctzll(t); if (pick-- == 0) { p = q; break; } }
        occ |= u64(1) << p; lastp = p; X++;
      }
      if (X < 128) cnt[X]++;
      if (lastp >= 0) lastdeg[g.deg[lastp]]++;
      S1 += X; S2 += X * X; S3 += X * X * X; S4 += X * X * X * X;
    }
    for (int p = 0; p < g.V; ++p) for (long long r = 0; r < fruns; ++r) {
      u64 occ = u64(1) << p; long long X = 1;
      while (true) {
        u64 legal = 0, empty = g.full & ~occ;
        while (empty) {
          int q2 = __builtin_ctzll(empty); empty &= empty - 1;
          bool ok = true;
          for (u64 t : trip[q2]) if ((occ & t) == t) { ok = false; break; }
          if (ok) legal |= u64(1) << q2;
        }
        if (!legal) break;
        int nopt = pc(legal), pick = (int)(rng() % (u64)nopt), q2 = -1;
        for (u64 t = legal; t; t &= t - 1) { int z = __builtin_ctzll(t); if (pick-- == 0) { q2 = z; break; } }
        occ |= u64(1) << q2; X++;
      }
      fsum[p] += X; f2[p] += X * X;
    }
    printf("{\"key\":\"mc_n%d\",\"runs\":%lld,\"K\":%lld,\"S1\":%lld,\"S2\":%lld,\"S3\":%lld,\"S4\":%lld,\"dist\":[",
           n, runs, K, S1, S2, S3, S4);
    { bool f2 = true; for (int i = 0; i < 128; ++i) if (cnt[i]) { printf("%s[%d,%lld]", f2 ? "" : ",", i, cnt[i]); f2 = false; } }
    printf("],\"lastdeg_hist\":[");
    { bool f2 = true; for (int i = 0; i < 128; ++i) if (lastdeg[i]) { printf("%s[%d,%lld]", f2 ? "" : ",", i, lastdeg[i]); f2 = false; } }
    printf("],\"boarddeg_hist\":[");
    { int h[128] = {0}; for (int p = 0; p < g.V; ++p) h[g.deg[p]]++;
      bool f2 = true; for (int i = 0; i < 128; ++i) if (h[i]) { printf("%s[%d,%d]", f2 ? "" : ",", i, h[i]); f2 = false; } }
    printf("],\"firstmove_runs\":%lld,\"firstmove_S1\":[", fruns);
    { bool f2 = true; for (int p = 0; p < g.V; ++p) { printf("%s[%d,%lld]", f2 ? "" : ",", p, fsum[p]); f2 = false; } }
    printf("]}\n"); fflush(stdout);
    return 0;
  }

  fprintf(stderr, "unknown job %s\n", job.c_str());
  return 1;
}
