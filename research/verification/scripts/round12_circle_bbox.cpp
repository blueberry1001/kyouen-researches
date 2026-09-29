// Exact finite census for B454.  g++ -O3 -std=c++17 this.cpp -o census.exe
// Usage: census.exe W [both|power2|odd] > result.json.
// W is the coordinate span (board side W+1).
// Every complete circle with >=4 lattice points fitting such a square can be
// translated so its lowest leftmost point is (0,0). Two other points determine
// A(x*x+y*y)=D*x+E*y. Pair multiplicity >=3 is necessary for >=4 points.
// All decisions, including square roots, use integers. No floating point.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <numeric>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
using I = int64_t;
using Key = std::array<I,3>;
using Pt = std::pair<I,I>;
struct Hash {
    size_t operator()(const Key& k) const {
        uint64_t h=1469598103934665603ULL;
        for(I v:k) { h ^= uint64_t(v); h *= 1099511628211ULL; }
        return size_t(h);
    }
};
I root(I n) {
    assert(n>=0);
    uint64_t rem=uint64_t(n), r=0, bit=uint64_t(1)<<62;
    while(bit>rem) bit>>=2;
    while(bit) {
        if(rem>=r+bit) { rem-=r+bit; r=(r>>1)+bit; }
        else r>>=1;
        bit>>=2;
    }
    return I(r);
}
I floor_div(I a,I b) { assert(b>0); I t=a/b; return t-(a%b<0); }
I ceil_div(I a,I b) { return -floor_div(-a,b); }
I denominator(const Key& k) { return 2*k[0]/std::gcd(2*k[0],std::gcd(std::abs(k[1]),std::abs(k[2]))); }
int family(I q) { return (q&(q-1))==0 ? 0 : (q%2 ? 1 : -1); }
struct Record { I span=0,q=0; Key key{}; std::vector<Pt> pts; };
int main(int argc,char**argv) {
    const I w=argc>1?std::stoll(argv[1]):24;
    const std::string selection=argc>2?argv[2]:"both";
    if(selection!="both" && selection!="power2" && selection!="odd") return 2;
    // Coefficient and discriminant bounds in this implementation fit int64.
    if(w<1 || w>256) { std::cerr<<"require 1 <= W <= 256\n"; return 2; }
    std::vector<Pt> pts;
    for(I x=0;x<=w;++x) for(I y=-w;y<=w;++y)
        if(x>0 || y>0) pts.emplace_back(x,y);
    std::unordered_map<Key,uint32_t,Hash> keys;
    I pairs=0, selected=0;
    for(size_t i=0;i<pts.size();++i) for(size_t j=i+1;j<pts.size();++j) {
        auto [x,y]=pts[i]; auto [u,v]=pts[j];
        if(std::max({I(0),y,v})-std::min({I(0),y,v})>w) continue;
        I a=x*v-y*u;
        if(!a) continue;
        ++pairs;
        I d=(x*x+y*y)*v-(u*u+v*v)*y;
        I e=x*(u*u+v*v)-u*(x*x+y*y);
        if(a<0) { a=-a;d=-d;e=-e; }
        if(selection=="power2") {
            // Primitive A is a power of two iff the entire odd part of the
            // determinant divides both other coefficients. Exact early filter.
            I odd=a;
            while(odd%2==0) odd/=2;
            if(d%odd || e%odd) continue;
        }
        I g=std::gcd(a,std::gcd(std::abs(d),std::abs(e)));
        Key key={a/g,d/g,e/g};
        int f=family(denominator(key));
        if(f<0 || (selection=="power2" && f!=0) || (selection=="odd" && f!=1)) continue;
        ++selected;
        ++keys[key];
    }
    std::map<std::pair<int,I>,Record> best;
    std::map<std::pair<int,I>,I> counts;
    I checked=0, complete=0, x_scans=0;
    for(const auto& item:keys) {
        if(item.second<3) continue;
        ++checked;
        const auto k=item.first; const I a=k[0],d=k[1],e=k[2];
        I r=root(d*d+e*e), lo=ceil_div(d-r,2*a), hi=floor_div(d+r,2*a);
        std::vector<Pt> cp;
        I ymin=0,ymax=0,xmax=0; bool reject=false;
        for(I x=lo;x<=hi && !reject;++x) {
            ++x_scans;
            I h2=e*e-4*a*(a*x*x-d*x);
            if(h2<0) continue;
            I h=root(h2); if(h*h!=h2) continue;
            for(int s:{-1,1}) {
                if(s==1 && h==0) continue;
                I num=e+s*h; if(num%(2*a)) continue;
                I y=num/(2*a);
                if(x<0 || x>w || (x==0 && y<0)) { reject=true; break; }
                ymin=std::min(ymin,y);ymax=std::max(ymax,y);xmax=std::max(xmax,x);
                if(ymax-ymin>w) { reject=true;break; }
                cp.emplace_back(x,y);
            }
        }
        if(reject || cp.size()<4) continue;
        ++complete;
        std::sort(cp.begin(),cp.end());
        assert(std::find(cp.begin(),cp.end(),Pt(0,0))!=cp.end());
        const I q=denominator(k), span=std::max(xmax,ymax-ymin);
        auto index=std::make_pair(family(q),I(cp.size()));
        ++counts[index];
        if(!best.count(index) || span<best[index].span ||
           (span==best[index].span && k<best[index].key)) best[index]={span,q,k,cp};
    }
    std::cout<<"{\n\"selection\":\""<<selection<<"\",\n\"minimum_point_count\":4,\n\"coordinate_span_limit\":"<<w<<",\n\"board_side_limit\":"<<w+1
      <<",\n\"noncollinear_pairs\":"<<pairs<<",\n\"selected_pairs\":"<<selected
      <<",\n\"selected_unique_circles\":"<<keys.size()<<",\n\"candidates_with_three_pairs\":"<<checked
      <<",\n\"x_scans\":"<<x_scans<<",\n\"complete_anchored_circles\":"<<complete<<",\n\"minima\":[\n";
    bool comma=false;
    for(const auto& entry:best) {
        if(comma) std::cout<<",\n"; comma=true;
        auto [fam,m]=entry.first; const auto&r=entry.second;
        std::cout<<"{\"family\":\""<<(fam==0?"power2":"odd")<<"\",\"m\":"<<m
          <<",\"span\":"<<r.span<<",\"board_side\":"<<r.span+1<<",\"q\":"<<r.q
          <<",\"complete_anchored_count\":"<<counts[entry.first]<<",\"circle_A_D_E\":["
          <<r.key[0]<<","<<r.key[1]<<","<<r.key[2]<<"],\"points\":[";
        for(size_t i=0;i<r.pts.size();++i) { if(i) std::cout<<","; std::cout<<"["<<r.pts[i].first<<","<<r.pts[i].second<<"]"; }
        std::cout<<"]}";
    }
    std::cout<<"\n]}\n";
}
