#define Q35_NO_MAIN
#include "q35_support_exclusion.cpp"
#include <numeric>
#include <random>
#include <fstream>
#include <unordered_map>
#include <utility>

namespace legacy {
#define main q35_legacy_main
#include "q5_w3_stabilization.cpp"
#undef main
}

struct Point {long long x,y;};
static long long det(Point a,Point b,Point c,Point d) {
    // Translate d to the origin and use the 3x3 in-circle determinant.
    a.x-=d.x;a.y-=d.y;b.x-=d.x;b.y-=d.y;c.x-=d.x;c.y-=d.y;
    auto norm=[](Point p){return p.x*p.x+p.y*p.y;};
    return norm(a)*(b.x*c.y-b.y*c.x)-norm(b)*(a.x*c.y-a.y*c.x)
        +norm(c)*(a.x*b.y-a.y*b.x);
}
static bool forbidden(std::array<Point,5> p) {
    // Check all five 4x4 lifted minors, independent of the three-row equations.
    for(int skip=0;skip<5;++skip) {
        std::array<Point,4> q;int n=0;
        for(int i=0;i<5;++i) if(i!=skip) q[n++]=p[i];
        if(det(q[0],q[1],q[2],q[3])) return false;
    }
    return true;
}
static Graph direct(const Four& b,const Four& c,int m,bool middle) {
    Graph g; int ty=middle?1:0,by=middle?0:1,cy=2;
    for(int x=0;x<m;++x) {
        bool blocked=false;
        for(int i=0;i<4;++i) for(int j=i+1;j<4;++j)
        for(int k=0;k<4;++k) for(int l=k+1;l<4;++l)
            if(forbidden({Point{x,ty},Point{b.x[i],by},Point{b.x[j],by},
                          Point{c.x[k],cy},Point{c.x[l],cy}})) blocked=true;
        if(blocked) g.z |= Mask(1)<<x;
    }
    for(int x=0;x<m;++x) for(int y=x+1;y<m;++y) {
        bool e=false;
        for(int i=0;i<4;++i) for(int j=i+1;j<4;++j) for(int k=0;k<4;++k) {
            if(forbidden({Point{x,ty},Point{y,ty},Point{b.x[i],by},
                          Point{b.x[j],by},Point{c.x[k],cy}})) e=true;
            if(forbidden({Point{x,ty},Point{y,ty},Point{c.x[i],cy},
                          Point{c.x[j],cy},Point{b.x[k],by}})) e=true;
        }
        if(e) edge(g,(Mask(1)<<x)|(Mask(1)<<y));
    }
    return g;
}
static void compare(const Four& b,const Four& c,int m) {
    legacy::FourSet lb,lc;
    lb.x=b.x;lc.x=c.x;
    for(int i=0;i<6;++i) {
        lb.pairs[i]={b.pairs[i].s,b.pairs[i].p};
        lc.pairs[i]={c.pairs[i].s,c.pairs[i].p};
    }
    for(bool middle:{false,true}) {
        Graph g=graph(b,c,m,middle),d=direct(b,c,m,middle);
        auto old=middle?legacy::middle_cover(lb,lc,m):legacy::outer_cover(lb,lc,m);
        assert(g.z==d.z);
        assert(old.no_target_stone==d.z);
        for(int x=0;x<m;++x) {
            assert(g.adj[x]==d.adj[x]);
            assert(old.with_a[x]==d.adj[x]);
        }
        Mask support=0,actual=g.z;
        for(auto p:b.pairs) for(int x:c.x) support|=triple_roots(p,x,middle?2:0,m);
        for(auto p:c.pairs) for(int x:b.x) support|=triple_roots(p,x,middle?2:1,m);
        for(int x=0;x<m;++x) actual |= g.adj[x];
        assert((actual&~support)==0);
    }
}

static std::vector<Mask> forbidden_masks(int m) {
    std::vector<Point> p;
    for(int y=0;y<3;++y) for(int x=0;x<m;++x) p.push_back({x,y});
    std::vector<Mask> result;
    for(int a=0;a<3*m;++a) for(int b=a+1;b<3*m;++b) for(int c=b+1;c<3*m;++c)
    for(int d=c+1;d<3*m;++d) for(int e=d+1;e<3*m;++e)
        if(forbidden({p[a],p[b],p[c],p[d],p[e]}))
            result.push_back((Mask(1)<<a)|(Mask(1)<<b)|(Mask(1)<<c)|(Mask(1)<<d)|(Mask(1)<<e));
    return result;
}
static void direct_grundy(int m) {
    auto f=forbidden_masks(m);
    std::size_t size=std::size_t(1)<<(3*m);
    std::vector<std::uint8_t> sg(size,255);
    std::array<std::uint64_t,13> safe_by_size{},terminal_by_size{},hist{};
    std::uint64_t safe=0;int maxg=0;
    for(std::size_t z=size;z-->0;) {
        bool ok=true;for(Mask edge:f) if((z&edge)==edge) {ok=false;break;}
        if(!ok) continue;
        ++safe;int k=__builtin_popcountll(z);++safe_by_size[k];
        unsigned seen=0;
        for(int p=0;p<3*m;++p) if(!(z&(std::size_t(1)<<p))) {
            int child=sg[z|(std::size_t(1)<<p)];
            if(child!=255) seen|=1U<<child;
        }
        if(!seen) ++terminal_by_size[k];
        int g=__builtin_ctz(~seen);sg[z]=(std::uint8_t)g;++hist[g];maxg=std::max(maxg,g);
    }
    std::cout<<"{\"m\":"<<m<<",\"forbidden5\":"<<f.size()<<",\"safe_states\":"<<safe
        <<",\"empty_grundy\":"<<(int)sg[0]<<",\"max_grundy\":"<<maxg<<",\"safe_by_size\":[";
    for(int i=0;i<=12;++i){if(i)std::cout<<",";std::cout<<safe_by_size[i];}
    std::cout<<"],\"terminal_by_size\":[";
    for(int i=0;i<=12;++i){if(i)std::cout<<",";std::cout<<terminal_by_size[i];}
    std::cout<<"],\"grundy_histogram\":[";
    for(int i=0;i<=maxg;++i){if(i)std::cout<<",";std::cout<<hist[i];}
    std::cout<<"]}";
}

int main() {
    std::uint64_t cases=0;
    for(int m=4;m<=7;++m) {
        auto v=fours(m);
        for(auto& b:v) for(auto& c:v) {compare(b,c,m);++cases;}
    }
    std::mt19937 rng(20261003);
    for(int m=8;m<=40;++m) {
        auto v=fours(m);
        for(int n=0;n<25;++n) {compare(v[rng()%v.size()],v[rng()%v.size()],m);++cases;}
    }
    auto v=fours(9);
    for(auto& b:v) for(auto& c:v) {
        if(b.x==std::array<int,4>{0,1,7,8} && c.x==std::array<int,4>{0,2,6,8}) {
            compare(b,c,9);++cases;
            assert(graph(b,c,9,false).z & (Mask(1)<<4));
        }
    }
    std::cout<<"{\"determinant_graph_cases\":"<<2*cases
        <<",\"all_m4_to_m7_pairs\":true,\"random_pairs_per_m8_to_m40\":25,"
        "\"seed\":20261003,\"tangent_regression\":true,\"legacy_graphs_also_checked\":true,"
        "\"legacy_m11_witness_verified\":"<<(legacy::verify_m11_witness()?"true":"false")
        <<",\"status\":\"passed\",\"independent_full_grundy\":[";
    for(int m=4;m<=6;++m) {if(m>4)std::cout<<",";direct_grundy(m);}
    std::cout<<"]}\n";
}
