// Exact 8x8 misere P/N search, bounded flat memo, and pruned proof export.
// A six-or-fewer legal-point endgame is reduced to its complete safe-subset
// mask. Its P/N recurrence is solved exactly; the cache key forgets occupied
// geometry but preserves every remaining forbidden edge of sizes 2, 3, 4.
// The exported proof expands these shortcuts back into ordinary board moves.
// Canonical occupied sets of at most 15 points have a reversible 48-bit
// combinatorial rank. Larger sets trigger UNKNOWN rather than key truncation.
// 201,326,611 six-byte slots plus two bit arrays use about 1.27 decimal GB.
// Usage: binary proof.bin [node-cap=145000000] [first-point=27] [all|root].
// Exit 2 and complete:false mean UNKNOWN, never a losing verdict.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unordered_map>
using U=uint64_t;
constexpr int V=64;
constexpr U EMPTY_KEY=(U(1)<<48)-1;
struct __attribute__((packed)) Key {
 uint32_t low;uint16_t high;
 Key(U v=EMPTY_KEY):low(uint32_t(v)),high(uint16_t(v>>32)){}
 operator U()const{return U(low)|(U(high)<<32);}
};
static_assert(sizeof(Key)==6,"48-bit key packing");
std::array<std::array<U,16>,65> choose{};
std::array<U,16> offsets{};
U encode(U s){int k=__builtin_popcountll(s);if(k>15)throw std::runtime_error("rank encoding domain exceeded; UNKNOWN");U value=offsets[k];int j=1;while(s){int p=__builtin_ctzll(s);s&=s-1;value+=choose[p][j++];}if(value>=EMPTY_KEY)throw std::runtime_error("rank overflow; UNKNOWN");return value;}
std::vector<U> finish(64*64*64),wins,marked;
std::vector<Key>keys;
size_t slots,limit,used=0,proofsize=0;int first_order=27;
U transpose(U x){U t=(x^(x>>7))&0x00AA00AA00AA00AAULL;x^=t^(t<<7);t=(x^(x>>14))&0x0000CCCC0000CCCCULL;x^=t^(t<<14);t=(x^(x>>28))&0x00000000F0F0F0F0ULL;return x^t^(t<<28);}
U horizontal(U x){x=((x>>1)&0x5555555555555555ULL)|((x&0x5555555555555555ULL)<<1);x=((x>>2)&0x3333333333333333ULL)|((x&0x3333333333333333ULL)<<2);return ((x>>4)&0x0F0F0F0F0F0F0F0FULL)|((x&0x0F0F0F0F0F0F0F0FULL)<<4);}
U canonical(U x){U h=horizontal(x),t=transpose(x),th=horizontal(t);return std::min({x,h,__builtin_bswap64(x),__builtin_bswap64(h),t,th,__builtin_bswap64(t),__builtin_bswap64(th)});}
size_t lookup(U s){U rank=encode(s),h=rank;h^=h>>30;h*=0xbf58476d1ce4e5b9ULL;h^=h>>27;h*=0x94d049bb133111ebULL;h^=h>>31;size_t i=h%slots;while(U(keys[i])!=EMPTY_KEY&&U(keys[i])!=rank){if(++i==slots)i=0;}return i;}
bool get(size_t i){return wins[i>>6]>>(i&63)&1;}
void save(size_t i,U s,bool win){if(used>=limit)throw std::runtime_error("node cap reached; UNKNOWN");keys[i]=Key(encode(s));if(win)wins[i>>6]|=U(1)<<(i&63);used++;if(used%5000000==0)fprintf(stderr,"memo %zu\n",used);}
U nextlegal(U s,U legal,int p){U r=legal&~(U(1)<<p),a=s;while(a){int i=__builtin_ctzll(a);a&=a-1;U b=a;while(b){int j=__builtin_ctzll(b);b&=b-1;r&=~finish[(p*64+i)*64+j];}}return r;}
std::array<std::array<U,64>,7>super{};
std::unordered_map<U,unsigned char>tiny_cache;
size_t tiny_calls=0;
bool tiny(U s,U legal){
 tiny_calls++;int points[6],k=0;U b=legal;while(b){points[k++]=__builtin_ctzll(b);b&=b-1;}
 U forbidden=0,blocked[6]{};U a=s;
 while(a){int i=__builtin_ctzll(a);a&=a-1;U b=a;while(b){int j=__builtin_ctzll(b);b&=b-1;for(int t=0;t<k;t++)blocked[t]|=finish[(points[t]*64+i)*64+j];}}
 for(int i=0;i<k;i++)for(int j=i+1;j<k;j++)if(blocked[i]>>points[j]&1)forbidden|=super[k][(1<<i)|(1<<j)];
 for(int i=0;i<k;i++)for(int j=i+1;j<k;j++)for(int t=j+1;t<k;t++){
  U comp=finish[(points[i]*64+points[j])*64+points[t]];int edge=(1<<i)|(1<<j)|(1<<t);
  if(comp&s)forbidden|=super[k][edge];
  for(int u=t+1;u<k;u++)if(comp>>points[u]&1)forbidden|=super[k][edge|(1<<u)];
 }
 U safe=(k==6?~U(0):(U(1)<<(1<<k))-1)&~forbidden;
 auto found=tiny_cache.find(safe);if(found!=tiny_cache.end())return found->second;
 bool win[64];for(int subset=(1<<k)-1;subset>=0;subset--)if(safe>>subset&1){bool result=false,move=false;for(int p=0;p<k;p++)if(!(subset>>p&1)){int child=subset|(1<<p);if(safe>>child&1){move=true;if(!win[child])result=true;}}win[subset]=!move||result;}
 tiny_cache.emplace(safe,win[0]);return win[0];
}
bool solve(U s,U legal){if(__builtin_popcountll(legal)<=6)return tiny(s,legal);U key=canonical(s);size_t slot=lookup(key);if(U(keys[slot])!=EMPTY_KEY)return get(slot);bool result=!legal;U remaining=legal;
 if(!s&&first_order)remaining=U(1)<<first_order;
 while(remaining){int p=__builtin_ctzll(remaining);remaining&=remaining-1;U child=s|(U(1)<<p),cl=nextlegal(s,legal,p);if(!solve(child,cl)){result=true;break;}}
 // With a special opening, a losing chosen move does not establish a P root.
 if(!s&&first_order&&!result){remaining=legal&~(U(1)<<first_order);while(remaining){int p=__builtin_ctzll(remaining);remaining&=remaining-1;if(!solve(U(1)<<p,nextlegal(s,legal,p))){result=true;break;}}}
 // Descendants may have occupied this previously empty hash slot.
 slot=lookup(key);save(slot,key,result);return result;
}
U legal_from_s(U s){U r=~s,a=s;while(a){int i=__builtin_ctzll(a);a&=a-1;U b=a;while(b){int j=__builtin_ctzll(b);b&=b-1;U c=b;while(c){int k=__builtin_ctzll(c);c&=c-1;r&=~finish[(i*64+j)*64+k];}}}return r;}
void export_proof(U input,std::ofstream&out){U s=canonical(input);size_t slot=lookup(s);if(U(keys[slot])==EMPTY_KEY){U l=legal_from_s(s);if(__builtin_popcountll(l)>6)throw std::runtime_error("proof state absent");save(slot,s,tiny(s,l));}if(marked[slot>>6]>>(slot&63)&1)return;marked[slot>>6]|=U(1)<<(slot&63);bool w=get(slot);U legal=legal_from_s(s),remaining=legal;
 bool witness=false;while(remaining){int p=__builtin_ctzll(remaining);remaining&=remaining-1;U c=canonical(s|(U(1)<<p));size_t ci=lookup(c);bool cw;
 if(U(keys[ci])!=EMPTY_KEY)cw=get(ci);else{U cl=legal_from_s(c);if(__builtin_popcountll(cl)>6){if(w)continue;throw std::runtime_error("P child absent from proof memo");}cw=tiny(c,cl);}
 if(!w){if(!cw)throw std::runtime_error("P proof closure");export_proof(c,out);}else if(!cw){export_proof(c,out);witness=true;break;}}
 if(w&&legal&&!witness)throw std::runtime_error("N proof witness absent");
 out.write((char*)&s,8);out.put(w);proofsize++;
}
long long det(int a,int b,int c,int d){long long ax=a%8-d%8,ay=a/8-d/8,bx=b%8-d%8,by=b/8-d/8,cx=c%8-d%8,cy=c/8-d/8;return (ax*ax+ay*ay)*(bx*cy-by*cx)-(bx*bx+by*by)*(ax*cy-ay*cx)+(cx*cx+cy*cy)*(ax*by-ay*bx);}
int run(int argc,char**argv){if(argc<2)throw std::runtime_error("usage: binary proof.bin [node-cap] [opening]");limit=argc>2?std::stoull(argv[2]):145000000;first_order=argc>3?std::stoi(argv[3]):27;slots=201326611;
 if(limit<1||limit>145000000||first_order<0||first_order>=64)throw std::runtime_error("invalid node cap or opening");
 keys.assign(slots,Key());wins.resize((slots+63)/64);marked.resize((slots+63)/64);
 for(int a=0;a<=64;a++){choose[a][0]=1;for(int b=1;b<=std::min(a,15);b++)choose[a][b]=(a?choose[a-1][b]:0)+(a?choose[a-1][b-1]:0);}
 for(int k=1;k<=15;k++)offsets[k]=offsets[k-1]+choose[64][k-1];
 // Check all coordinate-basis transformations against the bit permutations.
 for(int p=0;p<64;p++){if(transpose(U(1)<<p)!=(U(1)<<((p%8)*8+p/8)))throw std::runtime_error("transpose");if(horizontal(U(1)<<p)!=(U(1)<<((p/8)*8+7-p%8)))throw std::runtime_error("reflection");}
 int forbidden=0;for(int a=0;a<64;a++)for(int b=a+1;b<64;b++)for(int c=b+1;c<64;c++)for(int d=c+1;d<64;d++)if(!det(a,b,c,d)){forbidden++;std::array<int,4>q{a,b,c,d};for(int z=0;z<4;z++){std::array<int,3>t{};int j=0;for(int k=0;k<4;k++)if(k!=z)t[j++]=q[k];do{finish[(t[0]*64+t[1])*64+t[2]]|=U(1)<<q[z];}while(std::next_permutation(t.begin(),t.end()));}}
 for(int k=0;k<=6;k++)for(int edge=0;edge<(1<<k);edge++)for(int t=0;t<(1<<k);t++)if((edge&t)==edge)super[k][edge]|=U(1)<<t;
 fprintf(stderr,"geometry %d, cap %zu\n",forbidden,limit);
 bool result=solve(0,~U(0));
 fprintf(stderr,"root solved %d, memo %zu, tiny %zu/%zu\n",result,used,tiny_calls,tiny_cache.size());
 bool all_first=argc>4&&std::string(argv[4])=="all";
 std::array<int,64>first_result{};first_result.fill(-1);
 if(all_first)for(int p=0;p<64;p++){
  first_result[p]=solve(U(1)<<p,~(U(1)<<p));
  if(canonical(U(1)<<p)==(U(1)<<p))fprintf(stderr,"first point %d has child outcome %d; memo %zu\n",p,first_result[p],used);
 }
 else for(int p=0;p<64;p++){
  size_t i=lookup(canonical(U(1)<<p));
  if(U(keys[i])!=EMPTY_KEY)first_result[p]=get(i);
 }
 size_t search_nodes=used,search_tiny_calls=tiny_calls,search_tiny_types=tiny_cache.size();
 // Proof expansion can insert exact tiny endgames not stored by the search.
 // This separate bound keeps the same fixed allocation below 92% occupancy.
 limit=185000000;
 std::ofstream out(argv[1],std::ios::binary);
 if(!out)throw std::runtime_error("cannot create proof");
 export_proof(0,out);
 for(int p=0;p<64;p++)if(first_result[p]>=0)export_proof(U(1)<<p,out);
 out.close();if(!out)throw std::runtime_error("proof write failed");
 printf("{\"n\":8,\"complete\":true,\"misere_first_wins\":%s,\"search_memo_size\":%zu,\"tiny_calls\":%zu,\"tiny_types\":%zu,\"memo_after_export\":%zu,\"proof_size\":%zu,\"all_first_moves_classified\":%s,\"first_move_child_outcomes\":[",result?"true":"false",search_nodes,search_tiny_calls,search_tiny_types,used,proofsize,all_first?"true":"false");
 for(int p=0;p<64;p++)printf("%s%d",p?",":"",first_result[p]);
 printf("]}\n");return 0;
}

int main(int argc,char**argv){try{return run(argc,argv);}catch(const std::exception&e){fprintf(stderr,"%s\n",e.what());printf("{\"n\":8,\"complete\":false,\"winner\":\"UNKNOWN\",\"memo_size\":%zu}\n",used);return 2;}}
