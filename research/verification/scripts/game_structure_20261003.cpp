// Exact, uncapped normal and misere Grundy-pair census on n x n boards.
// Misere recurrence has terminal value 1; its zero test gives misere P/N.
// It is NOT a Sprague-Grundy value usable with xor in disjunctive sums.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <fstream>
#include <map>
#include <unordered_map>
#include <vector>
using U=uint64_t;
struct Val { unsigned char normal,misere; };
int n,V;
U full;
std::vector<U> completion;
std::unordered_map<U,Val> memo;
std::map<int,std::map<int,uint64_t>> hist;
std::map<int,std::map<int,U>> witness;
std::map<int,uint64_t> terminals;
U nextlegal(U s,U legal,int p);
std::unordered_map<U,unsigned char> pn;
size_t node_limit=15000000;
std::vector<std::array<int,64>> transformations;
U canonical(U s){U best=s;for(auto &t:transformations){U v=s,r=0;while(v){int p=__builtin_ctzll(v);v&=v-1;r|=U(1)<<t[p];}best=std::min(best,r);}return best;}
bool solve_pn(U s,U legal){U key=canonical(s);auto it=pn.find(key);if(it!=pn.end())return it->second;bool result=!legal;
 U l=legal;while(l){int p=__builtin_ctzll(l);l&=l-1;if(!solve_pn(s|(U(1)<<p),nextlegal(s,legal,p))){result=true;break;}}
 if(pn.size()>=node_limit)throw std::runtime_error("node limit: no completed result");
 pn.emplace(key,result);return result;
}
long long forbidden=0;
size_t ix(int a,int b,int c){return (a*V+b)*V+c;}
U nextlegal(U s,U legal,int p){
 U result=legal&~(U(1)<<p),a=s;
 while(a){int i=__builtin_ctzll(a);a&=a-1;U b=a;
  while(b){int j=__builtin_ctzll(b);b&=b-1;result&=~completion[ix(p,i,j)];}
 }
 return result;
}
Val solve(U s,U legal){
 auto it=memo.find(s);if(it!=memo.end())return it->second;
 Val r{0,1};
 if(legal){U mask=0,mis=0,l=legal;
  while(l){int p=__builtin_ctzll(l);l&=l-1;Val c=solve(s|(U(1)<<p),nextlegal(s,legal,p));mask|=U(1)<<c.normal;mis|=U(1)<<c.misere;}
  r.normal=__builtin_ctzll(~mask);r.misere=__builtin_ctzll(~mis);
 } else ++terminals[__builtin_popcountll(s)];
 memo.emplace(s,r);
 int k=__builtin_popcountll(s),pair=r.normal*64+r.misere;
 ++hist[k][pair];
 if(!witness[k].count(pair)||s<witness[k][pair])witness[k][pair]=s;
 return r;
}
long long determinant(int a,int b,int c,int d){
 long long ax=a%n-d%n,ay=a/n-d/n,bx=b%n-d%n,by=b/n-d/n,cx=c%n-d%n,cy=c/n-d/n;
 long long aa=ax*ax+ay*ay,bb=bx*bx+by*by,cc=cx*cx+cy*cy;
 return aa*(bx*cy-by*cx)-bb*(ax*cy-ay*cx)+cc*(ax*by-ay*bx);
}
int run(int argc,char**argv){
 n=argc>1?atoi(argv[1]):5;assert(n>=1&&n<=8);V=n*n;full=V==64?~U(0):(U(1)<<V)-1;
 completion.resize(V*V*V);
 for(int a=0;a<V;a++)for(int b=a+1;b<V;b++)for(int c=b+1;c<V;c++)for(int d=c+1;d<V;d++)if(!determinant(a,b,c,d)){
  ++forbidden;std::array<int,4>q{a,b,c,d};
  for(int z=0;z<4;z++){std::array<int,3>t{};int k=0;for(int j=0;j<4;j++)if(j!=z)t[k++]=q[j];do{completion[ix(t[0],t[1],t[2])]|=U(1)<<q[z];}while(std::next_permutation(t.begin(),t.end()));}
 }
 if(argc>2&&std::string(argv[2])=="pn"){
 for(int t=0;t<8;t++){std::array<int,64>a{};for(int p=0;p<V;p++){int x=p%n,y=p/n;if(t&4)std::swap(x,y);if(t&1)x=n-1-x;if(t&2)y=n-1-y;a[p]=y*n+x;}transformations.push_back(a);}
 if(argc>4)node_limit=std::stoull(argv[4]);
 pn.reserve(2000000);bool r=solve_pn(0,full);std::vector<int> winning;
 for(int p=0;p<V;p++)if(!solve_pn(U(1)<<p,full&~(U(1)<<p)))winning.push_back(p);
 printf("{\"n\":%d,\"mode\":\"misere_pn\",\"complete\":true,\"misere_first_wins\":%s,\"memo_size\":%zu,\"winning_first_moves\":[",n,r?"true":"false",pn.size());
 for(size_t j=0;j<winning.size();j++)printf("%s%d",j?",":"",winning[j]);
 printf("]}\n");
 if(argc>3){std::vector<std::pair<U,unsigned char>>data(pn.begin(),pn.end());std::sort(data.begin(),data.end());std::ofstream out(argv[3],std::ios::binary);for(auto [s,v]:data){out.write((char*)&s,8);out.put(v);}}
 return 0;}

 if(n>6)throw std::runtime_error("full pair census is limited to n<=6; use pn mode");
 memo.reserve(n==6?5500000:200000);
 Val root=solve(0,full);
 printf("{\n\"n\":%d,\"complete\":true,\"forbidden\":%lld,\"safe_sets\":%zu,\"empty\":[%d,%d],\n\"first_moves\":[",n,forbidden,memo.size(),root.normal,root.misere);
 for(int p=0;p<V;p++){Val r=memo.at(U(1)<<p);printf("%s[%d,%d]",p?",":"",r.normal,r.misere);}printf("],\n\"layers\":[");
 bool first=true;for(auto &[k,h]:hist){printf("%s{\"k\":%d,\"terminal\":%llu,\"pairs\":[",first?"":",",k,(unsigned long long)terminals[k]);first=false;bool f=true;
 for(auto &[pair,c]:h){printf("%s{\"g\":%d,\"gm\":%d,\"count\":%llu,\"witness\":%llu}",f?"":",",pair/64,pair%64,(unsigned long long)c,(unsigned long long)witness[k][pair]);f=false;}printf("]}");}
 printf("]\n}\n");
 if(argc>2){std::vector<std::pair<U,Val>> data(memo.begin(),memo.end());std::sort(data.begin(),data.end(),[](auto&a,auto&b){return a.first<b.first;});std::ofstream out(argv[2],std::ios::binary);for(auto [s,r]:data){out.write((char*)&s,8);out.put(r.normal);out.put(r.misere);}}
 return 0;
}
int main(int argc,char**argv){try{return run(argc,argv);}catch(const std::exception&e){fprintf(stderr,"Incomplete search: %s\n",e.what());return 2;}}
