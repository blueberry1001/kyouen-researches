// Independent certificate checker. Shares no implementation with search.
// Geometry: permutation expansion of the original 4x4 integer determinant.
// Legal moves: union of all completions of occupied triples, reconstructed
// from the entire forbidden family, without incremental next-legal updates.
// Independent verifier for a pruned, unordered 8x8 misere certificate.
// Reports the full initial-move classification iff all first classes occur.
// Usage: checker 8 pn certificate.bin
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
using U=uint64_t;
void require(bool x,const char*message){if(!x)throw std::runtime_error(message);}
int main(int argc,char**argv){
 require(argc==4,"usage: check n pairs|pn certificate.bin");
 int n=std::stoi(argv[1]),v=n*n;bool pn=std::string(argv[2])=="pn";
 require(n==8&&pn,"this checker requires n=8 pn");require(pn||std::string(argv[2])=="pairs","mode");
 U all=v==64?~U(0):(U(1)<<v)-1;
 std::vector<U> quads,finish(v*v*v);
 std::array<std::array<long long,4>,64>rows{};
 for(int p=0;p<v;p++){int x=p%n,y=p/n;rows[p]={x*x+y*y,x,y,1};}
 for(int a=0;a<v;a++)for(int b=a+1;b<v;b++)for(int c=b+1;c<v;c++)for(int d=c+1;d<v;d++){
  std::array<int,4>q{a,b,c,d},perm{0,1,2,3};long long det=0;
  do{int inversions=0;long long product=1;for(int i=0;i<4;i++){product*=rows[q[i]][perm[i]];for(int j=0;j<i;j++)inversions+=perm[j]>perm[i];}det+=(inversions&1)?-product:product;}while(std::next_permutation(perm.begin(),perm.end()));
  if(det)continue;
  U mask=0;for(int p:q)mask|=U(1)<<p;quads.push_back(mask);
  for(int z=0;z<4;z++){std::array<int,3>t{};int j=0;for(int i=0;i<4;i++)if(i!=z)t[j++]=q[i];finish[(t[0]*v+t[1])*v+t[2]]|=U(1)<<q[z];}
 }
 std::array<std::array<U,64>,8> transform{};
 for(int t=0;t<8;t++)for(int p=0;p<v;p++){
  int x=p%n,y=p/n;if(t>=4)x=n-1-x;for(int k=0;k<t%4;k++){int old=x;x=n-1-y;y=old;}transform[t][p]=U(1)<<(y*n+x);
 }
 auto canon=[&](U s){U answer=s;for(int t=1;t<8;t++){U r=0,m=s;while(m){int p=__builtin_ctzll(m);m&=m-1;r|=transform[t][p];}answer=std::min(answer,r);}return answer;};
 std::ifstream in(argv[3],std::ios::binary);require(bool(in),"open certificate");
 in.seekg(0,std::ios::end);size_t bytes=in.tellg();in.seekg(0);size_t stride=pn?9:10;require(bytes%stride==0,"record size");
 std::unordered_map<U,uint16_t>values;values.reserve(bytes/stride+1);
 while(in.peek()!=EOF){U s;in.read((char*)&s,8);int a=in.get(),b=pn?0:in.get();require(a>=0&&b>=0,"truncated record");require((s&~all)==0,"point outside board");require(!pn||a<=1,"outcome not boolean");require(pn||(a<64&&b<64),"mex out of bit range");require(!pn||canon(s)==s,"noncanonical pn state");require(values.emplace(s,a+256*b).second,"duplicate certificate record");}
 require(values.count(0),"missing root");
 uint64_t edges=0,terminal=0;int root=values.at(0);std::vector<int>winning,losing;std::array<int,64>first_outcomes{};first_outcomes.fill(-1);int known_first=0;
 for(auto &[s,value]:values){
  std::vector<int>points;U m=s;while(m){int p=__builtin_ctzll(m);m&=m-1;points.push_back(p);}U blocked=0;
  for(size_t a=0;a<points.size();a++)for(size_t b=a+1;b<points.size();b++)for(size_t c=b+1;c<points.size();c++)blocked|=finish[(points[a]*v+points[b])*v+points[c]];
  require(!(blocked&s),"unsafe certificate state");U legal=all&~s&~blocked;
  if(!legal){++terminal;require(value==(pn?1:256),"incorrect terminal label");continue;}
  U seen=0,seenm=0;bool has_losing=false;
  while(legal){int p=__builtin_ctzll(legal);legal&=legal-1;U child=s|(U(1)<<p);if(pn)child=canon(child);auto it=values.find(child);
   if(pn){if(value==0)require(it!=values.end()&&it->second==1,"P node missing N child");else if(it!=values.end()&&it->second==0)has_losing=true;}
   else{require(it!=values.end(),"missing child (incomplete census)");seen|=U(1)<<(it->second&255);seenm|=U(1)<<(it->second>>8);}
   ++edges;
  }
  if(pn){require(value==0||has_losing,"N node lacks P witness");}
  else{require((value&255)==__builtin_ctzll(~seen),"normal mex mismatch");require((value>>8)==__builtin_ctzll(~seenm),"misere mex mismatch");}
 }
 for(int p=0;p<v;p++){U key=U(1)<<p;if(pn)key=canon(key);auto it=values.find(key);if(it!=values.end()){first_outcomes[p]=it->second;known_first++;if(it->second==0)winning.push_back(p);else losing.push_back(p);}}
 printf("{\"n\":%d,\"mode\":\"%s\",\"verified\":true,\"forbidden\":%zu,\"records\":%zu,\"terminal_records\":%llu,\"legal_edges_checked\":%llu,\"empty_normal\":%d,\"empty_misere\":%d,\"all_first_moves_classified\":%s,\"misere_winning_first_moves_certified\":[",n,pn?"pn":"pairs",quads.size(),values.size(),(unsigned long long)terminal,(unsigned long long)edges,pn?-1:root&255,pn?root:root>>8,known_first==64?"true":"false");
 for(size_t i=0;i<winning.size();i++)printf("%s%d",i?",":"",winning[i]);
 printf("],\"misere_losing_first_moves_certified\":[");
 for(size_t i=0;i<losing.size();i++)printf("%s%d",i?",":"",losing[i]);
 printf("],\"first_move_child_outcomes\":[");
 for(int p=0;p<64;p++)printf("%s%d",p?",":"",first_outcomes[p]);
 printf("]}\n");
}
