#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

struct Bits {
    std::uint64_t lo = 0, hi = 0; // bits 0..63, 64..80
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

class FlatMemo81 {
public:
    enum : std::uint32_t { Losing=1, Winning=2 };
    explicit FlatMemo81(unsigned power)
      : lows_(std::size_t{1}<<power), metas_(std::size_t{1}<<power),
        mask_((std::size_t{1}<<power)-1) {}
    inline std::uint32_t get(Bits key) const {
        std::size_t i=mix(key)&mask_;
        while(metas_[i]){
            std::uint32_t m=metas_[i];
            if(lows_[i]==key.lo && (m>>2)==key.hi) return m&3;
            i=(i+1)&mask_;
        }
        return 0;
    }
    inline void put(Bits key,std::uint32_t value){
        std::size_t i=mix(key)&mask_;
        const std::uint32_t meta=(std::uint32_t(key.hi)<<2)|value;
        while(metas_[i]){
            if(lows_[i]==key.lo && (metas_[i]>>2)==key.hi){metas_[i]=meta;return;}
            i=(i+1)&mask_;
        }
        lows_[i]=key.lo; metas_[i]=meta; ++used_;
        if(used_*10 > metas_.size()*8) throw std::runtime_error("memo table over 80%");
    }
    std::size_t used()const{return used_;}
private:
    std::vector<std::uint64_t> lows_;
    std::vector<std::uint32_t> metas_;
    std::size_t mask_,used_=0;
    static inline std::uint64_t mix64(std::uint64_t x){
        x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;
        x^=x>>27;x*=0x94d049bb133111ebULL;
        return x^(x>>31);
    }
    static inline std::uint64_t mix(Bits b){return mix64(b.lo ^ (b.hi*0x9e3779b97f4a7c15ULL));}
};

class Solver9 {
    static constexpr int N=9,V=81;
    using Clock=std::chrono::steady_clock;
    struct TState { std::array<Bits,8> t{}; };
    struct Child { TState ts; Bits legal,key; int count,move; std::uint32_t cached; };
public:
    explicit Solver9(unsigned memo_power=28): completion_(std::size_t(V)*V*V),memo_(memo_power),start_(Clock::now()){
        build_maps(); build_forbidden_quadruples();
    }
    void run(int forced_first=-1){
        TState root{};
        Bits legal{~0ULL,(1ULL<<17)-1};
        bool result;
        if(forced_first<0){
            result=win(root,legal,0);
            std::cout<<"9x9 root: "<<(result?"FIRST":"SECOND")<<"\n";
            if(!result) print_orbit_replies();
            else print_winning_firsts();
        }else{
            TState s=add(root,forced_first);
            Bits bit=bitof(forced_first);
            legal=legal & ~bit;
            result=win(s,legal,1);
            std::cout<<"first move ("<<forced_first%N<<','<<forced_first/N<<") leaves "
                     <<(result?"WIN":"LOSS")<<" for player to move\n";
            if(forced_first==40 && !result) print_center_third_replies(s);
        }
        double sec=std::chrono::duration<double>(Clock::now()-start_).count();
        std::cout<<"forbidden="<<forbidden_count_<<" visited="<<visited_<<" memo="<<memo_.used()
                 <<" maxdepth="<<max_depth_<<" seconds="<<sec<<"\n";
    }
private:
    std::vector<Bits> completion_;
    std::array<std::array<Bits,V>,8> tbit_{};
    FlatMemo81 memo_;
    std::uint64_t forbidden_count_=0,visited_=0;
    int max_depth_=0;
    Clock::time_point start_;

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
        std::cerr<<"built forbidden="<<forbidden_count_<<"\n";
    }
    inline TState add(const TState&s,int v)const{TState r=s;for(int k=0;k<8;++k)r.t[k]=r.t[k]|tbit_[k][v];return r;}
    static inline Bits canonical(const TState&s){Bits r=s.t[0];for(int k=1;k<8;++k)if(s.t[k]<r)r=s.t[k];return r;}
    inline Bits added_bans(Bits state,int v)const{
        int verts[V],k=0;Bits s=state;while(any(s))verts[k++]=take_lsb(s);
        Bits out{};for(int i=0;i<k;++i)for(int j=i+1;j<k;++j){int a=verts[i],b=verts[j],c=v;sort3(a,b,c);out=out|completion_[idx(a,b,c)];}return out;
    }
    bool win(const TState&state,Bits legal,int depth){
        Bits key=canonical(state);auto cached=memo_.get(key);if(cached)return cached==FlatMemo81::Winning;
        ++visited_;if(depth>max_depth_){max_depth_=depth;std::cerr<<"depth "<<depth<<" at "<<visited_<<" states\n";}
        if((visited_&((1ULL<<22)-1))==0){double sec=std::chrono::duration<double>(Clock::now()-start_).count();std::cerr<<"states="<<visited_<<" memo="<<memo_.used()<<" depth="<<depth<<" rate="<<(visited_/sec/1e6)<<" M/s\n";}
        if(!any(legal)){memo_.put(key,FlatMemo81::Losing);return false;}
        std::array<Child,V> ch{};int n=0;Bits moves=legal;
        while(any(moves)){int v=take_lsb(moves);Bits bit=bitof(v);TState ns=add(state,v);Bits nl=(legal&~bit)&~added_bans(state.t[0],v);nl.hi&=(1ULL<<17)-1;Bits nk=canonical(ns);
            bool dup=false;for(int i=0;i<n;++i)if(ch[i].key==nk){dup=true;break;}if(dup)continue;
            auto cv=memo_.get(nk);ch[n++]={ns,nl,nk,popcount(nl),v,cv};
        }
        std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){
            // Known losing child proves current win immediately; known winning goes last.
            int pa=a.cached==FlatMemo81::Losing?0:(a.cached==0?1:2);
            int pb=b.cached==FlatMemo81::Losing?0:(b.cached==0?1:2);
            if(pa!=pb)return pa<pb;if(a.count!=b.count)return a.count<b.count;return a.key<b.key;
        });
        for(int i=0;i<n;++i){bool cw;if(ch[i].cached)cw=ch[i].cached==FlatMemo81::Winning;else cw=win(ch[i].ts,ch[i].legal,depth+1);if(!cw){memo_.put(key,FlatMemo81::Winning);return true;}}
        memo_.put(key,FlatMemo81::Losing);return false;
    }
    void print_center_third_replies(const TState& center){
        std::cout<<"representative second moves and one winning third reply after center:\n";
        for(int a=0;a<=4;++a)for(int b=a;b<=4;++b){
            if(a==4 && b==4) continue;
            int second=b*N+a;
            TState s2=add(center,second);
            bool found=false;
            for(int third=0;third<V;++third){
                if(third==40 || third==second) continue;
                TState s3=add(s2,third);
                if(memo_.get(canonical(s3))==FlatMemo81::Losing){
                    std::cout<<"  second ("<<a<<','<<b<<") -> third ("
                             <<third%N<<','<<third/N<<")\n";
                    found=true; break;
                }
            }
            if(!found) std::cout<<"  second ("<<a<<','<<b<<") -> [not found]\n";
        }
    }
    void print_orbit_replies(){
        std::cout<<"representative first moves and one winning second reply:\n";
        TState root{};
        for(int a=0;a<=4;++a)for(int b=a;b<=4;++b){int first=b*N+a;TState s1=add(root,first);bool found=false;
            for(int second=0;second<V;++second){if(second==first)continue;TState s2=add(s1,second);if(memo_.get(canonical(s2))==FlatMemo81::Losing){std::cout<<"  first ("<<a<<','<<b<<") -> second ("<<second%N<<','<<second/N<<")\n";found=true;break;}}
            if(!found)std::cout<<"  first ("<<a<<','<<b<<") -> [not found]\n";
        }
    }
    void print_winning_firsts(){
        std::cout<<"winning first-move orbit representatives:\n";TState root{};
        for(int a=0;a<=4;++a)for(int b=a;b<=4;++b){int first=b*N+a;TState s=add(root,first);if(memo_.get(canonical(s))==FlatMemo81::Losing)std::cout<<"  ("<<a<<','<<b<<")\n";}
    }
};

int main(int argc,char**argv){try{int first=-1;unsigned pow=28;if(argc>=2)first=std::atoi(argv[1]);if(argc>=3)pow=std::atoi(argv[2]);Solver9 s(pow);s.run(first);}catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<"\n";return 1;}}
