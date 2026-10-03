#define Q34_NO_MAIN
#include "q34_support_exclusion.cpp"
#include <map>
#include <set>
#include <unordered_map>
#include <fstream>

struct Row{std::uint64_t mask=0;std::vector<int>x;std::vector<Pair>pairs;};
struct Geometry{Mask base=0;std::array<Mask,69>adj{};};
static Row row(std::uint64_t mask,int m){
    Row r;r.mask=mask;
    for(int x=0;x<m;++x)if(mask&(1ULL<<x))r.x.push_back(x);
    for(std::size_t i=0;i<r.x.size();++i)for(std::size_t j=i+1;j<r.x.size();++j)
        r.pairs.push_back({r.x[i]+r.x[j],r.x[i]*r.x[j]});
    return r;
}
static Geometry geometry(const Row&b,const Row&c,const std::vector<Cross>&g,int m,bool middle){
    Geometry z;
    for(auto p:b.pairs)for(int x:c.x)z.base|=triple(p,x,middle?2:0,m);
    for(auto p:c.pairs)for(int x:b.x)z.base|=triple(p,x,middle?2:1,m);
    for(int a=0;a<m;++a){
        for(auto p:b.pairs){int x=p.s-a;if(x>=0&&x<m&&x!=a)z.adj[a]|=bit(x);}
        for(auto p:c.pairs){int x=p.s-a;if(x>=0&&x<m&&x!=a)z.adj[a]|=bit(x);}
        for(int x:b.x)for(int y:c.x)z.adj[a]|=g[x*m+y].adj[a];
    }
    return z;
}
static Mask blocked(const Row&a,const Row&b,const Row&c,const std::vector<Cross>&g,int m,bool middle){
    if(a.x.size()==3)return bit(m)-1;
    Mask z=a.mask;
    for(auto p:b.pairs)for(int x:c.x)z|=triple(p,x,middle?2:0,m);
    for(auto p:c.pairs)for(int x:b.x)z|=triple(p,x,middle?2:1,m);
    for(int a0:a.x){
        for(auto p:b.pairs){int x=p.s-a0;if(x>=0&&x<m)z|=bit(x);}
        for(auto p:c.pairs){int x=p.s-a0;if(x>=0&&x<m)z|=bit(x);}
        for(int x:b.x)for(int y:c.x)z|=g[x*m+y].adj[a0];
    }
    return z;
}
struct Hash{
    std::size_t operator()(Mask z)const{
        std::uint64_t x=(std::uint64_t)z^((std::uint64_t)(z>>64)*0x9e3779b97f4a7c15ULL);
        x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);
    }
};
static void print_rows(Mask s,int m){
    std::cout<<"[";
    for(int y=0;y<3;++y){if(y)std::cout<<",";std::cout<<"[";bool first=true;
        for(int x=0;x<m;++x)if(s&bit(y*m+x)){if(!first)std::cout<<",";first=false;std::cout<<x;}
        std::cout<<"]";
    }
    std::cout<<"]";
}
int main(int argc,char**argv){
    int low=argc>1?std::atoi(argv[1]):12,high=argc>2?std::atoi(argv[2]):low;
    if(low<7||high>24||low>high)return 2;
    for(int m=low;m<=high;++m){
        auto start=std::chrono::steady_clock::now();
        std::vector<Row>rows;
        rows.push_back(row(0,m));
        for(int a=0;a<m;++a){rows.push_back(row(1ULL<<a,m));
            for(int b=a+1;b<m;++b){rows.push_back(row((1ULL<<a)|(1ULL<<b),m));
                for(int c=b+1;c<m;++c)rows.push_back(row((1ULL<<a)|(1ULL<<b)|(1ULL<<c),m));
            }
        }
        std::array<std::vector<Cross>,2>crosses;
        for(int k=0;k<2;++k)for(int b=0;b<m;++b)for(int c=0;c<m;++c)
            crosses[k].push_back(cross(b,c,m,k));
        Mask all=bit(m)-1;
        std::set<Mask>short_facets;
        for(const Row&b:rows)for(const Row&c:rows){
            bool exterior_safe=true;
            for(auto p:b.pairs)for(auto q:c.pairs)if(p.s==q.s)exterior_safe=false;
            if(!exterior_safe)continue;
            for(int k=0;k<2;++k){
                if(k&&b.mask>c.mask)continue;
                Geometry g=geometry(b,c,crosses[k],m,k);
                Mask need=all&~g.base;
                std::array<Mask,69>closed{};
                int top[2]={0,0};
                for(int a=0;a<m;++a)if(!(g.base&bit(a))){
                    closed[a]=g.adj[a]|bit(a);int gain=pc(closed[a]&need);
                    if(gain>top[0]){top[1]=top[0];top[0]=gain;}else if(gain>top[1])top[1]=gain;
                }
                if(top[0]+top[1]<pc(need))continue;
                auto accept=[&](std::uint64_t a_mask){
                    Row a=row(a_mask,m);
                    std::array<Row,3>r=k?std::array<Row,3>{b,a,c}:std::array<Row,3>{a,b,c};
                    if(blocked(r[0],r[1],r[2],crosses[0],m,false)!=all)return;
                    if(blocked(r[1],r[0],r[2],crosses[1],m,true)!=all)return;
                    if(blocked(r[2],r[1],r[0],crosses[0],m,false)!=all)return;
                    short_facets.insert(Mask(r[0].mask)|(Mask(r[1].mask)<<m)|(Mask(r[2].mask)<<(2*m)));
                    // Both possible exterior target rows, or swapped exterior rows for middle target.
                    short_facets.insert(Mask(r[2].mask)|(Mask(r[1].mask)<<m)|(Mask(r[0].mask)<<(2*m)));
                };
                if(!need)accept(0);
                for(int a=0;a<m;++a)if(closed[a]){
                    if(!(need&~closed[a]))accept(1ULL<<a);
                    for(int d=a+1;d<m;++d)if(closed[d]&&!(g.adj[a]&bit(d))&&!(need&~(closed[a]|closed[d])))
                        accept((1ULL<<a)|(1ULL<<d));
                }
            }
        }
        double census_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::map<int,std::uint64_t>counts;
        std::unordered_map<Mask,std::uint8_t,Hash>sg;
        for(Mask facet:short_facets){
            ++counts[pc(facet)];
            Mask sub=facet;
            while(true){sg.emplace(sub,255);if(!sub)break;sub=(sub-1)&facet;}
        }
        std::vector<Mask>order;order.reserve(sg.size());for(auto [s,g]:sg)order.push_back(s);
        std::sort(order.begin(),order.end(),[](Mask a,Mask b){int pa=pc(a),pb=pc(b);return pa!=pb?pa>pb:a<b;});
        int maxg=1;Mask max_witness=0;std::array<std::uint64_t,10>hist{};
        for(Mask s:order){
            std::array<Row,3>r;
            for(int y=0;y<3;++y)r[y]=row((std::uint64_t)((s>>(y*m))&all),m);
            std::array<Mask,3>ban={blocked(r[0],r[1],r[2],crosses[0],m,false),
                blocked(r[1],r[0],r[2],crosses[1],m,true),blocked(r[2],r[1],r[0],crosses[0],m,false)};
            unsigned seen=0;int k=pc(s);
            for(int y=0;y<3;++y)for(int x=0;x<m;++x)if(!(ban[y]&bit(x))){
                Mask child=s|bit(y*m+x);auto it=sg.find(child);
                int g=it==sg.end()?(8-k)%2:it->second;
                assert(g!=255);seen|=1U<<g;
            }
            int g=__builtin_ctz(~seen);assert(g<=9-k);sg[s]=(std::uint8_t)g;++hist[g];
            if(g>maxg){maxg=g;max_witness=s;}
        }
        int root=sg.count(0)?sg.at(0):1;
        if(argc>3){
            std::ofstream dump(std::string(argv[3])+"_"+std::to_string(m)+".txt");
            if(!dump)return 4;
            dump<<"M "<<m<<"\n";
            for(Mask f:short_facets)dump<<"F "<<(std::uint64_t)f<<" "<<(std::uint64_t)(f>>64)<<"\n";
            for(Mask s:order)dump<<"S "<<(std::uint64_t)s<<" "<<(std::uint64_t)(s>>64)<<" "<<(int)sg.at(s)<<"\n";
        }
        double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout<<"{\"m\":"<<m<<",\"row_subsets\":"<<rows.size()<<",\"short_terminal_counts\":{";
        bool first=true;for(auto [k,n]:counts){if(!first)std::cout<<",";first=false;std::cout<<"\""<<k<<"\":"<<n;}
        std::cout<<"},\"exceptional_states\":"<<sg.size()<<",\"empty_grundy\":"<<root
            <<",\"global_max_grundy\":"<<maxg<<",\"max_grundy_witness_rows\":";
        print_rows(max_witness,m);std::cout<<",\"winning_first_moves\":[";first=true;
        for(int y=0;y<3;++y)for(int x=0;x<m;++x){Mask s=bit(y*m+x);auto it=sg.find(s);int g=it==sg.end()?0:it->second;
            if(!g){if(!first)std::cout<<",";first=false;std::cout<<"["<<x<<","<<y<<"]";}}
        std::cout<<"],\"exceptional_grundy_histogram\":[";
        for(int k=0;k<10;++k){if(k)std::cout<<",";std::cout<<hist[k];}
        std::cout<<"]";
        // Boundary certificates are small; earlier complete lists can be requested
        // in the optional machine-readable dump without flooding the JSON report.
        if(m>=22){
            std::cout<<",\"short_terminal_rows\":[";first=true;
            for(Mask s:short_facets){if(!first)std::cout<<",";first=false;print_rows(s,m);}
            std::cout<<"]";
        }
        std::cout<<",\"census_seconds\":"<<census_seconds<<",\"seconds\":"<<seconds<<"}"<<std::endl;
    }
}
