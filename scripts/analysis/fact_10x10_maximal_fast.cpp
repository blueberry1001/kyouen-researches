// Fast minimal-maximal safe set search on 10x10 using bitsets.
// Modes: shrink | exact_k <k> | spectrum
#include <bits/stdc++.h>
using namespace std;

static const int N = 10;
static const int PTS = 100;

static inline int pid(int x, int y) { return y * N + x; }
static inline int px(int p) { return p % N; }
static inline int py(int p) { return p / N; }

static long long det4(int x0,int y0,int x1,int y1,int x2,int y2,int x3,int y3){
  auto s=[&](int x,int y)->long long{return 1LL*x*x+1LL*y*y;};
  long long A[4][4] = {
    {s(x0,y0), x0, y0, 1},
    {s(x1,y1), x1, y1, 1},
    {s(x2,y2), x2, y2, 1},
    {s(x3,y3), x3, y3, 1},
  };
  auto d3=[&](long long m00,long long m01,long long m02,
              long long m10,long long m11,long long m12,
              long long m20,long long m21,long long m22){
    return m00*(m11*m22-m12*m21)-m01*(m10*m22-m12*m20)+m02*(m10*m21-m11*m20);
  };
  long long det=0;
  for(int j=0;j<4;j++){
    long long c[3][3]; int cj=0;
    for(int jj=0;jj<4;jj++) if(jj!=j){ c[0][cj]=A[1][jj]; c[1][cj]=A[2][jj]; c[2][cj]=A[3][jj]; cj++; }
    long long cof=d3(c[0][0],c[0][1],c[0][2],c[1][0],c[1][1],c[1][2],c[2][0],c[2][1],c[2][2]);
    if(j%2==0) det += A[0][j]*cof; else det -= A[0][j]*cof;
  }
  return det;
}

struct Q { int a,b,c,d; };

static vector<Q> quads;
// For each unordered pair, list of the two completion points for each quad? better:
// for each pair index, vector of other-two pairs (as two points).
static vector<vector<array<int,2>>> pair_blocks; // pair_id -> list of {u,v} such that {p,q,u,v} forbidden

static inline int pair_id(int a,int b){ if(a>b) swap(a,b); return a*PTS + b; }

static void build(){
  quads.clear();
  for(int a=0;a<PTS;a++) for(int b=a+1;b<PTS;b++) for(int c=b+1;c<PTS;c++) for(int d=c+1;d<PTS;d++){
    if(det4(px(a),py(a),px(b),py(b),px(c),py(c),px(d),py(d))==0) quads.push_back({a,b,c,d});
  }
  pair_blocks.assign(PTS*PTS, {});
  for(auto&q:quads){
    int v[4]={q.a,q.b,q.c,q.d};
    for(int i=0;i<4;i++) for(int j=i+1;j<4;j++){
      array<int,2> oth{}; int k=0;
      for(int t=0;t<4;t++) if(t!=i && t!=j) oth[k++]=v[t];
      pair_blocks[pair_id(v[i],v[j])].push_back(oth);
    }
  }
}

static bool safe_add(const vector<int>&occ, int p, const char*in){
  for(int x:occ){
    int a=x,b=p; if(a>b) swap(a,b);
    for(auto&oth: pair_blocks[pair_id(a,b)]){
      if(in[oth[0]] && in[oth[1]]) return false;
    }
  }
  return true;
}

static bool is_maximal(const vector<int>&occ){
  char in[PTS]; memset(in,0,sizeof(in));
  for(int x:occ) in[x]=1;
  for(int p=0;p<PTS;p++){
    if(in[p]) continue;
    if(safe_add(occ, p, in)) return false;
  }
  return true;
}

static int mobility(const vector<int>&occ){
  char in[PTS]; memset(in,0,sizeof(in));
  for(int x:occ) in[x]=1;
  int m=0;
  for(int p=0;p<PTS;p++) if(!in[p] && safe_add(occ, p, in)) m++;
  return m;
}

static void print_set(const vector<int>&s){
  cout << "[";
  for(int i=0;i<(int)s.size();i++){ if(i) cout << ", "; cout << s[i]; }
  cout << "]";
}

static void cmd_shrink(){
  // Greedy maximal, then try to drop points while remaining maximal.
  vector<int> g;
  char in[PTS]; memset(in,0,sizeof(in));
  for(int p=0;p<PTS;p++) if(safe_add(g,p,in)){ g.push_back(p); in[p]=1; }
  bool changed=true;
  while(changed){
    changed=false;
    memset(in,0,sizeof(in));
    for(int x:g) in[x]=1;
    for(int p=0;p<PTS;p++) if(!in[p] && safe_add(g,p,in)){ g.push_back(p); in[p]=1; changed=true; break; }
  }
  cerr << "greedy size=" << g.size() << " mobility=" << mobility(g) << "\n";
  // local search: try remove each point
  vector<int> best=g;
  for(int round=0;round<20;round++){
    bool improved=false;
    for(int i=(int)best.size()-1;i>=0;i--){
      vector<int> cand=best;
      cand.erase(cand.begin()+i);
      if(is_maximal(cand) && cand.size()<best.size()){
        best=cand; improved=true; break;
      }
    }
    if(!improved) break;
  }
  cerr << "shrunk size=" << best.size() << "\n";
  cout << "{\"method\":\"shrink\",\"greedy\": " << g.size() << ",\"shrunk\": " << best.size()
       << ",\"set\": "; print_set(best); cout << "}\n";
}

static void cmd_exact_k(int k, int time_limit_s=120, int max_keep=20){
  auto t0=chrono::steady_clock::now();
  auto elapsed=[&](){ return chrono::duration<double>(chrono::steady_clock::now()-t0).count(); };
  vector<vector<int>> found;
  long long nodes=0;
  bool complete=true;
  vector<int> occ;
  char in[PTS]; memset(in,0,sizeof(in));

  function<void(int,int)> dfs = [&](int from, int need){
    if(!complete) return;
    nodes++;
    if(elapsed()>time_limit_s){ complete=false; return; }
    if(need==0){
      if(is_maximal(occ) && (int)found.size()<max_keep) found.push_back(occ);
      return;
    }
    for(int p=from; p<=PTS-need; p++){
      if(!safe_add(occ, p, in)) continue;
      occ.push_back(p); in[p]=1;
      dfs(p+1, need-1);
      occ.pop_back(); in[p]=0;
      if(!complete) return;
      if(!found.empty() && k<=5) return; // first witness enough for min-size claim at small k
    }
  };
  dfs(0,k);
  cout << "{\"k\": " << k << ", \"complete\": " << (complete?"true":"false")
       << ", \"nodes\": " << nodes << ", \"seconds\": " << elapsed()
       << ", \"n_found\": " << found.size() << ", \"sets\": [";
  for(int i=0;i<(int)found.size();i++){ if(i) cout << ", "; print_set(found[i]); }
  cout << "]}\n";
}

int main(int argc,char**argv){
  ios::sync_with_stdio(false); cin.tie(nullptr);
  string mode = argc>1? argv[1]: "shrink";
  cerr << "building...\n";
  build();
  cerr << "forbidden=" << quads.size() << "\n";
  if(mode=="shrink") cmd_shrink();
  else if(mode=="exact_k"){
    int k = argc>2? atoi(argv[2]): 4;
    int tl = argc>3? atoi(argv[3]): 900;
    cmd_exact_k(k, tl);
  } else if(mode=="spectrum"){
    for(int k=4;k<=10;k++){
      cerr << "exact k=" << k << "\n";
      cmd_exact_k(k, /*time*/ k<=5? 180: 30, 5);
    }
  } else {
    cerr << "usage: shrink | exact_k <k> | spectrum\n";
    return 1;
  }
  return 0;
}
