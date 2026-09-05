#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <unordered_map>
#include <unordered_set>
#include <vector>

struct Mask81 { std::uint64_t lo = 0, hi = 0; };
static inline Mask81 operator|(Mask81 a, Mask81 b) { return {a.lo | b.lo, a.hi | b.hi}; }
static inline Mask81 operator&(Mask81 a, Mask81 b) { return {a.lo & b.lo, a.hi & b.hi}; }
static inline Mask81 operator~(Mask81 a) { return {~a.lo, ~a.hi}; }
static inline void add_bit(Mask81& m, int i) {
    if (i < 64) m.lo |= 1ULL << i;
    else m.hi |= 1ULL << (i - 64);
}
static inline bool has_bit(Mask81 m, int i) {
    return i < 64 ? ((m.lo >> i) & 1ULL) : ((m.hi >> (i - 64)) & 1ULL);
}
static inline int popcount(Mask81 m) {
    return __builtin_popcountll(m.lo) + __builtin_popcountll(m.hi);
}

static inline std::size_t triple_index(int a, int b, int c) {
    if (a > b) std::swap(a, b);
    if (b > c) std::swap(b, c);
    if (a > b) std::swap(a, b);
    return (std::size_t(a) * 81 + b) * 81 + c;
}
static inline std::uint32_t key4(int a, int b, int c, int d) {
    return (((a * 81u + b) * 81u + c) * 81u + d);
}
static long long det3(long long a,long long b,long long c,
                      long long d,long long e,long long f,
                      long long g,long long h,long long i) {
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
}
static bool forbidden4(int a, int b, int c, int d) {
    int p[4] = {a,b,c,d};
    long long x[4], y[4], z[4];
    for (int k=0;k<4;++k) {
        x[k]=p[k]%9; y[k]=p[k]/9; z[k]=x[k]*x[k]+y[k]*y[k];
    }
    return det3(x[1]-x[0],y[1]-y[0],z[1]-z[0],
                x[2]-x[0],y[2]-y[0],z[2]-z[0],
                x[3]-x[0],y[3]-y[0],z[3]-z[0]) == 0;
}

static int transform_point(int v, int g) {
    int x=v%9, y=v/9, nx=0, ny=0;
    switch(g) {
        case 0: nx=x; ny=y; break;
        case 1: nx=8-y; ny=x; break;
        case 2: nx=8-x; ny=8-y; break;
        case 3: nx=y; ny=8-x; break;
        case 4: nx=8-x; ny=y; break;
        case 5: nx=x; ny=8-y; break;
        case 6: nx=y; ny=x; break;
        default:nx=8-y; ny=8-x; break;
    }
    return ny*9+nx;
}
struct Canonical4 { std::uint32_t key; std::array<int,4> parent; int transform; };
static Canonical4 canonical4(std::array<int,4> p) {
    Canonical4 best{UINT32_MAX,{},0};
    for (int g=0;g<8;++g) {
        std::array<int,4> q;
        for (int i=0;i<4;++i) q[i]=transform_point(p[i],g);
        std::sort(q.begin(),q.end());
        auto k=key4(q[0],q[1],q[2],q[3]);
        if (k<best.key) best={k,q,g};
    }
    return best;
}

struct Features { int T=0, E=0, O=0, raw=0; };
struct CanonicalRow {
    std::array<int,4> parent;
    int pair_top=-1, true_top=-1;
    int cause_class=0;
};

int main() {
    std::vector<Mask81> completion(81*81*81);
    std::unordered_set<std::uint32_t> forbidden;
    forbidden.reserve(40000);
    long long forbidden_count=0;

    for (int a=0;a<81;++a)
    for (int b=a+1;b<81;++b)
    for (int c=b+1;c<81;++c)
    for (int d=c+1;d<81;++d) {
        if (!forbidden4(a,b,c,d)) continue;
        ++forbidden_count;
        forbidden.insert(key4(a,b,c,d));
        int q[4]={a,b,c,d};
        for (int omit=0;omit<4;++omit) {
            int t[3], n=0;
            for (int j=0;j<4;++j) if (j!=omit) t[n++]=q[j];
            add_bit(completion[triple_index(t[0],t[1],t[2])],q[omit]);
        }
    }

    long long parents=0, candidates=0;
    long long overlap_positive=0, existing_positive=0, both_positive=0;
    int max_O=0, max_E=0, max_gap=0;
    long long strict=0, e_sufficient=0, o_sufficient=0, both_sufficient=0, synergy_only=0;
    long long pair_e_advantage=0, pair_o_advantage=0;
    std::array<long long,4> o_hist{};
    std::array<long long,10> e_hist{}, gap_hist{};
    std::unordered_map<std::uint32_t,CanonicalRow> canonical;

    for (int a=0;a<81;++a)
    for (int b=a+1;b<81;++b)
    for (int c=b+1;c<81;++c)
    for (int d=c+1;d<81;++d) {
        if (forbidden.count(key4(a,b,c,d))) continue;
        ++parents;
        int p[4]={a,b,c,d};
        Mask81 occupied{};
        for (int x:p) add_bit(occupied,x);
        Mask81 existing = completion[triple_index(a,b,c)] |
                          completion[triple_index(a,b,d)] |
                          completion[triple_index(a,c,d)] |
                          completion[triple_index(b,c,d)];

        int best_raw=-1, best_true=-1, n_raw=0, n_true=0, raw_move=-1, true_move=-1;
        Features features[81]{};

        for (int v=0;v<81;++v) {
            if (has_bit(occupied,v) || has_bit(existing,v)) continue;
            ++candidates;
            int raw=0;
            Mask81 uni{};
            for (int i=0;i<4;++i) for (int j=i+1;j<4;++j) {
                auto m=completion[triple_index(p[i],p[j],v)];
                raw += popcount(m);
                uni = uni | m;
            }
            int U=popcount(uni);
            int T=popcount(uni & ~existing);
            int E=U-T;
            int O=raw-U;
            features[v]={T,E,O,raw};

            overlap_positive += O>0;
            existing_positive += E>0;
            both_positive += O>0 && E>0;
            max_O=std::max(max_O,O);
            max_E=std::max(max_E,E);
            max_gap=std::max(max_gap,E+O);
            if (O<4) ++o_hist[O];
            if (E<10) ++e_hist[E];
            if (E+O<10) ++gap_hist[E+O];

            if (raw>best_raw) { best_raw=raw; n_raw=1; raw_move=v; }
            else if (raw==best_raw) ++n_raw;
            if (T>best_true) { best_true=T; n_true=1; true_move=v; }
            else if (T==best_true) ++n_true;
        }

        if (n_raw==1 && n_true==1 && raw_move!=true_move) {
            ++strict;
            auto P=features[raw_move], Q=features[true_move];
            int dT=Q.T-P.T, dE=P.E-Q.E, dO=P.O-Q.O;
            bool e_ok=P.T+P.E > Q.T+Q.E;
            bool o_ok=P.T+P.O > Q.T+Q.O;
            e_sufficient += e_ok;
            o_sufficient += o_ok;
            both_sufficient += e_ok && o_ok;
            synergy_only += !e_ok && !o_ok;
            pair_e_advantage += dE>0;
            pair_o_advantage += dO>0;
            if (!(dT>=1 && dE+dO>=dT+1)) {
                std::cerr << "strict-reversal invariant failed\n";
                return 3;
            }

            int cause=e_ok ? (o_ok ? 3 : 1) : (o_ok ? 2 : 4);
            auto ck=canonical4({a,b,c,d});
            canonical.emplace(ck.key,CanonicalRow{
                ck.parent,
                transform_point(raw_move,ck.transform),
                transform_point(true_move,ck.transform),
                cause
            });
        }
    }

    auto pct=[](long long x,long long n){ return 100.0*double(x)/double(n); };
    std::cout << "forbidden=" << forbidden_count << '\n';
    std::cout << "safe_4stone_parents=" << parents << '\n';
    std::cout << "safe_parent_candidate_pairs=" << candidates << '\n';
    std::cout << "O>0=" << overlap_positive << " (" << pct(overlap_positive,candidates) << "%)\n";
    std::cout << "E>0=" << existing_positive << " (" << pct(existing_positive,candidates) << "%)\n";
    std::cout << "E>0 and O>0=" << both_positive << " (" << pct(both_positive,candidates) << "%)\n";
    std::cout << "max_O=" << max_O << " max_E=" << max_E << " max_E_plus_O=" << max_gap << '\n';
    std::cout << "strict_raw_vs_true_unique=" << strict << '\n';
    std::cout << "E_sufficient=" << e_sufficient << " (" << pct(e_sufficient,strict) << "%)\n";
    std::cout << "O_sufficient=" << o_sufficient << " (" << pct(o_sufficient,strict) << "%)\n";
    std::cout << "both_individually_sufficient=" << both_sufficient << " (" << pct(both_sufficient,strict) << "%)\n";
    std::cout << "synergy_only=" << synergy_only << " (" << pct(synergy_only,strict) << "%)\n";
    std::cout << "pair_winner_E_advantage=" << pair_e_advantage << " (" << pct(pair_e_advantage,strict) << "%)\n";
    std::cout << "pair_winner_O_advantage=" << pair_o_advantage << " (" << pct(pair_o_advantage,strict) << "%)\n";

    long long classes[5]{};
    for (const auto& kv:canonical) ++classes[kv.second.cause_class];
    std::cout << "D4_strict_orbits=" << canonical.size()
              << " E_only=" << classes[1]
              << " O_only=" << classes[2]
              << " both=" << classes[3]
              << " synergy=" << classes[4] << '\n';

    std::cout << "O_hist";
    for (int i=0;i<4;++i) std::cout << ' ' << i << ':' << o_hist[i];
    std::cout << '\n' << "E_hist";
    for (int i=0;i<10;++i) std::cout << ' ' << i << ':' << e_hist[i];
    std::cout << '\n' << "gap_hist";
    for (int i=0;i<10;++i) std::cout << ' ' << i << ':' << gap_hist[i];
    std::cout << '\n';
}
