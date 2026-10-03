#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>

// q=5, three consecutive integer rows. Each row has at most four stones.
// No floating-point decisions: sqrt is corrected and checked exactly.
using Mask = std::uint64_t;
struct Pair { int s, p; };
struct Four {
    std::array<int,4> x;
    std::array<Pair,6> pairs;
};

static Mask roots(int s, int p, int m, bool require_two = false) {
    int d=s*s-4*p;
    if (d<0) return 0;
    int r=(int)std::sqrt((double)d);
    while ((r+1)*(r+1)<=d) ++r;
    while (r*r>d) --r;
    if (r*r!=d || ((s-r)&1)) return 0;
    int a=(s-r)/2, b=(s+r)/2;
    if (require_two && !(0<=a && a<b && b<m)) return 0;
    Mask z=0;
    // A singleton target intersection may be tangent or have its mate outside.
    if (0<=a && a<m) z |= Mask(1)<<a;
    if (0<=b && b<m) z |= Mask(1)<<b;
    return z;
}

// kind 0: pair on y=1, singleton on y=2, target y=0.
// kind 1: pair on y=2, singleton on y=1, target y=0.
// kind 2: pair on y=0, singleton on y=2, target y=1.
static Mask triple_roots(Pair a, int b, int kind, int m, bool two=false) {
    int pb=b*(a.s-b), pt;
    if (kind==0) pt=2+2*a.p-pb;
    else if (kind==1) pt=2+2*pb-a.p;
    else {
        int n=a.p+pb-2;
        if (n&1) return 0;
        pt=n/2;
    }
    return roots(a.s,pt,m,two);
}

static std::vector<Four> fours(int m) {
    std::vector<Four> v;
    for(int a=0;a<m;++a) for(int b=a+1;b<m;++b)
    for(int c=b+1;c<m;++c) for(int d=c+1;d<m;++d) {
        Four f; f.x={a,b,c,d}; int n=0;
        for(int i=0;i<4;++i) for(int j=i+1;j<4;++j)
            f.pairs[n++]={f.x[i]+f.x[j],f.x[i]*f.x[j]};
        v.push_back(f);
    }
    return v;
}

struct Graph { Mask z=0; std::array<Mask,64> adj{}; };
static void edge(Graph& g, Mask x) {
    if (!x) return;
    assert(__builtin_popcountll(x)==2);
    int a=__builtin_ctzll(x); x &= x-1;
    int b=__builtin_ctzll(x);
    g.adj[a] |= Mask(1)<<b;
    g.adj[b] |= Mask(1)<<a;
}
template<class Row>
static Graph graph(const Row& b, const Row& c, int m, bool middle) {
    Graph g;
    for(auto p:b.pairs) for(auto q:c.pairs) if(p.s==q.s) {
        int pt;
        if(middle) { int n=p.p+q.p-2; if(n&1) continue; pt=n/2; }
        else pt=2+2*p.p-q.p;
        g.z |= roots(p.s,pt,m);
    }
    for(auto p:b.pairs) for(int x:c.x)
        edge(g,triple_roots(p,x,middle?2:0,m,true));
    for(auto p:c.pairs) for(int x:b.x)
        edge(g,triple_roots(p,x,middle?2:1,m,true));
    return g;
}

static std::array<int,3> cover(const Graph& g, int m) {
    Mask need=((Mask(1)<<m)-1)&~g.z;
    std::array<Mask,64> n{};
    int top[3]={0,0,0};
    for(int a=0;a<m;++a) {
        n[a]=(g.adj[a]|(Mask(1)<<a))&need;
        int k=__builtin_popcountll(n[a]);
        if(k>top[0]) {top[2]=top[1];top[1]=top[0];top[0]=k;}
        else if(k>top[1]) {top[2]=top[1];top[1]=k;}
        else if(k>top[2]) top[2]=k;
    }
    if(top[0]+top[1]+top[2]<__builtin_popcountll(need)) return {-1,-1,-1};
    for(int a=0;a<m;++a) for(int b=a+1;b<m;++b) {
        Mask rem=need&~(n[a]|n[b]);
        for(int c=b+1;c<m;++c) if(!(rem&~n[c])) return {a,b,c};
    }
    return {-1,-1,-1};
}

#ifndef Q35_NO_MAIN
int main(int argc,char**argv) {
    int low=argc>1?std::atoi(argv[1]):12;
    int high=argc>2?std::atoi(argv[2]):low;
    if(low<4 || high>=64 || low>high) return 2;
    // Tangency: (x-4)^2+(y-5)^2=25 on target y=0.
    assert(roots(8,16,9)==(Mask(1)<<4));
    assert(roots(8,16,9,true)==0);
    // One mate outside board: roots -1 and 3, singleton 3 still counts.
    assert(roots(2,-3,5)==(Mask(1)<<3));
    assert(roots(2,-3,5,true)==0);
    for(int m=low;m<=high;++m) {
        auto start=std::chrono::steady_clock::now();
        auto v=fours(m); std::size_t count=v.size();
        std::array<std::vector<Mask>,3> support;
        for(int k=0;k<3;++k) {
            support[k].resize(count*m);
            for(std::size_t i=0;i<count;++i) for(int c=0;c<m;++c) {
                Mask z=0;
                for(auto p:v[i].pairs) z|=triple_roots(p,c,k,m);
                support[k][i*m+c]=z;
            }
        }
        std::uint64_t candidates[2]={0,0},covers[2]={0,0};
        for(std::size_t i=0;i<count;++i) {
            const auto& b=v[i];
            const Mask* a0=&support[0][i*m];
            const Mask* a2=&support[2][i*m];
            for(std::size_t j=0;j<count;++j) {
                const auto& c=v[j];
                const Mask* a1=&support[1][j*m];
                Mask z=a0[c.x[0]]|a0[c.x[1]]|a0[c.x[2]]|a0[c.x[3]]|
                    a1[b.x[0]]|a1[b.x[1]]|a1[b.x[2]]|a1[b.x[3]];
                if(__builtin_popcountll(z)>=m-3) {
                    ++candidates[0];
                    auto a=cover(graph(b,c,m,false),m);
                    if(a[0]>=0) {
                        ++covers[0];
                        std::cerr<<"outer cover m="<<m<<" A="<<a[0]<<","<<a[1]<<","<<a[2]<<" B=";
                        for(int x:b.x) std::cerr<<x<<",";
                        std::cerr<<" C=";for(int x:c.x) std::cerr<<x<<",";std::cerr<<"\n";
                        return 3;
                    }
                }
                if(j<i) continue; // middle row is symmetric in its exterior rows
                const Mask* a3=&support[2][j*m];
                z=a2[c.x[0]]|a2[c.x[1]]|a2[c.x[2]]|a2[c.x[3]]|
                    a3[b.x[0]]|a3[b.x[1]]|a3[b.x[2]]|a3[b.x[3]];
                if(__builtin_popcountll(z)>=m-3) {
                    ++candidates[1];
                    auto a=cover(graph(b,c,m,true),m);
                    if(a[0]>=0) {
                        ++covers[1];
                        std::cerr<<"middle cover m="<<m<<"\n";
                        return 3;
                    }
                }
            }
        }
        double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout<<"{\"m\":"<<m<<",\"four_sets\":"<<count<<",\"outer_candidates\":"<<candidates[0]
            <<",\"middle_candidates\":"<<candidates[1]<<",\"outer_covers\":"<<covers[0]
            <<",\"middle_covers\":"<<covers[1]<<",\"seconds\":"<<seconds<<"}"<<std::endl;
    }
}
#endif
