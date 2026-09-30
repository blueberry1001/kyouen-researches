// Exact standard P/N byte tables for accelerated single-edge removal research.
// Reads the independently validated round28 safe-set layers.
#include "kc_core.h"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
using U=uint64_t;
struct File {
    int fd;size_t count;const U* masks;
    explicit File(std::string path){fd=open(path.c_str(),O_RDONLY);if(fd<0)exit(2);struct stat st;if(fstat(fd,&st)||st.st_size%8)exit(3);count=st.st_size/8;masks=static_cast<const U*>(mmap(nullptr,st.st_size,PROT_READ,MAP_PRIVATE,fd,0));if(masks==MAP_FAILED)exit(4);}
    ~File(){munmap(const_cast<U*>(masks),count*8);close(fd);}
};
int main(int argc,char**argv){
    if(argc!=3)return 1;int n=atoi(argv[1]);kc::Board B;kc::build_square(B,n);std::string dir=argv[2];
    auto path=[&](int k){return dir+"/level_"+std::to_string(k)+".occ";};int K=0;while(access(path(K+1).c_str(),R_OK)==0)++K;
    static U completion[64][64][64]{};
    for(U q:B.quads){int p[4],i=0;for(U x=q;x;x&=x-1)p[i++]=__builtin_ctzll(x);for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];completion[a[0]][a[1]][a[2]]|=U(1)<<p[skip];}}
    std::vector<uint8_t> child;
    for(int k=K;k>=0;--k){File A(path(k));std::vector<uint8_t> current(A.count);unsigned long long np=0;
        if(k<K){File C(path(k+1));
            #pragma omp parallel for schedule(dynamic,4096)
            for(long long i=0;i<(long long)A.count;++i){U s=A.masks[i],blocked=0;
                for(U x=s;x;x&=x-1){int a=__builtin_ctzll(x);for(U y=x&(x-1);y;y&=y-1){int b=__builtin_ctzll(y);for(U z=y&(y-1);z;z&=z-1)blocked|=completion[a][b][__builtin_ctzll(z)];}}
                U legal=B.full&~s&~blocked;
                for(U x=legal;x;x&=x-1){U c=s|(x&-x);auto ptr=std::lower_bound(C.masks,C.masks+C.count,c);if(ptr==C.masks+C.count||*ptr!=c)exit(5);if(!child[ptr-C.masks]){current[i]=1;break;}}
            }
        }
        for(auto g:current)np+=!g;
        std::string output=dir+"/standard_"+std::to_string(k)+".pn";FILE*f=fopen(output.c_str(),"wb");if(!f||fwrite(current.data(),1,current.size(),f)!=current.size())return 6;fclose(f);
        fprintf(stderr,"standard k=%d states=%zu P=%llu\n",k,A.count,np);fflush(stderr);child.swap(current);
    }
}
