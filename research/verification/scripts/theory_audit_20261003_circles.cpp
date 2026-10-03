// Exhaustive maxima over ALL rational circle centers; no center cutoff.
// Build: g++ -O3 -std=c++20 theory_audit_20261003_circles.cpp -o /tmp/circle-audit
// Run: /tmp/circle-audit 60 > /tmp/circle-audit-60.json
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <vector>

struct Record {
    int32_t a,b,c;
    uint32_t pair;
    bool operator<(const Record& o) const {
        if(a!=o.a) return a<o.a;
        if(b!=o.b) return b<o.b;
        return c<o.c;
    }
    bool same(const Record& o) const {return a==o.a&&b==o.b&&c==o.c;}
};
struct Result {int count=0,ay=0,a=0,b=0,c=0;};

int main(int argc,char**argv){
    const int n=argc>1?std::atoi(argv[1]):32;
    assert(2<=n&&n<=255);
    const int nn=n*n;
    std::vector<Result> all(n+1), nonhalf(n+1);
    for(int side=2;side<=n;++side){
        all[side]={4,0,1,1,1};
        nonhalf[side]=side==2?Result{2,0,2,2,3}:Result{3,0,2,4,3};
    }
    std::vector<Record> records;
    records.reserve(int64_t(nn-1)*(nn-2)/2);
    std::vector<int> support,thresholds;
    uint64_t tested=0,groups_ge4=0;
    for(int ay=0;ay<=(n-1)/2;++ay){
        records.clear();
        for(int p=0;p<nn;++p){
            if(p==ay) continue;
            int x=p/n,y=p%n-ay,u=x*x+y*y;
            for(int q=p+1;q<nn;++q){
                if(q==ay) continue;
                int X=q/n,Y=q%n-ay,U=X*X+Y*Y;
                int a=x*Y-X*y;
                if(!a) continue;
                int b=u*Y-U*y,c=x*U-X*u;
                if(a<0){a=-a;b=-b;c=-c;}
                int d=std::gcd(a,std::gcd(std::abs(b),std::abs(c)));
                records.push_back({a/d,b/d,c/d,uint32_t(p)|(uint32_t(q)<<16)});
            }
        }
        tested+=records.size();
        std::sort(records.begin(),records.end());
        for(size_t i=0;i<records.size();){
            size_t j=i+1;
            while(j<records.size()&&records[i].same(records[j])) ++j;
            if(j-i>=3){
                ++groups_ge4;
                support.clear();support.push_back(ay);
                for(size_t k=i;k<j;++k){support.push_back(records[k].pair&65535);support.push_back(records[k].pair>>16);}
                std::sort(support.begin(),support.end());
                support.erase(std::unique(support.begin(),support.end()),support.end());
                assert((support.size()-1)*(support.size()-2)/2==j-i);
                thresholds.clear();
                for(int p:support) thresholds.push_back(1+std::max(p/n,p%n));
                std::sort(thresholds.begin(),thresholds.end());
                // Circles realizing a smaller square can be reflected there,
                // so only anchors ay <= (side-1)/2 need to update that side.
                for(int side=std::max(2,2*ay+1);side<=n;++side){
                    int count=std::upper_bound(thresholds.begin(),thresholds.end(),side)-thresholds.begin();
                    auto update=[&](Result& r){if(count>r.count)r={count,ay,records[i].a,records[i].b,records[i].c};};
                    update(all[side]);
                    if(records[i].a>1) update(nonhalf[side]);
                }
            }
            i=j;
        }
        std::cerr<<"anchor "<<ay<<"/"<<(n-1)/2<<" records="<<records.size()<<" max="<<all[n].count<<" nonhalf="<<nonhalf[n].count<<"\n";
    }
    std::cout<<"{\"max_side\":"<<n<<",\"noncollinear_anchor_pairs\":"<<tested<<",\"circle_anchor_groups_ge4\":"<<groups_ge4<<",\"results\":[\n";
    for(int side=2;side<=n;++side){
        auto emit=[&](const Result&r){std::cout<<"{\"count\":"<<r.count<<",\"anchor\":[0,"<<r.ay<<"],\"equation\":["<<r.a<<","<<r.b<<","<<r.c<<"]}";};
        std::cout<<"{\"n\":"<<side<<",\"all\":";emit(all[side]);std::cout<<",\"nonhalf\":";emit(nonhalf[side]);std::cout<<"}"<<(side==n?"\n":",\n");
    }
    std::cout<<"]}\n";
}
