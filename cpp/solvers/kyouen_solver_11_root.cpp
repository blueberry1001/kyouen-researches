// 11x11 AND/OR proof-search solver.
//
// Why this file exists: full layer-by-layer DP for 11x11 is dead.
// A union bound from F_11 = 95,670 alone gives safe(6) >= 3.19e9
// (>= 3.99e8 D4 orbits) and safe(7) >= 3.83e10 (>= 4.78e9 D4 orbits,
// 76 GB at 16 B/state before any index/Grundy/sort workspace).
// Enumerating every safe position is therefore off the table.
//
// But the winner only needs proof search, not enumeration:
//   N-position: find ONE P-child and stop.
//   P-position: confirm every child is N.
// If 11x11 is a first-player win, a single P one-stone move out of the
// 21 D4-distinct first moves ends the game. If it is a second-player win,
// all 21 one-stone orbits must be shown N.
//
// This solver is a mechanical port of cpp/solvers/kyouen_solver_10_root.cpp
// (which classified all 100 first moves of 10x10) to V = 121, with one
// correctness fix the port forced: FlatMemo81 stores (key.hi << 2) | value
// in a uint32_t meta, silently truncating key.hi above 30 bits. For n = 9
// (hi uses 17 bits) that is harmless; for n = 10 (36 bits) high-board keys
// already miss the memo; for n = 11 (57 bits) the memo would be ~dead.
// FlatMemo121 below stores the full (lo, hi) key.
//
// State: 121 points fit in two uint64_t words. D4 canonical key = min of
// the 8 transformed images, exactly as in the 9/10 solvers.
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
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

// Full 121-bit key memo. power=27 -> 1.34e8 slots x 17 B ~= 2.2 GB.
// power=24 -> 1.68e7 slots x 17 B ~= 285 MB (for 16-way parallel runs).
class FlatMemo121 {
public:
    enum : std::uint32_t { Unknown=0, Losing=1, Winning=2 };
    explicit FlatMemo121(unsigned power)
      : n_(std::size_t{1}<<power), mask_(n_-1),
        lo_(n_,0), hi_(n_,0), st_(n_,0) {}
    inline std::uint32_t get(std::uint64_t klo,std::uint64_t khi) const {
        std::size_t i=mix(klo,khi)&mask_;
        while(st_[i]){
            if(lo_[i]==klo && hi_[i]==khi) return st_[i];
            i=(i+1)&mask_;
        }
        return 0;
    }
    inline void put(std::uint64_t klo,std::uint64_t khi,std::uint32_t value){
        std::size_t i=mix(klo,khi)&mask_;
        while(st_[i]){
            if(lo_[i]==klo && hi_[i]==khi){st_[i]=(std::uint8_t)value;return;}
            i=(i+1)&mask_;
        }
        lo_[i]=klo; hi_[i]=khi; st_[i]=(std::uint8_t)value; ++used_;
        if(used_*10 > n_*8) throw std::runtime_error("memo table over 80%");
    }
    std::size_t used()const{return used_;}
    std::size_t capacity()const{return n_;}
private:
    std::size_t n_,mask_,used_=0;
    std::vector<std::uint64_t> lo_,hi_;
    std::vector<std::uint8_t> st_;
    static inline std::uint64_t mix64(std::uint64_t x){
        x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;
        x^=x>>27;x*=0x94d049bb133111ebULL;
        return x^(x>>31);
    }
    static inline std::uint64_t mix(std::uint64_t a,std::uint64_t b){
        return mix64(a ^ (b*0x9e3779b97f4a7c15ULL));
    }
};

class Solver11 {
    static constexpr int N=11,V=121;
    static constexpr std::uint64_t HI_MASK=(1ULL<<57)-1; // points 64..120
    using Clock=std::chrono::steady_clock;
    struct TState { std::array<Bits,8> t{}; };
    struct Child { TState ts; Bits legal,key; int count,move; std::uint32_t cached; };
public:
    struct Result {
        bool win;
        std::uint64_t visited_delta;
        std::size_t memo_used;
        double seconds;
    };

    explicit Solver11(unsigned memo_power=27): completion_(std::size_t(V)*V*V),memo_(memo_power){
        build_maps(); build_forbidden_quadruples();
    }

    Result solve_root(const std::vector<int>& stones){
        validate_root(stones);
        TState state{};
        Bits occupied{};
        for(int v:stones){ state=add(state,v); setbit(occupied,v); }
        Bits legal=legal_for(occupied);
        const auto before=visited_;
        const auto start=Clock::now();
        bool w=win(state,legal,int(stones.size()));
        double sec=std::chrono::duration<double>(Clock::now()-start).count();
        return {w,visited_-before,memo_.used(),sec};
    }

    std::uint64_t forbidden_count() const { return forbidden_count_; }

private:
    std::vector<Bits> completion_;
    std::array<std::array<Bits,V>,8> tbit_{};
    FlatMemo121 memo_;
    std::uint64_t forbidden_count_=0,visited_=0;

    static long long det3(long long a00,long long a01,long long a02,long long a10,long long a11,long long a12,long long a20,long long a21,long long a22){
        return a00*(a11*a22-a12*a21)-a01*(a10*a22-a12*a20)+a02*(a10*a21-a11*a20);
    }
    static bool forbidden(int a,int b,int c,int d){
        int ids[4]={a,b,c,d};long long m[4][4]{};
        for(int r=0;r<4;++r){long long x=ids[r]%N,y=ids[r]/N;m[r][0]=x*x+y*y;m[r][1]=x;m[r][2]=y;m[r][3]=1;}
        long long determinant=0;
        for(int col=0;col<4;++col){long long z[3][3]{};for(int r=1;r<4;++r){int q=0;for(int c2=0;c2<4;++c2)if(c2!=col)z[r-1][q++]=m[r][c2];}
            long long md=det3(z[0][0],z[0][1],z[0][2],z[1][0],z[1][1],z[1][2],z[2][0],z[2][1],z[2][2]);
            determinant+=(col%2==0?1:-1)*m[0][col]*md;
        }return determinant==0;
    }
    static constexpr std::size_t idx(int a,int b,int c){return(std::size_t(a)*V+b)*V+c;}
    static inline void sort3(int&a,int&b,int&c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);}
    void build_maps(){
        for(int p=0;p<V;++p){int x=p%N,y=p/N;int nx[8]={x,N-1-x,x,N-1-x,y,N-1-y,y,N-1-y};int ny[8]={y,y,N-1-y,N-1-y,x,x,N-1-x,N-1-x};
            for(int k=0;k<8;++k)tbit_[k][p]=bitof(ny[k]*N+nx[k]);
        }
    }
    void build_forbidden_quadruples(){
        for(int a=0;a<V;++a)for(int b=a+1;b<V;++b)for(int c=b+1;c<V;++c)for(int d=c+1;d<V;++d){
            if(!forbidden(a,b,c,d))continue;++forbidden_count_;int q[4]={a,b,c,d};
            for(int omit=0;omit<4;++omit){int t[3],p=0;for(int j=0;j<4;++j)if(j!=omit)t[p++]=q[j];completion_[idx(t[0],t[1],t[2])]=completion_[idx(t[0],t[1],t[2])]|bitof(q[omit]);}
        }
    }
    inline TState add(const TState&s,int v)const{TState r=s;for(int k=0;k<8;++k)r.t[k]=r.t[k]|tbit_[k][v];return r;}
    static inline Bits canonical(const TState&s){Bits r=s.t[0];for(int k=1;k<8;++k)if(s.t[k]<r)r=s.t[k];return r;}
    inline Bits added_bans(Bits state,int v)const{
        int verts[V],k=0;Bits s=state;while(any(s))verts[k++]=take_lsb(s);
        Bits out{};for(int i=0;i<k;++i)for(int j=i+1;j<k;++j){int a=verts[i],b=verts[j],c=v;sort3(a,b,c);out=out|completion_[idx(a,b,c)];}return out;
    }
    Bits legal_for(Bits occupied) const {
        int verts[V],k=0;Bits s=occupied;while(any(s))verts[k++]=take_lsb(s);
        Bits danger{};
        for(int i=0;i<k;++i)for(int j=i+1;j<k;++j)for(int l=j+1;l<k;++l){
            int a=verts[i],b=verts[j],c=verts[l];
            danger= danger | completion_[idx(a,b,c)];
        }
        Bits legal{~0ULL,HI_MASK};
        legal=legal & ~occupied & ~danger;
        legal.hi&=HI_MASK;
        return legal;
    }
    void validate_root(const std::vector<int>& stones) const {
        Bits seen{};
        for(int v:stones){
            if(v<0||v>=V) throw std::runtime_error("root point out of range");
            if(has(seen,v)) throw std::runtime_error("duplicate root point");
            setbit(seen,v);
        }
        for(std::size_t i=0;i<stones.size();++i)
        for(std::size_t j=i+1;j<stones.size();++j)
        for(std::size_t k=j+1;k<stones.size();++k)
        for(std::size_t l=k+1;l<stones.size();++l)
            if(forbidden(stones[i],stones[j],stones[k],stones[l]))
                throw std::runtime_error("unsafe root contains forbidden quadruple");
    }
    bool win(const TState&state,Bits legal,int depth){
        (void)depth;
        Bits key=canonical(state);
        auto cached=memo_.get(key.lo,key.hi);
        if(cached)return cached==FlatMemo121::Winning;
        ++visited_;
        if(!any(legal)){memo_.put(key.lo,key.hi,FlatMemo121::Losing);return false;}
        std::array<Child,V> ch{};int n=0;Bits moves=legal;
        while(any(moves)){int v=take_lsb(moves);Bits bit=bitof(v);TState ns=add(state,v);Bits nl=(legal&~bit)&~added_bans(state.t[0],v);nl.hi&=HI_MASK;Bits nk=canonical(ns);
            bool dup=false;for(int i=0;i<n;++i)if(ch[i].key==nk){dup=true;break;}if(dup)continue;
            auto cv=memo_.get(nk.lo,nk.hi);ch[n++]={ns,nl,nk,popcount(nl),v,cv};
        }
        std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){
            int pa=a.cached==FlatMemo121::Losing?0:(a.cached==0?1:2);
            int pb=b.cached==FlatMemo121::Losing?0:(b.cached==0?1:2);
            if(pa!=pb)return pa<pb;if(a.count!=b.count)return a.count<b.count;return a.key<b.key;
        });
        for(int i=0;i<n;++i){bool cw;if(ch[i].cached)cw=ch[i].cached==FlatMemo121::Winning;else cw=win(ch[i].ts,ch[i].legal,depth+1);if(!cw){memo_.put(key.lo,key.hi,FlatMemo121::Winning);return true;}}
        memo_.put(key.lo,key.hi,FlatMemo121::Losing);return false;
    }
};

static std::string outcome(bool win){ return win?"WIN":"LOSS"; }

// D4-distinct one-stone first moves: fundamental domain {(x,y): 0<=x<=5, 0<=y<=x}.
// 1+2+3+4+5+6 = 21 orbits. Center (5,5) first: strongest candidate for a P-move.
static std::vector<int> first_move_reps(){
    std::vector<int> reps;
    reps.push_back(5*11+5); // center first
    reps.push_back(0);      // corner
    for(int x=0;x<=5;++x)for(int y=0;y<=x;++y){
        int v=y*11+x;
        if(v==5*11+5||v==0)continue;
        reps.push_back(v);
    }
    return reps;
}

int main(int argc,char**argv){
    try{
        unsigned pow=27;
        bool reps=false;
        for(int i=1;i<argc;++i){
            std::string a=argv[i];
            if(a=="--reps")reps=true;
            else if(a.rfind("--memo=",0)==0)pow=unsigned(std::stoul(a.substr(7)));
            else { std::cerr<<"usage: "<<argv[0]<<" [--reps] [--memo=N]\n"; return 2; }
        }
        Solver11 solver(pow);
        std::cerr<<"built forbidden="<<solver.forbidden_count()
                 <<" (expect 95670)"<<std::endl;
        if(solver.forbidden_count()!=95670){
            std::cerr<<"F_11 mismatch, abort\n";return 1;
        }
        if(!reps){ std::cerr<<"nothing to do without --reps\n"; return 2; }
        std::cout<<"v,x,y,outcome,visited,seconds,memo_used\n";
        std::cout.flush();
        for(int v : first_move_reps()){
            auto r=solver.solve_root({v});
            std::cout<<v<<","<<(v%11)<<","<<(v/11)<<","
                     <<outcome(r.win)<<","<<r.visited_delta<<","
                     <<r.seconds<<","<<r.memo_used<<"\n";
            std::cout.flush();
            // A single LOSS (P-position) one-stone move proves the empty
            // board N: the first player wins. Stop early.
            if(!r.win){
                std::cout<<"# FIRST_PLAYER_WIN via "<<v<<"\n";
                return 0;
            }
        }
        std::cout<<"# SECOND_PLAYER_WIN (all 21 first moves WIN)\n";
        return 0;
    }catch(const std::exception&e){
        std::cerr<<"error: "<<e.what()<<"\n";return 1;
    }
}
