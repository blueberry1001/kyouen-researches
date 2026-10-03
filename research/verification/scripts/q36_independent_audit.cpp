#define Q35_NO_MAIN
#include "q35_support_exclusion.cpp"
#include <random>

struct Point{long long x,y;};
static long long det(Point a,Point b,Point c,Point d){
    a.x-=d.x;a.y-=d.y;b.x-=d.x;b.y-=d.y;c.x-=d.x;c.y-=d.y;
    auto norm=[](Point p){return p.x*p.x+p.y*p.y;};
    return norm(a)*(b.x*c.y-b.y*c.x)-norm(b)*(a.x*c.y-a.y*c.x)+norm(c)*(a.x*b.y-a.y*b.x);
}
static bool forbidden(const std::array<Point,6>&p){
    for(int a=0;a<6;++a)for(int b=a+1;b<6;++b)for(int c=b+1;c<6;++c)for(int d=c+1;d<6;++d)
        if(det(p[a],p[b],p[c],p[d]))return false;
    return true;
}
struct Five{std::array<int,5>x;std::array<Pair,10>pairs;};
static std::vector<Five>fives(int m){
    std::vector<Five>out;
    for(int a=0;a<m;++a)for(int b=a+1;b<m;++b)for(int c=b+1;c<m;++c)
    for(int d=c+1;d<m;++d)for(int e=d+1;e<m;++e){
        Five s;s.x={a,b,c,d,e};int t=0;
        for(int i=0;i<5;++i)for(int j=i+1;j<5;++j)s.pairs[t++]={s.x[i]+s.x[j],s.x[i]*s.x[j]};
        out.push_back(s);
    }
    return out;
}
static void compare(const Five&b,const Five&c,int m){
    Graph g;
    for(auto p:b.pairs)for(auto q:c.pairs)if(p.s==q.s)edge(g,roots(p.s,2+2*p.p-q.p,m,true));
    for(int a=0;a<m;++a)for(int d=a+1;d<m;++d){
        bool expected=false;
        for(int i=0;i<5;++i)for(int j=i+1;j<5;++j)for(int k=0;k<5;++k)for(int l=k+1;l<5;++l)
            if(forbidden({Point{a,0},Point{d,0},Point{b.x[i],1},Point{b.x[j],1},Point{c.x[k],2},Point{c.x[l],2}}))
                expected=true;
        assert(expected==bool(g.adj[a]&(Mask(1)<<d)));
    }
}
static void direct_game(int m){
    std::vector<Point>p;for(int y=0;y<3;++y)for(int x=0;x<m;++x)p.push_back({x,y});
    std::vector<Mask>f;
    for(int a=0;a<3*m;++a)for(int b=a+1;b<3*m;++b)for(int c=b+1;c<3*m;++c)
    for(int d=c+1;d<3*m;++d)for(int e=d+1;e<3*m;++e)for(int h=e+1;h<3*m;++h)
        if(forbidden({p[a],p[b],p[c],p[d],p[e],p[h]}))
            f.push_back((Mask(1)<<a)|(Mask(1)<<b)|(Mask(1)<<c)|(Mask(1)<<d)|(Mask(1)<<e)|(Mask(1)<<h));
    std::size_t n=std::size_t(1)<<(3*m);std::vector<std::uint8_t>sg(n,255);
    std::array<std::uint64_t,16>safe_by_size{},terminals{},hist{};std::uint64_t safe=0;int maxg=0;
    for(std::size_t s=n;s-->0;){
        bool ok=true;for(Mask z:f)if((s&z)==z){ok=false;break;}
        if(!ok)continue;
        int k=__builtin_popcountll(s);++safe;++safe_by_size[k];unsigned seen=0;
        for(int x=0;x<3*m;++x)if(!(s&(std::size_t(1)<<x))){int child=sg[s|(std::size_t(1)<<x)];if(child!=255)seen|=1U<<child;}
        if(!seen)++terminals[k];int g=__builtin_ctz(~seen);sg[s]=(std::uint8_t)g;++hist[g];maxg=std::max(maxg,g);
    }
    std::cout<<"{\"m\":"<<m<<",\"forbidden6\":"<<f.size()<<",\"safe_states\":"<<safe
        <<",\"empty_grundy\":"<<(int)sg[0]<<",\"max_grundy\":"<<maxg<<",\"safe_by_size\":[";
    for(int k=0;k<=15;++k){if(k)std::cout<<",";std::cout<<safe_by_size[k];}
    std::cout<<"],\"terminal_by_size\":[";for(int k=0;k<=15;++k){if(k)std::cout<<",";std::cout<<terminals[k];}
    std::cout<<"],\"grundy_histogram\":[";for(int k=0;k<=maxg;++k){if(k)std::cout<<",";std::cout<<hist[k];}
    std::cout<<"]}";
}
int main(){
    int cases=0;
    for(int m=5;m<=7;++m){auto v=fives(m);for(auto b:v)for(auto c:v){compare(b,c,m);++cases;}}
    std::mt19937 rng(20261003);
    for(int m=8;m<=9;++m){auto v=fives(m);for(int i=0;i<100;++i){compare(v[rng()%v.size()],v[rng()%v.size()],m);++cases;}}
    std::cout<<"{\"determinant_graph_cases\":"<<cases<<",\"all_pairs_m5_to_m7\":true,"
        "\"random_pairs_per_m8_and_m9\":100,\"seed\":20261003,\"status\":\"passed\",\"direct_full_grundy\":[";
    for(int m=1;m<=8;++m){if(m>1)std::cout<<",";direct_game(m);}
    std::cout<<"]}\n";
}
