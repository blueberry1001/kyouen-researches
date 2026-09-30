// kyouen_dfpn_root.cpp -- df-pn proof-search solver for the Kyouen circle game.
//
// WHY: plain DFS + transposition table hits the same wall on all four 11x11
// first moves (2.5-2.8e8 visited / 15 min, unsolved, exploding at d13-d16;
// see research/verification/N11-PROBE-4WAY.md). df-pn concentrates resources
// on branches that look provable instead of sweeping every layer uniformly.
// This file is 11x11-first but templated on N; the DFS solver stays as the
// comparison baseline.
//
// PROPOSITION (fixed for the whole search): "the player who moved FIRST on
// this line eventually wins". Stone count grows by exactly one per move, so
// the side to move is a function of the position itself:
//   even stones -> first player to move -> OR node (one winning child suffices)
//   odd stones  -> second player to move -> AND node (every reply must stay
//                  winning for the first player).
// The same canonical position always has the same stone count, so its OR/AND
// role never changes.
//
// Terminal (no legal moves): side to move loses.
//   OR node  -> proposition false: (pn, dn) = (INF, 0)
//   AND node -> proposition true:  (pn, dn) = (0, INF)
//
// Aggregation (saturating at INF):
//   OR:  pn = min pn(c),  dn = sum dn(c)
//   AND: pn = sum pn(c),  dn = min dn(c)
//
// Child thresholds (standard df-pn):
//   OR:  tp_c = min(tp, pn2+1);  td_c = td - sum_{c'!=c} dn(c')
//   AND: td_c = min(td, dn2+1);  tp_c = tp - sum_{c'!=c} pn(c')
// (64-bit math, clamped to [1, INF]; INF propagates.)
//
// The TT stores open (pn, dn) bounds AND solved marks, so unsolved-position
// knowledge is shared across the search -- the main advantage over the
// WIN/LOSS-only DFS table. Eviction drops open entries first and never the
// active root; soundness never depends on the table (worst case: recompute).
//
// REGRESSION (solve --empty): n=4 LOSS, n=5 WIN, n=6 WIN, n=7 LOSS.
// First success criterion is NOT solving 11x11: it is pushing root pn/dn
// one-sidedly with clearly fewer expansions than DFS in the same 15 min.
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
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

class PnTT {
public:
    enum : std::uint8_t { FREE=0, OPEN=1, WIN=2, LOSS=3 };
    static constexpr int PROBE = 32;
    explicit PnTT(unsigned power=26){
        n_ = std::size_t{1}<<power;
        if(n_==0 || (n_ & (n_-1))) throw std::runtime_error("bad memo power");
        mask_=n_-1;
        lo_.assign(n_,0); hi_.assign(n_,0);
        pn_.assign(n_,0); dn_.assign(n_,0);
        vis_.assign(n_,0); st_.assign(n_,0);
    }
    void set_root(std::uint64_t lo,std::uint64_t hi){ rlo_=lo; rhi_=hi; }
    int find(std::uint64_t klo,std::uint64_t khi) {
        std::size_t i=mix(klo,khi)&mask_;
        for(int j=0;j<PROBE;++j){
            if(!st_[i]){ ++misses_; probe_sum_+=std::uint64_t(j+1); ++probe_n_; return -1; }
            if(lo_[i]==klo && hi_[i]==khi){ ++hits_; probe_sum_+=std::uint64_t(j+1); ++probe_n_; return (int)i; }
            i=(i+1)&mask_;
        }
        ++misses_; probe_sum_+=PROBE; ++probe_n_; return -1;
    }
    int acquire(std::uint64_t klo,std::uint64_t khi){
        std::size_t h=mix(klo,khi)&mask_;
        std::size_t i=h;
        int first_open=-1;
        for(int j=0;j<PROBE;++j){
            if(!st_[i]){
                lo_[i]=klo;hi_[i]=khi;st_[i]=OPEN;++used_;++puts_new_;return (int)i;
            }
            if(lo_[i]==klo && hi_[i]==khi) return (int)i;
            if(first_open<0 && st_[i]==OPEN && !(lo_[i]==rlo_ && hi_[i]==rhi_))
                first_open=(int)i;
            i=(i+1)&mask_;
        }
        if(first_open>=0){
            i=(std::size_t)first_open;
            lo_[i]=klo;hi_[i]=khi;st_[i]=OPEN;++evictions_;return first_open;
        }
        if(lo_[h]==rlo_ && hi_[h]==rhi_){
            for(int j=0;j<PROBE;++j){
                i=(h+(std::size_t)j)&mask_;
                if(!(lo_[i]==rlo_ && hi_[i]==rhi_)){
                    std::uint8_t old=st_[i];
                    lo_[i]=klo;hi_[i]=khi;st_[i]=OPEN;
                    if(old>=WIN){ ++evict_solved_; --solved_; }
                    else ++evictions_;
                    return (int)i;
                }
            }
            return -1;
        }
        std::uint8_t oldh=st_[h];
        lo_[h]=klo;hi_[h]=khi;st_[h]=OPEN;
        if(oldh>=WIN){ ++evict_solved_; --solved_; }
        else ++evictions_;
        return (int)h;
    }
    std::size_t used()const{return used_;}
    std::size_t capacity()const{return n_;}
    // Three SEPARATE counters:
    //   solved_now()           = solved entries CURRENTLY in the TT
    //   solved_discoveries()   = total times an entry was marked solved
    //                            (never decremented; re-marking an
    //                            already-solved slot does not count)
    //   evicted_solved()       = solved entries evicted so far
    // Previously solved_ was an effective cumulative count: evicting a
    // solved entry bumped evict_solved_ but not solved_, so
    // used_-solved_ (open) drifted once evict_solved_>0. Splitting
    // the three keeps open exact for every eviction.
    std::uint64_t solved_now()const{return solved_;}
    std::uint64_t solved_discoveries()const{return solved_disc_;}
    std::uint64_t evicted_solved()const{return evict_solved_;}
    void mark_solved(int s,std::uint8_t v){
        if(st_[(std::size_t)s]<WIN){ ++solved_; ++solved_disc_; }
        st_[(std::size_t)s]=v;
    }
    void counters(std::uint64_t& hits,std::uint64_t& misses,
                  std::uint64_t& puts_new,std::uint64_t& puts_update,
                  std::uint64_t& ev,std::uint64_t& evs,double& ap) const {
        hits=hits_; misses=misses_; puts_new=puts_new_; puts_update=0;
        ev=evictions_; evs=evict_solved_; ap=avg_probe();
    }
    double avg_probe() const {
        return probe_n_ ? (double)probe_sum_/(double)probe_n_ : 0.0;
    }
    std::vector<std::uint64_t> lo_,hi_;
    std::vector<std::uint32_t> pn_,dn_,vis_;
    std::vector<std::uint8_t> st_;
    std::uint64_t used_=0;
    std::uint64_t hits_=0, misses_=0, puts_new_=0, evictions_=0, evict_solved_=0, solved_=0, solved_disc_=0;
    std::uint64_t probe_sum_=0, probe_n_=0;
private:
    std::size_t n_,mask_;
    std::uint64_t rlo_=~0ULL, rhi_=~0ULL;
    static inline std::uint64_t mix64(std::uint64_t x){
        x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;
        x^=x>>27;x*=0x94d049bb133111ebULL;
        return x^(x>>31);
    }
    static inline std::uint64_t mix(std::uint64_t a,std::uint64_t b){
        return mix64(a ^ (b*0x9e3779b97f4a7c15ULL));
    }
};

template<int N>
class DfPn {
public:
    static constexpr int V = N*N;
    static constexpr std::uint64_t HI_MASK =
        (V>64) ? (((V-64)>=64) ? ~0ULL : ((1ULL<<(V-64))-1ULL)) : 0ULL;
    static constexpr std::uint32_t INF = 1000000000u;
    using Clock=std::chrono::steady_clock;
    struct TState { std::array<Bits,8> t{}; };
    struct GChild {
        TState ts; Bits legal,key; int count=0;
        std::uint32_t pn=1,dn=1; std::uint8_t st=0;
    };
    struct Gen { std::array<GChild,V> ch; int n=0; };
    // sizeof(Gen) sanity per N: GChild=176 B (8x16 B TState + 48 B).
    // n=6: 36*176+4 = 6,340. n=11: 121*176+4 = 21,300. If Gen ever grows
    // past ~64 KB the frame-heap buffers need auditing (not the stack --
    // frames are already heap/box-allocated -- but TT-adjacent RSS).
    static_assert(sizeof(Gen) < 65536,
        "Gen unexpectedly large; audit GChild/TState layout");
    struct Result {
        int outcome=0;
        std::uint64_t expansions=0;
        std::uint32_t root_pn=INF, root_dn=INF;
        double seconds=0;
    };

    explicit DfPn(unsigned memo_power=26)
      : completion_(std::size_t(V)*V*V), tt_(memo_power) {
        build_maps(); build_forbidden_quadruples();
    }

    Result solve_empty(){
        TState state{};
        Bits occupied{};
        // Empty board: every point is legal. Build the mask directly instead
        // of (~0ULL, HI_MASK): for V<=64 (n<=8) HI_MASK is 0 and hi would be
        // ~0 & 0 = 0 (fine), but writing it via bitof loop is unambiguous
        // for every N and immune to mask typos (the n=4 "bad move index":
        // legal.hi ended up nonzero -> take_lsb on hi=garbage -> v>=V).
        Bits legal{};
        for(int p=0;p<V;++p) setbit(legal,p);
        return solve_common(state, occupied, legal, 0);
    }

    Result solve_root(const std::vector<int>& stones){
        validate_root(stones);
        TState state{};
        Bits occupied{};
        for(int v:stones){ state=add(state,v); setbit(occupied,v); }
        Bits legal=legal_for(occupied);
        return solve_common(state, occupied, legal, (int)stones.size());
    }

    std::uint64_t forbidden_count() const { return forbidden_count_; }
    std::uint64_t visited() const { return visited_; }
    std::uint64_t expansions() const { return expanded_; }

private:
    std::array<std::array<Bits,V>,8> tbit_{};
    PnTT tt_;
    std::vector<Bits> completion_;
    std::uint64_t forbidden_count_=0,visited_=0,expanded_=0;
    std::uint64_t exp_hist_[64]={};
    int max_depth_=0;
    double deadline_s_=0;
    Clock::time_point t0_;
    // Heartbeat rate state (per-solver, reset per root in solve_common).
    std::uint64_t hb_last_vis_=0;
    double hb_last_t_=0;
    double hb_prev_t_=0;
    std::uint64_t hb_prev_exp_=0;
    Bits root_key_{};
    int root_stones_=0;
    // Partial-progress fallback: written by the catch in solve_common when
    // mid() throws (TIME_BUDGET), read by the run_one() handler.
    std::uint32_t r_exp_fallback_pn=INF, r_exp_fallback_dn=INF;
    std::uint64_t r_exp_fallback_exp=0, r_exp_fallback_vis=0;

    static std::uint32_t sadd(std::uint32_t a,std::uint32_t b){
        std::uint64_t s=(std::uint64_t)a+b;
        return s>=INF?INF:(std::uint32_t)s;
    }
    static bool is_or(int stones){ return (stones%2)==0; }

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

    void child_bound(const Bits& nk,int child_stones,int* n_out,std::uint32_t* pnp,std::uint32_t* dnp,std::uint8_t* stp){
        int s=tt_.find(nk.lo,nk.hi);
        if(s>=0){ *pnp=tt_.pn_[(std::size_t)s]; *dnp=tt_.dn_[(std::size_t)s]; *stp=tt_.st_[(std::size_t)s]; return; }
        *pnp=1; *dnp=1; *stp=PnTT::OPEN;
        (void)n_out; (void)child_stones;
    }

    // Child-list buffers: ONE Gen PER mid() FRAME, allocated on the HEAP via
    // std::unique_ptr (never on the stack, never returned by value). One Gen
    // holds up to V GChild, each with 8x16 B TState (~18 KB at n=11, smaller
    // for small n). Returning it by value while several frames stayed live
    // blew the 8 MB stack (the original n=5 segfault); a vector<Gen> pool
    // indexed by depth then threw bad_alloc because resize() default-builds
    // every Gen up to that depth including ~18 KB each. unique_ptr<Gen>
    // allocates exactly one buffer per frame, lazily, on the heap.
    void gen_into(const TState& state,int stones,Bits legal,Gen& g){
        g.n=0;
        Bits moves=legal;
        // Mask hygiene: legal must never carry bits >= V. take_lsb on a
        // stray hi bit returns v>=V -> bitof(v) shifts UB -> the move loop
        // walks off into garbage children (the roots-csv overflow: 36-move
        // roots grew >36 "children"). Mask once here so every caller is safe
        // even if its legal mask came from a different path.
        if(V<64){ if(V==0){moves.lo=0;} else moves.lo &= ((1ULL<<V)-1ULL); moves.hi = 0; }
        else if(V==64){ moves.hi = 0; }
        else { moves.hi &= HI_MASK; }
        while(any(moves)){
            int v=take_lsb(moves);
            if(v<0||v>=V) throw std::runtime_error("gen_into: move index out of range");
            Bits bit=bitof(v);
            TState ns=add(state,v);
            Bits nl=(legal&~bit)&~added_bans(state.t[0],v);
            nl.hi&=HI_MASK;
            Bits nk=canonical(ns);
            bool dup=false;
            int nn=g.n;
            for(int i=0;i<nn;++i)if(g.ch[(std::size_t)i].key==nk){dup=true;break;}
            if(dup)continue;
            // BOUNDS CHECK (ASan found this): a Gen holds exactly V GChild.
            // children <= legal moves <= V, so g.n>=V means the move loop
            // produced a duplicate-free child beyond the array -- a logic bug
            // (stale Gen reuse, corrupted legal mask, ...). Fail loud.
            if(g.n<0 || g.n>=V) throw std::runtime_error("gen_into: child index out of range");
            GChild& c=g.ch[(std::size_t)g.n];
            c.ts=ns; c.legal=nl; c.key=nk; c.count=popcount(nl);
            int cs=stones+1;
            int s=tt_.find(nk.lo,nk.hi);
            if(s>=0){
                c.pn=tt_.pn_[(std::size_t)s]; c.dn=tt_.dn_[(std::size_t)s]; c.st=tt_.st_[(std::size_t)s];
            }else{
                if(!any(nl)){
                    if(is_or(cs)){ c.pn=INF; c.dn=0; c.st=PnTT::LOSS; }
                    else{ c.pn=0; c.dn=INF; c.st=PnTT::WIN; }
                }else{ c.pn=1; c.dn=1; c.st=PnTT::OPEN; }
            }
            ++g.n;
        }
    }

    void aggregate(int stones,const Gen& g,std::uint32_t* pnp,std::uint32_t* dnp){
        if(is_or(stones)){
            std::uint32_t pn=INF,dn=0;
            for(int i=0;i<g.n;++i){
                if(g.ch[(std::size_t)i].pn<pn)pn=g.ch[(std::size_t)i].pn;
                dn=sadd(dn,g.ch[(std::size_t)i].dn);
            }
            *pnp=pn; *dnp=dn;
        }else{
            std::uint32_t pn=0,dn=INF;
            for(int i=0;i<g.n;++i){
                pn=sadd(pn,g.ch[(std::size_t)i].pn);
                if(g.ch[(std::size_t)i].dn<dn)dn=g.ch[(std::size_t)i].dn;
            }
            *pnp=pn; *dnp=dn;
        }
    }

    void expand(const Bits& key,const TState& state,int stones,Bits legal,int depth){
        auto gb=std::make_unique<Gen>();
        Gen& g=*gb;
        gen_into(state,stones,legal,g);
        std::uint32_t pn,dn;
        aggregate(stones,g,&pn,&dn);
        int s=tt_.acquire(key.lo,key.hi);
        if(s<0) throw std::runtime_error("TT full at expand");
        tt_.pn_[(std::size_t)s]=pn; tt_.dn_[(std::size_t)s]=dn;
        tt_.vis_[(std::size_t)s]=1;
        if(pn==0) tt_.mark_solved(s,PnTT::WIN);
        else if(dn==0) tt_.mark_solved(s,PnTT::LOSS);
        else tt_.st_[(std::size_t)s]=PnTT::OPEN;
        ++expanded_;
        ++exp_hist_[depth<64?depth:63];
        if(depth>max_depth_)max_depth_=depth;
    }

    void heartbeat(){
        if(deadline_s_<=0) return;
        double el=std::chrono::duration<double>(Clock::now()-t0_).count();
        // NOTE: no early throw here. The gate below means the throw only
        // fires after real work; the entry check in mid() covers
        // already-expired budgets. Throwing here before the gate would kill
        // roots that never reach the first gate (the "expansions=1" ghost).
        //
        // The hb line doubles as the ROOT PN/DN TIME SERIES: root bounds are
        // re-read from the TT on every heartbeat, so the log shows whether
        // the proof is moving one-sidedly long before it completes.
        //
        // TIME-BASED gating: fire at the next 10 s mark after at least
        // 2^16 iterations since the last beat. Iteration-count gating alone
        // starves the log on slow phases; pure wall-clock polling every
        // iteration costs a clock read each node. 2^16 amortizes the clock
        // to ~1/65536 nodes while guaranteeing a beat within ~10 s.
        // Elapsed t=0 is solver construction end (set_deadline time).
        if(visited_ - hb_last_vis_ < (std::uint64_t(1)<<16)) return;
        if(el - hb_last_t_ < 10.0) return;
        hb_last_vis_ = visited_;
        hb_last_t_ = el;
        int rs=tt_.find(root_key_.lo,root_key_.hi);
        std::uint32_t rpn=INF,rdn=INF;
        if(rs>=0){ rpn=tt_.pn_[(std::size_t)rs]; rdn=tt_.dn_[(std::size_t)rs]; }
        std::uint64_t open = tt_open();
        double pndn = (rpn>0 && rdn<INF) ? (double)rpn/(double)rdn : -1.0;
        std::uint64_t hits,misses,pn_put,pu_put,ev,evs; double ap;
        tt_.counters(hits,misses,pn_put,pu_put,ev,evs,ap);
        double dt = el - hb_prev_t_;
        std::uint64_t dexp = expanded_ - hb_prev_exp_;
        double exprate = dt>0 ? (double)dexp/dt : 0.0;
        hb_prev_t_ = el; hb_prev_exp_ = expanded_;
        *log_ << "[hb] t=" << (long long)el << "s"
              << " visited=" << visited_ << " expanded=" << expanded_
              << " exprate=" << (long long)exprate << "/s"
              << " root_pn=" << rpn << " root_dn=" << rdn
              << " pndn=" << pndn
              << " memo=" << tt_.used() << "/" << tt_.capacity()
              << " open=" << open
              << " solved=" << tt_.solved_now()
              << " solved_disc=" << tt_.solved_discoveries()
              << " evict_open=" << tt_.evictions_
              << " evict_solved=" << tt_.evicted_solved()
              << " maxdepth=" << max_depth_
              << " tthit=" << hits << " ttmiss=" << misses
              << " avgprobe=" << ap << std::endl;
        log_->flush();
        if(el>=deadline_s_) throw std::runtime_error("TIME_BUDGET");
    }

    void mid(const Bits& key,const TState& state,int stones,Bits legal,int depth,
             std::uint32_t tp,std::uint32_t td){
        if(deadline_s_>0){
            double el=std::chrono::duration<double>(Clock::now()-t0_).count();
            if(el>=deadline_s_) throw std::runtime_error("TIME_BUDGET");
        }
        std::vector<std::unique_ptr<Gen>> scratch;
        mid_iter(key,state,stones,legal,depth,tp,td,scratch);
    }

    // Child-list buffers: ONE Gen PER mid() FRAME, heap-allocated on FIRST
    // use and NEVER reallocated. vector<Frame> may RELOCATE on push_back
    // (move-constructing every Frame); unique_ptr<Gen> moves the POINTER, so
    // the buffer address is stable. But gen() must NEVER be called twice on
    // the same frame expecting a fresh buffer... it isn't: gen_into resets
    // g.n=0 each call, and the frame's buffer is only read while the frame
    // is live. The ACTUAL invariant: expand() uses a THROWAWAY Gen, never
    // the frame's buffer, so a child's expand cannot clobber the parent's
    // in-progress child list. (The roots-csv crash: expand() wrote into the
    // frame buffer via a shared path; fixed by keeping expand heap-local.)
    struct Frame {
        Bits key; TState state; Bits legal;
        int stones=0, depth=0;
        std::uint32_t tp=INF, td=INF;
        int slot=-1;
        int stage=0;
        std::unique_ptr<Gen> gb;
        Gen& gen(){
            if(!gb) gb=std::make_unique<Gen>();
            return *gb;
        }
    };

    // Stack dump for loop diagnosis: prints each live frame's stones/tp/td
    // and stored pn/dn so a threshold cycle shows as repeated rows.
    // Declared AFTER Frame (must precede use in signature).
    void dump_stack(const std::vector<Frame>& st){
        *log_ << "[stack] depth=" << st.size() << std::endl;
        for(std::size_t i=0;i<st.size();++i){
            const Frame& f=st[i];
            int s=tt_.find(f.key.lo,f.key.hi);
            std::uint32_t pn=0xffffffffu,dn=0xffffffffu;
            int sv=-9;
            if(s>=0){ pn=tt_.pn_[(std::size_t)s]; dn=tt_.dn_[(std::size_t)s]; sv=(int)tt_.st_[(std::size_t)s]; }
            *log_ << "  [" << i << "] stones=" << f.stones
                  << " tp=" << f.tp << " td=" << f.td
                  << " slot=" << f.slot << " tt=" << s
                  << " pn=" << pn << " dn=" << dn << " st=" << sv
                  << " stage=" << f.stage << std::endl;
        }
        log_->flush();
    }

    void mid_iter(const Bits& rkey,const TState& rstate,int rstones,Bits rlegal,
                  int rdepth,std::uint32_t rtp,std::uint32_t rtd,
                  std::vector<std::unique_ptr<Gen>>& scratch){
        std::vector<Frame> st;
        st.reserve(256);
        {
            Frame f;
            f.key=rkey; f.state=rstate; f.legal=rlegal;
            f.stones=rstones; f.depth=rdepth; f.tp=rtp; f.td=rtd;
            st.push_back(std::move(f));
        }
        while(!st.empty()){
            // NOTE: no Frame& may survive a push_back (vector may relocate).
            // All access goes through st.back() after each potential growth.
            ++visited_;
            // Deadline check on EVERY iteration, not just every 2^20: the
            // explicit stack can sit thousands deep doing re-aggregation
            // passes with visited_ barely moving (threshold returns), so the
            // 2^20 gate may never fire. Check is one clock read; demonstrated
            // ~zero cost on the DFS solver's 340k/s rate.
            if(deadline_s_>0){
                double el=std::chrono::duration<double>(Clock::now()-t0_).count();
                if(el>=deadline_s_) throw std::runtime_error("TIME_BUDGET");
            }
            if((visited_ & ((std::uint64_t(1)<<20)-1))==0) heartbeat();
            // Depth guard: a legal game never exceeds V stones. Past V+8 is a
            // BUG (threshold cycle or phantom descent), not proof progress.
            // Throw loud instead of silently popping: silent pops hide cycles
            // as slow progress. (V is the template board's point count, so
            // this is exact for every N, not just 11.)
            if(st.back().depth>V+8){ throw std::runtime_error("depth guard: legality exceeded"); }
            if(st.back().stage==0){
                Bits fk=st.back().key;
                int s=tt_.find(fk.lo,fk.hi);
                if(s<0){
                    if(deadline_s_>0){
                        double el=std::chrono::duration<double>(Clock::now()-t0_).count();
                        if(el>=deadline_s_) throw std::runtime_error("TIME_BUDGET");
                    }
                    expand(st.back().key,st.back().state,st.back().stones,st.back().legal,st.back().depth);
                    // DO NOT POP: the frame must now descend into its best
                    // child (stage 1 below). Popping here was the
                    // "expansions=1" bug: mid() returned after expanding the
                    // root instead of continuing the proof search.
                    s=tt_.find(st.back().key.lo,st.back().key.hi);
                    st.back().slot=s;
                    st.back().stage=1;
                } else {
                    if(tt_.st_[(std::size_t)s]>=PnTT::WIN){ st.pop_back(); continue; }
                    st.back().slot=s;
                    st.back().stage=1;
                }
            }
            int frd=st.back().depth, frs=st.back().stones;
            std::uint32_t frtp=st.back().tp, frtd=st.back().td;
            Gen& g=st.back().gen();
            gen_into(st.back().state,frs,st.back().legal,g);
            std::uint32_t pn,dn;
            aggregate(frs,g,&pn,&dn);
            int s=st.back().slot;
            int s2=tt_.find(st.back().key.lo,st.back().key.hi);
            if(s2>=0) s=s2;
            else {
                // Slot lost to eviction between stage-0 and now: re-acquire.
                // Without this the write below goes to a stale index, which
                // corrupts a DIFFERENT position's (pn,dn) -- silent wrong
                // bounds that can loop forever (n=4: root_pn=1/root_dn=3
                // frozen while visited ran to 2.5e8).
                s=tt_.acquire(st.back().key.lo,st.back().key.hi);
                if(s<0) throw std::runtime_error("TT full at re-aggregate");
                st.back().slot=s;
            }
            tt_.pn_[(std::size_t)s]=pn; tt_.dn_[(std::size_t)s]=dn;
            if(pn==0){ tt_.mark_solved(s,PnTT::WIN); st.pop_back(); continue; }
            if(dn==0){ tt_.mark_solved(s,PnTT::LOSS); st.pop_back(); continue; }
            if(pn>=frtp || dn>=frtd){ st.pop_back(); continue; }
            int b1=-1,b2=-1;
            bool isor=is_or(frs);
            // b1 = best child (pn/dn, tie-broken by count then key).
            // b2 = TRUE second minimum INCLUDING ties: the minimum over all
            // children except b1 itself. If every child ties b1, b2 points at
            // another tied child and pn2/dn2 equal b1's value -- NOT INF.
            // Standard df-pn needs this: with children (1,1,1,...) the chosen
            // child gets threshold min(parent, 1+1) = 2, i.e. "come back to
            // the parent as soon as this child's number rises to 2, because
            // it is no longer uniquely best". The old code left b2=-1 on ties
            // (-> INF threshold), which dug one child almost to solution
            // before returning -- near-DFS behaviour. It also made b2 depend
            // on generation order (only set when a tie later stole b1), so
            // identical number-multisets gave 1 or INF by accident.
            for(int i=0;i<g.n;++i){
                bool better=false;
                if(b1<0) better=true;
                else if(isor){
                    if(g.ch[(std::size_t)i].pn<g.ch[(std::size_t)b1].pn) better=true;
                    else if(g.ch[(std::size_t)i].pn==g.ch[(std::size_t)b1].pn &&
                        (g.ch[(std::size_t)i].count<g.ch[(std::size_t)b1].count ||
                         (g.ch[(std::size_t)i].count==g.ch[(std::size_t)b1].count &&
                          g.ch[(std::size_t)i].key<g.ch[(std::size_t)b1].key))) better=true;
                }else{
                    if(g.ch[(std::size_t)i].dn<g.ch[(std::size_t)b1].dn) better=true;
                    else if(g.ch[(std::size_t)i].dn==g.ch[(std::size_t)b1].dn &&
                        (g.ch[(std::size_t)i].count<g.ch[(std::size_t)b1].count ||
                         (g.ch[(std::size_t)i].count==g.ch[(std::size_t)b1].count &&
                           g.ch[(std::size_t)i].key<g.ch[(std::size_t)b1].key))) better=true;
                }
                if(better){ b2=b1; b1=i; }
                else{
                    // Runner-up by number ONLY (no count/key tie-break): any
                    // non-best child qualifies, tied or not.
                    if(isor){
                        if(b2<0 || g.ch[(std::size_t)i].pn<g.ch[(std::size_t)b2].pn) b2=i;
                    }else{
                        if(b2<0 || g.ch[(std::size_t)i].dn<g.ch[(std::size_t)b2].dn) b2=i;
                    }
                }
            }
            std::uint32_t tp_c,td_c;
            if(isor){
                std::uint32_t pn2 = b2>=0 ? g.ch[(std::size_t)b2].pn : INF;
                tp_c = std::min(frtp, sadd(pn2,1));
                std::uint64_t rest=0;
                for(int i=0;i<g.n;++i)if(i!=b1){
                    rest+=(std::uint64_t)g.ch[(std::size_t)i].dn;
                    if(rest>=(std::uint64_t)INF)break;
                }
                if(frtd>=INF) td_c=INF;
                else if(rest>=(std::uint64_t)frtd) td_c=sadd(g.ch[(std::size_t)b1].dn,1);
                else td_c=(std::uint32_t)((std::uint64_t)frtd-rest);
                if(td_c<1)td_c=1;
            }else{
                std::uint32_t dn2 = b2>=0 ? g.ch[(std::size_t)b2].dn : INF;
                td_c = std::min(frtd, sadd(dn2,1));
                std::uint64_t rest=0;
                for(int i=0;i<g.n;++i)if(i!=b1){
                    rest+=(std::uint64_t)g.ch[(std::size_t)i].pn;
                    if(rest>=(std::uint64_t)INF)break;
                }
                if(frtp>=INF) tp_c=INF;
                else if(rest>=(std::uint64_t)frtp) tp_c=sadd(g.ch[(std::size_t)b1].pn,1);
                else tp_c=(std::uint32_t)((std::uint64_t)frtp-rest);
                if(tp_c<1)tp_c=1;
            }
            Bits ck=g.ch[(std::size_t)b1].key;
            Bits cl=g.ch[(std::size_t)b1].legal;
            int cs=frs+1, cd=frd+1;
            // Reuse the child's TState DIRECTLY from the parent's Gen buffer.
            // Rebuilding it from the key (old code) is both slower AND wrong:
            // canonical(ns) is the MINIMUM over 8 D4 images, so the key's bit
            // pattern is generally a ROTATED image, not the position reached
            // by playing the move. added_bans(state.t[0], v) computed from a
            // rotated occupancy is inconsistent with cl (computed in the
            // parent's frame), so the child explored a phantom position whose
            // bounds never matched its TT entry -- the infinite loop (n=4:
            // visited=2.5e8, expanded=108 frozen, root_pn=1/root_dn=3).
            // Lifetime: COPIED into the child frame (not referenced), because
            // the parent's Gen buffer is reused on revisit while the child
            // frame is still alive.
            TState ct=g.ch[(std::size_t)b1].ts;
            Frame nf;
            nf.key=ck; nf.state=ct; nf.legal=cl;
            nf.stones=cs; nf.depth=cd;
            nf.tp=tp_c; nf.td=td_c;
            st.push_back(std::move(nf));
        }
    }

    // DEAD CODE (kept for the comment): scratch Gens keyed by stack slot
    // aliased parent/child buffers and caused the n=4 crash at gen_into+305.
    // Frames now own their Gen buffers; expand() uses a heap-local throwaway.
    // gen_scratch is no longer called; left in place so the history is clear.
    Gen& gen_scratch(int slot,std::vector<std::unique_ptr<Gen>>& scratch){
        if((int)scratch.size()<=slot) scratch.resize((std::size_t)slot+1);
        if(!scratch[(std::size_t)slot]) scratch[(std::size_t)slot]=std::make_unique<Gen>();
        return *scratch[(std::size_t)slot];
    }

    Result solve_common(const TState& state,const Bits& occupied,Bits legal,int stones){
        (void)occupied;
        Bits key=canonical(state);
        root_key_=key; root_stones_=stones;
        tt_.set_root(key.lo,key.hi);
        t0_=Clock::now();
        const auto start=t0_;
        const auto before_exp=expanded_;
        const auto before_vis=visited_;
        // Reset per-root heartbeat rate state (TT is shared across roots).
        hb_last_vis_=visited_; hb_last_t_=0.0;
        hb_prev_t_=0.0; hb_prev_exp_=before_exp;
        // Emit the t=0 series point immediately: roots that finish or die
        // before the first 10 s gate would otherwise leave no series at all
        // (the missing-hb bug: only [timeout]/[done] survived).
        {
            int rs=tt_.find(key.lo,key.hi);
            std::uint32_t rpn=INF,rdn=INF;
            if(rs>=0){ rpn=tt_.pn_[(std::size_t)rs]; rdn=tt_.dn_[(std::size_t)rs]; }
            *log_ << "[hb] t=0s"
                  << " visited=" << visited_ << " expanded=" << expanded_
                  << " exprate=0/s"
                  << " root_pn=" << rpn << " root_dn=" << rdn
                  << " pndn=-1"
                  << " memo=" << tt_.used() << "/" << tt_.capacity()
                  << " open=" << tt_open()
                  << " solved=" << tt_.solved_now()
                  << " solved_disc=" << tt_.solved_discoveries()
                  << " evict_open=" << tt_.evictions_
                  << " evict_solved=" << tt_.evicted_solved()
                  << " maxdepth=" << max_depth_
                  << " tthit=0 ttmiss=0 avgprobe=0" << std::endl;
            log_->flush();
        }
        // Reset the partial-progress fallback BEFORE running: the TT is
        // shared across roots, so a stale fallback from a previous root
        // would otherwise masquerade as this root's progress
        // (the "root_pn=20 wall_s=0" ghost).
        r_exp_fallback_pn=INF; r_exp_fallback_dn=INF;
        r_exp_fallback_exp=0; r_exp_fallback_vis=0;
        try {
            mid(key,state,stones,legal,stones,INF,INF);
        } catch(...){
            // Record partial progress even on TIME_BUDGET: root bounds may
            // already have moved one-sidedly, which is the success signal.
            int sp=tt_.find(key.lo,key.hi);
            if(sp>=0){
                r_exp_fallback_pn=tt_.pn_[(std::size_t)sp];
                r_exp_fallback_dn=tt_.dn_[(std::size_t)sp];
            }
            r_exp_fallback_exp=expanded_-before_exp;
            r_exp_fallback_vis=visited_-before_vis;
            throw;
        }
        double sec=std::chrono::duration<double>(Clock::now()-start).count();
        Result r;
        r.expansions=expanded_-before_exp;
        r.seconds=sec;
        int s=tt_.find(key.lo,key.hi);
        if(s>=0){
            r.root_pn=tt_.pn_[(std::size_t)s];
            r.root_dn=tt_.dn_[(std::size_t)s];
            if(tt_.st_[(std::size_t)s]==PnTT::WIN) r.outcome=1;
            else if(tt_.st_[(std::size_t)s]==PnTT::LOSS) r.outcome=-1;
        }
        return r;
    }

public:
    void set_deadline(double s){
        deadline_s_=s;
        t0_=Clock::now();
    }
    // Attach caller-owned streams. The solver never owns these; main() keeps
    // the ofstreams alive for the whole run. After attach, ALL solver output
    // (heartbeat, timeout, completion, depth lines) goes to the same sink.
    void attach_log(std::ostream& os){ log_=&os; }
    void attach_csv(std::ostream& os){ csv_=&os; }
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
    std::uint64_t tt_open() const {
        return tt_.used_ >= tt_.solved_ ? tt_.used_ - tt_.solved_ : 0;
    }
    std::uint64_t memo_used() const { return tt_.used(); }
    std::uint64_t memo_solved() const { return tt_.solved_now(); }
    std::uint64_t memo_solved_disc() const { return tt_.solved_discoveries(); }
    std::size_t memo_capacity() const { return tt_.capacity(); }
    void partial_progress(std::uint32_t& pn,std::uint32_t& dn,
                          std::uint64_t& exp,std::uint64_t& vis) const {
        pn=r_exp_fallback_pn; dn=r_exp_fallback_dn;
        exp=r_exp_fallback_exp; vis=r_exp_fallback_vis;
    }
    void exp_hist(std::uint64_t* out,int n) const {
        for(int i=0;i<n;++i) out[i]=exp_hist_[i<64?i:63];
    }
    int max_depth() const { return max_depth_; }

private:
    std::ostream* log_=&std::cerr;
    std::ofstream log_file_;
    std::ostream* csv_=&std::cout;
    std::ofstream csv_file_;
};

template<int N>
static std::vector<int> first_move_reps(){
    std::vector<int> reps;
    int c=(N/2)*N+(N/2);
    reps.push_back(c);
    reps.push_back(0);
    for(int x=0;x<=N/2;++x)for(int y=0;y<=x;++y){
        int v=y*N+x;
        if(v==c||v==0)continue;
        reps.push_back(v);
    }
    return reps;
}

static std::string outcome_str(int o){ return o>0?"WIN":(o<0?"LOSS":"TIMEOUT"); }

template<int N>
static int run(const std::string& only,double budget_s,unsigned memo_power,
               bool do_empty,bool do_reps,std::ostream& L,std::ostream& C,
               std::uint64_t* total_exp,
               const std::string& csv_roots_path=""){
    DfPn<N> solver(memo_power);
    // SINGLE-STREAM wiring: the solver writes heartbeat/timeout/completion
    // through the SAME L/C objects run() uses. Previously the solver held
    // its own log_/csv_ (default cerr/cout, or --log/--csv files) while
    // run() wrote to L/C -- so heartbeat went wherever log_ pointed and the
    // --log file only ever saw [timeout]/[done]. Now everything converges.
    solver.attach_log(L);
    solver.attach_csv(C);
    L<<"n="<<N<<" built forbidden="<<solver.forbidden_count()<<std::endl;
    L.flush();
    // Deadline counts from the first root actually started, not from solver
    // construction (which builds the ~8M-entry forbidden table). Setting it
    // here keeps per-probe budgets comparable across --only selections.
    solver.set_deadline(budget_s);
    int n_done=0,n_timeout=0;
    auto wall0=std::chrono::steady_clock::now();
    auto run_one=[&](const std::string& tag,const std::vector<int>& stones){
        typename DfPn<N>::Result r;
        bool done=false;
        try{
            if(stones.empty()) r=solver.solve_empty();
            else r=solver.solve_root(stones);
            done=true;
        }catch(const std::exception& e){
            double wall=std::chrono::duration<double>(
                std::chrono::steady_clock::now()-wall0).count();
            std::uint32_t fpn,fdn; std::uint64_t fexp,fvis;
            solver.partial_progress(fpn,fdn,fexp,fvis);
            C<<"# ["<<tag<<"] TIMEOUT reason="<<e.what()
             <<" expansions="<<fexp
             <<" visited="<<fvis
             <<" root_pn="<<fpn<<" root_dn="<<fdn
             <<" memo="<<solver.memo_used()<<"/"<<solver.memo_capacity()
             <<" solved="<<solver.memo_solved()
             <<" solved_disc="<<solver.memo_solved_disc()
             <<" wall_s="<<(long long)wall<<"\n";
            solver.csv_flush();
            {
                std::uint64_t dh[64]; solver.exp_hist(dh,64);
                std::uint64_t p=0;
                for(int d=0;d<48;++d)p+=dh[d];
                L<<"[depth-exp] total="<<p;
                for(int d=0;d<48;++d){
                    if(!dh[d])continue;
                    L<<" d"<<d<<"="<<dh[d];
                }
                L<<"\n";
                L.flush();
            }
            ++n_timeout;
            return;
        }
        double wall=std::chrono::duration<double>(
            std::chrono::steady_clock::now()-wall0).count();
        L<<"[done] ["<<tag<<"] "<<outcome_str(r.outcome)
         <<" expansions="<<r.expansions
         <<" root_pn="<<r.root_pn<<" root_dn="<<r.root_dn
         <<" memo="<<solver.memo_used()<<"/"<<solver.memo_capacity()
         <<" wall_s="<<(long long)wall<<std::endl;
        L.flush();
        *total_exp+=r.expansions;
        ++n_done;
    };
    if(do_empty) run_one("empty",{});
    // Arbitrary multi-stone roots from a CSV file (cross-check vs DFS).
    // Format: header "canonical_parent,move" then rows "a,b,c",m meaning the
    // root {a,b,c,m}. Unsafe rows (forbidden quadruple inside) are reported
    // as UNSAFE and skipped -- they are not legal positions.
    if(!csv_roots_path.empty()){
        std::ifstream f(csv_roots_path);
        if(!f){ L<<"cannot open --roots-csv\n"; L.flush(); return 1; }
        std::string header;
        if(!std::getline(f,header)){ L<<"empty --roots-csv\n"; L.flush(); return 1; }
        std::string line;
        while(std::getline(f,line)){
            if(line.empty()) continue;
            if(line[0]!='"'){ L<<"bad roots row (want quoted parent): "<<line<<"\n"; L.flush(); continue; }
            auto q=line.find('"',1);
            if(q==std::string::npos){ L<<"bad roots row: "<<line<<"\n"; L.flush(); continue; }
            std::string ptext=line.substr(1,q-1);
            std::vector<int> stones;
            {
                std::stringstream ss(ptext); std::string tok;
                while(std::getline(ss,tok,',')) if(!tok.empty()) stones.push_back(std::stoi(tok));
            }
            if(q+1>=line.size()||line[q+1]!=','){ L<<"bad roots row: "<<line<<"\n"; L.flush(); continue; }
            stones.push_back(std::stoi(line.substr(q+2)));
            std::stringstream tag;
            tag<<"roots{";
            for(std::size_t i=0;i<stones.size();++i){ if(i)tag<<","; tag<<stones[i]; }
            tag<<"}";
            try{
                run_one(tag.str(),stones);
            }catch(const std::exception& e){
                L<<"[roots] "<<tag.str()<<" UNSAFE ("<<e.what()<<")\n"; L.flush();
            }
        }
    }
    if(do_reps){
        for(int v: first_move_reps<N>()){
            if(!only.empty()){
                bool want=false;
                std::stringstream ss(only); std::string tok;
                while(std::getline(ss,tok,',')){
                    if(!tok.empty()&&std::stoi(tok)==v){want=true;break;}
                }
                if(!want)continue;
            }
            run_one("v="+std::to_string(v),{v});
        }
    }
    L<<"# done="<<n_done<<" timeout="<<n_timeout<<std::endl;
    L.flush();
    return 0;
}

int main(int argc,char**argv){
    try{
        int n=11;
        unsigned pow=26;
        bool reps=false, empty=false;
        std::string only="";
        double budget_s=0;
        std::string log_path="", csv_path="", roots_path="";
        for(int i=1;i<argc;++i){
            std::string a=argv[i];
            if(a=="--reps")reps=true;
            else if(a=="--empty")empty=true;
            else if(a.rfind("--n=",0)==0)n=std::stoi(a.substr(4));
            else if(a.rfind("--memo=",0)==0)pow=unsigned(std::stoul(a.substr(7)));
            else if(a.rfind("--only=",0)==0)only=a.substr(7);
            else if(a.rfind("--budget=",0)==0)budget_s=std::stod(a.substr(9));
            else if(a.rfind("--log=",0)==0)log_path=a.substr(6);
            else if(a.rfind("--csv=",0)==0)csv_path=a.substr(6);
            else if(a.rfind("--roots-csv=",0)==0)roots_path=a.substr(12);
            else{
                std::cerr<<"usage: "<<argv[0]<<" [--n=N] [--empty] [--reps] [--memo=P] [--only=v,..] [--budget=S] [--log=P] [--csv=P] [--roots-csv=P]\n";
                return 2;
            }
        }
        if(!reps && !empty && roots_path.empty()){
            std::cerr<<"nothing to do without --empty/--reps/--roots-csv\n";
            return 2;
        }
        std::ostream* lp=&std::cerr;
        std::ofstream lf;
        if(!log_path.empty()){
            lf.open(log_path, std::ios::out | std::ios::app);
            if(!lf){ std::cerr<<"cannot open log\n"; return 1; }
            lp=&lf;
        }
        std::ostream* cp=&std::cout;
        std::ofstream cf;
        if(!csv_path.empty()){
            cf.open(csv_path, std::ios::out | std::ios::app);
            if(!cf){ std::cerr<<"cannot open csv\n"; return 1; }
            cp=&cf;
        }
        std::uint64_t total_exp=0;
        int rc=0;
        switch(n){
            case 4: rc=run<4>(only,budget_s,pow,empty,reps,*lp,*cp,&total_exp,roots_path); break;
            case 5: rc=run<5>(only,budget_s,pow,empty,reps,*lp,*cp,&total_exp,roots_path); break;
            case 6: rc=run<6>(only,budget_s,pow,empty,reps,*lp,*cp,&total_exp,roots_path); break;
            case 7: rc=run<7>(only,budget_s,pow,empty,reps,*lp,*cp,&total_exp,roots_path); break;
            case 11: rc=run<11>(only,budget_s,pow,empty,reps,*lp,*cp,&total_exp,roots_path); break;
            default: std::cerr<<"unsupported n\n"; return 2;
        }
        return rc;
    }catch(const std::exception&e){
        std::cerr<<"error: "<<e.what()<<"\n";return 1;
    }
}
