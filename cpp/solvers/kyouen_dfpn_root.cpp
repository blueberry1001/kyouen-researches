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
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
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
                lo_[i]=klo;hi_[i]=khi;pn_[i]=dn_[i]=vis_[i]=0;st_[i]=OPEN;++used_;++puts_new_;return (int)i;
            }
            if(lo_[i]==klo && hi_[i]==khi) return (int)i;
            if(first_open<0 && st_[i]==OPEN && !(lo_[i]==rlo_ && hi_[i]==rhi_))
                first_open=(int)i;
            i=(i+1)&mask_;
        }
        if(first_open>=0){
            i=(std::size_t)first_open;
            lo_[i]=klo;hi_[i]=khi;pn_[i]=dn_[i]=vis_[i]=0;st_[i]=OPEN;++evictions_;return first_open;
        }
        if(lo_[h]==rlo_ && hi_[h]==rhi_){
            for(int j=0;j<PROBE;++j){
                i=(h+(std::size_t)j)&mask_;
                if(!(lo_[i]==rlo_ && hi_[i]==rhi_)){
                    std::uint8_t old=st_[i];
                    lo_[i]=klo;hi_[i]=khi;pn_[i]=dn_[i]=vis_[i]=0;st_[i]=OPEN;
                    if(old>=WIN){ ++evict_solved_; --solved_; }
                    else ++evictions_;
                    return (int)i;
                }
            }
            return -1;
        }
        std::uint8_t oldh=st_[h];
        lo_[h]=klo;hi_[h]=khi;pn_[h]=dn_[h]=vis_[h]=0;st_[h]=OPEN;
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
        std::uint64_t work=0;      // cumulative expansions under this child
        std::uint32_t last_pn=1,last_dn=1; // for delta tracking
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

    // ---- STANDALONE EXACT REPLAY (--exact-replay=P) ---------------
    // Re-solve a recorded handoff root with the exact solver alone, free
    // of df-pn, so its true cost can be measured. This is the
    // benchmark that move-ordering work is graded against: unlike a
    // proof number, "nodes to solve this exact position" is a direct,
    // comparable quantity.
    //
    // The position is rebuilt from the CANONICAL occupancy carried in a
    // --exact-record row. Crucially, TState is rebuilt by REPLAYING the
    // occupied points through add() in the canonical orientation, and
    // the legal mask is RE-DERIVED by legal_for() from that same
    // occupancy. It is never inherited from a parent frame and never
    // assumed to match the canonical key's bit pattern. The game is D4
    // invariant, so a canonical-orientation reconstruction is a valid
    // representative of the orbit; using the key as if it were the
    // orientation actually reached by play was a previous bug.
    //
    // Returns: 0 UNKNOWN (budget exhausted), 1 WIN, 2 LOSS.
    // `out_nodes` receives the exact nodes consumed by this call.
    int exact_replay(const Bits& occupied,int stones,std::uint64_t budget,
                    std::uint64_t& out_nodes) {
        int verts[V],k=0;
        Bits s=occupied;
        while(any(s)){ if(k>=V) throw std::runtime_error("exact_replay: bad occupancy"); verts[k++]=take_lsb(s); }
        if(k!=stones) throw std::runtime_error("exact_replay: stones mismatch");
        TState state{};
        for(int i=0;i<k;++i) state=add(state,verts[i]);
        // Re-derive legality from the reconstructed occupancy.
        Bits legal=legal_for(occupied);
        // Reset the exact-local memo before every replayed position. The
        // replay driver reuses ONE solver for all rows, and exact_prop
        // consults exact_local_ when the publish mode is not ALL, so
        // without this a position solved by an earlier row would be
        // answered instantly from the cache (observed: one root reported
        // "LOSS" in 1 node at budget 500k after taking 8588 nodes at
        // 200k). That silently contaminates the per-root node counts this
        // benchmark exists to measure.
        exact_local_.reset();
        std::uint64_t b=budget;
        std::uint64_t before=exact_nodes_;
        ExactResult r=exact_prop(state,stones,legal,b);
        out_nodes=exact_nodes_-before;
        return (r==ExactResult::WIN)?1:((r==ExactResult::LOSS)?2:0);
    }
    void reset_exact_counters(){ exact_nodes_=0; }
    std::uint64_t exact_total_nodes() const { return exact_nodes_; }

    // ---- s5 ORACLE with a persistent canonical-key cache ----------
    // The quantified search below leans on this hard, so the oracle is
    // a first-class object with its own memo keyed by the canonical
    // occupancy. Every quantifier level revisits the same s5 positions
    // (different r3 choices can reach the same D4 orbit, and all 20
    // two-stone roots share the same reply set), so a shared cache
    // turns 20 * 121 * 117 * 116 queries into a far smaller number of
    // distinct exact searches.
    //
    // Only WIN/LOSS are cached. UNKNOWN means the node budget ran out
    // and must never be remembered as a result, or a later, better
    // funded query would inherit the earlier failure.
    struct Oracle {
        std::map<Bits,std::uint8_t> memo;  // 0 absent, 1 WIN, 2 LOSS
        std::uint64_t queries=0, hits=0, wins=0, losses=0, unknowns=0;
        std::uint64_t nodes=0;
    };
    Oracle oracle;
    // The first move of the root, needed by quant_solve to rebuild the
    // two-stone position. Set by quant_root().
    int root_first_move_=-1;

    // Solve one 5-stone position exactly, consulting and filling the
    // oracle. Returns 1 WIN, 2 LOSS, 0 UNKNOWN (budget exhausted).
    int s5_oracle(const TState& state,Bits occupied,std::uint64_t budget){
        Bits key=canonical(state);
        auto it=oracle.memo.find(key);
        if(it!=oracle.memo.end()){
            ++oracle.hits; ++oracle.queries;
            return it->second;
        }
        ++oracle.queries;
        Bits legal=legal_for(occupied);
        std::uint64_t b=budget;
        std::uint64_t before=exact_nodes_;
        ExactResult r=exact_prop(state,5,legal,b);
        oracle.nodes+=exact_nodes_-before;
        if(r==ExactResult::WIN){
            oracle.memo[key]=1; ++oracle.wins; return 1;
        }
        if(r==ExactResult::LOSS){
            oracle.memo[key]=2; ++oracle.losses; return 2;
        }
        ++oracle.unknowns;
        return 0;
    }
    void oracle_clear(){ oracle=Oracle(); }

    // Certificate for one winning two-stone reply. Filled only when the
    // quantified search returns WIN:
    //   reply r2, one winning third move r3, and for EVERY legal fourth
    //   reply r4 a winning fifth move r5 with that s5's canonical key.
    struct Cert5 {
        int r2=-1, r3=-1;
        struct Q4 { int r4=-1, r5=-1; Bits key{}; };
        std::vector<Q4> q4;
    };

    // Run the quantified search for one two-stone root {first,r2}.
    // Exposed so the driver can loop over replies while KEEPING the
    // oracle cache across them: all 20 replies share most of their s5
    // positions, so a per-reply oracle would redo the exact work.
    int quant_root(int first,int r2,std::uint64_t budget,Cert5* cert){
        root_first_move_=first;
        return quant_solve(r2,budget,cert);
    }
    const Oracle& oracle_stats() const { return oracle; }

    // ---- QUANTIFIED s5 SEARCH  (exists m3 forall m4 exists m5) ----
    // A two-stone root {m2,r2} is an OR node: to show the ORIGINAL
    // FIRST PLAYER wins it, ONE winning third move suffices. A
    // three-stone position is an AND node: every legal fourth reply
    // must be held. A four-stone position is an OR node again: one
    // winning fifth move per fourth reply.
    //
    //   two-stone r2  =  exists m3 : forall m4 : exists m5 : s5 WIN
    //
    // Solving it directly with a generic exact DFS would throw away
    // the structure we already paid for: the s5 layer is solved by an
    // exact oracle, so the search only has to decide three levels.
    // Nothing here touches proof numbers or thresholds; each step is a
    // direct evaluation of the quantifier formula.
    //
    // Returns 1 WIN, 2 LOSS, 0 UNKNOWN (a budget ran out somewhere).
    // `cert` is filled only on a WIN.
    int quant_solve(int r2,std::uint64_t budget,Cert5* cert){
        TState s2{}; s2=add(s2,root_first_move_); s2=add(s2,r2);
        Bits occ2{}; setbit(occ2,root_first_move_); setbit(occ2,r2);
        Bits legal3=legal_for(occ2);
        int n3=popcount(legal3);
        for(int i=0;i<n3;++i){
            int v=take_lsb(legal3);
            if(v<0) break;
            TState s3=add(s2,v);
            Bits occ3=occ2; setbit(occ3,v);
            Bits legal4=legal_for(occ3);
            int n4=popcount(legal4);
            bool all=true;
            std::vector<typename Cert5::Q4> rows;
            rows.reserve((std::size_t)n4);
            for(int j=0;j<n4;++j){
                int w=take_lsb(legal4);
                if(w<0) break;
                TState s4=add(s3,w);
                Bits occ4=occ3; setbit(occ4,w);
                Bits legal5=legal_for(occ4);
                int n5=popcount(legal5);
                bool found=false;
                for(int k=0;k<n5;++k){
                    int z=take_lsb(legal5);
                    if(z<0) break;
                    TState s5=add(s4,z);
                    Bits occ5=occ4; setbit(occ5,z);
                    int r=s5_oracle(s5,occ5,budget);
                    if(r==1){ typename Cert5::Q4 row; row.r4=w; row.r5=z; row.key=canonical(s5);
                              rows.push_back(row); found=true; break; }
                    // r==2 (this fifth move loses) -> try another
                    // r==0 (budget) -> the whole branch is inconclusive
                    if(r==0){ all=false; break; }
                }
                if(!found) break;
            }
            if(!all||(int)rows.size()!=n4) continue; // not a proof
            if(cert){
                cert->r2=r2; cert->r3=v; cert->q4=rows;
            }
            return 1; // exists m3 satisfied
        }
        return 0; // no winning third move found within budget
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

    // CHILD WORK: per direct child of the ROOT, keyed by the
    // child's canonical Bits (NOT a hash -- lo*const+hi collides
    // and produced 970 phantom "children" for a 20-child root).
    // work = number of times the search DESCENDED into this child
    // from the root (b1==this child at a root re-aggregation);
    // pn/dn/st = the child's CURRENT stored bounds; legal/count =
    // its legal-move count. Only populated when track_children_
    // is set (the diagnostic mode), because the per-child
    // bookkeeping would slow the main runs.
    struct ChildStat {
        std::uint64_t work=0;
        std::uint32_t pn=INF, dn=INF;
        std::uint8_t st=0;
        int count=0;
        int move=-1;
    };
    std::map<Bits,ChildStat> child_stat_;
    std::uint64_t child_stat_updates_=0;
    bool track_children_=false;

    // Create-or-update one child observation for the root-child
    // diagnostic. Called from gen_into when track_children_ is
    // set AND the parent is the root (is_root passed explicitly).
    // work is NOT touched here (it is accumulated at descent
    // time by add_child_work); pn/dn/st/count/move are refreshed.
    void note_child(const Bits& key,int move,int count,
                    std::uint32_t pn,std::uint32_t dn,std::uint8_t st){
        if(!track_children_) return;
        auto it=child_stat_.find(key);
        if(it==child_stat_.end()){
            ChildStat cs; cs.pn=pn; cs.dn=dn; cs.st=st;
            cs.count=count; cs.move=move;
            child_stat_[key]=cs;
        }else{
            it->second.pn=pn; it->second.dn=dn; it->second.st=st;
            it->second.count=count;
            if(move>=0) it->second.move=move;
        }
        ++child_stat_updates_;
    }

    // Accumulate one descent into the child with the given key.
    // Called from mid_iter when the search pushes a child frame
    // whose parent is the root.
    void add_child_work(const Bits& key){
        if(!track_children_) return;
        auto it=child_stat_.find(key);
        if(it!=child_stat_.end()) it->second.work += 1;
    }

    // Print the root-child diagnostic: one line per direct child of
    // the root, ranked by work descending. Fields: move, pn, dn,
    // solved status, cumulative work, legal count. The ranking
    // answers "which of the 20 replies dominates the proof search"
    // without waiting for the root to solve. The v=11 one-stone root
    // has 20 D4-distinct children; a larger n child count means the
    // map accumulated children of deeper frames too (should not
    // happen -- the guard is stones_==root_stones_ in note_child).
    void dump_children(){
        if(child_stat_.empty()){ *log_<<"[children] n=0\n"; return; }
        std::vector<std::pair<Bits,ChildStat>> v;
        v.reserve(child_stat_.size());
        for(auto& kv:child_stat_) v.push_back({kv.first,kv.second});
        std::sort(v.begin(),v.end(),
            [](const std::pair<Bits,ChildStat>& a,
               const std::pair<Bits,ChildStat>& b){
                if(a.second.work!=b.second.work)
                    return a.second.work>b.second.work;
                return a.second.pn<b.second.pn;
            });
        *log_ << "[children] t=" << (long long)std::chrono::duration<double>(
            Clock::now()-t0_).count() << "s n=" << v.size()
              << " updates=" << child_stat_updates_ << "\n";
        for(auto& kv:v){
            const ChildStat& cs=kv.second;
            *log_ << "  move=" << cs.move
                  << " pn=" << cs.pn << " dn=" << cs.dn
                  << " st=" << (int)cs.st
                  << " work=" << cs.work
                  << " legal=" << cs.count << "\n";
        }
        log_->flush();
    }

    // TIE-BREAK between children with EQUAL proof number, applied only
    // when the numbers are equal (so it can never change correctness --
    // b1 is only ever a choice of which equally-bounded child to dig
    // first). Ties are extremely common early in a search, which is
    // why the tie-break has outsized influence on the order in which
    // subproofs are visited.
    //
    // Modes (--tiebreak=):
    //   asc  (0, default) legal count ASC,  then canonical key ASC
    //   desc (1)         legal count DESC, then canonical key DESC
    //   key  (2)         canonical key ASC only (no count term)
    //
    // The `desc` rule is the one that helped the DFS solver in the
    // preregistered depth-5 experiment
    // (cpp/solvers/kyouen_solver_10_depth5_max_first.cpp).
    //
    // NOTE from the v=60 child diagnostic (N11-DFPN-CHILDREN.md): all 20
    // root children have legal=119, so at the root the count term is
    // inert for every mode and selection falls through to the key term.
    // The rule still differs at deeper nodes, where counts do vary.
    bool tie_better(const Gen& g,int i,int b) const {
        const GChild& ci=g.ch[(std::size_t)i];
        const GChild& cb=g.ch[(std::size_t)b];
        if(ci.count!=cb.count)
            return tiebreak_desc_ ? ci.count>cb.count : ci.count<cb.count;
        return tiebreak_desc_ ? (cb.key<ci.key) : (ci.key<cb.key);
    }
    bool tiebreak_desc_=false;

    // Optional exact endgame handoff. df-pn remains the outer search, but
    // when a node has few legal moves we can try to solve that subgame by
    // exact DFS. Only COMPLETED exact results are written back as WIN/LOSS;
    // a node-budget exhaustion returns UNKNOWN and leaves the df-pn bounds
    // sound. The exact DFS reuses solved entries in the same TT, so work
    // learned by one root/sweep can help later roots too.
    enum class ExactResult : std::uint8_t { UNKNOWN=0, WIN=1, LOSS=2 };
    int exact_legal_=0;                    // 0 disables the hybrid
    std::uint64_t exact_budget_=100000;    // nodes per handoff attempt
    // Per-stone-count budget overrides. The s5 frontier measured in
    // N11-DFPN-S5-BENCH.md needs 130k..5.7M nodes to close while s6
    // closes inside 200k, so a single global budget either wastes a lot
    // on s6 or leaves s5 aborting. Lookup is by stone count; anything
    // not listed falls back to exact_budget_.
    std::array<std::uint64_t,64> exact_budget_by_stones_{};
    bool exact_budget_by_stones_set_[64]={};
    std::uint64_t budget_for_stones(int stones) const {
        int s=(stones>=0&&stones<64)?stones:63;
        if(exact_budget_by_stones_set_[s]) return exact_budget_by_stones_[s];
        return exact_budget_;
    }
    int exact_retries_=1;                  // attempts per TT residency
    // Per-stone-count THRESHOLD overrides, mirroring the per-stone
    // budget above. Needed because the legal-move gate cannot separate
    // layers on its own: a k-stone position has at most 121-k legal
    // moves, so a single --exact-legal that admits s7 (>=114) also
    // admits every shallower layer, and raising it makes the shallower
    // layers fail the gate more often rather than less. See
    // research/verification/N11-DFPN-FRONTIER-LAYERS.md.
    // Lookup is by stone count; anything not listed falls back to
    // exact_legal_.
    std::array<int,64> exact_legal_by_stones_{};
    bool exact_legal_by_stones_set_[64]={};
    bool handoff_allowed(int stones,int legal) const {
        int s=(stones>=0&&stones<64)?stones:63;
        int lim=exact_legal_by_stones_set_[s]?exact_legal_by_stones_[s]:exact_legal_;
        return lim>0 && legal<=lim;
    }
    // Exact-DFS child ordering, A/B-able. Ordering cannot change a
    // result, only the work needed to reach it, so this is safe to vary
    // and is graded on total nodes over a fixed benchmark set.
    enum class ExactOrder : std::uint8_t { COUNT=0, COUNTD=1, KEY=2 };
    ExactOrder exact_order_=ExactOrder::COUNT;
    bool exact_order_desc_=false;          // true when exact_order_==COUNTD
    enum class ExactPublishMode : std::uint8_t { ALL=0, ROOT=1, SEPARATE=2 };
    ExactPublishMode exact_publish_mode_=ExactPublishMode::ALL;

    // Fixed-capacity generation-stamped memo for ONE exact handoff.
    // exact_budget defaults to 200k in the experiments; 2^19 slots keeps
    // load comfortably below 50% without any per-node heap allocation.
    // Replacement can only lose cache hits, never affect correctness.
    class ExactLocalMemo {
    public:
        static constexpr int PROBE=32;
        explicit ExactLocalMemo(unsigned power=19)
          : n_(std::size_t{1}<<power),mask_(n_-1),
            lo_(n_,0),hi_(n_,0),gen_(n_,0),st_(n_,0) {}
        void reset(){
            ++cur_;
            if(cur_==0){
                std::fill(gen_.begin(),gen_.end(),0);
                cur_=1;
            }
        }
        std::uint8_t get(Bits k) const {
            std::size_t i=mix(k.lo,k.hi)&mask_;
            for(int j=0;j<PROBE;++j){
                if(gen_[i]!=cur_) return 0;
                if(lo_[i]==k.lo && hi_[i]==k.hi) return st_[i];
                i=(i+1)&mask_;
            }
            return 0;
        }
        bool put(Bits k,std::uint8_t v){
            std::size_t h=mix(k.lo,k.hi)&mask_;
            std::size_t i=h;
            for(int j=0;j<PROBE;++j){
                if(gen_[i]!=cur_){
                    lo_[i]=k.lo;hi_[i]=k.hi;st_[i]=v;gen_[i]=cur_;
                    return true;
                }
                if(lo_[i]==k.lo && hi_[i]==k.hi){
                    st_[i]=v;
                    return false;
                }
                i=(i+1)&mask_;
            }
            lo_[h]=k.lo;hi_[h]=k.hi;st_[h]=v;gen_[h]=cur_;
            return true;
        }
    private:
        std::size_t n_,mask_;
        std::vector<std::uint64_t> lo_,hi_;
        std::vector<std::uint32_t> gen_;
        std::vector<std::uint8_t> st_;
        std::uint32_t cur_=1;
        static std::uint64_t mix64(std::uint64_t x){
            x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;
            x^=x>>27;x*=0x94d049bb133111ebULL;
            return x^(x>>31);
        }
        static std::uint64_t mix(std::uint64_t a,std::uint64_t b){
            return mix64(a ^ (b*0x9e3779b97f4a7c15ULL));
        }
    };
    ExactLocalMemo exact_local_;
    std::uint64_t exact_calls_=0, exact_nodes_=0, exact_aborts_=0;
    std::uint64_t exact_trigger_win_=0, exact_trigger_loss_=0, exact_stores_=0;
    std::uint64_t exact_local_stores_=0;
    std::uint64_t exact_call_hist_[64]={};
    std::uint64_t exact_win_hist_[64]={}, exact_loss_hist_[64]={}, exact_abort_hist_[64]={};

    // ---- HANDOFF RECORD DIAGNOSTIC (--exact-record) ----------------
    // One record per exact-handoff ATTEMPT, emitted as it happens, so
    // that aborted handoffs can be counted, deduplicated by canonical
    // key, and replayed standalone. Without this, an aborted s5 root is
    // invisible: exact_abort_hist_ only says "N calls aborted", not
    // which positions, how many were repeats, or how deep they were.
    //
    // The position is recorded as its canonical Bits key plus the stone
    // count and legal count. A standalone replay RE-DERIVES occupied and
    // legal from the canonical occupancy rather than trusting an
    // inherited mask: canonical() returns the minimum over the 8 D4
    // images, so the key is generally a rotated image and does not
    // correspond to the orientation actually reached by play. The game
    // is D4 invariant, so recomputing legal from the canonical occupancy
    // is correct. This is the same mistake the old root-child code made
    // (rebuilding TState from the key and mixing it with the parent's
    // inherited legal mask), so it is called out explicitly here.
    struct HandoffRec {
        Bits key{};              // canonical occupancy mask
        int stones=0;
        int legal=0;            // popcount(legal) at handoff time
        int depth_from_root=0;  // frame depth - root stone count
        bool is_or=false;       // is_or(stones): OR node for side to move
        int retries=0;          // handoff attempt index for this key (0-based)
        std::uint64_t nodes=0;  // exact nodes consumed by THIS attempt
        std::uint8_t result=0;  // 0=UNKNOWN 1=WIN 2=LOSS
        std::uint64_t seq=0;    // global attempt counter
    };
    std::vector<HandoffRec> exact_recs_;
    bool track_exact_=false;
    int exact_record_limit_=0;   // 0 = unlimited
    std::uint64_t exact_rec_seq_=0;

    // Reset the per-root handoff record list. Called from solve_common
    // so each root's records are its own; the exact_* counters and the
    // stone histogram stay cumulative for the whole process.
    void exact_record_begin(){
        exact_recs_.clear();
        exact_rec_seq_=0;
    }
    void exact_record_add(const Bits& key,int stones,int legal_cnt,
                          int depth_from_root,unsigned retries,
                          std::uint64_t nodes,ExactResult r){
        if(exact_record_limit_>0 && (int)exact_recs_.size()>=exact_record_limit_) return;
        HandoffRec h;
        h.key=key; h.stones=stones; h.legal=legal_cnt;
        h.depth_from_root=depth_from_root; h.is_or=is_or(stones);
        h.retries=(int)retries; h.nodes=nodes;
        h.result=(r==ExactResult::WIN)?1:((r==ExactResult::LOSS)?2:0);
        h.seq=exact_rec_seq_++;
        exact_recs_.push_back(h);
    }
    const std::vector<HandoffRec>& exact_records() const { return exact_recs_; }

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
    void gen_into(const TState& state,int stones,Bits legal,Gen& g,bool is_root=false){
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
            c.work=0; c.last_pn=1; c.last_dn=1;
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
            if(track_children_ && is_root) note_child(nk,v,c.count,c.pn,c.dn,c.st);
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

    void exact_store(const Bits& key,ExactResult r){
        if(r==ExactResult::UNKNOWN) return;
        int s=tt_.find(key.lo,key.hi);
        if(s>=0 && tt_.st_[(std::size_t)s]>=PnTT::WIN){
            const bool old_win=tt_.st_[(std::size_t)s]==PnTT::WIN;
            const bool new_win=r==ExactResult::WIN;
            if(old_win!=new_win) throw std::runtime_error("exact solver contradicts solved TT entry");
            return;
        }
        if(s<0){
            s=tt_.acquire(key.lo,key.hi);
            if(s<0) throw std::runtime_error("TT full at exact_store");
        }
        tt_.pn_[(std::size_t)s]=(r==ExactResult::WIN)?0:INF;
        tt_.dn_[(std::size_t)s]=(r==ExactResult::WIN)?INF:0;
        tt_.mark_solved(s,(r==ExactResult::WIN)?PnTT::WIN:PnTT::LOSS);
        ++exact_stores_;
    }

    void exact_record(const Bits& key,ExactResult r){
        if(r==ExactResult::UNKNOWN) return;
        if(exact_publish_mode_==ExactPublishMode::ALL){
            exact_store(key,r);
        }else{
            // ROOT: per-handoff cache (generation reset before every call).
            // SEPARATE: the same fixed cache persists across handoffs and
            // roots, giving cross-call exact reuse without occupying PnTT.
            if(exact_local_.put(
                    key,(r==ExactResult::WIN)?std::uint8_t(1):std::uint8_t(2)))
                ++exact_local_stores_;
        }
    }

    ExactResult exact_prop(const TState& state,int stones,Bits legal,
                           std::uint64_t& budget){
        Bits key=canonical(state);
        int s=tt_.find(key.lo,key.hi);
        if(s>=0 && tt_.st_[(std::size_t)s]>=PnTT::WIN)
            return tt_.st_[(std::size_t)s]==PnTT::WIN ? ExactResult::WIN : ExactResult::LOSS;
        if(exact_publish_mode_!=ExactPublishMode::ALL){
            std::uint8_t lv=exact_local_.get(key);
            if(lv) return lv==1 ? ExactResult::WIN : ExactResult::LOSS;
        }

        if(budget==0) return ExactResult::UNKNOWN;
        --budget;
        ++exact_nodes_;
        if((exact_nodes_ & 4095ULL)==0 && deadline_s_>0){
            double el=std::chrono::duration<double>(Clock::now()-t0_).count();
            if(el>=deadline_s_) throw std::runtime_error("TIME_BUDGET");
        }

        if(!any(legal)){
            // Side to move loses. The fixed proposition is "the original
            // first player wins", so a terminal is true exactly when the
            // second player is to move (odd number of stones).
            ExactResult r=is_or(stones)?ExactResult::LOSS:ExactResult::WIN;
            exact_record(key,r);
            return r;
        }

        auto gb=std::make_unique<Gen>();
        Gen& g=*gb;
        gen_into(state,stones,legal,g,false);
        const bool isor=is_or(stones);

        // DFS ordering only affects speed, never the result, so it is safe to
        // A/B. The decisive-child rule comes first because it is the only
        // part that can terminate the loop early: if an OR node's child
        // is already known WIN (or an AND node's already LOSS) we return
        // on the first such child regardless of the rest of the order.
        // Within each priority class we then choose by a named rule so
        // that a single rule can be changed at a time:
        //
        //   count : fewer legal moves first        (baseline)
        //   countd: more legal moves first         (the rule that won the
        //          preregistered depth-5 DFS experiment, see
        //          cpp/solvers/kyouen_solver_10_depth5_max_first.cpp)
        //   key   : canonical key ascending, count ignored
        //
        // --exact-order selects this; it is recorded in the run header
        // and in every replay row so a benchmark can never be attributed
        // to the wrong rule.
        const bool asc=!exact_order_desc_;
        const bool by_key=(exact_order_==ExactOrder::KEY);
        std::sort(g.ch.begin(),g.ch.begin()+g.n,[&](const GChild& a,const GChild& b){
            auto pri=[&](const GChild& x){
                if(isor){
                    if(x.st==PnTT::WIN) return 0;
                    if(x.st==PnTT::OPEN) return 1;
                    return 2;
                }else{
                    if(x.st==PnTT::LOSS) return 0;
                    if(x.st==PnTT::OPEN) return 1;
                    return 2;
                }
            };
            int pa=pri(a),pb=pri(b);
            if(pa!=pb) return pa<pb;
            if(!by_key && a.count!=b.count)
                return asc ? (a.count<b.count) : (a.count>b.count);
            if(by_key) return a.key<b.key;
            // count ties: keep the key order deterministic in both modes
            // so the only variable is the count comparison.
            return a.key<b.key;
        });

        bool unknown=false;
        for(int i=0;i<g.n;++i){
            ExactResult cr;
            const GChild& ch=g.ch[(std::size_t)i];
            if(ch.st==PnTT::WIN) cr=ExactResult::WIN;
            else if(ch.st==PnTT::LOSS) cr=ExactResult::LOSS;
            else cr=exact_prop(ch.ts,stones+1,ch.legal,budget);

            if(isor && cr==ExactResult::WIN){
                exact_record(key,ExactResult::WIN);
                return ExactResult::WIN;
            }
            if(!isor && cr==ExactResult::LOSS){
                exact_record(key,ExactResult::LOSS);
                return ExactResult::LOSS;
            }
            if(cr==ExactResult::UNKNOWN) unknown=true;
        }

        if(unknown) return ExactResult::UNKNOWN;
        ExactResult r=isor?ExactResult::LOSS:ExactResult::WIN;
        exact_record(key,r);
        return r;
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
        tt_.vis_[(std::size_t)s]|=1u;
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
              << " avgprobe=" << ap
              << " exact_calls=" << exact_calls_
              << " exact_nodes=" << exact_nodes_
              << " exact_abort=" << exact_aborts_
              << " exact_win=" << exact_trigger_win_
              << " exact_loss=" << exact_trigger_loss_
              << " exact_stores=" << exact_stores_
              << " exact_local=" << exact_local_stores_
              << std::endl;
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
            // Handoff gate. The per-stone-count threshold overrides the
            // global --exact-legal when set, which is the only way to
            // target a specific layer (see N11-DFPN-FRONTIER-LAYERS.md).
            if(handoff_allowed(st.back().stones,popcount(st.back().legal))){
                int es=tt_.find(st.back().key.lo,st.back().key.hi);
                if(es>=0 && tt_.st_[(std::size_t)es]==PnTT::OPEN){
                    unsigned attempts=(tt_.vis_[(std::size_t)es]>>1)&0xffu;
                    if(attempts<(unsigned)exact_retries_){
                        tt_.vis_[(std::size_t)es]=(tt_.vis_[(std::size_t)es]&1u)
                            | ((std::uint32_t(attempts+1)&0xffu)<<1);
                        ++exact_calls_;
                        int eh=st.back().stones<64?st.back().stones:63;
                        ++exact_call_hist_[eh];
                        if(exact_publish_mode_==ExactPublishMode::ROOT)
                            exact_local_.reset();
                        std::uint64_t b=budget_for_stones(st.back().stones);
                        // Snapshot the GLOBAL exact-node counter so the
                        // nodes consumed by THIS attempt can be isolated.
                        std::uint64_t nodes_before=exact_nodes_;
                        int legal_cnt=popcount(st.back().legal);
                        int depth_from_root=st.back().depth-root_stones_;
                        ExactResult er=exact_prop(st.back().state,st.back().stones,
                                                  st.back().legal,b);
                        if(track_exact_)
                            exact_record_add(st.back().key,st.back().stones,legal_cnt,
                                             depth_from_root,attempts,
                                             exact_nodes_-nodes_before,er);
                        if(er==ExactResult::WIN){
                            if(exact_publish_mode_!=ExactPublishMode::ALL)
                                exact_store(st.back().key,er);
                            ++exact_trigger_win_;
                            ++exact_win_hist_[eh];
                            st.pop_back();
                            continue;
                        }
                        if(er==ExactResult::LOSS){
                            if(exact_publish_mode_!=ExactPublishMode::ALL)
                                exact_store(st.back().key,er);
                            ++exact_trigger_loss_;
                            ++exact_loss_hist_[eh];
                            st.pop_back();
                            continue;
                        }
                        ++exact_aborts_;
                        ++exact_abort_hist_[eh];
                    }
                }
            }

            int frd=st.back().depth, frs=st.back().stones;
            std::uint32_t frtp=st.back().tp, frtd=st.back().td;
            // Only the ROOT frame contributes to the child diagnostic.
            // Passing it explicitly (rather than inferring from a
            // shared stones_ field) is what keeps the child count at
            // exactly the root's fan-out: expand()'s throwaway Gen and
            // every deeper frame pass false.
            bool is_root=(frs==root_stones_);
            Gen& g=st.back().gen();
            gen_into(st.back().state,frs,st.back().legal,g,is_root);
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
                        tie_better(g,i,b1)) better=true;
                }else{
                    if(g.ch[(std::size_t)i].dn<g.ch[(std::size_t)b1].dn) better=true;
                    else if(g.ch[(std::size_t)i].dn==g.ch[(std::size_t)b1].dn &&
                        tie_better(g,i,b1)) better=true;
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
            // CHILD WORK: attribute this descent to b1 so the
            // root-child diagnostic can rank children by the
            // expansions their subproof consumed. last_pn/last_dn
            // are refreshed on every re-aggregation below so the
            // diagnostic sees the freshest bounds, not the stale
            // values from the initial gen_into.
            g.ch[(std::size_t)b1].work += 1;
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
            // CHILD WORK: attribute this descent to b1 so the
            // root-child diagnostic can rank children by the
            // expansions their subproof consumed.
            if(track_children_ && frs==root_stones_) add_child_work(ck);
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
        // Reset per-root child diagnostics.
        child_stat_.clear(); child_stat_updates_=0;
        exact_record_begin();
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
        // Emit the t=0 child diagnostic header (empty for now).
        *log_ << "[children] t=0s n=0\n";
        log_->flush();
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
            if(track_children_) dump_children();
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
        dump_children();
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
    void memo_evictions(std::uint64_t& open_ev,std::uint64_t& solved_ev) const {
        open_ev=tt_.evictions_;
        solved_ev=tt_.evicted_solved();
    }
    void partial_progress(std::uint32_t& pn,std::uint32_t& dn,
                          std::uint64_t& exp,std::uint64_t& vis) const {
        pn=r_exp_fallback_pn; dn=r_exp_fallback_dn;
        exp=r_exp_fallback_exp; vis=r_exp_fallback_vis;
    }
    void exp_hist(std::uint64_t* out,int n) const {
        for(int i=0;i<n;++i) out[i]=exp_hist_[i<64?i:63];
    }
    int max_depth() const { return max_depth_; }
    // Enable the root-child diagnostic. When set, each direct child
    // of the root gets its cumulative work (descents), current
    // pn/dn, solved status and legal count logged on completion.
    void set_track_children(bool b){ track_children_=b; }
    bool tracking_children() const { return track_children_; }
    // Handoff recording for the exact-frontier diagnostic. When set, one
    // record per exact-handoff attempt is kept for the current root and
    // dumped as CSV by run() on completion or timeout.
    void set_track_exact(bool b){ track_exact_=b; }
    void set_exact_record_limit(int n){ exact_record_limit_=n<0?0:n; }
    // Tie-break mode: false = count ASC then key ASC (baseline),
    // true = count DESC then key DESC (the DFS depth-5 winner).
    void set_tiebreak_desc(bool b){ tiebreak_desc_=b; }
    void set_exact_handoff(int legal,std::uint64_t budget,int retries,int publish_mode){
        exact_legal_=std::max(0,legal);
        exact_budget_=std::max<std::uint64_t>(1,budget);
        exact_retries_=std::clamp(retries,1,255);
        exact_publish_mode_=(publish_mode==0?ExactPublishMode::ALL:
                            (publish_mode==1?ExactPublishMode::ROOT:
                                             ExactPublishMode::SEPARATE));
    }
    // Per-stone-count budget override, e.g. 5 -> 5000000.
    void set_exact_budget_for_stones(int stones,std::uint64_t budget){
        int s=(stones>=0&&stones<64)?stones:63;
        exact_budget_by_stones_[s]=std::max<std::uint64_t>(1,budget);
        exact_budget_by_stones_set_[s]=true;
    }
    // Per-stone-count threshold override, e.g. 7 -> 114. A value of 0
    // disables handoff for that stone count entirely.
    void set_exact_legal_for_stones(int stones,int legal){
        int s=(stones>=0&&stones<64)?stones:63;
        exact_legal_by_stones_[s]=std::max(0,legal);
        exact_legal_by_stones_set_[s]=true;
    }
    // Child ordering for the exact DFS. 0=count asc (baseline),
    // 1=count desc, 2=key asc. Affects speed only, never the result.
    void set_exact_order(int mode){
        exact_order_=(mode==1)?ExactOrder::COUNTD:
                     ((mode==2)?ExactOrder::KEY:ExactOrder::COUNT);
        exact_order_desc_=(mode==1);
    }
    int exact_order_name() const {
        return exact_order_desc_?1:((exact_order_==ExactOrder::KEY)?2:0);
    }
    void exact_counters(std::uint64_t& calls,std::uint64_t& nodes,
                        std::uint64_t& aborts,std::uint64_t& wins,
                        std::uint64_t& losses,std::uint64_t& stores,
                        std::uint64_t& local_stores) const {
        calls=exact_calls_; nodes=exact_nodes_; aborts=exact_aborts_;
        wins=exact_trigger_win_; losses=exact_trigger_loss_;
        stores=exact_stores_; local_stores=exact_local_stores_;
    }
    void dump_exact_hist(std::ostream& os) const {
        os<<"[exact-depth]";
        bool anyv=false;
        for(int s=0;s<64;++s){
            if(!exact_call_hist_[s]) continue;
            anyv=true;
            os<<" s"<<s<<"="<<exact_call_hist_[s]
              <<"/"<<exact_win_hist_[s]
              <<"/"<<exact_loss_hist_[s]
              <<"/"<<exact_abort_hist_[s];
        }
        if(!anyv) os<<" none";
        os<<" (call/win/loss/abort)\n";
        os.flush();
    }

    // Dump every recorded handoff attempt as one CSV row. The header is
    // emitted once per process (guarded by a static) so the file is
    // directly loadable. Columns are chosen so a standalone replay can
    // rebuild the position from (key_lo, key_hi, stones) and re-derive
    // the legal mask from the canonical occupancy:
    //   seq,stones,key_lo,key_hi,legal,depth_from_root,is_or,retries,nodes,result
    // result is 0=UNKNOWN 1=WIN 2=LOSS. is_or is 1 for an OR node (the
    // side to move maximizes), 0 for AND.
    void dump_exact_records(std::ostream& os,const std::string& tag) const {
        static bool header_written=false;
        if(!header_written){
            os<<"# exact-handoff records: tag,seq,stones,key_lo,key_hi,legal,"
                 "depth_from_root,is_or,retries,nodes,result\n";
            header_written=true;
        }
        for(const auto& h:exact_recs_){
            os<<tag<<","<<h.seq<<","<<h.stones<<","
              <<h.key.lo<<","<<h.key.hi<<","<<h.legal<<","
              <<h.depth_from_root<<","<<(h.is_or?1:0)<<","
              <<h.retries<<","<<h.nodes<<","<<(int)h.result<<"\n";
        }
        os.flush();
    }

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
               bool do_empty,bool do_reps,bool do_children,bool tiebreak_desc,
               int exact_legal,std::uint64_t exact_budget,int exact_retries,
               int exact_publish_mode,bool do_exact_record,
               int exact_record_limit,
               const std::vector<std::pair<int,std::uint64_t>>& budget_by_stones,
               const std::vector<std::pair<int,int>>& legal_by_stones,
               int exact_order,
               std::ostream& L,std::ostream& C,
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
    solver.set_track_children(do_children);
    solver.set_track_exact(do_exact_record);
    solver.set_exact_record_limit(exact_record_limit);
    solver.set_tiebreak_desc(tiebreak_desc);
    solver.set_exact_handoff(exact_legal,exact_budget,exact_retries,exact_publish_mode);
    for(const auto& kv:budget_by_stones)
        solver.set_exact_budget_for_stones(kv.first,kv.second);
    for(const auto& kv:legal_by_stones)
        solver.set_exact_legal_for_stones(kv.first,kv.second);
    solver.set_exact_order(exact_order);
    L<<"n="<<N<<" built forbidden="<<solver.forbidden_count()
     <<" tiebreak="<<(tiebreak_desc?"desc":"asc")
     <<" exact_legal="<<exact_legal
     <<" exact_order="<<exact_order
     <<" exact_budget="<<exact_budget
     <<" exact_retries="<<exact_retries
     <<" exact_publish="<<(exact_publish_mode==0?"all":
                            (exact_publish_mode==1?"root":"separate"))<<std::endl;
    L.flush();
    // Deadline counts from the first root actually started, not from solver
    // construction (which builds the ~8M-entry forbidden table). Setting it
    // here keeps per-probe budgets comparable across --only selections.
    solver.set_deadline(budget_s);
    int n_done=0,n_timeout=0;
    std::uint64_t root_seq=0;
    auto wall0=std::chrono::steady_clock::now();
    auto run_one=[&](const std::string& tag,const std::vector<int>& stones){
        const std::uint64_t seq=++root_seq;
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
             <<" solved_disc="<<solver.memo_solved_disc();
            {
                std::uint64_t eo,es;
                solver.memo_evictions(eo,es);
                C<<" evict_open="<<eo<<" evict_solved="<<es;
            }
            {
                std::uint64_t ec,en,ea,ew,el,es,els;
                solver.exact_counters(ec,en,ea,ew,el,es,els);
                C<<" exact_calls="<<ec<<" exact_nodes="<<en
                 <<" exact_abort="<<ea<<" exact_win="<<ew
                 <<" exact_loss="<<el<<" exact_stores="<<es
                 <<" exact_local="<<els;
            }
            C<<" seq="<<seq<<" wall_s="<<(long long)wall<<"\n";
            solver.csv_flush();
            solver.dump_exact_hist(L);
            if(do_exact_record) solver.dump_exact_records(C,tag);
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
        solver.dump_exact_hist(L);
        if(do_exact_record) solver.dump_exact_records(C,tag);
        L<<"[done] ["<<tag<<"] "<<outcome_str(r.outcome)
         <<" expansions="<<r.expansions
         <<" root_pn="<<r.root_pn<<" root_dn="<<r.root_dn
         <<" memo="<<solver.memo_used()<<"/"<<solver.memo_capacity();
        {
            std::uint64_t eo,es;
            solver.memo_evictions(eo,es);
            L<<" evict_open="<<eo<<" evict_solved="<<es;
        }
        {
            std::uint64_t ec,en,ea,ew,el,es,els;
            solver.exact_counters(ec,en,ea,ew,el,es,els);
            L<<" exact_calls="<<ec<<" exact_nodes="<<en
             <<" exact_abort="<<ea<<" exact_win="<<ew
             <<" exact_loss="<<el<<" exact_stores="<<es
             <<" exact_local="<<els;
        }
        L<<" seq="<<seq<<" wall_s="<<(long long)wall<<std::endl;
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

// ---- standalone exact replay of recorded handoff roots ------------
// Reads an --exact-record CSV and re-solves each recorded position with
// the exact solver ALONE, no df-pn and no transposition table shared
// between positions, so each root's true cost is measured in isolation.
// One solver instance is reused for all rows: building the forbidden
// table per row would dominate the runtime (the 11x11 table has ~95k
// entries) and has nothing to do with what is being measured.
//
// `--only=` here filters by STONE COUNT, so `--only=5` benchmarks just
// the s5 frontier.
template<int N>
    static int run_exact_replay(const std::string& path,std::uint64_t budget,
                            unsigned memo_power,const std::string& only,
                            int exact_order,std::ostream& O){
    std::ifstream in(path);
    if(!in){ std::cerr<<"cannot open --exact-replay\n"; return 1; }
    O<<"# exact replay: order="<<exact_order<<" (0=count-asc 1=count-desc 2=key-asc)"<<std::endl;
    O<<"# exact replay: id,stones,legal,is_or,budget,result,nodes,wall_s,key_lo,key_hi\n";
    O.flush();
    // Memo size for the per-row solver. The main table default is 2^26,
    // whose assign() touches ~1 GB and would dominate a benchmark whose
    // whole point is a few million nodes. 2^22 (4M entries, ~100 MB)
    // comfortably holds a single exact search and is reset per row.
    unsigned row_memo = std::min<unsigned>(memo_power,22);
    std::string line; int id=0;
    double w0=std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    while(std::getline(in,line)){
        if(line.empty()||line[0]=='#') continue;
        std::vector<std::string> f;
        std::stringstream ss(line); std::string tok;
        while(std::getline(ss,tok,',')) f.push_back(tok);
        // record rows: tag,seq,stones,lo,hi,legal,depth,is_or,retries,nodes,result
        if(f.size()<11) continue;
        int stones=std::stoi(f[2]);
        if(!only.empty()){
            std::stringstream t(only); std::string w; bool want=false;
            while(std::getline(t,w,','))
                if(!w.empty()&&std::stoi(w)==stones){want=true;break;}
            if(!want) continue;
        }
        Bits occ; occ.lo=std::stoull(f[3]); occ.hi=std::stoull(f[4]);
        int legal=std::stoi(f[5]);
        double t0=std::chrono::duration<double>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        std::uint64_t nodes=0; int res=-1;
        try{
            // A FRESH solver per row. Reusing one instance leaks state
            // between positions: exact_prop consults the main PnTT first,
            // and publish=ALL writes solved entries into it, so a position
            // overlapping an earlier row would be answered from that
            // table and report a tiny node count. That is exactly what a
            // per-root benchmark must not measure.
            DfPn<N> row_solver(row_memo);
            row_solver.set_deadline(0);
            row_solver.set_exact_handoff(0,1,1,0); // publish=ALL
            row_solver.set_exact_order(exact_order);
            res=row_solver.exact_replay(occ,stones,budget,nodes);
        }catch(const std::exception& e){
            O<<"replay_error,"<<id<<","<<stones<<",0,\""<<e.what()<<"\"\n"; O.flush(); ++id; continue;
        }
        double t1=std::chrono::duration<double>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        O<<"replay,"<<id<<","<<stones<<","<<legal<<","
         <<(stones%2==0?1:0)<<","<<budget<<","<<res<<","
         <<nodes<<","<<(long long)(t1-t0)<<","<<occ.lo<<","<<occ.hi<<"\n";
        O.flush();
        ++id;
    }
    double w1=std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    O<<"# replay_done rows="<<id<<" wall_s="<<(long long)(w1-w0)<<"\n";
    O.flush();
    return 0;
}

// ---- quantified s5 search driver ----------------------------------
// For a two-stone root {m2,r2}, decide
//     exists m3 : forall m4 : exists m5 : s5 WIN
// against a shared s5 exact oracle. The oracle cache persists across
// all replies in one process, because different replies and different
// third moves reach many of the same D4 orbits of 5-stone positions.
//
// Certificate output on a WIN:
//   reply r2
//     winning third move r3
//       for every legal fourth reply r4
//         a winning fifth move r5 and the canonical key of that s5
template<int N>
static int run_quant(int first,const std::string& replies,
                     std::uint64_t budget,double timeout_s,
                     unsigned memo_power,std::ostream& O){
    DfPn<N> solver(memo_power);
    // The exact DFS inside the oracle must not be gated by any hybrid
    // threshold or by the global time budget: it is called directly.
    solver.set_deadline(0);
    solver.set_exact_handoff(0,1,1,0); // publish=ALL (oracle is its own memo)
    solver.oracle_clear();

    std::vector<int> rs;
    {
        std::stringstream ss(replies); std::string tok;
        while(std::getline(ss,tok,',')) {
            if(tok.empty()) continue;
            try { rs.push_back(std::stoi(tok)); }
            catch(const std::exception&){ /* skip malformed token */ }
        }
    }
    if(rs.empty()){ O<<"# no valid replies parsed from: "<<replies<<"\n"; return 2; }
    O<<"# quantified s5 search: first="<<first
     <<" replies="<<rs.size()<<" node_budget="<<budget
     <<" timeout_s="<<timeout_s<<"\n";
    O<<"# reply,outcome,r3,n_r4,oracle_queries,oracle_hits,oracle_nodes,wall_s\n";
    O.flush();

    int nwin=0, nloss=0, nunk=0;
    double t_all=std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    for(int r2:rs){
        double t0=std::chrono::duration<double>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        typename DfPn<N>::Cert5 cert;
        int res=0;
        bool timed_out=false;
        try{
            res=solver.quant_root(first,r2,budget,&cert);
        }catch(const std::exception& e){
            O<<"quant_error,"<<r2<<",EXCEPTION,\""<<e.what()<<"\"\n"; O.flush();
            ++nunk; continue;
        }
        double t1=std::chrono::duration<double>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        const auto& oc=solver.oracle_stats();
        O<<"quant,"<<r2<<","
         <<(res==1?"WIN":(res==2?"LOSS":"UNKNOWN"))<<","
         <<(cert.r3>=0?cert.r3:-1)<<","<<cert.q4.size()<<","
         <<oc.queries<<","<<oc.hits<<","<<oc.nodes<<","<<(long long)(t1-t0)<<"\n";
        if(res==1){
            ++nwin;
            O<<"# certificate reply="<<r2<<" r3="<<cert.r3
             <<" n_r4="<<cert.q4.size()<<"\n";
            for(const auto& row:cert.q4){
                O<<"#   r4="<<row.r4<<" r5="<<row.r5
                 <<" s5key="<<row.key.lo<<","<<row.key.hi<<"\n";
            }
        }else if(res==2) ++nloss; else ++nunk;
        O.flush();
        if(timeout_s>0 && (t1-t_all)>=timeout_s){ timed_out=true; }
        if(timed_out) break;
    }
    double t_end=std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    const auto& oc=solver.oracle_stats();
    O<<"# SUMMARY WIN="<<nwin<<" LOSS="<<nloss<<" UNKNOWN="<<nunk
     <<" oracle_queries="<<oc.queries<<" oracle_hits="<<oc.hits
     <<" oracle_wins="<<oc.wins<<" oracle_losses="<<oc.losses
     <<" oracle_unknowns="<<oc.unknowns<<" oracle_nodes="<<oc.nodes
     <<" wall_s="<<(long long)(t_end-t_all)<<"\n";
    O.flush();
    return 0;
}

int main(int argc,char**argv){
    try{
        int n=11;
        unsigned pow=26;
        bool reps=false, empty=false, children=false, tiebreak_desc=false;
        bool exact_record=false;
        int exact_record_limit=0;
        std::string exact_replay_path="";
        std::uint64_t exact_replay_budget=1000000;
        std::string exact_budget_by_stones_spec="";
        std::string exact_legal_by_stones_spec="";
        int quant_first=60;
        std::string quant_replies="";
        std::uint64_t quant_budget=20000000;
        double quant_timeout=0;
        int exact_order=0; // 0=count asc, 1=count desc, 2=key asc
        std::string only="";
        double budget_s=0;
        int exact_legal=0, exact_retries=1;
        std::uint64_t exact_budget=100000;
        int exact_publish_mode=0; // 0=all, 1=root-only, 2=separate persistent exact cache
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
            else if(a=="--children")children=true;
            else if(a=="--tiebreak=asc")tiebreak_desc=false;
            else if(a=="--tiebreak=desc")tiebreak_desc=true;
            else if(a.rfind("--exact-legal=",0)==0)exact_legal=std::stoi(a.substr(14));
            else if(a.rfind("--exact-budget=",0)==0)exact_budget=std::stoull(a.substr(15));
            else if(a.rfind("--exact-retries=",0)==0)exact_retries=std::stoi(a.substr(16));
            else if(a=="--exact-publish=all")exact_publish_mode=0;
            else if(a=="--exact-publish=root")exact_publish_mode=1;
            else if(a=="--exact-publish=separate")exact_publish_mode=2;
            else if(a=="--exact-record")exact_record=true;
            else if(a.rfind("--exact-record-limit=",0)==0)exact_record_limit=std::stoi(a.substr(21));
            else if(a.rfind("--exact-replay=",0)==0)exact_replay_path=a.substr(15);
            else if(a.rfind("--exact-replay-budget=",0)==0)exact_replay_budget=std::stoull(a.substr(22));
            else if(a.rfind("--quant-first=",0)==0)quant_first=std::stoi(a.substr(14));
            else if(a.rfind("--quant-replies=",0)==0)quant_replies=a.substr(16);
            else if(a.rfind("--quant-budget=",0)==0)quant_budget=std::stoull(a.substr(15));
            else if(a.rfind("--quant-timeout=",0)==0)quant_timeout=std::stod(a.substr(16));
            else if(a=="--exact-order=count")exact_order=0;
            else if(a=="--exact-order=countd")exact_order=1;
            else if(a=="--exact-order=key")exact_order=2;
            else if(a.rfind("--exact-budget-by-stones=",0)==0){
                // Format: 5:5000000,6:500000,7:200000
                exact_budget_by_stones_spec=a.substr(25);
            }
            else if(a.rfind("--exact-legal-by-stones=",0)==0){
                // Format: 5:80,6:72,7:114. A value of 0 disables the
                // handoff for that stone count.
                exact_legal_by_stones_spec=a.substr(24);
            }
            else{
                std::cerr<<"usage: "<<argv[0]<<" [--n=N] [--empty] [--reps] [--memo=P] [--only=v,..] [--budget=S] [--log=P] [--csv=P] [--roots-csv=P] [--children] [--tiebreak=asc|desc] [--exact-legal=N] [--exact-budget=N] [--exact-retries=N] [--exact-publish=all|root|separate] [--exact-record] [--exact-record-limit=N] [--exact-replay=P] [--exact-replay-budget=N] [--exact-order=count|countd|key] [--exact-budget-by-stones=5:N,6:N] [--exact-legal-by-stones=5:N,6:N]\n";
                return 2;
            }
        }
        if(!reps && !empty && roots_path.empty() && exact_replay_path.empty()
           && quant_replies.empty()){
            std::cerr<<"nothing to do without --empty/--reps/--roots-csv/--exact-replay/--quant-replies\n";
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
        // Parse --exact-budget-by-stones into a vector of (stones,budget).
        // Format: 5:5000000,6:500000,7:200000
        std::vector<std::pair<int,std::uint64_t>> budget_by_stones;
        if(!exact_budget_by_stones_spec.empty()){
            std::stringstream bs(exact_budget_by_stones_spec); std::string part;
            while(std::getline(bs,part,',')){
                if(part.empty()) continue;
                std::size_t c=part.find(':');
                if(c==std::string::npos){
                    std::cerr<<"bad --exact-budget-by-stones entry: "<<part<<"\n";
                    return 2;
                }
                int st=std::stoi(part.substr(0,c));
                std::uint64_t bv=std::stoull(part.substr(c+1));
                budget_by_stones.push_back({st,bv});
            }
        }
        // Parse --exact-legal-by-stones the same way. Format: 5:80,6:72,7:114
        std::vector<std::pair<int,int>> legal_by_stones;
        if(!exact_legal_by_stones_spec.empty()){
            std::stringstream ls(exact_legal_by_stones_spec); std::string part;
            while(std::getline(ls,part,',')){
                if(part.empty()) continue;
                std::size_t c=part.find(':');
                if(c==std::string::npos){
                    std::cerr<<"bad --exact-legal-by-stones entry: "<<part<<"\n";
                    return 2;
                }
                int st=std::stoi(part.substr(0,c));
                int lv=std::stoi(part.substr(c+1));
                legal_by_stones.push_back({st,lv});
            }
        }
        std::uint64_t total_exp=0;
        int rc=0;
        switch(n){
            case 4:
                if(!exact_replay_path.empty()) return run_exact_replay<4>(exact_replay_path,exact_replay_budget,pow,only,exact_order,*cp);
                if(!quant_replies.empty()) return run_quant<4>(quant_first,quant_replies,quant_budget,quant_timeout,pow,*cp);
                rc=run<4>(only,budget_s,pow,empty,reps,children,tiebreak_desc,exact_legal,exact_budget,exact_retries,exact_publish_mode,exact_record,exact_record_limit,budget_by_stones,legal_by_stones,exact_order,*lp,*cp,&total_exp,roots_path); break;
            case 5:
                if(!exact_replay_path.empty()) return run_exact_replay<5>(exact_replay_path,exact_replay_budget,pow,only,exact_order,*cp);
                if(!quant_replies.empty()) return run_quant<5>(quant_first,quant_replies,quant_budget,quant_timeout,pow,*cp);
                rc=run<5>(only,budget_s,pow,empty,reps,children,tiebreak_desc,exact_legal,exact_budget,exact_retries,exact_publish_mode,exact_record,exact_record_limit,budget_by_stones,legal_by_stones,exact_order,*lp,*cp,&total_exp,roots_path); break;
            case 6:
                if(!exact_replay_path.empty()) return run_exact_replay<6>(exact_replay_path,exact_replay_budget,pow,only,exact_order,*cp);
                if(!quant_replies.empty()) return run_quant<6>(quant_first,quant_replies,quant_budget,quant_timeout,pow,*cp);
                rc=run<6>(only,budget_s,pow,empty,reps,children,tiebreak_desc,exact_legal,exact_budget,exact_retries,exact_publish_mode,exact_record,exact_record_limit,budget_by_stones,legal_by_stones,exact_order,*lp,*cp,&total_exp,roots_path); break;
            case 7:
                if(!exact_replay_path.empty()) return run_exact_replay<7>(exact_replay_path,exact_replay_budget,pow,only,exact_order,*cp);
                if(!quant_replies.empty()) return run_quant<7>(quant_first,quant_replies,quant_budget,quant_timeout,pow,*cp);
                rc=run<7>(only,budget_s,pow,empty,reps,children,tiebreak_desc,exact_legal,exact_budget,exact_retries,exact_publish_mode,exact_record,exact_record_limit,budget_by_stones,legal_by_stones,exact_order,*lp,*cp,&total_exp,roots_path); break;
            case 11:
                if(!exact_replay_path.empty()) return run_exact_replay<11>(exact_replay_path,exact_replay_budget,pow,only,exact_order,*cp);
                if(!quant_replies.empty()) return run_quant<11>(quant_first,quant_replies,quant_budget,quant_timeout,pow,*cp);
                rc=run<11>(only,budget_s,pow,empty,reps,children,tiebreak_desc,exact_legal,exact_budget,exact_retries,exact_publish_mode,exact_record,exact_record_limit,budget_by_stones,legal_by_stones,exact_order,*lp,*cp,&total_exp,roots_path); break;
            default: std::cerr<<"unsupported n\n"; return 2;
        }
        return rc;
    }catch(const std::exception&e){
        std::cerr<<"error: "<<e.what()<<"\n";return 1;
    }
}
