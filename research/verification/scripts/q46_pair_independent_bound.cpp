// Independent finite certificate for three-row q=6 blocker bounds in four rows.
// The horizontal diameter is at most 67 (enough for every board length <=68).
// Five translated B points are enumerated without using reflection symmetry.
// Profiles come from a circle equation through two horizontal pairs.
// For each resulting weighted C graph, enumerate ALL subsets of size <=5
// inside each connected component and combine components by exact knapsack.
// This does not use connected-subset expansion or the 2+3 partition bound
// used by q46_pair_bound.cpp. Negative C/target coordinates are permitted;
// each individual circle plus all B points must have diameter at most D.
// The component optimization omits further whole-C diameter and safety tests,
// so every genuine configuration is included and the reported bounds are safe.
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <numeric>
#include <queue>
#include <tuple>
#include <vector>
using namespace std;
struct Profile{int c,t;};
int main(int argc,char** argv){
 int D=argc>1?atoi(argv[1]):67,which=argc>2?atoi(argv[2]):-1;
 if(D<4||D>67||which < -1||which>4)return 2;
 int poses[5][3]={{0,1,2},{0,1,3},{0,2,3},{1,0,2},{1,0,3}};
 for(int shape=0;shape<5;shape++){
  if(which>=0&&shape!=which)continue;
  int limits[5]={6,6,7,6,7};int limit=limits[shape];if(shape==0&&D<=35)limit=5;
  int t=poses[shape][0],v=poses[shape][1],w=poses[shape][2];
  vector<vector<Profile>> profiles(D+1);int pc=0;
  for(int db=1;db<=D;db++)for(int dc=1;dc<=D;dc++){
   if((db-dc)%2)continue;
   long long a=w-v,b=-a*db,c=(db*db-dc*dc)/4-a*(v+w),d=-a*v*v-c*v;
   long long disc=b*b-4*a*(a*t*t+c*t+d);if(disc<=0)continue;
   long long r=sqrt((long double)disc);while(r*r<disc)r++;while(r*r>disc)r--;if(r*r!=disc||r%a)continue;
   int dt=r/a;if(dt>D||(db-dt)%2)continue;
   profiles[db].push_back({dc,dt});pc++;
  }
  long long sets=0,graphs=0,combinations=0;int max_component=0,bound=0;
  array<int,5> witness{};vector<int> selected_witness;
  for(int end=4;end<=D;end++)for(int b1=1;b1<end;b1++)for(int b2=b1+1;b2<end;b2++)for(int b3=b2+1;b3<end;b3++){
   array<int,5>B{0,b1,b2,b3,end};sets++;vector<pair<int,int>> raw;
   for(int i=0;i<5;i++)for(int j=i+1;j<5;j++)for(auto p:profiles[B[j]-B[i]]){
    int s=B[i]+B[j],loC=(s-p.c)/2,hiC=(s+p.c)/2,loT=(s-p.t)/2,hiT=(s+p.t)/2;
    if(max({end,hiC,hiT})-min({0,loC,loT})<=D)raw.push_back({loC,hiC});
   }
   if(raw.size()<=(unsigned)limit)continue;graphs++;
   vector<int> coords;for(auto e:raw){coords.push_back(e.first);coords.push_back(e.second);}sort(coords.begin(),coords.end());coords.erase(unique(coords.begin(),coords.end()),coords.end());int n=coords.size();
   vector<vector<int>> weights(n,vector<int>(n));
   for(auto e:raw){int x=lower_bound(coords.begin(),coords.end(),e.first)-coords.begin(),y=lower_bound(coords.begin(),coords.end(),e.second)-coords.begin();weights[x][y]++;weights[y][x]++;}
   vector<int> seen(n);array<int,6> dp;dp.fill(-1000);dp[0]=0;
   for(int seed=0;seed<n;seed++)if(!seen[seed]){
    vector<int> component;queue<int> queue;queue.push(seed);seen[seed]=1;
    while(!queue.empty()){int x=queue.front();queue.pop();component.push_back(x);for(int y=0;y<n;y++)if(weights[x][y]&&!seen[y]){seen[y]=1;queue.push(y);}}
    max_component=max(max_component,(int)component.size());array<int,6> local;local.fill(-1000);local[0]=0;vector<int> chosen;
    function<void(int,int)> enumerate=[&](int first,int value){
     local[chosen.size()]=max(local[chosen.size()],value);combinations++;
     if(chosen.size()==5)return;
     for(int j=first;j<(int)component.size();j++){int x=component[j],extra=0;for(int y:chosen)extra+=weights[x][y];chosen.push_back(x);enumerate(j+1,value+extra);chosen.pop_back();}
    };
    enumerate(0,0);array<int,6> next;next.fill(-1000);
    for(int i=0;i<=5;i++)for(int j=0;i+j<=5;j++)next[i+j]=max(next[i+j],dp[i]+local[j]);dp=next;
   }
   int current=*max_element(dp.begin(),dp.end());if(current>bound){bound=current;witness=B;cerr<<"shape "<<shape<<" bound "<<bound<<" B";for(int x:B)cerr<<' '<<x;cerr<<"\n";}
   if(bound>limit){cout<<"FAIL bound exceeds target\n";return 3;}
  }
  cout<<"{\"D\":"<<D<<",\"shape\":"<<shape<<",\"profiles\":"<<pc<<",\"normalized_B_sets\":"<<sets<<",\"graphs_needing_exact_optimization\":"<<graphs<<",\"component_subsets\":"<<combinations<<",\"max_component_size\":"<<max_component<<",\"heavy_graph_exact_maximum\":"<<bound<<",\"universal_upper_bound\":"<<limit<<"}"<<endl;
 }
}
