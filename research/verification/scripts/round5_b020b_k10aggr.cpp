// Aggressive 10x10 search: from each greedy set, try k-out (k+1)-in for k=1,2,3.
// Also try starting from the known 18 and doing 2-out 3-in exhaustively around it.
#include <bits/stdc++.h>
using namespace std;
static const int N = 10, PTS = 100;
static inline int px(int p){return p%N;} static inline int py(int p){return p/N;}
static long long det4(int x0,int y0,int x1,int y1,int x2,int y2,int x3,int y3){
  auto s=[&](int x,int y)->long long{return 1LL*x*x+1LL*y*y;};
  long long A[4][4]={{s(x0,y0),x0,y0,1},{s(x1,y1),x1,y1,1},{s(x2,y2),x2,y2,1},{s(x3,y3),x3,y3,1}};
  auto d3=[&](long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h,long long i){
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);};
  long long det=0;
  for(int j=0;j<4;j++){
    long long c[3][3]; int cj=0;
    for(int jj=0;jj<4;jj++) if(jj!=j){c[0][cj]=A[1][jj];c[1][cj]=A[2][jj];c[2][cj]=A[3][jj];cj++;}
    long long cof=d3(c[0][0],c[0][1],c[0][2],c[1][0],c[1][1],c[1][2],c[2][0],c[2][1],c[2][2]);
    if(j%2==0) det+=A[0][j]*cof; else det-=A[0][j]*cof;
  }
  return det;
}
static vector<vector<array<int,2>>> pb;
static inline int pid(int a,int b){if(a>b)swap(a,b);return a*PTS+b;}
static void build(){
  pb.assign(PTS*PTS,{});
  for(int a=0;a<PTS;a++)for(int b=a+1;b<PTS;b++)for(int c=b+1;c<PTS;c++)for(int d=c+1;d<PTS;d++)
    if(det4(px(a),py(a),px(b),py(b),px(c),py(c),px(d),py(d))==0){
      int v[4]={a,b,c,d};
      for(int i=0;i<4;i++)for(int j=i+1;j<4;j++){
        array<int,2> oth{};int k=0;
        for(int t=0;t<4;t++) if(t!=i&&t!=j) oth[k++]=v[t];
        pb[pid(v[i],v[j])].push_back(oth);
      }
    }
}
static bool safe_add(const char*in,int p){
  for(int x=0;x<PTS;x++){
    if(!in[x]||x==p) continue;
    for(auto&o:pb[pid(x,p)]) if(in[o[0]]&&in[o[1]]) return false;
  }
  return true;
}
static bool is_safe(const vector<int>&s){
  char in[PTS]; memset(in,0,sizeof(in));
  for(int x:s) in[x]=1;
  if(s.size()<4) return true;
  for(int i=0;i<(int)s.size();i++)for(int j=i+1;j<(int)s.size();j++)
    for(auto&o:pb[pid(s[i],s[j])]) if(in[o[0]]&&in[o[1]]) return false;
  return true;
}
static void print_set(const vector<int>&s){
  cout<<"["; for(int i=0;i<(int)s.size();i++){if(i)cout<<",";cout<<s[i];} cout<<"]";
}
// After removing subset R, greedily add as many as possible (random order).
static vector<int> rebuild(const vector<int>&base, const vector<int>&removed, mt19937&rng){
  char in[PTS]; memset(in,0,sizeof(in));
  for(int x:base){
    bool skip=false;
    for(int r:removed) if(r==x){skip=true;break;}
    if(!skip) in[x]=1;
  }
  vector<int> order(PTS); iota(order.begin(),order.end(),0); shuffle(order.begin(),order.end(),rng);
  for(int p:order) if(!in[p]&&safe_add(in,p)) in[p]=1;
  for(int pass=0;pass<3;pass++)
    for(int p=0;p<PTS;p++) if(!in[p]&&safe_add(in,p)) in[p]=1;
  vector<int> s; for(int p=0;p<PTS;p++) if(in[p]) s.push_back(p);
  return s;
}
int main(int argc,char**argv){
  build();
  mt19937 rng(argc>1?atoi(argv[1]):7);
  vector<int> known18={1,8,15,20,21,26,38,39,41,54,70,72,73,82,86,88,93,99};
  vector<int> best=known18;
  int best_sz=18;
  // 1) From known18, try all 1-out then rebuild
  cerr<<"phase1: 1-out rebuild from known18\n";
  for(int i=0;i<(int)known18.size();i++){
    auto s=rebuild(known18,{known18[i]},rng);
    if((int)s.size()>best_sz){best=s;best_sz=s.size();cerr<<"NEW "<<best_sz<<"\n";print_set(best);cerr<<"\n";}
  }
  // 2) 2-out rebuild from known18 (all pairs)
  cerr<<"phase2: 2-out rebuild from known18\n";
  for(int i=0;i<(int)known18.size();i++)for(int j=i+1;j<(int)known18.size();j++){
    auto s=rebuild(known18,{known18[i],known18[j]},rng);
    if((int)s.size()>best_sz){best=s;best_sz=s.size();cerr<<"NEW "<<best_sz<<"\n";print_set(best);cerr<<"\n";}
    // also try several random rebuilds
    for(int t=0;t<3;t++){
      auto s2=rebuild(known18,{known18[i],known18[j]},rng);
      if((int)s2.size()>best_sz){best=s2;best_sz=s2.size();cerr<<"NEW "<<best_sz<<"\n";print_set(best);cerr<<"\n";}
    }
  }
  cerr<<"after phase2 best="<<best_sz<<"\n";
  // 3) 3-out rebuild (sample)
  cerr<<"phase3: 3-out rebuild sample\n";
  for(int t=0;t<2000;t++){
    int a=rng()%known18.size(),b=rng()%known18.size(),c=rng()%known18.size();
    if(a==b||b==c||a==c) continue;
    auto s=rebuild(known18,{known18[a],known18[b],known18[c]},rng);
    if((int)s.size()>best_sz){best=s;best_sz=s.size();cerr<<"NEW "<<best_sz<<" trial="<<t<<"\n";print_set(best);cerr<<"\n";}
    if(best_sz>=19) break;
  }
  // 4) Greedy many + 2-out rebuild
  cerr<<"phase4: greedy + aggressive\n";
  for(int t=0;t<3000 && best_sz<19;t++){
    char in[PTS]; memset(in,0,sizeof(in));
    vector<int> order(PTS); iota(order.begin(),order.end(),0); shuffle(order.begin(),order.end(),rng);
    for(int p:order) if(!in[p]&&safe_add(in,p)) in[p]=1;
    for(int pass=0;pass<2;pass++) for(int p=0;p<PTS;p++) if(!in[p]&&safe_add(in,p)) in[p]=1;
    vector<int> s; for(int p=0;p<PTS;p++) if(in[p]) s.push_back(p);
    if((int)s.size()>best_sz){best=s;best_sz=s.size();cerr<<"NEW greedy "<<best_sz<<" t="<<t<<"\n";print_set(best);cerr<<"\n";}
    // 1-out and 2-out rebuild
    for(int i=0;i<(int)s.size() && best_sz<19;i++){
      auto r=rebuild(s,{s[i]},rng);
      if((int)r.size()>best_sz){best=r;best_sz=r.size();cerr<<"NEW "<<best_sz<<"\n";print_set(best);cerr<<"\n";}
      for(int j=i+1;j<(int)s.size() && best_sz<19;j++){
        auto r2=rebuild(s,{s[i],s[j]},rng);
        if((int)r2.size()>best_sz){best=r2;best_sz=r2.size();cerr<<"NEW "<<best_sz<<"\n";print_set(best);cerr<<"\n";}
      }
    }
    if(t%200==0) cerr<<"greedy t="<<t<<" best="<<best_sz<<" last_greedy="<<s.size()<<"\n";
  }
  cerr<<"FINAL best="<<best_sz<<"\n";
  cout<<"{\"best\":"<<best_sz<<",\"set\":"; print_set(best); cout<<"}\n";
  return 0;
}
