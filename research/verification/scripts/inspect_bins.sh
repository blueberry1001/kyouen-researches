#!/bin/bash
# Inspect the committed .bin files: count + size distribution.
cat > /tmp/insp.cpp <<'EOF'
#include <cstdio>
#include <cstdint>
#include <map>
#include <vector>
#include <algorithm>
using u64 = uint64_t;
int main(int argc,char**argv){
  for(int i=1;i<argc;++i){
    FILE*f=fopen(argv[i],"rb"); if(!f){printf("%s MISSING\n",argv[i]);continue;}
    u64 c=0; if(fread(&c,sizeof c,1,f)!=1){fclose(f);printf("%s BAD\n",argv[i]);continue;}
    std::vector<u64> v(c); size_t rd=fread(v.data(),8,c,f); v.resize(rd); fclose(f);
    std::map<int,int> h; for(u64 m:v) h[__builtin_popcountll(m)]++;
    printf("%-70s count=%-10zu sizes:",argv[i],v.size());
    for(auto&kv:h) printf(" %d:%d",kv.first,kv.second);
    printf("\n");
  }
}
EOF
g++ -O2 -o /tmp/insp /tmp/insp.cpp && /tmp/insp \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/night-research/maxsafe_n6_K11.bin \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/night-research/maxsafe_n7_K14.bin \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/kc_maximal_n5_k8.bin \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/kc_maximal_n6_k10.bin \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/maximal_n4.bin \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/maximal_n5.bin \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/safe_n6_k10.bin \
  /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/data/safe_n7_k13.bin
