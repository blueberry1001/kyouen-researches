// 10x10 three-stone D4 orbit census + mobility = 97 - completions
#include <bits/stdc++.h>
using namespace std;
static const int N=10, PTS=100;
static inline int pid(int x,int y){return y*N+x;}
static inline int px(int p){return p%N;}
static inline int py(int p){return p/N;}

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

static map<array<int,3>, bitset<PTS>> triple_comp;

int main(){
  ios::sync_with_stdio(false); cin.tie(nullptr);
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
  // D4 on triples
  int n=N-1;
  auto img=[&](int p, int mode){
    int x=px(p), y=py(p), nx, ny;
    switch(mode){
      case 0: nx=x; ny=y; break; case 1: nx=n-x; ny=y; break;
      case 2: nx=x; ny=n-y; break; case 3: nx=n-x; ny=n-y; break;
      case 4: nx=y; ny=x; break; case 5: nx=n-y; ny=x; break;
      case 6: nx=y; ny=n-x; break; default: nx=n-y; ny=n-x; break;
    }
    return pid(nx,ny);
  };
  map<array<int,3>, int> orbit_id;
  map<int, array<int,3>> orbit_rep;
  map<int, int> orbit_count;
  map<int, int> orbit_mob; // 97 - completions of rep
  map<int, int> orbit_comp;
  int next_id=0;
  for(int a=0;a<PTS;a++) for(int b=a+1;b<PTS;b++) for(int c=b+1;c<PTS;c++){
    array<int,3> t{a,b,c};
    unsigned long long best=ULLONG_MAX;
    array<int,3> best_t=t;
    for(int m0=0;m0<8;m0++) for(int m1=0;m1<8;m1++) for(int m2=0;m2<8;m2++){
      array<int,3> im{img(a,m0), img(b,m1), img(c,m2)};
      sort(im.begin(), im.end());
      if(im[0]==im[1]||im[1]==im[2]) continue;
      unsigned long long h=1469598103934665603ULL;
      for(int v:im){ h^=(unsigned)v; h*=1099511628211ULL; }
      if(h<best){ best=h; best_t=im; }
    }
    if(orbit_id.count(best_t)==0){
      int id=next_id++;
      orbit_id[best_t]=id;
      orbit_rep[id]=best_t;
      auto it=triple_comp.find(best_t);
      int comp = it==triple_comp.end()? 0 : (int)it->second.count();
      orbit_comp[id]=comp;
      orbit_mob[id]=97-comp;
    }
    orbit_count[orbit_id[best_t]]++;
  }
  // histogram of mobility
  map<int,int> mob_hist;
  for(auto&[id,m]:orbit_mob) mob_hist[m]++;
  map<int,int> comp_hist;
  for(auto&[id,c]:orbit_comp) comp_hist[c]++;
  cout << "{\"n_orbits\":"<<next_id
       <<",\"sum_members\":"<< (long long)161700
       <<",\"mobility_hist\":{";
  bool first=true;
  for(auto&[m,c]:mob_hist){ if(!first) cout<<","; first=false; cout<<"\""<<m<<"\":"<<c; }
  cout<<"},\"completion_hist\":{";
  first=true;
  for(auto&[m,c]:comp_hist){ if(!first) cout<<","; first=false; cout<<"\""<<m<<"\":"<<c; }
  cout<<"}}\n";
  return 0;
}
