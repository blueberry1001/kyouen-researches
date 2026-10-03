#define Q35_NO_MAIN
#include "q35_support_exclusion.cpp"
#include <map>
#include <set>

struct Row {
    std::vector<int> x;
    std::vector<Pair> pairs;
    Mask mask=0;
};
static Row row(Mask mask,int m) {
    Row r;r.mask=mask;
    for(int x=0;x<m;++x) if(mask&(Mask(1)<<x)) r.x.push_back(x);
    for(std::size_t i=0;i<r.x.size();++i) for(std::size_t j=i+1;j<r.x.size();++j)
        r.pairs.push_back({r.x[i]+r.x[j],r.x[i]*r.x[j]});
    return r;
}
static bool safe_target(const Graph& g,const Row& a) {
    if(g.z&a.mask) return false;
    for(int x:a.x) if(g.adj[x]&a.mask) return false;
    return true;
}
static bool blocked(const Graph& g,const Row& a,Mask all) {
    if(a.x.size()==4) return true;
    Mask u=a.mask|g.z;
    for(int x:a.x) u|=g.adj[x];
    return u==all;
}
static Mask canonical(Mask v,int m) {
    Mask best=v;
    for(int fx=0;fx<2;++fx) for(int fy=0;fy<2;++fy) {
        Mask z=0;
        for(int y=0;y<3;++y) for(int x=0;x<m;++x)
            if(v&(Mask(1)<<(y*m+x))) z|=Mask(1)<<((fy?2-y:y)*m+(fx?m-1-x:x));
        best=std::min(best,z);
    }
    return best;
}
int main(int argc,char**argv) {
    int low=argc>1?std::atoi(argv[1]):7,high=argc>2?std::atoi(argv[2]):11;
    if(low<4 || low>high || high>15) return 2;
    for(int m=low;m<=high;++m) {
        Mask all=(Mask(1)<<m)-1;
        std::vector<Row> rows,deficient;
        for(Mask z=0;z<=all;++z) if(__builtin_popcountll(z)<=4) {
            rows.push_back(row(z,m));
            if(__builtin_popcountll(z)<=3) deficient.push_back(row(z,m));
        }
        std::set<Mask> configurations;
        for(const Row& b:rows) for(const Row& c:rows) for(bool middle:{false,true}) {
            Graph g=graph(b,c,m,middle);
            Mask support=g.z;
            for(int x=0;x<m;++x) support|=g.adj[x];
            if(__builtin_popcountll(support)<m-3) continue;
            for(const Row& a:deficient) {
                if(!safe_target(g,a) || !blocked(g,a,all)) continue;
                std::array<Row,3> r=middle?std::array<Row,3>{b,a,c}:std::array<Row,3>{a,b,c};
                if(!blocked(graph(r[1],r[2],m,false),r[0],all)) continue;
                if(!blocked(graph(r[0],r[2],m,true),r[1],all)) continue;
                if(!blocked(graph(r[1],r[0],m,false),r[2],all)) continue;
                Mask z=r[0].mask|(r[1].mask<<m)|(r[2].mask<<(2*m));
                configurations.insert(z);
                // Outer deficient row may be either y=0 or y=2.
                if(!middle) configurations.insert(r[2].mask|(r[1].mask<<m)|(r[0].mask<<(2*m)));
            }
        }
        std::map<int,std::uint64_t> counts,orbits;
        std::set<Mask> representatives;
        for(Mask v:configurations) {++counts[__builtin_popcountll(v)];representatives.insert(canonical(v,m));}
        for(Mask v:representatives) ++orbits[__builtin_popcountll(v)];
        std::cout<<"{\"m\":"<<m<<",\"deficient_maximal_counts\":{";
        bool first=true;for(auto [n,c]:counts) {if(!first)std::cout<<",";first=false;std::cout<<"\""<<n<<"\":"<<c;}
        std::cout<<"},\"reflection_orbits\":{";
        first=true;for(auto [n,c]:orbits) {if(!first)std::cout<<",";first=false;std::cout<<"\""<<n<<"\":"<<c;}
        std::cout<<"},\"representatives\":[";
        first=true;for(Mask v:representatives) {
            if(!first)std::cout<<",";first=false;std::cout<<"[";
            for(int y=0;y<3;++y) {
                if(y)std::cout<<",";std::cout<<"[";bool fx=true;
                for(int x=0;x<m;++x) if(v&(Mask(1)<<(y*m+x))) {if(!fx)std::cout<<",";fx=false;std::cout<<x;}
                std::cout<<"]";
            }
            std::cout<<"]";
        }
        std::cout<<"]}"<<std::endl;
    }
}
