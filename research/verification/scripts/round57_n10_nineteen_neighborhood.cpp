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

static int N,P,K,max_completion,root_only=-1;
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


static bool timeout(){return limit_s>0 && chrono::duration<double>(chrono::steady_clock::now()-started).count()>limit_s;}

// Round57: exact bounded deletion neighborhoods around a verified 19-set.
// It proves only local exclusions when each radius is complete.
static vector<int> seed={9,15,16,18,20,22,30,36,44,58,62,65,67,70,71,87,91,93,97}, retained, answer;
static vector<int> removed;
static long long neighborhoods=0, extension_nodes=0;
static bool local_complete=true, improved=false;
static int current_radius=0, complete_radius=0;
static void grow(Mask occupied,Mask forbidden,int from,int need){
  if(improved || !local_complete)return;
  ++extension_nodes;
  if((extension_nodes&65535)==0 && timeout()) {local_complete=false;return;}
  vector<int> available;
  for(int p=from;p<P;p++)if(!mhas(occupied,p)&&!mhas(forbidden,p))available.push_back(p);
  if((int)available.size()<need)return;
  if(need==0){improved=true;answer=retained;return;}
  for(int p:available){
    Mask next=forbidden;
    for(int i=0;i<(int)retained.size();i++)for(int j=i+1;j<(int)retained.size();j++)mor(next,getm(retained[i],retained[j],p));
    Mask occnext=occupied;mset(occnext,p);retained.push_back(p);
    grow(occnext,next,p+1,need-1);retained.pop_back();
    if(improved || !local_complete)return;
  }
}
static void deletions(int from,int need){
  if(improved || !local_complete)return;
  if(need==0){
    ++neighborhoods;
    if((neighborhoods&1023)==0 && timeout()){local_complete=false;return;}
    retained.clear();Mask occupied{},forbidden{};
    for(int i=0;i<(int)seed.size();i++)if(find(removed.begin(),removed.end(),i)==removed.end()){
      retained.push_back(seed[i]);mset(occupied,seed[i]);
    }
    for(int i=0;i<(int)retained.size();i++)for(int j=i+1;j<(int)retained.size();j++)for(int k=j+1;k<(int)retained.size();k++)mor(forbidden,getm(retained[i],retained[j],retained[k]));
    grow(occupied,forbidden,0,20-retained.size());return;
  }
  for(int i=from;i<=(int)seed.size()-need;i++){
    removed.push_back(i);deletions(i+1,need-1);removed.pop_back();
    if(improved || !local_complete)return;
  }
}
int main(int argc,char**argv){
 N=10;P=100;K=20;limit_s=argc>1?atof(argv[1]):600;
 build();started=chrono::steady_clock::now();
 for(current_radius=1;current_radius<=8;current_radius++){
   deletions(0,current_radius);
   if(improved || !local_complete)break;
   complete_radius=current_radius;
 }
 cout<<"{\"n\":10,\"target\":20,\"found\":"<<(improved?"true":"false")
     <<",\"local_complete\":"<<(local_complete?"true":"false")<<",\"complete_deletion_radius\":"<<complete_radius
     <<",\"active_radius\":"<<current_radius<<",\"subsets_examined\":"<<neighborhoods
     <<",\"extension_nodes\":"<<extension_nodes<<",\"seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-started).count()
     <<",\"seed_ids\":[";
 for(size_t i=0;i<seed.size();i++){if(i)cout<<",";cout<<seed[i];}
 cout<<"],\"witness_ids\":[";
 sort(answer.begin(),answer.end());
 for(size_t i=0;i<answer.size();i++){if(i)cout<<",";cout<<answer[i];}
 cout<<"]}\n";
 return local_complete?0:3;
}
