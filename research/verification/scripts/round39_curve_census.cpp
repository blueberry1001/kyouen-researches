// Independent candidate test by WHOLE CURVE occupancy; values by direct
// whole-curve incremental recursion. Reads validated sorted safe-set layers.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <map>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
using U=uint64_t;
struct Mapping{
    size_t count;const U* masks;
    explicit Mapping(std::string path){int fd=open(path.c_str(),O_RDONLY);if(fd<0)exit(2);struct stat st;if(fstat(fd,&st)||st.st_size%8)exit(3);count=st.st_size/8;
        masks=static_cast<const U*>(mmap(nullptr,st.st_size,PROT_READ,MAP_PRIVATE,fd,0));close(fd);if(masks==MAP_FAILED)exit(4);}
    ~Mapping(){munmap(const_cast<U*>(masks),count*8);}
};
struct Game{
    const std::vector<U>&curves;const std::vector<std::vector<U>>&at;std::unordered_map<U,uint8_t> memo;
    Game(const std::vector<U>&c,const std::vector<std::vector<U>>&a):curves(c),at(a){}
    int value(U s,U legal){auto p=memo.find(s);if(p!=memo.end())return p->second;U seen=0;
        for(U x=legal;x;x&=x-1){int p=__builtin_ctzll(x);U child=s|(U(1)<<p),next=legal&~(U(1)<<p);
            for(U c:at[p])if(__builtin_popcountll(child&c)==3)next&=~c;
            seen|=U(1)<<value(child,next);}
        return memo[s]=__builtin_ctzll(~seen);
    }
};
int main(int argc,char**argv){
    if(argc!=4)return 1;std::ifstream in(argv[1]);int n,v,nq,nc;in>>n>>v>>nq;std::vector<U>quads(nq);for(U&q:quads)in>>q;
    in>>nc;std::vector<U>curves(nc);for(U&c:curves)in>>c;if(!in||v>63)return 5;U full=(U(1)<<v)-1;
    std::vector<std::vector<U>>at(v);for(U c:curves)for(U x=c;x;x&=x-1)at[__builtin_ctzll(x)].push_back(c);
    std::vector<U> completion(v*v*v);for(U q:quads){int p[4],i=0;for(U x=q;x;x&=x-1)p[i++]=__builtin_ctzll(x);
        for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];completion[(a[0]*v+a[1])*v+a[2]]|=U(1)<<p[skip];}}
    std::string dir=argv[2];unsigned long long all=0,candidates=0;std::map<int,unsigned long long>Lhist,ghist;
    U max_s=0,max_L=0;int max_g=-1;
    for(int k=0;;++k){std::string path=dir+"/level_"+std::to_string(k)+".occ";if(access(path.c_str(),R_OK))break;Mapping A(path);all+=A.count;if(k<2)continue;
        unsigned long long eligible=0;std::map<int,unsigned long long> localL,localg;
        #pragma omp parallel
        {
            Game game(curves,at);unsigned long long count=0;std::map<int,unsigned long long> lh,gh;U best_s=0,best_L=0;int best=-1;
            #pragma omp for schedule(dynamic,4096)
            for(long long i=0;i<(long long)A.count;++i){U s=A.masks[i],blocked=0;
                for(U x=s;x;x&=x-1){int a=__builtin_ctzll(x);for(U y=x&(x-1);y;y&=y-1){int b=__builtin_ctzll(y);for(U z=y&(y-1);z;z&=z-1)blocked|=completion[(a*v+b)*v+__builtin_ctzll(z)];}}
                U L=full&~s&~blocked;int m=__builtin_popcountll(L);if(m<4)continue;bool has_pair=false;
                for(U c:curves)if(__builtin_popcountll(s&c)==2&&__builtin_popcountll(L&c)>=2){has_pair=true;break;}
                if(has_pair)continue;++count;++lh[m];U curve_legal=full&~s;
                for(U c:curves)if(__builtin_popcountll(s&c)==3)curve_legal&=~c;
                if(L!=curve_legal)exit(6);game.memo.clear();int g=game.value(s,L);++gh[g];
                if(g>best||(g==best&&s<best_s)){best=g;best_s=s;best_L=L;}
            }
            #pragma omp critical
            {eligible+=count;for(auto[m,c]:lh)localL[m]+=c;for(auto[g,c]:gh)localg[g]+=c;
             if(best>max_g||(best==max_g&&best>=0&&best_s<max_s)){max_g=best;max_s=best_s;max_L=best_L;}}
        }
        candidates+=eligible;for(auto[m,c]:localL)Lhist[m]+=c;for(auto[g,c]:localg)ghist[g]+=c;
        fprintf(stderr,"curve n=%d k=%d count=%zu empty-pair-L>=4=%llu\n",n,k,A.count,eligible);fflush(stderr);
    }
    std::ofstream out(argv[3]);out<<"{\"n\":"<<n<<",\"all_safe_sets_considered\":"<<all<<",\"S_size_min\":2,\"L_size_min\":4,\"empty_pair_candidates\":"<<candidates<<",\"max_computed_g\":"<<std::max(max_g,0)<<",\"maximum_witness_S_mask\":"<<max_s<<",\"maximum_witness_L_mask\":"<<max_L<<",\"legal_size_histogram\":{";
    bool first=true;for(auto[m,c]:Lhist){out<<(first?"":",")<<'"'<<m<<"\":"<<c;first=false;}out<<"},\"g_histogram\":{";first=true;for(auto[g,c]:ghist){out<<(first?"":",")<<'"'<<g<<"\":"<<c;first=false;}out<<"}}\n";
}
