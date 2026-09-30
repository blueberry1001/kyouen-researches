// Independent variant: full curve occupancies, affected-curve updates,
// ascending move order. No quad-completion masks from the first solver.
#include "round32_standard_table.h"
#include <cstdio>
#include <fstream>
#include <unordered_map>
using U=uint64_t;
struct Search {
    int v;U full,removed,target;uint64_t states=0,shortcuts=0,limit;
    std::vector<U> curves;std::vector<std::vector<U>> incidence;
    std::unordered_map<U,uint8_t> memo;const Standard& standard;
    explicit Search(const Standard& table):standard(table){}
    U after(U s,U legal,int p)const{
        U next=s|(U(1)<<p);legal&=~(U(1)<<p);
        for(U c:incidence[p]){U selected=next&c;int occupied=__builtin_popcountll(selected);
            if(occupied==3){U blocked=c;if(c==target&&(selected&removed)==selected)blocked&=~removed;legal&=~blocked;}
            else if(occupied>=4){if(c!=target||occupied!=4||selected!=removed)throw std::logic_error("unsafe curve state");legal&=~c;}
        }
        return legal;
    }
    bool win(U s,U legal){auto found=memo.find(s);if(found!=memo.end())return found->second;
        if(++states>limit)throw std::runtime_error("budget");
        if(removed&~(s|legal)){++shortcuts;bool value=standard.win(s);memo.emplace(s,value);return value;}
        struct Move{int p,priority;U next;};std::vector<Move> moves;
        for(U x=legal;x;x&=x-1){int p=__builtin_ctzll(x);U c=s|(U(1)<<p),next=after(s,legal,p);
            if(removed&~(c|next)){++shortcuts;if(!standard.win(c)){memo.emplace(s,1);return true;}continue;}
            int priority=(c&removed)==removed?0:standard.win(c)?2:1;moves.push_back({p,priority,next});
        }
        std::stable_sort(moves.begin(),moves.end(),[](auto a,auto b){return a.priority<b.priority;});
        for(auto move:moves)if(!win(s|(U(1)<<move.p),move.next)){memo.emplace(s,1);return true;}
        memo.emplace(s,0);return false;
    }
    int run(U q){removed=q;int count=0;for(U c:curves)if((c&q)==q){target=c;++count;}if(count!=1)throw std::logic_error("curve not unique");
        states=shortcuts=0;memo.clear();try{return win(0,full);}catch(const std::runtime_error&){return -1;}}
};
int main(int argc,char**argv){if(argc!=5)return 1;Standard standard(argv[2]);Search S(standard);std::ifstream in(argv[1]);int nq,count,nc;
    if(!(in>>S.v>>nq>>count)||S.v!=49)return 5;S.full=(U(1)<<S.v)-1;S.limit=std::stoull(argv[4]);
    std::vector<U> quads(nq);for(U&q:quads)in>>q;std::vector<int> reps(count);for(int&r:reps)in>>r;
    in>>nc;S.curves.resize(nc);for(U&c:S.curves)in>>c;S.incidence.resize(S.v);
    for(U c:S.curves)for(U x=c;x;x&=x-1)S.incidence[__builtin_ctzll(x)].push_back(c);
    S.memo.reserve(std::min<uint64_t>(S.limit,4000000));if(standard.win(0))return 6;
    std::ofstream out(argv[3]);out<<"{\"n\":7,\"standard_outcome\":0,\"node_budget\":"<<S.limit<<",\"representatives_total\":"<<count<<",\"cases\":[";
    int done=0,unknown=0,flips=0;
    for(int index:reps){int value=S.run(quads[index]);if(done)out<<',';out<<"{\"removed_index\":"<<index<<",\"removed_mask\":"<<S.removed<<",\"outcome\":"<<value<<",\"states\":"<<S.states<<",\"standard_shortcuts\":"<<S.shortcuts<<"}"<<std::flush;
        ++done;unknown+=value<0;flips+=value==1;
        if(done%25==0||done==count){fprintf(stderr,"curve verified=%d unknown=%d flips=%d\n",done,unknown,flips);fflush(stderr);}
    }
    out<<"],\"checked\":"<<done<<",\"unknown\":"<<unknown<<",\"flips\":"<<flips<<",\"all_representatives_processed\":true}\n";
}
