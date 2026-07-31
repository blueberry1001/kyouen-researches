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
struct ProofCheckpoint final:std::exception{const char*what()const noexcept override{return "proof extraction checkpoint";}};

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
 char magic[8];std::uint32_t version,slotSize;
 std::uint64_t capacity,maxNodes,completeCount,activeCount,rootLo,rootHi;
};
struct ProofIndexSlot{
 std::uint64_t lo,hi;std::uint8_t outcome,witness,rank,status;std::uint32_t reserved;
};
#pragma pack(pop)
static_assert(sizeof(ProofIndexHeader)==64);
static_assert(sizeof(ProofIndexSlot)==24);

class MmapProofIndex{
public:
 MmapProofIndex(const std::string&path,std::size_t max_nodes,Bits root,bool resume):path_(path),max_nodes_(max_nodes),root_(root){
  if(max_nodes_==0)throw std::runtime_error("proof index max_nodes must be positive");
  if(resume&&file_exists(path)){open_existing();resumed_nodes_=size();return;}
  create_new();
 }
 ~MmapProofIndex(){if(mapping_){::msync(mapping_,bytes_,MS_SYNC);::munmap(mapping_,bytes_);}if(fd_>=0)::close(fd_);}
 MmapProofIndex(const MmapProofIndex&)=delete;MmapProofIndex&operator=(const MmapProofIndex&)=delete;
 bool get(Bits key,CertMeta&out)const{const auto*i=find_slot(key,false);if(!i||i->status!=Complete)return false;out={i->outcome,i->witness,i->rank};return true;}
 void insert_pending(Bits key,CertMeta meta){
  if(active_size()>=max_nodes_)throw std::runtime_error("certificate node limit exceeded");
  auto&i=find_insert_slot(key);
  if(i.status==Complete){if(i.outcome!=meta.outcome)throw std::runtime_error("certificate outcome mismatch");return;}
  if(i.status==Pending){if(i.outcome!=meta.outcome)throw std::runtime_error("pending certificate outcome mismatch");return;}
  i.lo=key.lo;i.hi=key.hi;i.outcome=meta.outcome;i.witness=meta.witness;i.rank=meta.rank;i.reserved=0;i.status=Pending;++header_->activeCount;
 }
 void mark_complete(Bits key){
  auto*i=find_slot_mut(key,true);if(!i)throw std::runtime_error("proof index state missing while completing node");
  if(i->status==Complete)return;
  if(i->status!=Pending)throw std::runtime_error("proof index node is not pending");
  i->status=Complete;++header_->completeCount;
 }
 void set_witness(Bits key,std::uint8_t witness){auto*i=find_slot_mut(key,true);if(!i)throw std::runtime_error("proof index state missing while setting witness");i->witness=witness;}
 std::size_t size()const{return static_cast<std::size_t>(header_->completeCount);}
 std::size_t active_size()const{return static_cast<std::size_t>(header_->activeCount);}
 template<class F>void for_each(F&&f)const{for(std::size_t i=0;i<capacity_;++i)if(slots_[i].status==Complete)f(Bits{slots_[i].lo,slots_[i].hi},CertMeta{slots_[i].outcome,slots_[i].witness,slots_[i].rank});}
 std::size_t file_bytes()const{return bytes_;}
 std::size_t resumed_nodes()const{return resumed_nodes_;}
 std::size_t discarded_pending()const{return discarded_pending_;}
private:
 enum:std::uint8_t{Empty=0,Complete=1,Pending=2,Tombstone=3};
 std::string path_;std::size_t max_nodes_=0,capacity_=0,bytes_=0;Bits root_{};int fd_=-1;void*mapping_=nullptr;ProofIndexHeader*header_=nullptr;ProofIndexSlot*slots_=nullptr;std::size_t resumed_nodes_=0,discarded_pending_=0;
 static bool file_exists(const std::string&path){struct stat st{};return::stat(path.c_str(),&st)==0;}
 void create_new(){
  std::size_t needed=max_nodes_+(max_nodes_+1)/2+1;capacity_=1;while(capacity_<needed){if(capacity_>(std::size_t{1}<<61))throw std::runtime_error("proof index capacity overflow");capacity_<<=1;}
  if(capacity_>std::numeric_limits<std::uint64_t>::max()/sizeof(ProofIndexSlot))throw std::runtime_error("proof index file too large");
  bytes_=sizeof(ProofIndexHeader)+capacity_*sizeof(ProofIndexSlot);
  fd_=::open(path_.c_str(),O_RDWR|O_CREAT|O_TRUNC,0600);if(fd_<0)throw std::runtime_error("cannot create proof index file");
  if(::ftruncate(fd_,static_cast<off_t>(bytes_))!=0){::close(fd_);fd_=-1;throw std::runtime_error("cannot size proof index file");}
  map_file();
  std::memcpy(header_->magic,"KYOENPI",7);header_->version=2;header_->slotSize=sizeof(ProofIndexSlot);header_->capacity=capacity_;header_->maxNodes=max_nodes_;header_->completeCount=0;header_->activeCount=0;header_->rootLo=root_.lo;header_->rootHi=root_.hi;
 }
 void open_existing(){
  fd_=::open(path_.c_str(),O_RDWR);if(fd_<0)throw std::runtime_error("cannot open proof index for resume");
  ProofIndexHeader probe{};const auto got=::pread(fd_,&probe,sizeof(probe),0);if(got!=static_cast<ssize_t>(sizeof(probe))){::close(fd_);fd_=-1;throw std::runtime_error("proof index header is truncated");}
  if(std::memcmp(probe.magic,"KYOENPI",7)!=0||probe.version!=2||probe.slotSize!=sizeof(ProofIndexSlot))throw std::runtime_error("unsupported proof index format");
  if(probe.maxNodes!=max_nodes_)throw std::runtime_error("proof index max_nodes mismatch");
  if(probe.rootLo!=root_.lo||probe.rootHi!=root_.hi)throw std::runtime_error("proof index root mismatch");
