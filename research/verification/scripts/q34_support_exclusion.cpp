#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>

using Mask=unsigned __int128;
static Mask bit(int x){return Mask(1)<<x;}
static int pc(Mask a){return __builtin_popcountll((std::uint64_t)a)+__builtin_popcountll((std::uint64_t)(a>>64));}
struct Pair{int s,p;};
struct Three{std::array<int,3>x;std::array<Pair,3>pairs;};
static Mask roots(int s,int p,int m){
    int d=s*s-4*p;if(d<0)return 0;
    int r=(int)std::sqrt((double)d);while((r+1)*(r+1)<=d)++r;while(r*r>d)--r;
    if(r*r!=d||((s-r)&1))return 0;
    int a=(s-r)/2,b=(s+r)/2;Mask out=0;
    if(0<=a&&a<m)out|=bit(a);if(0<=b&&b<m)out|=bit(b);return out;
}
static Mask triple(Pair a,int b,int kind,int m){
    int pb=b*(a.s-b),pt;
    if(kind==0)pt=2+2*a.p-pb;
    else if(kind==1)pt=2+2*pb-a.p;
    else {int n=a.p+pb-2;if(n&1)return 0;pt=n/2;}
    return roots(a.s,pt,m);
}
struct Cross{Mask support=0;std::array<Mask,69>adj{};};
static Cross cross(int b,int c,int m,bool middle){
    Cross g;
    for(int a=0;a<m;++a){
        int num,den;
        if(middle){num=2-a*(b+c)+b*b+c*c;den=b+c-2*a;}
        else{num=2+a*(2*b-c)-2*b*b+c*c;den=a-2*b+c;}
        if(!den||num%den)continue;
        int x=num/den;if(x<0||x>=m||x==a)continue;
        g.adj[a]|=bit(x);g.support|=bit(a)|bit(x);
    }
    return g;
}
static std::vector<Three> threes(int m){
    std::vector<Three>v;
    for(int a=0;a<m;++a)for(int b=a+1;b<m;++b)for(int c=b+1;c<m;++c)
        v.push_back({{a,b,c},{{{a+b,a*b},{a+c,a*c},{b+c,b*c}}}});
    return v;
}
static std::array<int,2> cover(Mask z,const Three&b,const Three&c,
                            const std::vector<Cross>&g,int m,bool require_safe){
    Mask need=(bit(m)-1)&~z;
    std::array<Mask,69> n{};int top[2]={0,0};
    for(int a=0;a<m;++a){
        if(require_safe&&(z&bit(a)))continue;
        n[a]=bit(a);
        for(auto p:b.pairs){int x=p.s-a;if(x>=0&&x<m&&x!=a)n[a]|=bit(x);}
        for(auto p:c.pairs){int x=p.s-a;if(x>=0&&x<m&&x!=a)n[a]|=bit(x);}
        for(int x:b.x)for(int y:c.x)n[a]|=g[x*m+y].adj[a];
        int gain=pc(n[a]&need);
        if(gain>top[0]){top[1]=top[0];top[0]=gain;}
        else if(gain>top[1])top[1]=gain;
    }
    if(top[0]+top[1]<pc(need))return {-1,-1};
    for(int a=0;a<m;++a)for(int d=a+1;d<m;++d){
        if(require_safe&&(!n[a]||!n[d]||(n[a]&bit(d))))continue;
        if(!(need&~(n[a]|n[d])))return {a,d};
    }
    return {-1,-1};
}

#ifndef Q34_NO_MAIN
int main(int argc,char**argv){
    int low=argc>1?std::atoi(argv[1]):12,high=argc>2?std::atoi(argv[2]):low;
    if(low<9||high>68||low>high)return 2;
    for(int m=low;m<=high;++m){
        auto start=std::chrono::steady_clock::now();auto v=threes(m);std::size_t n=v.size();
        std::array<std::vector<Mask>,3>z;
        for(int kind=0;kind<3;++kind){
            z[kind].resize(n*m);
            for(std::size_t i=0;i<n;++i)for(int c=0;c<m;++c)
                for(auto p:v[i].pairs)z[kind][i*m+c]|=triple(p,c,kind,m);
        }
        std::array<std::vector<Cross>,2>g;
        for(int k=0;k<2;++k)for(int b=0;b<m;++b)for(int c=0;c<m;++c)
            g[k].push_back(cross(b,c,m,k));
        std::array<bool,2>found{};std::array<std::uint64_t,2> candidates{};
        std::array<std::array<int,2>,2>wA{};std::array<Three,2>wB{},wC{};
        for(std::size_t i=0;i<n;++i)for(std::size_t j=0;j<n;++j){
            bool exterior_safe=true;
            for(auto p:v[i].pairs)for(auto q:v[j].pairs)if(p.s==q.s)exterior_safe=false;
            if(!exterior_safe)continue;
            for(int k=0;k<2;++k){
                if(found[k]||(k&&j<i))continue;
                const auto&b=v[i];const auto&c=v[j];
                Mask base=0,support=0;
                for(int x:c.x)base|=z[k?2:0][i*m+x];
                for(int x:b.x)base|=z[k?2:1][j*m+x];
                // Every vertex has <=15 neighbors, hence two closed neighborhoods <=32.
                if(pc(base)<m-32)continue;
                for(int x:b.x)for(int y:c.x)support|=g[k][x*m+y].support;
                // Without cross-row pair circles each target vertex has <=6 neighbors.
                if(pc(base|support)<m-14)continue;
                ++candidates[k];
                auto a=cover(base,b,c,g[k],m,false);
                if(a[0]>=0){found[k]=true;wA[k]=a;wB[k]=b;wC[k]=c;}
            }
            if(found[0]&&found[1])break;
        }
        double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout<<"{\"m\":"<<m<<",\"three_sets\":"<<n<<",\"cover_exists\":["<<found[0]<<","<<found[1]
            <<"],\"candidates\":["<<candidates[0]<<","<<candidates[1]<<"],\"witnesses\":[";
        for(int k=0;k<2;++k){
            if(k)std::cout<<",";
            if(!found[k]){std::cout<<"null";continue;}
            std::cout<<"{\"A\":["<<wA[k][0]<<","<<wA[k][1]<<"],\"B\":[";
            for(int i=0;i<3;++i){if(i)std::cout<<",";std::cout<<wB[k].x[i];}
            std::cout<<"],\"C\":[";for(int i=0;i<3;++i){if(i)std::cout<<",";std::cout<<wC[k].x[i];}
            std::cout<<"]}";
        }
        std::cout<<"],\"seconds\":"<<seconds<<"}"<<std::endl;
    }
}
#endif
