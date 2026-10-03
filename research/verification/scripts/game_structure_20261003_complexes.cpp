// Exhaustive minimal-forbidden-antichain census for hereditary placement games.
// Every singleton is legal; empty move set has misere value 1.
// Safe-mask bit s records whether vertex subset s is legal.
// Usage: binary [number of vertices, 1..6]
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <map>
#include <vector>
using U=uint64_t;
int n,N,M;std::vector<int>edges;std::vector<U>incompatible,supersets;
std::map<int,U>hist;std::map<U,U>failures;U count=0,anomalies=0;
std::array<std::array<int,64>,720>permutations;int nperm;
U canonical(U safe){U best=~U(0);for(int t=0;t<nperm;t++){U r=0,bits=safe;while(bits){int s=__builtin_ctzll(bits);bits&=bits-1;r|=U(1)<<permutations[t][s];}best=std::min(best,r);}return best;}
void visit(U rem,U unsafe){
 if(rem){int i=__builtin_ctzll(rem);visit(rem&~(U(1)<<i),unsafe);visit(rem&~incompatible[i],unsafe|supersets[i]);return;}
 ++count;U safe=~unsafe;if(n<6)safe&=(U(1)<<N)-1;
 unsigned char g[64],m[64];for(int s=N-1;s>=0;s--)if((safe>>s)&1){unsigned gs=0,ms=0;for(int p=0;p<n;p++)if(!(s>>p&1)){int c=s|(1<<p);if(safe>>c&1){gs|=1u<<g[c];ms|=1u<<m[c];}}g[s]=__builtin_ctz(~gs);m[s]=gs?__builtin_ctz(~ms):1;}
 ++hist[16*g[0]+m[0]];int tau=g[0]<2?1-g[0]:g[0];if(m[0]!=tau){++anomalies;failures[canonical(safe)]++;}
}
int main(int argc,char**argv){n=argc>1?atoi(argv[1]):6;assert(n>=1&&n<=6);N=1<<n;
 std::vector<int>perm(n);for(int i=0;i<n;i++)perm[i]=i;do{for(int s=0;s<N;s++){int t=0;for(int p=0;p<n;p++)if(s>>p&1)t|=1<<perm[p];permutations[nperm][s]=t;}nperm++;}while(std::next_permutation(perm.begin(),perm.end()));
 for(int s=0;s<N;s++)if(__builtin_popcount((unsigned)s)>=2)edges.push_back(s);
 M=edges.size();
 for(int s:edges){U inc=0,sup=0;for(int j=0;j<M;j++)if((s&edges[j])==s||(s&edges[j])==edges[j])inc|=U(1)<<j;for(int t=0;t<N;t++)if((s&t)==s)sup|=U(1)<<t;incompatible.push_back(inc);supersets.push_back(sup);}
 visit((U(1)<<M)-1,0);
 printf("{\"n\":%d,\"families\":%llu,\"anomalies\":%llu,\"pair_histogram\":[",n,(unsigned long long)count,(unsigned long long)anomalies);bool first=true;for(auto[p,c]:hist){printf("%s[%d,%d,%llu]",first?"":",",p/16,p%16,(unsigned long long)c);first=false;}printf("],\"exception_isomorphism_classes\":[");first=true;for(auto [s,c]:failures){printf("%s{\"safe_mask\":\"%llu\",\"labelings\":%llu}",first?"":",",(unsigned long long)s,(unsigned long long)c);first=false;}printf("]}\n");
}
