// Original B065: search standard geometric residual games with no pair edges.
// Sorted DFS enumerates each safe set once. Larger legal sets are reported
// uncomputed; finite non-witnesses are never promoted to a general refutation.
#include "kc_core.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <map>
using U=uint64_t;
struct Search{
    kc::Board B;int cap;std::vector<U> completion;std::vector<std::vector<U>> pair_rest;
    uint64_t checked=0,candidates=0,uncomputed=0;bool found=false;std::ofstream out;
    std::map<int,uint64_t> legal_hist,g_hist;int maximum_g=0;
    size_t key(int a,int b,int c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);return (a*B.V+b)*B.V+c;}
    U after(U s,U legal,int p){legal&=~(U(1)<<p);for(U x=s;x;x&=x-1){int a=__builtin_ctzll(x);for(U y=x&(x-1);y;y&=y-1)legal&=~completion[key(a,__builtin_ctzll(y),p)];}return legal;}
    void prepare(){completion.assign(B.V*B.V*B.V,0);pair_rest.resize(B.V*B.V);
        for(U q:B.quads){int p[4],i=0;for(U x=q;x;x&=x-1)p[i++]=__builtin_ctzll(x);
            for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];completion[key(a[0],a[1],a[2])]|=U(1)<<p[skip];}
            for(int a=0;a<4;++a)for(int b=a+1;b<4;++b)pair_rest[p[a]*B.V+p[b]].push_back(q&~((U(1)<<p[a])|(U(1)<<p[b])));}
    }
    void examine(U s,U L){
        ++checked;int m=__builtin_popcountll(L);if(m<4||__builtin_popcountll(s)<2)return;
        for(U x=s;x;x&=x-1){int a=__builtin_ctzll(x);for(U y=x&(x-1);y;y&=y-1){int b=__builtin_ctzll(y);for(U r:pair_rest[a*B.V+b])if((r&L)==r)return;}}
        ++candidates;++legal_hist[m];if(m>cap){++uncomputed;return;}
        std::vector<int> ids;int index[64];std::fill(index,index+64,-1);for(U x=L;x;x&=x-1){int p=__builtin_ctzll(x);index[p]=ids.size();ids.push_back(p);}
        std::vector<int> edges;for(U q:B.quads){U r=q&~s;if(r&~L)continue;int e=0;for(U x=r;x;x&=x-1)e|=1<<index[__builtin_ctzll(x)];edges.push_back(e);}
        std::sort(edges.begin(),edges.end());edges.erase(std::unique(edges.begin(),edges.end()),edges.end());
        int full=(1<<m)-1;std::vector<uint8_t> unsafe(full+1),g(full+1);
        for(int e:edges){if(__builtin_popcount(e)<3)exit(3);int rest=full^e,x=rest;for(;;){unsafe[x|e]=1;if(!x)break;x=(x-1)&rest;}}
        for(int t=full;t>=0;--t)if(!unsafe[t]){U seen=0;for(int x=full^t;x;x&=x-1){int c=t|(x&-x);if(!unsafe[c])seen|=U(1)<<g[c];}g[t]=__builtin_ctzll(~seen);}
        ++g_hist[g[0]];maximum_g=std::max(maximum_g,int(g[0]));if(g[0]<4)return;
        found=true;out<<"{\"n\":"<<B.n<<",\"S_mask\":"<<s<<",\"L_ids\":[";for(int i=0;i<m;++i)out<<(i?",":"")<<ids[i];
        out<<"],\"g\":"<<int(g[0])<<",\"pair_edges\":0,\"states_considered_before_witness\":"<<checked<<"}\n";
    }
    void visit(U s,U legal,int first){examine(s,legal);if(found)return;U choices=legal&(~U(0)<<first);
        for(U x=choices;x;x&=x-1){int p=__builtin_ctzll(x);visit(s|(U(1)<<p),after(s,legal,p),p+1);if(found)return;}}
};
int main(int argc,char**argv){if(argc!=4)return 1;Search S;kc::build_square(S.B,atoi(argv[1]));S.cap=atoi(argv[3]);if(S.B.V>63||S.cap>20)return 2;S.prepare();S.out.open(argv[2]);S.visit(0,S.B.full,0);
    if(!S.found){S.out<<"{\"n\":"<<S.B.n<<",\"all_safe_sets_considered\":"<<S.checked<<",\"S_size_min\":2,\"L_size_min\":4,\"L_cap\":"<<S.cap<<",\"empty_pair_candidates\":"<<S.candidates<<",\"uncomputed_over_cap\":"<<S.uncomputed<<",\"max_computed_g\":"<<S.maximum_g<<",\"legal_size_histogram\":{";
        bool first=true;for(auto [m,c]:S.legal_hist){S.out<<(first?"":",")<<'"'<<m<<"\":"<<c;first=false;}S.out<<"},\"g_histogram\":{";first=true;for(auto [g,c]:S.g_hist){S.out<<(first?"":",")<<'"'<<g<<"\":"<<c;first=false;}S.out<<"},\"witness\":null}\n";}
    fprintf(stderr,"n=%d checked=%llu empty_pair_candidates=%llu overcap=%llu max_g=%d found=%d\n",S.B.n,(unsigned long long)S.checked,(unsigned long long)S.candidates,(unsigned long long)S.uncomputed,S.maximum_g,S.found);
}
