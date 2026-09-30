// Look for counterexamples to B078/B361 among eight-board catalogue + one stone.
// s9=9 is now proved; this is a restricted witness search, not an n9 census.
#define main round46_tight_unused_main
#include "round46_kmin_tight.cpp"
#undef main

int main(int argc,char**argv){
  if(argc!=2)return 2;N=9;P=81;K=9;build();
  ifstream in(argv[1],ios::binary);uint64_t count,s;if(!in.read((char*)&count,8)||count!=408)return 3;
  long long embeddings=0,extensions=0,duplicates=0;
  set<pair<uint64_t,uint64_t>> seen;map<int,int> hist,releasehist;
  vector<int> b078,b361;
  vector<vector<int>> maximal_sets;
  for(uint64_t z=0;z<count;z++){
    if(!in.read((char*)&s,8))return 4;
    vector<int> old;for(int i=0;i<64;i++)if(s>>i&1)old.push_back(i);if(old.size()!=8)return 5;
    for(int dx=0;dx<2;dx++)for(int dy=0;dy<2;dy++){
      ++embeddings;vector<int> ids;Mask occupied{},base{};
      for(int a:old){int p=9*(a/8+dy)+a%8+dx;ids.push_back(p);mset(occupied,p);}
      for(int a=0;a<8;a++)for(int b=a+1;b<8;b++)for(int c=b+1;c<8;c++)mor(base,getm(ids[a],ids[b],ids[c]));
      if((base.lo&occupied.lo)||(base.hi&occupied.hi))return 6;
      for(int p=0;p<P;p++){
        if(mhas(occupied,p)||mhas(base,p))continue;++extensions;
        vector<int> current=ids;current.push_back(p);Mask occupied1=occupied;mset(occupied1,p);
        Mask blocked1=base;
        for(int a=0;a<8;a++)for(int b=a+1;b<8;b++)mor(blocked1,getm(ids[a],ids[b],p));
        Mask all1=blocked1;mor(all1,occupied1);if(mpc(all1)!=P)continue;
        if(!seen.insert({occupied1.lo,occupied1.hi}).second){++duplicates;continue;}
        maximal_sets.push_back(current);
        int covercount[100]{};Mask common[100];for(auto &m:common)m=occupied1;
        for(int a=0;a<9;a++)for(int b=a+1;b<9;b++)for(int c=b+1;c<9;c++){
          Mask t{},targets=getm(current[a],current[b],current[c]);
          mset(t,current[a]);mset(t,current[b]);mset(t,current[c]);
          for(int q=0;q<P;q++)if(mhas(targets,q)){++covercount[q];common[q].lo&=t.lo;common[q].hi&=t.hi;}
        }
        int minimum=999,releasable=0;
        for(int q=0;q<P;q++)if(!mhas(occupied1,q)){
          if(!covercount[q])return 7;minimum=min(minimum,covercount[q]);if(mpc(common[q]))++releasable;
        }
        ++hist[minimum];++releasehist[releasable];
        if(minimum>=2&&b078.empty())b078=current;
        if(!releasable&&b361.empty())b361=current;
      }
    }
  }
  {char extra;if(in.read(&extra,1))return 8;}
  cout<<"{\"n\":9,\"k\":9,\"restricted_family_complete\":true,\"embeddings\":"<<embeddings
      <<",\"extensions_checked\":"<<extensions<<",\"distinct_maximal_nine_stone_sets\":"<<seen.size()
      <<",\"duplicate_maximal_extensions\":"<<duplicates<<",\"min_b_histogram\":{";bool first=true;
  for(auto [a,b]:hist){if(!first)cout<<",";cout<<"\""<<a<<"\":"<<b;first=false;}
  cout<<"},\"one_deletion_releasable_point_histogram\":{";first=true;
  for(auto [a,b]:releasehist){if(!first)cout<<",";cout<<"\""<<a<<"\":"<<b;first=false;}
  cout<<"},\"B078_counterexample_ids\":";printv(b078);cout<<",\"B361_counterexample_ids\":";printv(b361);
  cout<<",\"maximal_sets_ids\":[";first=true;for(auto ids:maximal_sets){if(!first)cout<<",";printv(ids);first=false;}cout<<"]}\n";
}
