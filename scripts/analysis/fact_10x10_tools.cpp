// 10x10 fact-discovery tools:
//  - forbidden quad census + local structure
//  - minimal maximal safe sets
//  - minimum saturating (terminal) safe sets
// Usage:
//   fact_10x10.exe geometry
//   fact_10x10.exe minmaximal
//   fact_10x10.exe saturation
//   fact_10x10.exe two_stone
#include <bits/stdc++.h>
using namespace std;

static const int N = 10;
static const int PTS = N * N;

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
    long long c[3][3];
    int cj=0;
    for(int jj=0;jj<4;jj++) if(jj!=j){
      c[0][cj]=A[1][jj]; c[1][cj]=A[2][jj]; c[2][cj]=A[3][jj]; cj++;
    }
    long long cof=d3(c[0][0],c[0][1],c[0][2],c[1][0],c[1][1],c[1][2],c[2][0],c[2][1],c[2][2]);
    if(j%2==0) det += A[0][j]*cof; else det -= A[0][j]*cof;
  }
  return det;
}

struct Forbidden {
  vector<array<int,4>> quads;
  vector<vector<int>> by_point; // for each point, list of quad ids
  vector<vector<array<int,3>>> by_point_others; // for each point, other 3 members
  vector<int> deg;
};

static Forbidden build_forbidden(){
  Forbidden F;
  F.by_point.assign(PTS, {});
  F.by_point_others.assign(PTS, {});
  F.deg.assign(PTS, 0);
  for(int a=0;a<PTS;a++) for(int b=a+1;b<PTS;b++) for(int c=b+1;c<PTS;c++) for(int d=c+1;d<PTS;d++){
    if(det4(px(a),py(a),px(b),py(b),px(c),py(c),px(d),py(d))==0){
      int id = (int)F.quads.size();
      F.quads.push_back({a,b,c,d});
      int q[4]={a,b,c,d};
      for(int i=0;i<4;i++){
        F.deg[q[i]]++;
        array<int,3> others{};
        int k=0;
        for(int j=0;j<4;j++) if(j!=i) others[k++]=q[j];
        F.by_point[q[i]].push_back(id);
        F.by_point_others[q[i]].push_back(others);
      }
    }
  }
  return F;
}

static bool safe_add(const Forbidden&F, const vector<int>&occ, int p){
  // occupied as sorted vector; check if any quad (p + 3 in occ)
  static char in[PTS];
  memset(in,0,sizeof(in));
  for(int x:occ) in[x]=1;
  for(const auto& oth : F.by_point_others[p]){
    if(in[oth[0]] && in[oth[1]] && in[oth[2]]) return false;
  }
  return true;
}

static int d4_canon_key(const vector<int>&pts){
  int n=N-1;
  int best=INT_MAX;
  for(int mode=0;mode<8;mode++){
    vector<int> img; img.reserve(pts.size());
    for(int p:pts){
      int x=px(p),y=py(p),nx,ny;
      switch(mode){
        case 0: nx=x; ny=y; break;
        case 1: nx=n-x; ny=y; break;
        case 2: nx=x; ny=n-y; break;
        case 3: nx=n-x; ny=n-y; break;
        case 4: nx=y; ny=x; break;
        case 5: nx=n-y; ny=x; break;
        case 6: nx=y; ny=n-x; break;
        default: nx=n-y; ny=n-x; break;
      }
      img.push_back(pid(nx,ny));
    }
    sort(img.begin(), img.end());
    // pack first 6 into key hash
    unsigned long long h=1469598103934665603ULL;
    for(int v:img){ h^= (unsigned)v; h*=1099511628211ULL; }
    int key=(int)(h & 0x7fffffff);
    best=min(best,key);
  }
  return best;
}

static void cmd_geometry(const Forbidden&F){
  // collinear vs concyclic
  int ncol=0, ncirc=0;
  map<pair<int,int>, int> dirs;
  map<int,int> circle_size_hist; // not fully classified; count via unique circles later
  // For local structure: degree, quads per point already
  // circle sizes: for non-collinear quads, try to find circumcircle lattice size among board points
  // expensive if naive; instead count how many board points lie on each unique circle
  map<string,int> circle_hit; // circle key -> lattice points on it (sampled later)
  for(const auto&q:F.quads){
    int x0=px(q[0]),y0=py(q[0]),x1=px(q[1]),y1=py(q[1]),x2=px(q[2]),y2=py(q[2]),x3=px(q[3]),y3=py(q[3]);
    // collinear?
    bool col=true;
    for(int i=2;i<4;i++){
      int x=px(q[i]),y=py(q[i]);
      if(1LL*(x1-x0)*(y-y0)!=1LL*(y1-y0)*(x-x0)){ col=false; break; }
    }
    if(col){
      ncol++;
      int dx=x1-x0, dy=y1-y0;
      int g=std::gcd(abs(dx),abs(dy)); if(g==0) g=1;
      dx/=g; dy/=g;
      if(dx<0 || (dx==0 && dy<0)){ dx=-dx; dy=-dy; }
      dirs[{dx,dy}]++;
    } else ncirc++;
  }
  cout << "{\n";
  cout << "  \"board\": \"10x10\",\n";
  cout << "  \"forbidden_total\": " << F.quads.size() << ",\n";
  cout << "  \"collinear_quads\": " << ncol << ",\n";
  cout << "  \"concyclic_quads\": " << ncirc << ",\n";
  cout << "  \"collinear_by_dir\": {";
  bool first=true;
  for(auto&[d,c]:dirs){
    if(!first) cout << ", ";
    first=false;
    cout << "\"" << d.first << "," << d.second << "\": " << c;
  }
  cout << "},\n";
  int dmin=INT_MAX,dmax=INT_MIN; double dsum=0;
  for(int d:F.deg){ dmin=min(dmin,d); dmax=max(dmax,d); dsum+=d; }
  cout << "  \"point_degree_min\": " << dmin << ",\n";
  cout << "  \"point_degree_max\": " << dmax << ",\n";
  cout << "  \"point_degree_mean\": " << (dsum/PTS) << ",\n";
  // radius buckets
  map<string, pair<vector<int>,int>> rad;
  for(int p=0;p<PTS;p++){
    double cx=(N-1)/2.0;
    double r2=(px(p)-cx)*(px(p)-cx)+(py(p)-cx)*(py(p)-cx);
    ostringstream oss; oss<<fixed<<setprecision(1)<<r2;
    rad[oss.str()].first.push_back(F.deg[p]);
    rad[oss.str()].second++;
  }
  cout << "  \"point_degree_by_radius\": {";
  first=true;
  for(auto&[r,pair]:rad){
    auto&vs=pair.first;
    double mean=0; for(int v:vs) mean+=v; mean/=vs.size();
    int mn=*min_element(vs.begin(),vs.end()), mx=*max_element(vs.begin(),vs.end());
    if(!first) cout << ", ";
    first=false;
    cout << "\"" << r << "\": {\"n\": " << pair.second << ", \"deg_mean\": " << mean << ", \"deg_min\": " << mn << ", \"deg_max\": " << mx << "}";
  }
  cout << "}\n";
  cout << "}\n";
}

static bool is_maximal_safe(const Forbidden&F, const vector<int>&occ){
  static char in[PTS];
  memset(in,0,sizeof(in));
  for(int x:occ) in[x]=1;
  for(int p=0;p<PTS;p++) if(!in[p] && safe_add(F, occ, p)) return false;
  return true;
}

// Count admissible points not in occ (how many moves remain).
static int mobility(const Forbidden&F, const vector<int>&occ){
  static char in[PTS];
  memset(in,0,sizeof(in));
  for(int x:occ) in[x]=1;
  int m=0;
  for(int p=0;p<PTS;p++) if(!in[p] && safe_add(F, occ, p)) m++;
  return m;
}

static void cmd_minmaximal(const Forbidden&F, int time_limit_s=600, int max_keep=50){
  auto t0=chrono::steady_clock::now();
  auto elapsed=[&](){ return chrono::duration<double>(chrono::steady_clock::now()-t0).count(); };
  // greedy upper bound
  vector<int> greedy;
  for(int p=0;p<PTS;p++) if(safe_add(F, greedy, p)) greedy.push_back(p);
  bool changed=true;
  while(changed){
    changed=false;
    for(int p=0;p<PTS;p++){
      bool in=false; for(int x:greedy) if(x==p){in=true;break;}
      if(in) continue;
      if(safe_add(F, greedy, p)){ greedy.push_back(p); changed=true; break; }
    }
  }

  // Iterative deepening: find maximal safe sets of size exactly k.
  // Any size < 4 cannot be maximal (a single triple is always safe).
  int found_size=-1;
  vector<vector<int>> best;
  bool complete=true;
  long long nodes=0;

  function<bool(vector<int>&, int, int)> dfs_k = [&](vector<int>&occ, int from, int k)->bool{
    nodes++;
    if(elapsed()>time_limit_s){ complete=false; return false; }
    if((int)occ.size()==k){
      if(is_maximal_safe(F, occ)){
        if((int)best.size()<max_keep) best.push_back(occ);
        return true;
      }
      return false;
    }
    // prune: not enough remaining slots
    int need = k - (int)occ.size();
    for(int p=from;p<PTS;p++){
      if(PTS - p < need) break;
      if(!safe_add(F, occ, p)) continue;
      occ.push_back(p);
      bool got = dfs_k(occ, p+1, k);
      occ.pop_back();
      if(got) return true;
      if(!complete) return false;
    }
    return false;
  };

  for(int k=4;k<=12;k++){
    best.clear();
    nodes=0;
    vector<int> occ;
    bool got=false;
    // early stop when a solution is found at size k
    function<void(vector<int>&,int)> dfs_collect = [&](vector<int>&occ, int from){
      if(!complete) return;
      nodes++;
      if(elapsed()>time_limit_s){ complete=false; return; }
      if((int)occ.size()==k){
        if(is_maximal_safe(F, occ) && (int)best.size()<max_keep) best.push_back(occ);
        return;
      }
      int need=k-(int)occ.size();
      for(int p=from;p<PTS;p++){
        if(PTS-p<need) break;
        if(!safe_add(F, occ, p)) continue;
        occ.push_back(p);
        dfs_collect(occ, p+1);
        occ.pop_back();
        if(!complete) return;
        // for minimal discovery we can stop early after first hit at this k
        if(!best.empty() && best.size()>=1 && k<=6) return;
      }
    };
    dfs_collect(occ, 0);
    if(!best.empty()){
      found_size=k;
      break;
    }
    if(!complete) break;
  }

  cout << "{\n";
  cout << "  \"board\": \"10x10\",\n";
  cout << "  \"forbidden_total\": " << F.quads.size() << ",\n";
  cout << "  \"greedy_maximal_size\": " << greedy.size() << ",\n";
  cout << "  \"min_maximal_size\": " << found_size << ",\n";
  cout << "  \"n_sets_recorded\": " << best.size() << ",\n";
  cout << "  \"complete\": " << (complete?"true":"false") << ",\n";
  cout << "  \"nodes\": " << nodes << ",\n";
  cout << "  \"seconds\": " << elapsed() << ",\n";
  cout << "  \"sample_sets\": [";
  for(int i=0;i<(int)best.size();i++){
    if(i) cout << ", ";
    cout << "[";
    for(int j=0;j<(int)best[i].size();j++){
      if(j) cout << ", ";
      cout << best[i][j];
    }
    cout << "]";
  }
  cout << "]\n";
  cout << "}\n";
}

// A safe set is saturating/terminal if no point can be added.
static void cmd_saturation(const Forbidden&F, int time_limit_s=600, int max_keep=30){
  auto t0=chrono::steady_clock::now();
  auto elapsed=[&](){ return chrono::duration<double>(chrono::steady_clock::now()-t0).count(); };
  int min_size=INT_MAX;
  vector<vector<int>> best;
  bool complete=true;
  long long nodes=0;
  function<void(vector<int>&, int)> dfs = [&](vector<int>&occ, int from){
    nodes++;
    if(elapsed()>time_limit_s){ complete=false; return; }
    // if already cannot extend and nonempty -> terminal
    bool can=false;
    for(int p=from;p<PTS;p++) if(safe_add(F, occ, p)){ can=true; break; }
    // also points < from? In construction order we only add increasing p, so
    // maximality must consider ALL points not in set.
    // Check full maximality:
    auto maximal=[&](){
      static char in[PTS]; memset(in,0,sizeof(in));
      for(int x:occ) in[x]=1;
      for(int p=0;p<PTS;p++) if(!in[p] && safe_add(F, occ, p)) return false;
      return true;
    };
    if(maximal()){
      int sz=(int)occ.size();
      if(sz<min_size){ min_size=sz; best.clear(); }
      if(sz==min_size && (int)best.size()<max_keep) best.push_back(occ);
      // a maximal set cannot be extended, so return
      return;
    }
    if((int)occ.size()>=min_size) return;
    for(int p=from;p<PTS;p++){
      if(!safe_add(F, occ, p)) continue;
      occ.push_back(p);
      dfs(occ, p+1);
      occ.pop_back();
      if(!complete) return;
    }
  };
  vector<int> occ;
  dfs(occ, 0);
  cout << "{\n";
  cout << "  \"board\": \"10x10\",\n";
  cout << "  \"min_saturating_size\": " << (min_size==INT_MAX? -1: min_size) << ",\n";
  cout << "  \"n_sets_recorded\": " << best.size() << ",\n";
  cout << "  \"complete\": " << (complete?"true":"false") << ",\n";
  cout << "  \"nodes\": " << nodes << ",\n";
  cout << "  \"seconds\": " << elapsed() << ",\n";
  cout << "  \"sample_sets\": [";
  for(int i=0;i<(int)best.size();i++){
    if(i) cout << ", ";
    cout << "[";
    for(int j=0;j<(int)best[i].size();j++){
      if(j) cout << ", ";
      cout << best[i][j];
    }
    cout << "]";
  }
  cout << "]\n";
  cout << "}\n";
}

static void cmd_two_stone(const Forbidden&F){
  // D4 orbits of pairs + sum of degrees + quads containing pair
  vector<int> deg=F.deg;
  map<pair<int,int>, int> pair_quad;
  for(auto&q:F.quads){
    for(int i=0;i<4;i++) for(int j=i+1;j<4;j++){
      int a=q[i], b=q[j];
      if(a>b) swap(a,b);
      pair_quad[{a,b}]++;
    }
  }
  int n=N-1;
  auto images_xy=[&](int x,int y){
    array<pair<int,int>,8> im{{
      {x,y},{n-x,y},{x,n-y},{n-x,n-y},{y,x},{n-y,x},{y,n-x},{n-y,n-x}
    }};
    return im;
  };
  auto canon_pair=[&](int p,int q){
    int x1=px(p),y1=py(p),x2=px(q),y2=py(q);
    unsigned long long best=ULLONG_MAX;
    for(auto A:images_xy(x1,y1)) for(auto B:images_xy(x2,y2)){
      int a=pid(A.first,A.second), b=pid(B.first,B.second);
      if(a==b) continue;
      if(a>b) swap(a,b);
      unsigned long long key=(1ULL*a<<8)|b;
      best=min(best,key);
    }
    return best;
  };
  map<unsigned long long, vector<pair<int,int>>> orbits;
  for(int p=0;p<PTS;p++) for(int q=p+1;q<PTS;q++){
    orbits[canon_pair(p,q)].push_back({p,q});
  }
  cout << "{\n  \"board\": \"10x10\",\n  \"pair_orbits\": " << orbits.size() << ",\n  \"orbits\": [\n";
  bool first=true;
  int omin=INT_MAX,omax=INT_MIN,qmin=INT_MAX,qmax=INT_MIN;
  for(auto&[key, members]:orbits){
    int p=members[0].first, q=members[0].second;
    int a=min(p,q), b=max(p,q);
    int sd=deg[a]+deg[b];
    int nq=pair_quad[{a,b}];
    omin=min(omin,sd); omax=max(omax,sd);
    qmin=min(qmin,nq); qmax=max(qmax,nq);
    if(!first) cout << ",\n";
    first=false;
    cout << "    {\"rep\": [" << a << "," << b << "], \"n_members\": " << members.size()
         << ", \"d_p\": " << deg[a] << ", \"d_q\": " << deg[b]
         << ", \"sum_d\": " << sd << ", \"quads_containing_pair\": " << nq
         << ", \"dx_dy\": [" << (px(b)-px(a)) << "," << (py(b)-py(a)) << "]}";
  }
  cout << "\n  ],\n";
  cout << "  \"sum_d_min\": " << omin << ",\n  \"sum_d_max\": " << omax << ",\n";
  cout << "  \"pair_quad_min\": " << qmin << ",\n  \"pair_quad_max\": " << qmax << "\n";
  cout << "}\n";
}

int main(int argc, char**argv){
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  string mode = argc>1 ? argv[1] : "geometry";
  if(mode != "two_stone" && mode != "geometry_fast"){
    // need forbidden for most
  }
  if(mode=="geometry" || mode=="minmaximal" || mode=="saturation" || mode=="two_stone" || mode=="geometry_fast"){
    cerr << "building forbidden...\n";
    auto F=build_forbidden();
    cerr << "forbidden=" << F.quads.size() << "\n";
    if(mode=="geometry" || mode=="geometry_fast") cmd_geometry(F);
    else if(mode=="minmaximal") cmd_minmaximal(F);
    else if(mode=="saturation") cmd_saturation(F);
    else if(mode=="two_stone") cmd_two_stone(F);
    return 0;
  }
  cerr << "unknown mode\n";
  return 1;
}
