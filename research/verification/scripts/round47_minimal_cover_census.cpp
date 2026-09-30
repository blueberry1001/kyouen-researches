// Fresh geometry + complete existing safe layer: minimal-maximal cover census.
#include "kc_core.h"
#include <algorithm>
#include <fstream>
#include <cstdio>
using U=uint64_t;
int main(int argc,char**argv){
    if(argc!=5)return 1;int n=atoi(argv[1]),k=atoi(argv[2]);kc::Board B;kc::build_square(B,n);
    std::vector<U> completion(B.V*B.V*B.V);auto key=[&](int a,int b,int c){return (a*B.V+b)*B.V+c;};
    for(U q:B.quads){int ids[4],i=0;for(U x=q;x;x&=x-1)ids[i++]=__builtin_ctzll(x);
        for(int omit=0;omit<4;++omit){int t[3],j=0;for(int z=0;z<4;++z)if(z!=omit)t[j++]=ids[z];
            completion[key(t[0],t[1],t[2])]|=U(1)<<ids[omit];}}
    std::ifstream in(argv[3],std::ios::binary);if(!in)return 2;std::ofstream out(argv[4]);
    out<<"{\"n\":"<<n<<",\"layer_k\":"<<k<<",\"maximal_sets\":[";bool first=true;U s;uint64_t loaded=0,terminal=0;
    while(in.read((char*)&s,8)){
        ++loaded;if(__builtin_popcountll(s)!=k||(s&~B.full))return 3;
        int ids[64],count=0;for(U x=s;x;x&=x-1)ids[count++]=__builtin_ctzll(x);U blocked=0;
        for(int a=0;a<k;++a)for(int b=a+1;b<k;++b)for(int c=b+1;c<k;++c)blocked|=completion[key(ids[a],ids[b],ids[c])];
        if(blocked&s)return 4;if(B.full&~s&~blocked)continue;++terminal;
        int cover[64]{};for(int a=0;a<k;++a)for(int b=a+1;b<k;++b)for(int c=b+1;c<k;++c)
            for(U x=completion[key(ids[a],ids[b],ids[c])];x;x&=x-1)++cover[__builtin_ctzll(x)];
        int minimum=999,maximum=0;for(U x=B.full&~s;x;x&=x-1){int p=__builtin_ctzll(x);minimum=std::min(minimum,cover[p]);maximum=std::max(maximum,cover[p]);}
        out<<(first?"":",")<<"{\"S_mask\":"<<s<<",\"min_b\":"<<minimum<<",\"max_b\":"<<maximum<<"}";first=false;
    }
    if(!in.eof())return 5;out<<"],\"safe_layer_states_checked\":"<<loaded<<",\"terminal_count\":"<<terminal<<",\"input_processed_completely\":true}\n";
    fprintf(stderr,"n=%d k=%d layer=%llu maximal=%llu\n",n,k,(unsigned long long)loaded,(unsigned long long)terminal);
}
