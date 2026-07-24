#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <vector>
struct Bits{uint64_t lo=0,hi=0;};
static inline bool operator==(Bits a,Bits b){return a.lo==b.lo&&a.hi==b.hi;}
static inline bool operator<(Bits a,Bits b){return a.hi<b.hi||(a.hi==b.hi&&a.lo<b.lo);}
static inline Bits operator|(Bits a,Bits b){return{a.lo|b.lo,a.hi|b.hi};}
static inline Bits operator&(Bits a,Bits b){return{a.lo&b.lo,a.hi&b.hi};}
static inline Bits operator~(Bits a){return{~a.lo,~a.hi};}
static inline bool any(Bits a){return a.lo||a.hi;}
static inline int pc(Bits a){return std::popcount(a.lo)+std::popcount(a.hi);}
static inline Bits bitof(int p){return p<64?Bits{1ULL<<p,0}:Bits{0,1ULL<<(p-64)};}
static inline void setbit(Bits&a,int p){if(p<64)a.lo|=1ULL<<p;else a.hi|=1ULL<<(p-64);}
static inline int poplsb(Bits&a){if(a.lo){int p=std::countr_zero(a.lo);a.lo&=a.lo-1;return p;}int p=std::countr_zero(a.hi);a.hi&=a.hi-1;return p+64;}
class Memo{public:enum:uint32_t{L=1,W=2};Memo(unsigned p):lo(size_t{1}<<p),m(size_t{1}<<p),mask((size_t{1}<<p)-1){}uint32_t get(Bits k)const{size_t i=h(k)&mask;while(m[i]){if(lo[i]==k.lo&&(m[i]>>2)==k.hi)return m[i]&3;i=(i+1)&mask;}return 0;}void put(Bits k,uint32_t v){size_t i=h(k)&mask;uint32_t z=(uint32_t(k.hi)<<2)|v;while(m[i]){if(lo[i]==k.lo&&(m[i]>>2)==k.hi){m[i]=z;return;}i=(i+1)&mask;}lo[i]=k.lo;m[i]=z;if(++used*10>m.size()*8)throw std::runtime_error("memo full");}size_t count()const{return used;}private:std::vector<uint64_t>lo;std::vector<uint32_t>m;size_t mask,used=0;static uint64_t h64(uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}static uint64_t h(Bits b){return h64(b.lo^(b.hi*0x9e3779b97f4a7c15ULL));}};
class Verify{static constexpr int N=9,V=81;struct Child{Bits s,l,k;int n,v;uint32_t c;};public:Verify(unsigned p):comp(size_t(V)*V*V),memo(p){build();}void run(){Bits s=bitof(40),legal{~0ULL,(1ULL<<17)-1};legal=legal&~bitof(40);bool r=win(s,legal,1);std::cout<<(r?"WIN":"LOSS")<<" for player after center; forbidden="<<fc<<" states="<<vis<<" memo="<<memo.count()<<" maxdepth="<<md<<"\n";}private:std::vector<Bits>comp;Memo memo;uint64_t fc=0,vis=0;int md=0;static long long d3(long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h,long long i){return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);}static bool bad(int a,int b,int c,int d){int q[4]={a,b,c,d};long long m[4][4]{};for(int r=0;r<4;r++){long long x=q[r]%N,y=q[r]/N;m[r][0]=x*x+y*y;m[r][1]=x;m[r][2]=y;m[r][3]=1;}long long z=0;for(int col=0;col<4;col++){long long u[3][3]{};for(int r=1;r<4;r++){int k=0;for(int j=0;j<4;j++)if(j!=col)u[r-1][k++]=m[r][j];}long long w=d3(u[0][0],u[0][1],u[0][2],u[1][0],u[1][1],u[1][2],u[2][0],u[2][1],u[2][2]);z+=(col&1?-1:1)*m[0][col]*w;}return z==0;}static size_t ix(int a,int b,int c){return(size_t(a)*V+b)*V+c;}static void sort3(int&a,int&b,int&c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);}void build(){for(int a=0;a<V;a++)for(int b=a+1;b<V;b++)for(int c=b+1;c<V;c++)for(int d=c+1;d<V;d++)if(bad(a,b,c,d)){fc++;int q[4]={a,b,c,d};for(int o=0;o<4;o++){int t[3],k=0;for(int j=0;j<4;j++)if(j!=o)t[k++]=q[j];comp[ix(t[0],t[1],t[2])]=comp[ix(t[0],t[1],t[2])]|bitof(q[o]);}}std::cerr<<"built "<<fc<<"\n";}
Bits trans(Bits s,int kind)const{Bits o{};while(any(s)){int p=poplsb(s),x=p%N,y=p/N,nx=x,ny=y;switch(kind){case 0:break;case 1:nx=N-1-x;break;case 2:ny=N-1-y;break;case 3:nx=N-1-x;ny=N-1-y;break;case 4:nx=y;ny=x;break;case 5:nx=N-1-y;ny=x;break;case 6:nx=y;ny=N-1-x;break;case 7:nx=N-1-y;ny=N-1-x;break;}setbit(o,ny*N+nx);}return o;}Bits canon(Bits s)const{Bits z=s;for(int k=1;k<8;k++){Bits t=trans(s,k);if(t<z)z=t;}return z;}Bits bans(Bits s,int v)const{int a[V],n=0;Bits t=s;while(any(t))a[n++]=poplsb(t);Bits o{};for(int i=0;i<n;i++)for(int j=i+1;j<n;j++){int x=a[i],y=a[j],z=v;sort3(x,y,z);o=o|comp[ix(x,y,z)];}return o;}
bool win(Bits s,Bits legal,int dep){Bits key=canon(s);auto q=memo.get(key);if(q)return q==Memo::W;vis++;md=std::max(md,dep);if((vis&((1ULL<<22)-1))==0)std::cerr<<"states="<<vis<<" depth="<<dep<<"\n";if(!any(legal)){memo.put(key,Memo::L);return false;}std::array<Child,V>ch{};int n=0;Bits mv=legal;while(any(mv)){int v=poplsb(mv);Bits ns=s|bitof(v),nl=(legal&~bitof(v))&~bans(s,v);nl.hi&=(1ULL<<17)-1;Bits nk=canon(ns);bool dup=false;for(int i=0;i<n;i++)if(ch[i].k==nk){dup=true;break;}if(dup)continue;auto c=memo.get(nk);ch[n++]={ns,nl,nk,pc(nl),v,c};}std::sort(ch.begin(),ch.begin()+n,[](auto&a,auto&b){int pa=a.c==Memo::L?0:(a.c?2:1),pb=b.c==Memo::L?0:(b.c?2:1);if(pa!=pb)return pa<pb;if(a.n!=b.n)return a.n<b.n;return a.k<b.k;});for(int i=0;i<n;i++){bool r=ch[i].c?ch[i].c==Memo::W:win(ch[i].s,ch[i].l,dep+1);if(!r){memo.put(key,Memo::W);return true;}}memo.put(key,Memo::L);return false;}}
;int main(){try{Verify v(28);v.run();}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
