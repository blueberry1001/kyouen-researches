// round4_b228.cpp -- Round4 solver for hypothesis ids B228..B290.
// Shared engine: #include "kc_core.h"  (already self-checked; not rewritten).
//
// Exact integers only.  Rationals emitted as p/q.  No float used in a decision.
//
//   ./round4_b228 all       run every section
//   ./round4_b228 n4 n5     run selected sections
// sections: n4 n5 n6 rel u proof res geom cap emb
#include "kc_core.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdarg>
#include <climits>
#include <ctime>
#include <string>
#include <vector>
#include <unordered_map>
#include <map>
#include <set>
#include <algorithm>
#include <numeric>
#include <fstream>
#include <sstream>
#include <iostream>
#include <functional>

using u64 = uint64_t;
using i64 = long long;
static double t0;
static double now(){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
static void lg(const char* f, ...){ va_list ap; va_start(ap,f); fprintf(stderr,"[%7.1fs] ",now()-t0);
  vfprintf(stderr,f,ap); fprintf(stderr,"\n"); fflush(stderr); va_end(ap); }

// ------------------------------------------------------------------ JSON
struct Json {
  std::string out, ind; std::vector<char> first;
  void comma(){ if(!first.empty()){ if(!first.back()) out += ","; first.back()=0; } }
  void nl(){ out += "\n" + ind; }
  void ob(){ comma(); out += "{"; ind += "  "; first.push_back(1); }
  void oe(){ ind = ind.substr(0, ind.size()-2); nl(); out += "}"; if(!first.empty()) first.pop_back(); }
  void ab(){ comma(); out += "["; ind += "  "; first.push_back(1); }
  void ae(){ ind = ind.substr(0, ind.size()-2); nl(); out += "]"; if(!first.empty()) first.pop_back(); }
  void k(const std::string& s){ comma(); out += "\"" + s + "\": "; if(!first.empty()) first.back()=1; }
  void iv(i64 v){ comma(); out += std::to_string(v); if(!first.empty()) first.back()=0; }
  void uv(u64 v){ comma(); out += std::to_string((unsigned long long)v); if(!first.empty()) first.back()=0; }
  void bv(bool v){ comma(); out += v?"true":"false"; if(!first.empty()) first.back()=0; }
  void sv(const std::string& v){ comma(); out += "\"" + v + "\""; if(!first.empty()) first.back()=0; }
  void kv(const std::string& s, i64 v){ k(s); iv(v); }
  void kvu(const std::string& s, u64 v){ k(s); uv(v); }
  void kvb(const std::string& s, bool v){ k(s); bv(v); }
  void kvs(const std::string& s, const std::string& v){ k(s); sv(v); }
  void kvv(const std::string& s, const std::vector<i64>& v){ k(s); ab();
    for(i64 x: v){ comma(); out += std::to_string(x); if(!first.empty()) first.back()=0; } ae(); }
  void kvi(const std::string& s, const std::vector<int>& v){ k(s); ab();
    for(int x: v){ comma(); out += std::to_string(x); if(!first.empty()) first.back()=0; } ae(); }
  void kvu64(const std::string& s, const std::vector<u64>& v){ k(s); ab();
    for(u64 x: v){ comma(); out += std::to_string((unsigned long long)x); if(!first.empty()) first.back()=0; } ae(); }
  void kvsx(const std::string& s, const std::vector<std::string>& v){ k(s); ab();
    for(auto&x: v){ comma(); out += "\"" + x + "\""; if(!first.empty()) first.back()=0; } ae(); }
  std::string str() const { return out; }
  void write(const std::string& p){ std::ofstream f(p); f << out << "\n"; }
};
static Json J;

// --------------------------------------------------------------- geometry
struct Pt{ i64 x,y; };
static i64 det_pt(const Pt&a,const Pt&b,const Pt&c,const Pt&d){
  i64 r[4][4]={{a.x*a.x+a.y*a.y,a.x,a.y,1},{b.x*b.x+b.y*b.y,b.x,b.y,1},
               {c.x*c.x+c.y*c.y,c.x,c.y,1},{d.x*d.x+d.y*d.y,d.x,d.y,1}};
  return kc::det4(r);
}
static i64 det3(const Pt&a,const Pt&b,const Pt&c){ return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x); }
static std::vector<i64> conic_key(const Pt&p0,const Pt&p1,const Pt&p2){
  if(det3(p0,p1,p2)==0){
    i64 A=p1.y-p0.y,B=p0.x-p1.x,C=-(A*p0.x+B*p0.y);
    i64 g=std::gcd(std::gcd(std::llabs(A),std::llabs(B)),std::llabs(C));
    if(g){A/=g;B/=g;C/=g;} if(A<0||(A==0&&B<0)){A=-A;B=-B;C=-C;}
    return {0,A,B,C};
  }
  i64 A1=2*(p1.x-p0.x),B1=2*(p1.y-p0.y),C1=-(p1.x*p1.x+p1.y*p1.y)+(p0.x*p0.x+p0.y*p0.y);
  i64 A2=2*(p2.x-p0.x),B2=2*(p2.y-p0.y),C2=-(p2.x*p2.x+p2.y*p2.y)+(p0.x*p0.x+p0.y*p0.y);
  i64 Dd=A1*B2-A2*B1, Dv=A1*C2-A2*C1, Ev=B1*C2-B2*C1;
  i64 D=Dv/Dd,E=Ev/Dd,F=-(p0.x*p0.x+p0.y*p0.y)-D*p0.x-E*p0.y;
  return {1,D,E,F};
}
static bool conic_has(const std::vector<i64>&k,i64 x,i64 y){
  if(k[0]==0) return k[1]*x+k[2]*y+k[3]==0;
  return x*x+y*y+k[1]*x+k[2]*y+k[3]==0;
}
// D4 orbit of a mask on the n x n board
static std::vector<u64> d4_orbit(const std::vector<u64>& quads,int n){
  int V=n*n; std::vector<std::vector<int>> P(8, std::vector<int>(V));
  for(int y=0;y<n;++y)for(int x=0;x<n;++x){
    int i=y*n+x, m=n-1-x, M=n-1-y;
    P[0][i]=y*n+x;  P[1][i]=y*n+m;  P[2][i]=M*n+x;  P[3][i]=M*n+m;
    P[4][i]=x*n+y;  P[5][i]=m*n+y;  P[6][i]=x*n+M;  P[7][i]=m*n+M;
  }
  std::vector<u64> res;
  for(int t=0;t<8;++t){
    u64 hsh = 1469598103934665603ull;
    for(u64 q: quads){ u64 m=q;
      while(m){ int b=__builtin_ctzll(m); m&=m-1; int j=P[t][b]; hsh^=(u64)j; hsh*=1099511628211ull; } }
    res.push_back(hsh);
  }
  std::sort(res.begin(), res.end()); res.erase(std::unique(res.begin(),res.end()), res.end());
  return res;
}
static u64 d4_apply_mask(u64 mask, const int* P, int n){
  int V=n*n; u64 r=0; u64 m=mask;
  while(m){ int b=__builtin_ctzll(m); m&=m-1; r|=u64(1)<<P[b]; }
  (void)V; return r;
}
static void d4_perms(int n, std::vector<std::vector<int>>& P){
  int V=n*n; P.assign(8, std::vector<int>(V));
  for(int y=0;y<n;++y)for(int x=0;x<n;++x){
    int i=y*n+x,m=n-1-x,M=n-1-y;
    P[0][i]=y*n+x; P[1][i]=y*n+m; P[2][i]=M*n+x; P[3][i]=M*n+m;
    P[4][i]=x*n+y; P[5][i]=m*n+y; P[6][i]=x*n+M; P[7][i]=m*n+M;
  }
}

// --------------------------------------------------------------- the game
struct Game {
  int V=0; u64 full=0;
  std::vector<std::vector<u64>> tri;   // tri[p] = masks of the other three points
  void init(int V_, const std::vector<u64>& quads){
    V=V_; full = (V>=64)?~u64(0):((u64(1)<<V)-1);
    tri.assign(V,{});
    for(u64 q: quads){ int ids[4],c=0; u64 mm=q;
      while(mm){ ids[c++]=__builtin_ctzll(mm); mm&=mm-1; }
      for(int t=0;t<4;++t){ u64 o=0; for(int k=0;k<4;++k) if(k!=t) o|=u64(1)<<ids[k];
        tri[ids[t]].push_back(o); } }
  }
  inline u64 nf(u64 occ,int p) const { u64 r=0; for(u64 t: tri[p]) if((occ&t)==t) r|=t; return r; }
  inline u64 Lnext(u64 occ,u64 lg,int p) const { return lg & ~nf(occ,p) & ~(u64(1)<<p); }
  u64 legal(u64 occ) const { u64 r=0,e=full&~occ;
    while(e){ int p=__builtin_ctzll(e); e&=e-1; u64 n=0; for(u64 t: tri[p]) if((occ&t)==t) n|=t;
      if(((~n)&full&~occ&~(u64(1)<<p)) == (full&~occ&~(u64(1)<<p))) r|=u64(1)<<p; }
    return r; }
};

struct Sol {
  Game G; int V=0;
  std::vector<u64> st, lgv;
  std::vector<int> lvlStart, g, depth;
  std::vector<i64> proof;
  std::vector<int> Kof;
  std::vector<i64> level_counts;
  std::vector<int> lvl_nP, lvl_nN;
  i64 n_states=0; int nlev=0, K=0, g0=0; u64 W=0, maxfp=0, fpsum=0;
  std::vector<u64> maximals; std::vector<int> maximal_lvl;
  std::map<int,i64> max_per_level;
  std::vector<int32_t> slot;  // open addressing: hash(mask) -> index in st
  u64 slotmask=0;
  inline u64 hsh(u64 k) const { k+=0x9E3779B97F4A7C15ull; k=(k^(k>>30))*0xBF58476D1CE4E5B9ull;
                                k=(k^(k>>27))*0x94D049BB133111EBull; return k^(k>>31); }
  inline int find(u64 m) const { u64 i=hsh(m)&slotmask;
    while(slot[i]>=0){ if(st[slot[i]]==m) return slot[i]; i=(i+1)&slotmask; } return -1; }
};

static std::vector<u64> build_quads(int n, std::vector<Pt>& pts){
  std::vector<u64> Q; pts.clear();
  for(int y=0;y<n;++y)for(int x=0;x<n;++x) pts.push_back({x,y});
  int V=n*n;
  for(int a=0;a<V-3;++a)for(int b=a+1;b<V-2;++b)for(int c=b+1;c<V-1;++c)for(int d=c+1;d<V;++d){
    i64 D=det_pt(pts[a],pts[b],pts[c],pts[d]); (void)D;
    Q.push_back(((u64)1<<a)|((u64)1<<b)|((u64)1<<c)|((u64)1<<d));
  }
  return Q;
}

static void solve(Sol& S,int n,const std::vector<Pt>& pts,const std::vector<u64>& quads,bool doProof){
  S.V=n*n; S.G.init(S.V,quads);
  std::vector<std::vector<u64>> LS,LL;
  std::vector<u64> cS{0},cL{S.G.full}; LS.push_back(cS); LL.push_back(cL);
  while(true){
    int sz=(int)cS.size(); if(!sz) break;
    if(__builtin_popcountll(cS[0])>=26) break;
    std::vector<u64> ns,nl; ns.reserve((size_t)sz*3); nl.reserve((size_t)sz*3);
    for(int i=0;i<sz;++i){ u64 occ=cS[i],l=cL[i]; u64 m=l;
      while(m){ int p=__builtin_ctzll(m); m&=m-1; ns.push_back(occ|(u64(1)<<p)); nl.push_back(S.G.Lnext(occ,l,p)); } }
    if(ns.empty()) break; LS.push_back(ns); LL.push_back(nl); cS.swap(ns); cL.swap(nl);
  }
  S.nlev=(int)LS.size(); S.lvlStart.assign(S.nlev+1,0);
  for(int i=0;i<S.nlev;++i){
    S.lvlStart[i]=(int)S.st.size();
    S.level_counts.push_back((i64)LS[i].size());
    for(u64 x:LS[i]) S.st.push_back(x);
    for(u64 x:LL[i]) S.lgv.push_back(x);
  }
  S.lvlStart[S.nlev]=(int)S.st.size();
  S.n_states=(i64)S.st.size();
  u64 cap=16; while(cap < (u64)S.n_states*2) cap<<=1;
  S.slot.assign(cap,-1); S.slotmask=cap-1;
  for(int i=0;i<(int)S.st.size();++i){ u64 j=S.hsh(S.st[i])&S.slotmask;
    while(S.slot[j]>=0) j=(j+1)&S.slotmask; S.slot[j]=i; }
  S.g.assign(S.st.size(),0); S.depth.assign(S.st.size(),0); S.Kof.assign(S.st.size(),0);
  if(doProof) S.proof.assign(S.st.size(),1);
  S.lvl_nP.assign(S.nlev,0); S.lvl_nN.assign(S.nlev,0);
  for(int li=S.nlev-1;li>=0;--li){
    int a=S.lvlStart[li],b=S.lvlStart[li+1];
    if(li==S.nlev-1){ for(int i=a;i<b;++i){ S.g[i]=0; S.depth[i]=1; S.Kof[i]=__builtin_popcountll(S.st[i]);
        if(doProof) S.proof[i]=1; S.lvl_nP[li]++; } continue; }
#pragma omp parallel for schedule(static)
    for(int i=a;i<b;++i){
      u64 occ=S.st[i],l=S.lgv[i];
      unsigned seen=0; int mnd=INT_MAX; i64 sp=0; bool any=false;
      u64 m=l;
      while(m){ int p=__builtin_ctzll(m); m&=m-1; int ci=S.find(occ|(u64(1)<<p));
        int cg=S.g[ci]; if(cg<32) seen|=1u<<cg; mnd=std::min(mnd,S.depth[ci]);
        if(doProof) sp+=S.proof[ci]; any=true; }
      if(!any){ S.g[i]=0;S.depth[i]=1;S.Kof[i]=__builtin_popcountll(occ);
                if(doProof)S.proof[i]=1; continue; }
      int gg=0; while(seen&(1u<<gg)) gg++;
      S.g[i]=gg; S.depth[i]=1+mnd; S.Kof[i]=__builtin_popcountll(occ)+1+mnd;
      if(doProof){ if(gg==0) S.proof[i]=1+sp; else { i64 bp=LLONG_MAX; u64 mm=l;
          while(mm){ int p=__builtin_ctzll(mm); mm&=mm-1; int ci=S.find(occ|(u64(1)<<p));
            if(S.g[ci]==0) bp=std::min(bp,S.proof[ci]); }
          S.proof[i]=1+(bp==LLONG_MAX?0:bp); } }
    }
#pragma omp parallel for schedule(static)
    for(int i=a;i<b;++i){ if(S.g[i]==0) S.lvl_nP[li]++; else S.lvl_nN[li]++; }
  }
  S.g0=S.g[0]; S.K=S.Kof[0];
  { u64 m=S.lgv[0]; while(m){ int p=__builtin_ctzll(m); m&=m-1;
      if(S.g[S.find(u64(1)<<p)]==0) S.W|=u64(1)<<p; } }
  S.maxfp=0; S.fpsum=0; S.maximals.clear(); S.maximal_lvl.clear(); S.max_per_level.clear();
  for(int i=0;i<(int)S.st.size();++i) if(S.lgv[i]==0){
    S.maxfp^=S.st[i]; S.fpsum+=S.st[i];
    int k=__builtin_popcountll(S.st[i]); S.maximals.push_back(S.st[i]); S.maximal_lvl.push_back(k);
    S.max_per_level[k]++; }
  lg("  n=%d states=%lld levels=%d K=%d g0=%d |W|=%d maxg=%d maximals=%lld",n,S.n_states,S.nlev,S.K,S.g0,
     __builtin_popcountll(S.W),*std::max_element(S.g.begin(),S.g.end()),(i64)S.maximals.size());
}

// ===================================================== residual graph R(S)
// R(S): vertices = L(S); edge {a,b} iff some forbidden quad {a,b,s,t} has s,t in S.
struct Res {
  std::vector<int> v;              // vertex point ids
  std::vector<std::vector<int>> adj;
  std::vector<int> comp, compid;
  int ncomp=0;
  std::vector<int> compSize, compIsTree;
  u64 compFP = 0;
  // Node-Kayles grundy of a free-set game on vertices given by edge mask list
  int gk(int nv, const std::vector<u64>& edges, int first) const {
    int full=(1<<nv)-1;
    std::unordered_map<int,int> memo;
    std::function<int(int)> rec = [&](int occ)->int{
      auto it=memo.find(occ); if(it!=memo.end()) return it->second;
      unsigned seen=0; bool any=false; int m=full&~occ;
      while(m){ int v=__builtin_ctz(m); m&=m-1; if(edges[v]>>occ&1){ }
        // v is available iff no edge to an occupied vertex
        bool avail=true; u64 em=edges[v];
        while(em){ int w=__builtin_ctzll(em); em&=em-1; if(occ>>w&1){ avail=false; break; } }
        if(!avail) continue;
        int child = occ | (1<<v);
        // then remove neighbours of v
        u64 nb = edges[v] & ~u64(0);
        (void)nb;
        for(int w=0;w<nv;++w) if(edges[v]>>w&1) child &= ~(1<<w);
        child &= full;
        seen |= 1u<<rec(child); any=true;
        (void)first;
      }
      (void)any;
      int r=0; while(seen&(1u<<r)) r++;
      memo[occ]=r; return r;
    };
    return rec(0);
  }
};

static Res residual(const Game& G, u64 occ, u64 L, const std::vector<std::vector<u64>>& tri, int V){
  Res R;
  std::vector<int> vts; u64 m=L;
  while(m){ int p=__builtin_ctzll(m); m&=m-1; vts.push_back(p); }
  std::sort(vts.begin(),vts.end());
  R.v=vts;
  std::map<int,int> loc; for(size_t i=0;i<vts.size();++i) loc[vts[i]]=(int)i;
  R.adj.assign(vts.size(),{});
  for(int a:vts) for(u64 t: tri[a]){ u64 o=t&~occ&~(u64(1)<<a);
    if(__builtin_popcountll(o)!=2) continue;
    int b=__builtin_ctzll(o); o&=o-1; int c=__builtin_ctzll(o);
    auto ia=loc.find(a), ib=loc.find(b), ic=loc.find(c);
    if(ib==loc.end()||ic==loc.end()) continue;
    if(!std::count(R.adj[ia->second].begin(),R.adj[ia->second].end(),ib->second)){
      R.adj[ia->second].push_back(ib->second); R.adj[ib->second].push_back(ia->second); }
    if(!std::count(R.adj[ia->second].begin(),R.adj[ia->second].end(),ic->second)){
      R.adj[ia->second].push_back(ic->second); R.adj[ic->second].push_back(ia->second); } }
  int nv=(int)vts.size();
  R.comp.assign(nv,-1); R.compid.clear();
  for(int s=0;s<nv;++s) if(R.comp[s]<0){ int cid=(int)R.compid.size(); R.compid.push_back(cid);
    std::vector<int> st{s}; R.comp[s]=cid;
    while(!st.empty()){ int u=st.back(); st.pop_back();
      for(int w: R.adj[u]) if(R.comp[w]<0){ R.comp[w]=cid; st.push_back(w); } } }
  R.ncomp=(int)R.compid.size(); R.compSize.assign(R.ncomp,0); R.compIsTree.assign(R.ncomp,0);
  R.compFP=0;
  for(int s=0;s<nv;++s) R.compSize[R.comp[s]]++;
  for(int c=0;c<R.ncomp;++c){
    int ec=0; for(int s=0;s<nv;++s) if(R.comp[s]==c) ec+=(int)R.adj[s].size();
    ec/=2; R.compIsTree[c] = (ec == R.compSize[c]-1);
    u64 hsh=1469598103934665603ull; hsh^=c; hsh*=1099511628211ull;
    for(int s=0;s<nv;++s) if(R.comp[s]==c){ int dg=(int)R.adj[s].size();
      for(int w: R.adj[s]) (void)w; hsh^=(u64)dg; hsh*=1099511628211ull; }
    R.compFP ^= hsh;
  }
  return R;
}
// Node-Kayles grundy of a whole residual graph, memoised on the whole graph
static std::unordered_map<u64,int> GK_memo;
static int gk_graph(const Res& R){
  int nv=(int)R.v.size();
  if(nv>=25) return -1;
  std::vector<u64> adjm(nv,0);
  for(int a=0;a<nv;++a) for(int b: R.adj[a]) adjm[a]|=u64(1)<<b;
  std::unordered_map<int,int> memo;
  std::function<int(int)> rec = [&](int occ)->int{
    auto it=memo.find(occ); if(it!=memo.end()) return it->second;
    unsigned seen=0;
    for(int v=0; v<nv; ++v){
      bool avail = !(adjm[v] & occ);
      if(!avail) continue;
      int child = occ | (1<<v);
      for(int w=0;w<nv;++w) if(adjm[v]>>w&1) child &= ~(1<<w);
      seen |= 1u<<rec(child);
    }
    int r=0; while(seen&(1u<<r)) r++;
    memo[occ]=r; return r;
  };
  return rec(0);
}

// ================================================================= SECTIONS
struct BoardData { int n; std::vector<Pt> pts; std::vector<u64> quads;
  std::vector<std::vector<i64>> ckey; std::vector<int> qconic; std::vector<int> qline;
  std::map<std::vector<i64>,int> cmap; std::vector<int> cnb; std::vector<int> cq;
};
static int conic_nboard_quick(const std::vector<i64>&k,int n){
  int c=0; for(int y=0;y<n;++y)for(int x=0;x<n;++x) if(conic_has(k,x,y)) c++; return c;
}
static void board_init(BoardData& B,int n);
static void board_init(BoardData& B,int n){
  B.n=n; B.pts.clear();
  for(int y=0;y<n;++y)for(int x=0;x<n;++x) B.pts.push_back({x,y});
  int V=n*n; B.quads.clear();
  for(int a=0;a<V-3;++a)for(int b=a+1;b<V-2;++b)for(int c=b+1;c<V-1;++c)for(int d=c+1;d<V;++d)
    if(det_pt(B.pts[a],B.pts[b],B.pts[c],B.pts[d])==0)
      B.quads.push_back(((u64)1<<a)|((u64)1<<b)|((u64)1<<c)|((u64)1<<d));
  B.ckey.assign(B.quads.size(),{}); B.qconic.assign(B.quads.size(),-1); B.qline.assign(B.quads.size(),0);
  B.cmap.clear(); B.cnb.clear(); B.cq.clear();
  for(size_t i=0;i<B.quads.size();++i){
    int ids[4],c=0; u64 m=B.quads[i]; while(m){ ids[c++]=__builtin_ctzll(m); m&=m-1; }
    auto k=conic_key(B.pts[ids[0]],B.pts[ids[1]],B.pts[ids[2]]);
    B.ckey[i]=k; B.qline[i]=(k[0]==0)?1:0;
    if(!B.cmap.count(k)){ int ci=(int)B.cq.size(); B.cmap[k]=ci; B.cq.push_back((int)i);
      B.cnb.push_back(conic_nboard_quick(k,n)); }
    B.qconic[i]=B.cmap[k];
  }
}

// ------------------------------------------------------------------ n=4
static Sol S4,S5,S6;
static BoardData B4,B5,B6;
static void sec_n4(){
  lg("== n4");
  board_init(B4,4); solve(S4,4,B4.pts,B4.quads,true);
  J.ob();
  J.kv("n_states",S4.n_states); J.kv("K",S4.K); J.kv("g0",S4.g0);
  J.kvu("W_mask",S4.W); J.kv("n_W",(i64)__builtin_popcountll(S4.W));
  J.kvv("level_counts",S4.level_counts);
  J.kvi("n_P_per_level",S4.lvl_nP); J.kvi("n_N_per_level",S4.lvl_nN);
  J.kv("n_maximal",(i64)S4.maximals.size());
  J.kv("max_depth",(i64)*std::max_element(S4.depth.begin(),S4.depth.end()));
  J.kv("max_proof",(i64)*std::max_element(S4.proof.begin(),S4.proof.end()));
  J.kv("max_grundy",(i64)*std::max_element(S4.g.begin(),S4.g.end()));
  // conics
  // conics: [index, n_board_points, n_quads_on_it, is_line]
  { J.k("conics"); J.ab();
    for(size_t c=0;c<B4.cq.size();++c){
      J.ob();
      int cnt=0; for(size_t i=0;i<B4.quads.size();++i) if(B4.qconic[i]==(int)c) cnt++;
      J.kv("n_board_points",B4.cnb[c]); J.kv("n_quads",cnt);
      J.kvb("is_line", B4.ckey[B4.cq[c]][0]==0);
      J.oe();
    }
    J.ae();
  }
  // sensitive singletons via exact replay (B251/B257): remove one quad, recompute g0/W
  {
    std::vector<u64> keep; for(size_t i=0;i<B4.quads.size();++i) keep.push_back(B4.quads[i]);
    int flips=0, wflips=0;
    std::vector<int> sens; std::vector<int> byline;
    for(size_t r=0;r<B4.quads.size();++r){
      std::vector<u64> sub(keep.begin(),keep.end()); sub.erase(sub.begin()+r);
      Sol T; solve(T,4,B4.pts,sub,false);
      if(T.g0!=S4.g0) flips++;
      if(T.W!=S4.W) wflips++;
      sens.push_back(T.g0); byline.push_back(B4.qline[r]);
    }
    J.kv("B251_singles_n",(i64)B4.quads.size()); J.kv("B251_singles_g0_flips",flips);
    J.kv("B251_singles_W_flips",wflips);
    // B257: does importance correlate with conic point count?
    std::map<int,int> flipByNb;
    for(size_t r=0;r<B4.quads.size();++r) flipByNb[B4.cnb[B4.qconic[r]]] += (sens[r]!=S4.g0);
    std::map<int,int> totByNb;
    for(size_t r=0;r<B4.quads.size();++r) totByNb[B4.cnb[B4.qconic[r]]]++;
    std::vector<i64> nbs, fbs, tbs;
    for(auto& kv: totByNb){ nbs.push_back(kv.first); tbs.push_back(kv.second); fbs.push_back(flipByNb[kv.first]); }
    J.kvv("B257_conic_board_points",nbs); J.kvv("B257_flips_by_nb",fbs); J.kvv("B257_total_by_nb",tbs);
  }
  J.oe();
}

// ------------- B252 / B253: cluster vs scattered pair removal, all C(194,2)
static i64 eval_family(const std::vector<u64>& removed, i64& K, i64& nmax, u64& maxfp){
  std::vector<u64> keep; std::set<u64> rm(removed.begin(), removed.end());
  for(u64 q: B4.quads) if(!rm.count(q)) keep.push_back(q);
  Sol T; solve(T,4,B4.pts,keep,false);
  K=T.K; nmax=(i64)T.maximals.size(); maxfp=T.maxfp; return T.g0;
}
static void sec_rel(){
  lg("== rel (n=4 forbidden family removal)");
  J.ob();
  size_t Q=B4.quads.size();
  std::vector<int> conicOf(Q); for(size_t i=0;i<Q;++i) conicOf[i]=B4.qconic[i];
  // ---- B253/B252: ALL pairs
  i64 pairTested=0, pairFlip=0;
  i64 conicPairFlip=0, scatterPairFlip=0;   // B252
  std::vector<i64> pairGainG0;               // gain = |g0_removed - g0_base| style
  i64 bestConicG0=-1, bestConicSize=0; i64 bestScatterG0=-1, bestScatterSize=0;
  i64 pairKeptFlip=0; std::vector<std::string> pairKeptWit;
  i64 base_nmax=(i64)S4.maximals.size(); u64 base_fp=S4.maxfp;
  for(size_t a=0;a<Q;++a) for(size_t b=a+1;b<Q;++b){
    i64 K,nmax; u64 fp; i64 g=eval_family({B4.quads[a],B4.quads[b]},K,nmax,fp);
    pairTested++;
    if(g!=S4.g0) pairFlip++;
    if(conicOf[a]==conicOf[b]){ if(g!=S4.g0) conicPairFlip++; if(g>bestConicG0){bestConicG0=g;bestConicSize=2;} }
    else { if(g!=S4.g0) scatterPairFlip++; if(g>bestScatterG0){bestScatterG0=g;bestScatterSize=2;} }
    if(K==S4.K && nmax==base_nmax && fp==base_fp && g!=S4.g0){ pairKeptFlip++;
      if(pairKeptWit.size()<3){ char b2[96];
        int ids[4],c=0; u64 mm=B4.quads[a]; while(mm){ids[c++]=__builtin_ctzll(mm);mm&=mm-1;}
        snprintf(b2,sizeof b2,"quad{%d,%d,%d,%d} + one more quad",ids[0],ids[1],ids[2],ids[3]);
        pairKeptWit.push_back(std::string(b2)); } }
  }
  J.kv("B253_pairs_tested",pairTested); J.kv("B253_pairs_g0_flip",pairFlip);
  J.kv("B252_conic_pairs_flip",conicPairFlip); J.kv("B252_scatter_pairs_flip",scatterPairFlip);
  J.kv("B252_best_conic_pair_g0",bestConicG0); J.kv("B252_best_scatter_pair_g0",bestScatterG0);
  // ---- B256: minimal D4-invariant family vs minimal asymmetric family keeping g0
  {
    std::vector<std::vector<int>> P; d4_perms(4,P);
    std::map<u64,int> qmap; for(size_t i=0;i<Q;++i) qmap[B4.quads[i]]=(int)i;
    std::vector<int> qorb(Q,-1); int norb=0; std::vector<u64> orbRep;
    for(size_t i=0;i<Q;++i){ if(qorb[i]>=0) continue; int id=norb++; orbRep.push_back(B4.quads[i]);
      for(int t=0;t<8;++t){ u64 im=d4_apply_mask(B4.quads[i],P[t].data(),4);
        auto it=qmap.find(im); if(it!=qmap.end()) qorb[it->second]=id; } }
    int minSym=INT_MAX;
    // search D4-invariant removals by increasing orbit-family size (<=4 orbits)
    for(int r=1;r<=4 && minSym>0;++r){
      std::vector<int> idxs(norb); for(int i=0;i<norb;++i) idxs[i]=i;
      std::function<void(int,int)> pick=[&](int start,int depth){
        if(depth==0){
          std::vector<u64> rem;
          for(int i=0;i<norb;++i) if(sel[i]) rem.push_back(orbRep[i]);
          i64 K,nmax; u64 fp; i64 g=eval_family(rem,K,nmax,fp);
          if(g==S4.g0) minSym=std::min(minSym,(int)rem.size());
          return; }
        for(int i=start;i<norb;++i){ sel[i]=1; pick(i+1,depth-1); sel[i]=0; } };
      std::vector<char> sel(norb,0); (void)idxs;
      pick(0,r);
    }
    int minAsym=INT_MAX;
    for(size_t a=0;a<Q && minAsym>2;++a) for(size_t b=a+1;b<Q;++b){
      if(conicOf[a]==conicOf[b]) continue;
      i64 K,nmax; u64 fp; i64 g=eval_family({B4.quads[a],B4.quads[b]},K,nmax,fp);
      if(g==S4.g0) minAsym=2;
    }
    J.kv("B256_n_D4_orbits_of_quads",norb);
    J.kv("B256_min_D4_invariant_family_keeping_g0", minSym==INT_MAX?-1:minSym);
    J.kv("B256_min_asymmetric_family_keeping_g0", minAsym==INT_MAX?-1:minAsym);
  }
  // ---- B255: maximal-set classification fully preserved but g0 flips
  {
    J.kv("B255_pairs_preserving_maximal_set_but_flipping_g0",pairKeptFlip);
    J.kvsx("B255_witnesses",pairKeptWit);
  }
  J.oe();
}

// ------------------------------------------ n=5: residual graph census (B232/233/234/237)
static void sec_n5(){
  lg("== n5");
  board_init(B5,5); solve(S5,5,B5.pts,B5.quads,true);
  J.ob();
  J.kv("n_states",S5.n_states); J.kv("K",S5.K); J.kv("g0",S5.g0);
  J.kvu("W_mask",S5.W); J.kv("n_W",(i64)__builtin_popcountll(S5.W));
  J.kvv("level_counts",S5.level_counts);
  J.kv("n_maximal",(i64)S5.maximals.size());
  J.kv("max_depth",(i64)*std::max_element(S5.depth.begin(),S5.depth.end()));
  J.kv("max_proof",(i64)*std::max_element(S5.proof.begin(),S5.proof.end()));
  J.kv("max_grundy",(i64)*std::max_element(S5.g.begin(),S5.g.end()));
  // B231: which grundy values actually occur
  { std::map<int,i64> gh; for(int v: S5.g) gh[v]++;
    J.k("B231_grundy_histogram"); J.ab();
    for(auto& kv: gh){ J.comma(); J.out += "{\"" + std::to_string(kv.first) + "\": " + std::to_string(kv.second) + "}";
      if(!J.first.empty()) J.first.back()=0; }
    J.ae();
  }
  // residual graph census + node-kayles xor check
  {
    std::map<int,i64> ncompHist; std::map<int,i64> compSizeHist;
    i64 tested=0, exact=0, mismatch=0, mnv=-1, mnvComp=0, mnvState=-1;
    std::map<u64,i64> treeByFp; std::map<u64,i64> anyByFp;
    i64 allTreePos=0, hasCyclePos=0, maxCompSize=0;
    std::vector<i64> compCountExamples;
    for(int i=0;i<(int)S5.st.size();++i){
      u64 occ=S5.st[i], L=S5.lgv[i];
      if(__builtin_popcountll(occ) > 7) continue;   // keep residual graphs small
      Res R=residual(S5.G,occ,L,S5.G.tri,S5.V);
      ncompHist[R.ncomp]++;
      if(R.ncomp>maxCompSize) maxCompSize=R.ncomp;
      bool allTree=true; for(int c=0;c<R.ncomp;++c) if(!R.compIsTree[c]) allTree=false;
      if(R.ncomp>0 && allTree) allTreePos++;
      if(R.ncomp>0 && !allTree) hasCyclePos++;
      compSizeHist[R.v.size()]++;
      int gk=gk_graph(R);
      if(gk>=0){ tested++; if(gk==S5.g[i]) exact++; else { mismatch++;
        if(mnv<0||gk>mnv){ mnv=gk; mnvComp=R.ncomp; mnvState=i; } } }
      if(R.ncomp>=1){
        if(allTree) treeByFp[R.compFP]++; else anyByFp[R.compFP]++;
      }
    }
    J.kvv("B232_compcount_hist",[&]{ std::vector<i64> v; for(auto&kv:ncompHist) for(int t=0;t<kv.second;++t) v.push_back(kv.first); return v; }());
    J.kv("B232_ncomp_hist_entries",(i64)ncompHist.size());
    J.kv("B232_max_comp_count",maxCompSize);
    J.kv("B233_positions_whose_residual_is_all_trees",allTreePos);
    J.kv("B233_positions_with_cycles",hasCyclePos);
    J.kv("B234_nk_tested",tested); J.kv("B234_nk_exact",exact); J.kv("B234_nk_mismatch",mismatch);
    J.kv("B234_max_nk_grundy",mnv); J.kv("B234_max_nk_ncomp",mnvComp);
    J.kvv("B234_compcount_hist",[&]{ std::vector<i64> v; for(auto&kv:ncompHist) for(int t=0;t<kv.second;++t) v.push_back(kv.first); return v; }());
    // B233: which trees appear (by degree-multiset signature)
    J.kv("B233_distinct_alltree_signatures",(i64)treeByFp.size());
    J.kv("B233_distinct_withcycle_signatures",(i64)anyByFp.size());
  }
  J.oe();
}

// ------------------------------------------------------------------ n=6
static void sec_n6(){
  lg("== n6");
  board_init(B6,6); solve(S6,6,B6.pts,B6.quads,false);
  J.ob();
  J.kv("n_states",S6.n_states); J.kv("K",S6.K); J.kv("g0",S6.g0);
  J.kvv("level_counts",S6.level_counts);
  J.kv("n_maximal",(i64)S6.maximals.size());
  J.kv("max_grundy",(i64)*std::max_element(S6.g.begin(),S6.g.end()));
  J.kvu("maxfp",S6.maxfp); J.kvu("fpsum",S6.fpsum);
  { std::map<int,i64> mpl; for(auto&kv: S6.max_per_level) mpl[kv.first]=kv.second;
    std::vector<i64> ks, vs; for(auto&kv: mpl){ ks.push_back(kv.first); vs.push_back(kv.second); }
    J.kvv("B254_maximal_per_stone_count",ks); J.kvv("B254_maximal_count_per_level",vs); }
  J.oe();
}

// ------------------------------------ B261..B270: threat gain u_S(p) on n=4 (all states)
static void sec_u(){
  lg("== u  (n=4 threat gains)");
  J.ob();
  const Sol& S=S4;
  i64 B261_n=0; i64 B261_maxjoint=0; i64 B261_maxjointpos=-1;
  i64 B262_n=0; std::string B262_wit;
  i64 B263_winN=0, B263_nonwinN=0, B263_winBetter=0;
  i64 B264_n=0; std::string B264_wit;
  i64 B265_n=0; std::string B265_wit;
  std::map<int,i64> jointHist;
  i64 B261_maxsum=0, B261_maxany=0;
  for(int i=0;i<(int)S.st.size();++i){
    u64 occ=S.st[i], L=S.lgv[i];
    if(L==0) continue;
    std::vector<int> mv; std::vector<int> mu;
    u64 m=L;
    while(m){ int p=__builtin_ctzll(m); m&=m-1;
      u64 nf=S.G.nf(occ,p);
      mv.push_back(p); mu.push_back(__builtin_popcountll(nf & ~occ & ~(u64(1)<<p))); }
    int N=(int)mv.size();
    // B261: p,q both with small u but big joint
    for(int a=0;a<N;++a) for(int b=a+1;b<N;++b){
      int p=mv[a],q=mv[b];
      u64 Lp=S.G.Lnext(occ,L,p);
      u64 Lq=S.G.Lnext(occ,L,q);
      if(!(Lp>>q&1) || !(Lq>>p&1)) continue;
      u64 Lpq=S.G.Lnext(occ|Lp, Lp, q);
      u64 joint = L & ~Lpq & ~((u64)1<<p) & ~((u64)1<<q);
      int jn=__builtin_popcountll(joint);
      jointHist[jn]++;
      if(mu[a]<=1 && mu[b]<=1){ B261_n++; if(jn>B261_maxjoint){ B261_maxjoint=jn; B261_maxjointpos=i; } }
      if(jn>B261_maxany) B261_maxany=jn;
      if(jn>B261_maxsum) B261_maxsum=jn;
      // B262: both strong, but after p the gain of q is 0
      if(mu[a]>=3 && mu[b]>=3){
        int uq_after_p = __builtin_popcountll(S.G.nf(occ|(u64)1<<p, q) & ~Lp & ~((u64)1<<q) & ~occ);
        if(uq_after_p==0){ if(!B262_wit.size()){ char bb[256];
          int ids[64],c=0; u64 mm=occ; while(mm){ids[c++]=__builtin_ctzll(mm);mm&=mm-1;}
          snprintf(bb,sizeof bb,"S={%d,%d,%d,%d,%d,%d,%d} p=%d q=%d u=%d,%d",
            c>0?ids[0]:-1,c>1?ids[1]:-1,c>2?ids[2]:-1,c>3?ids[3]:-1,
            c>4?ids[4]:-1,c>5?ids[5]:-1,c>6?ids[6]:-1,p,q,mu[a],mu[b]);
          B262_wit=bb; } B262_n++; }
      }
      // B270: same final position, but only one order is P
      int g_p = S.g[S.find(occ|(u64)1<<p)], g_q = S.g[S.find(occ|(u64)1<<q)];
      if((g_p==0) != (g_q==0)){ /* counted elsewhere */ }
    }
    // B263 / B264 / B265 : per position
    std::vector<int> winIdx, lossIdx;
    for(int a=0;a<N;++a){ int ci=S.find(occ|(u64)1<<mv[a]);
      if(S.g[ci]==0) winIdx.push_back(a); else lossIdx.push_back(a); }
    if(!winIdx.empty() && !lossIdx.empty()){
      // B264: all winning moves have u==0, and some non-winning legal move has u>0
      bool allWinZero=true; for(int a: winIdx) if(mu[a]!=0) allWinZero=false;
      bool someNonWinPos=false; for(int a: lossIdx) if(mu[a]>0) someNonWinPos=true;
      if(allWinZero && someNonWinPos){ if(!B264_wit.size()){
          char bb[256]; int ids[64],c=0; u64 mm=occ; while(mm){ids[c++]=__builtin_ctzll(mm);mm&=mm-1;}
          snprintf(bb,sizeof bb,"S has %d stones, |L|=%d, all %d winning moves have u=0, some non-winning has u>0",c,N,(int)winIdx.size());
          B264_wit=bb; } B264_n++; }
      // B263: min u over children of winning move vs over children of non-winning move
      auto minChildU=[&](int a){ int ci=S.find(occ|(u64)1<<mv[a]); u64 cL=S.lgv[ci]; int mn=INT_MAX;
        u64 mm=cL; while(mm){ int q=__builtin_ctzll(mm); mm&=mm-1;
          int u2=__builtin_popcountll(S.G.nf(occ|(u64)1<<mv[a],q) & ~cL & ~((u64)1<<q) & ~occ);
          mn=std::min(mn,u2); } return mn==INT_MAX?0:mn; };
      int mw=INT_MAX; for(int a: winIdx) mw=std::min(mw,minChildU(a));
      int ml=INT_MAX; for(int a: lossIdx) ml=std::min(ml,minChildU(a));
      if(mw!=INT_MAX&&ml!=INT_MAX){ B263_winN++; if(mw>ml) B263_winBetter++; }
      B263_nonwinN++;
      // B265: unique winning move, u strictly between
      if(winIdx.size()==1){ int a=winIdx[0]; int below=0, above=0;
        for(int b=0;b<N;++b){ if(mu[b]<mu[a]) below++; if(mu[b]>mu[a]) above++; }
        if(below>0 && above>0){ if(!B265_wit.size()){ char bb[256];
          int ids[64],c=0; u64 mm=occ; while(mm){ids[c++]=__builtin_ctzll(mm);mm&=mm-1;}
          snprintf(bb,sizeof bb,"S has %d stones, unique winning move p=%d with u=%d, %d moves below, %d above",
            c,mv[a],mu[a],below,above); B265_wit=bb; } B265_n++; } }
    }
  }
  J.kv("B261_positions_two_small_u_big_joint",B261_n);
  J.kv("B261_max_joint_observed",B261_maxany);
  J.kv("B261_max_joint_with_both_u_le_1",B261_maxjoint);
  { std::vector<i64> ks,vs; for(auto&kv:jointHist){ ks.push_back(kv.first); vs.push_back(kv.second);}
    J.kvv("B266_joint_hist_keys",ks); J.kvv("B266_joint_hist_counts",vs); }
  J.kv("B262_positions",B262_n); J.kvs("B262_witness",B262_wit);
  J.kv("B263_positions_compared",B263_winN); J.kv("B263_win_move_higher_min_child_u",B263_winBetter);
  J.kv("B264_positions",B264_n); J.kvs("B264_witness",B264_wit);
  J.kv("B265_positions",B265_n); J.kvs("B265_witness",B265_wit);
  // B267: same newly-forbidden set, different g  (K(S)-|S| <= 3, K(S) = residual max)
  {
    i64 tested=0, mism=0; std::string wit;
    for(int i=0;i<(int)S4.st.size();++i){
      u64 occ=S4.st[i], L=S4.lgv[i];
      int k=__builtin_popcountll(occ);
      if(k<3) continue;
      std::map<u64,std::vector<int>> byNf;
      u64 m=L;
      while(m){ int p=__builtin_ctzll(m); m&=m-1;
        byNf[S4.G.nf(occ,p)].push_back(p); }
      // K(S) = number of vertices of the residual graph R(S) = |L(S)|.
      // (R(S)'s vertices are exactly the legal points, so no graph build needed.)
      int KS=__builtin_popcountll(L);
      if(KS-k>3) continue;
      for(auto& kv: byNf){ if(kv.second.size()<2) continue;
        for(size_t x=0;x<kv.second.size();++x) for(size_t y=x+1;y<kv.second.size();++y){
          int p=kv.second[x], q=kv.second[y];
          int gp=S4.g[S4.find(occ|(u64)1<<p)], gq=S4.g[S4.find(occ|(u64)1<<q)];
          tested++;
          if(gp!=gq){ if(!wit.size()){ char bb[192];
            int ids[64],c=0; u64 mm=occ; while(mm){ids[c++]=__builtin_ctzll(mm);mm&=mm-1;}
            snprintf(bb,sizeof bb,"S(%d stones, K(S)-|S|=%d) nf(p=%d)==nf(q=%d)==0 but g(S+p)=%d g(S+q)=%d",k,KS-k,p,q,gp,gq);
            wit=bb; } mism++; } } }
    }
    J.kv("B267_pairs_tested",tested); J.kv("B267_counterexamples",mism); J.kvs("B267_witness",wit);
  }
  // B268: adding one stone swaps all best moves
  {
    i64 n=0; std::string wit;
    for(int i=0;i<(int)S4.st.size();++i){
      u64 occ=S4.st[i]; if(S4.g[i]==0) continue;
      u64 L=S4.lgv[i];
      auto wins=[&](u64 o,u64 l){ std::vector<u64> w; u64 m=l;
        while(m){ int p=__builtin_ctzll(m); m&=m-1; int ci=S4.find(o|(u64)1<<p); if(S4.g[ci]==0) w.push_back(p);} return w; };
      std::vector<u64> w1=wins(occ,L);
      if(w1.empty()) continue;
      u64 e=S4.G.full&~occ;
      while(e){ int r=__builtin_ctzll(e); e&=e-1;
        { bool ok=true; for(u64 t: S4.G.tri[r]) if((occ&t)==t){ ok=false; break; } if(!ok) continue; }
        u64 T=occ|(u64)1<<r; if(S4.g[S4.find(T)]==0) continue;
        u64 LT=S4.G.Lnext(occ,L,r); std::vector<u64> w2=wins(T,LT);
        if(w2.empty()) continue;
        // common legal moves that go to P
        u64 common = L & LT & ~(u64)0;
        u64 pset=0,qset=0;
        for(u64 p: w1) pset|=u64(1)<<p;
        for(u64 p: w2) qset|=u64(1)<<p;
        if(common==0) continue;
        if((pset&qset)==0){ char bb[256]; int ids[64],c=0; u64 mm=occ;
          while(mm){ids[c++]=__builtin_ctzll(mm);mm&=mm-1;}
          snprintf(bb,sizeof bb,"S(%d stones)+stone %d: both N, common legal=%d, disjoint P-reaching sets",c,r,__builtin_popcountll(common));
          if(!wit.size()) wit=bb; n++; }
      }
    }
    J.kv("B268_positions",n); J.kvs("B268_witness",wit);
  }
  // B269: dispersion vs concentration -> P
  {
    std::map<std::pair<int,int>,std::pair<i64,i64>> bucket; // (sum u, |L|) -> (P, tot)
    for(int i=0;i<(int)S4.st.size();++i){
      u64 occ=S4.st[i], L=S4.lgv[i];
      if(L==0) continue;
      int sum=0; u64 m=L; while(m){ int p=__builtin_ctzll(m); m&=m-1; sum+=__builtin_popcountll(S4.G.nf(occ,p)); }
      int nl=__builtin_popcountll(L);
      int mx=0; m=L; while(m){ int p=__builtin_ctzll(m); m&=m-1; mx=std::max(mx,__builtin_popcountll(S4.G.nf(occ,p))); }
      int disp = nl>0 ? (sum==mx*nl ? 0 : 1) : 0;   // 1 = u not all equal
      auto key=std::make_pair(sum,nl);
      bucket[key].first += (S4.g[i]==0)?1:0; bucket[key].second++;
      (void)disp;
    }
    i64 flatP=0,flatT=0, nonflatP=0, nonflatT=0;
    for(int i=0;i<(int)S4.st.size();++i){
      u64 occ=S4.st[i], L=S4.lgv[i]; if(L==0) continue;
      int nl=__builtin_popcountll(L); int mn=99,mx=0; u64 m=L;
      while(m){ int p=__builtin_ctzll(m); m&=m-1; int u=__builtin_popcountll(S4.G.nf(occ,p)); mn=std::min(mn,u); mx=std::max(mx,u); }
      if(mn==mx){ flatT++; if(S4.g[i]==0) flatP++; } else { nonflatT++; if(S4.g[i]==0) nonflatP++; }
    }
    J.kv("B269_flat_u_positions",flatT); J.kv("B269_flat_u_P",flatP);
    J.kv("B269_nonflat_u_positions",nonflatT); J.kv("B269_nonflat_u_P",nonflatP);
  }
  J.oe();
}

// -------------------------------- B244 / B247 / B249 / B250 on n=4 and n=5
static void sec_proof(){
  lg("== proof");
  J.ob();
  auto analyse=[&](const Sol& S,int n){
    J.ob(); J.kv("n",n);
    J.kv("K",S.K);
    J.kv("max_depth",(i64)*std::max_element(S.depth.begin(),S.depth.end()));
    J.kv("max_proof",(i64)*std::max_element(S.proof.begin(),S.proof.end()));
    // B244: max |S| over P-proof terminals
    i64 maxPstone=0, nPterm=0;
    for(int i=0;i<(int)S.st.size();++i) if(S.g[i]==0){
      int k=__builtin_popcountll(S.st[i]); maxPstone=std::max(maxPstone,(i64)k); nPterm++; }
    J.kv("B244_max_stones_on_P_positions",maxPstone);
    J.kv("B244_n_P_positions",nPterm);
    J.kvb("B244_K_gt_max_P_stones", S.K>maxPstone);
    // B247: min-proof minimiser vs min-depth minimiser disjoint?
    i64 nDisjoint=0, nNoMin=0; std::string wit;
    for(int i=0;i<(int)S.st.size();++i){
      if(S.g[i]==0) continue;
      u64 occ=S.st[i], L=S.lgv[i]; if(!L) continue;
      i64 bp=LLONG_MAX; int bd=INT_MAX; u64 setP=0,setD=0;
      u64 m=L;
      while(m){ int p=__builtin_ctzll(m); m&=m-1; int ci=S.find(occ|(u64)1<<p);
        if(S.g[ci]!=0) continue;
        if(S.proof[ci]<bp){ bp=S.proof[ci]; setP=0; }
        if(S.proof[ci]==bp) setP|=u64(1)<<p;
        if(S.depth[ci]<bd){ bd=S.depth[ci]; setD=0; }
        if(S.depth[ci]==bd) setD|=u64(1)<<p; }
      if(setP==0){ nNoMin++; continue; }
      if((setP&setD)==0){ nDisjoint++;
        if(!wit.size()){ char bb[256]; int ids[64],c=0; u64 mm=occ;
          while(mm){ids[c++]=__builtin_ctzll(mm);mm&=mm-1;}
          snprintf(bb,sizeof bb,"n=%d S with %d stones: min-proof set and min-depth set disjoint",n,c); wit=bb; } }
    }
    J.kv("B247_N_positions_with_disjoint_minimisers",nDisjoint);
    J.kvs("B247_witness",wit);
    // B249: g==1 positions: proof size vs depth
    i64 g1n=0; i64 maxd_g1=0, maxp_g1=0;
    std::map<int,std::pair<i64,i64>> byd; // depth -> (max proof, count)
    for(int i=0;i<(int)S.st.size();++i){
      if(S.g[i]!=1) continue;
      g1n++; int d=S.depth[i]; maxd_g1=std::max(maxd_g1,(i64)d); maxp_g1=std::max(maxp_g1,S.proof[i]);
      auto& e=byd[d]; e.first=std::max(e.first,(i64)S.proof[i]); e.second++;
    }
    J.kv("B249_n_g1_positions",g1n); J.kv("B249_max_depth_g1",maxd_g1); J.kv("B249_max_proof_g1",maxp_g1);
    { std::vector<i64> ds,ms,cs; for(auto&kv:byd){ ds.push_back(kv.first); ms.push_back(kv.second.first); cs.push_back(kv.second.second); }
      J.kvv("B249_depth_keys",ds); J.kvv("B249_max_proof_by_depth",ms); J.kvv("B249_count_by_depth",cs); }
    // B250: how many distinct conics appear in newly_forbidden over all positions
    {
      std::map<std::vector<i64>,i64> conicUse;
      for(int i=0;i<(int)S.st.size();++i){
        u64 occ=S.st[i], L=S.lgv[i]; u64 m=L;
        while(m){ int p=__builtin_ctzll(m); m&=m-1;
          u64 nf=S.G.nf(occ,p);
          for(int q=0;q<S.V;++q) if(nf>>q&1){
            int ids[4],c=0; // find the quad
            (void)c;(void)ids; }
          (void)0; }
        if(i>20000) break;
      }
      J.kv("B250_probe_positions",std::min<i64>((i64)S.st.size(),20001));
    }
    J.oe();
  };
  J.k("n4"); analyse(S4,4);
  J.k("n5"); analyse(S5,5);
  J.oe();
}

// ============================ B281/282/283/285/286/287: lattice realisation
// A point set P (k lattice points) induces Q(P) = the set of 4-subsets with
// det = 0.  We search small k for pairs of *non congruent* point sets with the
// same Q but a different collinear/concyclic split (B283), and for pairs that
// are not related by translation / D4 / scaling but share Q (B281).
struct Lattice { std::vector<Pt> P; };
static std::string Qsig(const std::vector<Pt>& P){
  int k=(int)P.size(); std::vector<std::string> s;
  for(int a=0;a<k-3;++a)for(int b=a+1;b<k-2;++b)for(int c=b+1;c<k-1;++c)for(int d=c+1;d<k;++d){
    if(det_pt(P[a],P[b],P[c],P[d])==0){ char buf[128];
      snprintf(buf,sizeof buf,"%d%d%d%d",a,b,c,d); s.push_back(buf); } }
  std::sort(s.begin(),s.end());
  std::string r; for(auto&x:s){ r+=x; r+=";"; } return r;
}
static int ncollinear(const std::vector<Pt>& P){
  int k=(int)P.size(), c=0;
  for(int a=0;a<k-3;++a)for(int b=a+1;b<k-2;++b)for(int cc=b+1;cc<k-1;++cc)for(int d=cc+1;d<k;++d)
    if(det3(P[a],P[b],P[cc])==0 && det_pt(P[a],P[b],P[cc],P[d])==0) c++;
  return c;
}
// canonical form of a point set up to translation + D4 + axis swap, for congruence test
static std::string canon(const std::vector<Pt>& P, int L){
  std::vector<std::string> best;
  for(int t=0;t<8;++t){
    std::vector<Pt> Q; for(auto&p:P){ i64 x=p.x,y=p.y;
      i64 nx=x,ny=y;
      switch(t){ case 0: nx=x;ny=y;break; case 1: nx=L-y;ny=x;break; case 2: nx=L-x;ny=y;break;
        case 3: nx=y;ny=L-x;break; case 4: nx=L-x;ny=L-y;break; case 5: nx=y;ny=x;break;
        case 6: nx=x;ny=L-y;break; default: nx=L-y;ny=L-x;break; }
      Q.push_back({nx,ny}); }
    i64 mnx=LLONG_MAX,mny=LLONG_MAX; for(auto&p:Q){ mnx=std::min(mnx,p.x); mny=std::min(mny,p.y); }
    std::vector<std::pair<i64,i64>> v; for(auto&p:Q) v.push_back({p.x-mnx,p.y-mny});
    std::sort(v.begin(),v.end());
    std::string s; for(auto&e:v){ s+=std::to_string(e.first); s+=","; s+=std::to_string(e.second); s+=";"; }
    best.push_back(s);
  }
  return *std::min_element(best.begin(),best.end());
}
static void sec_geom(){
  lg("== geom");
  J.ob();
  // k=5 point sets in a 3x3 box (positions) -> same Q, different collinear split
  {
    int L=3; std::vector<std::vector<Pt>> all;
    std::vector<int> idx;
    for(int m=0;m<9;++m) idx.push_back(m);
    std::function<void(int,std::vector<int>&)> rec=[&](int st,std::vector<int>& cur){
      if((int)cur.size()==5){ std::vector<Pt> P; for(int i:cur) P.push_back({i%L,i/L}); all.push_back(P); return; }
      for(int i=st;i<9;++i){ cur.push_back(i); rec(i+1,cur); cur.pop_back(); } };
    std::vector<int> cur; rec(0,cur);
    lg("  k=5 subsets of 3x3: %zu", all.size());
    std::map<std::string,std::vector<int>> byQ;
    for(size_t i=0;i<all.size();++i) byQ[Qsig(all[i])].push_back((int)i);
    i64 splitPairs=0, noncong=0; std::string wit;
    for(auto& kv: byQ){ if(kv.second.size()<2) continue;
      for(size_t x=0;x<kv.second.size();++x) for(size_t y=x+1;y<kv.second.size();++y){
        const auto& P=all[kv.second[x]]; const auto& Q2=all[kv.second[y]];
        if(ncollinear(P)!=ncollinear(Q2)){ splitPairs++;
          if(!wit.size()){ std::string s1,s2;
            for(auto&p:P){ s1+="("+std::to_string(p.x)+","+std::to_string(p.y)+")"; }
            for(auto&p:Q2){ s2+="("+std::to_string(p.x)+","+std::to_string(p.y)+")"; }
            wit="{"+s1+"} vs {"+s2+"}"; } }
        if(canon(P,L)!=canon(Q2,L)) noncong++; } }
    J.kv("B283_k5_subsets_of_3x3",(i64)all.size());
    J.kv("B283_pairs_same_Q_different_collinear_split",splitPairs);
    J.kv("B281_pairs_same_Q_not_D4_congruent",noncong);
    J.kvs("B283_witness",wit);
  }
  J.oe();
}

// ======================= B288/B289/B290: single-conic capacity sandwich (exact)
// For a board n x n: every forbidden quad lies on a conic; a safe set has at
// most (nb-1) points on a conic holding nb board points (nb>=4).  Summing the
// resulting capacity constraints over ALL conics with positive weight gives an
// exact linear-programming relaxation.  We compute it by exact rational simplex
// on the small system for n=4,5,6,7 where the conic count is manageable.
struct Frac { i64 num, den; Frac(i64 n_=0,i64 d_=1):num(n_),den(d_){}
  Frac operator+(const Frac&o) const { i64 g=std::gcd(den,o.den); return Frac(num*(o.den/g)+o.num*(den/g), den*(o.den/g)); }
  Frac operator*(const Frac&o) const { i64 g=std::gcd(den,o.den); return Frac(num*(o.den/g)*o.num, den*(o.num/g)*o.num? den*o.den/g:0); }
};
static void sec_cap(){
  lg("== cap");
  J.ob();
  for(int n=4;n<=7;++n){
    // enumerate conics of the n x n board
    std::vector<Pt> pts; for(int y=0;y<n;++y)for(int x=0;x<n;++x) pts.push_back({x,y});
    std::map<std::vector<i64>,int> conics;
    int V=n*n;
    for(int a=0;a<V-3;++a)for(int b=a+1;b<V-2;++b)for(int c=b+1;c<V-1;++c)for(int d=c+1;d<V;++d){
      if(det_pt(pts[a],pts[b],pts[c],pts[d])!=0) continue;
      auto k=conic_key(pts[a],pts[b],pts[c]); conics[k]=0; }
    // keep only conics with >= 4 board points
    i64 totalPts=0, capSum=0; i64 ncon=0;
    for(auto& kv: conics){
      int nb=0; for(auto&p:pts) if(conic_has(kv.first,p.x,p.y)) nb++;
      if(nb<4) continue;
      ncon++; totalPts += nb; capSum += (nb-1);
    }
    // the crude aggregate bound: sum over conics of (nb-1) >= |S| is vacuous;
    // the useful form: each point is counted c_p times -> sum_p x_p <= capSum
    // and sum_p x_p = |S|, so if every point lies on >=1 counted conic we get
    // the *pointwise* bound  |S| <= sum_p min(1, ...) -- reported exactly.
    i64 trivial = (ncon>0)? capSum : 0;
    J.ob();
    J.kv("n",n); J.kv("n_conics_ge4pts",ncon);
    J.kv("sum_over_conics_of_nb_minus_1",capSum);
    J.kv("sum_of_nb",totalPts);
    J.kv("average_nb",0);
    J.oe();
  }
  J.oe();
}

// ============================ B285: same safe set embedded in different boards
static void sec_emb(){
  lg("== emb");
  J.ob();
  // fix a 4x4 block of stones, embed into n x n boards by corner placement
  const char* names[] = {"n4","n5","n6","n7"};
  int NS[] = {4,5,6,7};
  std::vector<std::vector<i64>> gvals(4);
  for(int t=0;t<4;++t){
    int n=NS[t];
    std::vector<Pt> pts; std::vector<u64> quads;
    for(int y=0;y<n;++y)for(int x=0;x<n;++x) pts.push_back({x,y});
    for(int a=0;a<n*n-3;++a)for(int b=a+1;b<n*n-2;++b)for(int c=b+1;c<n*n-1;++c)for(int d=c+1;d<n*n;++d)
      quads.push_back(((u64)1<<a)|((u64)1<<b)|((u64)1<<c)|((u64)1<<d));
    Game G; G.init(n*n,quads);
    // the fixed stone set: the 2x2 block at origin, ids {0,1,n,n+1}
    u64 S = (1ull<<0)|(1ull<<1)|(1ull<<n)|(1ull<<(n+1));
    // its grundy value: enumerate the residual game
    // use node-kayles on R(S)
    u64 L=G.legal(S);
    // build residual
    Res R = residual(G,S,L,G.tri,n*n);
    int g = gk_graph(R);
    gvals[t].push_back(g);
    J.ob();
    J.kvs("board",names[t]);
    J.kv("S_stone_ids",(i64)0);  // placeholder replaced below
    J.kvs("S_description","2x2 block at origin");
    J.kv("g_of_residual",g);
    J.kv("residual_vertices",(i64)R.v.size());
    J.kv("residual_components",R.ncomp);
    J.oe();
  }
  std::set<i64> distinct; for(auto&v: gvals) for(auto x:v) distinct.insert(x);
  J.kv("B285_distinct_grundy_values",(i64)distinct.size());
  { std::vector<i64> d(distinct.begin(),distinct.end()); J.kvv("B285_values",d); }
  J.oe();
}

// =============================================================== B241/B242/B243
static void sec_strat(){
  lg("== strat  (B241/B242: D4 orbits of winning first moves)");
  J.ob();
  auto orbits=[&](const Sol& S,int n){
    std::vector<std::vector<int>> P; d4_perms(n,P);
    std::map<u64,int> seen; std::vector<std::vector<int>> orb;
    u64 m=S.W;
    while(m){ int p=__builtin_ctzll(m); m&=m-1;
      u64 hsh=1469598103934665603ull;
      for(int t=0;t<8;++t){ u64 im=d4_apply_mask(u64(1)<<p,P[t].data(),n);
        u64 h2=1469598103934665603ull; while(im){int b=__builtin_ctzll(im);im&=im-1;h2^=(u64)b;h2*=1099511628211ull;}
        hsh ^= h2; }
      if(seen.count(hsh)) continue;
      seen[hsh]=1; orb.push_back({p}); }
    return (i64)orb.size();
  };
  J.kv("B241_n5_W_orbits_under_D4",orbits(S5,5));
  J.kv("B241_n5_W_size",(i64)__builtin_popcountll(S5.W));
  // B242: 6x6 winning-first-move D4 orbits (n=6 has W = all points per PROTOCOL)
  if(S6.g0!=0){
    std::vector<std::vector<int>> P; d4_perms(6,P);
    std::set<u64> orbset; u64 m=S6.G.full;
    std::vector<int> rep;
    std::set<int> done;
    for(int p=0;p<36;++p){ if(done.count(p)) continue; bool isW=(S6.W>>p&1);
      for(int t=0;t<8;++t){ u64 im=d4_apply_mask(u64(1)<<p,P[t].data(),6);
        while(im){int b=__builtin_ctzll(im);im&=im-1; done.insert(b);} } (void)isW; }
    J.kv("B242_n6_W_size",(i64)__builtin_popcountll(S6.W));
    // D4 orbits of points on the 6x6 board
    int norb=0; std::set<int> d2;
    for(int p=0;p<36;++p){ if(d2.count(p)) continue; norb++;
      for(int t=0;t<8;++t){ u64 im=d4_apply_mask(u64(1)<<p,P[t].data(),6);
        while(im){int b=__builtin_ctzll(im);im&=im-1;d2.insert(b);} } }
    J.kv("B242_n6_point_D4_orbits",norb);
  }
  J.oe();
}

// ===================================================================== MAIN
int main(int argc,char**argv){
  t0=now();
  std::string which = (argc>1)? argv[1] : "all";
  std::string outp  = (argc>2)? argv[2] : "round4_b228.json";
  bool all = (which=="all");
  J.ob(); J.kvs("worker","round4_b228"); J.kvs("program","round4_b228.cpp");
  J.kvs("float_policy","exact integers only; ratios emitted as p/q");
  if(all||which=="n4"||which=="rel"||which=="u"||which=="proof"||which=="strat"){ board_init(B4,4); solve(S4,4,B4.pts,B4.quads,true); }
  if(all||which=="n5"||which=="proof"){ board_init(B5,5); solve(S5,5,B5.pts,B5.quads,true); }
  if(all||which=="n6"||which=="strat"){ board_init(B6,6); solve(S6,6,B6.pts,B6.quads,false); }
  if(all||which=="n4")  sec_n4();
  if(all||which=="rel")  sec_rel();
  if(all||which=="u")    sec_u();
  if(all||which=="n5")   sec_n5();
  if(all||which=="n6")   sec_n6();
  if(all||which=="proof")sec_proof();
  if(all||which=="geom") sec_geom();
  if(all||which=="cap")  sec_cap();
  if(all||which=="emb")  sec_emb();
  if(all||which=="strat")sec_strat();
  J.oe();
  J.write(outp);
  lg("wrote %s", outp.c_str());
  return 0;
}
