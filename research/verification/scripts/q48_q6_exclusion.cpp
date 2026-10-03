// Exact necessary-condition search for deficient maximal q=6 positions on 4xm.
// Every target-row subset of size <=4 is checked, up to horizontal reflection.
// A state cap produces UNKNOWN, never an exclusion claim.
#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <set>
#include <unordered_set>
#include <vector>
using Mask=std::bitset<272>;
struct Circle {Mask mask; std::vector<int> points;};
struct Option {Mask mask; std::vector<int> points;};
struct BaseOption {Option option; int absent_partner;};
struct Candidate {Mask mask; std::vector<int> added;};
int m,target;std::uint64_t cap,nodes,total_nodes,demand_prunes;bool aborted;Mask found;
std::array<Mask,4> row_masks;
std::vector<Circle> circles;
std::vector<std::vector<const Option*>> choices;
std::unordered_set<Mask> failed;
std::vector<std::vector<BaseOption>> base_options;
std::vector<std::vector<std::vector<Option>>> pair_options;
std::vector<std::vector<int>> incident;
std::vector<int> circle_counts;
std::array<int,4> row_counts{};
std::vector<std::uint64_t> checked;
std::uint64_t stamp=0;

bool safe(const Mask& s){
 for(const auto& row:row_masks)if((s&row).count()>5)return false;
 for(const auto& c:circles)if((s&c.mask).count()>5)return false;
 return true;
}
void update_counts(const std::vector<int>& points,int sign){
 for(int p:points){row_counts[p/m]+=sign;for(int id:incident[p])circle_counts[id]+=sign;}
}
bool extend(const Mask& s,const Option& option,Candidate& out){
 out.mask=s|option.mask;out.added.clear();std::array<int,4> delta{};
 for(int p:option.points)if(!s.test(p)){out.added.push_back(p);++delta[p/m];}
 for(int y=0;y<4;y++)if(row_counts[y]+delta[y]>5)return false;
 ++stamp;
 for(int p:out.added)for(int id:incident[p])if(checked[id]!=stamp){
  checked[id]=stamp;int extra=0;
  for(int v:out.added)extra+=circles[id].mask.test(v);
  if(circle_counts[id]+extra>5)return false;
 }
 return true;
}
bool visit(const Mask& s){
 if(failed.count(s))return false;
 if(++nodes>cap){aborted=true;return false;}
 std::vector<Candidate> best;bool pending=false;
 std::array<std::vector<std::pair<Mask,int>>,4> demands;
 for(const auto& opts:choices){
  bool covered=false;for(const auto* o:opts)if((s&o->mask)==o->mask){covered=true;break;}
  if(covered)continue;
  std::vector<Candidate> next;
  for(const auto* o:opts){Candidate z;if(extend(s,*o,z)){
   if(std::none_of(next.begin(),next.end(),[&](const auto& x){return x.mask==z.mask;}))next.push_back(std::move(z));
  }}
  if(next.empty()){failed.insert(s);return false;}
  if(m>=26){
   std::array<Mask,4> support;std::array<int,4> minimum{6,6,6,6};
   for(const auto& z:next){std::array<int,4> count{};
    for(int p:z.added){support[p/m].set(p);++count[p/m];}
    for(int y=0;y<4;y++)minimum[y]=std::min(minimum[y],count[y]);
   }
   for(int y=0;y<4;y++)if(minimum[y])demands[y].push_back({support[y],minimum[y]});
  }
  if(!pending||next.size()<best.size()){best=std::move(next);pending=true;}
  // One remaining option is forced.  Other constraints can be checked after
  // applying it; this changes search order but never drops a possible solution.
  if(best.size()==1)break;
 }
 if(m>=26)for(int y=0;y<4;y++)for(int reverse=0;reverse<2;reverse++){
  Mask used;int required=0;const auto& ds=demands[y];
  for(unsigned j=0;j<ds.size();j++){
   const auto& d=ds[reverse?ds.size()-1-j:j];
   if((used&d.first).none()){used|=d.first;required+=d.second;}
  }
  if(required+row_counts[y]>5){++demand_prunes;failed.insert(s);return false;}
 }
 if(!pending){found=s;return true;}
 for(const auto& z:best){update_counts(z.added,1);bool win=visit(z.mask);update_counts(z.added,-1);if(win)return true;if(aborted)return false;}
 failed.insert(s);return false;
}
std::vector<Circle> generate_circles(int width){
 std::vector<std::vector<int>> products(2*width-1);
 for(int a=0;a<width;a++)for(int b=a+1;b<width;b++)products[a+b].push_back(a*b);
 std::set<std::array<int,4>> keys;
 for(int i=0;i<4;i++)for(int j=i+1;j<4;j++){
  int h=j-i;
  for(int s=0;s<2*width-1;s++)for(int pa:products[s])for(int pb:products[s]){
   int c=pb-pa-h*(i+j),d=h*pa-h*i*i-c*i;
   std::array<int,4> key{h,-s*h,c,d};int g=0;
   for(int v:key)g=std::gcd(g,v);for(int&v:key)v/=g;keys.insert(key);
  }
 }
 std::vector<Circle> out;
 for(const auto& key:keys){
  auto [a,b,c,d]=key;Circle curve;
  for(int y=0;y<4;y++){
   long long disc=1LL*b*b-4LL*a*(a*y*y+c*y+d);
   if(disc<0)continue;
   long long root=std::sqrt((long double)disc);
   while((root+1)*(root+1)<=disc)++root;while(root*root>disc)--root;
   if(root*root!=disc)continue;
   for(long long sign:{-1LL,1LL}){
    long long numerator=-b+sign*root;if(numerator%(2*a))continue;
    long long x=numerator/(2*a);if(x<0||x>=width)continue;
    int k=y*width+(int)x;if(!curve.mask.test(k)){curve.mask.set(k);curve.points.push_back(k);}
   }
  }
  if(curve.points.size()>=6)out.push_back(std::move(curve));
 }
 return out;
}
void add_subsets(const std::vector<int>& vs,int need,std::vector<Option>& out){
 for(unsigned bits=0;bits<(1U<<vs.size());bits++)if(__builtin_popcount(bits)==need){
  Option z;for(unsigned i=0;i<vs.size();i++)if(bits>>i&1U){z.mask.set(vs[i]);z.points.push_back(vs[i]);}out.push_back(std::move(z));
 }
}
void prepare_options(){
 base_options.assign(m,{});pair_options.assign(m,std::vector<std::vector<Option>>(m));
 for(const auto& c:circles){
  std::vector<int> in,out;
  for(int k:c.points)(k/m==target?in:out).push_back(k);
  for(int k:in){
   int x=k%m,partner=-1;for(int other:in)if(other!=k)partner=other%m;
   std::vector<Option> base;add_subsets(out,5,base);
   for(const auto& option:base)base_options[x].push_back({option,partner});
   if(partner>=0)add_subsets(out,4,pair_options[x][partner]);
  }
 }
}
std::uint64_t all_subsets,representatives,searched,unknown;bool any_found;
void test_subset(const std::vector<int>& subset){
 ++all_subsets;
 std::vector<int> reflected;for(auto i=subset.rbegin();i!=subset.rend();i++)reflected.push_back(m-1-*i);
 if(subset>reflected)return;
 ++representatives;
 Mask occupied;std::vector<bool> selected(m,false);
 for(int x:subset){occupied.set(target*m+x);selected[x]=true;}
 row_counts.fill(0);std::fill(circle_counts.begin(),circle_counts.end(),0);
 std::vector<int> occupied_points;for(int x:subset)occupied_points.push_back(target*m+x);update_counts(occupied_points,1);
 choices.clear();
 for(int x=0;x<m;x++)if(!selected[x]){
  std::vector<const Option*> options;
  // An initial option puts 4 or 5 exterior points on one circle, which then
  // contains exactly 5 occupied points including the required target partner.
  // Any distinct circle meets those exterior points in at most 2 points and
  // the target row in at most 2, so it cannot contain 6 occupied points.
  // Thus every applicable initial option is automatically safe.
  for(const auto& o:base_options[x])if(o.absent_partner<0||!selected[o.absent_partner])options.push_back(&o.option);
  for(int y:subset)for(const auto& o:pair_options[x][y])options.push_back(&o);
  if(options.empty())return;
  choices.push_back(std::move(options));
 }
 std::stable_sort(choices.begin(),choices.end(),[](const auto& a,const auto& b){return a.size()<b.size();});
 ++searched;failed.clear();nodes=0;aborted=false;
 if(visit(occupied)){
  any_found=true;
  // Extend the forced witness to a maximal safe configuration.
  for(int k=0;k<4*m;k++)if(!found.test(k)){Mask z=found;z.set(k);if(safe(z))found=z;}
  std::cerr<<"WITNESS m="<<m<<" target="<<target<<"\n";
  for(int y=0;y<4;y++){for(int x=0;x<m;x++)if(found.test(y*m+x))std::cerr<<x<<",";std::cerr<<"\n";}
 }
 total_nodes+=nodes;if(aborted)++unknown;
}
void subsets(int next,int remaining,std::vector<int>& subset){
 if(any_found)return;
 if(!remaining){test_subset(subset);return;}
 for(int x=next;x<=m-remaining;x++){
  subset.push_back(x);subsets(x+1,remaining-1,subset);subset.pop_back();if(any_found)return;
 }
}
int main(int argc,char**argv){
 int lo=argc>1?std::atoi(argv[1]):16,hi=argc>2?std::atoi(argv[2]):lo;
 cap=argc>3?std::strtoull(argv[3],nullptr,10):1000000;
 if(lo<6||hi>68||lo>hi||!cap)return 2;
 bool any_unknown=false;
 for(m=lo;m<=hi;m++){
  circles=generate_circles(m);for(auto& row:row_masks)row.reset();
  incident.assign(4*m,{});circle_counts.assign(circles.size(),0);checked.assign(circles.size(),0);
  for(unsigned id=0;id<circles.size();id++)for(int p:circles[id].points)incident[p].push_back(id);
  for(int y=0;y<4;y++)for(int x=0;x<m;x++)row_masks[y].set(y*m+x);
  for(target=0;target<2;target++){
   auto start=std::chrono::steady_clock::now();prepare_options();
   all_subsets=representatives=searched=unknown=total_nodes=demand_prunes=0;any_found=false;
   std::vector<int> subset;for(int size=0;size<=4&&!any_found;size++)subsets(0,size,subset);
   double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
   std::cout<<"{\"m\":"<<m<<",\"target_row\":"<<target<<",\"circles\":"<<circles.size()
    <<",\"target_subsets\":"<<all_subsets<<",\"reflection_representatives\":"<<representatives
    <<",\"searched_subsets\":"<<searched<<",\"visited_states\":"<<total_nodes
    <<",\"disjoint_support_prunes\":"<<demand_prunes
    <<",\"unknown_subsets\":"<<unknown<<",\"found_witness\":"<<(any_found?"true":"false")
    <<",\"seconds\":"<<seconds<<"}"<<std::endl;
   if(any_found)return 3;
   if(unknown)any_unknown=true;
  }
 }
 return any_unknown?4:0;
}
