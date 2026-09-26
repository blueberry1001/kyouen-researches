// K_min for general small n using triple-cover, plus targeted 10x10 k=7..9
#include <bits/stdc++.h>
using namespace std;

static int n, pts;
static inline int pid(int x,int y){ return y*n+x; }
static inline int px(int p){ return p%n; }
static inline int py(int p){ return p/n; }

static long long det4(int x0,int y0,int x1,int y1,int x2,int y2,int x3,int y3){
  auto s=[&](int x,int y)->long long{return 1LL*x*x+1LL*y*y;};
  long long A[4][4]={{s(x0,y0),x0,y0,1},{s(x1,y1),x1,y1,1},{s(x2,y2),x2,y2,1},{s(x3,y3),x3,y3,1}};
  auto d3=[&](long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h,long long i){
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
  };
  long long det=0;
  for(int j=0;j<4;j++){
    long long c[3][3]; int cj=0;
    for(int jj=0;jj<4;jj++) if(jj!=j){c[0][cj]=A[1][jj];c[1][cj]=A[2][jj];c[2][cj]=A[3][jj];cj++;}
    long long cof=d3(c[0][0],c[0][1],c[0][2],c[1][0],c[1][1],c[1][2],c[2][0],c[2][1],c[2][2]);
    if(j%2==0) det+=A[0][j]*cof; else det-=A[0][j]*cof;
  }
  return det;
}

static map<array<int,3>, bitset<128>> triple_comp;

static void build(){
  triple_comp.clear();
  for(int a=0;a<pts;a++) for(int b=a+1;b<pts;b++) for(int c=b+1;c<pts;c++) for(int d=c+1;d<pts;d++){
    if(det4(px(a),py(a),px(b),py(b),px(c),py(c),px(d),py(d))==0){
      int v[4]={a,b,c,d};
      for(int i=0;i<4;i++){
        array<int,3> t{}; int k=0;
        for(int j=0;j<4;j++) if(j!=i) t[k++]=v[j];
        triple_comp[t].set(v[i]);
      }
    }
  }
}

static bool search_k(int k, int time_limit_s, vector<int>& out, long long& nodes, bool& complete){
  auto t0=chrono::steady_clock::now();
  auto elapsed=[&](){ return chrono::duration<double>(chrono::steady_clock::now()-t0).count(); };
  vector<int> occ;
  bitset<128> in;
  complete=true;
  bool found=false;
  function<void(int)> dfs=[&](int from){
    if(found || !complete) return;
    nodes++;
    if(elapsed()>time_limit_s){ complete=false; return; }
    if((int)occ.size()==k){
      bitset<128> blocked;
      for(int i=0;i<k;i++) for(int j=i+1;j<k;j++) for(int l=j+1;l<k;l++){
        array<int,3> t{occ[i],occ[j],occ[l]};
        auto it=triple_comp.find(t);
        if(it!=triple_comp.end()) blocked |= it->second;
      }
      bool ok=true;
      for(int p=0;p<pts;p++) if(!in[p] && !blocked[p]){ ok=false; break; }
      if(ok){ out=occ; found=true; }
      return;
    }
    int need=k-(int)occ.size();
    for(int p=from;p<=pts-need;p++){
      occ.push_back(p); in[p]=1;
      dfs(p+1);
      occ.pop_back(); in[p]=0;
      if(found || !complete) return;
    }
  };
  dfs(0);
  return found;
}

int main(int argc,char**argv){
  ios::sync_with_stdio(false); cin.tie(nullptr);
  n = argc>1? atoi(argv[1]): 7;
  pts = n*n;
  int kmin_start = argc>2? atoi(argv[2]): 4;
  int kmax = argc>3? atoi(argv[3]): 12;
  int tl = argc>4? atoi(argv[4]): 300;
  cerr << "n="<<n<<" building...\n";
  build();
  cerr << "triples="<<triple_comp.size()<<"\n";
  for(int k=kmin_start;k<=kmax;k++){
    vector<int> out; long long nodes=0; bool complete=true;
    cerr << "k="<<k<<"...\n";
    bool ok=search_k(k, tl, out, nodes, complete);
    cout << "{\"n\":"<<n<<",\"k\":"<<k<<",\"found\":"<<(ok?"true":"false")
         <<",\"complete\":"<<(complete?"true":"false")
         <<",\"nodes\":"<<nodes<<",\"set\":[";
    for(int i=0;i<(int)out.size();i++){ if(i) cout<<", "; cout<<out[i]; }
    cout<<"]}\n";
    if(ok) break;
    if(!complete) break;
  }
  return 0;
}
