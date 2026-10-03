#define Q34_AUDIT_NO_MAIN
#include "q34_independent_audit.cpp"
#include <fstream>
#include <map>
#include <set>

static std::vector<Point> points(Mask s,int m){
    std::vector<Point>p;for(int y=0;y<3;++y)for(int x=0;x<m;++x)if(s&bit(y*m+x))p.push_back({x,y});return p;
}
static bool add_safe(const std::vector<Point>&p,Point q){
    int n=(int)p.size();
    for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)for(int c=b+1;c<n;++c)
        if(!det(p[a],p[b],p[c],q))return false;
    return true;
}
int main(int argc,char**argv){
    if(argc<2)return 2;
    std::cout<<"[";
    for(int arg=1;arg<argc;++arg){
        std::ifstream in(argv[arg]);if(!in)return 3;
        int m=0;char type;std::set<Mask>facets;std::map<Mask,int>sg;
        while(in>>type){
            if(type=='M'){in>>m;continue;}
            std::uint64_t lo,hi;in>>lo>>hi;Mask s=Mask(lo)|(Mask(hi)<<64);
            if(type=='F')facets.insert(s);else{int g;in>>g;sg[s]=g;}
        }
        assert(m>=7&&m<=23);
        std::set<Mask>closure;
        for(Mask f:facets){
            auto p=points(f,m);assert(safe(p));
            for(int i=0;i<3*m;++i)if(!(f&bit(i)))assert(!add_safe(p,{i%m,i/m}));
            Mask s=f;while(true){closure.insert(s);if(!s)break;s=(s-1)&f;}
        }
        assert(closure.size()==sg.size());for(Mask s:closure)assert(sg.count(s));
        std::uint64_t transitions=0;
        for(auto [s,g]:sg){
            auto p=points(s,m);unsigned seen=0;
            for(int i=0;i<3*m;++i)if(!(s&bit(i))&&add_safe(p,{i%m,i/m})){
                ++transitions;auto it=sg.find(s|bit(i));
                int child=it==sg.end()?(8-(int)p.size())%2:it->second;
                seen|=1U<<child;
            }
            assert(g==__builtin_ctz(~seen));
        }
        std::uint64_t full_safe=0;
        if(m==7){
            std::vector<std::uint32_t>forbidden;
            for(int a=0;a<21;++a)for(int b=a+1;b<21;++b)for(int c=b+1;c<21;++c)for(int d=c+1;d<21;++d)
                if(!det({a%m,a/m},{b%m,b/m},{c%m,c/m},{d%m,d/m}))
                    forbidden.push_back((1U<<a)|(1U<<b)|(1U<<c)|(1U<<d));
            assert(forbidden.size()==355);
            std::vector<std::uint8_t>full(1U<<21,255);
            for(std::uint32_t s=1U<<21;s-->0;){
                bool ok=true;for(auto f:forbidden)if((s&f)==f){ok=false;break;}
                if(!ok)continue;++full_safe;unsigned seen=0;
                for(int i=0;i<21;++i)if(!(s&(1U<<i))){int g=full[s|(1U<<i)];if(g!=255)seen|=1U<<g;}
                int g=__builtin_ctz(~seen);full[s]=(std::uint8_t)g;
                auto it=sg.find(s);int expected=it==sg.end()?(9-__builtin_popcount(s))%2:it->second;
                assert(g==expected);
            }
            assert(full_safe==55964);
        }
        if(arg>1)std::cout<<",";
        std::cout<<"{\"m\":"<<m<<",\"short_facets_checked\":"<<facets.size()
            <<",\"exceptional_states_checked\":"<<sg.size()<<",\"legal_transitions_checked\":"<<transitions
            <<",\"independent_full_safe_states_checked\":"<<full_safe<<",\"status\":\"passed\"}";
    }
    std::cout<<"]\n";
}
