#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <utility>
#include <vector>

using Point = std::pair<int,int>;

struct FourSet {
    std::array<int,4> x{};
    std::array<std::pair<int,int>,6> pairs{};
};

static std::vector<FourSet> four_sets(int m) {
    std::vector<FourSet> out;
    for (int a=0;a<m;++a) for (int b=a+1;b<m;++b)
    for (int c=b+1;c<m;++c) for (int d=c+1;d<m;++d) {
        FourSet s; s.x={a,b,c,d};
        int z[4]={a,b,c,d}, t=0;
        for (int i=0;i<4;++i) for (int j=i+1;j<4;++j)
            s.pairs[t++]={z[i]+z[j], z[i]*z[j]};
        std::sort(s.pairs.begin(), s.pairs.end());
        out.push_back(s);
    }
    return out;
}

static void add_integer_root_pair(int sum, long long prod, int m, std::uint64_t& mask) {
    long long disc=1LL*sum*sum-4*prod;
    if (disc<0) return;
    long long r=(long long)std::sqrt((long double)disc);
    while ((r+1)*(r+1)<=disc) ++r;
    while (r*r>disc) --r;
    if (r*r!=disc || ((sum-r)&1)) return;
    long long u=(sum-r)/2, v=(sum+r)/2;
    if (0<=u && u<v && v<m) mask |= (1ULL<<u)|(1ULL<<v);
}

struct CoverData {
    std::uint64_t no_target_stone=0;
    std::vector<std::uint64_t> with_a;
};

static CoverData outer_cover(const FourSet& B, const FourSet& C, int m) {
    CoverData out{0,std::vector<std::uint64_t>(m,0)};
    for (auto [s,p1]:B.pairs) for (auto [t,p2]:C.pairs) if (s==t)
        add_integer_root_pair(s, 2+2LL*p1-p2, m, out.no_target_stone);

    for (int a=0;a<m;++a) {
        std::uint64_t h=0;
        for (auto [s,p1]:B.pairs) {
            int x=s-a;
            if (x<0 || x>=m || x==a) continue;
            long long p0=1LL*a*x, p2=2-p0+2LL*p1;
            for (int c:C.x) if (1LL*c*c-1LL*s*c+p2==0) {
                h |= 1ULL<<x; break;
            }
        }
        for (auto [s,p2]:C.pairs) {
            int x=s-a;
            if (x<0 || x>=m || x==a) continue;
            long long p0=1LL*a*x, num=p0+p2-2;
            if (num&1) continue;
            long long p1=num/2;
            for (int b:B.x) if (1LL*b*b-1LL*s*b+p1==0) {
                h |= 1ULL<<x; break;
            }
        }
        out.with_a[a]=h;
    }
    return out;
}

static CoverData middle_cover(const FourSet& B, const FourSet& C, int m) {
    CoverData out{0,std::vector<std::uint64_t>(m,0)};
    for (auto [s,p0]:B.pairs) for (auto [t,p2]:C.pairs) if (s==t) {
        long long num=p0+p2-2;
        if (!(num&1)) add_integer_root_pair(s, num/2, m, out.no_target_stone);
    }
    for (int a=0;a<m;++a) {
        std::uint64_t h=0;
        for (auto [s,p0]:B.pairs) {
            int x=s-a;
            if (x<0 || x>=m || x==a) continue;
            long long p1=1LL*a*x, p2=2-p0+2LL*p1;
            for (int c:C.x) if (1LL*c*c-1LL*s*c+p2==0) {
                h |= 1ULL<<x; break;
            }
        }
        for (auto [s,p2]:C.pairs) {
            int x=s-a;
            if (x<0 || x>=m || x==a) continue;
            long long p1=1LL*a*x, p0=2+2LL*p1-p2;
            for (int b:B.x) if (1LL*b*b-1LL*s*b+p0==0) {
                h |= 1ULL<<x; break;
            }
        }
        out.with_a[a]=h;
    }
    return out;
}

static bool has_three_stone_cover(const CoverData& d, int m) {
    const std::uint64_t U=(1ULL<<m)-1;
    std::vector<std::uint64_t> c(m);
    for (int a=0;a<m;++a) c[a]=d.with_a[a] | (1ULL<<a);
    const std::uint64_t need=U & ~d.no_target_stone;
    if (!need) return true;

    // Safe optimistic prune: even if the best three closed-neighborhood masks
    // were disjoint, their individual gains must cover every still-needed bit.
    int top[3]={0,0,0};
    for (int a=0;a<m;++a) {
        int g=__builtin_popcountll(c[a] & need);
        if (g>top[0]) { top[2]=top[1]; top[1]=top[0]; top[0]=g; }
        else if (g>top[1]) { top[2]=top[1]; top[1]=g; }
        else if (g>top[2]) top[2]=g;
    }
    if (top[0]+top[1]+top[2] < __builtin_popcountll(need)) return false;

    for (int a=0;a<m;++a) for (int b=a+1;b<m;++b) {
        std::uint64_t rem=need & ~(c[a]|c[b]);
        for (int z=b+1;z<m;++z)
            if ((rem & ~c[z])==0) return true;
    }
    return false;
}

static long long det4(const std::array<Point,4>& p) {
    long long a[4][4];
    for (int i=0;i<4;++i) {
        long long x=p[i].first, y=p[i].second;
        a[i][0]=x*x+y*y; a[i][1]=x; a[i][2]=y; a[i][3]=1;
    }
    int perm[4]={0,1,2,3}; long long det=0;
    do {
        int inv=0;
        for(int i=0;i<4;++i) for(int j=i+1;j<4;++j) inv += perm[i]>perm[j];
        long long prod=1;
        for(int i=0;i<4;++i) prod*=a[i][perm[i]];
        det += (inv&1)?-prod:prod;
    } while (std::next_permutation(perm,perm+4));
    return det;
}

static bool forbidden5(const std::array<Point,5>& p) {
    for (int omit=0;omit<5;++omit) {
        std::array<Point,4> q{}; int t=0;
        for (int i=0;i<5;++i) if (i!=omit) q[t++]=p[i];
        if (det4(q)!=0) return false;
    }
    return true;
}

static bool safe(const std::vector<Point>& s) {
    const int n=(int)s.size();
    for(int a=0;a<n;++a) for(int b=a+1;b<n;++b) for(int c=b+1;c<n;++c)
    for(int d=c+1;d<n;++d) for(int e=d+1;e<n;++e) {
        std::array<Point,5> p={s[a],s[b],s[c],s[d],s[e]};
        if (forbidden5(p)) return false;
    }
    return true;
}

static bool verify_m11_witness() {
    const int m=11;
    const int A[3]={1,4,8}, B[4]={1,2,4,7}, C[4]={1,4,7,10};
    std::vector<Point> s;
    for(int x:A)s.push_back({x,0});
    for(int x:B)s.push_back({x,1});
    for(int x:C)s.push_back({x,2});
    if (!safe(s)) return false;

    for(int y=0;y<3;++y) for(int x=0;x<m;++x) {
        if (std::find(s.begin(),s.end(),Point{x,y})!=s.end()) continue;
        auto t=s; t.push_back({x,y});
        if (safe(t)) return false;
    }
    return true;
}

int main() {
    std::cout << "{\n";
    std::cout << "  \"q\": 5, \"w\": 3,\n";
    std::cout << "  \"m11_maximal_witness_verified\": " << (verify_m11_witness()?"true":"false") << ",\n";
    std::cout << "  \"m11_witness_rows\": [[1,4,8],[1,2,4,7],[1,4,7,10]],\n";
    std::cout << "  \"finite_exclusion\": [\n";
    for(int m=12;m<=21;++m) {
        auto sets=four_sets(m); bool outer=false,middle=false;
        for(const auto& B:sets) {
            for(const auto& C:sets) {
                if (!outer && has_three_stone_cover(outer_cover(B,C,m),m)) outer=true;
                if (!middle && has_three_stone_cover(middle_cover(B,C,m),m)) middle=true;
                if (outer && middle) break;
            }
            if (outer && middle) break;
        }
        std::cout << "    {\"m\": "<<m<<", \"four_sets\": "<<sets.size()
                  <<", \"outer_cover_exists\": "<<(outer?"true":"false")
                  <<", \"middle_cover_exists\": "<<(middle?"true":"false")<<"}"
                  << (m==21?"\n":",\n");
    }
    std::cout << "  ],\n";
    std::cout << "  \"analytic_tail\": {\"all_m_at_least\": 56, \"reason\": \"at most 55 unavailable points on a deficient row\"},\n";
    std::cout << "  \"current_stabilization_bracket\": [12,56]\n";
    std::cout << "}\n";
}
