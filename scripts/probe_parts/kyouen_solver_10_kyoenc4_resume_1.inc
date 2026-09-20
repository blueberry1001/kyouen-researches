  capacity_=static_cast<std::size_t>(probe.capacity);if(!capacity_||(capacity_&(capacity_-1)))throw std::runtime_error("proof index capacity is not a power of two");
  bytes_=sizeof(ProofIndexHeader)+capacity_*sizeof(ProofIndexSlot);struct stat st{};if(::fstat(fd_,&st)!=0||static_cast<std::uint64_t>(st.st_size)!=bytes_)throw std::runtime_error("proof index file size mismatch");
  map_file();
  std::size_t complete=0,active=0;
  for(std::size_t i=0;i<capacity_;++i){auto&s=slots_[i];if(s.status==Complete){++complete;++active;}else if(s.status==Pending){s.status=Tombstone;++discarded_pending_;}else if(s.status!=Empty&&s.status!=Tombstone)throw std::runtime_error("proof index has invalid slot status");}
  header_->completeCount=complete;header_->activeCount=active;
 }
 void map_file(){mapping_=::mmap(nullptr,bytes_,PROT_READ|PROT_WRITE,MAP_SHARED,fd_,0);if(mapping_==MAP_FAILED){mapping_=nullptr;::close(fd_);fd_=-1;throw std::runtime_error("cannot mmap proof index file");}header_=static_cast<ProofIndexHeader*>(mapping_);slots_=reinterpret_cast<ProofIndexSlot*>(static_cast<std::uint8_t*>(mapping_)+sizeof(ProofIndexHeader));}
 static std::uint64_t mix(std::uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
 std::size_t home(Bits b)const{return static_cast<std::size_t>(mix(b.lo^(mix(b.hi)+0x9e3779b97f4a7c15ULL)))&(capacity_-1);}
 const ProofIndexSlot*find_slot(Bits key,bool include_pending)const{
  std::size_t i=home(key);for(std::size_t probes=0;probes<capacity_;++probes,i=(i+1)&(capacity_-1)){const auto&s=slots_[i];if(s.status==Empty)return nullptr;if((s.status==Complete||(include_pending&&s.status==Pending))&&s.lo==key.lo&&s.hi==key.hi)return&s;}throw std::runtime_error("proof index probe overflow");
 }
 ProofIndexSlot*find_slot_mut(Bits key,bool include_pending){return const_cast<ProofIndexSlot*>(static_cast<const MmapProofIndex*>(this)->find_slot(key,include_pending));}
 ProofIndexSlot&find_insert_slot(Bits key){
  std::size_t i=home(key),first_tombstone=capacity_;
  for(std::size_t probes=0;probes<capacity_;++probes,i=(i+1)&(capacity_-1)){auto&s=slots_[i];if(s.status==Empty)return first_tombstone==capacity_?s:slots_[first_tombstone];if(s.status==Tombstone){if(first_tombstone==capacity_)first_tombstone=i;continue;}if(s.lo==key.lo&&s.hi==key.hi)return s;}
  if(first_tombstone!=capacity_)return slots_[first_tombstone];
  throw std::runtime_error("proof index full");
 }
};

template<unsigned Bytes> class RankCompactTable{
public:
 RankCompactTable(unsigned rank_bits,unsigned power,unsigned load):rank_bits_(rank_bits),power_(power),capacity_(std::size_t{1}<<power),mask_(capacity_-1),quotient_bits_(rank_bits-power),displacement_bits_(Bytes*8-quotient_bits_-2),max_displacement_((std::uint64_t{1}<<displacement_bits_)-1),outcome_shift_(quotient_bits_+displacement_bits_),occupied_shift_(outcome_shift_+1),max_used_(capacity_*load/100),entries_(std::make_unique<std::uint8_t[]>(capacity_*Bytes)){if(rank_bits<=power||displacement_bits_==0||occupied_shift_>=Bytes*8)throw std::runtime_error("bad rank table layout");}
 std::uint32_t get(std::uint64_t rank)const{auto h=permute(rank);auto home=h&mask_;auto q0=h>>power_;for(std::uint64_t d=0;d<=max_displacement_;++d){auto i=(home+d)&mask_;auto e=read(i);if(!e)return 0;auto q=e&low_mask(quotient_bits_);auto sd=(e>>quotient_bits_)&low_mask(displacement_bits_);if(q==q0&&sd==d)return((e>>outcome_shift_)&1)?2:1;}return 0;}
 bool try_put(std::uint64_t rank,std::uint32_t value){if(closed_||used_>=max_used_){closed_=true;return false;}auto h=permute(rank);auto home=h&mask_;auto q0=h>>power_;for(std::uint64_t d=0;d<=max_displacement_;++d){auto i=(home+d)&mask_;auto e=read(i);if(!e){auto v=q0|(d<<quotient_bits_)|(std::uint64_t(value==2)<<outcome_shift_)|(std::uint64_t{1}<<occupied_shift_);write(i,v);++used_;return true;}auto q=e&low_mask(quotient_bits_);auto sd=(e>>quotient_bits_)&low_mask(displacement_bits_);if(q==q0&&sd==d){auto old=((e>>outcome_shift_)&1)?2u:1u;if(old!=value)throw std::runtime_error("inconsistent memo outcome");return true;}}closed_=true;return false;}
 std::size_t used()const{return used_;}
 std::size_t capacity()const{return capacity_;}
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
 std::size_t capacity()const{return capacity_;}
private:static constexpr std::uint64_t Outcome=1ULL<<63;std::size_t capacity_,mask_,max_used_,used_=0;std::unique_ptr<std::uint64_t[]>entries_;static std::uint64_t mix(std::uint64_t x){x+=0x9e3779b97f4a7c15ULL;x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
};
class MultiDepthMemo100{
 static unsigned p(unsigned base,unsigned shrink){if(base<=shrink+1)throw std::runtime_error("shrink too large");return base-shrink;}
public:enum:std::uint32_t{Losing=1,Winning=2};
 MultiDepthMemo100(unsigned shrink,unsigned load):d9_(41,p(23,shrink),load),d10_(44,p(25,shrink),load),d11_(48,p(26,shrink),load),d11b_(48,p(24,shrink),load),d12a_(50,p(28,shrink),load),d12b_(50,p(25,shrink),load),d13a_(53,p(28,shrink>0?shrink-1:0),load),d13b_(53,p(26,shrink>0?shrink-1:0),load),d14a_(56,p(28,shrink),load),d14b_(56,p(25,shrink),load),d15_(58,p(27,shrink),load),d16_(61,p(24,shrink),load),d17_(p(19,shrink),load){build();}
