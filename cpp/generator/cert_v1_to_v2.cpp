#include <bit>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#pragma pack(push,1)
struct Header { char magic[8]; uint32_t version, board; uint64_t count, rootLo; uint32_t rootHi, forbidden; };
struct NodeV1 { uint64_t lo; uint32_t hi; uint8_t outcome,witness; uint16_t reserved; };
struct NodeV2 { uint64_t lo; uint32_t hi; uint8_t outcome,witness,rank,reserved; };
#pragma pack(pop)
static_assert(sizeof(Header)==40 && sizeof(NodeV1)==16 && sizeof(NodeV2)==16);
int main(int argc,char**argv){
  try{
    if(argc!=3){std::cerr<<"usage: cert_v1_to_v2 IN OUT\n";return 2;}
    std::ifstream in(argv[1],std::ios::binary); std::ofstream out(argv[2],std::ios::binary|std::ios::trunc);
    if(!in||!out) throw std::runtime_error("open failed");
    Header h{}; in.read((char*)&h,sizeof h); if(!in)throw std::runtime_error("short header");
    if(std::memcmp(h.magic,"KYOENC1",7)||h.version!=1||h.board!=9)throw std::runtime_error("bad v1 header");
    std::memcpy(h.magic,"KYOENC2",7); h.version=2; out.write((char*)&h,sizeof h);
    for(uint64_t i=0;i<h.count;i++){
      NodeV1 a{}; in.read((char*)&a,sizeof a); if(!in)throw std::runtime_error("short node");
      const unsigned stones=std::popcount(a.lo)+std::popcount(a.hi);
      if(stones>81)throw std::runtime_error("bad state");
      NodeV2 b{a.lo,a.hi,a.outcome,a.witness,(uint8_t)(81-stones),0};
      out.write((char*)&b,sizeof b); if(!out)throw std::runtime_error("write failed");
    }
    char extra; if(in.read(&extra,1))throw std::runtime_error("trailing data");
    std::cout<<"converted nodes="<<h.count<<"\n";
  }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
