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
// ReplaceMemo121 below stores the full (lo, hi) key.
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

// Fixed-capacity memo with replacement. The game graph is a DAG (stones
// strictly increase along every edge), so evicting a settled entry can
// never corrupt the result -- at worst it forces recomputation of that
// subtree. The table therefore never stops the search: when the probe
// window is full, a put replaces the occupant of its home slot.
// Every key lives within PROBE slots of its home, so get searches the
// same window and both operations always terminate, even at 100% load.
class ReplaceMemo121 {
public:
    enum : std::uint32_t { Unknown=0, Losing=1, Winning=2 };
    static constexpr int PROBE = 32;
    explicit ReplaceMemo121(unsigned power)
      : n_(std::size_t{1}<<power), mask_(n_-1),
        lo_(n_,0), hi_(n_,0), st_(n_,0) {}
    inline std::uint32_t get(std::uint64_t klo,std::uint64_t khi) {
        std::size_t i=mix(klo,khi)&mask_;
        int j=0;
        for(;j<PROBE;++j){
            if(!st_[i]){ ++misses_; probe_sum_+=j+1; ++probe_n_; return 0; }
            if(lo_[i]==klo && hi_[i]==khi){ ++hits_; probe_sum_+=j+1; ++probe_n_; return st_[i]; }
            i=(i+1)&mask_;
        }
        ++misses_; probe_sum_+=j; ++probe_n_; return 0;
    }
    inline void put(std::uint64_t klo,std::uint64_t khi,std::uint32_t value){
        std::size_t h=mix(klo,khi)&mask_;
        std::size_t i=h;
        for(int j=0;j<PROBE;++j){
            if(!st_[i]){
                lo_[i]=klo;hi_[i]=khi;st_[i]=(std::uint8_t)value;
                ++used_;++puts_new_;return;
            }
            if(lo_[i]==klo && hi_[i]==khi){
                if(st_[i]!=value){st_[i]=(std::uint8_t)value;++puts_update_;}
                return;
            }
            i=(i+1)&mask_;
        }
        if(lo_[h]==klo && hi_[h]==khi){ st_[h]=(std::uint8_t)value;++puts_update_;return; }
        lo_[h]=klo;hi_[h]=khi;st_[h]=(std::uint8_t)value;++evictions_;
    }
    std::size_t used()const{return used_;}
    std::size_t capacity()const{return n_;}
    std::uint64_t used_=0;
    std::uint64_t hits_=0, misses_=0, puts_new_=0, puts_update_=0, evictions_=0;
    std::uint64_t probe_sum_=0, probe_n_=0;
    void counters(std::uint64_t& hits, std::uint64_t& misses,
                  std::uint64_t& puts_new, std::uint64_t& puts_update,
                  std::uint64_t& evictions,
                  double& avg_probe) const {
        hits=hits_; misses=misses_; puts_new=puts_new_;
        puts_update=puts_update_; evictions=evictions_;
        avg_probe = probe_n_ ? (double)probe_sum_/(double)probe_n_ : 0.0;
    }
private:
    std::size_t n_,mask_;
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

static bool memo_key_width_self_test(){
    // Include the old 30-bit truncation boundary, board point 120 (hi bit
    // 56), and bit 127: this memo promises to retain both complete words.
    const std::array<Bits,9> keys{{
        {0,0},
        {0x0123456789abcdefULL,12345ULL},
        {0x0123456789abcdefULL,(1ULL<<30)|12345ULL},
        {0x0123456789abcdefULL,(1ULL<<35)|12345ULL},
        {0x0123456789abcdefULL,(1ULL<<56)|12345ULL},
        {0x0123456789abcdefULL,(1ULL<<63)|12345ULL},
        {0xfedcba9876543210ULL,12345ULL},
        {~0ULL,~0ULL},
        {1ULL<<63,0}
    }};
    ReplaceMemo121 memo(4);
    for(std::size_t i=0;i<keys.size();++i){
        const auto value=i%2 ? ReplaceMemo121::Winning : ReplaceMemo121::Losing;
        memo.put(keys[i].lo,keys[i].hi,value);
        if(memo.used()!=i+1) return false;
        for(std::size_t j=0;j<keys.size();++j){
            const auto expected=j>i ? ReplaceMemo121::Unknown :
                (j%2 ? ReplaceMemo121::Winning : ReplaceMemo121::Losing);
            if(memo.get(keys[j].lo,keys[j].hi)!=expected) return false;
        }
    }
    memo.put(keys[2].lo,keys[2].hi,ReplaceMemo121::Winning);
    if(memo.used()!=keys.size()) return false;
    for(std::size_t j=0;j<keys.size();++j){
        const auto expected=(j==2 || j%2) ? ReplaceMemo121::Winning : ReplaceMemo121::Losing;
        if(memo.get(keys[j].lo,keys[j].hi)!=expected) return false;
    }

    // One slot forces every hash to collide and exercises replacement and
    // probe wraparound. Eviction may cause a miss, never a false key hit.
    ReplaceMemo121 collision(0);
    for(std::size_t i=0;i<keys.size();++i){
        collision.put(keys[i].lo,keys[i].hi,ReplaceMemo121::Losing);
        if(collision.used()!=1) return false;
        for(std::size_t j=0;j<keys.size();++j){
            const auto expected=i==j ? ReplaceMemo121::Losing : ReplaceMemo121::Unknown;
            if(collision.get(keys[j].lo,keys[j].hi)!=expected) return false;
        }
    }
    return true;
}

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
    std::uint64_t visited() const { return visited_; }
    void child_stats(std::uint64_t& probe_hit, std::uint64_t& used,
                     std::uint64_t& unused, std::uint64_t& loss_cut,
                     std::uint64_t& rec_cut) const {
        probe_hit=child_probe_hit_; used=child_used_;
        unused=child_unused_; loss_cut=child_loss_cut_; rec_cut=rec_loss_cut_;
    }
    std::size_t memo_used() const { return memo_.used(); }
    std::size_t memo_capacity() const { return memo_.capacity(); }
    void memo_counters(std::uint64_t& hits, std::uint64_t& misses,
                       std::uint64_t& puts_new, std::uint64_t& puts_update,
                       std::uint64_t& evictions, double& avg_probe) const {
        memo_.counters(hits, misses, puts_new, puts_update, evictions, avg_probe);
    }
    void set_deadline(double s){
        deadline_s_=s;
        t0_=std::chrono::steady_clock::now();
    }
    void set_log(const std::string& path){
        if(path.empty()) return;
        log_file_.open(path, std::ios::out | std::ios::app);
        if(!log_file_) throw std::runtime_error("cannot open log file");
        log_= &log_file_;
    }
    void set_csv(const std::string& path){
        if(path.empty()) return;
        csv_file_.open(path, std::ios::out | std::ios::app);
        if(!csv_file_) throw std::runtime_error("cannot open csv file");
        csv_= &csv_file_;
    }
    std::ostream& log() { return *log_; }
    std::ostream& csv() { return *csv_; }
    void log_flush() { log_->flush(); }
    void csv_flush() { csv_->flush(); }
    void depth_hist(std::uint64_t* out, int n) const {
        for(int i=0;i<n;++i) out[i]=depth_hist_[i<64?i:63];
    }
    void depth_stats(std::uint64_t* h, std::uint64_t* mv,
                     double* hr, int n) const {
        for(int i=0;i<n;++i){
            int d=i<64?i:63;
            h[i]=depth_hist_[d]; mv[i]=d_moves_[d];
            std::uint64_t t=d_hit_[d]+d_miss_[d];
            hr[i]= t ? 100.0*(double)d_hit_[d]/(double)t : -1.0;
        }
    }
    int max_depth() const { return max_depth_; }

private:
    std::vector<Bits> completion_;
    std::array<std::array<Bits,V>,8> tbit_{};
    ReplaceMemo121 memo_;
    std::uint64_t forbidden_count_=0,visited_=0;
    std::uint64_t depth_hist_[64]={};
    std::uint64_t d_hit_[64]={}, d_miss_[64]={}, d_put_[64]={}, d_moves_[64]={};
    // TT effectiveness: how much work the child pre-probe actually saves.
    // child_probe_hit = pre-probe get() returned a value.
    // child_used      = ... and that child was reached before cutoff/return,
    //                     i.e. its cached value decided something.
    // child_unused    = ... but the loop returned before reaching it.
    // child_loss_cut  = ... and it was a cached LOSS that ended the node.
    // rec_loss_cut    = uncached child explored recursively, returned LOSS,
    //                     and ended the node.
    // cached_loss_cut / (cached_loss_cut + rec_loss_cut) = how much of the
    // tree-shrinking work the TT does. A cached LOSS kills not just that
    // child but every remaining sibling, so it is worth far more than one
    // saved node.
    std::uint64_t child_probe_hit_=0, child_used_=0, child_unused_=0, child_loss_cut_=0;
    std::uint64_t rec_loss_cut_=0;
    int max_depth_=0;
    double deadline_s_=0;
    std::chrono::steady_clock::time_point t0_;
    bool timed_out_=false;
    std::ostream* log_=&std::cerr;
    std::ofstream log_file_;
    std::ostream* csv_=&std::cout;
    std::ofstream csv_file_;

    void heartbeat(int depth){
        if(deadline_s_<=0) return;
        double el=std::chrono::duration<double>(
            std::chrono::steady_clock::now()-t0_).count();
        if(el < 5.0 && visited_ < (std::uint64_t(1)<<20)) return;
        std::uint64_t hits,misses,pn,pu,ev; double ap;
        memo_counters(hits,misses,pn,pu,ev,ap);
        double total=(double)(hits+misses);
        double hr = total>0 ? 100.0*(double)hits/total : 0.0;
        double cused = visited_ ? 100.0*(double)child_used_/(double)visited_ : 0.0;
        std::uint64_t tot_cut = child_loss_cut_+rec_loss_cut_;
        double cfrac = tot_cut ? 100.0*(double)child_loss_cut_/(double)tot_cut : -1.0;
        *log_ << "[hb] t=" << (long long)el << "s"
                  << " visited=" << visited_
                  << " depth=" << depth << " maxdepth=" << max_depth_
                  << " memo=" << memo_.used() << "/" << memo_.capacity()
                  << " hit=" << hr << "%"
                  << " puts_new=" << pn << " evict=" << ev
                  << " avgprobe=" << ap
                  << " child_used/vis=" << cused << "%"
                  << " loss_cut_cached=" << child_loss_cut_
                  << " loss_cut_rec=" << rec_loss_cut_;
        if(cfrac>=0) *log_ << " cached_cut_frac=" << cfrac << "%";
        *log_ << std::endl;
        log_->flush();
        if(el>=deadline_s_) throw std::runtime_error("TIME_BUDGET");
    }

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
        // Heartbeat + deadline check every 2^20 node entries: cheap enough
        // to be ~free, frequent enough (~1M nodes) to bound wasted work.
        if((visited_ & ((std::uint64_t(1)<<20)-1))==0) heartbeat(depth);
        int dd = depth<64?depth:63;
        Bits key=canonical(state);
        ++visited_;
        ++depth_hist_[dd];
        if(depth>max_depth_)max_depth_=depth;
        if(!any(legal)){memo_.put(key.lo,key.hi,ReplaceMemo121::Losing);++d_put_[dd];return false;}
        std::array<Child,V> ch{};int n=0;Bits moves=legal;
        while(any(moves)){int v=take_lsb(moves);Bits bit=bitof(v);TState ns=add(state,v);Bits nl=(legal&~bit)&~added_bans(state.t[0],v);nl.hi&=HI_MASK;Bits nk=canonical(ns);
            bool dup=false;for(int i=0;i<n;++i)if(ch[i].key==nk){dup=true;break;}if(dup)continue;
            auto cv=memo_.get(nk.lo,nk.hi);
            if(cv) ++child_probe_hit_;
            // Per-depth pre-probe hit%: of the positions generated as children
            // of depth-dd nodes (i.e. living at depth cd), what fraction was
            // already known. d_hit_/d_miss_ are fed ONLY here -- the win()
            // entry probe was removed as redundant, so nothing else writes them.
            int cd = dd<63?dd+1:63;
            if(cv) ++d_hit_[cd]; else ++d_miss_[cd];
            ch[n++]={ns,nl,nk,popcount(nl),v,cv};
        }
        d_moves_[dd]+= (std::uint64_t)n;
        std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){
            int pa=a.cached==ReplaceMemo121::Losing?0:(a.cached==0?1:2);
            int pb=b.cached==ReplaceMemo121::Losing?0:(b.cached==0?1:2);
            if(pa!=pb)return pa<pb;if(a.count!=b.count)return a.count<b.count;return a.key<b.key;
        });
        for(int i=0;i<n;++i){
            if(ch[i].cached){
                ++child_used_;
                bool cw=ch[i].cached==ReplaceMemo121::Winning;
                if(!cw){
                    ++child_loss_cut_;
                    for(int j=i+1;j<n;++j) if(ch[j].cached) ++child_unused_;
                    memo_.put(key.lo,key.hi,ReplaceMemo121::Winning);++d_put_[dd];return true;
                }
                continue;
            }
            bool cw=win(ch[i].ts,ch[i].legal,depth+1);
            if(!cw){
                ++rec_loss_cut_;
                for(int j=i+1;j<n;++j) if(ch[j].cached) ++child_unused_;
                memo_.put(key.lo,key.hi,ReplaceMemo121::Winning);++d_put_[dd];return true;
            }
        }
        memo_.put(key.lo,key.hi,ReplaceMemo121::Losing);++d_put_[dd];return false;
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
        if(argc==2 && std::string(argv[1])=="--memo-self-test"){
            const bool ok=memo_key_width_self_test();
            std::cout<<"memo_key_width_self_test="<<(ok?"PASS":"FAIL")<<"\n";
            return ok?0:1;
        }
        unsigned pow=27;
        bool reps=false;
        std::string only="";
        double budget_s=0;
        std::string log_path="", csv_path="";
        for(int i=1;i<argc;++i){
            std::string a=argv[i];
            if(a=="--reps")reps=true;
            else if(a.rfind("--memo=",0)==0)pow=unsigned(std::stoul(a.substr(7)));
            else if(a.rfind("--only=",0)==0)only=a.substr(7);
            else if(a.rfind("--budget=",0)==0)budget_s=std::stod(a.substr(9));
            else if(a.rfind("--log=",0)==0)log_path=a.substr(6);
            else if(a.rfind("--csv=",0)==0)csv_path=a.substr(6);
            else { std::cerr<<"usage: "<<argv[0]<<" [--reps] [--memo=N] [--only=v,...] [--budget=SEC] [--log=PATH] [--csv=PATH]\n"
                           <<"       "<<argv[0]<<" --memo-self-test\n"; return 2; }
        }
        Solver11 solver(pow);
        solver.set_deadline(budget_s);
        solver.set_log(log_path);
        solver.set_csv(csv_path);
        auto& L = solver.log();
        auto& C = solver.csv();
        L<<"built forbidden="<<solver.forbidden_count()
                 <<" (expect 95670)"<<std::endl;
        L.flush();
        if(solver.forbidden_count()!=95670){
            L<<"F_11 mismatch, abort\n";return 1;
        }
        if(!reps){ L<<"nothing to do without --reps\n"; return 2; }
        C<<"v,x,y,outcome,visited,seconds,memo_used\n";
        solver.csv_flush();
        auto wall0 = std::chrono::steady_clock::now();
        auto prev_visited = solver.visited();
        auto prev_t = wall0;
        std::uint64_t prev_puts=0, prev_evict=0;
        L << "[heartbeat] starting, solver ready" << std::endl;
        L.flush();
        int n_timeout=0, n_done=0;
        for(int v : first_move_reps()){
            if(!only.empty()){
                bool want=false;
                std::stringstream ss(only); std::string tok;
                while(std::getline(ss,tok,',')){ if(!tok.empty()&&std::stoi(tok)==v){want=true;break;} }
                if(!want) continue;
            }
            bool done=false;
            Solver11::Result r{false,0,0,0.0};
            try {
                r=solver.solve_root({v});
                done=true;
            } catch(const std::exception& e){
                double wall = std::chrono::duration<double>(std::chrono::steady_clock::now()-wall0).count();
                std::uint64_t hits,misses,pn,pu,ev; double ap;
                solver.memo_counters(hits,misses,pn,pu,ev,ap);
                double total=(double)(hits+misses);
                double hr = total>0 ? 100.0*(double)hits/total : 0.0;
                std::uint64_t cph,cu,cun,clc,rclc;
                solver.child_stats(cph,cu,cun,clc,rclc);
                double cused = solver.visited() ? 100.0*(double)cu/(double)solver.visited() : 0.0;
                std::uint64_t tot_cut = clc+rclc;
                double cfrac = tot_cut ? 100.0*(double)clc/(double)tot_cut : -1.0;
                // Hits consumed by the abort itself: probed but neither used
                // nor counted unused. ~0 on clean completion; on TIME_BUDGET it
                // is the "work left hanging by the measurement" count.
                std::uint64_t pending = (cph>cu+cun) ? (cph-cu-cun) : 0;
                L << "[timeout] v=" << v
                          << " reason=" << e.what()
                          << " visited=" << solver.visited()
                          << " memo=" << solver.memo_used() << "/" << solver.memo_capacity()
                          << " hit=" << hr << "%"
                          << " puts_new=" << pn << " evict=" << ev
                          << " avgprobe=" << ap
                          << " child_probe_hit=" << cph
                          << " child_used=" << cu << " (" << cused << "%/vis)"
                          << " child_unused=" << cun
                          << " loss_cut_cached=" << clc
                          << " loss_cut_rec=" << rclc;
                if(cfrac>=0) L << " cached_cut_frac=" << cfrac << "%";
                L << " pending_abort=" << pending
                          << " wall_s=" << (long long)wall << std::endl;
                {
                    std::uint64_t dh[64], mv[64]; double dhr[64];
                    solver.depth_stats(dh, mv, dhr, 64);
                    std::uint64_t p=0;
                    for(int d=0;d<22;++d){ p+=dh[d]; }
                    L<<"[depth] total="<<p;
                    for(int d=0;d<22;++d){
                        if(dh[d]==0) continue;
                        double avgm = dh[d] ? (double)mv[d]/(double)dh[d] : 0.0;
                        L<<" d"<<d<<"="<<dh[d]<<"/"<<avgm<<"mv";
                        if(dhr[d]>=0) L<<"/"<<dhr[d]<<"%h";
                    }
                    L<<"\n";
                }
                L.flush();
                prev_visited=solver.visited(); prev_t=std::chrono::steady_clock::now();
                prev_puts=pn; prev_evict=ev;
                ++n_timeout;
                continue;
            }
            double wall = std::chrono::duration<double>(std::chrono::steady_clock::now()-wall0).count();
            std::uint64_t hits,misses,pn,pu,ev; double ap;
            solver.memo_counters(hits,misses,pn,pu,ev,ap);
            double total=(double)(hits+misses);
            double hr = total>0 ? 100.0*(double)hits/total : 0.0;
            std::uint64_t cph,cu,cun,clc,rclc;
            solver.child_stats(cph,cu,cun,clc,rclc);
            double cused = solver.visited() ? 100.0*(double)cu/(double)solver.visited() : 0.0;
            std::uint64_t tot_cut = clc+rclc;
            double cfrac = tot_cut ? 100.0*(double)clc/(double)tot_cut : -1.0;
            double dt=std::chrono::duration<double>(std::chrono::steady_clock::now()-prev_t).count();
            std::uint64_t dv=solver.visited()-prev_visited;
            L << "[progress] v=" << v << " (" << (v%11) << "," << (v/11) << ") "
                      << outcome(r.win)
                      << " visited_total=" << solver.visited()
                      << " rate=" << (dt>0?(long long)(dv/dt):0) << "/s"
                      << " memo=" << solver.memo_used() << "/" << solver.memo_capacity()
                      << " hit=" << hr << "%"
                      << " puts_new_delta=" << (pn-prev_puts)
                      << " evict_delta=" << (ev-prev_evict)
                      << " avgprobe=" << ap
                      << " child_used=" << cu << " (" << cused << "%/vis)"
                      << " loss_cut_cached=" << clc
                      << " loss_cut_rec=" << rclc;
            if(cfrac>=0) L << " cached_cut_frac=" << cfrac << "%";
            L << " maxdepth=" << solver.max_depth()
                      << " wall_s=" << (long long)wall << std::endl;
            L.flush();
            prev_visited=solver.visited(); prev_t=std::chrono::steady_clock::now();
            prev_puts=pn; prev_evict=ev;
            ++n_done;
            C<<v<<","<<(v%11)<<","<<(v/11)<<","
                     <<outcome(r.win)<<","<<r.visited_delta<<","
                     <<r.seconds<<","<<r.memo_used<<"\n";
            solver.csv_flush();
            // A single LOSS (P-position) one-stone move proves the empty
            // board N: the first player wins. Stop early.
            if(!r.win){
                C<<"# FIRST_PLAYER_WIN via "<<v<<"\n";
                solver.csv_flush();
                return 0;
            }
        }
        {
            std::uint64_t dh[64], mv[64]; double hr[64];
            solver.depth_stats(dh, mv, hr, 64);
            std::uint64_t p=0;
            for(int d=0;d<22;++d){ p+=dh[d]; }
            L<<"[depth] total_visited_nodes="<<p;
            for(int d=0;d<22;++d){
                if(dh[d]==0) continue;
                double avgm = dh[d] ? (double)mv[d]/(double)dh[d] : 0.0;
                L<<" d"<<d<<"="<<dh[d]<<"/"<<avgm<<"mv";
                if(hr[d]>=0) L<<"/"<<hr[d]<<"%hit";
            }
            L<<"\n";
            L.flush();
        }
        C<<"# done="<<n_done<<" timeout="<<n_timeout
                 <<" (all 21 first moves WIN => SECOND_PLAYER_WIN)\n";
        solver.csv_flush();
        return 0;
    }catch(const std::exception&e){
        std::cerr<<"error: "<<e.what()<<"\n";return 1;
    }
}
