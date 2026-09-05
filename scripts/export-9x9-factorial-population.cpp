#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

struct Mask81 { std::uint64_t lo=0, hi=0; };
static inline Mask81 operator|(Mask81 a, Mask81 b){ return {a.lo|b.lo,a.hi|b.hi}; }
static inline Mask81 operator&(Mask81 a, Mask81 b){ return {a.lo&b.lo,a.hi&b.hi}; }
static inline Mask81 operator~(Mask81 a){ return {~a.lo,~a.hi}; }
static inline void setbit(Mask81& m,int p){ if(p<64)m.lo|=1ULL<<p;else m.hi|=1ULL<<(p-64); }
static inline bool has(Mask81 m,int p){ return p<64?((m.lo>>p)&1ULL):((m.hi>>(p-64))&1ULL); }
static inline int popcount(Mask81 m){ return __builtin_popcountll(m.lo)+__builtin_popcountll(m.hi); }
static inline std::size_t tidx(int a,int b,int c){ if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);return (std::size_t(a)*81+b)*81+c; }
static inline std::uint32_t key4(int a,int b,int c,int d){ return (((a*81u+b)*81u+c)*81u+d); }

static long long det3(long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h,long long i){
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
}
static bool forbidden4(int a,int b,int c,int d){
    int p[4]={a,b,c,d}; long long x[4],y[4],z[4];
    for(int k=0;k<4;++k){ x[k]=p[k]%9; y[k]=p[k]/9; z[k]=x[k]*x[k]+y[k]*y[k]; }
    return det3(x[1]-x[0],y[1]-y[0],z[1]-z[0],x[2]-x[0],y[2]-y[0],z[2]-z[0],x[3]-x[0],y[3]-y[0],z[3]-z[0])==0;
}

static int transform_point(int v,int g){
    int x=v%9,y=v/9,nx=0,ny=0;
    switch(g){
        case 0:nx=x;ny=y;break; case 1:nx=8-y;ny=x;break;
        case 2:nx=8-x;ny=8-y;break; case 3:nx=y;ny=8-x;break;
        case 4:nx=8-x;ny=y;break; case 5:nx=x;ny=8-y;break;
        case 6:nx=y;ny=x;break; default:nx=8-y;ny=8-x;break;
    }
    return ny*9+nx;
}
struct Canonical4 { std::uint32_t key; std::array<int,4> parent; int transform; };
static Canonical4 canonical4(const std::array<int,4>& p){
    Canonical4 best{UINT32_MAX,{},0};
    for(int g=0;g<8;++g){
        std::array<int,4> q; for(int i=0;i<4;++i)q[i]=transform_point(p[i],g);
        std::sort(q.begin(),q.end()); auto k=key4(q[0],q[1],q[2],q[3]);
        if(k<best.key)best={k,q,g};
    }
    return best;
}

struct Row { std::array<int,4> parent; std::array<int,4> top; };
static std::string parent_text(const std::array<int,4>& p){
    return std::to_string(p[0])+","+std::to_string(p[1])+","+std::to_string(p[2])+","+std::to_string(p[3]);
}

int main(int argc,char** argv){
    if(argc!=3 || std::string(argv[1])!="--csv"){
        std::cerr<<"usage: "<<argv[0]<<" --csv OUTPUT.csv\n"; return 2;
    }
    const std::string out_path=argv[2];
    std::vector<Mask81> completion(81*81*81);
    std::unordered_set<std::uint32_t> forbidden; forbidden.reserve(40000);
    long long forbidden_count=0;
    for(int a=0;a<81;++a)for(int b=a+1;b<81;++b)for(int c=b+1;c<81;++c)for(int d=c+1;d<81;++d){
        if(!forbidden4(a,b,c,d))continue; ++forbidden_count; forbidden.insert(key4(a,b,c,d));
        int q[4]={a,b,c,d};
        for(int omit=0;omit<4;++omit){ int t[3],n=0; for(int j=0;j<4;++j)if(j!=omit)t[n++]=q[j]; setbit(completion[tidx(t[0],t[1],t[2])],q[omit]); }
    }

    long long parents=0, all4_unique=0, any_diff=0;
    long long raw_E0=0,raw_O0=0,raw_E1=0,raw_O1=0,raw_Traw=0;
    std::unordered_map<std::uint32_t,Row> rows; rows.reserve(6000);
    std::unordered_set<std::uint32_t> orb_E0,orb_O0,orb_E1,orb_O1,orb_Traw;
    orb_E0.reserve(5000);orb_O0.reserve(1000);orb_E1.reserve(5000);orb_O1.reserve(1000);orb_Traw.reserve(6000);

    for(int a=0;a<81;++a)for(int b=a+1;b<81;++b)for(int c=b+1;c<81;++c)for(int d=c+1;d<81;++d){
        if(forbidden.count(key4(a,b,c,d)))continue; ++parents;
        int p[4]={a,b,c,d}; Mask81 occupied{}; for(int z:p)setbit(occupied,z);
        Mask81 existing=completion[tidx(a,b,c)]|completion[tidx(a,b,d)]|completion[tidx(a,c,d)]|completion[tidx(b,c,d)];
        int best[4]={-1,-1,-1,-1},count[4]={0,0,0,0},move[4]={-1,-1,-1,-1};
        for(int v=0;v<81;++v){
            if(has(occupied,v)||has(existing,v))continue;
            int raw=0; Mask81 uni{};
            for(int i=0;i<4;++i)for(int j=i+1;j<4;++j){ auto m=completion[tidx(p[i],p[j],v)]; raw+=popcount(m); uni=uni|m; }
            int U=popcount(uni), T=popcount(uni&~existing), E=U-T, O=raw-U;
            int score[4]={T,T+E,T+O,raw}; // S00,S10,S01,S11
            for(int k=0;k<4;++k){ if(score[k]>best[k]){best[k]=score[k];count[k]=1;move[k]=v;}else if(score[k]==best[k])++count[k]; }
        }
        if(!(count[0]==1&&count[1]==1&&count[2]==1&&count[3]==1))continue;
        ++all4_unique;
        bool diff=!(move[0]==move[1]&&move[0]==move[2]&&move[0]==move[3]);
        if(!diff)continue; ++any_diff;
        auto ck=canonical4({a,b,c,d});
        std::array<int,4> cmove{}; for(int k=0;k<4;++k)cmove[k]=transform_point(move[k],ck.transform);
        rows.emplace(ck.key,Row{ck.parent,cmove});
        if(move[0]!=move[1]){++raw_E0;orb_E0.insert(ck.key);} // S00 vs S10
        if(move[0]!=move[2]){++raw_O0;orb_O0.insert(ck.key);} // S00 vs S01
        if(move[2]!=move[3]){++raw_E1;orb_E1.insert(ck.key);} // S01 vs S11
        if(move[1]!=move[3]){++raw_O1;orb_O1.insert(ck.key);} // S10 vs S11
        if(move[0]!=move[3]){++raw_Traw;orb_Traw.insert(ck.key);}
    }

    std::vector<std::pair<std::uint32_t,Row>> ordered(rows.begin(),rows.end());
    std::sort(ordered.begin(),ordered.end(),[](const auto& x,const auto& y){return x.first<y.first;});
    std::ofstream f(out_path); if(!f){std::cerr<<"cannot open "<<out_path<<"\n";return 3;}
    f<<"canonical_parent,top_T,top_TE,top_TO,top_raw,diff_E_at_O0,diff_O_at_E0,diff_E_at_O1,diff_O_at_E1\n";
    for(const auto& [key,row]:ordered){(void)key;
        f<<'"'<<parent_text(row.parent)<<"\","<<row.top[0]<<','<<row.top[1]<<','<<row.top[2]<<','<<row.top[3]<<','
         <<(row.top[0]!=row.top[1])<<','<<(row.top[0]!=row.top[2])<<','<<(row.top[2]!=row.top[3])<<','<<(row.top[1]!=row.top[3])<<'\n';
    }
    std::cout<<"forbidden="<<forbidden_count<<"\n"
             <<"safe_4stone_parents="<<parents<<"\n"
             <<"all4_unique_raw="<<all4_unique<<"\n"
             <<"any_score_diff_raw="<<any_diff<<" D4_orbits="<<rows.size()<<"\n"
             <<"E_effect_O0_raw="<<raw_E0<<" D4_orbits="<<orb_E0.size()<<"\n"
             <<"O_effect_E0_raw="<<raw_O0<<" D4_orbits="<<orb_O0.size()<<"\n"
             <<"E_effect_O1_raw="<<raw_E1<<" D4_orbits="<<orb_E1.size()<<"\n"
             <<"O_effect_E1_raw="<<raw_O1<<" D4_orbits="<<orb_O1.size()<<"\n"
             <<"T_vs_raw_raw="<<raw_Traw<<" D4_orbits="<<orb_Traw.size()<<"\n"
             <<"wrote="<<ordered.size()<<" to "<<out_path<<"\n";
}
