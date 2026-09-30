// Exhaust all translated complete n8 eight-stone maximal catalogue extensions.
// This does not exhaust n10 configurations: no witness means only this family failed.
#define main round46_tight_unused_main
#include "round46_kmin_tight.cpp"
#undef main

int main(int argc,char**argv){
  if(argc<2||argc>3)return 2;
  N=10;P=100;K=argc==3?atoi(argv[2]):10;if(K!=9&&K!=10)return 2;build();
  ifstream in(argv[1],ios::binary);uint64_t count,s;
  if(!in.read((char*)&count,8)||count!=408)return 3;
  long long embeddings=0,ones=0,twos=0;map<int,int> hist;
  vector<int> answer,source_ids;int dx_w=-1,dy_w=-1;uint64_t mask_w=0;
  for(uint64_t z=0;z<count;z++){
    if(!in.read((char*)&s,8))return 4;
    vector<int> old;for(int i=0;i<64;i++)if(s>>i&1)old.push_back(i);
    if(old.size()!=8)return 5;
    for(int dx=0;dx<3;dx++)for(int dy=0;dy<3;dy++){
      vector<int> ids;Mask occupied{},base{};
      for(int a:old){int p=10*(a/8+dy)+a%8+dx;ids.push_back(p);mset(occupied,p);}
      for(int a=0;a<8;a++)for(int b=a+1;b<8;b++)for(int c=b+1;c<8;c++)mor(base,getm(ids[a],ids[b],ids[c]));
      if((base.lo&occupied.lo)||(base.hi&occupied.hi))return 6;
      vector<int> legal;for(int p=0;p<100;p++)if(!mhas(base,p)&&!mhas(occupied,p))legal.push_back(p);
      ++embeddings;++hist[legal.size()];
      for(int p:legal){
        ++ones;Mask blocked1=base,occupied1=occupied;mset(occupied1,p);
        for(int a=0;a<8;a++)for(int b=a+1;b<8;b++)mor(blocked1,getm(ids[a],ids[b],p));
        vector<int> current=ids;current.push_back(p);
        Mask all1=blocked1;mor(all1,occupied1);
        if(mpc(all1)==100){answer=current;source_ids=old;dx_w=dx;dy_w=dy;mask_w=s;goto done;}
        if(K==9)continue;
        for(int q:legal){
          if(q<=p||mhas(blocked1,q))continue;
          ++twos;Mask all2=all1;mset(all2,q);
          for(int a=0;a<9;a++)for(int b=a+1;b<9;b++)mor(all2,getm(current[a],current[b],q));
          if(mpc(all2)==100){answer=current;answer.push_back(q);source_ids=old;dx_w=dx;dy_w=dy;mask_w=s;goto done;}
        }
      }
    }
  }
  {char extra;if(in.read(&extra,1))return 7;}
done:
  cout<<"{\"n\":10,\"stone_count_limit\":"<<K<<",\"family\":\"408 n8 maximal eight-stone sets, translations dx/dy 0..2, up to K-8 added stones\",\"family_complete\":"<<(answer.empty()?"true":"false")
      <<",\"embeddings_checked\":"<<embeddings<<",\"one_extensions_checked\":"<<ones<<",\"two_extensions_checked\":"<<twos
      <<",\"source_mask\":"<<mask_w<<",\"translation\":["<<dx_w<<","<<dy_w<<"],\"source_ids\":";printv(source_ids);
  cout<<",\"witness_ids\":";printv(answer);cout<<",\"legal_count_histogram\":{";bool first=true;
  for(auto [a,b]:hist){if(!first)cout<<",";cout<<"\""<<a<<"\":"<<b;first=false;}cout<<"}}\n";
  return 0;
}
