#define Q35_NO_MAIN
#include "q35_support_exclusion.cpp"
#include <numeric>

struct GameRow {
    std::vector<int> x;
    std::vector<Pair> pairs;
    Mask mask=0, pairmask=0;
    std::vector<std::pair<int,int>> children;
};
struct Compatibility {Mask edges;std::uint16_t base;};
static void coordinates(std::ostream& out,const std::vector<GameRow>& rows,
                        const std::array<int,3>& indices) {
    out<<"[";
    for(int y=0;y<3;++y) {
        if(y)out<<",";out<<"[";
        for(std::size_t i=0;i<rows[indices[y]].x.size();++i) {
            if(i)out<<",";out<<rows[indices[y]].x[i];
        }
        out<<"]";
    }
    out<<"]";
}
int main(int argc,char**argv) {
    int low=argc>1?std::atoi(argv[1]):7,high=argc>2?std::atoi(argv[2]):11;
    if(low<4 || low>high || high>11) return 2;
    for(int m=low;m<=high;++m) {
        auto start=std::chrono::steady_clock::now();
        std::vector<GameRow> rows;
        std::vector<int> index(1<<m,-1);
        int pairindex[12][12]{};int pc=0;
        for(int x=0;x<m;++x) for(int y=x+1;y<m;++y) pairindex[x][y]=pc++;
        for(int z=0;z<(1<<m);++z) if(__builtin_popcount((unsigned)z)<=4) {
            GameRow r;r.mask=z;
            for(int x=0;x<m;++x) if(z&(1<<x)) r.x.push_back(x);
            for(std::size_t i=0;i<r.x.size();++i) for(std::size_t j=i+1;j<r.x.size();++j) {
                int a=r.x[i],b=r.x[j];
                r.pairs.push_back({a+b,a*b});
                r.pairmask |= Mask(1)<<pairindex[a][b];
            }
            rows.push_back(r);
        }
        std::sort(rows.begin(),rows.end(),[](const auto& a,const auto& b){
            return a.x.size()!=b.x.size()?a.x.size()>b.x.size():a.mask<b.mask;
        });
        int n=(int)rows.size();
        for(int i=0;i<n;++i) index[rows[i].mask]=i;
        for(int i=0;i<n;++i) if(rows[i].x.size()<4)
            for(int x=0;x<m;++x) if(!(rows[i].mask&(Mask(1)<<x))) {
                int j=index[rows[i].mask|(Mask(1)<<x)];
                assert(j>=0 && j<i);
                rows[i].children.push_back({x,j});
            }
        const std::size_t nn=(std::size_t)n*n,total=nn*n;
        std::vector<Compatibility> compatible(nn);
        for(int b=0;b<n;++b) for(int c=0;c<n;++c) {
            Graph g=graph(rows[b],rows[c],m,false);
            Mask edges=0;
            for(int x=0;x<m;++x) for(int y=x+1;y<m;++y)
                if(g.adj[x]&(Mask(1)<<y)) edges|=Mask(1)<<pairindex[x][y];
            compatible[(std::size_t)b*n+c]={edges,(std::uint16_t)g.z};
        }
        std::vector<std::uint8_t> grundy(total,255);
        std::array<std::uint64_t,13> safe_by_size{},terminal_by_size{},g_hist{};
        int max_g=0;std::array<int,3> max_g_rows{};
        for(int a=0;a<n;++a) for(int b=0;b<n;++b) {
            std::size_t offset=(std::size_t)a*nn+(std::size_t)b*n;
            for(int c=0;c<n;++c) {
                auto s=compatible[(std::size_t)b*n+c];
                if((s.base&rows[a].mask) || (s.edges&rows[a].pairmask)) continue;
                int size=(int)(rows[a].x.size()+rows[b].x.size()+rows[c].x.size());
                ++safe_by_size[size];
                unsigned seen=0;
                for(auto [x,j]:rows[a].children) {
                    int g=grundy[(std::size_t)j*nn+(std::size_t)b*n+c];
                    if(g!=255) seen|=1U<<g;
                }
                for(auto [x,j]:rows[b].children) {
                    int g=grundy[(std::size_t)a*nn+(std::size_t)j*n+c];
                    if(g!=255) seen|=1U<<g;
                }
                for(auto [x,j]:rows[c].children) {
                    int g=grundy[offset+j];
                    if(g!=255) seen|=1U<<g;
                }
                if(!seen) ++terminal_by_size[size];
                int g=__builtin_ctz(~seen);
                assert(g<=12-size);
                grundy[offset+c]=(std::uint8_t)g;
                ++g_hist[g];
                if(g>max_g) {max_g=g;max_g_rows={a,b,c};}
            }
        }
        std::uint64_t safe=std::accumulate(safe_by_size.begin(),safe_by_size.end(),std::uint64_t(0));
        int empty=index[0];std::size_t root=(std::size_t)empty*nn+(std::size_t)empty*n+empty;
        double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout<<"{\"m\":"<<m<<",\"row_subsets\":"<<n<<",\"table_entries\":"<<total
            <<",\"safe_states\":"<<safe<<",\"empty_grundy\":"<<(int)grundy[root]
            <<",\"max_grundy\":"<<max_g<<",\"terminal_counts\":{";
        bool first=true;for(int k=0;k<=12;++k) if(terminal_by_size[k]) {
            if(!first)std::cout<<",";first=false;std::cout<<"\""<<k<<"\":"<<terminal_by_size[k];
        }
        std::cout<<"},\"safe_by_size\":[";
        for(int k=0;k<=12;++k) {if(k)std::cout<<",";std::cout<<safe_by_size[k];}
        std::cout<<"],\"grundy_histogram\":[";
        for(int k=0;k<=max_g;++k) {if(k)std::cout<<",";std::cout<<g_hist[k];}
        std::cout<<"],\"max_grundy_witness_rows\":";
        coordinates(std::cout,rows,max_g_rows);
        std::cout<<",\"winning_first_moves\":[";first=true;
        for(int y=0;y<3;++y) for(auto [x,j]:rows[empty].children) {
            auto z=std::array<int,3>{empty,empty,empty};z[y]=j;
            std::size_t at=(std::size_t)z[0]*nn+(std::size_t)z[1]*n+z[2];
            if(grundy[at]==0) {if(!first)std::cout<<",";first=false;std::cout<<"["<<x<<","<<y<<"]";}
        }
        std::cout<<"],\"seconds\":"<<seconds<<"}"<<std::endl;
    }
}
