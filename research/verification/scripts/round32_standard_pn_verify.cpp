// Verify every standard P/N label by local proof obligations using whole-curve
// legality from independently generated integer geometry. Does not fill a DP.
#include "round32_standard_table.h"
#include <cstdio>
#include <fstream>
using U=uint64_t;
int main(int argc,char**argv){
    if(argc!=4)return 1;std::ifstream in(argv[1]);int v,nq,count,nc;in>>v>>nq>>count;
    U discarded;for(int i=0;i<nq;++i)in>>discarded;int ignored;for(int i=0;i<count;++i)in>>ignored;
    in>>nc;std::vector<U> curves(nc);for(U&c:curves)in>>c;if(!in||v!=49)return 2;
    Standard standard(argv[2]);U full=(U(1)<<v)-1;FILE*out=fopen(argv[3],"w");if(!out)return 3;
    fprintf(out,"{\"vertices\":49,\"curves\":%d,\"levels\":[",nc);unsigned long long total=0;
    for(int k=int(standard.layers.size())-1;k>=0;--k){auto A=standard.layers[k];unsigned long long np=0;
        #pragma omp parallel for schedule(dynamic,4096) reduction(+:np)
        for(long long i=0;i<(long long)A.count;++i){U s=A.masks[i],legal=full^s;
            if(A.pn[i]>1)exit(4);
            for(U c:curves){int stones=__builtin_popcountll(s&c);if(stones>3)exit(5);if(stones==3)legal&=~c;}
            bool has_P=false;
            for(U x=legal;x;x&=x-1){if(k+1>=int(standard.layers.size()))exit(6);auto C=standard.layers[k+1];U child=s|(x&-x);
                auto p=std::lower_bound(C.masks,C.masks+C.count,child);if(p==C.masks+C.count||*p!=child)exit(7);
                if(!C.pn[p-C.masks]){has_P=true;break;}
            }
            if(has_P!=bool(A.pn[i])){fprintf(stderr,"incorrect P/N label k=%d mask=%llu\n",k,(unsigned long long)s);exit(8);}
            np+=!A.pn[i];
        }
        fprintf(out,"%s{\"k\":%d,\"checked\":%zu,\"P\":%llu}",k==int(standard.layers.size())-1?"":",",k,A.count,np);fflush(out);
        fprintf(stderr,"whole-curve P/N proof checked k=%d states=%zu P=%llu\n",k,A.count,np);fflush(stderr);total+=A.count;
    }
    fprintf(out,"],\"checked_states\":%llu,\"all_local_proof_obligations_pass\":true}\n",total);fclose(out);
}
