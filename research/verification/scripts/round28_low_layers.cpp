// Export exact mex and low layers from sorted safe-set level files.
// Geometry/enumeration: kc_core.h and round5_prand_stream.cpp --enum.
// This solver uses only Grundy numbers, no probability or modular values.
#include "kc_core.h"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
using kc::u64;
struct Value { u64 terminal=0, forced=0; unsigned char g=0; };
struct Mapping {
    int fd; size_t size; const u64* data;
    explicit Mapping(const std::string& path) {
        fd=open(path.c_str(),O_RDONLY); if(fd<0){perror(path.c_str());exit(2);}
        struct stat st; if(fstat(fd,&st)||st.st_size%8){exit(3);}
        size=st.st_size/8;
        data=size ? static_cast<const u64*>(mmap(nullptr,st.st_size,PROT_READ,MAP_PRIVATE,fd,0)):nullptr;
        if(size && data==MAP_FAILED){perror("mmap");exit(4);}
    }
    ~Mapping(){if(size)munmap(const_cast<u64*>(data),size*8);close(fd);}
};
int main(int argc,char** argv){
    if(argc!=4){fprintf(stderr,"usage: round28_low_layers n spilldir output.json\n");return 1;}
    int n=atoi(argv[1]); kc::Board board;kc::build_square(board,n);
    if(board.V>64)return 2;
    std::string dir=argv[2];
    auto path=[&](int k){return dir+"/level_"+std::to_string(k)+".occ";};
    int K=0; while(access(path(K+1).c_str(),R_OK)==0)++K;
    static u64 completion[64][64][64]{};
    for(u64 q:board.quads){
        int p[4],i=0;for(u64 t=q;t;t&=t-1)p[i++]=__builtin_ctzll(t);
        if(i!=4)return 3;
        for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];
            completion[a[0]][a[1]][a[2]]|=u64(1)<<p[skip];}
    }
    FILE* out=fopen(argv[3],"w");if(!out)return 4;
    fprintf(out,"{\"n\":%d,\"quads\":%zu,\"max_safe\":%d,\"levels\":[\n",n,board.quads.size(),K);
    std::vector<Value> child;
    unsigned long long all=0,total_edges=0;
    for(int k=K;k>=0;--k){
        Mapping A(path(k));std::vector<Value> current(A.size);
        std::array<unsigned long long,65> histogram{};unsigned long long terminals=0,edges=0;
        if(k==K){histogram[0]=terminals=A.size;for(auto& v:current)v.terminal=v.forced=u64(1)<<k;}
        else {
            Mapping B(path(k+1));if(child.size()!=B.size)return 5;
            #pragma omp parallel for schedule(dynamic,4096) reduction(+:terminals,edges)
            for(long long i=0;i<(long long)A.size;++i){
                u64 s=A.data[i],blocked=0;
                for(u64 t=s;t;t&=t-1){int a=__builtin_ctzll(t);
                    for(u64 u=t&(t-1);u;u&=u-1){int b=__builtin_ctzll(u);
                        for(u64 v=u&(u-1);v;v&=v-1)blocked|=completion[a][b][__builtin_ctzll(v)];}}
                u64 legal=board.full&~s&~blocked,seen=0;
                u64 all_t=0,all_w=~u64(0),zero_t=0,zero_w=0;
                edges+=__builtin_popcountll(legal);if(!legal)++terminals;
                for(u64 t=legal;t;t&=t-1){u64 c=s|(t&-t);
                    auto ptr=std::lower_bound(B.data,B.data+B.size,c);
                    if(ptr==B.data+B.size||*ptr!=c){fprintf(stderr,"missing child\n");exit(6);}
                    Value v=child[ptr-B.data];unsigned g=v.g;if(g>=64)exit(7);seen|=u64(1)<<g;
                    all_t|=v.terminal;all_w&=v.forced;
                    if(!g){zero_t|=v.terminal;zero_w|=v.forced;}}
                Value result;
                result.g=__builtin_ctzll(~seen);
                if(!legal)result.terminal=result.forced=u64(1)<<k;
                else if(result.g){result.terminal=zero_t;result.forced=zero_w;}
                else {result.terminal=all_t;result.forced=all_w;}
                if(!result.terminal || (result.forced&~result.terminal))exit(8);
                const u64 parity=(k+bool(result.g))%2 ? 0xaaaaaaaaaaaaaaaaULL:0x5555555555555555ULL;
                if(result.terminal&~parity)exit(9);
                current[i]=result;
            }
            for(Value v:current)++histogram[v.g];
        }
        fprintf(out,"%s{\"k\":%d,\"states\":%zu,\"terminals\":%llu,\"edges\":%llu,\"histogram\":{",k==K?"":",\n",k,A.size,terminals,edges);
        bool first=true;for(int g=0;g<=64;++g)if(histogram[g]){fprintf(out,"%s\"%d\":%llu",first?"":",",g,histogram[g]);first=false;}
        fprintf(out,"}");
        if(k<=3){fprintf(out,",\"values\":[");for(size_t i=0;i<A.size;++i)fprintf(out,"%s[%llu,%u,%llu,%llu]",i?",":"",(unsigned long long)A.data[i],current[i].g,(unsigned long long)current[i].terminal,(unsigned long long)current[i].forced);fprintf(out,"]");}
        fprintf(out,"}");fflush(out);
        fprintf(stderr,"k=%d states=%zu P=%llu terminals=%llu edges=%llu\n",k,A.size,histogram[0],terminals,edges);fflush(stderr);
        all+=A.size;total_edges+=edges;child.swap(current);
    }
    fprintf(out,"\n],\"total_states\":%llu,\"total_edges\":%llu}\n",all,total_edges);fclose(out);
}
