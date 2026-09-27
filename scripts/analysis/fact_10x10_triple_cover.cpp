// Minimal maximal via triple-cover pruning for k<=8 on 10x10.
// A k-set S is maximal iff every point outside S is a completion of some
// 3-subset of S. We precompute triple -> completion point set.
#include <bits/stdc++.h>
using namespace std;

static const int PTS = 100;
static inline int pid(int x, int y) { return y * 10 + x; }
static inline int px(int p) { return p % 10; }
static inline int py(int p) { return p / 10; }

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

// map from sorted triple (a<b<c) to bitmask of completion points
static map<array<int,3>, bitset<PTS>> triple_comp;

static void build(){
  for(int a=0;a<PTS;a++) for(int b=a+1;b<PTS;b++) for(int c=b+1;c<PTS;c++) for(int d=c+1;d<PTS;d++){
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

static void print_set(const vector<int>&s){
  cout<<"["; for(int i=0;i<(int)s.size();i++){ if(i) cout<<", "; cout<<s[i]; } cout<<"]";
}

static void search_k(int k, int time_limit_s, int max_keep){
  auto t0=chrono::steady_clock::now();
  auto elapsed=[&](){ return chrono::duration<double>(chrono::steady_clock::now()-t0).count(); };
  vector<vector<int>> found;
  long long nodes=0;
  bool complete=true;
  vector<int> occ;
  bitset<PTS> in;

  function<void(int)> dfs=[&](int from){
    if(!complete) return;
    nodes++;
    if(elapsed()>time_limit_s){ complete=false; return; }
    int need = k - (int)occ.size();
    if(need==0){
      // compute blocked set; reject if any triple is completed inside occ (unsafe)
      bitset<PTS> blocked;
      bool safe=true;
      for(int i=0;i<(int)occ.size() && safe;i++) for(int j=i+1;j<(int)occ.size() && safe;j++) for(int l=j+1;l<(int)occ.size() && safe;l++){
        array<int,3> t{occ[i],occ[j],occ[l]};
        auto it=triple_comp.find(t);
        if(it!=triple_comp.end()){
          blocked |= it->second;
          for(int m=0;m<(int)occ.size();m++) if(it->second.test(occ[m])){ safe=false; break; }
        }
      }
      if(!safe) return;
      // all points not in occ must be blocked
      bool ok=true;
      for(int p=0;p<PTS;p++) if(!in[p] && !blocked[p]){ ok=false; break; }
      if(ok && (int)found.size()<max_keep) found.push_back(occ);
      return;
    }
    for(int p=from;p<=PTS-need;p++){
      // optional prune: remaining points must be enough
      occ.push_back(p); in[p]=1;
      dfs(p+1);
      occ.pop_back(); in[p]=0;
      if(!complete) return;
      if(!found.empty()) return; // first hit is enough for existence
    }
  };
  dfs(0);
  cout<<"{\"k\":"<<k<<",\"complete\":"<<(complete?"true":"false")
      <<",\"nodes\":"<<nodes<<",\"seconds\":"<<elapsed()
      <<",\"n_found\":"<<found.size()<<",\"sets\":[";
  for(int i=0;i<(int)found.size();i++){ if(i) cout<<", "; print_set(found[i]); }
  cout<<"]}\n";
}

int main(int argc,char**argv){
  ios::sync_with_stdio(false); cin.tie(nullptr);
  int k = argc>1? atoi(argv[1]): 6;
  int tl = argc>2? atoi(argv[2]): 600;
  cerr<<"building triple cover...\n";
  build();
  cerr<<"triples="<<triple_comp.size()<<"\n";
  search_k(k, tl, 5);
  return 0;
}
