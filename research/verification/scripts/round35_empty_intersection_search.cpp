// Seek a CARDINALITY-minimum (three-edge) flip with no common vertex, B524.
#include "kc_core.h"
#include <array>
#include <fstream>
#include <random>
#include <algorithm>
using U=uint64_t;
struct Solver{
    std::array<U,4> signature[65536]{},released{};uint32_t stamp[65536]{},epoch=0;uint8_t outcome[65536]{};
    bool safe(unsigned s){for(int j=0;j<4;++j)if(signature[s][j]&~released[j])return false;return true;}
    bool win(unsigned s){if(stamp[s]==epoch)return outcome[s];stamp[s]=epoch;bool value=false;
        for(unsigned x=65535^s;x;x&=x-1){unsigned c=s|(x&-x);if(safe(c)&&!win(c)){value=true;break;}}return outcome[s]=value;}
    bool run(std::array<int,3> ids){released={};for(int i:ids)released[i/64]|=U(1)<<(i%64);++epoch;return win(0);}
};
int main(int argc,char**argv){if(argc!=2)return 1;kc::Board B;kc::build_square(B,4);static Solver S;
    for(size_t i=0;i<B.quads.size();++i){unsigned q=B.quads[i],rest=65535^q,x=rest;for(;;){S.signature[x|q][i/64]|=U(1)<<(i%64);if(!x)break;x=(x-1)&rest;}}
    unsigned tried=0;std::ofstream out(argv[1]);bool found=false;
    auto test=[&](std::array<int,3> ids){std::sort(ids.begin(),ids.end());if(ids[0]==ids[1]||ids[1]==ids[2])return false;
        if(B.quads[ids[0]]&B.quads[ids[1]]&B.quads[ids[2]])return false;++tried;if(!S.run(ids))return false;
        out<<"{\"n\":4,\"removed_indices\":["<<ids[0]<<','<<ids[1]<<','<<ids[2]<<"],\"removed_masks\":["<<B.quads[ids[0]]<<','<<B.quads[ids[1]]<<','<<B.quads[ids[2]]<<"],\"empty_outcome\":1,\"common_intersection\":0,\"eligible_trials_before_witness\":"<<tried<<"}\n";return true;};
    auto find=[&](U q){auto p=std::find(B.quads.begin(),B.quads.end(),q);if(p==B.quads.end())exit(2);return int(p-B.quads.begin());};
    int a=find((1<<3)|(1<<5)|(1<<9)|(1<<14)),b=find((1<<4)|(1<<5)|(1<<8)|(1<<9));
    for(int c=0;c<int(B.quads.size())&&!found;++c)found=test({a,b,c});
    std::mt19937 rng(20260930);for(int i=0;i<20000&&!found;++i)found=test({int(rng()%194),int(rng()%194),int(rng()%194)});
    fprintf(stderr,"empty intersection trials=%u found=%d\n",tried,found);
    if(!found)out<<"{\"n\":4,\"trials\":"<<tried<<",\"seed\":20260930,\"witness\":null}\n";
}
