// Safety gate for docs/10X10_CACHE_AWARE_LOSS_FIRST_ONLY_PREREG.md.
// Tests the LIVE production ordering primitive exposed by Solver.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <set>
#include <string>
#include <vector>
#define main solver_main_disabled_in_loss_first_test
#include "probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"
#undef main

using C = Solver::OrderTestChild;
constexpr std::uint32_t L = MultiDepthMemo100::Losing;
constexpr std::uint32_t W = MultiDepthMemo100::Winning;

static C mk(std::uint64_t key, int count, std::uint32_t cached) {
    C c{}; c.key = Bits{key,0}; c.count=count; c.cached=cached; return c;
}
static bool blind_lt(const C&a,const C&b){
    if(a.count!=b.count)return a.count<b.count; return a.key<b.key;
}
static std::vector<C> expected(std::vector<C> x){
    std::sort(x.begin(),x.end(),blind_lt);
    auto it=std::find_if(x.begin(),x.end(),[](const C&c){return c.cached==L;});
    if(it!=x.end()&&it!=x.begin())std::rotate(x.begin(),it,std::next(it));
    return x;
}
static bool same(const std::vector<C>&a,const std::vector<C>&b){
    if(a.size()!=b.size())return false;
    for(size_t i=0;i<a.size();++i)
        if(!(a[i].key==b[i].key)||a[i].count!=b[i].count||a[i].cached!=b[i].cached)return false;
    return true;
}
static int check(std::vector<C> x,const std::string&name){
    auto e=expected(x); Solver::order_loss_first_only_for_test(x);
    if(!same(x,e)){std::cerr<<"FAIL "<<name<<"\n";return 1;} return 0;
}
struct Rng{std::uint64_t s;std::uint64_t next(){s+=0x9E3779B97F4A7C15ULL;auto z=s;z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL;z=(z^(z>>27))*0x94D049BB133111EBULL;return z^(z>>31);}};

int main(){
    int fail=0; std::uint64_t cases=0;
    auto t=[&](std::vector<C>x,const char*n){fail+=check(std::move(x),n);++cases;};
    t({},"n0"); t({mk(1,1,0)},"n1_unknown"); t({mk(1,1,L)},"n1_loss"); t({mk(1,1,W)},"n1_win");
    t({mk(9,3,0),mk(2,1,W),mk(5,2,0)},"no_loss");
    t({mk(9,3,0),mk(2,1,W),mk(5,2,L),mk(7,2,0)},"one_loss");
    t({mk(90,9,L),mk(20,2,L),mk(10,2,0),mk(30,2,L),mk(40,4,W)},"multi_loss");
    t({mk(9,5,W),mk(7,5,L),mk(3,5,0),mk(1,5,L),mk(5,5,0)},"equal_counts_key_tie_break");
    std::vector<C> rev={mk(1,1,0),mk(2,2,W),mk(3,3,L),mk(4,4,0),mk(5,5,L)};
    std::reverse(rev.begin(),rev.end()); t(rev,"reversed");
    // Exhaustive permutations catch swap-vs-stable-promotion errors with multiple LOSS.
    {std::vector<C>b={mk(10,5,L),mk(20,5,L),mk(30,5,0),mk(40,5,W),mk(50,5,0)};int p[5]={0,1,2,3,4};do{std::vector<C>x;for(int i:p)x.push_back(b[i]);fail+=check(x,"perm5");++cases;}while(std::next_permutation(p,p+5));}
    // Fixed-seed randomized fixtures, including equal counts and arbitrary input order.
    for(int q=0;q<4096;++q){Rng r{0xC0FFEE123456789ULL+(std::uint64_t)q*0x2545F4914F6CDD1DULL};int n=(int)(r.next()%32);std::set<std::uint64_t> used;std::vector<C>x;while((int)x.size()<n){auto k=r.next();if(!used.insert(k).second)continue;int cnt=(q%3==0)?7:(int)(r.next()%12);auto z=(unsigned)(r.next()%3);x.push_back(mk(k,cnt,z==1?L:(z==2?W:0)));}fail+=check(x,"random");++cases;}
    if(fail){std::cerr<<"LOSS-FIRST SAFETY FAIL cases="<<cases<<" failures="<<fail<<"\n";return 1;}
    std::cout<<"LOSS-FIRST SAFETY PASS cases="<<cases<<"\n";return 0;
}
