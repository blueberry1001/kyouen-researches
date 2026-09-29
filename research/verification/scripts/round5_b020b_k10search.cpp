// 10x10 large safe-set search: random greedy + local search toward K_10 >= 19.
// Also verifies known 18-witness and tries constructions.
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

// For each pair (a,b), list of completions (u,v) with u<v such that {a,b,u,v} forbidden.
static vector<vector<array<int,2>>> pair_blocks;

static inline int pair_id(int a,int b){ if(a>b) swap(a,b); return a*PTS + b; }

static void build(){
  pair_blocks.assign(PTS*PTS, {});
  long long nquads=0;
  for(int a=0;a<PTS;a++) for(int b=a+1;b<PTS;b++) for(int c=b+1;c<PTS;c++) for(int d=c+1;d<PTS;d++){
    if(det4(px(a),py(a),px(b),py(b),px(c),py(c),px(d),py(d))==0){
      nquads++;
      int v[4]={a,b,c,d};
      for(int i=0;i<4;i++) for(int j=i+1;j<4;j++){
        array<int,2> oth{}; int k=0;
        for(int t=0;t<4;t++) if(t!=i && t!=j) oth[k++]=v[t];
        pair_blocks[pair_id(v[i],v[j])].push_back(oth);
      }
    }
  }
  cerr << "quads=" << nquads << "\n";
}

static bool safe_add(const char* in, int p){
  for(int x=0;x<PTS;x++){
    if(!in[x] || x==p) continue;
    int a=x,b=p;
    for(auto&oth: pair_blocks[pair_id(a,b)]){
      if(in[oth[0]] && in[oth[1]]) return false;
    }
  }
  return true;
}

static bool is_safe(const vector<int>&occ){
  char in[PTS]; memset(in,0,sizeof(in));
  for(int x:occ) in[x]=1;
  if((int)occ.size()<4) return true;
  for(int i=0;i<(int)occ.size();i++) for(int j=i+1;j<(int)occ.size();j++){
    int a=occ[i],b=occ[j];
    for(auto&oth: pair_blocks[pair_id(a,b)]){
      if(in[oth[0]] && in[oth[1]]) return false;
    }
  }
  return true;
}

static int legal_count(const vector<int>&occ){
  char in[PTS]; memset(in,0,sizeof(in));
  for(int x:occ) in[x]=1;
  int m=0;
  for(int p=0;p<PTS;p++) if(!in[p] && safe_add(in,p)) m++;
  return m;
}

static void print_set(const vector<int>&s){
  cout << "[";
  for(int i=0;i<(int)s.size();i++){ if(i) cout << ","; cout << s[i]; }
  cout << "]";
}

// Greedy from a shuffled order, then closure.
static vector<int> greedy_random(mt19937& rng, int start_bias=0){
  vector<int> order(PTS);
  iota(order.begin(), order.end(), 0);
  shuffle(order.begin(), order.end(), rng);
  // optional: bias toward center / corners
  if(start_bias==1){ // center-first
    sort(order.begin(), order.end(), [&](int a,int b){
      int da=abs(px(a)-4)+abs(py(a)-4), db=abs(px(b)-4)+abs(py(b)-4);
      return da<db || (da==db && a<b);
    });
  } else if(start_bias==2){ // corner-first
    sort(order.begin(), order.end(), [&](int a,int b){
      auto corner=[&](int p){ int x=px(p),y=py(p); return min(x,9-x)+min(y,9-y); };
      int da=corner(a), db=corner(b);
      return da<db || (da==db && a<b);
    });
  }
  vector<int> s;
  char in[PTS]; memset(in,0,sizeof(in));
  for(int p: order){
    if(!in[p] && safe_add(in,p)){ s.push_back(p); in[p]=1; }
  }
  // second pass
  bool changed=true;
  while(changed){
    changed=false;
    for(int p=0;p<PTS;p++) if(!in[p] && safe_add(in,p)){ s.push_back(p); in[p]=1; changed=true; }
  }
  sort(s.begin(), s.end());
  return s;
}

// Local search: try remove one + add two (or add one after remove) to grow.
static bool local_improve(vector<int>& best, mt19937& rng, int iters){
  bool improved=false;
  for(int it=0; it<iters; it++){
    int sz = (int)best.size();
    if(sz<4) break;
    // pick a random point to remove
    int ri = rng()%sz;
    vector<int> cand = best;
    cand.erase(cand.begin()+ri);
    if(!is_safe(cand)) continue;
    // try add any 1 or 2 points
    char in[PTS]; memset(in,0,sizeof(in));
    for(int x:cand) in[x]=1;
    // try single add first
    for(int p=0;p<PTS;p++){
      if(in[p]) continue;
      if(safe_add(in,p)){
        vector<int> t=cand; t.push_back(p); sort(t.begin(),t.end());
        if((int)t.size()>(int)best.size()){
          best=t; improved=true; break;
        }
      }
    }
    if(improved) continue;
    // try two adds
    for(int p=0;p<PTS;p++){
      if(in[p]) continue;
      if(!safe_add(in,p)) continue;
      char in2[PTS]; memcpy(in2,in,sizeof(in)); in2[p]=1;
      vector<int> t=cand; t.push_back(p);
      for(int q=p+1;q<PTS;q++){
        if(in2[q]) continue;
        if(safe_add(in2,q)){
          vector<int> t2=t; t2.push_back(q); sort(t2.begin(),t2.end());
          if((int)t2.size()>(int)best.size()){
            best=t2; improved=true; break;
          }
        }
      }
      if(improved) break;
    }
  }
  return improved;
}

// Maximize size with simulated-annealing-ish: repeatedly greedy + local.
int main(int argc, char** argv){
  int n_trials = argc>1 ? atoi(argv[1]) : 2000;
  int seed = argc>2 ? atoi(argv[2]) : 42;
  build();
  mt19937 rng(seed);

  vector<int> known18 = {1,8,15,20,21,26,38,39,41,54,70,72,73,82,86,88,93,99};
  cerr << "known18 safe=" << is_safe(known18) << " legal_left=" << legal_count(known18) << " size=" << known18.size() << "\n";

  vector<int> best = known18;
  int best_size = (int)best.size();
  int hist[32]={0};
  int n18=0, n17=0, n16=0;

  for(int t=0;t<n_trials;t++){
    int bias = t%3;
    auto s = greedy_random(rng, bias);
    hist[s.size()]++;
    if((int)s.size()==18) n18++;
    if((int)s.size()==17) n17++;
    if((int)s.size()==16) n16++;
    // local improve
    for(int r=0;r<8;r++){
      if(!local_improve(s, rng, 200)) break;
    }
    if((int)s.size()>best_size){
      best_size = s.size();
      best = s;
      cerr << "NEW BEST " << best_size << " trial=" << t << " legal_left=" << legal_count(best) << "\n";
      print_set(best); cerr << "\n";
    }
    if(t%200==0){
      cerr << "trial=" << t << " best=" << best_size << " greedy18=" << n18 << " greedy17=" << n17 << " greedy16=" << n16 << "\n";
    }
    if(best_size>=19) break;
  }

  cerr << "FINAL best=" << best_size << " legal_left=" << legal_count(best) << "\n";
  cout << "{\"board\":\"10x10\",\"best_size\":" << best_size
       << ",\"legal_left\":" << legal_count(best)
       << ",\"greedy_hist\":{";
  bool first=true;
  for(int i=0;i<32;i++) if(hist[i]){ if(!first) cout<<","; first=false; cout<<"\""<<i<<"\":"<<hist[i]; }
  cout << "},\"best_set\":"; print_set(best); cout << "}\n";
  return 0;
}
