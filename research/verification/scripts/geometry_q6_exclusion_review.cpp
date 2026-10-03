// Independent implementation audit for q48_q6_exclusion.cpp.
// Compile without -DNDEBUG so all exact comparison assertions remain active.
// The production circle generator uses two horizontal pairs; this oracle uses
// every noncollinear triple and solves its circumcircle independently.
// The transition audit compares incremental checks against complete scans.
#ifdef NDEBUG
#error "The audit must be compiled with assertions enabled"
#endif
// Renaming main removes its implicit return-0 exception. The unused renamed
// function is never called, so suppress only that resulting compiler warning.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#define main exclusion_program_main
#include "q48_q6_exclusion.cpp"
#undef main
#pragma GCC diagnostic pop
#include <random>
std::set<std::string> triple_masks(int width){
 std::set<std::array<long long,4>> keys;
 int n=4*width;
 for(int p=0;p<n;p++)for(int q=p+1;q<n;q++)for(int r=q+1;r<n;r++){
  long long x=p%width,y=p/width,u=q%width-x,v=q/width-y,s=r%width-x,t=r/width-y;
  long long a=u*t-v*s;if(!a)continue;
  long long b=-(u*u+v*v)*t+(s*s+t*t)*v,c=-(s*s+t*t)*u+(u*u+v*v)*s;
  long long d=a*(x*x+y*y)-b*x-c*y;b-=2*a*x;c-=2*a*y;
  std::array<long long,4> k{a,b,c,d};long long g=0;for(auto value:k)g=std::gcd(g,value);if(a<0)g=-g;for(auto& value:k)value/=g;keys.insert(k);
 }
 std::set<std::string> out;
 for(auto k:keys){Mask z;for(int p=0;p<n;p++){long long x=p%width,y=p/width;if(k[0]*(x*x+y*y)+k[1]*x+k[2]*y+k[3]==0)z.set(p);}if(z.count()>=6)out.insert(z.to_string());}
 return out;
}
int main(){
 std::mt19937 rng(142857);long long transitions=0,total_circles=0,accepted=0,rejected=0;
 for(m=6;m<=20;m++){
  circles=generate_circles(m);std::set<std::string> actual;for(auto& c:circles)actual.insert(c.mask.to_string());
  assert(actual==triple_masks(m));total_circles+=actual.size();
  incident.assign(4*m,{});circle_counts.assign(circles.size(),0);checked.assign(circles.size(),0);
  for(auto& row:row_masks)row.reset();for(int p=0;p<4*m;p++)row_masks[p/m].set(p);
  for(unsigned i=0;i<circles.size();i++)for(int p:circles[i].points)incident[p].push_back(i);
  for(int trial=0;trial<1000;trial++){
   Mask state;std::vector<int> active;row_counts.fill(0);std::fill(circle_counts.begin(),circle_counts.end(),0);
   for(int k=0;k<25;k++){int p=rng()%(4*m);if(state.test(p))continue;Mask next=state;next.set(p);if(safe(next)){state=next;active.push_back(p);}}
   update_counts(active,1);assert(safe(state));Option option;
   for(int k=0;k<6;k++){int p=rng()%(4*m);if(!option.mask.test(p)){option.mask.set(p);option.points.push_back(p);}}
   Candidate candidate;bool ok=extend(state,option,candidate);assert(ok==safe(state|option.mask));
   if(ok){++accepted;update_counts(candidate.added,1);for(int y=0;y<4;y++)assert(row_counts[y]==(candidate.mask&row_masks[y]).count());for(unsigned i=0;i<circles.size();i++)assert(circle_counts[i]==(candidate.mask&circles[i].mask).count());update_counts(candidate.added,-1);}else ++rejected;
   for(int y=0;y<4;y++)assert(row_counts[y]==(state&row_masks[y]).count());for(unsigned i=0;i<circles.size();i++)assert(circle_counts[i]==(state&circles[i].mask).count());transitions++;
  }
 }
 std::cout<<"{\n"
  <<"  \"status\": \"passed\",\n"
  <<"  \"rectangle_rows\": 4,\n"
  <<"  \"length_min\": 6,\n"
  <<"  \"length_max\": 20,\n"
  <<"  \"all_three_point_circle_generation_matches\": true,\n"
  <<"  \"total_distinct_six_or_more_point_circles_across_lengths\": "<<total_circles<<",\n"
  <<"  \"pseudorandom_seed\": 142857,\n"
  <<"  \"direct_safety_transition_checks\": "<<transitions<<",\n"
  <<"  \"accepted_transitions_with_update_and_undo_checks\": "<<accepted<<",\n"
  <<"  \"rejected_transitions\": "<<rejected<<",\n"
  <<"  \"safety_and_counter_mismatches\": 0,\n"
  <<"  \"search_tree_exhaustion_checked_by_this_audit\": false\n"
  <<"}\n";
}
