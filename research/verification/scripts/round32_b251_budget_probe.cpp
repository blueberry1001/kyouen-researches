// Exact P/N search after one forbidden quad removal. Shortcut theorem:
// if any vertex of the removed quad is currently illegal and unoccupied,
// it stays illegal forever, so every continuation is the standard game.
#include <algorithm>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
using U=uint64_t;
struct Standard {
    struct Layer{const U* masks;const uint8_t* pn;size_t count;};
    std::vector<Layer> layers;
    explicit Standard(std::string dir){
        for(int k=0;;++k){std::string path=dir+"/level_"+std::to_string(k)+".occ";int fd=open(path.c_str(),O_RDONLY);if(fd<0)break;
            struct stat st;if(fstat(fd,&st)||st.st_size%8)exit(2);size_t count=st.st_size/8;
            auto masks=static_cast<const U*>(mmap(nullptr,st.st_size,PROT_READ,MAP_PRIVATE,fd,0));close(fd);
            path=dir+"/standard_"+std::to_string(k)+".pn";fd=open(path.c_str(),O_RDONLY);if(fd<0||fstat(fd,&st)||size_t(st.st_size)!=count)exit(3);
            auto pn=static_cast<const uint8_t*>(mmap(nullptr,count,PROT_READ,MAP_PRIVATE,fd,0));close(fd);
            if(masks==MAP_FAILED||pn==MAP_FAILED)exit(4);layers.push_back({masks,pn,count});}
    }
    bool win(U s)const{int k=__builtin_popcountll(s);if(k>=int(layers.size()))throw std::logic_error("standard unsafe height");auto L=layers[k];
        auto p=std::lower_bound(L.masks,L.masks+L.count,s);if(p==L.masks+L.count||*p!=s)throw std::logic_error("standard unsafe mask");return L.pn[p-L.masks];}
};
struct Search {
    int v;U full,removed;uint64_t states=0,shortcuts=0,limit;
    std::vector<U> quads,base,completion;std::unordered_map<U,uint8_t> memo;const Standard& standard;
    explicit Search(const Standard& table):standard(table){}
    size_t key(int a,int b,int c)const{if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);return (a*v+b)*v+c;}
    U after(U s,U legal,int p)const{legal&=~(U(1)<<p);for(U x=s;x;x&=x-1){int a=__builtin_ctzll(x);for(U y=x&(x-1);y;y&=y-1)legal&=~completion[key(a,__builtin_ctzll(y),p)];}return legal;}
    bool win(U s,U legal){auto found=memo.find(s);if(found!=memo.end())return found->second;
        if(++states>limit)throw std::runtime_error("budget");
        if(removed&~(s|legal)){++shortcuts;bool value=standard.win(s);memo.emplace(s,value);return value;}
        for(U x=legal;x;){int p=63-__builtin_clzll(x);x^=U(1)<<p;if(!win(s|(U(1)<<p),after(s,legal,p))){memo.emplace(s,1);return true;}}
        memo.emplace(s,0);return false;
    }
    void prepare(){base.assign(v*v*v,0);for(U q:quads){int p[4],i=0;for(U x=q;x;x&=x-1)p[i++]=__builtin_ctzll(x);if(i!=4)throw std::logic_error("quad");
        for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];base[key(a[0],a[1],a[2])]|=U(1)<<p[skip];}}
    }
    int run(int index){completion=base;removed=quads[index];int p[4],i=0;for(U x=removed;x;x&=x-1)p[i++]=__builtin_ctzll(x);
        for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];completion[key(a[0],a[1],a[2])]&=~(U(1)<<p[skip]);}
        states=shortcuts=0;memo.clear();try{return win(0,full);}catch(const std::runtime_error&){return -1;}
    }
};
int main(int argc,char**argv){if(argc!=5)return 1;Standard standard(argv[2]);Search S(standard);std::ifstream input(argv[1]);int nq,count;
    if(!(input>>S.v>>nq>>count)||S.v!=49)return 5;S.full=(U(1)<<S.v)-1;S.limit=std::stoull(argv[4]);S.quads.resize(nq);for(U&q:S.quads)input>>q;
    std::vector<int> reps(count);for(int&r:reps)input>>r;S.prepare();S.memo.reserve(std::min<uint64_t>(S.limit,4000000));
    if(standard.win(0))return 6;
    std::ofstream out(argv[3]);out<<"{\"n\":7,\"standard_outcome\":0,\"node_budget\":"<<S.limit<<",\"representatives_total\":"<<count<<",\"cases\":[";
    int done=0,unknown=0,flips=0;
    for(int index:reps){int value=S.run(index);if(done)out<<',';out<<"{\"removed_index\":"<<index<<",\"removed_mask\":"<<S.removed<<",\"outcome\":"<<value<<",\"states\":"<<S.states<<",\"standard_shortcuts\":"<<S.shortcuts<<"}"<<std::flush;
        ++done;unknown+=value<0;flips+=value==1;fprintf(stderr,"case=%d index=%d outcome=%d states=%llu shortcuts=%llu\n",done,index,value,(unsigned long long)S.states,(unsigned long long)S.shortcuts);fflush(stderr);
        if(flips)break;
    }
    out<<"],\"checked\":"<<done<<",\"unknown\":"<<unknown<<",\"flips\":"<<flips<<",\"all_representatives_processed\":"<<(done==count?"true":"false")<<"}\n";
}
