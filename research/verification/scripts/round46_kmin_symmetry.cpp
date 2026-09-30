// Round46 exact minimal-maximal search. New suffix count upper bound.
// Derived from scripts/analysis/fact_kmin_cover_bound.cpp; shared file unchanged.
// Usage:
//   g++ -O3 -std=c++17 scripts/analysis/fact_kmin_cover_bound.cpp -o kmin_cover
//   ./kmin_cover <n> <k> [time_limit_seconds]
// Supports n<=10. A time limit of 0 means unlimited.
// The search is exact when "complete":true.
#include <bits/stdc++.h>
using namespace std;

struct Mask { uint64_t lo=0, hi=0; };
static inline void mor(Mask& x, Mask y){ x.lo|=y.lo; x.hi|=y.hi; }
static inline bool mhas(Mask x,int p){ return p<64 ? ((x.lo>>p)&1ULL) : ((x.hi>>(p-64))&1ULL); }
static inline void mset(Mask& x,int p){ if(p<64)x.lo|=1ULL<<p; else x.hi|=1ULL<<(p-64); }
static inline int mpc(Mask x){ return __builtin_popcountll(x.lo)+__builtin_popcountll(x.hi); }
static inline Mask mandnot(Mask x,Mask y){ return {x.lo&~y.lo,x.hi&~y.hi}; }

static Mask cmask[100][100][100];
static unsigned char ccount[100][100][100];
static Mask pair_suf[100][100][101], one_suf[100][101], tri_suf[101];
static unsigned char pair_best[100][100][101], one_best[100][101], tri_best[101];

static int N,P,K,max_completion;
static long long forbidden_quads, completion_incidence;
static double limit_s;
static chrono::steady_clock::time_point started;
static bool complete_search=true, found=false;
static vector<int> occ,witness;
static Mask occ_mask,blocked;
static int score;
static long long nodes[101], cover_prunes[101], score_prunes[101];

static inline int px(int p){ return p%N; }
static inline int py(int p){ return p/N; }

static long long det4(int p0,int p1,int p2,int p3){
  int ps[4]={p0,p1,p2,p3};
  long long A[4][4];
  for(int i=0;i<4;i++){
    long long x=px(ps[i]),y=py(ps[i]);
    A[i][0]=x*x+y*y; A[i][1]=x; A[i][2]=y; A[i][3]=1;
  }
  auto d3=[](long long a,long long b,long long c,long long d,long long e,long long f,
             long long g,long long h,long long i){
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
  };
  long long out=0;
  for(int j=0;j<4;j++){
    long long c[3][3]; int jj2=0;
    for(int jj=0;jj<4;jj++) if(jj!=j){
      for(int i=1;i<4;i++) c[i-1][jj2]=A[i][jj];
      ++jj2;
    }
    long long cof=d3(c[0][0],c[0][1],c[0][2],c[1][0],c[1][1],c[1][2],
                     c[2][0],c[2][1],c[2][2]);
    out += (j%2?-1:1)*A[0][j]*cof;
  }
  return out;
}

static inline Mask getm(int a,int b,int c){
  int v[3]={a,b,c}; sort(v,v+3); return cmask[v[0]][v[1]][v[2]];
}
static inline int getc(int a,int b,int c){
  int v[3]={a,b,c}; sort(v,v+3); return ccount[v[0]][v[1]][v[2]];
}
static inline int C3(int n){ return n<3?0:n*(n-1)*(n-2)/6; }

static Mask allmask(){
  Mask m{};
  if(P<64) m.lo=(1ULL<<P)-1;
  else if(P==64) m.lo=~0ULL;
  else { m.lo=~0ULL; m.hi=(1ULL<<(P-64))-1; }
  return m;
}
static Mask prefixmask(int from){
  Mask m{};
  if(from<=0) return m;
  if(from<64) m.lo=(1ULL<<from)-1; else m.lo=~0ULL;
  if(from>64){ int h=from-64; m.hi=(1ULL<<h)-1; }
  return m;
}

static void build(){
  forbidden_quads=completion_incidence=0;
  max_completion=0;
  for(int a=0;a<P;a++) for(int b=a+1;b<P;b++)
    for(int c=b+1;c<P;c++) for(int d=c+1;d<P;d++){
      if(det4(a,b,c,d)!=0) continue;
      ++forbidden_quads;
      int v[4]={a,b,c,d};
      for(int omit=0;omit<4;omit++){
        int t[3],q=0;
        for(int i=0;i<4;i++) if(i!=omit) t[q++]=v[i];
        sort(t,t+3);
        mset(cmask[t[0]][t[1]][t[2]],v[omit]);
        ++ccount[t[0]][t[1]][t[2]];
        ++completion_incidence;
      }
    }
  for(int a=0;a<P;a++) for(int b=a+1;b<P;b++) for(int c=b+1;c<P;c++)
    max_completion=max(max_completion,(int)ccount[a][b][c]);

  for(int a=0;a<P;a++) for(int b=a+1;b<P;b++){
    Mask cur{}; unsigned char best=0;
    for(int f=P-1;f>=0;f--){
      if(f!=a && f!=b){ mor(cur,getm(a,b,f));best=max(best,(unsigned char)getc(a,b,f));}
      pair_suf[a][b][f]=cur;pair_best[a][b][f]=best;
    }
  }
  for(int a=0;a<P;a++){
    Mask cur{};unsigned char best=0;
    for(int f=P-1;f>=0;f--){
      if(f!=a) for(int q=f+1;q<P;q++) if(q!=a){mor(cur,getm(a,f,q));best=max(best,(unsigned char)getc(a,f,q));}
      one_suf[a][f]=cur;one_best[a][f]=best;
    }
  }
  Mask cur{};unsigned char best=0;
  for(int f=P-1;f>=0;f--){
    for(int q=f+1;q<P;q++) for(int r=q+1;r<P;r++){mor(cur,getm(f,q,r));best=max(best,(unsigned char)getc(f,q,r));}
    tri_suf[f]=cur;tri_best[f]=best;
  }
}

static bool coverage_possible(int from,int need){
  Mask possible=blocked;
  if(need>=1){
    for(int i=0;i<(int)occ.size();i++) for(int j=i+1;j<(int)occ.size();j++){
      int a=occ[i],b=occ[j]; if(a>b) swap(a,b);
      mor(possible,pair_suf[a][b][from]);
    }
  }
  if(need>=2) for(int a:occ) mor(possible,one_suf[a][from]);
  if(need>=3) mor(possible,tri_suf[from]);

  Mask fixed=mandnot(prefixmask(from),occ_mask);
  if(mpc(mandnot(fixed,possible))!=0) return false;

  Mask unselected=mandnot(allmask(),occ_mask);
  return mpc(mandnot(unselected,possible))<=need;
}

static inline bool timeout(){
  if(limit_s<=0) return false;
  return chrono::duration<double>(chrono::steady_clock::now()-started).count()>limit_s;
}

static void dfs(int from,int need){
  if(!complete_search || found) return;
  int depth=(int)occ.size();
  ++nodes[depth];
  if((nodes[depth]&((1<<20)-1))==0 && timeout()){ complete_search=false; return; }

  int total=C3(K),cur=C3(depth);
  int upper=score;
  if(need>=1)for(int i=0;i<depth;i++)for(int j=i+1;j<depth;j++)upper+=need*pair_best[occ[i]][occ[j]][from];
  if(need>=2)for(int a:occ)upper+=need*(need-1)/2*one_best[a][from];
  if(need>=3)upper+=C3(need)*tri_best[from];
  assert(upper<=score+(total-cur)*max_completion);
  if(upper < P-K){
    ++score_prunes[depth];
    return;
  }
  if(!coverage_possible(from,need)){
    ++cover_prunes[depth];
    return;
  }
  if(need==0){
    if(mpc(blocked)==P-K){ found=true; witness=occ; }
    return;
  }

  for(int p=from;p<=P-need;p++){
    // Proven orbit reduction: round46 embedding certificate excludes all 8x8 windows.
    // Rotate a full-span axis vertically and reflect the first-row minimum into x<=4.
    if(N==9 && K==8 && depth==0 && p>4) break;
    if(mhas(blocked,p)) continue;
    Mask oldb=blocked, oldo=occ_mask;
    int olds=score;
    for(int i=0;i<depth;i++) for(int j=i+1;j<depth;j++){
      mor(blocked,getm(occ[i],occ[j],p));
      score+=getc(occ[i],occ[j],p);
    }
    occ.push_back(p); mset(occ_mask,p);
    dfs(p+1,need-1);
    occ.pop_back(); blocked=oldb; occ_mask=oldo; score=olds;
    if(!complete_search || found) return;
  }
}

static void printv(const vector<int>& v){
  cout<<"[";
  for(size_t i=0;i<v.size();i++){ if(i) cout<<","; cout<<v[i]; }
  cout<<"]";
}
static void printa(long long* a,int last){
  cout<<"[";
  for(int i=0;i<=last;i++){ if(i) cout<<","; cout<<a[i]; }
  cout<<"]";
}

int main(int argc,char**argv){
  if(argc<3){
    cerr<<"usage: "<<argv[0]<<" <n<=10> <k> [time_limit_seconds]\n";
    return 2;
  }
  N=atoi(argv[1]); K=atoi(argv[2]); P=N*N;
  limit_s=argc>=4?atof(argv[3]):0.0;
  if(N<1 || N>10 || K<0 || K>P) return 2;

  build();
  started=chrono::steady_clock::now();
  dfs(0,K);
  double seconds=chrono::duration<double>(chrono::steady_clock::now()-started).count();
  long long total_nodes=0; for(int i=0;i<=K;i++) total_nodes+=nodes[i];

  cout<<"{\"n\":"<<N<<",\"k\":"<<K
      <<",\"orbit_reduction\":\"n9 k8 first occupied ID <=4; requires 408-set embedding certificate\""
      <<",\"score_upper_bound\":\"suffix-conditioned triple counts\",\"complete\":"<<(complete_search?"true":"false")
      <<",\"found\":"<<(found?"true":"false")
      <<",\"forbidden_quads\":"<<forbidden_quads
      <<",\"triple_completion_incidence\":"<<completion_incidence
      <<",\"max_completion\":"<<max_completion
      <<",\"nodes\":"<<total_nodes
      <<",\"seconds\":"<<fixed<<setprecision(6)<<seconds
      <<",\"nodes_by_depth\":"; printa(nodes,K);
  cout<<",\"coverage_prunes\":"; printa(cover_prunes,K);
  cout<<",\"score_prunes\":"; printa(score_prunes,K);
  cout<<",\"witness\":"; printv(witness);
  cout<<"}\n";
  return complete_search?0:3;
}
