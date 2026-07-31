#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <limits>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

struct Bits { std::uint64_t lo=0, hi=0; };
static inline bool operator==(Bits a,Bits b){return a.lo==b.lo&&a.hi==b.hi;}
static inline bool operator<(Bits a,Bits b){return a.hi<b.hi||(a.hi==b.hi&&a.lo<b.lo);}
static inline Bits operator|(Bits a,Bits b){return {a.lo|b.lo,a.hi|b.hi};}
static inline Bits operator&(Bits a,Bits b){return {a.lo&b.lo,a.hi&b.hi};}
static inline Bits operator~(Bits a){return {~a.lo,~a.hi};}
static inline bool any(Bits a){return a.lo||a.hi;}
static inline int popcount(Bits a){return std::popcount(a.lo)+std::popcount(a.hi);}
static inline Bits bitof(int p){return p<64?Bits{1ULL<<p,0}:Bits{0,1ULL<<(p-64)};}
static inline int take_lsb(Bits& a){if(a.lo){int p=std::countr_zero(a.lo);a.lo&=a.lo-1;return p;}int p=std::countr_zero(a.hi);a.hi&=a.hi-1;return p+64;}
struct TableFull final:std::exception{const char*what()const noexcept override{return "memo table full";}};

struct BitsHash{
 std::size_t operator()(Bits b)const noexcept{
  auto mix=[](std::uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);};
  return static_cast<std::size_t>(mix(b.lo^(mix(b.hi)+0x9e3779b97f4a7c15ULL)));
 }
};
#pragma pack(push,1)
struct CertHeaderV4{char magic[8];std::uint32_t version,boardSize;std::uint64_t nodeCount,rootLo,rootHi,forbiddenCount;};
struct CertNodeV4{std::uint64_t lo,hi;std::uint8_t outcome,witness,rank,flags;std::uint32_t reserved;};
#pragma pack(pop)
static_assert(sizeof(CertHeaderV4)==48);
static_assert(sizeof(CertNodeV4)==24);
static_assert(std::endian::native==std::endian::little,"KYOENC4 writer requires little-endian");
struct CertMeta{std::uint8_t outcome=0,witness=255,rank=0;};

#pragma pack(push,1)
struct ProofIndexHeader{
 char magic[8];std::uint32_t version,slotSize;std::uint64_t capacity,maxNodes,used,reserved[3];
};
struct ProofIndexSlot{
 std::uint64_t lo,hi;std::uint8_t outcome,witness,rank,status;std::uint32_t reserved;
};
#pragma pack(pop)
static_assert(sizeof(ProofIndexHeader)==64);
static_assert(sizeof(ProofIndexSlot)==24);

class MmapProofIndex{
public:
 MmapProofIndex(const std::string&path,std::size_t max_nodes):path_(path),max_nodes_(max_nodes){
  if(max_nodes_==0)throw std::runtime_error("proof index max_nodes must be positive");
  std::size_t needed=max_nodes_+(max_nodes_+1)/2+1;capacity_=1;while(capacity_<needed){if(capacity_>(std::size_t{1}<<61))throw std::runtime_error("proof index capacity overflow");capacity_<<=1;}
  if(capacity_>std::numeric_limits<std::uint64_t>::max()/sizeof(ProofIndexSlot))throw std::runtime_error("proof index file too large");
  bytes_=sizeof(ProofIndexHeader)+capacity_*sizeof(ProofIndexSlot);
  fd_=::open(path.c_str(),O_RDWR|O_CREAT|O_TRUNC,0600);if(fd_<0)throw std::runtime_error("cannot create proof index file");
  if(::ftruncate(fd_,static_cast<off_t>(bytes_))!=0){::close(fd_);fd_=-1;throw std::runtime_error("cannot size proof index file");}
  mapping_=::mmap(nullptr,bytes_,PROT_READ|PROT_WRITE,MAP_SHARED,fd_,0);if(mapping_==MAP_FAILED){mapping_=nullptr;::close(fd_);fd_=-1;throw std::runtime_error("cannot mmap proof index file");}
  header_=static_cast<ProofIndexHeader*>(mapping_);slots_=reinterpret_cast<ProofIndexSlot*>(static_cast<std::uint8_t*>(mapping_)+sizeof(ProofIndexHeader));
  std::memcpy(header_->magic,"KYOENPI",7);header_->version=1;header_->slotSize=sizeof(ProofIndexSlot);header_->capacity=capacity_;header_->maxNodes=max_nodes_;header_->used=0;
 }
 ~MmapProofIndex(){if(mapping_){::msync(mapping_,bytes_,MS_SYNC);::munmap(mapping_,bytes_);}if(fd_>=0)::close(fd_);}
 MmapProofIndex(const MmapProofIndex&)=delete;MmapProofIndex&operator=(const MmapProofIndex&)=delete;
 bool get(Bits key,CertMeta&out)const{const auto*i=find_slot(key);if(!i)return false;out={i->outcome,i->witness,i->rank};return true;}
 void insert(Bits key,CertMeta meta){if(size()>=max_nodes_)throw std::runtime_error("certificate node limit exceeded");auto&i=find_insert_slot(key);if(i.status){if(i.lo!=key.lo||i.hi!=key.hi)throw std::runtime_error("proof index collision failure");if(i.outcome!=meta.outcome)throw std::runtime_error("certificate outcome mismatch");return;}i.lo=key.lo;i.hi=key.hi;i.outcome=meta.outcome;i.witness=meta.witness;i.rank=meta.rank;i.reserved=0;i.status=1;++header_->used;}
 void set_witness(Bits key,std::uint8_t witness){auto*i=find_slot_mut(key);if(!i)throw std::runtime_error("proof index state missing while setting witness");i->witness=witness;}
 std::size_t size()const{return static_cast<std::size_t>(header_->used);}
 template<class F>void for_each(F&&f)const{for(std::size_t i=0;i<capacity_;++i)if(slots_[i].status)f(Bits{slots_[i].lo,slots_[i].hi},CertMeta{slots_[i].outcome,slots_[i].witness,slots_[i].rank});}
 std::size_t file_bytes()const{return bytes_;}
private:
 std::string path_;std::size_t max_nodes_=0,capacity_=0,bytes_=0;int fd_=-1;void*mapping_=nullptr;ProofIndexHeader*header_=nullptr;ProofIndexSlot*slots_=nullptr;
 static std::uint64_t mix(std::uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
 std::size_t home(Bits b)const{return static_cast<std::size_t>(mix(b.lo^(mix(b.hi)+0x9e3779b97f4a7c15ULL)))&(capacity_-1);}
 const ProofIndexSlot*find_slot(Bits key)const{std::size_t i=home(key);for(std::size_t probes=0;probes<capacity_;++probes,i=(i+1)&(capacity_-1)){const auto&s=slots_[i];if(!s.status)return nullptr;if(s.lo==key.lo&&s.hi==key.hi)return&s;}throw std::runtime_error("proof index probe overflow");}
 ProofIndexSlot*find_slot_mut(Bits key){return const_cast<ProofIndexSlot*>(static_cast<const MmapProofIndex*>(this)->find_slot(key));}
 ProofIndexSlot&find_insert_slot(Bits key){std::size_t i=home(key);for(std::size_t probes=0;probes<capacity_;++probes,i=(i+1)&(capacity_-1)){auto&s=slots_[i];if(!s.status||(s.lo==key.lo&&s.hi==key.hi))return s;}throw std::runtime_error("proof index full");}
};

template<unsigned Bytes> class RankCompactTable{
public:
 RankCompactTable(unsigned rank_bits,unsigned power,unsigned load):rank_bits_(rank_bits),power_(power),capacity_(std::size_t{1}<<power),mask_(capacity_-1),quotient_bits_(rank_bits-power),displacement_bits_(Bytes*8-quotient_bits_-2),max_displacement_((std::uint64_t{1}<<displacement_bits_)-1),outcome_shift_(quotient_bits_+displacement_bits_),occupied_shift_(outcome_shift_+1),max_used_(capacity_*load/100),entries_(std::make_unique<std::uint8_t[]>(capacity_*Bytes)){if(rank_bits<=power||displacement_bits_==0||occupied_shift_>=Bytes*8)throw std::runtime_error("bad rank table layout");}
 std::uint32_t get(std::uint64_t rank)const{auto h=permute(rank);auto home=h&mask_;auto q0=h>>power_;for(std::uint64_t d=0;d<=max_displacement_;++d){auto i=(home+d)&mask_;auto e=read(i);if(!e)return 0;auto q=e&low_mask(quotient_bits_);auto sd=(e>>quotient_bits_)&low_mask(displacement_bits_);if(q==q0&&sd==d)return((e>>outcome_shift_)&1)?2:1;}return 0;}
 bool try_put(std::uint64_t rank,std::uint32_t value){if(closed_||used_>=max_used_){closed_=true;return false;}auto h=permute(rank);auto home=h&mask_;auto q0=h>>power_;for(std::uint64_t d=0;d<=max_displacement_;++d){auto i=(home+d)&mask_;auto e=read(i);if(!e){auto v=q0|(d<<quotient_bits_)|(std::uint64_t(value==2)<<outcome_shift_)|(std::uint64_t{1}<<occupied_shift_);write(i,v);++used_;return true;}auto q=e&low_mask(quotient_bits_);auto sd=(e>>quotient_bits_)&low_mask(displacement_bits_);if(q==q0&&sd==d){auto old=((e>>outcome_shift_)&1)?2u:1u;if(old!=value)throw std::runtime_error("inconsistent memo outcome");return true;}}closed_=true;return false;}
 std::size_t used()const{return used_;}
private:
 unsigned rank_bits_,power_;std::size_t capacity_,mask_;unsigned quotient_bits_,displacement_bits_;std::uint64_t max_displacement_;unsigned outcome_shift_,occupied_shift_;std::size_t max_used_,used_=0;bool closed_=false;std::unique_ptr<std::uint8_t[]>entries_;
 static constexpr std::uint64_t low_mask(unsigned b){return b==64?~0ULL:((1ULL<<b)-1);}
 std::uint64_t permute(std::uint64_t x)const{auto mask=low_mask(rank_bits_);x=(x+0x9e3779b97f4a7c15ULL)&mask;x^=x>>30;x=(x*0xbf58476d1ce4e5b9ULL)&mask;x^=x>>27;x=(x*0x94d049bb133111ebULL)&mask;x^=x>>31;return x&mask;}
 std::uint64_t read(std::size_t i)const{auto*p=entries_.get()+i*Bytes;std::uint64_t x=0;for(unsigned j=0;j<Bytes;++j)x|=std::uint64_t(p[j])<<(8*j);return x;}
 void write(std::size_t i,std::uint64_t x){auto*p=entries_.get()+i*Bytes;for(unsigned j=0;j<Bytes;++j)p[j]=std::uint8_t(x>>(8*j));}
};
class RankFlat17{
public:RankFlat17(unsigned power,unsigned load):capacity_(std::size_t{1}<<power),mask_(capacity_-1),max_used_(capacity_*load/100),entries_(std::make_unique<std::uint64_t[]>(capacity_)){}
 std::uint32_t get(std::uint64_t rank)const{auto key=rank+1;auto i=mix(key)&mask_;for(;;){auto e=entries_[i];if(!e)return 0;if((e&~Outcome)==key)return(e&Outcome)?2:1;i=(i+1)&mask_;}}
 bool try_put(std::uint64_t rank,std::uint32_t value){if(used_>=max_used_)return false;auto key=rank+1,entry=key|(value==2?Outcome:0);auto i=mix(key)&mask_;for(;;){auto e=entries_[i];if(!e){entries_[i]=entry;++used_;return true;}if((e&~Outcome)==key){if(((e&Outcome)?2u:1u)!=value)throw std::runtime_error("inconsistent memo outcome");return true;}i=(i+1)&mask_;}}
 std::size_t used()const{return used_;}
private:static constexpr std::uint64_t Outcome=1ULL<<63;std::size_t capacity_,mask_,max_used_,used_=0;std::unique_ptr<std::uint64_t[]>entries_;static std::uint64_t mix(std::uint64_t x){x+=0x9e3779b97f4a7c15ULL;x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
};
class MultiDepthMemo100{
 static unsigned p(unsigned base,unsigned shrink){if(base<=shrink+1)throw std::runtime_error("shrink too large");return base-shrink;}
public:enum:std::uint32_t{Losing=1,Winning=2};
 MultiDepthMemo100(unsigned shrink,unsigned load):d9_(41,p(23,shrink),load),d10_(44,p(25,shrink),load),d11_(48,p(26,shrink),load),d11b_(48,p(24,shrink),load),d12a_(50,p(27,shrink),load),d12b_(50,p(24,shrink),load),d13a_(53,p(27,shrink>0?shrink-1:0),load),d13b_(53,p(25,shrink>0?shrink-1:0),load),d14a_(56,p(27,shrink),load),d14b_(56,p(24,shrink),load),d15_(58,p(26,shrink),load),d16_(61,p(23,shrink),load),d17_(p(19,shrink),load){build();}
 std::uint32_t get(Bits s,int n)const{if(n<9||n>17)return 0;auto r=rank(s,n);switch(n){case 9:return d9_.get(r);case 10:return d10_.get(r);case 11:{auto v=d11_.get(r);return v?v:d11b_.get(r);}case 12:{auto v=d12a_.get(r);return v?v:d12b_.get(r);}case 13:{auto v=d13a_.get(r);return v?v:d13b_.get(r);}case 14:{auto v=d14a_.get(r);return v?v:d14b_.get(r);}case 15:return d15_.get(r);case 16:return d16_.get(r);case 17:return d17_.get(r);}return 0;}
 void put(Bits s,int n,std::uint32_t v){if(n<9||n>17)return;auto r=rank(s,n);bool ok=false;switch(n){case 9:ok=d9_.try_put(r,v);break;case 10:ok=d10_.try_put(r,v);break;case 11:ok=d11_.try_put(r,v)||d11b_.try_put(r,v);break;case 12:ok=d12a_.try_put(r,v)||d12b_.try_put(r,v);break;case 13:ok=d13a_.try_put(r,v)||d13b_.try_put(r,v);break;case 14:ok=d14a_.try_put(r,v)||d14b_.try_put(r,v);break;case 15:ok=d15_.try_put(r,v);break;case 16:ok=d16_.try_put(r,v);break;case 17:ok=d17_.try_put(r,v);break;}if(!ok)throw TableFull{};}
 std::size_t used()const{return d9_.used()+d10_.used()+d11_.used()+d11b_.used()+d12a_.used()+d12b_.used()+d13a_.used()+d13b_.used()+d14a_.used()+d14b_.used()+d15_.used()+d16_.used()+d17_.used();}
 void print(std::ostream&o)const{o<<"memo_by_depth 9:"<<d9_.used()<<" 10:"<<d10_.used()<<" 11:"<<(d11_.used()+d11b_.used())<<" 12:"<<(d12a_.used()+d12b_.used())<<" 13:"<<(d13a_.used()+d13b_.used())<<" 14:"<<(d14a_.used()+d14b_.used())<<" 15:"<<d15_.used()<<" 16:"<<d16_.used()<<" 17:"<<d17_.used()<<"\n";}
private:RankCompactTable<4>d9_;RankCompactTable<5>d10_,d11_,d11b_,d12a_,d12b_,d13a_;RankCompactTable<6>d13b_,d14a_,d14b_,d15_;RankCompactTable<7>d16_;RankFlat17 d17_;std::array<std::array<std::uint64_t,18>,101>ch_{};
 void build(){ch_[0][0]=1;for(int n=1;n<=100;++n){ch_[n][0]=1;for(int k=1;k<=17;++k){ch_[n][k]=ch_[n-1][k];if(k<=n)ch_[n][k]+=ch_[n-1][k-1];}}}
 std::uint64_t rank(Bits s,int k)const{std::uint64_t r=0;int i=1;while(any(s))r+=ch_[take_lsb(s)][i++];if(i!=k+1)throw std::runtime_error("stone count mismatch");return r;}
};
class Solver{
 static constexpr int N=10,V=100;static constexpr std::uint64_t HiMask=(1ULL<<36)-1;using Clock=std::chrono::steady_clock;struct TState{std::array<Bits,8>t{};};struct Child{TState ts;Bits legal,key;int count;std::uint32_t cached;};
public:
 struct Stats{std::uint64_t visited=0;int maxdepth=0;};
 Solver(unsigned shrink,unsigned load):completion_(std::size_t(V)*V*V),memo_(shrink,load),start_(Clock::now()){maps();quads();}
 bool solve(const std::vector<int>&pts,Stats&st){TState s{};Bits legal{~0ULL,HiMask};for(int v:pts){if(!any(legal&bitof(v)))throw std::runtime_error("illegal initial state");Bits old=s.t[0];s=add(s,v);legal=(legal&~bitof(v))&~bans(old,v);legal.hi&=HiMask;}return win(s,legal,(int)pts.size(),st);}
 void write_certificate(const std::vector<int>&pts,const std::string&path,bool root_winning,std::size_t max_nodes,const std::string&index_path){
  TState original{};Bits legal{~0ULL,HiMask};
  for(int v:pts){if(!any(legal&bitof(v)))throw std::runtime_error("illegal certificate root");Bits old=original.t[0];original=add(original,v);legal=(legal&~bitof(v))&~bans(old,v);legal.hi&=HiMask;}
  Bits root=canonical(original);
  cert_nodes_.clear();disk_nodes_.reset();if(index_path.empty())cert_nodes_.reserve(std::min<std::size_t>(max_nodes,1u<<20));else disk_nodes_=std::make_unique<MmapProofIndex>(index_path,max_nodes);cert_limit_=max_nodes;cert_recomputed_=0;
  build_proof(root,root_winning);
  CertHeaderV4 h{};std::memcpy(h.magic,"KYOENC4",7);h.version=4;h.boardSize=N;h.nodeCount=cert_size();h.rootLo=root.lo;h.rootHi=root.hi;h.forbiddenCount=forbidden_count_;
  std::ofstream out(path,std::ios::binary|std::ios::trunc);if(!out)throw std::runtime_error("cannot open certificate output");
  out.write(reinterpret_cast<const char*>(&h),sizeof(h));
  cert_for_each([&](Bits s,CertMeta m){CertNodeV4 n{s.lo,s.hi,m.outcome,m.witness,m.rank,0,0};out.write(reinterpret_cast<const char*>(&n),sizeof(n));});
  if(!out)throw std::runtime_error("certificate write failed");
  std::cerr<<"certificate nodes="<<cert_size()<<" recomputed="<<cert_recomputed_<<" bytes="<<(sizeof(h)+cert_size()*sizeof(CertNodeV4))<<" root_stones="<<popcount(root)<<" proof_index="<<(disk_nodes_?"mmap":"memory");if(disk_nodes_)std::cerr<<" index_bytes="<<disk_nodes_->file_bytes();std::cerr<<"\n";
 }
 std::size_t memo_used()const{return memo_.used();}
 double seconds()const{return std::chrono::duration<double>(Clock::now()-start_).count();}
 void print(std::ostream&o)const{memo_.print(o);}
 std::uint64_t forbidden_count()const{return forbidden_count_;}
private:std::vector<Bits>completion_;std::array<std::array<Bits,V>,8>tbit_{};MultiDepthMemo100 memo_;std::uint64_t forbidden_count_=0;Clock::time_point start_;std::unordered_map<Bits,CertMeta,BitsHash>cert_nodes_;std::unique_ptr<MmapProofIndex>disk_nodes_;std::size_t cert_limit_=0;std::uint64_t cert_recomputed_=0;
 static long long det3(long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h,long long i){return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);}
 static bool forbidden(int a,int b,int c,int d){int ids[4]={a,b,c,d};long long m[4][4]{};for(int r=0;r<4;++r){long long x=ids[r]%N,y=ids[r]/N;m[r][0]=x*x+y*y;m[r][1]=x;m[r][2]=y;m[r][3]=1;}long long z=0;for(int col=0;col<4;++col){long long q[3][3]{};for(int r=1;r<4;++r){int k=0;for(int j=0;j<4;++j)if(j!=col)q[r-1][k++]=m[r][j];}auto md=det3(q[0][0],q[0][1],q[0][2],q[1][0],q[1][1],q[1][2],q[2][0],q[2][1],q[2][2]);z+=(col%2? -1:1)*m[0][col]*md;}return z==0;}
 static constexpr std::size_t idx(int a,int b,int c){return(std::size_t(a)*V+b)*V+c;}static void sort3(int&a,int&b,int&c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);}
 void maps(){for(int p=0;p<V;++p){int x=p%N,y=p/N;int nx[8]={x,N-1-x,x,N-1-x,y,N-1-y,y,N-1-y};int ny[8]={y,y,N-1-y,N-1-y,x,x,N-1-x,N-1-x};for(int k=0;k<8;++k)tbit_[k][p]=bitof(ny[k]*N+nx[k]);}}
 void quads(){for(int a=0;a<V;++a)for(int b=a+1;b<V;++b)for(int c=b+1;c<V;++c)for(int d=c+1;d<V;++d)if(forbidden(a,b,c,d)){++forbidden_count_;int q[4]={a,b,c,d};for(int omit=0;omit<4;++omit){int t[3],p=0;for(int j=0;j<4;++j)if(j!=omit)t[p++]=q[j];completion_[idx(t[0],t[1],t[2])]=completion_[idx(t[0],t[1],t[2])]|bitof(q[omit]);}}}
 TState add(const TState&s,int v)const{TState r=s;for(int k=0;k<8;++k)r.t[k]=r.t[k]|tbit_[k][v];return r;}static Bits canonical(const TState&s){Bits r=s.t[0];for(int k=1;k<8;++k)if(s.t[k]<r)r=s.t[k];return r;}
 Bits bans(Bits state,int v)const{int verts[V],k=0;while(any(state))verts[k++]=take_lsb(state);Bits out{};for(int i=0;i<k;++i)for(int j=i+1;j<k;++j){int a=verts[i],b=verts[j],c=v;sort3(a,b,c);out=out|completion_[idx(a,b,c)];}return out;}

 std::optional<CertMeta>cert_get(Bits state)const{CertMeta m;if(disk_nodes_){if(disk_nodes_->get(state,m))return m;return std::nullopt;}auto it=cert_nodes_.find(state);if(it==cert_nodes_.end())return std::nullopt;return it->second;}
 void cert_insert(Bits state,CertMeta meta){if(disk_nodes_)disk_nodes_->insert(state,meta);else{if(cert_nodes_.size()>=cert_limit_)throw std::runtime_error("certificate node limit exceeded");auto[it,inserted]=cert_nodes_.emplace(state,meta);if(!inserted&&it->second.outcome!=meta.outcome)throw std::runtime_error("certificate outcome mismatch");}}
 void cert_set_witness(Bits state,std::uint8_t witness){if(disk_nodes_)disk_nodes_->set_witness(state,witness);else{auto it=cert_nodes_.find(state);if(it==cert_nodes_.end())throw std::runtime_error("certificate state missing while setting witness");it->second.witness=witness;}}
 std::size_t cert_size()const{return disk_nodes_?disk_nodes_->size():cert_nodes_.size();}
 template<class F>void cert_for_each(F&&f)const{if(disk_nodes_)disk_nodes_->for_each(std::forward<F>(f));else for(const auto&kv:cert_nodes_)f(kv.first,kv.second);}
 TState from_bits(Bits state)const{TState r{};while(any(state)){int v=take_lsb(state);for(int k=0;k<8;++k)r.t[k]=r.t[k]|tbit_[k][v];}return r;}
 Bits legal_from_state(Bits state)const{int verts[V],n=0;Bits copy=state;while(any(copy))verts[n++]=take_lsb(copy);Bits banned{};for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)for(int k=j+1;k<n;++k)banned=banned|completion_[idx(verts[i],verts[j],verts[k])];Bits legal=(Bits{~0ULL,HiMask}&~state)&~banned;legal.hi&=HiMask;return legal;}
 bool evaluate_canonical(Bits state){auto known=cert_get(state);if(known)return known->outcome==2;TState ts=from_bits(state);Bits legal=legal_from_state(state);Stats scratch;++cert_recomputed_;return win(ts,legal,popcount(state),scratch);}
 void build_proof(Bits state,bool winning){
  auto existing=cert_get(state);if(existing){if((existing->outcome==2)!=winning)throw std::runtime_error("certificate outcome mismatch");return;}
  CertMeta meta;meta.outcome=winning?2:1;meta.witness=255;meta.rank=static_cast<std::uint8_t>(V-popcount(state));cert_insert(state,meta);
  TState ts=from_bits(state);Bits legal=legal_from_state(state);
  if(winning){
   Bits moves=legal;bool found=false;
   while(any(moves)){int v=take_lsb(moves);TState child_ts=add(ts,v);Bits child=canonical(child_ts);bool child_winning=evaluate_canonical(child);if(!child_winning){cert_set_witness(state,static_cast<std::uint8_t>(v));build_proof(child,false);found=true;break;}}
   if(!found)throw std::runtime_error("winning certificate node has no losing child");
  }else{
   std::array<Bits,V>unique{};int count=0;Bits moves=legal;
   while(any(moves)){int v=take_lsb(moves);Bits child=canonical(add(ts,v));bool duplicate=false;for(int i=0;i<count;++i)if(unique[i]==child){duplicate=true;break;}if(duplicate)continue;unique[count++]=child;if(!evaluate_canonical(child))throw std::runtime_error("losing certificate node has a losing child");}
   for(int i=0;i<count;++i)build_proof(unique[i],true);
  }
  if((cert_size()&((1u<<20)-1))==0)std::cerr<<"certificate progress nodes="<<cert_size()<<" recomputed="<<cert_recomputed_<<"\n";
 }
 bool win(const TState&s,Bits legal,int depth,Stats&st){Bits key=canonical(s);auto cached=memo_.get(key,depth);if(cached)return cached==MultiDepthMemo100::Winning;++st.visited;st.maxdepth=std::max(st.maxdepth,depth);if((st.visited&((1ULL<<24)-1))==0)std::cerr<<"progress visited="<<st.visited<<" memo="<<memo_.used()<<" depth="<<depth<<" maxdepth="<<st.maxdepth<<" seconds="<<seconds()<<"\n";if(!any(legal)){memo_.put(key,depth,MultiDepthMemo100::Losing);return false;}std::array<Child,V>ch{};int n=0;Bits moves=legal;while(any(moves)){int v=take_lsb(moves);Bits bit=bitof(v);TState ns=add(s,v);Bits nl=(legal&~bit)&~bans(s.t[0],v);nl.hi&=HiMask;Bits nk=canonical(ns);bool dup=false;for(int i=0;i<n;++i)if(ch[i].key==nk){dup=true;break;}if(dup)continue;auto cv=memo_.get(nk,depth+1);ch[n++]={ns,nl,nk,popcount(nl),cv};}std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){int pa=a.cached==MultiDepthMemo100::Losing?0:(a.cached==0?1:2),pb=b.cached==MultiDepthMemo100::Losing?0:(b.cached==0?1:2);if(pa!=pb)return pa<pb;if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});for(int i=0;i<n;++i){bool cw=ch[i].cached?ch[i].cached==MultiDepthMemo100::Winning:win(ch[i].ts,ch[i].legal,depth+1,st);if(!cw){memo_.put(key,depth,MultiDepthMemo100::Winning);return true;}}memo_.put(key,depth,MultiDepthMemo100::Losing);return false;}
};
static std::vector<int> parse(const std::string&s){std::vector<int>v;std::size_t b=0;while(b<s.size()){auto e=s.find(',',b);auto t=s.substr(b,e==std::string::npos?std::string::npos:e-b);if(!t.empty())v.push_back(std::stoi(t));if(e==std::string::npos)break;b=e+1;}return v;}
int main(int argc,char**argv){try{
 if(argc<2){std::cerr<<"usage: solver STATES_FILE [shrink=3] [load=80]\n       solver --certificate STATE OUTPUT.cert [shrink=3] [load=80] [max_nodes=10000000] [proof_index_file]\n";return 2;}
 if(std::string(argv[1])=="--certificate"){
  if(argc<4){std::cerr<<"usage: solver --certificate STATE OUTPUT.cert [shrink=3] [load=80] [max_nodes=10000000] [proof_index_file]\n";return 2;}
  auto pts=parse(argv[2]);unsigned shrink=argc>=5?std::atoi(argv[4]):3,load=argc>=6?std::atoi(argv[5]):80;std::size_t max_nodes=argc>=7?std::stoull(argv[6]):10000000ULL;std::string index_path=argc>=8?argv[7]:"";
  Solver solver(shrink,load);Solver::Stats st;bool w=solver.solve(pts,st);
  std::cout<<"state,outcome,visited,maxdepth,memo,seconds\n"<<argv[2]<<','<<(w?"WIN":"LOSS")<<','<<st.visited<<','<<st.maxdepth<<','<<solver.memo_used()<<','<<solver.seconds()<<"\n";
  solver.write_certificate(pts,argv[3],w,max_nodes,index_path);solver.print(std::cerr);return 0;
 }
 unsigned shrink=argc>=3?std::atoi(argv[2]):3,load=argc>=4?std::atoi(argv[3]):80;std::ifstream in(argv[1]);if(!in)throw std::runtime_error("cannot open states file");std::vector<std::vector<int>>tasks;std::string line;while(std::getline(in,line))if(!line.empty())tasks.push_back(parse(line));Solver solver(shrink,load);std::cout<<"state,outcome,visited,maxdepth,memo,seconds\n";std::size_t done=0;for(auto&pts:tasks){Solver::Stats st;try{bool w=solver.solve(pts,st);for(std::size_t i=0;i<pts.size();++i){if(i)std::cout<<'-';std::cout<<pts[i];}std::cout<<','<<(w?"WIN":"LOSS")<<','<<st.visited<<','<<st.maxdepth<<','<<solver.memo_used()<<','<<solver.seconds()<<"\n";std::cout.flush();++done;}catch(const TableFull&){solver.print(std::cerr);std::cerr<<"forbidden="<<solver.forbidden_count()<<" completed="<<done<<" requested="<<tasks.size()<<" memo="<<solver.memo_used()<<" seconds="<<solver.seconds()<<" table_full=1\n";return 3;}}solver.print(std::cerr);std::cerr<<"forbidden="<<solver.forbidden_count()<<" completed="<<done<<" requested="<<tasks.size()<<" memo="<<solver.memo_used()<<" seconds="<<solver.seconds()<<" table_full=0\n";return 0;
 }catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<"\n";return 1;}}
