#define Q34_NO_MAIN
#include "q34_support_exclusion.cpp"
#include <random>

struct Point{long long x,y;};
static long long det(Point a,Point b,Point c,Point d){
    a.x-=d.x;a.y-=d.y;b.x-=d.x;b.y-=d.y;c.x-=d.x;c.y-=d.y;
    auto norm=[](Point p){return p.x*p.x+p.y*p.y;};
    return norm(a)*(b.x*c.y-b.y*c.x)-norm(b)*(a.x*c.y-a.y*c.x)+norm(c)*(a.x*b.y-a.y*b.x);
}
static void compare(const Three&b,const Three&c,int m,bool middle){
    int ty=middle?1:0,by=middle?0:1;
    std::array<Point,6>outside{};
    for(int i=0;i<3;++i){outside[i]={b.x[i],by};outside[i+3]={c.x[i],2};}
    Mask base=0,expected=0;
    for(auto p:b.pairs)for(int x:c.x)base|=triple(p,x,middle?2:0,m);
    for(auto p:c.pairs)for(int x:b.x)base|=triple(p,x,middle?2:1,m);
    for(int x=0;x<m;++x)for(int i=0;i<6;++i)for(int j=i+1;j<6;++j)for(int k=j+1;k<6;++k)
        if(!det({x,ty},outside[i],outside[j],outside[k]))expected|=bit(x);
    assert(base==expected);
    std::array<Mask,69>adj{};
    for(int a=0;a<m;++a){
        for(auto p:b.pairs){int x=p.s-a;if(0<=x&&x<m&&x!=a)adj[a]|=bit(x);}
        for(auto p:c.pairs){int x=p.s-a;if(0<=x&&x<m&&x!=a)adj[a]|=bit(x);}
        for(int x:b.x)for(int y:c.x)adj[a]|=cross(x,y,m,middle).adj[a];
    }
    for(int a=0;a<m;++a)for(int d=a+1;d<m;++d){
        bool found=false;
        for(int i=0;i<6;++i)for(int j=i+1;j<6;++j)
            if(!det({a,ty},{d,ty},outside[i],outside[j]))found=true;
        assert(found==bool(adj[a]&bit(d)));
    }
}
static bool safe(const std::vector<Point>&p){
    int n=(int)p.size();
    for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)for(int c=b+1;c<n;++c)for(int d=c+1;d<n;++d)
        if(!det(p[a],p[b],p[c],p[d]))return false;
    return true;
}
static bool witness(bool middle){
    int m=23;
    std::vector<std::vector<int>>rows=middle?std::vector<std::vector<int>>{{4,7,18},{3,4},{4,10,13}}:
        std::vector<std::vector<int>>{{1,17},{7,10,13},{9,10,12}};
    std::vector<Point>p;
    for(int y=0;y<3;++y)for(int x:rows[y])p.push_back({x,y});
    assert(safe(p));
    for(int y=0;y<3;++y)for(int x=0;x<m;++x){
        bool occupied=false;for(auto q:p)if(q.x==x&&q.y==y)occupied=true;
        if(occupied)continue;
        p.push_back({x,y});assert(!safe(p));p.pop_back();
    }
    return true;
}
#ifndef Q34_AUDIT_NO_MAIN
int main(){
    std::uint64_t cases=0;
    for(int m=3;m<=7;++m){auto v=threes(m);for(auto b:v)for(auto c:v)for(bool middle:{false,true}){
        compare(b,c,m,middle);++cases;
    }}
    std::mt19937 rng(20261003);
    for(int m=8;m<=68;++m){auto v=threes(m);for(int i=0;i<12;++i)for(bool middle:{false,true}){
        compare(v[rng()%v.size()],v[rng()%v.size()],m,middle);++cases;
    }}
    assert(witness(false)&&witness(true));
    std::cout<<"{\"determinant_graph_cases\":"<<cases<<",\"all_m3_to_m7_pairs\":true,"
        "\"random_pairs_per_orientation_per_m8_to_m68\":12,\"seed\":20261003,"
        "\"m23_outer_witness\":[[1,17],[7,10,13],[9,10,12]],"
        "\"m23_middle_witness\":[[4,7,18],[3,4],[4,10,13]],"
        "\"both_witnesses_safe_and_maximal\":true,\"status\":\"passed\"}\n";
}
#endif
