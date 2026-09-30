// Memory-mapped addresses and certified baseline P/N bytes. Both modified-game
// solvers share this reader; their legality and recursion implementations differ.
#pragma once
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
struct Standard {
    struct Layer{const uint64_t* masks;const uint8_t* pn;size_t count;};
    std::vector<Layer> layers;
    explicit Standard(std::string dir){
        for(int k=0;;++k){std::string path=dir+"/level_"+std::to_string(k)+".occ";int fd=open(path.c_str(),O_RDONLY);if(fd<0)break;
            struct stat st;if(fstat(fd,&st)||st.st_size%8)exit(2);size_t count=st.st_size/8;
            auto masks=static_cast<const uint64_t*>(mmap(nullptr,st.st_size,PROT_READ,MAP_PRIVATE,fd,0));close(fd);
            path=dir+"/standard_"+std::to_string(k)+".pn";fd=open(path.c_str(),O_RDONLY);if(fd<0||fstat(fd,&st)||size_t(st.st_size)!=count)exit(3);
            auto pn=static_cast<const uint8_t*>(mmap(nullptr,count,PROT_READ,MAP_PRIVATE,fd,0));close(fd);
            if(masks==MAP_FAILED||pn==MAP_FAILED)exit(4);layers.push_back({masks,pn,count});}
    }
    bool win(uint64_t s)const{int k=__builtin_popcountll(s);if(k>=int(layers.size()))throw std::logic_error("standard unsafe height");auto L=layers[k];
        auto p=std::lower_bound(L.masks,L.masks+L.count,s);if(p==L.masks+L.count||*p!=s)throw std::logic_error("standard unsafe mask");return L.pn[p-L.masks];}
};
