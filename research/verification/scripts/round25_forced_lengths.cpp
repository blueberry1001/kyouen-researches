// All safe states: mex, winner-preserving terminal sizes, forceable sizes.
// Legality uses incremental triple-completion masks; no previous DP included.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
using U = uint64_t;
struct Value {
    U terminal = 0, forced = 0;
    uint8_t g = 0, h = 0, mu = 0, fast = 0;
};
struct Solver {
    int v;
    U full;
    std::vector<U> completion;
    std::unordered_map<U,uint32_t> ids;
    std::vector<Value> values;
    std::vector<U> masks;
    size_t key(int a, int b, int c) const {
        if(a>b) std::swap(a,b);
        if(b>c) std::swap(b,c);
        if(a>b) std::swap(a,b);
        return (a*v+b)*v+c;
    }
    U after(U s, U legal, int p) const {
        legal &= ~(U(1)<<p);
        while(s) {
            int a=__builtin_ctzll(s); s &= s-1;
            for(U tail=s; tail; tail &= tail-1)
                legal &= ~completion[key(a,__builtin_ctzll(tail),p)];
        }
        return legal;
    }
    uint32_t solve(U s, U legal) {
        auto old=ids.find(s); if(old!=ids.end()) return old->second;
        Value result;
        if(!legal) {
            int k=__builtin_popcountll(s);
            result.terminal=result.forced=U(1)<<k;
            result.fast=k;
        } else {
            U nimbers=0, all_t=0, all_w=~U(0), zero_t=0, zero_w=0;
            int max_h=0, min_mu=v, min_fast=v, max_fast=0;
            for(U tail=legal; tail; tail &= tail-1) {
                int p=__builtin_ctzll(tail);
                uint32_t ci=solve(s|(U(1)<<p),after(s,legal,p));
                Value child=values[ci];
                nimbers |= U(1)<<child.g;
                max_h=std::max(max_h,int(child.h));
                min_mu=std::min(min_mu,int(child.mu));
                max_fast=std::max(max_fast,int(child.fast));
                all_t |= child.terminal; all_w &= child.forced;
                if(!child.g) {
                    zero_t |= child.terminal; zero_w |= child.forced;
                    min_fast=std::min(min_fast,int(child.fast));
                }
            }
            int g=0; while(nimbers&(U(1)<<g)) ++g;
            result.g=g; result.h=max_h+1; result.mu=min_mu+1;
            result.terminal=g ? zero_t : all_t;
            result.forced=g ? zero_w : all_w;
            result.fast=g ? min_fast : max_fast;
            if(!result.terminal || (result.forced & ~result.terminal))
                throw std::runtime_error("terminal-set invariant");
        }
        uint32_t id=values.size();
        values.push_back(result); masks.push_back(s); ids.emplace(s,id);
        if(values.size()%1000000==0) std::cout<<"completed="<<values.size()<<std::endl;
        return id;
    }
};
void write_value(std::ostream& out,U mask,Value a) {
    out<<"{\"mask\":"<<mask<<",\"k\":"<<__builtin_popcountll(mask)
       <<",\"g\":"<<int(a.g)<<",\"h\":"<<int(a.h)<<",\"mu\":"<<int(a.mu)
       <<",\"Tstar_bits\":"<<a.terminal<<",\"WFT_bits\":"<<a.forced
       <<",\"fast_terminal\":"<<int(a.fast)<<"}";
}
int main(int argc,char** argv) {
    if(argc!=3) return 2;
    auto started=std::chrono::steady_clock::now();
    std::ifstream in(argv[1]); Solver s; int nq,count;
    if(!(in>>s.v>>nq>>count)||s.v>49||s.v<4) return 3;
    s.full=(U(1)<<s.v)-1; s.completion.assign(s.v*s.v*s.v,0);
    for(int qi=0;qi<nq;++qi) {
        U q; in>>q; std::vector<int> points;
        for(U tail=q;tail;tail &= tail-1) points.push_back(__builtin_ctzll(tail));
        if(points.size()!=4) return 4;
        for(int i=0;i<4;++i) {
            std::vector<int> other;
            for(int j=0;j<4;++j) if(j!=i) other.push_back(points[j]);
            s.completion[s.key(other[0],other[1],other[2])] |= U(1)<<points[i];
        }
    }
    s.ids.reserve(s.v<=25?200000:6000000);
    s.values.reserve(s.v<=25?200000:6000000); s.masks.reserve(s.values.capacity());
    uint32_t root=s.solve(0,s.full);
    uint64_t count334=0,count334N=0,count333=0; uint64_t forced_hist[50]={};
    std::vector<uint32_t> witnesses, gaps;
    uint32_t least334=0,least334N=0;
    for(uint32_t i=0;i<s.values.size();++i) {
        Value a=s.values[i]; int nw=__builtin_popcountll(a.forced); ++forced_hist[nw];
        if(__builtin_popcountll(a.terminal)>=3 && !a.forced) {
            if(!count334 || __builtin_popcountll(s.masks[i])<__builtin_popcountll(s.masks[least334])
               || (__builtin_popcountll(s.masks[i])==__builtin_popcountll(s.masks[least334])
                   && s.masks[i]<s.masks[least334])) least334=i;
            ++count334; if(witnesses.size()<16) witnesses.push_back(i);
            if(a.g) {
                if(!count334N || __builtin_popcountll(s.masks[i])<__builtin_popcountll(s.masks[least334N])
                   || (__builtin_popcountll(s.masks[i])==__builtin_popcountll(s.masks[least334N])
                       && s.masks[i]<s.masks[least334N])) least334N=i;
                ++count334N;
            }
        }
        if(nw>1) {
            int lo=__builtin_ctzll(a.forced),hi=63-__builtin_clzll(a.forced);
            for(int j=lo;j<=hi;j+=2) if(!(a.forced&(U(1)<<j))) {
                ++count333; gaps.push_back(i); break;
            }
        }
    }
    std::ofstream out(argv[2]);
    out<<"{\"vertices\":"<<s.v<<",\"forbidden_quads\":"<<nq<<",\"safe_states\":"<<s.values.size()
       <<",\"root\":"; write_value(out,0,s.values[root]);
    out<<",\"B334_count\":"<<count334<<",\"B334_N_count\":"<<count334N
       <<",\"B333_gap_count\":"<<count333<<",\"forced_size_hist\":{";
    bool first=true;
    for(int j=0;j<50;++j) if(forced_hist[j]) {
        if(!first) out<<',';
        first=false; out<<'"'<<j<<"\":"<<forced_hist[j];
    }
    out<<"},\"B334_witnesses\":[";
    for(size_t i=0;i<witnesses.size();++i) {
        if(i) out<<',';
        uint32_t wi=witnesses[i]; write_value(out,s.masks[wi],s.values[wi]);
    }
    out<<"],\"B333_gap_witnesses\":[";
    for(size_t i=0;i<gaps.size();++i) {
        if(i) out<<',';
        uint32_t wi=gaps[i]; write_value(out,s.masks[wi],s.values[wi]);
    }
    out<<"],\"B334_least_stone_witness\":";
    if(count334) write_value(out,s.masks[least334],s.values[least334]); else out<<"null";
    out<<",\"B334_least_N_witness\":";
    if(count334N) write_value(out,s.masks[least334N],s.values[least334N]); else out<<"null";
    out<<",\"B334_least_witness_children\":[";
    if(count334) {
        U mask=s.masks[least334], legal=s.full;
        U prefix=0;
        for(U tail=mask;tail;tail &= tail-1) {
            int p=__builtin_ctzll(tail); legal=s.after(prefix,legal,p); prefix |= U(1)<<p;
        }
        bool comma=false;
        for(U tail=legal;tail;tail &= tail-1) {
            if(comma) out<<',';
            comma=true;
            U child=mask|(tail&-tail); write_value(out,child,s.values[s.ids.at(child)]);
        }
    }
    out<<"],\"first_moves\":[";
    for(int p=0;p<s.v;++p) {
        if(p) out<<',';
        U bit=U(1)<<p; write_value(out,bit,s.values[s.ids.at(bit)]);
    }
    double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    out<<"],\"seconds\":"<<seconds<<"}\n";
    std::cout<<"DONE states="<<s.values.size()<<" B334="<<count334<<" B333_gaps="<<count333
             <<" seconds="<<seconds<<std::endl;
}
