// Independent decomposition enumeration: K on six vertices splits uniquely
// into (K0,K1) on five vertices, with empty in K1 subset K0 and all singletons
// in K0. No minimal-forbidden-antichain generator is used.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <map>
#include <unordered_map>
#include <vector>
using U=uint64_t;
struct Complex { uint32_t safe;unsigned char g,gm;std::array<uint16_t,5>links; };
std::vector<Complex> list;
void generate(int s,uint32_t mask){
 if(s==32){
  unsigned char g[32],gm[32];
  for(int t=31;t>=0;t--)if(mask>>t&1){unsigned gs=0,ms=0;bool move=false;for(int p=0;p<5;p++)if(!(t>>p&1)){int child=t|(1<<p);if(mask>>child&1){move=true;gs|=1u<<g[child];ms|=1u<<gm[child];}}g[t]=__builtin_ctz(~gs);gm[t]=move?__builtin_ctz(~ms):1;}
  assert(gm[0]==(g[0]<2?1-g[0]:g[0]));
  Complex c{mask,g[0],gm[0],{}};
  for(int p=0;p<5;p++)for(int t=0;t<32;t++)if((t>>p&1)&&(mask>>t&1)){int reduced=(t&((1<<p)-1))|((t>>(p+1))<<p);c.links[p]|=1u<<reduced;}
  list.push_back(c);return;
 }
 generate(s+1,mask);bool allowed=true;for(int p=0;p<5;p++)if((s>>p&1)&&!(mask>>(s^(1<<p))&1))allowed=false;
 if(allowed)generate(s+1,mask|(uint32_t(1)<<s));
}
int main(){
 generate(1,1);std::unordered_map<uint32_t,unsigned char>g5;g5.reserve(list.size()*2);for(auto&k:list)g5.emplace(k.safe,k.g);
 U families=0;std::map<int,U>hist;int full5=0;uint32_t singles=0;for(int p=0;p<5;p++)singles|=uint32_t(1)<<(1<<p);
 for(auto&a:list)if((a.safe&singles)==singles){++full5;for(auto&b:list)if((a.safe&b.safe)==b.safe){++families;unsigned gs=1u<<b.g,ms=1u<<b.gm;for(int p=0;p<5;p++){
   uint32_t link=uint32_t(a.links[p])|(uint32_t(b.links[p])<<16);auto it=g5.find(link);assert(it!=g5.end());int g=it->second,gm=g<2?1-g:g;gs|=1u<<g;ms|=1u<<gm;
  }
  int g=__builtin_ctz(~gs),gm=__builtin_ctz(~ms);++hist[g*16+gm];
 }}
 printf("{\"method\":\"deletion_link_pairs\",\"verified\":true,\"complexes_on_five_allowing_absent_vertices\":%zu,\"full_vertex_complexes_on_five\":%d,\"families_on_six\":%llu,\"pair_histogram\":[",list.size(),full5,(unsigned long long)families);bool first=true;for(auto[p,c]:hist){printf("%s[%d,%d,%llu]",first?"":",",p/16,p%16,(unsigned long long)c);first=false;}printf("]}\n");
}
