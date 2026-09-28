#define MAIN_DISABLED 1
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include <string>
using kc::u64;
static inline int pc(u64 x){return __builtin_popcountll(x);}

// paste the pieces we need
struct Geo { int V=0; u64 full=0; std::vector<int> xs,ys; std::vector<u64> quads; std::vector<u64> P2; std::vector<int> deg; };
static long long det4p(int x0,int y0,int x1,int y1,int x2,int y2,int x3,int y3){
  long long m[4][4]; int X[4]={x0,x1,x2,x3},Y[4]={y0,y1,y2,y3};
  for(int i=0;i<4;++i){m[i][0]=(long long)X[i]*X[i]+(long long)Y[i]*Y[i];m[i][1]=X[i];m[i][2]=Y[i];m[i][3]=1;}
  extern long long det4x(const long long[4][4]);
  return det4x(m);
}
long long det4x(const long long r[4][4]){
  long long total=0;
  for(int i=0;i<4;++i){long long mm[3][3];int ri=0;
    for(int r2=0;r2<4;++r2){if(r2==i)continue;int ci=0;for(int c2=1;c2<4;++c2)mm[ri][ci++]=r[r2][c2];++ri;}
    long long d3=mm[0][0]*(mm[1][1]*mm[2][2]-mm[1][2]*mm[2][1])-mm[0][1]*(mm[1][0]*mm[2][2]-mm[1][2]*mm[2][0])+mm[0][2]*(mm[1][0]*mm[2][1]-mm[1][1]*mm[2][0]);
    total+=(i%2==0?1:-1)*r[i][0]*d3;}
  return total;
}
int main(){
  int n=4; Geo g; g.V=n*n; g.full=(1ULL<<g.V)-1;
  for(int y=0;y<n;++y)for(int x=0;x<n;++x){g.xs.push_back(x);g.ys.push_back(y);}
  g.P2.assign((size_t)g.V*g.V*g.V,0); g.deg.assign(g.V,0);
  for(int a=0;a<g.V-3;++a)for(int b=a+1;b<g.V-2;++b)for(int c=b+1;c<g.V-1;++c)for(int d=c+1;d<g.V;++d){
    if(det4p(g.xs[a],g.ys[a],g.xs[b],g.ys[b],g.xs[c],g.ys[c],g.xs[d],g.ys[d])!=0)continue;
    int id[4]={a,b,c,d}; g.quads.push_back((1ULL<<a)|(1ULL<<b)|(1ULL<<c)|(1ULL<<d));
    for(int t=0;t<4;++t){g.deg[id[t]]++;
      for(int i=0;i<4;++i)for(int j=i+1;j<4;++j){ if(i==t||j==t)continue;
        int p2=id[t],A=id[i],B=id[j],r=-1;
        for(int z=0;z<4;++z)if(z!=t&&z!=i&&z!=j)r=id[z];
        g.P2[((size_t)p2*g.V+A)*g.V+B]|=1ULL<<r;}}
  }
  printf("quads=%zu\n",g.quads.size());
  // manual level-0..1 check with the same P2 indexing
  for(int p=0;p<4;++p){
    u64 bl=0;
    // S has 0 elements -> no pairs, so bl=0. legal mask at empty should be full.
    printf("p=%d alone legal (no triples to check) => P2 unused\n",p);
    (void)bl;
  }
  // check: from a 2-set, is the blocked mask right?
  for(int a=0;a<g.V;++a)for(int b=a+1;b<g.V;++b){
    u64 S=(1ULL<<a)|(1ULL<<b);
    for(int p=0;p<g.V;++p){
      if(S>>p&1) continue;
      u64 bl=g.P2[((size_t)p*g.V+a)*g.V+b];
      if(bl){ printf("  adding %d to {%d,%d} blocks %llx\n",p,a,b,(unsigned long long)bl); }
    }
  }
  return 0;
}
