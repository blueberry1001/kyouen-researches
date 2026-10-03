// Exact residual intersection layer for the almost-safe 20-set U.
// Usage: executable [time_limit_seconds=300]; zero means unlimited.
// See saturation-20261003-extra.md for its reduction from the 19-set search.
#include <bits/stdc++.h>
using namespace std;

struct Mask { uint64_t lo=0, hi=0; };
static inline void mor(Mask& x, Mask y){ x.lo|=y.lo; x.hi|=y.hi; }
static inline bool mhas(Mask x,int p){ return p<64 ? ((x.lo>>p)&1ULL) : ((x.hi>>(p-64))&1ULL); }
static inline void mset(Mask& x,int p){ if(p<64)x.lo|=1ULL<<p; else x.hi|=1ULL<<(p-64); }

static Mask cmask[100][100][100];
static constexpr int N=10, P=100;
static double limit_s;
static chrono::steady_clock::time_point started;

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
// Enumerate each forbidden quadruple and cache its four triple completions.
static void build(){
  for(int a=0;a<P;a++) for(int b=a+1;b<P;b++)
    for(int c=b+1;c<P;c++) for(int d=c+1;d<P;d++){
      if(det4(a,b,c,d)!=0) continue;
      int v[4]={a,b,c,d};
      for(int omit=0;omit<4;omit++){
        int t[3],q=0;
        for(int i=0;i<4;i++) if(i!=omit) t[q++]=v[i];
        mset(cmask[t[0]][t[1]][t[2]],v[omit]);
      }
    }
}

static bool timeout(){return limit_s>0 && chrono::duration<double>(chrono::steady_clock::now()-started).count()>limit_s;}


// Complete the only intersection layer not excluded by the 19-set U\{25}:
// a safe 20-set meeting U in >=10 points must meet U in exactly 10, contain
// 25, and omit at least one of 59,62,83. Remaining points must be outside U.
static vector<int> U={2,6,16,18,21,25,32,35,40,59,62,67,74,77,78,80,81,83,97,99};
static vector<int> choices, retained, answer;
static bool universe[100]{};
static bool done=true, found20=false;
static long long subsets=0, skipped=0, extension_nodes=0;
static void grow(Mask occupied,Mask forbidden,int from,int need){
 if(!done||found20)return;++extension_nodes;
 if((extension_nodes&65535)==0&&timeout()){done=false;return;}
 if(need==0){found20=true;answer=retained;return;}
 vector<int>available;for(int p=from;p<P;p++)if(!universe[p]&&!mhas(occupied,p)&&!mhas(forbidden,p))available.push_back(p);
 if((int)available.size()<need)return;
 for(int p:available){Mask next=forbidden;for(int i=0;i<(int)retained.size();i++)for(int j=i+1;j<(int)retained.size();j++)mor(next,getm(retained[i],retained[j],p));Mask nextocc=occupied;mset(nextocc,p);retained.push_back(p);grow(nextocc,next,p+1,need-1);retained.pop_back();if(!done||found20)return;}
}
static void choose(int from,int need){
 if(!done||found20)return;
 if(need==0){
  bool q=true;for(int p:{59,62,83})q&=find(retained.begin(),retained.end(),p)!=retained.end();
  if(q){++skipped;return;}++subsets;
  Mask occupied{},forbidden{};for(int p:retained)mset(occupied,p);
  for(int i=0;i<10;i++)for(int j=i+1;j<10;j++)for(int k=j+1;k<10;k++)mor(forbidden,getm(retained[i],retained[j],retained[k]));
  assert((occupied.lo&forbidden.lo)==0&&(occupied.hi&forbidden.hi)==0);
  grow(occupied,forbidden,0,10);return;
 }
 for(int i=from;i<=(int)choices.size()-need;i++){retained.push_back(choices[i]);choose(i+1,need-1);retained.pop_back();if(!done||found20)return;}
}
int main(int argc,char**argv){limit_s=argc>1?atof(argv[1]):300;build();for(int p:U){universe[p]=true;if(p!=25)choices.push_back(p);}started=chrono::steady_clock::now();retained={25};choose(0,9);
 cout<<"{\"n\":10,\"target\":20,\"found\":"<<(found20?"true":"false")<<",\"complete\":"<<(done?"true":"false")<<",\"intersection_layer\":10,\"required_point\":25,\"subsets_examined\":"<<subsets<<",\"unsafe_subsets_skipped\":"<<skipped<<",\"extension_nodes\":"<<extension_nodes<<",\"seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<",\"universe_ids\":[";for(int i=0;i<20;i++){if(i)cout<<",";cout<<U[i];}cout<<"],\"witness_ids\":[";sort(answer.begin(),answer.end());for(int i=0;i<(int)answer.size();i++){if(i)cout<<",";cout<<answer[i];}cout<<"]}\n";return done?0:3;}
