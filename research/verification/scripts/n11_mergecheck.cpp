// Brute-force cross-check of the v-block merge on a tiny board.
// For every state S at level k it collects the children g by (a) the merge
// used in n11_grundy.cpp and (b) an O(V) scan with a linear search in level
// k+1, then compares the two multisets of child g values.
#include "kc_core121.h"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif
using kc::u64; using kc::Bits; using kc::Board;

static int top_point(const Bits& b) {
    if (b.hi) return 127 - __builtin_clzll(b.hi);
    return 63 - __builtin_clzll(b.lo);
}
struct Tri4 {
    std::vector<Bits> tab; std::vector<int> c1,c2,c3; int V=0;
    void build(const Board& B) {
        V=B.V; c1.resize((size_t)V); c2.resize((size_t)V); c3.resize((size_t)V);
        for (int p=0;p<V;++p){c1[(size_t)p]=p;c2[(size_t)p]=p*(p-1)/2;c3[(size_t)p]=p>2?p*(p-1)*(p-2)/6:0;}
        tab.assign((size_t)V*(V-1)*(V-2)/6, Bits{0,0});
        for (const Bits& q : B.quads) { int p[4],c=0; u64 e=q.lo;
            while(e){p[c++]=__builtin_ctzll(e);e&=e-1;} e=q.hi;
            while(e){p[c++]=64+__builtin_ctzll(e);e&=e-1;}
            for(int t=0;t<4;++t){int a,b,d;
                if(t==0){a=p[1];b=p[2];d=p[3];}else if(t==1){a=p[0];b=p[2];d=p[3];}
                else if(t==2){a=p[0];b=p[1];d=p[3];}else{a=p[0];b=p[1];d=p[2];}
                size_t r=(size_t)(c1[(size_t)a]+c2[(size_t)b]+c3[(size_t)d]);
                tab[r].set(p[t]); } }
    }
};
static void free_mask_level(const Board& B,const Tri4& T,const std::vector<Bits>& A,std::vector<Bits>& out){
    out.resize(A.size()); const Bits* tab=T.tab.data(); const int*c1=T.c1.data();const int*c2=T.c2.data();const int*c3=T.c3.data();
#pragma omp parallel for schedule(static)
    for(long long i=0;i<(long long)A.size();++i){ const Bits&S=A[(size_t)i]; int pt[128],k=0;
        u64 e=S.lo; while(e){pt[k++]=__builtin_ctzll(e);e&=e-1;} e=S.hi; while(e){pt[k++]=64+__builtin_ctzll(e);e&=e-1;}
        Bits blk{0,0};
        for(int a=0;a<k;++a){const int ca=c1[pt[a]];
            for(int b=a+1;b<k;++b){const Bits* row=tab+c2[pt[b]]+ca;
                for(int d=b+1;d<k;++d){blk.lo|=row[c3[pt[d]]].lo;blk.hi|=row[c3[pt[d]]].hi;}}}
        Bits f; f.lo=B.full_lo&~S.lo&~blk.lo; f.hi=B.hi_marks&~S.hi&~blk.hi; out[(size_t)i]=f; }
}
static void build_next(const Board& B,const std::vector<Bits>& cur,const std::vector<Bits>& fm,std::vector<Bits>& nxt){
    const int V=B.V; std::vector<int> plen((size_t)V);
#pragma omp parallel for schedule(static)
    for(int v=0;v<V;++v){Bits bit;bit.set(v);plen[(size_t)v]=(int)(std::lower_bound(cur.begin(),cur.end(),bit)-cur.begin());}
    std::vector<u64> off((size_t)V+1,0);
    for(int v=0;v<V;++v){u64 c=0;for(int i=0;i<plen[(size_t)v];++i)if(fm[(size_t)i].test(v))c++;off[(size_t)v+1]=off[(size_t)v]+c;}
    nxt.resize((size_t)off[(size_t)V]);
#pragma omp parallel for schedule(static)
    for(int v=0;v<V;++v){Bits bit;bit.set(v);u64 p=off[(size_t)v];
        for(int i=0;i<plen[(size_t)v];++i)if(fm[(size_t)i].test(v)){
            nxt[(size_t)p].lo=cur[(size_t)i].lo|bit.lo;nxt[(size_t)p].hi=cur[(size_t)i].hi|bit.hi;p++;}}
}

int main(int argc,char**argv){
    int n=atoi(argv[1]);
    Board B; kc::build_square(B,n); Tri4 T4; T4.build(B);
    std::vector<std::vector<Bits>> L; L.push_back(std::vector<Bits>(1,Bits{0,0}));
    std::vector<Bits> fm;
    for(int k=0;k<64;++k){ free_mask_level(B,T4,L[(size_t)k],fm);
        L.push_back(std::vector<Bits>()); build_next(B,L[(size_t)k],fm,L.back());
        if(L.back().empty()){L.pop_back();break;} }
    int K=(int)L.size()-1;
    printf("n=%d K=%d\n",n,K);
    std::vector<uint8_t> g;
    g.assign(L[(size_t)K].size(),0);
    u64 totbad=0;
    for(int k=K-1;k>=0;--k){
        const std::vector<Bits>&Lk=L[(size_t)k]; const std::vector<Bits>&Lk1=L[(size_t)k+1];
        size_t Mk=Lk.size(),Mk1=Lk1.size();
        free_mask_level(B,T4,Lk,fm);
        std::vector<int> blo((size_t)B.V,-1),bhi((size_t)B.V,0),plen((size_t)B.V,0);
        for(size_t i=0;i<Mk1;++i){int t=top_point(Lk1[i]); if(blo[(size_t)t]<0)blo[(size_t)t]=(int)i; bhi[(size_t)t]=(int)i+1;}
        for(int v=0;v<B.V;++v){Bits bit;bit.set(v);plen[(size_t)v]=(int)(std::lower_bound(Lk.begin(),Lk.end(),bit)-Lk.begin());}
        // reference g for level k+1 is g itself (child level)
        u64 bad=0, refbad=0;
        // (a) v-block cursor, exactly as n11_grundy.cpp: for each v walk the
        //     prefix [0,plen[v]) and take legal states in order, consuming block
        //     v from a single cursor.
        std::vector<std::vector<uint8_t>> merged((size_t)Mk);
#pragma omp parallel for schedule(dynamic,1)
        for(int v=0;v<B.V;++v){
            if(blo[(size_t)v]<0) continue;
            size_t p=(size_t)blo[(size_t)v];
            for(int i=0;i<plen[(size_t)v];++i){
                if(!fm[(size_t)i].test(v)) continue;
                merged[(size_t)i].push_back(g[p]);
                p++;
            }
        }
        // (b) reference: EVERY legal move of EVERY state, located by search
        std::vector<std::vector<uint8_t>> ref((size_t)Mk);
#pragma omp parallel for schedule(static)
        for(long long i=0;i<(long long)Mk;++i){
            Bits S=Lk[(size_t)i];
            for(int u=0;u<B.V;++u){ if(S.test(u)) continue; if(!fm[(size_t)i].test(u)) continue;
                Bits c; c.set(u); c.lo|=S.lo; c.hi|=S.hi; size_t lo=0,hi=Mk1;
                while(lo<hi){size_t mid=(lo+hi)/2; if(Lk1[mid]<c)lo=mid+1;else hi=mid;}
                if(lo<Mk1&&Lk1[lo]==c) ref[(size_t)i].push_back(g[lo]); }
        }
#pragma omp parallel for schedule(static) reduction(+ : bad, refbad)
        for(long long i=0;i<(long long)Mk;++i){
            std::vector<uint8_t> ca = merged[(size_t)i];
            std::vector<uint8_t> cb = ref[(size_t)i];
            std::sort(ca.begin(),ca.end()); std::sort(cb.begin(),cb.end());
            if(ca!=cb) bad++;
        }
        if(getenv("MC_DIAG") && bad){
            // print the first mismatching state
            for(size_t i=0;i<Mk;++i){
                std::vector<uint8_t> ca2,cb2; Bits S=Lk[i];
                for(int v=0;v<B.V;++v){ if(blo[(size_t)v]<0) continue; size_t p=(size_t)blo[(size_t)v];
                    for(int j=0;j<plen[(size_t)v];++j){ if(!fm[(size_t)j].test(v)) continue; if(j==(int)i) ca2.push_back(g[p]); p++; } }
                for(int u=0;u<B.V;++u){ if(S.test(u))continue; if(!fm[i].test(u))continue;
                    Bits c;c.set(u);c.lo|=S.lo;c.hi|=S.hi; size_t lo=0,hi=Mk1;
                    while(lo<hi){size_t mid=(lo+hi)/2; if(Lk1[mid]<c)lo=mid+1;else hi=mid;}
                    if(lo<Mk1&&Lk1[lo]==c) cb2.push_back(g[lo]); }
                std::sort(ca2.begin(),ca2.end()); std::sort(cb2.begin(),cb2.end());
                if(ca2!=cb2){
                    printf("  DIAG k=%d i=%zu occ=",k,i); Bits z=S;
                    while(z.lo){int p=__builtin_ctzll(z.lo);z.lo&=z.lo-1;printf("%d,",p);}
                    while(z.hi){int p=64+__builtin_ctzll(z.hi);z.hi&=z.hi-1;printf("%d,",p);}
                    printf("  merge_g=[");
                    for(auto x:ca2)printf("%d,",x); printf("]  ref_g=[");
                    for(auto x:cb2)printf("%d,",x); printf("]\n");
                    // dump block boundaries and plen
                    printf("    V=%d Mk=%zu Mk1=%zu\n",B.V,Mk,Mk1);
                    for(int v=0;v<B.V;++v) if(blo[(size_t)v]>=0) printf("    v=%d blo=%d bhi=%d plen=%d\n",v,blo[(size_t)v],bhi[(size_t)v],plen[(size_t)v]);
                    break;
                }
            }
        }
        std::vector<uint8_t> gn(Mk,0);
#pragma omp parallel for schedule(static)
        for(long long i=0;i<(long long)Mk;++i){
            unsigned acc=0; Bits S=Lk[(size_t)i];
            for(int u=0;u<B.V;++u){ if(S.test(u))continue; if(!fm[(size_t)i].test(u))continue;
                Bits c;c.set(u);c.lo|=S.lo;c.hi|=S.hi;
                size_t lo=0,hi=Mk1; while(lo<hi){size_t mid=(lo+hi)/2; if(Lk1[mid]<c)lo=mid+1;else hi=mid;}
                if(lo<Mk1&&Lk1[lo]==c) acc|=1u<<g[(size_t)lo]; }
            unsigned z=~acc; int m=z?__builtin_ctz(z):0; if(m>30)m=0; gn[(size_t)i]=(uint8_t)m; }
        totbad+=bad;
        printf("  k=%2d M=%-8zu merge_vs_ref_mismatch=%llu  ref_lookup_failures=%llu\n",k,Mk,(unsigned long long)bad,(unsigned long long)refbad);
        if(refbad){printf("FATAL reference lookup failed\n");return 9;}
        g.swap(gn);
    }
    printf("  g(empty)=%d  total_merge_mismatch=%llu\n",(int)g[0],(unsigned long long)totbad);
    return 0;
}
