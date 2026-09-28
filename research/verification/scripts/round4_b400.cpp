// Round4 b400 worker: C++ (WSL g++ 13.3.0, 16 cores).
// Integer arithmetic only; every ratio is an exact reduced fraction p/q.
// Engine shared with all other round4 workers: kc_core.h.
#include "kc_core.h"
#include <cstdio>
#include <cmath>
#include <map>
#include <set>
#include <vector>
#include <algorithm>
#include <string>
#include <numeric>
#include <functional>
#include <random>
#include <sstream>
#include <iostream>
#include <omp.h>

using namespace kc;
using u64 = uint64_t;
using i128 = __int128;
using u128 = unsigned __int128;

static std::string i128s(i128 v) {
    if (v == 0) return "0";
    bool neg = v < 0; if (neg) v = -v;
    std::string s;
    while (v) { s += char('0' + (int)(v % 10)); v /= 10; }
    if (neg) s += '-';
    std::reverse(s.begin(), s.end());
    return s;
}
static long long gcdl(long long a, long long b) { return b ? gcdl(b, a % b) : a; }
static std::string frac(i128 p, i128 q) {
    if (q == 0) return "null";
    if (q < 0) { p = -p; q = -q; }
    if (p < 0) return "null";              // negative probabilities are not emitted
    i128 a = p, b = q;
    while (b) { i128 t = a % b; a = b; b = t; }
    i128 g = a ? a : 1;
    return i128s(p / g) + "/" + i128s(q / g);
}
static std::ostream& operator<<(std::ostream& os, i128 v) { return os << i128s(v); }
static std::string arr(const std::vector<long long>& v) {
    std::string s = "[";
    for (size_t i = 0; i < v.size(); ++i) { if (i) s += ", "; s += std::to_string(v[i]); }
    return s + "]";
}
static std::string arri(const std::map<int,int>& m) {
    std::string s = "{", f;
    for (auto& kv : m) { if (!f.empty()) s += ", "; f = "1";
        s += "\"" + std::to_string(kv.first) + "\": " + std::to_string(kv.second); }
    return s + "}";
}

// ---------------------------------------------------------------- 4x4 core
struct N4 {
    Board b;
    int V;
    u64 F;
    std::vector<int> pc, g, mu, hx;
    std::vector<i128> W, T;                // p_rand = W/T  (W = # winning complete play seqs)
    std::vector<long long> gpaths;         // # move-sequences from empty to this state
    std::vector<i128> nL, wins;
    std::vector<std::vector<int>> tstar, wft;
    std::vector<u64> maxsets;              // all maximal safe sets
    i128 T0;                               // total # complete play sequences from empty
};

static void build_n4(N4& S) {
    build_square(S.b, 4);
    S.V = S.b.V; S.F = 1ull << S.V;
    S.pc.assign(S.F, 0);
    for (u64 m = 1; m < S.F; ++m) S.pc[m] = S.pc[m >> 1] + (int)(m & 1);
    std::vector<u64> byC[17];
    for (u64 m = 0; m < S.F; ++m) byC[S.pc[m]].push_back(m);
    S.g.assign(S.F, 0); S.mu.assign(S.F, 0); S.hx.assign(S.F, 0);
    S.W.assign(S.F, 0); S.T.assign(S.F, 1);
    S.tstar.assign(S.F, {}); S.wft.assign(S.F, {});
    S.nL.assign(S.F, 0); S.wins.assign(S.F, 0);
    for (int k = S.V; k >= 0; --k) {
        for (u64 m : byC[k]) {
            u64 L = legal_mask(S.b, m);
            int nl = __builtin_popcountll(L);
            S.nL[m] = nl;
            if (!L) { S.T[m] = 1; S.W[m] = 0; S.tstar[m] = {k}; S.wft[m] = {k};
                      S.mu[m] = 0; S.hx[m] = 0; S.g[m] = 0; continue; }
            unsigned v = 0; i128 W = 0, T = 0, wins = 0; int mn = 1<<30, mx = 0;
            std::set<int> ts, wf;
            u64 s = L;
            while (s) {
                int u = __builtin_ctzll(s); s &= s - 1;
                u64 c = m | (1ull << u);
                v |= 1u << S.g[c];
                T += S.T[c];
                if (S.g[c] == 0) { W += S.T[c]; ++wins; for (int z : S.tstar[c]) ts.insert(z); }
                else { for (int z : S.tstar[c]) ts.insert(z); }
                for (int z : S.wft[c]) wf.insert(z);
                mn = std::min(mn, S.mu[c]); mx = std::max(mx, S.hx[c]);
            }
            int gg = 0; while (v & (1u << gg)) ++gg;
            S.g[m] = gg; S.W[m] = W; S.T[m] = T; S.wins[m] = wins;
            S.mu[m] = 1 + mn; S.hx[m] = 1 + mx;
            if (ts.empty()) ts.insert(k);
            S.tstar[m].assign(ts.begin(), ts.end());
            S.wft[m].assign(wf.begin(), wf.end());
        }
    }
    S.T0 = S.T[0];
    // forward path counts
    S.gpaths.assign(S.F, 0);
    S.gpaths[0] = 1;
    for (int k = 0; k < S.V; ++k) for (u64 m : byC[k]) {
        if (!S.gpaths[m]) continue;
        u64 L = legal_mask(S.b, m); u64 s = L;
        while (s) { int u = __builtin_ctzll(s); s &= s-1; S.gpaths[m | (1ull<<u)] += S.gpaths[m]; }
    }
    for (u64 m = 0; m < S.F; ++m) if (legal_mask(S.b, m) == 0 && S.pc[m] > 0) S.maxsets.push_back(m);
    std::sort(S.maxsets.begin(), S.maxsets.end());
}

int main(int argc, char** argv) {
    std::string job = (argc > 1) ? argv[1] : "help";
    std::ostringstream o;
    N4 S;
    build_n4(S);

    // ================================================= JOB "n4core" (stats)
    if (job == "n4core") {
        o << "{\n\"job\": \"n4core\", \"n_states\": " << S.F
          << ", \"quads_n4\": " << S.b.quads.size()
          << ", \"empty_g\": " << S.g[0]
          << ", \"empty_prand\": \"" << frac(S.W[0], S.T[0]) << "\""
          << ",\n\"T0\": \"" << i128s(S.T[0]) << "\""
          << ",\n\"max_g\": " << *std::max_element(S.g.begin(), S.g.end());
        { std::map<int,int> h; for (u64 m = 0; m < S.F; ++m) h[S.g[m]]++; o << ",\n\"g_hist\": " << arri(h); }
        { std::map<int,int> h; for (u64 m = 0; m < S.F; ++m) if (S.g[m]==0) h[S.pc[m]]++; o << ",\n\"nP_by_k\": " << arri(h); }
        { u64 L = legal_mask(S.b, 0); int nf = 0, nw = 0; u64 s = L;
          while (s) { int u = __builtin_ctzll(s); s &= s-1; ++nf; if (S.g[1ull<<u] == 0) ++nw; }
          o << ",\n\"empty_n_first\": " << nf << ", \"empty_n_W\": " << nw; }
        o << ",\n\"n_maximal\": " << S.maxsets.size();

        // ---- per-state derived features ----
        struct Rec { int k,g,isP,mu,hx,nL,tri,ncomp,ncge3,nb3,bmax,umax,umin,ndu,nb1;
                     long long b1sp; i128 W,T; long long wins; };
        std::vector<Rec> R; R.reserve(S.F);
        std::vector<std::string> isoV(S.F);
        for (u64 m = 0; m < S.F; ++m) {
            Rec r{}; r.k = S.pc[m]; r.g = S.g[m]; r.isP = (S.g[m]==0);
            r.mu = S.mu[m]; r.hx = S.hx[m]; r.nL = (int)S.nL[m]; r.wins = (long long)S.wins[m];
            r.W = S.W[m]; r.T = S.T[m];
            std::vector<int> emp;
            for (int p = 0; p < S.V; ++p) if (!((m>>p)&1)) emp.push_back(p);
            std::map<int,int> ep; for (size_t i=0;i<emp.size();++i) ep[emp[i]] = (int)i;
            std::set<std::pair<int,int>> es;
            for (u64 q : S.b.quads) {
                if (__builtin_popcountll(q & m) != 2) continue;
                u64 e2 = q & ~m; if (__builtin_popcountll(e2) != 2) continue;
                int a = __builtin_ctzll(e2); e2 &= e2-1; int c2 = __builtin_ctzll(e2);
                if (a > c2) std::swap(a, c2);
                es.insert({ep[a], ep[c2]});
            }
            std::vector<std::vector<int>> adj(emp.size());
            for (auto& e : es) { adj[e.first].push_back(e.second); adj[e.second].push_back(e.first); }
            for (auto& z : adj) { std::sort(z.begin(), z.end()); z.erase(std::unique(z.begin(), z.end()), z.end()); }
            r.tri = 0;
            for (size_t i=0;i<adj.size();++i) for (int y : adj[i]) if (y > (int)i)
                r.tri += (int)std::count(adj[i].begin(), adj[i].end(), y);
            std::vector<char> vis(emp.size(), 0); std::vector<int> sizes;
            for (size_t i=0;i<emp.size();++i) if (!vis[i]) {
                std::vector<int> st; st.push_back((int)i); vis[i]=1; int s2=0;
                while(!st.empty()){int u=st.back();st.pop_back();++s2;for(int v:adj[u])if(!vis[v]){vis[v]=1;st.push_back(v);}}
                sizes.push_back(s2); }
            std::sort(sizes.rbegin(), sizes.rend());
            r.ncomp = (int)sizes.size(); r.ncge3 = 0;
            for (int z : sizes) if (z>=3) ++r.ncge3;
            r.nb3 = 0; for (u64 q : S.b.quads) if (__builtin_popcountll(q & m) == 1) ++r.nb3;
            { std::vector<int> deg(emp.size(),0); for (auto& e : es){deg[e.first]++;deg[e.second]++;}
              std::vector<int> esz; for (auto& e : es) esz.push_back((int)std::count(adj[e.first].begin(), adj[e.first].end(), e.second));
              std::sort(esz.begin(), esz.end()); std::sort(deg.begin(), deg.end());
              std::string s4 = std::to_string(es.size())+"|";
              for (int z : esz) s4 += std::to_string(z)+",";
              s4 += "|"; for (int z : deg) s4 += std::to_string(z)+",";
              s4 += "|"; for (int z : sizes) s4 += std::to_string(z)+",";
              isoV[m] = s4; }
            { std::vector<int> bs, b1; int bmax=0;
              for (int p=0;p<S.V;++p){ if((m>>p)&1) continue; int bp=0; u64 bit=1ull<<p;
                  for (u64 t : S.b.triples_by_pt[p]) if ((m & t) == t) ++bp;
                  bs.push_back(bp); bmax=std::max(bmax,bp); if(bp==1) b1.push_back(p); }
              std::sort(bs.begin(), bs.end()); r.bmax = bmax; r.nb1 = (int)b1.size();
              long long sp = 0;
              for (size_t i=0;i<b1.size();++i) for (size_t j=i+1;j<b1.size();++j)
                  sp += std::max(std::abs(b1[i]%4 - b1[j]%4), std::abs(b1[i]/4 - b1[j]/4));
              r.b1sp = sp; }
            { std::vector<int> us; u64 L = legal_mask(S.b, m); std::set<int> ls;
              u64 s = L; while(s){int u=__builtin_ctzll(s); s&=s-1; ls.insert(u);}
              s = L;
              while (s) { int u = __builtin_ctzll(s); s &= s-1; int c2=0; std::set<int> sn;
                for (u64 t : S.b.triples_by_pt[u]) {
                    if (__builtin_popcountll(t & m) != 2) continue;
                    u64 miss = t & ~m; if (__builtin_popcountll(miss) != 1) continue;
                    int qv = __builtin_ctzll(miss);
                    if (ls.count(qv) && !sn.count(qv)) { sn.insert(qv); ++c2; } }
                us.push_back(c2); }
              if (us.empty()) r.umax = r.umin = r.ndu = 0;
              else { r.umax = *std::max_element(us.begin(), us.end());
                     r.umin = *std::min_element(us.begin(), us.end());
                     std::set<int> ss(us.begin(), us.end()); r.ndu = (int)ss.size(); } }
            R.push_back(r);
        }

        // ---------- B482 ----------
        std::cerr << "[MARK] B482\n";
        { std::map<std::string, std::vector<int>> c1, c2;
          for (size_t i=0;i<R.size();++i){ const Rec& r = R[i];
            c1[std::to_string(r.k)+"/"+std::to_string(r.nL)+"/"+std::to_string(r.tri)].push_back((int)i);
            c2[std::to_string(r.k)+"/"+std::to_string(r.tri)].push_back((int)i); }
          int A=0,w1=0,t1=0,B=0,w2=0,t2=0;
          for (auto& kv : c1) { if (kv.second.size()<4) continue; ++A;
            int mx=0; for(int i:kv.second) mx=std::max(mx,R[i].ncge3);
            std::set<int> gc,gs; int nc=0,nsp=0;
            for(int i:kv.second){ if(2*R[i].ncge3<=mx){gc.insert(R[i].g);++nc;} else {gs.insert(R[i].g);++nsp;} }
            if(nc<2||nsp<2) continue; if(gs.size()>gc.size())++w1; else if(gs.size()==gc.size())++t1; }
          for (auto& kv : c2) { if (kv.second.size()<6) continue; ++B;
            int mx=0; for(int i:kv.second) mx=std::max(mx,R[i].ncge3);
            std::set<int> gc,gs; int nc=0,nsp=0;
            for(int i:kv.second){ if(2*R[i].ncge3<=mx){gc.insert(R[i].g);++nc;} else {gs.insert(R[i].g);++nsp;} }
            if(nc<2||nsp<2) continue; if(gs.size()>gc.size())++w2; else if(gs.size()==gc.size())++t2; }
          o << ",\n\"B482_cells_k_tri_L\": " << A << ", \"B482_spread_more\": " << w1 << ", \"B482_tie\": " << t1
            << ", \"B482_cells_k_tri\": " << B << ", \"B482_spread_more_k_tri\": " << w2 << ", \"B482_tie_k_tri\": " << t2; }

        // ---------- B483 ----------
        { std::map<std::string, std::vector<int>> cells, cells2;
          for (size_t i=0;i<R.size();++i){ const Rec& r=R[i];
            cells[std::to_string(r.k)+"/"+std::to_string(r.nL)].push_back((int)i);
            cells2[std::to_string(r.k)+"/"+std::to_string(r.nL)+"/"+std::to_string(r.nb3)].push_back((int)i); }
          int nc=0, ctlSup=0, ctlTie=0;
          std::vector<std::pair<long long,long long>> pts;  // (total b3 in cell, err rate as 1e6)
          for (auto& kv : cells) { if (kv.second.size()<10) continue; ++nc;
            int nP=0; for(int i:kv.second) nP+=R[i].isP;
            int maj = (2*nP >= (int)kv.second.size())?1:0;
            int err=0; long long tb=0; for(int i:kv.second){ if(R[i].isP!=maj)++err; tb+=R[i].nb3; }
            pts.push_back({tb, (long long)err*1000000/(long long)kv.second.size()}); }
          for (auto& kv : cells2) { if (kv.second.size()<8) continue;
            int lo=1<<30,hi=-1; for(int i:kv.second){lo=std::min(lo,R[i].nb3);hi=std::max(hi,R[i].nb3);}
            if(lo!=hi)++ctlSup; else ++ctlTie; }
          double rho=0; { if (pts.size()>=3) {
            std::vector<double> a(pts.size()),b2(pts.size());
            for(size_t i=0;i<pts.size();++i){a[i]=0;b2[i]=0;
              for(size_t j=0;j<pts.size();++j){ if(pts[j].first<pts[i].first)++a[i]; if(pts[j].second<pts[i].second)++b2[i];}}
            double sx=0,sy=0; for(size_t i=0;i<pts.size();++i){sx+=a[i];sy+=b2[i];} sx/=pts.size();sy/=pts.size();
            double nu=0,d1=0,d2=0; for(size_t i=0;i<pts.size();++i){nu+=(a[i]-sx)*(b2[i]-sy);d1+=(a[i]-sx)*(a[i]-sx);d2+=(b2[i]-sy)*(b2[i]-sy);}
            rho=(d1>0&&d2>0)?nu/std::sqrt(d1*d2):0.0; } }
          o << ",\n\"B483_cells\": " << nc << ", \"B483_spearman_totalb3_vs_err\": " << rho
            << ", \"B483_controlled_cells\": " << ctlSup + ctlTie << ", \"B483_ctl_nonconstant_b3\": " << ctlSup
            << ", \"B483_ctl_constant_b3\": " << ctlTie; }

        // ---------- B484 / B485 ----------
        { std::map<std::string, std::vector<int>> cells;
          for (size_t i=0;i<R.size();++i){ const Rec& r=R[i]; if (r.isP||r.nL==0) continue;
            std::vector<int> bs; for (int p=0;p<S.V;++p){ if((R[i].T? 0:0)){} }
            std::string key = std::to_string(r.k)+"/"+std::to_string(r.nL)+"/";
            u64 m = (u64)i; std::vector<int> bv;
            for (int p=0;p<S.V;++p){ if((m>>p)&1) continue; int bp=0; u64 bit=1ull<<p;
                for (u64 t : S.b.triples_by_pt[p]) if ((m & t)==t) ++bp; bv.push_back(bp); }
            std::sort(bv.begin(), bv.end());
            for (int z : bv) key += std::to_string(z)+",";
            cells[key].push_back((int)i); }
          int usable=0, spr=0, tie=0;
          long long maxd = 0; int pos=0, neg=0, zero=0;
          for (auto& kv : cells) { if (kv.second.size()<4) continue; ++usable;
            long long lo=1LL<<60, hi=-1;
            for (int i:kv.second){ lo=std::min(lo,R[i].wins); hi=std::max(hi,R[i].wins); }
            if (hi>lo){++spr; maxd=std::max(maxd,hi-lo);} else ++tie;
            // B485 rank corr spread vs wins
            if (kv.second.size()>=4) {
              std::vector<double> a(kv.second.size()),b2(kv.second.size());
              for(size_t i=0;i<kv.second.size();++i){a[i]=0;b2[i]=0;
                for(size_t j=0;j<kv.second.size();++j){ if(R[kv.second[j]].b1sp<R[kv.second[i]].b1sp)++a[i];
                                                      if(R[kv.second[j]].wins <R[kv.second[i]].wins )++b2[i];}}
              double sx=0,sy=0; for(size_t i=0;i<kv.second.size();++i){sx+=a[i];sy+=b2[i];} sx/=kv.second.size();sy/=kv.second.size();
              double nu=0,d1=0,d2=0; for(size_t i=0;i<kv.second.size();++i){nu+=(a[i]-sx)*(b2[i]-sy);d1+=(a[i]-sx)*(a[i]-sx);d2+=(b2[i]-sy)*(b2[i]-sy);}
              double rho=(d1>0&&d2>0)?nu/std::sqrt(d1*d2):0.0;
              if(rho>1e-9)++pos; else if(rho<-1e-9)++neg; else ++zero; } }
          o << ",\n\"B484_bhist_cells\": " << usable << ", \"B484_cells_winratio_spread\": " << spr
            << ", \"B484_cells_tied\": " << tie << ", \"B484_max_wins_diff\": " << maxd;
          o << ",\n\"B485_pos\": " << pos << ", \"B485_neg\": " << neg << ", \"B485_zero\": " << zero; }

        // ---------- B486 ----------
        { std::map<std::string, std::vector<int>> cells;
          int nmu3=0;
          for (size_t i=0;i<R.size();++i){ if (R[i].mu<3) continue; ++nmu3;
            cells[std::to_string(R[i].k)+"/"+std::to_string(R[i].nL)+"/"+std::to_string(R[i].hx)].push_back((int)i); }
          int nc=0,nz=0,strict=0;
          for (auto& kv : cells) { if (kv.second.size()<6) continue;
            int nP=0,nN=0; for(int i:kv.second) (R[i].isP? nP : nN)++;
            if(nP<2||nN<2) continue; ++nc;
            i128 hiP=0, loP=0, hiN=0, loN=0; bool f1=1,f2=1,f3=1,f4=1;
            for (int i:kv.second) { const Rec& r=R[i];
              if (r.isP){ if(f1||r.W>hiP)hiP=r.W; if(f1||r.W<loP)loP=r.W; f1=0; }
              else { if(f2||r.W>hiN)hiN=r.W; if(f2||r.W<loN)loN=r.W; f2=0; } }
            // same cell: compare only if denominators equal (they generally differ)
            bool same = true; for (int i:kv.second) if (R[i].T != R[kv.second[0]].T) same = false;
            if (same) { if (hiP!=loP || hiN!=loN) ++nz;
                        if (hiP<loN || hiN<loP) ++strict; } }
          o << ",\n\"B486_n_mu_ge3\": " << nmu3 << ", \"B486_cells\": " << nc
            << ", \"B486_cells_nonzero_gap\": " << nz << ", \"B486_cells_strict\": " << strict; }

        // ---------- B487 ----------
        { std::map<std::string, std::vector<int>> cells;
          for (size_t i=0;i<R.size();++i){ if (R[i].isP) continue;
            cells[std::to_string(R[i].k)+"/"+std::to_string(R[i].umax)+"/"+std::to_string(R[i].umin)].push_back((int)i); }
          int nc=0,pos=0,neg=0,zero=0; double bmax=-2,bmin=2;
          for (auto& kv : cells) { if (kv.second.size()<6) continue;
            std::vector<double> a(kv.second.size()),b2(kv.second.size());
            for(size_t i=0;i<kv.second.size();++i){a[i]=0;b2[i]=0;
              for(size_t j=0;j<kv.second.size();++j){ if(R[kv.second[j]].ndu<R[kv.second[i]].ndu)++a[i];
                                                    if(R[kv.second[j]].g <R[kv.second[i]].g )++b2[i];}}
            double sx=0,sy=0; for(size_t i=0;i<kv.second.size();++i){sx+=a[i];sy+=b2[i];} sx/=kv.second.size();sy/=kv.second.size();
            double nu=0,d1=0,d2=0; for(size_t i=0;i<kv.second.size();++i){nu+=(a[i]-sx)*(b2[i]-sy);d1+=(a[i]-sx)*(a[i]-sx);d2+=(b2[i]-sy)*(b2[i]-sy);}
            double rho=(d1>0&&d2>0)?nu/std::sqrt(d1*d2):0.0;
            ++nc; if(rho>1e-9)++pos; else if(rho<-1e-9)++neg; else ++zero;
            bmax=std::max(bmax,rho); bmin=std::min(bmin,rho); }
          o << ",\n\"B487_cells\": " << nc << ", \"B487_pos\": " << pos << ", \"B487_neg\": " << neg
            << ", \"B487_zero\": " << zero << ", \"B487_rho_max\": " << bmax << ", \"B487_rho_min\": " << bmin; }

        // ---------- B488 ----------
        { std::map<int, std::vector<int>> cells; for (size_t i=0;i<R.size();++i) cells[R[i].k].push_back((int)i);
          int ncmp=0,nflip=0; std::string det;
          auto rho=[&](const std::vector<int>& s)->double{
            if (s.size()<8) return NAN;
            std::vector<double> a(s.size()),b2(s.size());
            for(size_t i=0;i<s.size();++i){a[i]=0;b2[i]=0;
              for(size_t j=0;j<s.size();++j){ if(R[s[j]].tri<R[s[i]].tri)++a[i]; if(R[s[j]].g <R[s[i]].g )++b2[i];}}
            double sx=0,sy=0; for(size_t i=0;i<s.size();++i){sx+=a[i];sy+=b2[i];} sx/=s.size();sy/=s.size();
            double nu=0,d1=0,d2=0; for(size_t i=0;i<s.size();++i){nu+=(a[i]-sx)*(b2[i]-sy);d1+=(a[i]-sx)*(a[i]-sx);d2+=(b2[i]-sy)*(b2[i]-sy);}
            return (d1>0&&d2>0)?nu/std::sqrt(d1*d2):0.0; };
          for (auto& kv : cells) { if (kv.second.size()<10) continue; ++ncmp;
            std::map<std::string,int> byIso;
            for (int i : kv.second) if (!byIso.count(isoV[i])) byIso[isoV[i]] = i;
            std::vector<int> reps; for (auto& z : byIso) reps.push_back(z.second);
            double r1 = rho(kv.second), r2 = rho(reps);
            if (std::isfinite(r1) && std::isfinite(r2)) {
              if (r1*r2 < 0) ++nflip;
              det += "\"k"+std::to_string(kv.first)+"\":{\"n\":"+std::to_string(kv.second.size())+
                     ",\"n_iso\":"+std::to_string(byIso.size())+
                     ",\"rho_raw\":"+std::to_string(r1)+",\"rho_dedup\":"+std::to_string(r2)+"},"; } }
          o << ",\n\"B488_comparable\": " << ncmp << ", \"B488_sign_flips\": " << nflip
            << ",\n\"B488_detail\": {" << (det.size()? det.substr(0,det.size()-1) : "") << "}"; }

        // ---------- B489 ----------
        { std::map<std::string, std::vector<int>> cells;
          for (size_t i=0;i<R.size();++i) cells[std::to_string(R[i].k)+"/"+std::to_string(R[i].nL)].push_back((int)i);
          int nc=0,pos=0,neg=0,zero=0;
          for (auto& kv : cells) { if (kv.second.size()<8) continue; ++nc;
            // x = Tstar_w - WFT_w ; y = illusion = p if P else 1-p
            std::vector<int> a(kv.second.size());
            std::vector<std::pair<i128,i128>> fr(kv.second.size());
            for (size_t i=0;i<kv.second.size();++i){ const Rec& r=R[kv.second[i]];
              a[i]=0; fr[i] = r.isP ? std::make_pair(r.W, r.T) : std::make_pair(r.T-r.W, r.T); }
            for (size_t i=0;i<kv.second.size();++i){ int x = (int)S.tstar[kv.second[i]].size() ? 0 : 0;
              (void)x; }
            std::vector<int> tw(kv.second.size());
            for (size_t i=0;i<kv.second.size();++i){ u64 m=(u64)kv.second[i];
              int ts = (int)S.tstar[m].size(), wf = (int)S.wft[m].size();
              int tsw = S.tstar[m].empty()?0:S.tstar[m].back()-S.tstar[m].front();
              int wfw = S.wft[m].empty()?0:S.wft[m].back()-S.wft[m].front();
              tw[i] = tsw - wfw; }
            for (size_t i=0;i<kv.second.size();++i) for (size_t j=0;j<kv.second.size();++j) if (tw[j]<tw[i]) ++a[i];
            std::vector<int> b2(kv.second.size(), 0);
            for (size_t i=0;i<kv.second.size();++i) for (size_t j=0;j<kv.second.size();++j)
                if (fr[j].first*fr[i].second < fr[i].first*fr[j].second) ++b2[i];
            double sx=0,sy=0; for(size_t i=0;i<kv.second.size();++i){sx+=a[i];sy+=b2[i];} sx/=kv.second.size();sy/=kv.second.size();
            double nu=0,d1=0,d2=0; for(size_t i=0;i<kv.second.size();++i){nu+=(a[i]-sx)*(b2[i]-sy);d1+=(a[i]-sx)*(a[i]-sx);d2+=(b2[i]-sy)*(b2[i]-sy);}
            double rho=(d1>0&&d2>0)?nu/std::sqrt(d1*d2):0.0;
            if(rho>1e-9)++pos; else if(rho<-1e-9)++neg; else ++zero; }
          o << ",\n\"B489_cells\": " << nc << ", \"B489_pos\": " << pos << ", \"B489_neg\": " << neg << ", \"B489_zero\": " << zero; }

        // ---------- B490 ----------
        { auto coll=[&](auto kf){ std::map<std::string,std::set<int>> kg,kp,kl;
            for (size_t i=0;i<R.size();++i){ std::string k = kf(R[i]);
              kg[k].insert(R[i].g); kp[k].insert(R[i].isP);
              u64 m=(u64)i; int wfw = S.wft[m].empty()?0:S.wft[m].back()-S.wft[m].front(); kl[k].insert(wfw); }
            int mg=0,mp=0,ml=0; for (auto& kv : kg){ if(kv.second.size()>1)++mg;
              if(kp[kv.first].size()>1)++mp; if(kl[kv.first].size()>1)++ml; }
            return std::array<long long,4>{(long long)kg.size(), mg, mp, ml}; };
          auto a1 = coll([](const Rec& r){ return std::to_string(r.k)+"/"+std::to_string(r.nL); });
          auto a2 = coll([](const Rec& r){ return std::to_string(r.k)+"/"+std::to_string(r.nL)+"/"+std::to_string(r.tri)
                                             +"/"+std::to_string(r.ncomp)+"/"+std::to_string(r.ncge3)+"/"+std::to_string(r.bmax); });
          auto a3 = coll([&](const Rec& r){ u64 m=(u64)&r - (u64)R.data(); (void)m;
            return std::to_string(r.k)+"/"+std::to_string(r.nL)+"/"+std::to_string(r.tri)
                   +"/"+std::to_string(r.ncomp)+"/"+std::to_string(r.ncge3)+"/"+std::to_string(r.bmax)
                   +"/"+std::to_string(r.umax)+"/"+std::to_string(r.ndu); });
          o << ",\n\"B490_small\": {\"n_keys\": " << a1[0] << ", \"multi_g\": " << a1[1] << ", \"multi_P\": " << a1[2] << ", \"multi_WFTw\": " << a1[3] << "}"
            << ",\n\"B490_mid\": {\"n_keys\": " << a2[0] << ", \"multi_g\": " << a2[1] << ", \"multi_P\": " << a2[2] << ", \"multi_WFTw\": " << a2[3] << "}"
            << ",\n\"B490_big\": {\"n_keys\": " << a3[0] << ", \"multi_g\": " << a3[1] << ", \"multi_P\": " << a3[2] << ", \"multi_WFTw\": " << a3[3] << "}"; }

        // ---------- B507 ----------
        { std::map<int, std::pair<i128,i128>> bestP, minN; std::map<int,int> cP,cN;
          for (u64 m = 0; m < S.F; ++m) { int hh = S.hx[m];
            if (S.g[m]==0) { ++cP[hh]; auto it=bestP.find(hh);
              if (it==bestP.end() || S.W[m]*it->second.second > it->second.first*S.T[m]) bestP[hh]={S.W[m],S.T[m]}; }
            else { ++cN[hh]; auto it=minN.find(hh);
              if (it==minN.end() || S.W[m]*it->second.second < it->second.first*S.T[m]) minN[hh]={S.W[m],S.T[m]}; } }
          o << ",\n\"B507_max_pr_by_h\": {";
          bool f=true;
          for (auto& kv : bestP) { if(!f) o<<", "; f=false;
            o << "\"" << kv.first << "\": {\"n_P\": " << cP[kv.first] << ", \"max_pr\": \"" << frac(kv.second.first, kv.second.second) << "\"";
            if (minN.count(kv.first)) { auto& mn = minN[kv.first];
              o << ", \"min_pr_N\": \"" << frac(mn.first, mn.second) << "\", \"n_N\": " << cN[kv.first]
                << ", \"Pmax_plus_Nmin_lt_1\": " << ((kv.second.first*mn.second + mn.first*kv.second.second < kv.second.second*mn.second) ? "true":"false");
            }
            o << "}"; }
          o << "}"; }

        // ---------- B504 / B505 / B508 / B510 ----------
        { int nW1=0, maxDecoys=0; long long maxDecoys_occ=-1; int nWgehalf=0;
          i128 bW=0,bT=1; long long b505occ=-1;
          std::map<std::string, std::pair<long long,long long>> gs;  // prand -> (minW,maxW)
          int n510=0; long long occ510=-1;
          for (u64 m = 0; m < S.F; ++m) {
            if (S.nL[m]==0) continue;
            if (S.g[m]==0) continue;                       // N positions only
            if (S.wins[m] == 1) { ++nW1; if ((long long)S.nL[m]-1 > maxDecoys){maxDecoys=(long long)S.nL[m]-1; maxDecoys_occ=(long long)m;} }
            if (2*S.wins[m] >= S.nL[m]) { ++nWgehalf;
              if (S.W[m]*bT < bW*S.T[m]) { bW=S.W[m]; bT=S.T[m]; b505occ=(long long)m; } }
            { std::string key = frac(S.W[m], S.T[m]);
              auto it = gs.find(key);
              if (it==gs.end()) gs[key]={S.wins[m],S.wins[m]};
              else { it->second.first = std::min(it->second.first, (long long)S.wins[m]);
                     it->second.second = std::max(it->second.second, (long long)S.wins[m]); } }
            { u64 L = legal_mask(S.b, m); u64 winMask = 0; u64 s = L;
              while (s) { int u=__builtin_ctzll(s); s&=s-1; if (S.g[m|(1ull<<u)]==0) winMask |= 1ull<<u; }
              if (winMask) {
                int bestMv=-1, worstMv=-1;
                s = L;
                while (s) { int u=__builtin_ctzll(s); s&=s-1; u64 c=m|(1ull<<u);
                  if (winMask & (1ull<<u)) { if (bestMv<0 || S.W[c]*S.T[(u64)bestMv|0] < 0) {}
                    if (bestMv<0) bestMv=u; else { u64 cb=m|(1ull<<bestMv);
                      if (S.W[c]*S.T[cb] < S.W[cb]*S.T[c]) bestMv=u; } }
                  else { if (worstMv<0) worstMv=u; else { u64 cw=m|(1ull<<worstMv);
                      if (S.W[c]*S.T[cw] > S.W[cw]*S.T[c]) worstMv=u; } } }
                if (bestMv>=0 && worstMv>=0) { u64 cb=m|(1ull<<bestMv), cw=m|(1ull<<worstMv);
                  if (S.W[cb]*S.T[cw] < S.W[cw]*S.T[cb]) { ++n510; if (occ510<0) occ510=(long long)m; } } } }
          int n508multi=0, n508max=0; std::string k508;
          for (auto& kv : gs) { long long d = kv.second.second - kv.second.first;
            if (d>0) ++n508multi; if (d>n508max){n508max=(int)d;k508=kv.first;} }
          o << ",\n\"B504_nW1\": " << nW1 << ", \"B504_max_decoys\": " << maxDecoys
            << ", \"B504_max_decoys_occ\": " << maxDecoys_occ << ", \"B504_n_Wge_half\": " << nWgehalf
            << ",\n\"B505_min_pr\": \"" << frac(bW, bT) << "\", \"B505_occ\": " << b505occ
            << ",\n\"B508_n_distinct_prand_N\": " << gs.size() << ", \"B508_groups_W_spread\": " << n508multi
            << ", \"B508_max_W_diff\": " << n508max << ", \"B508_key\": \"" << k508 << "\""
            << ",\n\"B510_n_hits\": " << n510 << ", \"B510_occ\": " << occ510; }

        // ---------- B494 / B495 / B496 / B499 / B500 : exact random-greedy ----------
        { // reach(x) = gpaths[x] / T0 for terminal x
            std::map<int, std::vector<int>> byStab;
            // D4 stabiliser size of a set in the 4x4 board
            for (size_t i = 0; i < S.maxsets.size(); ++i) {
                u64 m = S.maxsets[i];
                int minx=9,miny=9,maxx=-1,maxy=-1;
                for (int p=0;p<S.V;++p) if((m>>p)&1){ int x=p%4,y=p/4;
                    minx=std::min(minx,x);maxx=std::max(maxx,x);miny=std::min(miny,y);maxy=std::max(maxy,y);}
                int Wd=maxx-minx, Hd=maxy-miny; int stab=0;
                for (int kk=0;kk<8;++kk){ bool ok=true;
                    for (int p=0;p<S.V;++p) if((m>>p)&1){ int x=p%4-minx, y=p/4-miny,a,c;
                        if(kk==0){a=x;c=y;} else if(kk==1){a=y;c=x;} else if(kk==2){a=Wd-x;c=y;}
                        else if(kk==3){a=x;c=Hd-y;} else if(kk==4){a=Wd-x;c=Hd-y;} else if(kk==5){a=y;c=Hd-x;}
                        else if(kk==6){a=Wd-y;c=x;} else {a=Wd-y;c=Hd-x;}
                        int q=c*4+a; if(q<0||q>=16||!((m>>q)&1)){ok=false;break;} }
                    if(ok) ++stab; }
                byStab[S.pc[m]].push_back(i);
                (void)stab;
            }
            // full reach profile per (k, D4-orbit-invariant) is too fine; use k and
            // the exact reach fraction, aggregated by k
            std::map<int, std::pair<i128,i128>> agg;  // k -> (sum paths, count)
            for (u64 m : S.maxsets) { auto& a = agg[S.pc[m]]; a.first += S.gpaths[m]; ++a.second; }
            o << ",\n\"B494B495_reach_by_k\": {";
            bool f=true; for (auto& kv : agg) { if(!f)o<<", "; f=false;
                o << "\"" << kv.first << "\": {\"n\": " << kv.second.second
                  << ", \"sum_reach\": \"" << i128s(kv.second.first) << "\", \"mean_pr\": \""
                  << frac(kv.second.first, S.T0) << "\"}"; }
            o << "}";
            // B495: group terminals by the |L| profile over subset sizes
            // profile(x) = multiset of |L(S)| for S subseteq x, grouped by |S|
            std::map<std::string, std::vector<u64>> prof;
            for (u64 m : S.maxsets) {
                std::string key;
                for (int kk = 0; kk <= S.pc[m]; ++kk) { key += std::to_string(kk) + ":";
                    std::vector<long long> cnt;
                    // enumerate subsets of m of size kk
                    cnt.assign(16, 0);
                    std::vector<int> pts; for (int p=0;p<S.V;++p) if((m>>p)&1) pts.push_back(p);
                    // simple recursion
                    std::function<void(int,int,u64)> rec=[&](int start,int depth,u64 occ){
                        if (depth==kk) { cnt[(int)S.nL[occ]]++; return; }
                        for (int i=start;i<(int)pts.size();++i) rec(i+1,depth+1,occ|(1ull<<pts[i])); };
                    rec(0,0,0);
                    for (int c2=0;c2<16;++c2) key += std::to_string(c2) + "." + std::to_string(cnt[c2]) + ",";
                    key += ";";
                }
                prof[key].push_back(m);
            }
            int ngrp_multi=0, ngrp=0; long long ngrp_examples=0; i128 maxratio_num=0,maxratio_den=1;
            std::string maxratio_key;
            for (auto& kv : prof) { if (kv.second.size()<2) continue; ++ngrp;
                i128 lo=-1, hi=0; for (u64 m : kv.second) { i128 r = S.gpaths[m];
                    if (lo<0||r<lo) lo=r; if (r>hi) hi=r; }
                if (hi!=lo) { ++ngrp_multi; ngrp_examples += (long long)kv.second.size(); }
                if (lo>0 && hi*maxratio_den > maxratio_num*lo) { maxratio_num=hi; maxratio_den=lo; maxratio_key=kv.first.substr(0,40); } }
            o << ",\n\"B495_profile_groups_ge2\": " << ngrp << ", \"B495_groups_with_reach_spread\": " << ngrp_multi
              << ", \"B495_members_in_spreading_groups\": " << ngrp_examples
              << ", \"B495_max_reach_ratio\": \"" << frac(maxratio_num, maxratio_den) << "\"";
            // B496: within (k, stab-of-D4-image) cells
            // use the D4 orbit of the set as the cell key (excludes 4 reflections only
            // if the set is not reflection symmetric) -> use orbit SIZE as the cell
            std::map<std::string, std::vector<u64>> cell2;
            for (u64 m : S.maxsets) {
                int minx=9,miny=9,maxx=-1,maxy=-1;
                for (int p=0;p<S.V;++p) if((m>>p)&1){int x=p%4,y=p/4;minx=std::min(minx,x);maxx=std::max(maxx,x);miny=std::min(miny,y);maxy=std::max(maxy,y);}
                int Wd=maxx-minx,Hd=maxy-miny; std::set<std::vector<int>> imgs;
                for (int kk=0;kk<8;++kk){ std::vector<int> im;
                    for (int p=0;p<S.V;++p) if((m>>p)&1){int x=p%4-minx,y=p/4-miny,a,c;
                        if(kk==0){a=x;c=y;} else if(kk==1){a=y;c=x;} else if(kk==2){a=Wd-x;c=y;}
                        else if(kk==3){a=x;c=Hd-y;} else if(kk==4){a=Wd-x;c=Hd-y;} else if(kk==5){a=y;c=Hd-x;}
                        else if(kk==6){a=Wd-y;c=x;} else {a=Wd-y;c=Hd-x;} im.push_back(c*4+a);}
                    std::sort(im.begin(),im.end()); imgs.insert(im); }
                cell2[std::to_string(S.pc[m])+"/"+std::to_string((int)imgs.size())].push_back(m);
            }
            o << ",\n\"B496_cells\": [";
            f=true; i128 bestRatio=0, bestRatio_den=1; std::string bestCell;
            for (auto& kv : cell2) { if (!f) o<<", "; f=false;
                i128 lo=-1,hi=0; for (u64 m:kv.second){i128 r=S.gpaths[m]; if(lo<0||r<lo)lo=r; if(r>hi)hi=r;}
                o << "{\"k_orbit\": \"" << kv.first << "\", \"n\": " << kv.second.size()
                  << ", \"min_reach\": \"" << frac(lo, S.T0) << "\", \"max_reach\": \"" << frac(hi, S.T0) << "\"";
                if (lo>0) { i128 rr_num=hi, rr_den=lo;
                  o << ", \"ratio\": \"" << frac(rr_num, rr_den) << "\"";
                  if (rr_num*bestRatio_den > bestRatio*rr_den) { bestRatio=rr_num; bestRatio_den=rr_den; bestCell=kv.first; } }
                o << "}"; }
            o << "]";
            o << ",\n\"B496_best_ratio\": \"" << frac(bestRatio, bestRatio_den) << "\", \"B496_best_cell\": \"" << bestCell << "\"";
            // B499: per first move, E[X] and P(min size) and P(max size)
            if (job == "n4core" || job == "greedy") {
              int kmin = 1<<30, kmax = 0;
              for (u64 m : S.maxsets) { kmin=std::min(kmin,(int)S.pc[m]); kmax=std::max(kmax,(int)S.pc[m]); }
              o << ",\n\"B499_term_size_range\": [" << kmin << ", " << kmax << "]";
              struct FM { int mv; i128 eNum; i128 pmin; i128 pmax; long long cnt; };
              std::vector<FM> fms;
              i128 bestRatio499 = 0; long long ba = 0, bb = 0;
              u64 L0 = legal_mask(S.b, 0);
              (void)L0;
              // Do it properly: gpaths restricted to first move u.
              for (int uu = 0; uu < S.V; ++uu) {
                  if (!((legal_mask(S.b,0) >> uu) & 1)) continue;
                  i128 eNum = 0, pmin = 0, pmax = 0, cnt = 0;
                  // fstart[x] = number of move-sequences from {u} to x
                  std::vector<long long> fs(S.F, 0);
                  fs[1ull<<uu] = 1;
                  for (int kk = 1; kk < S.V; ++kk) for (u64 mm = 0; mm < S.F; ++mm) {
                      if (S.pc[mm] != kk || !fs[mm]) continue;
                      u64 LL = legal_mask(S.b, mm), s2 = LL;
                      while (s2) { int uu2 = __builtin_ctzll(s2); s2 &= s2-1; fs[mm | (1ull<<uu2)] += fs[mm]; } }
                  for (u64 m : S.maxsets) { if (!fs[m]) continue;
                      cnt += fs[m]; eNum += (i128)S.pc[m] * fs[m];
                      if (S.pc[m] == kmin) pmin += fs[m];
                      if (S.pc[m] == kmax) pmax += fs[m]; }
                  fms.push_back({uu, eNum, pmin, pmax, (long long)cnt});
              }
              o << ",\n\"B499_first_moves\": [";
              f = true;
              for (auto& fm : fms) { if(!f) o<<", "; f=false;
                  o << "{\"mv\": " << fm.mv << ", \"E_X\": \"" << frac(fm.eNum, fm.cnt) << "\""
                    << ", \"P_min\": \"" << frac(fm.pmin, fm.cnt ? fm.cnt : 1) << "\", \"P_max\": \"" << frac(fm.pmax, fm.cnt ? fm.cnt : 1) << "\"}"; }
              o << "]";
              for (size_t i=0;i<fms.size();++i) for (size_t j=i+1;j<fms.size();++j) {
                  if (!fms[i].cnt || !fms[j].cnt) continue;
                  // |dE| relative
                  i128 de = fms[i].eNum*fms[j].cnt - fms[j].eNum*fms[i].cnt; de = de<0? -de: de;
                  i128 den = (i128)fms[i].eNum*fms[j].cnt; if (den<0) den=-den;
                  if (de * 50 <= den) {   // |dE| <= 1/50 * E
                      if (fms[j].pmin*fms[i].cnt > 0) {
                        i128 r1 = fms[i].pmin*fms[j].cnt, r2 = fms[j].pmin*fms[i].cnt;
                        i128 mn = r1<r2?r1:r2, mx = r1<r2?r2:r1;
                        if (mn>0 && mx*bestRatio499 > bestRatio499*mn) {
                            bestRatio499 = mx; ba=fms[i].mv; bb=fms[j].mv; } } } }
              o << ",\n\"B499_best_pmin_ratio\": \"" << frac(bestRatio499, 1) << "\""
                << ", \"B499_pair\": [" << ba << ", " << bb << "]"; }
            // B500: exact cut bounds from the LAST layer only (exact and cheap).
            { i128 sumCutLo = 0, sumCutHi = 0, sumTrue = 0; int nb = 0;
              for (u64 m : S.maxsets) {
                  i128 pLo = 1<<30, pHi = 0;
                  for (int p = 0; p < S.V; ++p) if ((m>>p)&1) { i128 L = S.nL[m ^ (1ull<<p)];
                      pLo = std::min(pLo, L); pHi = std::max(pHi, L); }
                  if (pLo >= (i128)(1<<30) || pHi == 0) continue;
                  ++nb;
                  sumCutLo += S.T0 / pHi;      // reach(x) >= 1/pHi
                  sumCutHi += S.T0 / pLo;      // reach(x) <= 1/pLo
                  sumTrue  += S.gpaths[m]; }
              o << ",\n\"B500_terminals\": " << S.maxsets.size() << ", \"B500_with_bounds\": " << nb
                << ", \"B500_cut_lo_sum\": \"" << frac(sumCutLo, S.T0) << "\""
                << ", \"B500_cut_hi_sum\": \"" << frac(sumCutHi, S.T0) << "\""
                << ", \"B500_exact_sum\": \"" << frac(sumTrue, S.T0) << "\""; }
        } }
        o << "\n}\n";
        std::cerr << "[MARK] about to print\n";
        std::cout << o.str() << std::flush;
        return 0;
    }
    std::cout << "unknown job\n";
    return 0;
}
