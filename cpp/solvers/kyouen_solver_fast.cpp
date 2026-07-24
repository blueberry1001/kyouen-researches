#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <vector>

class FlatMemo {
public:
    enum : std::uint8_t { Empty = 0, Losing = 1, Winning = 2 };
    explicit FlatMemo(unsigned power)
        : keys_(std::size_t{1} << power), values_(std::size_t{1} << power, Empty),
          mask_((std::size_t{1} << power) - 1) {}

    inline std::uint8_t get(std::uint64_t key) const {
        std::size_t i = mix(key) & mask_;
        while (values_[i] != Empty) {
            if (keys_[i] == key) return values_[i];
            i = (i + 1) & mask_;
        }
        return Empty;
    }
    inline void put(std::uint64_t key, std::uint8_t value) {
        std::size_t i = mix(key) & mask_;
        while (values_[i] != Empty) {
            if (keys_[i] == key) { values_[i] = value; return; }
            i = (i + 1) & mask_;
        }
        keys_[i] = key;
        values_[i] = value;
        ++used_;
        if (used_ * 10 > values_.size() * 8)
            throw std::runtime_error("memo table over 80%");
    }
    std::size_t used() const { return used_; }
    std::uint8_t peek(std::uint64_t key) const { return get(key); }
private:
    std::vector<std::uint64_t> keys_;
    std::vector<std::uint8_t> values_;
    std::size_t mask_, used_ = 0;
    static inline std::uint64_t mix(std::uint64_t x) {
        x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27; x *= 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
};

class Solver8 {
    static constexpr int N = 8;
    static constexpr int V = 64;
public:
    explicit Solver8(unsigned memo_power = 27)
        : completion_(std::size_t(V)*V*V), memo_(memo_power), start_(Clock::now()) {
        build_forbidden_quadruples();
        verify_transforms();
    }

    void run(int forced_first = -1) {
        bool result;
        if (forced_first < 0) {
            result = win(0, ~0ULL, 0);
            std::cout << "8x8 root: " << (result ? "FIRST" : "SECOND") << "\n";
            if (!result) print_orbit_replies();
        } else {
            const std::uint64_t bit = 1ULL << forced_first;
            // first player has placed forced_first; it is now second player's turn.
            result = win(bit, ~bit, 1);
            std::cout << "first move (" << forced_first%8 << ',' << forced_first/8 << ") leaves "
                      << (result ? "WIN for player to move" : "LOSS for player to move") << "\n";
        }
        std::cout << "forbidden=" << forbidden_count_ << " visited=" << visited_
                  << " memo=" << memo_.used() << " maxdepth=" << max_depth_ << "\n";
    }

private:
    void print_orbit_replies() {
        std::cout << "representative first moves and one winning second reply:\n";
        for (int a = 0; a <= 3; ++a) {
            for (int b = a; b <= 3; ++b) {
                const int first = b * 8 + a;
                const std::uint64_t s1 = 1ULL << first;
                bool found = false;
                for (int second = 0; second < 64; ++second) {
                    if (second == first) continue;
                    const std::uint64_t s2 = s1 | (1ULL << second);
                    if (memo_.peek(canonical(s2)) == FlatMemo::Losing) {
                        std::cout << "  first (" << a << ',' << b << ") -> second ("
                                  << second%8 << ',' << second/8 << ")\n";
                        found = true;
                        break;
                    }
                }
                if (!found) std::cout << "  first (" << a << ',' << b << ") -> [not found in memo]\n";
            }
        }
    }

    using Clock = std::chrono::steady_clock;
    struct Child { std::uint64_t state, legal; std::uint64_t key; int count; int move; };
    std::vector<std::uint64_t> completion_;
    FlatMemo memo_;
    std::uint64_t forbidden_count_ = 0, visited_ = 0;
    int max_depth_ = 0;
    Clock::time_point start_;

    static long long det3(long long a00,long long a01,long long a02,
                          long long a10,long long a11,long long a12,
                          long long a20,long long a21,long long a22) {
        return a00*(a11*a22-a12*a21)-a01*(a10*a22-a12*a20)+a02*(a10*a21-a11*a20);
    }
    static bool forbidden(int a,int b,int c,int d) {
        int ids[4]={a,b,c,d}; long long m[4][4]{};
        for(int r=0;r<4;++r){ long long x=ids[r]%8,y=ids[r]/8;
            m[r][0]=x*x+y*y; m[r][1]=x; m[r][2]=y; m[r][3]=1;
        }
        long long determinant=0;
        for(int col=0;col<4;++col){ long long z[3][3]{};
            for(int r=1;r<4;++r){int q=0;for(int c2=0;c2<4;++c2)if(c2!=col)z[r-1][q++]=m[r][c2];}
            long long md=det3(z[0][0],z[0][1],z[0][2],z[1][0],z[1][1],z[1][2],z[2][0],z[2][1],z[2][2]);
            determinant += (col%2==0?1:-1)*m[0][col]*md;
        }
        return determinant==0;
    }
    static constexpr std::size_t idx(int a,int b,int c){return (std::size_t(a)*V+b)*V+c;}
    static inline void sort3(int& a,int& b,int& c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);}
    void build_forbidden_quadruples(){
        for(int a=0;a<V;++a)for(int b=a+1;b<V;++b)for(int c=b+1;c<V;++c)for(int d=c+1;d<V;++d){
            if(!forbidden(a,b,c,d))continue; ++forbidden_count_; int q[4]={a,b,c,d};
            for(int omit=0;omit<4;++omit){int t[3],p=0;for(int j=0;j<4;++j)if(j!=omit)t[p++]=q[j];
                completion_[idx(t[0],t[1],t[2])] |= 1ULL<<q[omit];
            }
        }
    }

    static inline std::uint64_t flip_h(std::uint64_t x) {
        x = ((x >> 1) & 0x5555555555555555ULL) | ((x & 0x5555555555555555ULL) << 1);
        x = ((x >> 2) & 0x3333333333333333ULL) | ((x & 0x3333333333333333ULL) << 2);
        x = ((x >> 4) & 0x0f0f0f0f0f0f0f0fULL) | ((x & 0x0f0f0f0f0f0f0f0fULL) << 4);
        return x;
    }
    static inline std::uint64_t flip_v(std::uint64_t x) { return __builtin_bswap64(x); }
    static inline std::uint64_t transpose(std::uint64_t x) {
        std::uint64_t t;
        t = (x ^ (x << 7)) & 0x5500550055005500ULL; x ^= t ^ (t >> 7);
        t = (x ^ (x <<14)) & 0x3333000033330000ULL; x ^= t ^ (t >>14);
        t = (x ^ (x <<28)) & 0x0f0f0f0f00000000ULL; x ^= t ^ (t >>28);
        return x;
    }
    static inline std::uint64_t canonical(std::uint64_t x) {
        std::uint64_t h=flip_h(x), v=flip_v(x), hv=flip_v(h);
        std::uint64_t t=transpose(x), th=flip_h(t), tv=flip_v(t), thv=flip_v(th);
        return std::min({x,h,v,hv,t,th,tv,thv});
    }
    static std::uint64_t slow_transform(std::uint64_t s,int kind){
        std::uint64_t out=0;
        while(s){int p=std::countr_zero(s);s&=s-1;int x=p%8,y=p/8,nx=x,ny=y;
            switch(kind){case 0:break;case 1:nx=7-x;break;case 2:ny=7-y;break;case 3:nx=7-x;ny=7-y;break;
                case 4:nx=y;ny=x;break;case 5:nx=7-y;ny=x;break;case 6:nx=y;ny=7-x;break;case 7:nx=7-y;ny=7-x;break;}
            out|=1ULL<<(ny*8+nx);
        }return out;
    }
    void verify_transforms(){
        std::uint64_t tests[]={1ULL,1ULL<<7,1ULL<<56,1ULL<<63,0x0123456789abcdefULL,0x8040201008040201ULL};
        for(auto x:tests){std::uint64_t c=x;for(int k=1;k<8;++k)c=std::min(c,slow_transform(x,k));
            if(canonical(x)!=c)throw std::runtime_error("bitboard transform verification failed");}
    }

    inline std::uint64_t added_bans(std::uint64_t state,int v) const {
        int verts[64],k=0; for(auto s=state;s;s&=s-1)verts[k++]=std::countr_zero(s);
        std::uint64_t out=0;
        for(int i=0;i<k;++i)for(int j=i+1;j<k;++j){int a=verts[i],b=verts[j],c=v;sort3(a,b,c);out|=completion_[idx(a,b,c)];}
        return out;
    }

    bool win(std::uint64_t state,std::uint64_t legal,int depth){
        const std::uint64_t key=canonical(state);
        auto cached=memo_.get(key); if(cached)return cached==FlatMemo::Winning;
        ++visited_; if(depth>max_depth_){max_depth_=depth; std::cerr<<"depth "<<depth<<" at "<<visited_<<" states\n";}
        if((visited_ & ((1ULL<<20)-1))==0){
            double sec=std::chrono::duration<double>(Clock::now()-start_).count();
            std::cerr<<"states="<<visited_<<" memo="<<memo_.used()<<" depth="<<depth<<" rate="<<(visited_/sec/1e6)<<" M/s\n";
        }
        if(!legal){memo_.put(key,FlatMemo::Losing);return false;}

        std::array<Child,64> ch{}; int n=0;
        auto moves=legal;
        while(moves){int v=std::countr_zero(moves);moves&=moves-1;std::uint64_t bit=1ULL<<v;
            std::uint64_t ns=state|bit;
            std::uint64_t nl=(legal&~bit)&~added_bans(state,v);
            std::uint64_t nk=canonical(ns);
            bool dup=false;for(int i=0;i<n;++i)if(ch[i].key==nk){dup=true;break;}if(dup)continue;
            ch[n++]={ns,nl,nk,std::popcount(nl),v};
        }
        std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){
            if(a.count!=b.count)return a.count<b.count;
            return a.key<b.key;
        });
        for(int i=0;i<n;++i){if(!win(ch[i].state,ch[i].legal,depth+1)){memo_.put(key,FlatMemo::Winning);return true;}}
        memo_.put(key,FlatMemo::Losing);return false;
    }
};

int main(int argc,char**argv){
    try{
        int first=-1; unsigned pow=27;
        if(argc>=2)first=std::atoi(argv[1]);
        if(argc>=3)pow=std::atoi(argv[2]);
        Solver8 s(pow);s.run(first);
    }catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<"\n";return 1;}
}
