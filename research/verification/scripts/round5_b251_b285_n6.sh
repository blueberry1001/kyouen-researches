#!/bin/bash
set -e
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
BIN=/tmp/r5b285
cat > /tmp/r5b285.cpp << 'CPP'
#include <cstdint>
#include <cstdio>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
using u64 = uint64_t;
static long long det4(const long long r[4][4]) {
    long long total = 0;
    for (int i = 0; i < 4; ++i) {
        long long mm[3][3]; int ri = 0;
        for (int r2 = 0; r2 < 4; ++r2) {
            if (r2 == i) continue;
            int ci = 0;
            for (int c2 = 1; c2 < 4; ++c2) mm[ri][ci++] = r[r2][c2];
            ++ri;
        }
        long long d3 = mm[0][0]*(mm[1][1]*mm[2][2]-mm[1][2]*mm[2][1])
                     - mm[0][1]*(mm[1][0]*mm[2][2]-mm[1][2]*mm[2][0])
                     + mm[0][2]*(mm[1][0]*mm[2][1]-mm[1][1]*mm[2][0]);
        total += (i%2==0?1:-1)*r[i][0]*d3;
    }
    return total;
}
struct Board {
    int n=0,V=0; u64 full=0;
    std::vector<std::vector<u64>> tri;
    std::vector<u64> quads;
};
static void build(Board& b, int n) {
    b.n=n; b.V=n*n; b.full=(1ULL<<b.V)-1;
    b.tri.assign(b.V,{}); b.quads.clear();
    std::vector<std::array<long long,4>> rows(b.V);
    for(int y=0;y<n;++y) for(int x=0;x<n;++x){
        int i=y*n+x;
        rows[i]={(long long)x*x+(long long)y*y,x,y,1};
    }
    for(int a=0;a<b.V-3;++a) for(int c=a+1;c<b.V-2;++c)
    for(int d=c+1;d<b.V-1;++d) for(int e=d+1;e<b.V;++e){
        int ids[4]={a,c,d,e};
        long long m[4][4];
        for(int i=0;i<4;++i) for(int j=0;j<4;++j) m[i][j]=rows[ids[i]][j];
        if(det4(m)!=0) continue;
        u64 q=0; for(int i=0;i<4;++i) q|=1ULL<<ids[i];
        b.quads.push_back(q);
        for(int t=0;t<4;++t){
            u64 o=0; for(int s=0;s<4;++s) if(s!=t) o|=1ULL<<ids[s];
            b.tri[ids[t]].push_back(o);
        }
    }
}
static inline u64 legal(const Board& b, u64 occ){
    u64 out=0, empty=b.full&~occ;
    while(empty){
        int p=__builtin_ctzll(empty); empty&=empty-1;
        bool ok=true;
        for(u64 t:b.tri[p]) if((occ&t)==t){ok=false;break;}
        if(ok) out|=1ULL<<p;
    }
    return out;
}
static std::map<u64,int> solve(const Board& b){
    std::vector<u64> order; std::set<u64> seen;
    std::vector<u64> st={0}; seen.insert(0);
    while(!st.empty()){
        u64 s=st.back(); st.pop_back(); order.push_back(s);
        u64 lm=legal(b,s);
        while(lm){ int p=__builtin_ctzll(lm); lm&=lm-1;
            u64 ns=s|(1ULL<<p);
            if(!seen.count(ns)){seen.insert(ns);st.push_back(ns);}
        }
    }
    std::sort(order.begin(),order.end(),[](u64 a,u64 b){
        return __builtin_popcountll(a)>__builtin_popcountll(b);
    });
    std::map<u64,int> g;
    for(u64 s:order){
        u64 lm=legal(b,s);
        if(!lm){g[s]=0;continue;}
        std::set<int> cg;
        u64 t=lm;
        while(t){int p=__builtin_ctzll(t);t&=t-1;cg.insert(g[s|(1ULL<<p)]);}
        int mex=0; while(cg.count(mex))++mex;
        g[s]=mex;
    }
    return g;
}
int main(){
    // B285: T4, Z4, L3, diag3 on n=4,5,6
    const char* names[]={"L3","diag3","T4","Z4"};
    int cfgs[4][4][2]={
        {{0,0},{1,0},{0,1},{-1,-1}},
        {{0,0},{1,1},{2,2},{-1,-1}},
        {{0,0},{1,0},{2,0},{1,1}},
        {{0,0},{1,0},{1,1},{2,1}},
    };
    printf("{\n");
    for(int n=4;n<=6;++n){
        Board b; build(b,n);
        auto g=solve(b);
        printf("\"n%d\":{\"nstates\":%zu,\"configs\":{",n,g.size());
        for(int ci=0;ci<4;++ci){
            u64 mask=0; bool ok=true;
            for(int k=0;k<4;++k){
                int x=cfgs[ci][k][0], y=cfgs[ci][k][1];
                if(x<0) break;
                if(x>=n||y>=n){ok=false;break;}
                mask|=1ULL<<(y*n+x);
            }
            if(!ok){printf("%s\"%s\":{\"skip\":\"range\"}",ci?",":"",names[ci]);continue;}
            // check safety
            bool safe=true;
            for(u64 q:b.quads) if((mask&q)==q){safe=false;break;}
            if(!safe){printf("%s\"%s\":{\"skip\":\"unsafe\"}",ci?",":"",names[ci]);continue;}
            int gv=g[mask];
            u64 L=legal(b,mask);
            printf("%s\"%s\":{\"g\":%d,\"nlegal\":%d}",ci?",":"",names[ci],gv,__builtin_popcountll(L));
        }
        printf("}}%s\n", n<6?",":"");
    }
    // T4 translations on n=6
    {
        Board b; build(b,6); auto g=solve(b);
        printf(",\"T4_trans_n6\":{");
        bool first=true;
        for(int y0=0;y0<4;++y0) for(int x0=0;x0<4;++x0){
            int pts[4][2]={{x0,y0},{x0+1,y0},{x0+2,y0},{x0+1,y0+1}};
            u64 mask=0;
            for(auto& p:pts) mask|=1ULL<<(p[1]*6+p[0]);
            bool safe=true;
            for(u64 q:b.quads) if((mask&q)==q){safe=false;break;}
            if(!safe) continue;
            printf("%s\"%d,%d\":%d",first?"":",",x0,y0,g[mask]);
            first=false;
        }
        printf("}\n");
    }
    printf("}\n");
    return 0;
}
CPP
echo "COMPILING..."
g++ -O2 -march=native -std=c++20 -o "$BIN" /tmp/r5b285.cpp
echo "RUN n=4..6"
"$BIN" > /tmp/r5b251/b285.json
cat /tmp/r5b251/b285.json
echo "DONE"
