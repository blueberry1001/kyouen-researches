// Original B345: a sole minimal triple changes a nontrivial clique-union game.
// All residual constraints are first restricted to initially legal points and
// inclusion-minimized. Pure isolated-point games are excluded.
#include "kc_core.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <unordered_set>
using U=uint64_t;
struct Value{int g;U winners;};
Value solve(int m,const std::vector<int>&edges,int omitted){
    int full=(1<<m)-1;std::vector<uint8_t> unsafe(full+1),g(full+1);
    for(int e:edges)if(e!=omitted){int rest=full^e,x=rest;for(;;){unsafe[x|e]=1;if(!x)break;x=(x-1)&rest;}}
    for(int s=full;s>=0;--s)if(!unsafe[s]){U seen=0;for(int x=full^s;x;x&=x-1){int c=s|(x&-x);if(!unsafe[c])seen|=U(1)<<g[c];}g[s]=__builtin_ctzll(~seen);}
    U winners=0;for(int p=0;p<m;++p)if(!g[1<<p])winners|=U(1)<<p;
    return {g[0],winners};
}
struct Search{
    kc::Board B;int cap;bool sole;uint64_t checked=0,candidates=0,deletions=0;std::ofstream out;bool found=false;
    void examine(U s){
        ++checked;U L=kc::legal_mask(B,s);int m=__builtin_popcountll(L);if(m>cap||m<3)return;
        std::vector<int> ids;int idx[64];std::fill(idx,idx+64,-1);for(U x=L;x;x&=x-1){int p=__builtin_ctzll(x);idx[p]=ids.size();ids.push_back(p);}
        std::vector<int> raw;for(U q:B.quads){U r=q&~s;if(r&~L)continue;int e=0;for(U x=r;x;x&=x-1)e|=1<<idx[__builtin_ctzll(x)];raw.push_back(e);}
        std::sort(raw.begin(),raw.end());raw.erase(std::unique(raw.begin(),raw.end()),raw.end());
        std::sort(raw.begin(),raw.end(),[](int a,int b){int x=__builtin_popcount(a),y=__builtin_popcount(b);return x!=y?x<y:a<b;});
        std::vector<int> edges;for(int a:raw){bool minimal=true;for(int b:edges)if((a&b)==b){minimal=false;break;}if(minimal)edges.push_back(a);}
        int triples=0;bool nontrivial=false;for(int e:edges){triples+=__builtin_popcount(e)==3;nontrivial|=__builtin_popcount(e)==2;}
        if(!nontrivial||triples!=1)return;
        std::vector<int> adj(m,0);
        for(int e:edges){int rank=__builtin_popcount(e);if(rank==4)return;
            if(rank==2){int a=__builtin_ctz(e),b=__builtin_ctz(e&(e-1));adj[a]|=1<<b;adj[b]|=1<<a;}}
        for(int a=0;a<m;++a)for(int b=a+1;b<m;++b)if(adj[a]&(1<<b))
            if((adj[a]|(1<<a))!=(adj[b]|(1<<b)))return;
        ++candidates;auto a=solve(m,edges,-1);
        for(int e:edges)if(__builtin_popcount(e)==3){++deletions;auto b=solve(m,edges,e);if(a.g==b.g)continue;
            found=true;out<<"{\"n\":"<<B.n<<",\"S_mask\":"<<s<<",\"L_ids\":[";
            for(int i=0;i<m;++i)out<<(i?",":"")<<ids[i];out<<"],\"minimal_edges\":[";
            for(size_t i=0;i<edges.size();++i)out<<(i?",":"")<<edges[i];
            out<<"],\"removed_compressed_mask\":"<<e<<",\"g_full\":"<<a.g<<",\"g_minus\":"<<b.g<<",\"win_full_compressed\":"<<a.winners<<",\"win_minus_compressed\":"<<b.winners<<",\"triple_count\":"<<triples<<",\"states_considered_before_witness\":"<<checked<<"}\n";
            fprintf(stderr,"FOUND n=%d mask=%llu L=%d triples=%d g=%d->%d\n",B.n,(unsigned long long)s,m,triples,a.g,b.g);return;
        }
    }
    void visit(U s,int first){examine(s);if(found)return;for(int p=first;p<B.V;++p)if(kc::can_add(B,s,p)){visit(s|(U(1)<<p),p+1);if(found)return;}}
};
int main(int argc,char**argv){if(argc!=5)return 1;Search S;kc::build_square(S.B,atoi(argv[1]));S.cap=atoi(argv[3]);S.sole=atoi(argv[4]);S.out.open(argv[2]);S.visit(0,0);
    fprintf(stderr,"checked=%llu candidates=%llu deletions=%llu found=%d\n",(unsigned long long)S.checked,(unsigned long long)S.candidates,(unsigned long long)S.deletions,S.found);
    if(!S.found)S.out<<"{\"n\":"<<S.B.n<<",\"L_cap\":"<<S.cap<<",\"sole_three_edge\":"<<S.sole<<",\"all_safe_sets_checked\":"<<S.checked<<",\"candidates\":"<<S.candidates<<",\"single_deletions_checked\":"<<S.deletions<<",\"witness\":null}\n";
}
