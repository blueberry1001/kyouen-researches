// B349: geometric realizations of the nine possible nontrivial five-vertex
// minimal residual families containing a four-edge. Does not weaken R.
#include "kc_core.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <map>
#include <string>
using U=uint64_t;
int solve(const std::vector<int>&edges){int full=31;uint8_t unsafe[32]{},g[32]{};
    for(int e:edges){int rest=full^e,x=rest;for(;;){unsafe[x|e]=1;if(!x)break;x=(x-1)&rest;}}
    for(int t=31;t>=0;--t)if(!unsafe[t]){U seen=0;for(int p=0;p<5;++p)if(!(t&(1<<p))&&!unsafe[t|(1<<p)])seen|=U(1)<<g[t|(1<<p)];g[t]=__builtin_ctzll(~seen);}return g[0];}
struct Witness{U s;std::vector<int>ids,edges;int full,approx;unsigned long long count=0;};
struct Search{
    kc::Board B;unsigned long long checked=0,candidates=0;std::map<std::string,Witness> types;std::vector<U> completion;
    size_t key(int a,int b,int c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);return (a*B.V+b)*B.V+c;}
    void prepare(){completion.assign(B.V*B.V*B.V,0);for(U q:B.quads){int p[4],i=0;for(U x=q;x;x&=x-1)p[i++]=__builtin_ctzll(x);for(int skip=0;skip<4;++skip){int a[3],j=0;for(int z=0;z<4;++z)if(z!=skip)a[j++]=p[z];completion[key(a[0],a[1],a[2])]|=U(1)<<p[skip];}}}
    U after(U s,U legal,int p){legal&=~(U(1)<<p);for(U x=s;x;x&=x-1){int a=__builtin_ctzll(x);for(U y=x&(x-1);y;y&=y-1)legal&=~completion[key(a,__builtin_ctzll(y),p)];}return legal;}
    void examine(U s,U L){++checked;if(__builtin_popcountll(L)!=5)return;
        std::vector<int>ids;int index[64];std::fill(index,index+64,-1);for(U x=L;x;x&=x-1){int p=__builtin_ctzll(x);index[p]=ids.size();ids.push_back(p);}
        std::vector<int>raw;for(U q:B.quads){U r=q&~s;if(r&~L)continue;int e=0;for(U x=r;x;x&=x-1)e|=1<<index[__builtin_ctzll(x)];raw.push_back(e);}
        std::sort(raw.begin(),raw.end());raw.erase(std::unique(raw.begin(),raw.end()),raw.end());
        std::vector<int>edges;for(int a:raw){bool minimal=true;for(int b:raw)if(b!=a&&(b&a)==b){minimal=false;break;}if(minimal)edges.push_back(a);}
        int nq=0,nt=0,np=0,quad=0;std::vector<int>lower;for(int e:edges){int r=__builtin_popcount(e);nq+=r==4;nt+=r==3;np+=r==2;if(r==4)quad=e;else lower.push_back(e);}
        if(!np||!nq)return;++candidates;std::string id;
        if(nq==1){int outside=31^quad;for(int e:edges)if(__builtin_popcount(e)<4&&!(e&outside))exit(4);
            id="q1-d"+std::to_string(np)+"-t"+std::to_string(nt);}
        else{if(nq!=2||np!=1||nt)exit(5);id="q2";}
        int g=solve(edges),ga=solve(lower);if(g==ga)exit(6);
        auto p=types.find(id);if(p==types.end())types.emplace(id,Witness{s,ids,edges,g,ga,1});else++p->second.count;
    }
    void visit(U s,U legal,int first){examine(s,legal);for(U x=legal&(~U(0)<<first);x;x&=x-1){int p=__builtin_ctzll(x);visit(s|(U(1)<<p),after(s,legal,p),p+1);}}
};
int main(int argc,char**argv){if(argc!=3)return 1;Search S;kc::build_square(S.B,atoi(argv[1]));S.prepare();S.visit(0,S.B.full,0);std::ofstream out(argv[2]);
    out<<"{\"n\":"<<S.B.n<<",\"all_safe_sets_considered\":"<<S.checked<<",\"legal_size\":5,\"nontrivial_four_edge_candidates\":"<<S.candidates<<",\"types\":[";bool first=true;
    for(auto [id,w]:S.types){out<<(first?"":",")<<"{\"type\":\""<<id<<"\",\"count\":"<<w.count<<",\"S_mask\":"<<w.s<<",\"L_ids\":[";for(size_t i=0;i<w.ids.size();++i)out<<(i?",":"")<<w.ids[i];out<<"],\"minimal_edges_compressed\":[";for(size_t i=0;i<w.edges.size();++i)out<<(i?",":"")<<w.edges[i];out<<"],\"g_full\":"<<w.full<<",\"g_up_to_three\":"<<w.approx<<"}";first=false;}
    out<<"]}\n";fprintf(stderr,"n=%d checked=%llu candidates=%llu types=%zu\n",S.B.n,S.checked,S.candidates,S.types.size());
}
