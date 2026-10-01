#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <set>
#include <utility>
#include <vector>

struct FiveSet {
    std::array<int,5> x{};
    std::vector<std::pair<int,int>> pairs;
    std::vector<std::pair<int,int>> sum_counts;
};

static bool target_edge(int sum, long long prod, int m, std::pair<int,int>& e) {
    long long disc = 1LL * sum * sum - 4 * prod;
    if (disc < 0) return false;
    long long r = (long long)std::sqrt((long double)disc);
    while ((r+1)*(r+1) <= disc) ++r;
    while (r*r > disc) --r;
    if (r*r != disc || ((sum-r)&1)) return false;
    long long a=(sum-r)/2, b=(sum+r)/2;
    if (0 <= a && a < b && b < m) { e={(int)a,(int)b}; return true; }
    return false;
}

static int dot_counts(const FiveSet& A, const FiveSet& B) {
    int i=0,j=0,dot=0;
    while (i<(int)A.sum_counts.size() && j<(int)B.sum_counts.size()) {
        if (A.sum_counts[i].first < B.sum_counts[j].first) ++i;
        else if (A.sum_counts[i].first > B.sum_counts[j].first) ++j;
        else { dot += A.sum_counts[i].second * B.sum_counts[j].second; ++i; ++j; }
    }
    return dot;
}

static std::pair<int,int> actual_edge_counts(const FiveSet& A, const FiveSet& B, int m) {
    std::set<std::pair<int,int>> outer, middle;
    int i=0,j=0;
    while (i<10 && j<10) {
        if (A.pairs[i].first < B.pairs[j].first) { ++i; continue; }
        if (A.pairs[i].first > B.pairs[j].first) { ++j; continue; }
        int s=A.pairs[i].first, i2=i, j2=j;
        while (i2<10 && A.pairs[i2].first==s) ++i2;
        while (j2<10 && B.pairs[j2].first==s) ++j2;
        for (int u=i; u<i2; ++u) for (int v=j; v<j2; ++v) {
            long long pA=A.pairs[u].second, pB=B.pairs[v].second;
            std::pair<int,int> e;
            // Target outer row y=0, other rows y=1,2.
            // p0 - 2 p1 + p2 = 2, hence p0 = 2 + 2 p1 - p2.
            if (target_edge(s, 2 + 2*pA - pB, m, e)) outer.insert(e);

            // Target middle row y=1, other rows y=0,2.
            // p0 - 2 p1 + p2 = 2, hence p1=(p0+p2-2)/2.
            long long num=pA+pB-2;
            if ((num&1)==0 && target_edge(s, num/2, m, e)) middle.insert(e);
        }
        i=i2; j=j2;
    }
    return {(int)outer.size(), (int)middle.size()};
}

static std::vector<FiveSet> five_sets(int m) {
    std::vector<FiveSet> out;
    for (int a=0;a<m;++a) for (int b=a+1;b<m;++b) for (int c=b+1;c<m;++c)
    for (int d=c+1;d<m;++d) for (int e=d+1;e<m;++e) {
        FiveSet s; s.x={a,b,c,d,e};
        int xs[5]={a,b,c,d,e};
        for (int i=0;i<5;++i) for (int j=i+1;j<5;++j)
            s.pairs.push_back({xs[i]+xs[j], xs[i]*xs[j]});
        std::sort(s.pairs.begin(), s.pairs.end());
        for (int i=0;i<10;) {
            int j=i+1;
            while (j<10 && s.pairs[j].first==s.pairs[i].first) ++j;
            s.sum_counts.push_back({s.pairs[i].first, j-i});
            i=j;
        }
        out.push_back(std::move(s));
    }
    return out;
}

int main() {
    std::cout << "{\n  \"method\": \"exhaustive ordered pairs of 5-subsets; exact integer root tests\",\n  \"cases\": [\n";
    bool first_case=true;

    for (int m=9;m<=20;++m) {
        auto sets=five_sets(m);
        const int need=m-4;
        long long candidates=0;
        int max_dot=0, max_outer=0, max_middle=0;

        for (const auto& A: sets) for (const auto& B: sets) {
            int dot=dot_counts(A,B);
            max_dot=std::max(max_dot,dot);

            // Each target edge needs a pair from A and a pair from B with
            // the same x-coordinate sum, so actual edge count <= dot.
            if (dot < need) continue;

            ++candidates;
            auto [eo,em]=actual_edge_counts(A,B,m);
            max_outer=std::max(max_outer,eo);
            max_middle=std::max(max_middle,em);

            if (eo >= need || em >= need) {
                std::cerr << "counterexample to edge bound at m="<<m
                          <<" need="<<need<<" outer="<<eo<<" middle="<<em<<"\n";
                return 2;
            }
        }

        if (!first_case) std::cout << ",\n";
        first_case=false;
        std::cout << "    {\"m\": "<<m
                  <<", \"five_subsets\": "<<sets.size()
                  <<", \"ordered_pairs\": "<<(1LL*sets.size()*sets.size())
                  <<", \"required_edges\": "<<need
                  <<", \"max_pair_sum_dot\": "<<max_dot
                  <<", \"candidate_pairs_dot_ge_required\": "<<candidates
                  <<", \"max_outer_target_edges_among_candidates\": "<<max_outer
                  <<", \"max_middle_target_edges_among_candidates\": "<<max_middle
                  <<"}";
    }

    std::cout << "\n  ],\n  \"conclusion\": \"no deficient maximal safe set exists for m=9..20\"\n}\n";
}
