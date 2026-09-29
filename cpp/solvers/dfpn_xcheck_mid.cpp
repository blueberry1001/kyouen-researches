// df-pn vs DFS cross-check on mid-game positions (n=6,7).
// Prints DFS ground truth for a deterministic sample of safe positions.
// The dfpn side is then run per-root via the dfpn binary; this driver only
// emits the position list. A second pass compares outcomes.
#include <array>
#include <algorithm>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Bits {
    std::uint64_t lo = 0, hi = 0;
};
static inline bool operator==(Bits a, Bits b){ return a.lo==b.lo && a.hi==b.hi; }
static inline bool operator<(Bits a, Bits b){ return a.hi<b.hi || (a.hi==b.hi && a.lo<b.lo); }
static inline Bits operator|(Bits a, Bits b){ return {a.lo|b.lo,a.hi|b.hi}; }
static inline Bits operator&(Bits a, Bits b){ return {a.lo&b.lo,a.hi&b.hi}; }
static inline Bits operator~(Bits a){ return {~a.lo,~a.hi}; }
static inline bool any(Bits a){ return a.lo || a.hi; }
static inline int popcount(Bits a){ return std::popcount(a.lo)+std::popcount(a.hi); }
static inline Bits bitof(int p){ return p<64 ? Bits{1ULL<<p,0} : Bits{0,1ULL<<(p-64)}; }
static inline bool has(Bits a,int p){ return p<64 ? ((a.lo>>p)&1) : ((a.hi>>(p-64))&1); }
static inline void setbit(Bits& a,int p){ if(p<64)a.lo|=1ULL<<p;else a.hi|=1ULL<<(p-64); }
static inline int take_lsb(Bits& a){
    if(a.lo){int p=std::countr_zero(a.lo);a.lo&=a.lo-1;return p;}
    int p=std::countr_zero(a.hi);a.hi&=a.hi-1;return p+64;
}

template<int N>
struct Game {
    static constexpr int V=N*N;
    static constexpr std::uint64_t HI_MASK =
        (V>64) ? (((V-64)>=64) ? ~0ULL : ((1ULL<<(V-64))-1ULL)) : 0ULL;
    static long long det3(long long a00,long long a01,long long a02,long long a10,long long a11,long long a12,long long a20,long long a21,long long a22){
        return a00*(a11*a22-a12*a21)-a01*(a10*a22-a12*a20)+a02*(a10*a21-a11*a20);
    }
    static bool forbidden(int a,int b,int c,int d){
        int ids[4]={a,b,c,d};long long m[4][4]{};
        for(int r=0;r<4;++r){long long x=ids[r]%N,y=ids[r]/N;m[r][0]=x*x+y*y;m[r][1]=x;m[r][2]=y;m[r][3]=1;}
        long long det=0;
        for(int col=0;col<4;++col){long long z[3][3]{};for(int r=1;r<4;++r){int q=0;for(int c2=0;c2<4;++c2)if(c2!=col)z[r-1][q++]=m[r][c2];}
            long long md=det3(z[0][0],z[0][1],z[0][2],z[1][0],z[1][1],z[1][2],z[2][0],z[2][1],z[2][2]);
            det+=(col%2==0?1:-1)*m[0][col]*md;
        }return det==0;
    }
    static constexpr std::size_t idx(int a,int b,int c){return(std::size_t(a)*V+b)*V+c;}
    static inline void sort3(int&a,int&b,int&c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);}
    std::vector<Bits> completion_;
    std::array<std::array<Bits,V>,8> tbit_{};
    Game(): completion_(std::size_t(V)*V*V){
        for(int p=0;p<V;++p){int x=p%N,y=p/N;
            int nx[8]={x,N-1-x,x,N-1-x,y,N-1-y,y,N-1-y};
            int ny[8]={y,y,N-1-y,N-1-y,x,x,N-1-x,N-1-x};
            for(int k=0;k<8;++k)tbit_[k][p]=bitof(ny[k]*N+nx[k]);}
        for(int a=0;a<V;++a)for(int b=a+1;b<V;++b)for(int c=b+1;c<V;++c)for(int d=c+1;d<V;++d){
            if(!forbidden(a,b,c,d))continue;int q[4]={a,b,c,d};
            for(int omit=0;omit<4;++omit){int t[3],p=0;for(int j=0;j<4;++j)if(j!=omit)t[p++]=q[j];
                completion_[idx(t[0],t[1],t[2])]=completion_[idx(t[0],t[1],t[2])]|bitof(q[omit]);}}
    }
    struct TState { std::array<Bits,8> t{}; };
    TState add(const TState&s,int v)const{TState r=s;for(int k=0;k<8;++k)r.t[k]=r.t[k]|tbit_[k][v];return r;}
    static Bits canonical(const TState&s){Bits r=s.t[0];for(int k=1;k<8;++k)if(s.t[k]<r)r=s.t[k];return r;}
    Bits added_bans(Bits state,int v)const{
        int verts[V],k=0;Bits s=state;while(any(s))verts[k++]=take_lsb(s);
        Bits out{};for(int i=0;i<k;++i)for(int j=i+1;j<k;++j){int a=verts[i],b=verts[j],c=v;sort3(a,b,c);out=out|completion_[idx(a,b,c)];}return out;
    }
    Bits legal_for(Bits occupied) const {
        int verts[V],k=0;Bits s=occupied;while(any(s))verts[k++]=take_lsb(s);
        Bits danger{};
        for(int i=0;i<k;++i)for(int j=i+1;j<k;++j)for(int l=j+1;l<k;++l){
            danger=danger|completion_[idx(verts[i],verts[j],verts[l])];}
        Bits legal{~0ULL,HI_MASK};
        legal=legal&~occupied&~danger; legal.hi&=HI_MASK;
        return legal;
    }
    bool safe(const std::vector<int>& stones) const {
        for(std::size_t i=0;i<stones.size();++i)
        for(std::size_t j=i+1;j<stones.size();++j)
        for(std::size_t k=j+1;k<stones.size();++k)
        for(std::size_t l=k+1;l<stones.size();++l)
            if(forbidden(stones[i],stones[j],stones[k],stones[l]))return false;
        return true;
    }
};

static std::vector<int> parse_csv(const std::string& s){
    std::vector<int> out; std::stringstream ss(s); std::string tok;
    while(std::getline(ss,tok,',')){ if(!tok.empty()) out.push_back(std::stoi(tok)); }
    return out;
}

// Plain recursive DFS (no memo): ground truth for small positions.
template<int N>
bool dfs_win(Game<N>& g,typename Game<N>::TState state,Bits legal){
    if(!any(legal)) return false;
    Bits moves=legal;
    while(any(moves)){
        int v=take_lsb(moves);
        Bits bit=bitof(v);
        auto ns=g.add(state,v);
        Bits nl=(legal&~bit)&~g.added_bans(state.t[0],v);
        nl.hi&=Game<N>::HI_MASK;
        if(!dfs_win<N>(g,ns,nl)) return true;
    }
    return false;
}

template<int N>
void emit_positions(Game<N>& g,const std::vector<std::vector<int>>& pos);

int main(int argc,char**argv){
    if(argc!=2){ std::cerr<<"usage: xcheck67 SEED\n"; return 2; }
    unsigned seed=unsigned(std::stoul(argv[1]));
    std::srand(seed);
    {
        Game<6> g;
        std::vector<std::vector<int>> pos;
        // deterministic sample: 1-stone reps + random safe 2..5-stone sets
        for(int v=0;v<36;++v) pos.push_back({v});
        int tries=0;
        while((int)pos.size()<60 && tries++<2000){
            int k=2+std::rand()%4;
            std::vector<int> s;
            for(int i=0;i<k;++i) s.push_back(std::rand()%36);
            std::sort(s.begin(),s.end()); s.erase(std::unique(s.begin(),s.end()),s.end());
            if((int)s.size()!=k) continue;
            if(!g.safe(s)) continue;
            pos.push_back(s);
        }
        std::cout<<"## n=6 "<<pos.size()<<" positions\n";
        for(const auto& stones: pos){
            typename Game<6>::TState st{};
            Bits occ{};
            for(int v:stones){ st=g.add(st,v); setbit(occ,v); }
            Bits legal=g.legal_for(occ);
            bool dw=dfs_win<6>(g,st,legal);
            std::cout<<"n=6 stones=";
            for(std::size_t i=0;i<stones.size();++i){ if(i)std::cout<<","; std::cout<<stones[i]; }
            std::cout<<" dfs="<<(dw?"WIN":"LOSS")<<"\n";
        }
    }
    {
        Game<7> g;
        std::vector<std::vector<int>> pos;
        for(int v=0;v<49;++v) pos.push_back({v});
        int tries=0;
        while((int)pos.size()<80 && tries++<3000){
            int k=2+std::rand()%4;
            std::vector<int> s;
            for(int i=0;i<k;++i) s.push_back(std::rand()%49);
            std::sort(s.begin(),s.end()); s.erase(std::unique(s.begin(),s.end()),s.end());
            if((int)s.size()!=k) continue;
            if(!g.safe(s)) continue;
            pos.push_back(s);
        }
        std::cout<<"## n=7 "<<pos.size()<<" positions\n";
        for(const auto& stones: pos){
            typename Game<7>::TState st{};
            Bits occ{};
            for(int v:stones){ st=g.add(st,v); setbit(occ,v); }
            Bits legal=g.legal_for(occ);
            bool dw=dfs_win<7>(g,st,legal);
            std::cout<<"n=7 stones=";
            for(std::size_t i=0;i<stones.size();++i){ if(i)std::cout<<","; std::cout<<stones[i]; }
            std::cout<<" dfs="<<(dw?"WIN":"LOSS")<<"\n";
        }
    }
    return 0;
}
