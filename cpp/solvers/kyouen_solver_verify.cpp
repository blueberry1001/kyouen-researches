#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

struct Memo {
  std::vector<uint64_t> k; std::vector<uint8_t> v; size_t m,u=0;
  Memo(unsigned p):k(size_t(1)<<p),v(size_t(1)<<p),m((size_t(1)<<p)-1){}
  static uint64_t h(uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
  uint8_t get(uint64_t x)const{size_t i=h(x)&m;while(v[i]){if(k[i]==x)return v[i];i=(i+1)&m;}return 0;}
  void put(uint64_t x,uint8_t z){size_t i=h(x)&m;while(v[i]){if(k[i]==x){v[i]=z;return;}i=(i+1)&m;}k[i]=x;v[i]=z;++u;}
};

class Verify {
  static constexpr int V=64;
  std::vector<uint64_t> comp = std::vector<uint64_t>(size_t(V)*V*V);
  std::array<std::array<std::array<uint64_t,256>,8>,8> map{};
  Memo memo{27}; uint64_t seen=0, forbidden_count=0;
  using Clock=std::chrono::steady_clock; Clock::time_point start=Clock::now();
  static size_t ix(int a,int b,int c){return(size_t(a)*V+b)*V+c;}
  static long long d3(long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h,long long i){return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);}
  static bool bad4(int a,int b,int c,int d){int q[4]={a,b,c,d};long long M[4][4]{};for(int r=0;r<4;r++){long long x=q[r]%8,y=q[r]/8;M[r][0]=x*x+y*y;M[r][1]=x;M[r][2]=y;M[r][3]=1;}long long D=0;for(int col=0;col<4;col++){long long z[3][3]{};for(int r=1;r<4;r++){int p=0;for(int j=0;j<4;j++)if(j!=col)z[r-1][p++]=M[r][j];}long long md=d3(z[0][0],z[0][1],z[0][2],z[1][0],z[1][1],z[1][2],z[2][0],z[2][1],z[2][2]);D+=(col&1?-1:1)*M[0][col]*md;}return D==0;}
  static std::pair<int,int> tf(int t,int x,int y){if(t>=4){x=7-x;t-=4;}while(t--){int nx=y,ny=7-x;x=nx;y=ny;}return{x,y};}
  void init(){for(int a=0;a<V;a++)for(int b=a+1;b<V;b++)for(int c=b+1;c<V;c++)for(int d=c+1;d<V;d++)if(bad4(a,b,c,d)){++forbidden_count;int q[4]={a,b,c,d};for(int o=0;o<4;o++){int t[3],p=0;for(int j=0;j<4;j++)if(j!=o)t[p++]=q[j];comp[ix(t[0],t[1],t[2])]|=1ULL<<q[o];}}
    for(int t=0;t<8;t++)for(int byte=0;byte<8;byte++)for(int z=0;z<256;z++){uint64_t out=0;for(int b=0;b<8;b++)if(z&(1<<b)){int p=byte*8+b;auto [x,y]=tf(t,p%8,p/8);out|=1ULL<<(y*8+x);}map[t][byte][z]=out;}}
  uint64_t trans(uint64_t s,int t)const{uint64_t o=0;for(int b=0;b<8;b++)o|=map[t][b][(s>>(8*b))&255];return o;}
  uint64_t canon(uint64_t s)const{uint64_t z=s;for(int t=1;t<8;t++)z=std::min(z,trans(s,t));return z;}
  uint64_t banned(uint64_t s)const{int a[64],n=0;for(uint64_t x=s;x;x&=x-1)a[n++]=std::countr_zero(x);uint64_t z=0;for(int i=0;i<n-2;i++)for(int j=i+1;j<n-1;j++)for(int k=j+1;k<n;k++)z|=comp[ix(a[i],a[j],a[k])];return z;}
  struct C{uint64_t s;int count;};
  bool win(uint64_t raw){uint64_t s=canon(raw);if(auto x=memo.get(s))return x==2;++seen;if((seen&((1ULL<<20)-1))==0){double sec=std::chrono::duration<double>(Clock::now()-start).count();std::cerr<<seen<<" "<<(seen/sec/1e6)<<"M/s\n";}uint64_t legal=~s&~banned(s);if(!legal){memo.put(s,1);return false;}std::array<C,64> c{};int n=0;while(legal){int p=std::countr_zero(legal);legal&=legal-1;uint64_t ns=canon(s|(1ULL<<p));bool dup=false;for(int i=0;i<n;i++)if(c[i].s==ns){dup=true;break;}if(dup)continue;uint64_t nl=~ns&~banned(ns);c[n++]={ns,std::popcount(nl)};}std::sort(c.begin(),c.begin()+n,[](auto&a,auto&b){return a.count<b.count||(a.count==b.count&&a.s<b.s);});for(int i=0;i<n;i++)if(!win(c[i].s)){memo.put(s,2);return true;}memo.put(s,1);return false;}
public:
  Verify(){init();}
  void run(){bool w=win(0);std::cout<<(w?"FIRST":"SECOND")<<" forbidden="<<forbidden_count<<" states="<<seen<<"\n";}
};
int main(){Verify v;v.run();}
