// Independent B317 checker: original-coordinate 4x4 determinants,
// dense all-subset mex, reverse-vertex matching enumeration, and certificates.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_set>
#include <vector>
using U = uint64_t;
int64_t determinant(const std::array<int,4>& points) {
    int64_t matrix[4][4];
    for(int i=0;i<4;++i) {
        int x=points[i]%4,y=points[i]/4;
        matrix[i][0]=x*x+y*y; matrix[i][1]=x; matrix[i][2]=y; matrix[i][3]=1;
    }
    std::array<int,4> permutation={0,1,2,3}; int64_t result=0;
    do {
        int inversions=0; int64_t term=1;
        for(int i=0;i<4;++i) {
            term*=matrix[i][permutation[i]];
            for(int j=0;j<i;++j) inversions+=permutation[j]>permutation[i];
        }
        result+=inversions%2 ? -term : term;
    } while(std::next_permutation(permutation.begin(),permutation.end()));
    return result;
}
U read_little(std::istream& in,int bytes) {
    U result=0;
    for(int i=0;i<bytes;++i) {
        int c=in.get(); if(c<0) throw std::runtime_error("truncated certificate");
        result |= U(c)<<(8*i);
    }
    return result;
}
struct Checker {
    std::array<bool,65536> safe={};
    std::array<uint8_t,65536> grundy={};
    std::array<uint16_t,16> adjacency={};
    std::array<int,16> mate={};
    std::unordered_set<U> unseen;
    U matching_count=0;
    void enumerate(uint16_t remaining) {
        if(!remaining) {
            U key=0; for(int p=0;p<16;++p) key |= U(mate[p])<<(4*p);
            if(unseen.erase(key)!=1) throw std::runtime_error("missing matching certificate");
            ++matching_count; return;
        }
        int p=31-__builtin_clz(unsigned(remaining));
        uint16_t candidates=adjacency[p]&remaining;
        while(candidates) {
            int q=31-__builtin_clz(unsigned(candidates));
            candidates ^= uint16_t(1<<q);
            mate[p]=q; mate[q]=p;
            enumerate(remaining & ~(uint16_t(1<<p)|uint16_t(1<<q)));
        }
    }
};
int main(int argc,char** argv) {
    try {
        if(argc!=3) return 2;
        Checker checker; std::vector<uint16_t> quads;
        for(int a=0;a<16;++a) for(int b=a+1;b<16;++b)
            for(int c=b+1;c<16;++c) for(int d=c+1;d<16;++d)
                if(!determinant({a,b,c,d})) quads.push_back((1<<a)|(1<<b)|(1<<c)|(1<<d));
        int safe_count=0;
        for(int s=65535;s>=0;--s) {
            bool safe=true;
            for(uint16_t q:quads) if((s&q)==q) { safe=false; break; }
            checker.safe[s]=safe;
            if(!safe) continue;
            ++safe_count; unsigned seen=0;
            for(int p=15;p>=0;--p) if(!(s&(1<<p)) && checker.safe[s|(1<<p)])
                seen |= 1u<<checker.grundy[s|(1<<p)];
            int g=0; while(seen&(1u<<g)) ++g;
            checker.grundy[s]=g;
        }
        if(quads.size()!=194 || safe_count!=5811 || checker.grundy[0]!=0)
            throw std::runtime_error("baseline mismatch");
        int edges=0;
        for(int a=0;a<16;++a) for(int b=a+1;b<16;++b)
            if(checker.grundy[(1<<a)|(1<<b)]==0) {
                checker.adjacency[a]|=1<<b; checker.adjacency[b]|=1<<a; ++edges;
            }
        std::ifstream in(argv[1],std::ios::binary); char magic[8]; in.read(magic,8);
        if(!in || std::string(magic,8)!="KYPAIR27") throw std::runtime_error("certificate header");
        U records=read_little(in,4), immediate=0;
        checker.unseen.reserve(records);
        for(U i=0;i<records;++i) {
            U key=read_little(in,8); int occupied=read_little(in,2);
            int opponent=read_little(in,1),reply=read_little(in,1);
            std::array<int,16> mate;
            for(int p=0;p<16;++p) mate[p]=(key>>(4*p))&15;
            for(int p=0;p<16;++p) {
                if(mate[p]==p || mate[mate[p]]!=p || !(checker.adjacency[p]&(1<<mate[p])))
                    throw std::runtime_error("not a J4 perfect matching");
                if(bool(occupied&(1<<p))!=bool(occupied&(1<<mate[p])))
                    throw std::runtime_error("prefix not paired");
            }
            if(opponent>=16 || reply>=16 || mate[opponent]!=reply
               || (occupied&((1<<opponent)|(1<<reply))) || !checker.safe[occupied]
               || !checker.safe[occupied|(1<<opponent)] || checker.safe[occupied|(1<<opponent)|(1<<reply)])
                throw std::runtime_error("illegal breaking witness");
            if(!checker.unseen.insert(key).second) throw std::runtime_error("duplicate matching");
            immediate+=__builtin_popcount(unsigned(occupied))==2;
        }
        if(in.get()!=EOF) throw std::runtime_error("trailing certificate bytes");
        checker.enumerate(65535);
        if(!checker.unseen.empty() || checker.matching_count!=records || records!=112212)
            throw std::runtime_error("matching coverage mismatch");
        std::ofstream out(argv[2]);
        out<<"{\"quad_count\":"<<quads.size()<<",\"safe_states\":"<<safe_count
           <<",\"g0\":0,\"J4_edge_count\":"<<edges<<",\"matching_count\":"<<records
           <<",\"certificates_verified\":"<<records<<",\"fourth_move_failures\":"<<immediate
           <<",\"later_failures\":"<<records-immediate<<",\"uncovered_matchings\":0}\n";
        std::cout<<"PASS independent geometry, mex, and all "<<records<<" matching certificates"<<std::endl;
    } catch(const std::exception& e) { std::cerr<<e.what()<<std::endl; return 1; }
}
