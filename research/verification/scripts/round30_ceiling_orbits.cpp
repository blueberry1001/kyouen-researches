// Research probe of original B326 on every safe state, using the retained
// round28 layers. Reuses validated file/geometry infrastructure, not results.
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
#include <climits>
#include <omp.h>
using kc::u64;
struct Mapping {
    int fd;size_t size;const u64* data;
    explicit Mapping(const std::string& path){
        fd=open(path.c_str(),O_RDONLY);if(fd<0){perror(path.c_str());exit(2);}
        struct stat st;if(fstat(fd,&st)||st.st_size%8)exit(3);size=st.st_size/8;
        data=size?static_cast<const u64*>(mmap(nullptr,st.st_size,PROT_READ,MAP_PRIVATE,fd,0)):nullptr;
        if(size&&data==MAP_FAILED){perror("mmap");exit(4);}
    }
    ~Mapping(){if(size)munmap(const_cast<u64*>(data),size*8);close(fd);}
};
struct Ceiling {uint8_t g=0,h=0;};
struct Counterexample {u64 mask,winning;int g,h,legal,stabilizer;};
int main(int argc,char** argv){
    if(argc!=4)return 1;int n=atoi(argv[1]);kc::Board B;kc::build_square(B,n);
    std::string dir=argv[2];auto path=[&](int k){return dir+"/level_"+std::to_string(k)+".occ";};
    int K=0;while(access(path(K+1).c_str(),R_OK)==0)++K;
    int action[8][64];for(int p=0;p<B.V;++p){int x=p%n,y=p/n;
        int xx[8]={x,n-1-y,n-1-x,y,n-1-x,x,y,n-1-y};
        int yy[8]={y,x,n-1-y,n-1-x,y,n-1-y,x,n-1-x};
        for(int z=0;z<8;++z)action[z][p]=xx[z]+n*yy[z];}
    static u64 completion[64][64][64]{};
    for(u64 q:B.quads){int p[4],i=0;for(u64 x=q;x;x&=x-1)p[i++]=__builtin_ctzll(x);
        for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];completion[a[0]][a[1]][a[2]]|=u64(1)<<p[skip];}}
    std::vector<Ceiling> child;FILE* out=fopen(argv[3],"w");if(!out)return 2;
    fprintf(out,"{\"n\":%d,\"levels\":[",n);
    for(int k=K;k>=0;--k){Mapping A(path(k));std::vector<Ceiling> current(A.size);
        unsigned long long ceiling_count=0,symmetric_count=0;int minimum_margin[65];std::fill_n(minimum_margin,65,INT_MAX);
        std::vector<Counterexample> failures;
        if(k<K){Mapping N(path(k+1));
            #pragma omp parallel
            {
                unsigned long long count=0,sym=0;int margin[65];std::fill_n(margin,65,INT_MAX);
                std::vector<Counterexample> local;
                #pragma omp for schedule(dynamic,4096)
                for(long long i=0;i<(long long)A.size;++i){u64 s=A.data[i],blocked=0;
                    for(u64 x=s;x;x&=x-1){int a=__builtin_ctzll(x);for(u64 y=x&(x-1);y;y&=y-1){int b=__builtin_ctzll(y);for(u64 z=y&(y-1);z;z&=z-1)blocked|=completion[a][b][__builtin_ctzll(z)];}}
                    u64 legal=B.full&~s&~blocked,seen=0,winning=0;int h=0;
                    for(u64 x=legal;x;x&=x-1){int p=__builtin_ctzll(x);u64 c=s|(u64(1)<<p);auto ptr=std::lower_bound(N.data,N.data+N.size,c);
                        if(ptr==N.data+N.size||*ptr!=c)exit(3);Ceiling v=child[ptr-N.data];seen|=u64(1)<<v.g;h=std::max(h,int(v.h)+1);if(!v.g)winning|=u64(1)<<p;}
                    int g=__builtin_ctzll(~seen);current[i]={uint8_t(g),uint8_t(h)};
                    if(g!=h)continue;int nl=__builtin_popcountll(legal);margin[h]=std::min(margin[h],nl-h);
                    if(g<3)continue;++count;
                    int stabilizer[8],ng=0;
                    for(int z=0;z<8;++z){u64 image=0;for(u64 x=s;x;x&=x-1)image|=u64(1)<<action[z][__builtin_ctzll(x)];if(image==s)stabilizer[ng++]=z;}
                    if(ng<4)continue;++sym;bool small=false;
                    for(u64 x=winning;x;x&=x-1){int p=__builtin_ctzll(x);u64 orbit=0;for(int j=0;j<ng;++j)orbit|=u64(1)<<action[stabilizer[j]][p];if(__builtin_popcountll(orbit)<=2){small=true;break;}}
                    if(!small)local.push_back({s,winning,g,h,nl,ng});
                }
                #pragma omp critical
                {ceiling_count+=count;symmetric_count+=sym;for(int h=0;h<=64;++h)minimum_margin[h]=std::min(minimum_margin[h],margin[h]);failures.insert(failures.end(),local.begin(),local.end());}
            }
        }else minimum_margin[0]=0;
        std::sort(failures.begin(),failures.end(),[](auto a,auto b){return a.mask<b.mask;});
        fprintf(out,"%s{\"k\":%d,\"states\":%zu,\"ceiling_g_ge3\":%llu,\"stabilizer_ge4\":%llu,\"min_legal_minus_h\":{",k==K?"":",",k,A.size,ceiling_count,symmetric_count);
        bool first=true;for(int h=0;h<=64;++h)if(minimum_margin[h]!=INT_MAX){fprintf(out,"%s\"%d\":%d",first?"":",",h,minimum_margin[h]);first=false;}fprintf(out,"},\"counterexamples\":[");
        for(size_t j=0;j<failures.size();++j){auto a=failures[j];fprintf(out,"%s{\"mask\":%llu,\"g\":%d,\"h\":%d,\"winning_mask\":%llu,\"legal_count\":%d,\"stabilizer_size\":%d}",j?",":"",(unsigned long long)a.mask,a.g,a.h,(unsigned long long)a.winning,a.legal,a.stabilizer);}fprintf(out,"]}");fflush(out);
        fprintf(stderr,"k=%d ceiling=%llu stab>=4=%llu counter=%zu\n",k,ceiling_count,symmetric_count,failures.size());fflush(stderr);child.swap(current);
    }
    fprintf(out,"]}\n");fclose(out);
}
