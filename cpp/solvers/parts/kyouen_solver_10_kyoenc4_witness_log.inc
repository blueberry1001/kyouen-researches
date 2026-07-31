#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <memory>
#include <ostream>
#include <stdexcept>
#include <string>
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
#pragma pack(pop)
static_assert(sizeof(WitnessLogHeader)==32);
static_assert(sizeof(WitnessLogRecord)==24);

class WitnessLog{
public:
 WitnessLog(const std::string&path,bool resume):path_(path){
  if(resume&&file_exists(path_))open_existing();else create_new();
 }
 ~WitnessLog(){
  if(fd_>=0){update_header();::fsync(fd_);::close(fd_);}
 }
 WitnessLog(const WitnessLog&)=delete;WitnessLog&operator=(const WitnessLog&)=delete;
 bool get(std::uint64_t lo,std::uint64_t hi,std::uint8_t&out)const{
  auto it=records_.find(WitnessKey{lo,hi});if(it==records_.end())return false;out=it->second.witness;return true;
 }
 void record(std::uint64_t lo,std::uint64_t hi,std::uint8_t witness,std::uint8_t rank){
  if(witness>=100)throw std::runtime_error("winning witness is outside the 10x10 board");
  WitnessKey key{lo,hi};auto it=records_.find(key);
  if(it!=records_.end()){
   if(it->second.witness!=witness)++conflicts_;
   return;
  }
  WitnessLogRecord rec{lo,hi,witness,rank,0,0};
  const auto offset=sizeof(WitnessLogHeader)+record_count_*sizeof(WitnessLogRecord);
  write_all_at(fd_,&rec,sizeof(rec),static_cast<off_t>(offset));
  records_.emplace(key,rec);++record_count_;++appended_records_;
  update_header();
 }
 std::size_t loaded_records()const{return loaded_records_;}
 std::size_t appended_records()const{return appended_records_;}
 std::size_t unique_records()const{return records_.size();}
 std::size_t conflicts()const{return conflicts_;}
 std::size_t file_bytes()const{return sizeof(WitnessLogHeader)+record_count_*sizeof(WitnessLogRecord);}
private:
 std::string path_;int fd_=-1;std::uint64_t record_count_=0;std::size_t loaded_records_=0,appended_records_=0,conflicts_=0;
 std::unordered_map<WitnessKey,WitnessLogRecord,WitnessKeyHash>records_;
 static bool file_exists(const std::string&path){struct stat st{};return::stat(path.c_str(),&st)==0;}
 static void read_all_at(int fd,void*data,std::size_t size,off_t offset){
  auto*p=static_cast<std::uint8_t*>(data);std::size_t done=0;
  while(done<size){auto n=::pread(fd,p+done,size-done,offset+static_cast<off_t>(done));if(n<=0)throw std::runtime_error("cannot read winning witness log");done+=static_cast<std::size_t>(n);}
 }
 static void write_all_at(int fd,const void*data,std::size_t size,off_t offset){
  const auto*p=static_cast<const std::uint8_t*>(data);std::size_t done=0;
  while(done<size){auto n=::pwrite(fd,p+done,size-done,offset+static_cast<off_t>(done));if(n<=0)throw std::runtime_error("cannot write winning witness log");done+=static_cast<std::size_t>(n);}
 }
 void create_new(){
  fd_=::open(path_.c_str(),O_RDWR|O_CREAT|O_TRUNC,0600);if(fd_<0)throw std::runtime_error("cannot create winning witness log");
  WitnessLogHeader h{};std::memcpy(h.magic,"KYOENW1",7);h.version=1;h.recordSize=sizeof(WitnessLogRecord);h.recordCount=0;h.reserved=0;
  write_all_at(fd_,&h,sizeof(h),0);
 }
 void open_existing(){
  fd_=::open(path_.c_str(),O_RDWR);if(fd_<0)throw std::runtime_error("cannot open winning witness log");
  WitnessLogHeader h{};read_all_at(fd_,&h,sizeof(h),0);
  if(std::memcmp(h.magic,"KYOENW1",7)!=0||h.version!=1||h.recordSize!=sizeof(WitnessLogRecord))throw std::runtime_error("unsupported winning witness log format");
  struct stat st{};if(::fstat(fd_,&st)!=0||st.st_size<static_cast<off_t>(sizeof(WitnessLogHeader)))throw std::runtime_error("winning witness log is truncated");
  const auto payload=static_cast<std::uint64_t>(st.st_size-sizeof(WitnessLogHeader));
  record_count_=payload/sizeof(WitnessLogRecord);
  const auto clean_size=sizeof(WitnessLogHeader)+record_count_*sizeof(WitnessLogRecord);
  if(static_cast<std::uint64_t>(st.st_size)!=clean_size&&::ftruncate(fd_,static_cast<off_t>(clean_size))!=0)throw std::runtime_error("cannot truncate partial winning witness record");
  records_.reserve(static_cast<std::size_t>(record_count_));
  for(std::uint64_t i=0;i<record_count_;++i){
   WitnessLogRecord rec{};read_all_at(fd_,&rec,sizeof(rec),static_cast<off_t>(sizeof(WitnessLogHeader)+i*sizeof(WitnessLogRecord)));
   if(rec.witness>=100||rec.rank>100)throw std::runtime_error("winning witness log has an invalid record");
   WitnessKey key{rec.lo,rec.hi};auto[it,inserted]=records_.emplace(key,rec);if(!inserted&&it->second.witness!=rec.witness)++conflicts_;
  }
  loaded_records_=records_.size();update_header();
 }
 void update_header(){
  WitnessLogHeader h{};std::memcpy(h.magic,"KYOENW1",7);h.version=1;h.recordSize=sizeof(WitnessLogRecord);h.recordCount=record_count_;h.reserved=0;
  write_all_at(fd_,&h,sizeof(h),0);
 }
};

static std::unique_ptr<WitnessLog> winning_witness_log;
static std::uint64_t winning_witness_hits=0,winning_witness_misses=0;
static void open_winning_witness_log(const std::string&path,bool resume){
 winning_witness_hits=0;winning_witness_misses=0;
 if(path.empty())winning_witness_log.reset();else winning_witness_log=std::make_unique<WitnessLog>(path,resume);
}
static bool get_winning_witness(std::uint64_t lo,std::uint64_t hi,std::uint8_t&out){
 if(!winning_witness_log)return false;return winning_witness_log->get(lo,hi,out);
}
static void record_winning_witness(std::uint64_t lo,std::uint64_t hi,std::uint8_t witness,std::uint8_t rank){
 if(winning_witness_log)winning_witness_log->record(lo,hi,witness,rank);
}
static void print_winning_witness_stats(std::ostream&out){
 if(!winning_witness_log)return;
 out<<"witness_log loaded="<<winning_witness_log->loaded_records()
    <<" appended="<<winning_witness_log->appended_records()
    <<" unique="<<winning_witness_log->unique_records()
    <<" conflicts="<<winning_witness_log->conflicts()
    <<" proof_hits="<<winning_witness_hits
    <<" proof_misses="<<winning_witness_misses
    <<" bytes="<<winning_witness_log->file_bytes()<<"\n";
}
