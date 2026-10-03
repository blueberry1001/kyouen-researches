// Bounded 9x9 misere experiment. No incomplete search is labelled P or N.
// 128-bit geometry; exact combinatorial ranks for occupied sets of size <=20.
// Tiny endgames preserve the complete family of safe subsets, not just pairs.
// Successful search is still provisional until its expanded proof is checked.
// Usage: binary proof.bin [seconds=800] [node-cap=130000000] [opening=40]
// Probe mode: binary --probe [samples=400] (JSONL for independent validation).
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
using U=uint64_t;using B=__uint128_t;
constexpr int N=9,V=N*N,K=20;constexpr U EMPTY=~U(0);
constexpr B ALL=(B(1)<<V)-1;
using Transforms=std::array<B,8>;
std::array<std::array<B,V>,8> transform{};
std::array<std::array<U,K+1>,V+1> choose{};
std::array<U,K+1> offsets{};
std::vector<B> finish(V*V*V);
std::vector<U> keys,wins,marked;
size_t slots=201326611,limit=130000000,used=0,proofsize=0,calls=0,tiny_calls=0;
size_t tiny_limit=2000000;
int first_order=40,forbidden_count=0;
double seconds=800;
auto started=std::chrono::steady_clock::now();
double elapsed(){return std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();}
void deadline(){if(elapsed()>seconds)throw std::runtime_error("wall time cap reached; UNKNOWN");}
int count(B s){return __builtin_popcountll(U(s))+__builtin_popcountll(U(s>>64));}
int take(B&s){int p=U(s)?__builtin_ctzll(U(s)):64+__builtin_ctzll(U(s>>64));s&=s-1;return p;}
B canonical(B s){B answer=s;for(int t=1;t<8;t++){B r=0,b=s;while(b)r|=transform[t][take(b)];answer=std::min(answer,r);}return answer;}
B canonical(const Transforms&t){return *std::min_element(t.begin(),t.end());}
Transforms extend(const Transforms&t,int p){Transforms r;for(int i=0;i<8;i++)r[i]=t[i]|transform[i][p];return r;}
U encode(B s){if(s&~ALL)throw std::runtime_error("rank outside board; UNKNOWN");int k=count(s);if(k>K)throw std::runtime_error("rank domain exceeded; UNKNOWN");U value=offsets[k];int j=1;while(s)value+=choose[take(s)][j++];if(value==EMPTY)throw std::runtime_error("rank sentinel collision; UNKNOWN");return value;}
size_t lookup(B s){U rank=encode(s),h=rank;h^=h>>30;h*=0xbf58476d1ce4e5b9ULL;h^=h>>27;h*=0x94d049bb133111ebULL;h^=h>>31;size_t i=h%slots;while(keys[i]!=EMPTY&&keys[i]!=rank){if(++i==slots)i=0;}return i;}
bool get(size_t i){return wins[i>>6]>>(i&63)&1;}
void save(size_t i,B s,bool win){if(keys[i]!=EMPTY)throw std::runtime_error("duplicate memo insertion");if(used>=limit)throw std::runtime_error("node cap reached; UNKNOWN");keys[i]=encode(s);if(win)wins[i>>6]|=U(1)<<(i&63);used++;if(used%5000000==0)fprintf(stderr,"memo %zu, elapsed %.3f, tiny calls %zu\n",used,elapsed(),tiny_calls);}
B nextlegal(B s,B legal,int p){B r=legal&~(B(1)<<p),a=s;while(a){int i=take(a);B b=a;while(b){int j=take(b);r&=~finish[(p*V+i)*V+j];}}return r;}
B legal_from_s(B s){B r=ALL&~s,a=s;while(a){int i=take(a);B b=a;while(b){int j=take(b);B c=b;while(c){int k=take(c);r&=~finish[(i*V+j)*V+k];}}}return r;}
std::array<std::array<U,64>,7> supersets{};
std::unordered_map<U,unsigned char> tiny_cache;
bool tiny(B s,B legal){
 tiny_calls++;int points[6],k=0;B b=legal;while(b)points[k++]=take(b);
 U forbidden=0;B blocked[6]{};B a=s;
 while(a){int i=take(a);B b=a;while(b){int j=take(b);for(int t=0;t<k;t++)blocked[t]|=finish[(points[t]*V+i)*V+j];}}
 for(int i=0;i<k;i++)for(int j=i+1;j<k;j++)if(blocked[i]>>points[j]&1)forbidden|=supersets[k][(1<<i)|(1<<j)];
 for(int i=0;i<k;i++)for(int j=i+1;j<k;j++)for(int t=j+1;t<k;t++){
  B comp=finish[(points[i]*V+points[j])*V+points[t]];int edge=(1<<i)|(1<<j)|(1<<t);
  if(comp&s)forbidden|=supersets[k][edge];
  for(int u=t+1;u<k;u++)if(comp>>points[u]&1)forbidden|=supersets[k][edge|(1<<u)];
 }
 U safe=(k==6?~U(0):(U(1)<<(1<<k))-1)&~forbidden;
 auto found=tiny_cache.find(safe);if(found!=tiny_cache.end())return found->second;
 bool win[64];for(int subset=(1<<k)-1;subset>=0;subset--)if(safe>>subset&1){bool result=false,move=false;for(int p=0;p<k;p++)if(!(subset>>p&1)){int child=subset|(1<<p);if(safe>>child&1){move=true;if(!win[child])result=true;}}win[subset]=!move||result;}
 // A full tiny cache only disables additional caching; it does not alter play.
 if(tiny_cache.size()<tiny_limit)tiny_cache.emplace(safe,win[0]);
 return win[0];
}
bool solve(const Transforms&t,B legal){
 if((++calls&16383)==0)deadline();
 B s=t[0];
 if(count(legal)<=6)return tiny(s,legal);
 B key=canonical(t);size_t slot=lookup(key);if(keys[slot]!=EMPTY)return get(slot);
 bool result=false;B remaining=legal;
 if(!s)remaining=B(1)<<first_order;
 while(remaining){int p=take(remaining);if(!solve(extend(t,p),nextlegal(s,legal,p))){result=true;break;}}
 if(!s&&!result){remaining=legal&~(B(1)<<first_order);while(remaining){int p=take(remaining);if(!solve(extend(t,p),nextlegal(s,legal,p))){result=true;break;}}}
 slot=lookup(key);save(slot,key,result);return result;
}
void export_proof(B input,std::ofstream&out){
 if((++calls&16383)==0)deadline();
 B s=canonical(input);size_t slot=lookup(s);
 if(keys[slot]==EMPTY){B l=legal_from_s(s);if(count(l)>6)throw std::runtime_error("proof state absent");save(slot,s,tiny(s,l));}
 if(marked[slot>>6]>>(slot&63)&1)return;
 marked[slot>>6]|=U(1)<<(slot&63);
 bool w=get(slot),witness=false;B legal=legal_from_s(s),remaining=legal;
 while(remaining){int p=take(remaining);B c=canonical(s|(B(1)<<p));size_t ci=lookup(c);bool cw;
  if(keys[ci]!=EMPTY)cw=get(ci);else{B cl=legal_from_s(c);if(count(cl)>6){if(w)continue;throw std::runtime_error("P child absent from proof memo");}cw=tiny(c,cl);}
  if(!w){if(!cw)throw std::runtime_error("P proof closure");export_proof(c,out);}else if(!cw){export_proof(c,out);witness=true;break;}
 }
 if(w&&legal&&!witness)throw std::runtime_error("N proof witness absent");
 U lo=U(s),hi=U(s>>64);out.write((char*)&lo,8);out.write((char*)&hi,8);out.put(w);proofsize++;
}
long long det(int a,int b,int c,int d){long long ax=a%N-d%N,ay=a/N-d/N,bx=b%N-d%N,by=b/N-d/N,cx=c%N-d%N,cy=c/N-d/N;return (ax*ax+ay*ay)*(bx*cy-by*cx)-(bx*bx+by*by)*(ax*cy-ay*cx)+(cx*cx+cy*cy)*(ax*by-ay*bx);}
void initialize(){
 for(int a=0;a<=V;a++){choose[a][0]=1;for(int b=1;b<=std::min(a,K);b++)choose[a][b]=(a?choose[a-1][b]:0)+(a?choose[a-1][b-1]:0);}
 for(int k=1;k<=K;k++)offsets[k]=offsets[k-1]+choose[V][k-1];
 // All ranks fit 63 bits; no truncated or probabilistic key is used.
 if(B(offsets[K])+choose[V][K]>=B(1)<<63)throw std::runtime_error("rank range assertion");
 for(int p=0;p<V;p++){int x=p%N,y=p/N;std::array<int,8>q{y*N+x,y*N+N-1-x,(N-1-y)*N+x,(N-1-y)*N+N-1-x,x*N+y,x*N+N-1-y,(N-1-x)*N+y,(N-1-x)*N+N-1-y};for(int t=0;t<8;t++)transform[t][p]=B(1)<<q[t];}
 for(int a=0;a<V;a++)for(int b=a+1;b<V;b++)for(int c=b+1;c<V;c++)for(int d=c+1;d<V;d++)if(!det(a,b,c,d)){forbidden_count++;std::array<int,4>q{a,b,c,d};for(int z=0;z<4;z++){std::array<int,3>t{};int j=0;for(int k=0;k<4;k++)if(k!=z)t[j++]=q[k];do{finish[(t[0]*V+t[1])*V+t[2]]|=B(1)<<q[z];}while(std::next_permutation(t.begin(),t.end()));}}
 for(int k=0;k<=6;k++)for(int edge=0;edge<(1<<k);edge++)for(int t=0;t<(1<<k);t++)if((edge&t)==edge)supersets[k][edge]|=U(1)<<t;
}
int probe(int samples){
 std::mt19937_64 random(20261003);printf("{\"n\":9,\"forbidden\":%d,\"samples\":%d}\n",forbidden_count,samples);
 for(int trial=0;trial<samples;trial++){
  Transforms t{};B legal=ALL;
  int stop=trial%19;
  for(int step=0;step<stop&&legal;step++){int skip=random()%count(legal);B r=legal;while(skip--)take(r);int p=take(r);legal=nextlegal(t[0],legal,p);t=extend(t,p);}
  if(legal!=legal_from_s(t[0])||canonical(t)!=canonical(t[0]))throw std::runtime_error("internal probe mismatch");
  B key=canonical(t);int outcome=count(legal)<=6?int(tiny(t[0],legal)):-1;
  printf("{\"occupied_lo\":%llu,\"occupied_hi\":%llu,\"legal_lo\":%llu,\"legal_hi\":%llu,\"canonical_lo\":%llu,\"canonical_hi\":%llu,\"rank\":%llu,\"misere\":%d}\n",(unsigned long long)U(t[0]),(unsigned long long)U(t[0]>>64),(unsigned long long)U(legal),(unsigned long long)U(legal>>64),(unsigned long long)U(key),(unsigned long long)U(key>>64),(unsigned long long)encode(key),outcome);
 }
 return 0;
}
int run(int argc,char**argv){
 if(argc<2)throw std::runtime_error("usage: binary proof.bin [seconds] [node-cap] [opening]");
 if(std::string(argv[1])=="--probe"){initialize();return probe(argc>2?std::stoi(argv[2]):400);}
 seconds=argc>2?std::stod(argv[2]):800;limit=argc>3?std::stoull(argv[3]):130000000;first_order=argc>4?std::stoi(argv[4]):40;
 if(seconds<=0||limit<1||limit>130000000||first_order<0||first_order>=V)throw std::runtime_error("invalid bounds");
 initialize();keys.assign(slots,EMPTY);wins.resize((slots+63)/64);deadline();
 fprintf(stderr,"geometry %d, seconds %.1f, memo cap %zu, opening %d\n",forbidden_count,seconds,limit,first_order);
 bool result=solve(Transforms{},ALL);deadline();size_t search_nodes=used;
 fprintf(stderr,"search root solved internally; exporting proof, memo %zu, elapsed %.3f\n",used,elapsed());
 marked.resize((slots+63)/64);limit=180000000;
 std::ofstream out(argv[1],std::ios::binary);if(!out)throw std::runtime_error("cannot create proof");export_proof(0,out);out.close();if(!out)throw std::runtime_error("proof write failed");
 printf("{\"n\":9,\"complete\":true,\"independently_verified\":false,\"provisional_misere_first_wins\":%s,\"forbidden\":%d,\"search_memo_size\":%zu,\"memo_size\":%zu,\"tiny_calls\":%zu,\"tiny_types\":%zu,\"proof_size\":%zu,\"elapsed_seconds\":%.6f}\n",result?"true":"false",forbidden_count,search_nodes,used,tiny_calls,tiny_cache.size(),proofsize,elapsed());return 0;
}
int main(int argc,char**argv){try{return run(argc,argv);}catch(const std::exception&e){fprintf(stderr,"%s\n",e.what());printf("{\"n\":9,\"complete\":false,\"winner\":\"UNKNOWN\",\"memo_size\":%zu,\"tiny_calls\":%zu,\"tiny_types\":%zu,\"elapsed_seconds\":%.6f}\n",used,tiny_calls,tiny_cache.size(),elapsed());return 2;}}
