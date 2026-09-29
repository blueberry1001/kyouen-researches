#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <memory>
#include <ostream>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <unordered_map>

struct WitnessKey{std::uint64_t lo=0,hi=0;};
static inline bool operator==(WitnessKey a,WitnessKey b){return a.lo==b.lo&&a.hi==b.hi;}
struct WitnessKeyHash{
 std::size_t operator()(WitnessKey key)const noexcept{
  auto mix=[](std::uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);};
  return static_cast<std::size_t>(mix(key.lo^(mix(key.hi)+0x9e3779b97f4a7c15ULL)));
 }
};

#pragma pack(push,1)
struct WitnessLogHeader{
 char magic[8];std::uint32_t version,recordSize;std::uint64_t recordCount,reserved;
};
struct WitnessLogRecord{
 std::uint64_t lo,hi;std::uint8_t witness,rank;std::uint16_t reserved16;std::uint32_t reserved32;
};
struct WitnessIndexHeader{
 char magic[8];std::uint32_t version,slotSize;
 std::uint64_t capacity,maxRecords,indexedRecords,uniqueCount,logRecordSize,reserved;
};
struct WitnessIndexSlot{
 std::uint64_t lo,hi;std::uint8_t witness,rank,status,reserved8;std::uint32_t reserved32;
};
#pragma pack(pop)
static_assert(sizeof(WitnessLogHeader)==32);
static_assert(sizeof(WitnessLogRecord)==24);
static_assert(sizeof(WitnessIndexHeader)==64);
static_assert(sizeof(WitnessIndexSlot)==24);

class MmapWitnessIndex{
public:
 MmapWitnessIndex(const std::string&path,std::size_t max_records,bool resume):path_(path),max_records_(max_records){
  if(max_records_==0)throw std::runtime_error("witness index max_records must be positive");
  if(resume&&file_exists(path_))open_existing();else create_new();
 }
 ~MmapWitnessIndex(){
  if(mapping_){::msync(mapping_,bytes_,MS_SYNC);::munmap(mapping_,bytes_);}
  if(fd_>=0)::close(fd_);
 }
 MmapWitnessIndex(const MmapWitnessIndex&)=delete;MmapWitnessIndex&operator=(const MmapWitnessIndex&)=delete;
 bool get(std::uint64_t lo,std::uint64_t hi,std::uint8_t&out)const{
  const auto*slot=find_slot(WitnessKey{lo,hi});if(!slot)return false;out=slot->witness;return true;
 }
 bool insert(const WitnessLogRecord&record,bool&conflict){
  conflict=false;WitnessKey key{record.lo,record.hi};auto&slot=find_insert_slot(key);
  if(slot.status==Full){if(slot.witness!=record.witness)conflict=true;return false;}
  if(unique_records()>=max_records_)throw std::runtime_error("winning witness index is full");
  slot.lo=record.lo;slot.hi=record.hi;slot.witness=record.witness;slot.rank=record.rank;slot.reserved8=0;slot.reserved32=0;slot.status=Full;++header_->uniqueCount;return true;
 }
 std::size_t unique_records()const{return static_cast<std::size_t>(header_->uniqueCount);}
 std::uint64_t indexed_records()const{return header_->indexedRecords;}
 void set_indexed_records(std::uint64_t value){header_->indexedRecords=value;}
 std::size_t file_bytes()const{return bytes_;}
 bool newly_created()const{return newly_created_;}
private:
 enum:std::uint8_t{Empty=0,Full=1};
 std::string path_;std::size_t max_records_=0,capacity_=0,bytes_=0;int fd_=-1;void*mapping_=nullptr;WitnessIndexHeader*header_=nullptr;WitnessIndexSlot*slots_=nullptr;bool newly_created_=false;
 static bool file_exists(const std::string&path){struct stat st{};return::stat(path.c_str(),&st)==0;}
 static std::uint64_t mix(std::uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
 std::size_t home(WitnessKey key)const{return static_cast<std::size_t>(mix(key.lo^(mix(key.hi)+0x9e3779b97f4a7c15ULL)))&(capacity_-1);}
 void create_new(){
  std::size_t needed=max_records_+(max_records_+1)/2+1;capacity_=1;
  while(capacity_<needed){if(capacity_>(std::size_t{1}<<61))throw std::runtime_error("witness index capacity overflow");capacity_<<=1;}
  if(capacity_>std::numeric_limits<std::uint64_t>::max()/sizeof(WitnessIndexSlot))throw std::runtime_error("witness index file too large");
  bytes_=sizeof(WitnessIndexHeader)+capacity_*sizeof(WitnessIndexSlot);
  fd_=::open(path_.c_str(),O_RDWR|O_CREAT|O_TRUNC,0600);if(fd_<0)throw std::runtime_error("cannot create winning witness index");
  if(::ftruncate(fd_,static_cast<off_t>(bytes_))!=0){::close(fd_);fd_=-1;throw std::runtime_error("cannot size winning witness index");}
  map_file();std::memcpy(header_->magic,"KYOENWI",7);header_->version=1;header_->slotSize=sizeof(WitnessIndexSlot);header_->capacity=capacity_;header_->maxRecords=max_records_;header_->indexedRecords=0;header_->uniqueCount=0;header_->logRecordSize=sizeof(WitnessLogRecord);header_->reserved=0;newly_created_=true;
 }
 void open_existing(){
  fd_=::open(path_.c_str(),O_RDWR);if(fd_<0)throw std::runtime_error("cannot open winning witness index");
  WitnessIndexHeader probe{};read_all_at(fd_,&probe,sizeof(probe),0);
  if(std::memcmp(probe.magic,"KYOENWI",7)!=0||probe.version!=1||probe.slotSize!=sizeof(WitnessIndexSlot)||probe.logRecordSize!=sizeof(WitnessLogRecord))throw std::runtime_error("unsupported winning witness index format");
  if(probe.maxRecords!=max_records_)throw std::runtime_error("winning witness index max_records mismatch");
  capacity_=static_cast<std::size_t>(probe.capacity);if(!capacity_||(capacity_&(capacity_-1)))throw std::runtime_error("winning witness index capacity is not a power of two");
  bytes_=sizeof(WitnessIndexHeader)+capacity_*sizeof(WitnessIndexSlot);struct stat st{};if(::fstat(fd_,&st)!=0||static_cast<std::uint64_t>(st.st_size)!=bytes_)throw std::runtime_error("winning witness index file size mismatch");
  map_file();if(header_->uniqueCount>header_->maxRecords)throw std::runtime_error("winning witness index unique count is invalid");
 }
 void map_file(){
  mapping_=::mmap(nullptr,bytes_,PROT_READ|PROT_WRITE,MAP_SHARED,fd_,0);if(mapping_==MAP_FAILED){mapping_=nullptr;::close(fd_);fd_=-1;throw std::runtime_error("cannot mmap winning witness index");}
  header_=static_cast<WitnessIndexHeader*>(mapping_);slots_=reinterpret_cast<WitnessIndexSlot*>(static_cast<std::uint8_t*>(mapping_)+sizeof(WitnessIndexHeader));
 }
 static void read_all_at(int fd,void*data,std::size_t size,off_t offset){
  auto*p=static_cast<std::uint8_t*>(data);std::size_t done=0;while(done<size){auto n=::pread(fd,p+done,size-done,offset+static_cast<off_t>(done));if(n<=0)throw std::runtime_error("cannot read winning witness index");done+=static_cast<std::size_t>(n);}
 }
 const WitnessIndexSlot*find_slot(WitnessKey key)const{
  std::size_t i=home(key);for(std::size_t probes=0;probes<capacity_;++probes,i=(i+1)&(capacity_-1)){const auto&slot=slots_[i];if(slot.status==Empty)return nullptr;if(slot.status!=Full)throw std::runtime_error("winning witness index has invalid slot status");if(slot.lo==key.lo&&slot.hi==key.hi)return&slot;}throw std::runtime_error("winning witness index probe overflow");
 }
 WitnessIndexSlot&find_insert_slot(WitnessKey key){
  std::size_t i=home(key);for(std::size_t probes=0;probes<capacity_;++probes,i=(i+1)&(capacity_-1)){auto&slot=slots_[i];if(slot.status==Empty)return slot;if(slot.status!=Full)throw std::runtime_error("winning witness index has invalid slot status");if(slot.lo==key.lo&&slot.hi==key.hi)return slot;}throw std::runtime_error("winning witness index is full");
 }
};

class WitnessLog{
public:
 WitnessLog(const std::string&path,bool resume,const std::string&index_path,std::size_t max_records):path_(path),index_path_(index_path),max_records_(max_records){
  if(resume&&file_exists(path_))open_log();else create_log();
  if(index_path_.empty())load_memory_index();else load_mmap_index(resume);
 }
 ~WitnessLog(){
  if(fd_>=0){update_header();::fsync(fd_);::close(fd_);}
 }
 WitnessLog(const WitnessLog&)=delete;WitnessLog&operator=(const WitnessLog&)=delete;
 bool get(std::uint64_t lo,std::uint64_t hi,std::uint8_t&out)const{
  if(disk_index_)return disk_index_->get(lo,hi,out);
  auto it=records_.find(WitnessKey{lo,hi});if(it==records_.end())return false;out=it->second.witness;return true;
 }
 void record(std::uint64_t lo,std::uint64_t hi,std::uint8_t witness,std::uint8_t rank){
  if(witness>=100||rank>100)throw std::runtime_error("winning witness record is invalid");
  std::uint8_t existing=255;if(get(lo,hi,existing)){if(existing!=witness)++conflicts_;return;}
  if(unique_records()>=max_records_)throw std::runtime_error("winning witness record limit exceeded");
  WitnessLogRecord record{lo,hi,witness,rank,0,0};const auto offset=sizeof(WitnessLogHeader)+record_count_*sizeof(WitnessLogRecord);write_all_at(fd_,&record,sizeof(record),static_cast<off_t>(offset));++record_count_;++appended_records_;update_header();
  if(disk_index_){bool conflict=false;disk_index_->insert(record,conflict);if(conflict)++conflicts_;disk_index_->set_indexed_records(record_count_);}else records_.emplace(WitnessKey{lo,hi},record);
 }
 std::size_t loaded_records()const{return loaded_records_;}
 std::size_t appended_records()const{return appended_records_;}
 std::size_t unique_records()const{return disk_index_?disk_index_->unique_records():records_.size();}
 std::size_t conflicts()const{return conflicts_;}
 std::size_t file_bytes()const{return sizeof(WitnessLogHeader)+record_count_*sizeof(WitnessLogRecord);}
 bool disk_backed()const{return static_cast<bool>(disk_index_);}
 std::size_t index_bytes()const{return disk_index_?disk_index_->file_bytes():0;}
 std::uint64_t indexed_records()const{return disk_index_?disk_index_->indexed_records():record_count_;}
 std::size_t rebuilt_records()const{return rebuilt_records_;}
private:
 std::string path_,index_path_;std::size_t max_records_=0;int fd_=-1;std::uint64_t record_count_=0;std::size_t loaded_records_=0,appended_records_=0,conflicts_=0,rebuilt_records_=0;
 std::unordered_map<WitnessKey,WitnessLogRecord,WitnessKeyHash>records_;std::unique_ptr<MmapWitnessIndex>disk_index_;
 static bool file_exists(const std::string&path){struct stat st{};return::stat(path.c_str(),&st)==0;}
 static void read_all_at(int fd,void*data,std::size_t size,off_t offset){
  auto*p=static_cast<std::uint8_t*>(data);std::size_t done=0;while(done<size){auto n=::pread(fd,p+done,size-done,offset+static_cast<off_t>(done));if(n<=0)throw std::runtime_error("cannot read winning witness log");done+=static_cast<std::size_t>(n);}
 }
 static void write_all_at(int fd,const void*data,std::size_t size,off_t offset){
  const auto*p=static_cast<const std::uint8_t*>(data);std::size_t done=0;while(done<size){auto n=::pwrite(fd,p+done,size-done,offset+static_cast<off_t>(done));if(n<=0)throw std::runtime_error("cannot write winning witness log");done+=static_cast<std::size_t>(n);}
 }
 WitnessLogRecord read_record(std::uint64_t index)const{
  WitnessLogRecord record{};read_all_at(fd_,&record,sizeof(record),static_cast<off_t>(sizeof(WitnessLogHeader)+index*sizeof(WitnessLogRecord)));if(record.witness>=100||record.rank>100)throw std::runtime_error("winning witness log has an invalid record");return record;
 }
 void create_log(){
  fd_=::open(path_.c_str(),O_RDWR|O_CREAT|O_TRUNC,0600);if(fd_<0)throw std::runtime_error("cannot create winning witness log");WitnessLogHeader header{};std::memcpy(header.magic,"KYOENW1",7);header.version=1;header.recordSize=sizeof(WitnessLogRecord);header.recordCount=0;header.reserved=0;write_all_at(fd_,&header,sizeof(header),0);
 }
 void open_log(){
  fd_=::open(path_.c_str(),O_RDWR);if(fd_<0)throw std::runtime_error("cannot open winning witness log");WitnessLogHeader header{};read_all_at(fd_,&header,sizeof(header),0);if(std::memcmp(header.magic,"KYOENW1",7)!=0||header.version!=1||header.recordSize!=sizeof(WitnessLogRecord))throw std::runtime_error("unsupported winning witness log format");
  struct stat st{};if(::fstat(fd_,&st)!=0||st.st_size<static_cast<off_t>(sizeof(WitnessLogHeader)))throw std::runtime_error("winning witness log is truncated");const auto payload=static_cast<std::uint64_t>(st.st_size-sizeof(WitnessLogHeader));record_count_=payload/sizeof(WitnessLogRecord);const auto clean_size=sizeof(WitnessLogHeader)+record_count_*sizeof(WitnessLogRecord);if(static_cast<std::uint64_t>(st.st_size)!=clean_size&&::ftruncate(fd_,static_cast<off_t>(clean_size))!=0)throw std::runtime_error("cannot truncate partial winning witness record");update_header();
 }
 void load_memory_index(){
  records_.reserve(static_cast<std::size_t>(record_count_));for(std::uint64_t i=0;i<record_count_;++i){auto record=read_record(i);WitnessKey key{record.lo,record.hi};auto[it,inserted]=records_.emplace(key,record);if(!inserted&&it->second.witness!=record.witness)++conflicts_;}loaded_records_=records_.size();
 }
 void load_mmap_index(bool resume){
  if(index_path_==path_)throw std::runtime_error("winning witness log and index paths must differ");disk_index_=std::make_unique<MmapWitnessIndex>(index_path_,max_records_,resume);std::uint64_t start=disk_index_->indexed_records();if(start>record_count_)throw std::runtime_error("winning witness index is ahead of its log");
  for(std::uint64_t i=start;i<record_count_;++i){auto record=read_record(i);bool conflict=false;disk_index_->insert(record,conflict);if(conflict)++conflicts_;disk_index_->set_indexed_records(i+1);++rebuilt_records_;}loaded_records_=disk_index_->unique_records();
 }
 void update_header(){
  WitnessLogHeader header{};std::memcpy(header.magic,"KYOENW1",7);header.version=1;header.recordSize=sizeof(WitnessLogRecord);header.recordCount=record_count_;header.reserved=0;write_all_at(fd_,&header,sizeof(header),0);
 }
};

static std::unique_ptr<WitnessLog> winning_witness_log;
static std::uint64_t winning_witness_hits=0,winning_witness_misses=0;
static void open_winning_witness_log(const std::string&path,bool resume,const std::string&index_path="",std::size_t max_records=10000000){
 winning_witness_hits=0;winning_witness_misses=0;if(path.empty())winning_witness_log.reset();else winning_witness_log=std::make_unique<WitnessLog>(path,resume,index_path,max_records);
}
static bool get_winning_witness(std::uint64_t lo,std::uint64_t hi,std::uint8_t&out){
 if(!winning_witness_log)return false;return winning_witness_log->get(lo,hi,out);
}
static void record_winning_witness(std::uint64_t lo,std::uint64_t hi,std::uint8_t witness,std::uint8_t rank){
 if(winning_witness_log)winning_witness_log->record(lo,hi,witness,rank);
}
static void print_winning_witness_stats(std::ostream&out){
 if(!winning_witness_log)return;out<<"witness_log loaded="<<winning_witness_log->loaded_records()<<" appended="<<winning_witness_log->appended_records()<<" unique="<<winning_witness_log->unique_records()<<" conflicts="<<winning_witness_log->conflicts()<<" proof_hits="<<winning_witness_hits<<" proof_misses="<<winning_witness_misses<<" bytes="<<winning_witness_log->file_bytes()<<" witness_index="<<(winning_witness_log->disk_backed()?"mmap":"memory");if(winning_witness_log->disk_backed())out<<" index_bytes="<<winning_witness_log->index_bytes()<<" indexed_records="<<winning_witness_log->indexed_records()<<" rebuilt_records="<<winning_witness_log->rebuilt_records();out<<"\n";
}
