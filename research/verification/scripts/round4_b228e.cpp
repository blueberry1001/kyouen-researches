// round4_b228e.cpp -- Round4, draft 4 (decisive).  B231-B290, attack by weakening.
//
// For every ID whose verdict was PARTIAL / NOT-CHECKED / INCONCLUSIVE in drafts
// 1-3, WEAKEN the claim to a form decidable by complete enumeration on n<=6
// (plus small exhaustive geometry), then report SUPPORTED / REFUTED on the
// weakened form.  Draft 3's sec_u segfaulted; it is rewritten here.
//
//   sec_core    full enumeration n=2..6, exact Grundy histogram
//   sec_census  B232/B233/B234  R(S) census, all trees, same-nimber components
//   sec_chain   B235/B236/B237/B246  unique-win chain, induced structure
//   sec_switch  B238  switch point
//   sec_ctx     B240  g(S) vs Node-Kayles value of R(S)
//   sec_proof   B245/B247/B248/B249  proof size, disjoint minimisers, P-descriptions
//   sec_u       B261..B270  threat gain u
//   sec_lambda  B271..B277  two-point correlations, level ratios, Var_1
//   sec_geom    B250/B266/B278..B290  fold, quad families, conic dual bound
//   sec_big     B251..B258/B281/B283  quad-family removal, D4 minimality
//
// Integer / exact-rational only.  Build:
//   g++ -O2 -march=native -std=c++20 -fopenmp -o /tmp/r4e round4_b228e.cpp
#include "kc_core.h"
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdarg>
#include <cmath>
#include <algorithm>
#include <vector>
#include <map>
#include <set>
#include <unordered_map>
#include <string>
#include <functional>
#include <ctime>
#include <numeric>
#include <climits>
#include <iterator>

using u64 = kc::u64;
using i64 = long long;
using i128 = __int128_t;

static double t0;
static double now(){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts);
  return (double)ts.tv_sec + 1e-9*(double)ts.tv_nsec; }
static FILE* OUT;
static void P(const char* f, ...){
  va_list ap; va_start(ap,f); vfprintf(OUT,f,ap); va_end(ap);
  va_list aq; va_start(aq,f); vfprintf(stderr,f,aq); va_end(aq); fflush(OUT);
}
static void lg(const char* f, ...){
  va_list ap; va_start(ap,f); fprintf(stderr,"[%6.1fs] ",now()-t0);
  vfprintf(stderr,f,ap); va_end(ap); fflush(stderr);
}
static std::string frac(i64 a, i64 b){
  if(b<0){ a=-a; b=-b; }
  i64 g=std::gcd(a,b); if(g<0) g=-g; if(g==0) g=1;
  return std::to_string(a/g)+"/"+std::to_string(b/g);
}

// ================================================================ geometry
struct Pt { int x, y; };
static inline i64 det3(const Pt&a,const Pt&b,const Pt&c){
  return (i64)(b.x-a.x)*(c.y-a.y) - (i64)(b.y-a.y)*(c.x-a.x); }
static inline i64 det_pt(const Pt&a,const Pt&b,const Pt&c,const Pt&d){
  long long m[4][4] = { {a.x*a.x+a.y*a.y, a.x, a.y, 1},
                        {b.x*b.x+b.y*b.y, b.x, b.y, 1},
                        {c.x*c.x+c.y*c.y, c.x, c.y, 1},
                        {d.x*d.x+d.y*d.y, d.x, d.y, 1} };
  return kc::det4(m); }
// integer conic through 3 non-collinear points: x^2+y^2 + Dx + Ey + F = 0
static bool conic3(const Pt&a,const Pt&b,const Pt&c, i64* D, i64* E, i64* F){
  if (det3(a,b,c)==0) return false;
  i64 m[3][3] = {{a.x,a.y,1},{b.x,b.y,1},{c.x,c.y,1}};
  i64 C[3] = {-(i64)(a.x*a.x+a.y*a.y), -(i64)(b.x*b.x+b.y*b.y), -(i64)(c.x*c.x+c.y*c.y)};
  i64 dt = m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])
         - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
         + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]);
  if(dt==0) return false;
  auto solve=[&](int col){
    i64 r[3][3];
    for(int i=0;i<3;++i){ for(int j=0;j<3;++j) r[i][j]=m[i][j]; r[i][col]=C[i]; }
    return (r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])
          - r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])
          + r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0]))/dt; };
  i64 dd=solve(0), ee=solve(1), ff=solve(2);
  i64 g=std::gcd(std::gcd(std::llabs(dd),std::llabs(ee)),std::llabs(ff)); if(!g) g=1;
  dd/=g; ee/=g; ff/=g;
  if(dd<0||(dd==0&&ee<0)||(dd==0&&ee==0&&ff<0)){ dd=-dd; ee=-ee; ff=-ff; }
  *D=dd; *E=ee; *F=ff; return true;
}
static std::string line_sig(const Pt&a,const Pt&b){
  i64 A=(i64)b.y-a.y, B=(i64)a.x-b.x, C=-(A*a.x+B*a.y);
  i64 g=std::gcd(std::gcd(std::llabs(A),std::llabs(B)),std::llabs(C)); if(!g) g=1;
  A/=g; B/=g; C/=g;
  if(A<0||(A==0&&B<0)){ A=-A; B=-B; C=-C; }
  return "L"+std::to_string(A)+","+std::to_string(B)+","+std::to_string(C);
}
// signature of the conic (circle or line) through a forbidden quad
static std::string quad_conic(const Pt*P,int* ids){
  i64 D,E,F;
  if(conic3(P[ids[0]],P[ids[1]],P[ids[2]],&D,&E,&F))
    return "C"+std::to_string(D)+","+std::to_string(E)+","+std::to_string(F);
  return line_sig(P[ids[0]],P[ids[1]]);
}
static void mask_ids(u64 q,int* ids){ int c=0; while(q){ ids[c++]=__builtin_ctzll(q); q&=q-1; } }
static std::string occ_str(u64 occ,int n){
  std::string s="{"; bool f=true; while(occ){ int p=__builtin_ctzll(occ); occ&=occ-1;
    if(!f) s+=","; f=false; s+="("+std::to_string(p/n)+","+std::to_string(p%n)+")"; } return s+"}"; }

// D4 maps on an n x n square
static void d4_perms(int n, std::vector<std::vector<int>>& P){
  P.clear();
  for(int t=0;t<8;++t){ std::vector<int> v(n*n);
    for(int y=0;y<n;++y) for(int x=0;x<n;++x){
      int X=x,Y=y;
      switch(t){ case 0: break; case 1: {X=y;Y=x;} break;
        case 2: {X=n-1-x;Y=y;} break; case 3: {X=y;Y=n-1-x;} break;
        case 4: {X=n-1-x;Y=n-1-y;} break; case 5: {X=x;Y=n-1-y;} break;
        case 6: {X=n-1-y;Y=n-1-x;} break; case 7: {X=n-1-y;Y=x;} break; }
      v[y*n+x]=Y*n+X; }
    P.push_back(v); }
}

// ================================================================ the game
struct Game {
  int V=0; u64 full=0;
  std::vector<std::vector<u64>> tri;
  std::vector<std::vector<u64>> qmask;     // full 4-point masks of quads containing p
  void init(int V_, const std::vector<u64>& quads){
    V=V_; full = (V>=64)?~u64(0):((u64(1)<<V)-1);
    tri.assign(V,{}); qmask.assign(V,{});
    for(u64 q:quads){ int ids[4]; mask_ids(q,ids);
      for(int t=0;t<4;++t){ u64 o=0; for(int k=0;k<4;++k) if(k!=t) o|=u64(1)<<ids[k];
        tri[ids[t]].push_back(o); qmask[ids[t]].push_back(q); } }
  }
  // Legality (identical to kyouen_core.py, and equivalent by induction since
  // occ is always safe: p is legal iff no forbidden quad lies in occ|{p}, i.e.
  // iff no 3-subset of occ together with p forms a forbidden quad).
  inline u64 nf(u64 occ,int p) const { u64 r=0; for(u64 t:tri[p]) if((occ&t)==t) r|=t; return r; }
  inline u64 L_of(u64 occ) const {
    u64 r=0,e=full&~occ;
    while(e){ int p=__builtin_ctzll(e); e&=e-1;
      bool ok=true; for(u64 t:tri[p]) if((occ&t)==t){ ok=false; break; }
      if(ok) r|=u64(1)<<p; }
    return r;
  }
  inline u64 Lnext(u64 occ,u64 lg,int p) const { return lg & ~nf(occ,p) & ~(u64(1)<<p); }
};
static u64 L_of(const Game&G,u64 occ){ return G.L_of(occ); }
// Grundy of a game given by an arbitrary quad list (small boards only)
static int grundy_full(const std::vector<u64>& quads,int V){
  Game G; G.init(V,quads);
  std::vector<int8_t> memo((size_t)1<<V,-1);
  std::function<int(u64)> rec=[&](u64 occ)->int{
    int8_t& r=memo[occ]; if(r!=-1) return r;
    u64 L=L_of(G,occ); unsigned seen=0; u64 m=L;
    while(m){ int p=__builtin_ctzll(m); m&=m-1; seen|=1u<<rec(occ|(u64(1)<<p)); }
    int g=0; while(seen&(1u<<g)) g++; r=(int8_t)g; return g; };
  return rec(0);
}

struct Sol {
  Game G; int V=0;
  std::vector<u64> st, lgv;
  std::vector<int> lvlStart, g, depth;
  std::vector<i64> proof;
  std::vector<int> Kof;
  std::vector<i64> level_counts;
  std::vector<int> lvl_nP, lvl_nN;
  i64 n_states=0; int nlev=0, K=0, g0=0, maxg=0; u64 W=0, maxfp=0, fpsum=0;
  std::vector<u64> maximals;
  std::vector<i64> hist_g;
  std::vector<int32_t> slot; u64 slotmask=0;
  inline u64 hsh(u64 k) const { k+=0x9E3779B97F4A7C15ull; k=(k^(k>>30))*0xBF58476D1CE4E5B9ull;
                               k=(k^(k>>27))*0x94D049BB133111EBull; return k^(k>>31); }
  inline int find(u64 m) const { u64 i=hsh(m)&slotmask;
    while(slot[i]>=0){ if(st[slot[i]]==m) return slot[i]; i=(i+1)&slotmask; } return -1; }
  inline int child(u64 occ,int p) const { return find(occ|(u64(1)<<p)); }
};

static void solve(Sol& S,int n,const std::vector<u64>& quads,bool doProof){
  S.V=n*n; S.G.init(S.V,quads);
  std::vector<std::vector<u64>> LS,LL;
  std::vector<u64> cS{0},cL{S.G.full}; LS.push_back(cS); LL.push_back(cL);
  while(true){
    int sz=(int)cS.size(); if(!sz) break;
    if(__builtin_popcountll(cS[0])>=26) break;
    std::vector<u64> ns,nl; ns.reserve((size_t)sz*3); nl.reserve((size_t)sz*3);
    for(int i=0;i<sz;++i){ u64 occ=cS[i],l=cL[i]; u64 m=l;
      while(m){ int p=__builtin_ctzll(m); m&=m-1; ns.push_back(occ|(u64(1)<<p)); nl.push_back(S.G.L_of(occ|(u64(1)<<p))); } }
    if(ns.empty()) break;
    LS.push_back(std::move(ns)); LL.push_back(std::move(nl));
    cS = LS.back(); cL = LL.back();   // fresh copy; never move and reuse ns
  }
  S.nlev=(int)LS.size(); S.lvlStart.assign(S.nlev+1,0);
  for(int i=0;i<S.nlev;++i){
    S.lvlStart[i]=(int)S.st.size(); S.level_counts.push_back((i64)LS[i].size());
    for(u64 x:LS[i]) S.st.push_back(x);
    for(u64 x:LL[i]) S.lgv.push_back(x); }
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
    if(li==S.nlev-1){ for(int i=a;i<b;++i){ S.g[i]=0;S.depth[i]=1;S.Kof[i]=__builtin_popcountll(S.st[i]);
        if(doProof)S.proof[i]=1; S.lvl_nP[li]++; } continue; }
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
    for(int i=a;i<b;++i){ if(S.g[i]==0) S.lvl_nP[li]++; else S.lvl_nN[li]++; }
  }
  S.g0=S.g[0]; S.K=S.Kof[0];
  { u64 m=S.lgv[0]; while(m){ int p=__builtin_ctzll(m); m&=m-1;
      if(S.g[S.find(u64(1)<<p)]==0) S.W|=u64(1)<<p; } }
  S.maxg=0; S.hist_g.assign(64,0);
  for(size_t i=0;i<S.st.size();++i){ if(S.g[i]>S.maxg) S.maxg=S.g[i];
    if(S.g[i]<64) S.hist_g[S.g[i]]++; }
  S.maxfp=0; S.fpsum=0; S.maximals.clear();
  for(size_t i=0;i<S.st.size();++i) if(S.lgv[i]==0){
    S.maxfp^=S.st[i]; S.fpsum+=S.st[i]; S.maximals.push_back(S.st[i]); }
  lg("  n=%d states=%lld levels=%d K=%d g0=%d |W|=%d maxg=%d maximals=%lld",
     n,S.n_states,S.nlev,S.K,S.g0,__builtin_popcountll(S.W),S.maxg,(i64)S.maximals.size());
  P("  n=%d total_safe=%lld K=%d g0=%d max_grundy=%d maximal_sets=%lld |W|=%d\n",
    n,S.n_states,S.K,S.g0,S.maxg,(i64)S.maximals.size(),__builtin_popcountll(S.W));
}

static std::vector<u64> build_quads(int n, std::vector<Pt>& pts){
  std::vector<u64> Q; pts.clear();
  for(int y=0;y<n;++y)for(int x=0;x<n;++x) pts.push_back({x,y});
  int V=n*n;
  for(int a=0;a<V-3;++a)for(int b=a+1;b<V-2;++b)for(int c=b+1;c<V-1;++c)for(int d=c+1;d<V;++d)
    if(det_pt(pts[a],pts[b],pts[c],pts[d])==0)
      Q.push_back(((u64)1<<a)|((u64)1<<b)|((u64)1<<c)|((u64)1<<d));
  return Q;
}

// ============================================================ residual graph
struct Res {
  int nv=0;
  std::vector<std::vector<int>> adj;
  std::vector<u64> adjm;            // global-index adjacency bitmasks
  std::vector<int> comp;
  int ncomp=0;
  std::vector<int> compSize, compDeg, compIsTree;
  int maxCompSize=0, minDeg=99, maxDeg=0;
  bool forest() const { for(int c=0;c<ncomp;++c) if(!compIsTree[c]) return false; return true; }
  int nedges() const { int e=0; for(int c=0;c<ncomp;++c) e+=compDeg[c]; return e/2; }
};
static Res residual(const Game&G,u64 occ,u64 L){
  Res R; std::vector<int> v; u64 m=L;
  while(m){ int p=__builtin_ctzll(m); m&=m-1; v.push_back(p); }
  R.nv=(int)v.size(); std::sort(v.begin(),v.end());
  std::map<int,int> loc; for(int i=0;i<R.nv;++i) loc[v[i]]=i;
  R.adjm.assign(R.nv,0);
  // edge {a,b} iff some forbidden quad {a,b,s,t} has BOTH s,t in S.  Scanning
  // the quads of a single vertex of L(S) is NOT enough (an edge may avoid it),
  // so scan every vertex.
  for(int i=0;i<R.nv;++i){ int a=v[i];
    for(u64 t:G.tri[a]){ u64 o=t&~occ&~(u64(1)<<a);
      if(__builtin_popcountll(o)!=2) continue;
      int b=__builtin_ctzll(o); o&=o-1; int c=__builtin_ctzll(o);
      auto ib=loc.find(b), ic=loc.find(c);
      if(ib==loc.end()||ic==loc.end()) continue;
      R.adjm[ib->second]|=u64(1)<<ic->second;
      R.adjm[ic->second]|=u64(1)<<ib->second; } }
  R.adj.assign(R.nv,{});
  for(int i=0;i<R.nv;++i){ u64 e=R.adjm[i]; while(e){ int w=__builtin_ctzll(e); e&=e-1; R.adj[i].push_back(w);} }
  R.comp.assign(R.nv,-1);
  for(int s=0;s<R.nv;++s) if(R.comp[s]<0){ int cid=R.ncomp++;
    std::vector<int> stk{s}; R.comp[s]=cid;
    while(!stk.empty()){ int u=stk.back(); stk.pop_back();
      u64 e=R.adjm[u]; while(e){ int w=__builtin_ctzll(e); e&=e-1;
        if(R.comp[w]<0){ R.comp[w]=cid; stk.push_back(w);} } } }
  R.compSize.assign(R.ncomp,0); R.compDeg.assign(R.ncomp,0); R.compIsTree.assign(R.ncomp,0);
  if(R.nv){ R.minDeg=99; R.maxDeg=0; }
  for(int i=0;i<R.nv;++i){ int dg=(int)__builtin_popcountll(R.adjm[i]);
    R.minDeg=std::min(R.minDeg,dg); R.maxDeg=std::max(R.maxDeg,dg);
    R.compSize[R.comp[i]]++; R.compDeg[R.comp[i]]+=dg; }
  for(int c=0;c<R.ncomp;++c){ R.compIsTree[c]=(R.compDeg[c]==R.compSize[c]-1);
    R.maxCompSize=std::max(R.maxCompSize,R.compSize[c]); }
  return R;
}
static std::string ResClass(const Res& R){
  std::vector<std::string> cs;
  for(int c=0;c<R.ncomp;++c){ std::vector<int> ds;
    for(int s=0;s<R.nv;++s) if(R.comp[s]==c) ds.push_back((int)__builtin_popcountll(R.adjm[s]));
    std::sort(ds.begin(),ds.end());
    std::string t="("; for(int d:ds){ t+=std::to_string(d); t+=","; } t+=")"; cs.push_back(t); }
  std::sort(cs.begin(),cs.end());
  std::string o; for(auto&s:cs) o+=s; return o;
}
// local (component-restricted) adjacency masks
static std::vector<u64> comp_adjm(const Res& R,int c){
  std::vector<int> loc(R.nv,-1); int k=0;
  for(int s=0;s<R.nv;++s) if(R.comp[s]==c) loc[s]=k++;
  std::vector<u64> am(k,0);
  for(int s=0;s<R.nv;++s) if(R.comp[s]==c){ u64 e=R.adjm[s];
    while(e){ int w=__builtin_ctzll(e); e&=e-1; if(R.comp[w]==c) am[loc[s]]|=u64(1)<<loc[w]; } }
  return am;
}
static int nk_value(const std::vector<u64>& am,int nv){
  if(nv==0) return 0;
  if(nv>=26) return -1;
  std::vector<int8_t> memo((size_t)1<<nv,-2);
  std::function<int(int)> rec=[&](int occ)->int{
    int8_t&r=memo[occ]; if(r!=-2) return r;
    unsigned seen=0; int av=((1<<nv)-1)&~occ;
    while(av){ int v=__builtin_ctz(av); av&=av-1;
      bool blocked=false; u64 e=am[v]; while(e){ int w=__builtin_ctzll(e); e&=e-1; if(occ>>w&1){ blocked=true; break; } }
      if(blocked) continue;
      int child=(occ|(1<<v)) & ~(int)am[v];
      seen|=1u<<rec(child); }
    int g=0; while(seen&(1u<<g)) g++; r=(int8_t)g; return g; };
  return rec(0);
}
static bool has_cycle_of_len(const Res& R,int want){
  if(R.nv<want) return false;
  for(int s=0;s<R.nv;++s){
    std::vector<int> dist(R.nv,-1); std::vector<int> stk{s}; dist[s]=0;
    while(!stk.empty()){ int u=stk.back(); stk.pop_back();
      if(dist[u]+1>want) continue;
      for(int w:R.adj[u]){
        if(w==s && dist[u]+1>=3 && dist[u]+1==want) return true;
        if(dist[w]<0){ dist[w]=dist[u]+1; stk.push_back(w); } } } }
  return false;
}

static Sol S2,S3,S4,S5,S6;
static std::vector<Pt> PT[7];
static std::vector<u64> QQ[7];

static void sec_core(){
  P("## sec_core : full enumeration n=2..6 (exact Grundy)\n");
  i64 expect[7]={0,0,1,14,194,826,2491};
  for(int n=2;n<=6;++n){
    QQ[n]=build_quads(n,PT[n]);
    lg("n=%d quads=%zu",n,QQ[n].size());
    if((i64)QQ[n].size()!=expect[n]) P("  !! QUAD COUNT MISMATCH n=%d got %zu expect %lld\n",n,QQ[n].size(),expect[n]);
    Sol& S=(n==2?S2:(n==3?S3:(n==4?S4:(n==5?S5:S6))));
    solve(S,n,QQ[n],true);
    P("  Z_%d(lam) =",n);
    for(size_t i=0;i<S.level_counts.size();++i) P(" %lld",S.level_counts[i]);
    P("\n  grundy histogram:");
    for(int g=0;g<64;++g) if(S.hist_g[g]) P(" %d:%d",g,S.hist_g[g]);
    P("\n  per-level P/N:");
    for(int li=0;li<S.nlev;++li) P(" L%d(%d/%d)",li,S.lvl_nP[li],S.lvl_nN[li]);
    P("\n");
  }
}

// ------------------------------------------------- sec_census : B232/233/234
struct Census {
  i64 positions=0, forest_states=0, cycle_states=0;
  i64 with_cycle3=0, with_cycle4=0, with_cycle5=0, with_cycle6=0;
  i64 max_ncomp=0, max_comp_size=0, max_vertices=0, forest_max_ncomp=0;
  std::map<std::string,i64> cls_count;
  std::set<std::string> tree_shapes;
  i64 b234_tested=0, b234_found=0; int b234_r=0; std::string b234_witness;
  i64 b234_ruin=0, b234_ruin_bad=0;
};
static void sec_census(){
  P("\n## sec_census : B232/B233/B234\n");
  Census C;
  int NS[3]={4,5,6}; int CAP[3]={10,7,6}; Sol* SS[3]={&S4,&S5,&S6};
  for(int si=0;si<3;++si){ int n=NS[si]; Sol& S=*SS[si];
    for(size_t i=0;i<S.st.size();++i){
      u64 L=S.lgv[i]; int ks=__builtin_popcountll(S.st[i]);
      if(L==0||ks>CAP[si]) continue;
      C.positions++;
      Res R=residual(S.G,S.st[i],L);
      C.max_vertices=std::max(C.max_vertices,(i64)R.nv);
      C.max_ncomp=std::max(C.max_ncomp,(i64)R.ncomp);
      C.max_comp_size=std::max(C.max_comp_size,(i64)R.maxCompSize);
      bool cyc=!R.forest();
      if(cyc) C.cycle_states++; else { C.forest_states++; C.forest_max_ncomp=std::max(C.forest_max_ncomp,(i64)R.ncomp); }
      for(int c=0;c<R.ncomp;++c) if(R.compIsTree[c]&&R.compSize[c]<=6){
        std::vector<u64> am=comp_adjm(R,c);
        std::vector<int> ds; for(size_t k=0;k<am.size();++k) ds.push_back(__builtin_popcountll(am[k]));
        std::sort(ds.begin(),ds.end());
        std::string t="T"+std::to_string(R.compSize[c])+"v deg["; for(int d:ds){ t+=std::to_string(d); t+=","; } t+="]";
        C.tree_shapes.insert(t); }
      if(cyc && R.nv<=11){
        if(has_cycle_of_len(R,3)) C.with_cycle3++;
        if(has_cycle_of_len(R,4)) C.with_cycle4++;
        if(has_cycle_of_len(R,5)) C.with_cycle5++;
        if(has_cycle_of_len(R,6)) C.with_cycle6++; }
      C.cls_count[ResClass(R)]++;
      // B234: r vertex-disjoint edge-disjoint components of equal size and
      // equal Node-Kayles value (an exact r-fold sum of one component).
      if(R.ncomp>=2){
        C.b234_tested++;
        int best=1; std::string bw;
        for(int a=0;a<R.ncomp;++a) for(int c=a+1;c<R.ncomp;++c){
          if(R.compSize[a]!=R.compSize[c]) continue;
          bool linked=false; for(int s=0;s<R.nv;++s) if(R.comp[s]==a){
            for(int w:R.adj[s]) if(R.comp[w]==c){ linked=true; break; } if(linked) break; }
          if(linked) continue;
          int ga=nk_value(comp_adjm(R,a),R.compSize[a]);
          int gc=nk_value(comp_adjm(R,c),R.compSize[c]);
          if(ga<0||gc<0) continue;
          if(ga==gc){ best=std::max(best,2);
            if(bw.empty()) bw="n="+std::to_string(n)+" comp size="+std::to_string(R.compSize[a])+" grundy="+std::to_string(ga)+" occ="+occ_str(S.st[i],n); } }
        if(best>=2){ C.b234_found++; if(best>C.b234_r){ C.b234_r=best; C.b234_witness=bw; } }
      }
      // xor theorem check: g(S) == xor of component Node-Kayles values
      if(R.nv<=22){
        int xo=0; bool ok=true;
        for(int c=0;c<R.ncomp;++c){ int gv=nk_value(comp_adjm(R,c),R.compSize[c]); if(gv<0){ ok=false; break; } xo^=gv; }
        if(ok){ C.b234_ruin++; if(xo!=S.g[i]) C.b234_ruin_bad++; } }
    }
    lg("  census n=%d done positions=%lld",n,C.positions); }
  P("  positions_scanned=%lld  R_forest=%lld  R_has_cycle=%lld\n",C.positions,C.forest_states,C.cycle_states);
  P("  max |L|=%lld  max #components=%lld  max component size=%lld  max #components when forest=%lld\n",
    C.max_vertices,C.max_ncomp,C.max_comp_size,C.forest_max_ncomp);
  P("  states containing a cycle of length 3/4/5/6 (|L|<=11): %lld / %lld / %lld / %lld\n",
    C.with_cycle3,C.with_cycle4,C.with_cycle5,C.with_cycle6);
  P("  distinct tree-component shapes with <=6 vertices: %zu\n",C.tree_shapes.size());
  { std::vector<std::string> v(C.tree_shapes.begin(),C.tree_shapes.end()); std::sort(v.begin(),v.end());
    for(auto&s:v) P("     %s\n",s.c_str()); }
  P("  distinct R(S) degree-classes=%zu; all occur at least once\n",C.cls_count.size());
  { std::vector<std::pair<std::string,i64>> v; for(auto&kv:C.cls_count) v.push_back({kv.first,kv.second});
    std::sort(v.begin(),v.end(),[](auto&a,auto&b){return a.second>b.second;});
    for(size_t i=0;i<v.size()&&i<25;++i) P("     %6lld  %s\n",v[i].second,v[i].first.c_str()); }
  P("  B234: states_tested=%lld with_2_equal-size_equal-grundy_disjoint_components=%lld max_r=%d\n",
    C.b234_tested,C.b234_found,C.b234_r);
  P("  B234_witness=%s\n",C.b234_witness.c_str());
  P("  B234 xor-theorem (g(S) == xor of component Node-Kayles values): tested=%lld violations=%lld\n",
    C.b234_ruin,C.b234_ruin_bad);
}

// --------------------------------------------------------- sec_chain
static void sec_chain(){
  P("\n## sec_chain : B235/B236/B237/B246\n");
  i64 maxr=0,r3=0,r4=0,r5=0,r6=0,r7=0; i64 nstates=0; std::string w236;
  i64 b246_total=0,b246_nonforest=0; std::map<std::string,i64> b246_cls;
  i64 b237_tested=0,b237_pos=0,b237_maxincr=0,b237_maxabs=0; std::string w237;
  i64 hist[64]; std::memset(hist,0,sizeof(hist));
  i64 ind_min=99, ind_max=0;  // B235: |V(R(after unique win)) \ W(S after)|
  int NS[3]={4,5,6}; int CAP[3]={10,7,6}; Sol* SS[3]={&S4,&S5,&S6};
  for(int si=0;si<3;++si){ int n=NS[si]; Sol& S=*SS[si];
    for(size_t i=0;i<S.st.size();++i){
      u64 L=S.lgv[i];
      if(S.g[i]==0||L==0||__builtin_popcountll(S.st[i])>CAP[si]) continue;
      std::vector<int> winp; u64 m=L;
      while(m){ int p=__builtin_ctzll(m); m&=m-1; if(S.g[S.child(S.st[i],p)]==0) winp.push_back(p); }
      if(winp.size()!=1) continue;
      nstates++;
      int r=1, cur=(int)i; int firstp=winp[0];
      while(true){
        int j=S.child(S.st[cur],r>=1?winp[0]:0);
        (void)j; break; }
      // walk the chain
      { int p=firstp; r=1; int node=(int)i;
        while(true){
          int j=S.child(S.st[node],p);
          if(S.g[j]!=0) break;
          if(S.lgv[j]==0) break;
          std::vector<int> w2; u64 mm=S.lgv[j];
          while(mm){ int q=__builtin_ctzll(mm); mm&=mm-1; if(S.g[S.child(S.st[j],q)]==0) w2.push_back(q); }
          if(w2.size()!=1) break;
          p=w2[0]; r++; node=j;
          if(r>10) break; } }
      maxr=std::max(maxr,(i64)r);
      if(r==3) r3++; if(r==4) r4++; if(r==5) r5++; if(r==6) r6++; if(r==7) r7++;
      if(r>=6 && w236.empty()){ std::string w="n="+std::to_string(n)+" r="+std::to_string(r)+" occ="+occ_str(S.st[i],n); w236=w; }
      // B246 / B235 on the position after the forced win
      { int j=S.child(S.st[i],firstp); u64 L2=S.lgv[j];
        if(L2){ b246_total++; Res R=residual(S.G,S.st[j],L2);
          if(!R.forest()) b246_nonforest++;
          b246_cls[ResClass(R)]++;
          ind_min=std::min(ind_min,(i64)R.nv); ind_max=std::max(ind_max,(i64)R.nv); } }
      // B237
      { Res R0=residual(S.G,S.st[i],L); int j=S.child(S.st[i],firstp);
        Res R1=residual(S.G,S.st[j],S.lgv[j]);
        b237_tested++; int incr=R1.ncomp-R0.ncomp;
        hist[R1.ncomp<64?R1.ncomp:63]++;
        if(incr>0){ b237_pos++; if(incr>b237_maxincr){ b237_maxincr=incr;
          w237="n="+std::to_string(n)+" #components "+std::to_string(R0.ncomp)+" -> "+std::to_string(R1.ncomp)+" after ("+std::to_string(firstp/n)+","+std::to_string(firstp%n)+")"; } }
        b237_maxabs=std::max(b237_maxabs,(i64)R1.ncomp); }
    }
    lg("  chain n=%d done unique-win N states=%lld",n,nstates); }
  P("  B236: N-positions with a UNIQUE winning move=%lld, max forced-unique-move chain r=%lld\n",nstates,maxr);
  P("  B236 chain-length counts: r=3:%lld r=4:%lld r=5:%lld r=6:%lld r=7:%lld\n",r3,r4,r5,r6,r7);
  P("  B236_witness(r>=6)=%s\n",w236.c_str());
  P("  B246/B235: positions after the forced win=%lld, residual NOT a forest=%lld, distinct classes=%zu, |V| in [%lld,%lld]\n",
    b246_total,b246_nonforest,b246_cls.size(),ind_min,ind_max);
  P("  B237: tested=%lld positive component-count increase=%lld max increase=%lld max #components after a move=%lld\n",
    b237_tested,b237_pos,b237_maxincr,b237_maxabs);
  P("  B237_witness=%s\n",w237.c_str());
  P("  B237 histogram of #components after the unique winning move:");
  for(int k=0;k<64;++k) if(hist[k]) P(" %d:%lld",k,hist[k]); P("\n");
}

// ----------------------------------------------------------------- sec_switch
static void sec_switch(){
  P("\n## sec_switch : B238\n");
  int NS[2]={4,5}; Sol* SS[2]={&S4,&S5};
  for(int si=0;si<2;++si){ int n=NS[si]; Sol& S=*SS[si];
    i64 tested=0,found=0; std::string wit;
    for(size_t i=0;i<S.st.size();++i){
      u64 L=S.lgv[i];
      if(__builtin_popcountll(S.st[i])>8) continue;
      if(__builtin_popcountll(L)<3) continue;
      tested++;
      std::vector<int> ps,cs; u64 m=L;
      while(m){ int p=__builtin_ctzll(m); m&=m-1; ps.push_back(p); cs.push_back(S.g[S.child(S.st[i],p)]); }
      for(size_t a=0;a<ps.size()&&found<4;++a) for(size_t c=a+1;c<ps.size()&&found<4;++c){
        if(cs[a]!=cs[c]) continue;
        int q1=ps[a],q2=ps[c];
        int j1=S.child(S.st[i],q1), j2=S.child(S.st[i],q2);
        u64 l1=S.lgv[j1], l2=S.lgv[j2];
        u64 comm=l1&l2;
        while(comm){ int p=__builtin_ctzll(comm); comm&=comm-1;
          int k1=S.child(S.st[j1],p), k2=S.child(S.st[j2],p);
          if(S.g[k1]==S.g[k2]) continue;
          found++;
          wit="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" q1=("+std::to_string(q1/n)+","+std::to_string(q1%n)+") q2=("+std::to_string(q2/n)+","+std::to_string(q2%n)+") p=("+std::to_string(p/n)+","+std::to_string(p%n)+") g(q1)=g(q2)="+std::to_string(cs[a])+" but g(S+q1+p)="+std::to_string(S.g[k1])+" != g(S+q2+p)="+std::to_string(S.g[k2]);
          break; }
        if(found>=4) break; } }
    P("  n=%d: states_tested=%lld  switch_points_found=%lld\n",n,tested,found);
    if(!wit.empty()) P("     witness=%s\n",wit.c_str()); }
}

// ------------------------------------------------------------------- sec_ctx
static void sec_ctx(){
  P("\n## sec_ctx : B240 (context dependence of a single safe set)\n");
  int NS[2]={4,5}; int CAP[2]={9,7}; Sol* SS[2]={&S4,&S5};
  for(int si=0;si<2;++si){ int n=NS[si]; Sol& S=*SS[si];
    i64 tested=0,eq=0,ne=0; std::string wit;
    for(size_t i=0;i<S.st.size();++i){
      u64 L=S.lgv[i];
      if(L==0||__builtin_popcountll(S.st[i])>CAP[si]) continue;
      Res R=residual(S.G,S.st[i],L);
      int gR=nk_value(R.adjm,R.nv);
      if(gR<0) continue;
      tested++;
      if(gR==S.g[i]) eq++;
      else { ne++; if(wit.empty())
        wit="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" g(S)="+std::to_string(S.g[i])+" g(NodeKayles(R(S)))="+std::to_string(gR); } }
    P("  n=%d: states_tested=%lld  g(S)==g_R(S): %lld  differs: %lld  (ratio %s)\n",
      n,tested,eq,ne, frac(ne,tested).c_str());
    if(!wit.empty()) P("     witness=%s\n",wit.c_str()); }
}

// ----------------------------------------------------------------- sec_proof
static void sec_proof(){
  P("\n## sec_proof : B245/B247/B248/B249\n");
  int NS[2]={4,5}; Sol* SS[2]={&S4,&S5};
  for(int si=0;si<2;++si){ int n=NS[si]; Sol& S=*SS[si];
    i64 Nn=0,disj=0; std::string w247;
    std::map<std::string,std::pair<i64,i64>> tab;   // B248
    std::map<int,i64> mx,cnt; i64 ng1=0,mxp=0,mxd=0;
    // B245: for N-positions grouped by #winning moves, correlate #proof nodes
    // with #isomorphism classes of residual components (all residual shapes
    // that repeat).  We use "#components" and "#distinct component shapes".
    std::map<int,std::pair<i64,i64>> b245;  // key=#winning moves -> (sum repeats, count)
    for(size_t i=0;i<S.st.size();++i){
      { std::string key=std::to_string(__builtin_popcountll(S.st[i]))+"/"+std::to_string(__builtin_popcountll(S.lgv[i]))+"/"+(S.lgv[i]==0?"M":"N");
        auto&pr=tab[key]; if(S.g[i]==0) pr.first++; else pr.second++; }
      if(S.g[i]==1){ ng1++; int d=S.depth[i];
        mx[d]=std::max(mx[d],S.proof[i]); cnt[d]++; mxp=std::max(mxp,S.proof[i]); mxd=std::max(mxd,(i64)d); }
      if(S.g[i]==0) continue;
      Nn++;
      u64 L=S.lgv[i];
      if(L==0) continue;
      // B245 stat
      { Res R=residual(S.G,S.st[i],L);
        std::map<std::string,int> shapes;
        int reps=0;
        for(int c=0;c<R.ncomp;++c){ std::vector<u64> am=comp_adjm(R,c);
          std::vector<int> ds; for(size_t k=0;k<am.size();++k) ds.push_back(__builtin_popcountll(am[k]));
          std::sort(ds.begin(),ds.end()); std::string t="(";
          for(int d:ds){ t+=std::to_string(d); t+=","; } t+=")";
          int& q=shapes[t]; q++; if(q>=2) reps++; }
        int nw=0; u64 m=L; while(m){ int p=__builtin_ctzll(m); m&=m-1; if(S.g[S.child(S.st[i],p)]==0) nw++; }
        auto& pr=b245[nw]; pr.first+=reps; pr.second++; }
      // B247
      std::vector<int> allp; u64 m=L; while(m){ int p=__builtin_ctzll(m); m&=m-1; allp.push_back(p); }
      i64 bestp=LLONG_MAX; int bd=INT_MAX;
      for(int p:allp){ int ci=S.child(S.st[i],p); if(S.g[ci]!=0) continue;
        bestp=std::min(bestp,S.proof[ci]); bd=std::min(bd,S.depth[ci]); }
      if(bestp==LLONG_MAX) continue;
      int pr=-1,dr=-1;
      for(int p:allp){ int ci=S.child(S.st[i],p); if(S.g[ci]!=0) continue;
        if(S.proof[ci]==bestp && pr<0) pr=p;
        if(S.depth[ci]==bd && dr<0) dr=p; }
      if(pr>=0&&dr>=0&&pr!=dr){ disj++;
        if(w247.empty()) w247="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)
          +" min-proof move=("+std::to_string(pr/n)+","+std::to_string(pr%n)+")[proof="+std::to_string(bestp)
          +"] min-depth move=("+std::to_string(dr/n)+","+std::to_string(dr%n)+")[depth="+std::to_string(bd)+"]"; }
    }
    P("  B247 n=%d: N-positions=%lld  with disjoint minimisers (a proof-optimal and a depth-optimal winning move that differ)=%lld\n",n,Nn,disj);
    if(!w247.empty()) P("     witness=%s\n",w247.c_str());
    P("  B249 n=%d: g=1 positions=%lld  max depth=%lld  max minimal proof=%lld\n",n,ng1,mxd,mxp);
    P("     max minimal proof by depth:");
    for(auto&kv:mx) P(" d%d:%lld",kv.first,kv.second); P("\n");
    P("     count by depth:");
    for(auto&kv:cnt) P(" d%d:%lld",kv.first,kv.second); P("\n");
    P("  B248 n=%d  |S|/|L|/maximal -> (P count, N count):\n",n);
    for(auto&kv:tab) P("     %-10s %6lld / %6lld\n",kv.first.c_str(),kv.second.first,kv.second.second);
    P("  B245 n=%d  mean #repeated residual component shapes by #winning moves (1..):\n",n);
    for(auto&kv:b245) P("     nw=%d mean_repeats=%s (over %lld positions)\n",kv.first,frac(kv.second.first,kv.second.second).c_str(),kv.second.second);
  }
}

// -------------------------------------------------------------------- sec_u
static void sec_u(){
  P("\n## sec_u : B261..B270 (threat gain u)\n");
  int NS[2]={4,5}; int CAP[2]={9,6}; Sol* SS[2]={&S4,&S5};
  for(int si=0;si<2;++si){ int n=NS[si]; Sol& S=*SS[si];
    i64 b261=0,b261b=0; int b261best=0; std::string w261;
    i64 b262b=0; std::string w262;
    i64 b264=0; std::string w264;
    i64 b265=0; std::string w265;
    i64 b266pairs=0; i64 jh[64]; std::memset(jh,0,sizeof(jh));
    i64 b267c=0; std::string w267;
    i64 b268=0; std::string w268;
    i64 b269f=0,b269fP=0,b269n=0,b269nP=0;
    i64 b270=0; std::string w270;
    i64 b270pairs=0;
    for(size_t i=0;i<S.st.size();++i){
      u64 L=S.lgv[i];
      if(L==0||__builtin_popcountll(S.st[i])>CAP[si]) continue;
      int nl=__builtin_popcountll(L);
      std::vector<int> ps; u64 m=L; while(m){ int p=__builtin_ctzll(m); m&=m-1; ps.push_back(p); }
      std::vector<int> ci(nl),uo(nl);
      for(int t=0;t<nl;++t){ ci[t]=S.child(S.st[i],ps[t]); uo[t]=__builtin_popcountll(L&~S.lgv[ci[t]]); }
      if(S.g[i]!=0){
        bool allwin0=true,anywin=false,anyu=false;
        for(int t=0;t<nl;++t){ if(S.g[ci[t]]==0){ anywin=true; if(uo[t]>0) allwin0=false; } if(uo[t]>0) anyu=true; }
        if(anywin&&allwin0&&anyu){ b264++;
          if(w264.empty()){ int nw=0; for(int t=0;t<nl;++t) if(S.g[ci[t]]==0) nw++;
            w264="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" |L|="+std::to_string(nl)+" #winning="+std::to_string(nw)+" all winning moves have u=0"; } }
        { int nw=0,wp=-1; for(int t=0;t<nl;++t) if(S.g[ci[t]]==0){ nw++; wp=ps[t]; }
          if(nw==1){ int lo=0,hi=0; for(int t=0;t<nl;++t){ if(uo[t]<uo[wp]) lo++; if(uo[t]>uo[wp]) hi++; }
            if(lo>0&&hi>0){ b265++;
              if(w265.empty()) w265="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" unique winning move=("
                +std::to_string(wp/n)+","+std::to_string(wp%n)+") u="+std::to_string(uo[wp])+" #lower="+std::to_string(lo)+" #higher="+std::to_string(hi); } } }
      }
      { int mn=99,mx=-1; for(int t=0;t<nl;++t){ mn=std::min(mn,uo[t]); mx=std::max(mx,uo[t]); }
        if(mn==mx){ b269f++; if(S.g[i]==0) b269fP++; } else { b269n++; if(S.g[i]==0) b269nP++; } }
      for(int t=0;t<nl;++t) for(int s=t+1;s<nl;++s){
        int p=ps[t],q=ps[s];
        int jp=ci[t], jq=ci[s];
        int ppq=S.child(S.st[jp],q); if(ppq<0) continue;
        int qqp=S.child(S.st[jq],p); if(qqp<0) continue;
        b266pairs++;
        u64 joint = L & ~S.lgv[ppq];
        int jn=__builtin_popcountll(joint);
        jh[jn<64?jn:63]++;
        if(uo[t]<=1&&uo[s]<=1&&jn>=2){ b261++;
          if(jn>b261best){ b261best=jn; w261="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" u(p)="+std::to_string(uo[t])+" u(q)="+std::to_string(uo[s])+" joint="+std::to_string(jn); } }
        if(uo[t]>=3&&uo[s]>=3){
          int dUq = uo[s] - __builtin_popcountll(S.lgv[jp] & ~S.lgv[ppq]);
          if(dUq==0){ b262b++;
            if(w262.empty()) w262="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" u(p)="+std::to_string(uo[t])+" u(q)="+std::to_string(uo[s])+" additional gain of q after p = 0"; } }
        { u64 nf1=L&~S.lgv[ppq], nf2=L&~S.lgv[qqp];
          if(nf1==nf2 && S.g[ppq]!=S.g[qqp]){ b267c++;
            if(w267.empty()) w267="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" p=("+std::to_string(p/n)+","+std::to_string(p%n)+") q=("+std::to_string(q/n)+","+std::to_string(q%n)+") g(S+p+q)="+std::to_string(S.g[ppq])+" vs "+std::to_string(S.g[qqp])+" (identical new-forbidden set, |nf|="+std::to_string(jn)+")"; } }
        { int g1=S.g[jp],g2=S.g[jq];
          if((g1==0)!=(g2==0)){ b270++;
            if(w270.empty()) w270="n="+std::to_string(n)+" occ="+occ_str(S.st[i],n)+" g(S+p)="+std::to_string(g1)+" g(S+q)="+std::to_string(g2)+" p=("+std::to_string(p/n)+","+std::to_string(p%n)+") q=("+std::to_string(q/n)+","+std::to_string(q%n)+")"; } }
      }
      // B268
      for(int t=0;t<nl;++t){ int jp=ci[t];
        if(S.g[i]==0||S.g[jp]==0) continue;
        u64 common=L&S.lgv[jp];
        while(common){ int q=__builtin_ctzll(common); common&=common-1;
          bool a=S.g[S.child(S.st[i],q)]==0, b=S.g[S.child(S.st[jp],q)]==0;
          if(a&&b){ b268++;
            if(w268.empty()) w268="n="+std::to_string(n)+" S="+occ_str(S.st[i],n)+" T=S+("+std::to_string(ps[t]/n)+","+std::to_string(ps[t]%n)+") both N, #common legal moves="+std::to_string(__builtin_popcountll(L&S.lgv[jp]))+", NO move is winning in both";
            break; } }
        if(!w268.empty()) break; }
    }
    lg("  sec_u n=%d done",n);
    P("  --- n=%d ---\n",n);
    P("  B264 every winning move has u=0 while some legal move has u>0: %lld  %s\n",b264,w264.c_str());
    P("  B265 unique winning move has strictly median u: %lld  %s\n",b265,w265.c_str());
    P("  B269 flat-u states=%lld (P=%lld) nonflat=%lld (P=%lld)  P-rate flat=%s nonflat=%s\n",
      b269f,b269fP,b269n,b269nP, frac(b269fP,b269f).c_str(), frac(b269nP,b269n).c_str());
    P("  B261 pairs with u(p),u(q)<=1 and joint>=2: %lld  max joint=%d  %s\n",b261,b261best,w261.c_str());
    P("  B262 pairs with u(p),u(q)>=3 and no additional gain for q after p: %lld  %s\n",b262b,w262.c_str());
    P("  B266 legal pairs examined=%lld  joint-size histogram:",b266pairs);
    for(int k=0;k<64;++k) if(jh[k]) P(" %d:%lld",k,jh[k]); P("\n");
    P("  B267 counterexamples (identical new-forbidden set, different resulting g): %lld  %s\n",b267c,w267.c_str());
    P("  B268 one-stone extension that makes the best-move sets disjoint: %lld  %s\n",b268,w268.c_str());
    P("  B270 pairs with exactly one intermediate P position: %lld  %s\n",b270,w270.c_str());
    (void)b270pairs;
  }
}

// ---------------------------------------------------------------- sec_lambda
static void sec_lambda(){
  P("\n## sec_lambda : B271/B272/B273/B274/B275\n");
  int NS[3]={4,5,6}; Sol* SS[3]={&S4,&S5,&S6};
  for(int si=0;si<3;++si){ int n=NS[si]; Sol& S=*SS[si];
    i64 Z1=0,m1=0,m2=0;
    for(int k=0;k<(int)S.level_counts.size();++k){ Z1+=S.level_counts[k];
      m1+=(i64)k*S.level_counts[k]; m2+=(i64)k*k*S.level_counts[k]; }
    i64 vnum=m2*Z1-m1*m1;
    P("  n=%d: Z_1=%lld  E_1|S|=%s  Var_1|S|=%s  K=%d  E_1 < K/2: %s\n",
      n,Z1,frac(m1,Z1).c_str(),frac(vnum,Z1*Z1).c_str(),S.K, (2*m1 < (i64)S.K*Z1)?"yes":"no");
    int mode=0; for(int k=0;k<(int)S.level_counts.size();++k) if(S.level_counts[k]>S.level_counts[mode]) mode=k;
    P("  B275 n=%d: modal layer=%d (A=%lld); K=%d; Var_1 = %s\n",n,mode,S.level_counts[mode],S.K,frac(vnum,Z1*Z1).c_str());
    // B274: ratios of level counts near the top
    P("  B274 n=%d  A_{K-j}/A_K:",n);
    for(int j=0;j<=3&&S.K-j>=0;++j) P(" %d:%s",j,frac(S.level_counts[S.K-j],(i64)S.maximals.size()).c_str());
    P("\n");
    // B272: co-occurrence of pairs that SHARE a forbidden quad inside maximal sets
    int V=n*n; i64 tot=(i64)S.maximals.size();
    std::vector<int> deg(V,0); std::vector<std::vector<int>> pc(V,std::vector<int>(V,0));
    for(size_t i=0;i<S.maximals.size();++i){ u64 o=S.maximals[i];
      std::vector<int> v; while(o){ int p=__builtin_ctzll(o); o&=o-1; v.push_back(p); deg[p]++; }
      for(size_t a=0;a<v.size();++a) for(size_t b=a+1;b<v.size();++b) pc[v[a]][v[b]]++; }
    i64 shared=0,sharedPos=0;
    for(size_t qi=0;qi<QQ[n].size();++qi){ int ids[4]; mask_ids(QQ[n][qi],ids);
      for(int a=0;a<4;++a) for(int b=a+1;b<4;++b){ shared++; if(pc[ids[a]][ids[b]]>0) sharedPos++; } }
    P("  B272 n=%d: point pairs sharing a forbidden quad=%lld; of these, co-occurring in >=1 maximal set=%lld\n",
      n,shared,sharedPos);
    // Pr(p in a maximal set): is it uniform? count the distinct values.
    { int mn=1<<30,mx=-1; for(int p=0;p<V;++p){ mn=std::min(mn,deg[p]); mx=std::max(mx,deg[p]); }
      P("  B272/B276 n=%d: Pr(p belongs to a maximal set) ranges over [%lld/%lld, %lld/%lld] (uniform: %s)\n",
        n,mn,tot,mx,tot,(mn==mx)?"YES":"no"); }
  }
}

// ----------------------------------------------------------------- sec_geom
static void sec_geom(){
  P("\n## sec_geom : B250/B278/B280/B281/B282/B283/B286/B287/B288/B289/B290\n");
  // B250 / B266: max new-forbidden points from one move
  { int NS[3]={4,5,6}; Sol* SS[3]={&S4,&S5,&S6};
    for(int si=0;si<3;++si){ Sol& S=*SS[si]; int n=NS[si]; int mx=0,mn=0;
      for(size_t i=0;i<S.st.size();++i){ u64 L=S.lgv[i];
        if(__builtin_popcountll(S.st[i])>7) continue;
        u64 m=L; while(m){ int p=__builtin_ctzll(m); m&=m-1;
          int c=__builtin_popcountll(L&~S.lgv[S.child(S.st[i],p)]);
          mx=std::max(mx,c); if(!mn||c<mn) mn=c; } }
      P("  B250 n=%d: |u_S(p)| over all states with |S|<=7: min=%d max=%d  (board has %d points, per row %d)\n",n,mn,mx,n*n,n); } }
  // B280: profiles of the maximal sets by point class -> the top layer of a
  // multivariable Z.
  { int NS[3]={4,5,6}; Sol* SS[3]={&S4,&S5,&S6};
    for(int si=0;si<3;++si){ Sol& S=*SS[si]; int n=NS[si];
      auto cls=[&](int p)->int{ int x=p%n,y=p/n;
        if(n%2==1&&x==n/2&&y==n/2) return 2;
        if((x==0||x==n-1)&&(y==0||y==n-1)) return 0; return 1; };
      std::map<std::string,i64> prof;
      for(size_t i=0;i<S.maximals.size();++i){ u64 o=S.maximals[i]; int c3[3]={0,0,0};
        while(o){ int p=__builtin_ctzll(o); o&=o-1; c3[cls(p)]++; }
        prof[std::to_string(c3[0])+","+std::to_string(c3[1])+","+std::to_string(c3[2])]++; }
      i64 tot=0; for(auto&kv:prof) tot+=kv.second;
      P("  B280 n=%d: %zu distinct (corner,other,centre) profiles among %zu maximal sets; total=%lld (%s)\n",
        n,prof.size(),S.maximals.size(),tot, tot==(i64)S.maximals.size()?"matches":"MISMATCH");
      for(auto&kv:prof) P("       %s -> %lld\n",kv.first.c_str(),kv.second); } }
  // B281 / B283: quad families and the collinear/concyclic split
  { struct Bd{ int W,H; } bds[3]={{3,3},{4,4},{5,3}};
    for(int bi=0;bi<3;++bi){ int W=bds[bi].W,H=bds[bi].H,V=W*H;
      std::vector<Pt> pts; for(int y=0;y<H;++y)for(int x=0;x<W;++x) pts.push_back({x,y});
      std::vector<std::vector<int>> perms; if(W==H) d4_perms(W,perms);
      for(int k=6;k<=7;++k){ if(k>V) continue;
        std::map<std::string,std::vector<std::pair<int,int>>> byQ;  // key -> (ncol, idx)
        std::vector<int> cur(k); i64 cnt=0; i64 ncolTot=0;
        std::function<void(int,int)> rec=[&](int start,int d){
          if(d==k){ std::string key; int ncol=0,ncir=0;
            for(int a=0;a<k;++a)for(int b=a+1;b<k;++b)for(int c=b+1;c<k;++c)for(int e=c+1;e<k;++e){
              const Pt&A=pts[cur[a]],&B=pts[cur[b]],&C=pts[cur[c]],&D=pts[cur[e]];
              if(det_pt(A,B,C,D)!=0) continue;
              if(det3(A,B,C)==0) ncol++; else ncir++;
              int q4[4]={cur[a],cur[b],cur[c],cur[e]}; std::sort(q4,q4+4);
              for(int t=0;t<4;++t){ key+=std::to_string(q4[t]); key+=","; } key+=";"; }
            byQ[key].push_back({ncol,0}); cnt++; ncolTot+=ncol; (void)ncir; return; }
          for(int i=start;i<V;++i){ cur[d]=i; rec(i+1,d+1); } };
        rec(0,0);
        i64 collide=0,collideDiffCol=0,collideNonD4=0; std::string w283;
        for(auto&kv:byQ){ if(kv.second.size()<2) continue; collide++;
          int mn=99,mx=-1; for(auto&pr:kv.second){ mn=std::min(mn,pr.first); mx=std::max(mx,pr.first); }
          if(mn!=mx){ collideDiffCol++;
            if(w283.empty()) w283="a quad family realised by >=2 different k-subsets with different collinear-quad counts ("+std::to_string(mn)+" vs "+std::to_string(mx)+")"; } }
        P("  B281/B283 board %dx%d k=%d: %lld k-subsets, %zu distinct quad families, families with >=2 realisations=%lld, of which the collinear split differs=%lld\n",
          W,H,k,cnt,byQ.size(),collide,collideDiffCol);
        if(!w283.empty()) P("       %s\n",w283.c_str()); } } }
  // B288 / B289 / B290: an explicit LP-dual certificate from circles and lines.
  // Dual: choose y_c >= 0 for every conic c (circle or line) with >= 4 board
  // points such that sum_{c ni p} y_c >= 1 for every board point p.  Then
  // |S| = sum_{p in S} 1 <= sum_p x_p * (sum_{c ni p} y_c) = sum_c y_c |S n c| <= 3 sum_c y_c.
  // Greedy construction: repeatedly take the conic covering the most uncovered
  // points m; give it y = 1/m.
  { int NS[4]={4,5,6,7};
    for(int ni=0;ni<4;++ni){ int n=NS[ni]; int V=n*n;
      std::vector<Pt> pts; for(int y=0;y<n;++y)for(int x=0;x<n;++x) pts.push_back({x,y});
      std::map<std::string,std::vector<int>> conics;
      for(int a=0;a<V-3;++a)for(int b=a+1;b<V-2;++b)for(int c=b+1;c<V-1;++c){
        i64 D,E,F; std::string key;
        std::vector<int> v;
        if(conic3(pts[a],pts[b],pts[c],&D,&E,&F)){ key="C"+std::to_string(D)+","+std::to_string(E)+","+std::to_string(F);
          for(int p=0;p<V;++p) if((i64)(pts[p].x*pts[p].x+pts[p].y*pts[p].y)+D*pts[p].x+E*pts[p].y+F==0) v.push_back(p); }
        else { std::string ls=line_sig(pts[a],pts[b]);
          // normalise by the same conic key machinery: any of the 3 collinear pairs
          // gives the same line, so recompute from a,c too and use a's,b's
          key=ls; i64 A=0,B=0,C2=0; sscanf(ls.c_str()+1,"%lld,%lld,%lld",&A,&B,&C2);
          for(int p=0;p<V;++p) if(A*pts[p].x+B*pts[p].y+C2==0) v.push_back(p); }
        if((int)v.size()>=4) conics[key]=v; }
      i64 ncirc=0,nline=0; for(auto&kv:conics) if(kv.first[0]=='C') ncirc++; else nline++;
      // greedy cover
      std::vector<char> cov(V,0); i64 uncovered=V; i64 ynum=0,yden=1; // sum y as fraction
      std::vector<std::pair<i64,i64>> ys;
      while(uncovered>0){
        int best=-1,bestm=0;
        for(auto&kv:conics){ int m=0; for(int p:kv.second) if(!cov[p]) m++;
          if(m>bestm){ bestm=m; best=(int)(&kv-&*conics.begin()); } }
        if(best<0||bestm==0) break;
        int m=bestm; ys.push_back({1,m});
        for(int p:conics[std::next(conics.begin(),best)->first]) if(!cov[p]){ cov[p]=1; uncovered--; }
      }
      // sum 1/m over batches (exact fraction)
      auto add=[&](i64 a,i64 b){ i128 N=(i128)ynum*b+(i128)a*yden; i128 D=(i128)yden*b;
        i64 gg=(i64)std::gcd((long long)(N%((i128)1<<62)?(N%((i128)1<<62)):(i64)(N&0x7fffffff)),1LL);
        (void)gg; ynum=(i64)N; yden=(i64)D; i64 g2=std::gcd(std::llabs(ynum),yden); if(g2){ ynum/=g2; yden/=g2; } };
      for(auto&pr:ys) add(pr.first,pr.second);
      // simpler: recompute the sum with int128
      { i64 N=0,D=1; for(auto&pr:ys){ i128 t=(i128)N*pr.second+(i128)pr.first*D; D=(i128)D*pr.second; N=(i64)t;
          i64 g2=std::gcd(std::llabs(N),(i64)D); if(g2){ N/=g2; D=(i64)D/g2; } } ynum=N; yden=D; }
      i64 Kbound_num = 3*ynum, Kbound_den = yden;
      P("  B288 n=%d: conics with >=4 board points: %lld circles + %lld lines = %lld; greedy dual needs %zu batches, sum y = %s -> |S| <= %s\n",
        n,ncirc,nline,(i64)conics.size(),ys.size(),frac(ynum,yden).c_str(),frac(Kbound_num,Kbound_den).c_str());
      // B289: compare with the true K
      i64 Kn=-1;
      if(n<=4) Kn=S4.K; else if(n==5) Kn=S5.K; else if(n==6) Kn=S6.K; else Kn=14;
      P("  B289 n=%d: fractional dual bound = %s, true K_n = %lld, bound is %s (gap %s)\n",
        n,frac(Kbound_num,Kbound_den).c_str(),Kn,
        ((i128)Kbound_num>(i128)Kbound_den*Kn)?"STRICTLY LOOSER":((i128)Kbound_num==(i128)Kbound_den*Kn)?"TIGHT":"INVALID",
        frac(Kbound_num-(i128)Kbound_den*Kn>0?Kbound_num-Kbound_den*Kn:0, Kbound_den).c_str());
      // B290: add the "small circle pencil" constraints -- a second greedy using
      // only conics with 4..5 points (small circles), to see whether they close
      // the gap.
      i64 smallbound_num=0,smallbound_den=1;
      { std::vector<char> c2(V,0); i64 unc2=V; i64 N2=0,D2=1;
        while(unc2>0){ int bm=0; const std::vector<int>* best=nullptr;
          for(auto&kv:conics){ if((int)kv.second.size()>5) continue; int m=0; for(int p:kv.second) if(!c2[p]) m++;
            if(m>bm){ bm=m; best=&kv.second; } }
          if(!best||bm==0) break;
          N2=D2*bm+bm; D2=D2*bm; i64 g2=std::gcd(std::llabs(N2),D2); if(g2){ N2/=g2; D2/=g2; }
          for(int p:*best) if(!c2[p]){ c2[p]=1; unc2--; } }
        smallbound_num=N2; smallbound_den=D2; }
      P("  B290 n=%d: using only conics with 4-5 board points, sum y = %s -> |S| <= %s (small-pencil constraints alone)\n",
        n,frac(smallbound_num,smallbound_den).c_str(),frac(3*smallbound_num,smallbound_den).c_str());
    } }
  // B278 / B279: mixing is not decidable here; report the exact state counts.
  P("  B278/B279: exact state counts (the quantity that controls a 1-point-update chain):\n");
  for(int n=4;n<=6;++n){ Sol& S=(n==4?S4:(n==5?S5:S6));
    P("     n=%d: V=%d, safe sets=%lld, maximal sets=%lld\n",n,n*n,S.n_states,(i64)S.maximals.size()); }
}

// ------------------------------------------------------------------ sec_big
static void sec_big(){
  P("\n## sec_big : B251/B252/B253/B255/B256/B258\n");
  // g0 of the game in which ONLY the quads in E are forbidden.
  auto g0_of=[&](const std::vector<u64>& E,int V)->int{
    return grundy_full(E,V); };
  // ---- n=4: D4 orbits of the 194 quads
  { int n=4,V=16; auto&Q=QQ[4];
    std::vector<std::vector<int>> perms; d4_perms(4,perms);
    std::vector<int> orbOf(Q.size(),-1); int norb=0;
    std::vector<std::vector<u64>> orbits;
    for(size_t i=0;i<Q.size();++i){ if(orbOf[i]>=0) continue;
      u64 q=Q[i]; int ids[4]; mask_ids(q,ids);
      u64 img=0;
      for(int p=0;p<V;++p) if(q>>p&1) img|=u64(1)<<perms[0][p];
      int k=(int)__builtin_popcountll(img); (void)k;
      orbits.push_back({q});
      for(int t=1;t<8;++t){ u64 im2=0;
        for(int ii=0;ii<4;++ii) im2|=u64(1)<<perms[t][ids[ii]];
        orbits.back().push_back(im2); }
      // find already-assigned members
      int target=-1;
      for(size_t j=0;j<orbits.size()-1;++j) for(u64 m:orbits[j]) if(m==img){ target=(int)j; break; }
      if(target>=0){ orbits.pop_back(); }
      else { for(u64 m:orbits.back()){ size_t idx=0; for(size_t z=0;z<Q.size();++z) if(Q[z]==m){ idx=z; break; } orbOf[idx]=(int)orbits.size()-1; } }
    }
    // recompute cleanly: assign orbit id by canonical minimum
    std::vector<u64> canon(Q.size(),0);
    for(size_t i=0;i<Q.size();++i){ int ids[4]; mask_ids(Q[i],ids); u64 best=~u64(0);
      for(int t=0;t<8;++t){ u64 im=0; for(int ii=0;ii<4;++ii) im|=u64(1)<<perms[t][ids[ii]]; best=std::min(best,im); }
      canon[i]=best; }
    std::map<u64,int> oid; for(size_t i=0;i<Q.size();++i) if(!oid.count(canon[i])) oid[canon[i]]=(int)oid.size();
    std::vector<int> oi(Q.size()); for(size_t i=0;i<Q.size();++i) oi[i]=oid[canon[i]];
    P("  n=4: %zu quads in %zu D4 orbits; orbit sizes:",Q.size(),oid.size());
    { std::map<int,int> h; for(size_t i=0;i<Q.size();++i) h[oi[i]]++; for(auto&kv:h) P(" %d",kv.second); P("\n"); }
    int gstd_full=g0_of(QQ[4],V);
    i64 inv=0, inv_minimal=0; int mininv=1<<30;
    std::vector<int> allinv;  // g0 for every non-empty union of orbits
    { int NO=(int)oid.size();
      for(int mask=1;mask<(1<<NO);++mask){ std::vector<u64> E; int sz=0;
        for(int b=0;b<NO;++b) if(mask>>b&1){ for(size_t i=0;i<Q.size();++i) if(oi[i]==b){ E.push_back(Q[i]); sz++; } }
        int g=g0_of(E,V); allinv.push_back(g);
        if(g==gstd_full){ inv++; allinv.push_back(g);
          // minimality: dropping any orbit changes g
          bool minimal=true;
          for(int b=0;b<NO;++b) if(mask>>b&1){ std::vector<u64> E2; int s2=0;
            for(int b2=0;b2<NO;++b2) if((mask>>b2&1)&&(b2!=b)){ for(size_t i=0;i<Q.size();++i) if(oi[i]==b2){ E2.push_back(Q[i]); s2++; } }
            if(g0_of(E2,V)==gstd_full){ minimal=false; break; } }
          if(minimal){ inv_minimal++; if(sz<mininv) mininv=sz; } } } }
    // asymmetric minimal families of size 1..3
    i64 asym_min=1<<30; i64 asym_flip_min=1<<30;
    { int gs1=-1; i64 singles_with_g0=0;
      for(size_t i=0;i<Q.size();++i){ std::vector<u64> E{Q[i]};
        if(g0_of(E,V)==gstd_full) singles_with_g0++; }
      if(singles_with_g0>0) asym_min=1;
      P("  B256 n=%4d: g0(standard)=%d ; g0(no quads)=%d ; g0(single quad q)=%d for %lld/zu of the 194 quads\n",
        n,gstd_full,grundy_full({},V),0,singles_with_g0);
      (void)gs1; }
    { // pairs and (sampled) triples
      i64 pair_g0=0; int pmin=1<<30;
      for(size_t i=0;i<Q.size();++i) for(size_t j=i+1;j<Q.size();++j){
        std::vector<u64> E{Q[i],Q[j]}; if(g0_of(E,V)==gstd_full) pair_g0++; }
      P("  B256 n=4: minimal-size D4-invariant families reproducing g0 = %d (over %zu non-empty orbit unions) ; asymmetric family of size 1 exists: %s\n",
        mininv,allinv.size(), asym_min==1?"YES":"no");
      (void)pair_g0;(void)pmin; }
    // B258: intersection of the D4 orbit sets of the minimal invariant families
    { int NO=(int)oid.size();
      std::vector<int> inter(NO,1); i64 nminfam=0;
      for(int mask=1;mask<(1<<NO);++mask){ std::vector<u64> E; int sz=0;
        for(int b=0;b<NO;++b) if(mask>>b&1){ for(size_t i=0;i<Q.size();++i) if(oi[i]==b){ E.push_back(Q[i]); sz++; } }
        if(g0_of(E,V)!=gstd_full) continue;
        bool minimal=true;
        for(int b=0;b<NO;++b) if(mask>>b&1){ std::vector<u64> E2;
          for(int b2=0;b2<NO;++b2) if((mask>>b2&1)&&(b2!=b)) for(size_t i=0;i<Q.size();++i) if(oi[i]==b2) E2.push_back(Q[i]);
          if(g0_of(E2,V)==gstd_full){ minimal=false; break; } }
        if(!minimal) continue;
        nminfam++;
        for(int b=0;b<NO;++b) if(!(mask>>b&1)) inter[b]=0; }
      int ncom=0; for(int b=0;b<NO;++b) ncom+=inter[b];
      P("  B258 n=4: minimal D4-invariant families reproducing g0 = %lld ; orbits common to ALL of them = %d (of %d)\n",
        nminfam,ncom,NO);
      if(ncom>0) for(int b=0;b<NO;++b) if(inter[b]){ int sz=0; for(size_t i=0;i<Q.size();++i) if(oi[i]==b) sz++;
        P("       common orbit #%d (size %d)\n",b,sz); } }
    // B251/B252/B253/B255: removal from the FULL family
    { i64 s1=0,s1f=0;
      for(size_t i=0;i<Q.size();++i){ std::vector<u64> E{ ~Q[i] }; (void)E; }
      // removal = use every quad except the removed ones
      auto g0_remove=[&](const std::vector<u64>& rm)->int{
        std::vector<u64> keep; for(u64 q:Q){ bool f=false; for(u64 r:rm) if(r==q){ f=true; break; } if(!f) keep.push_back(q); }
        return g0_of(keep,V); };
      for(size_t i=0;i<Q.size();++i){ s1++; if(g0_remove({Q[i]})!=gstd_full) s1f++; }
      P("  B251 n=4: single removals=%lld g0 flips=%lld\n",s1,s1f);
      std::vector<std::string> cs(Q.size());
      for(size_t i=0;i<Q.size();++i){ int ids[4]; mask_ids(Q[i],ids); cs[i]=quad_conic(PT[4].data(),ids); }
      i64 p2=0,p2f=0,cl=0,clf=0,sc=0,scf=0;
      for(size_t i=0;i<Q.size();++i) for(size_t j=i+1;j<Q.size();++j){
        p2++; int g=g0_remove({Q[i],Q[j]});
        if(g!=gstd_full) p2f++;
        if(cs[i]==cs[j]){ cl++; if(g!=gstd_full) clf++; } else { sc++; if(g!=gstd_full) scf++; } }
      P("  B252/B253 n=4: all %lld pair removals, g0 flips=%lld; same-conic pairs=%lld (flip %lld); scattered pairs=%lld (flip %lld)\n",
        p2,p2f,cl,clf,sc,scf);
      // triples: all same-conic triples, plus a deterministic sample of scattered ones
      i64 t3=0,t3f=0,cl3=0,cl3f=0;
      for(size_t i=0;i<Q.size();++i) for(size_t j=i+1;j<Q.size();++j) if(cs[i]==cs[j])
        for(size_t k=j+1;k<Q.size();++k) if(cs[k]==cs[j]){
          t3++; cl3++; if(g0_remove({Q[i],Q[j],Q[k]})!=gstd_full){ t3f++; cl3f++; } }
      i64 sampled=0,sampledf=0;
      for(size_t i=0;i<Q.size();++i) for(size_t j=i+1;j<Q.size();++j) if(cs[i]!=cs[j])
        for(size_t k=j+1;k<Q.size();++k) if(cs[k]!=cs[i]&&cs[k]!=cs[j]){
          if(((i*7919+j*104729+k)%50)!=0) continue;
          sampled++; if(g0_remove({Q[i],Q[j],Q[k]})!=gstd_full) sampledf++; }
      P("  B253 n=4: same-conic triples=%lld (g0 flips=%lld); sampled scattered triples=%lld (g0 flips=%lld)\n",
        cl3,cl3f,sampled,sampledf);
      (void)t3;(void)t3f; }
  }
  // ---- n=5: single removals (826) -- the decisive test for B251
  { int n=5,V=25; auto&Q=QQ[5];
    auto g0_remove5=[&](u64 q)->int{ std::vector<u64> keep; for(u64 r:Q) if(r!=q) keep.push_back(r);
      return g0_of(keep,V); };
    i64 s1=0,s1f=0; std::string wit;
    for(size_t i=0;i<Q.size();++i){ s1++; int g=g0_remove5(Q[i]);
      if(g!=S5.g0){ s1f++;
        if(wit.empty()){ int ids[4]; mask_ids(Q[i],ids); wit="removed quad "+occ_str(Q[i],n)+" -> g0="+std::to_string(g)+" (standard "+std::to_string(S5.g0)+")"; } } }
    P("  B251 n=5: single removals=%lld g0 flips=%lld  %s\n",s1,s1f,wit.c_str());
  }
}

int main(int argc,char**argv){
  t0=now();
  std::string which=(argc>1)?argv[1]:"all";
  OUT=fopen("/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/round4_b228e.txt","w");
  if(!OUT){ fprintf(stderr,"cannot open output\n"); return 1; }
  P("=== round4_b228e : draft 4 (decisive weakening) ===\n\n");
  sec_core();
  if(which=="all"||which=="census") sec_census();
  if(which=="all"||which=="chain")  sec_chain();
  if(which=="all"||which=="switch") sec_switch();
  if(which=="all"||which=="ctx")    sec_ctx();
  if(which=="all"||which=="proof")  sec_proof();
  if(which=="all"||which=="u")      sec_u();
  if(which=="all"||which=="lambda") sec_lambda();
  if(which=="all"||which=="geom")   sec_geom();
  if(which=="all"||which=="big")    sec_big();
  P("\n=== done in %.1f s ===\n",now()-t0);
  fclose(OUT);
  return 0;
}
