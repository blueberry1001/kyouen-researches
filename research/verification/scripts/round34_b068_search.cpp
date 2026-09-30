// Original B068 requires BOTH degree sequence and exact adjacency spectrum.
// Characteristic polynomials are exact via integer traces/Newton identities.
#include "kc_core.h"
#include <algorithm>
#include <fstream>
#include <map>
#include <sstream>
#include <unordered_set>
using U=uint64_t;
struct Record{U s,L,graph;int g;};
struct Search{
    kc::Board B;int cap;std::ofstream out;bool found=false;uint64_t checked=0,pure=0,unique=0;
    std::unordered_set<U> seen;std::map<std::string,Record> buckets;
    void record(const Record&r){out<<"{\"S_mask\":"<<r.s<<",\"L_mask\":"<<r.L<<",\"graph_compressed\":"<<r.graph<<",\"g\":"<<r.g<<"}";}
    void examine(U s){
        ++checked;U L=kc::legal_mask(B,s);int m=__builtin_popcountll(L);if(m<2||m>cap)return;
        std::vector<int> ids;int idx[64];std::fill(idx,idx+64,-1);for(U x=L;x;x&=x-1){int p=__builtin_ctzll(x);idx[p]=ids.size();ids.push_back(p);}
        std::vector<int> raw;for(U q:B.quads){U r=q&~s;if(r&~L)continue;int e=0;for(U x=r;x;x&=x-1)e|=1<<idx[__builtin_ctzll(x)];raw.push_back(e);}
        std::vector<int> pairs;for(int r:raw)if(__builtin_popcount(r)==2)pairs.push_back(r);
        std::sort(pairs.begin(),pairs.end());pairs.erase(std::unique(pairs.begin(),pairs.end()),pairs.end());if(pairs.empty())return;
        for(int r:raw)if(__builtin_popcount(r)>2){bool redundant=false;for(int e:pairs)if((r&e)==e){redundant=true;break;}if(!redundant)return;}
        ++pure;int A[10][10]{},deg[10]{};U graph=0;int bit=0;
        for(int i=0;i<m;++i)for(int j=i+1;j<m;++j){bool edge=std::binary_search(pairs.begin(),pairs.end(),(1<<i)|(1<<j));if(edge){graph|=U(1)<<bit;A[i][j]=A[j][i]=1;++deg[i];++deg[j];}++bit;}
        U key=graph|(U(m)<<56);if(!seen.insert(key).second)return;++unique;
        int full=(1<<m)-1;std::vector<uint8_t> unsafe(full+1),g(full+1);
        for(int e:pairs){int rest=full^e,x=rest;for(;;){unsafe[x|e]=1;if(!x)break;x=(x-1)&rest;}}
        for(int t=full;t>=0;--t)if(!unsafe[t]){U values=0;for(int x=full^t;x;x&=x-1){int c=t|(x&-x);if(!unsafe[c])values|=U(1)<<g[c];}g[t]=__builtin_ctzll(~values);}
        long long power[10][10]{},traces[11]{},coeff[11]{1};for(int i=0;i<m;++i)power[i][i]=1;
        for(int k=1;k<=m;++k){long long next[10][10]{};for(int i=0;i<m;++i)for(int j=0;j<m;++j)for(int z=0;z<m;++z)next[i][j]+=power[i][z]*A[z][j];
            for(int i=0;i<m;++i){traces[k]+=next[i][i];for(int j=0;j<m;++j)power[i][j]=next[i][j];}
            long long sum=0;for(int j=1;j<=k;++j)sum+=coeff[k-j]*traces[j];if(sum%k)exit(3);coeff[k]=-sum/k;
        }
        std::sort(deg,deg+m);std::ostringstream os;os<<m<<':';for(int i=0;i<m;++i)os<<deg[i]<<',';os<<':';for(int k=0;k<=m;++k)os<<coeff[k]<<',';
        Record r{s,L,graph,g[0]};auto [p,inserted]=buckets.emplace(os.str(),r);
        if(!inserted&&bool(p->second.g)!=bool(r.g)){found=true;out<<"{\"n\":"<<B.n<<",\"invariant_key\":\""<<os.str()<<"\",\"pair\":[";record(p->second);out<<',';record(r);out<<"],\"checked_before_witness\":"<<checked<<"}\n";}
    }
    void visit(U s,int p){examine(s);if(found)return;for(;p<B.V;++p)if(kc::can_add(B,s,p)){visit(s|(U(1)<<p),p+1);if(found)return;}}
};
int main(int argc,char**argv){if(argc!=4)return 1;Search S;kc::build_square(S.B,atoi(argv[1]));S.cap=atoi(argv[3]);if(S.cap>10)return 2;S.out.open(argv[2]);S.visit(0,0);
    fprintf(stderr,"n=%d considered=%llu pure_pair=%llu unique=%llu found=%d\n",S.B.n,(unsigned long long)S.checked,(unsigned long long)S.pure,(unsigned long long)S.unique,S.found);
    if(!S.found)S.out<<"{\"n\":"<<S.B.n<<",\"L_cap\":"<<S.cap<<",\"all_safe_sets_considered\":"<<S.checked<<",\"pure_pair_candidates\":"<<S.pure<<",\"unique_labeled_graphs\":"<<S.unique<<",\"witness\":null}\n";
}
