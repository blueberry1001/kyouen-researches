// Exhaustive finite upper bounds for six-point circles on three of four rows.
// Reproduce:
//   g++ -std=c++17 -O3 q46_pair_upper_bound.cpp -o /tmp/q46_pairs
//   /tmp/q46_pairs > q46_pair_upper_bound.json
//
// B is translated so min(B)=0 and reduced by horizontal reflection.  C and
// the target row may have negative coordinates after that translation.
// A chord profile and a B pair determine one C pair.  Different B pairs
// may produce the same C pair, so parallel edges are retained as weights.
// Every actual C with <=5 points induces a weighted subgraph.  A connected
// nontrivial component has 2..5 vertices; we enumerate every such set.
// If there are two nontrivial components their sizes are 2+2 or 2+3;
// 2*L2 and L2+L3 are safe upper bounds even if their maxima overlap.
// The geometric filters are NECESSARY conditions only; no safety, global
// C-span, or target-occupied-set condition is imposed.  Thus this is an
// upper-bound proof, not a claim that every enumerated graph is realizable.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <utility>
#include <vector>
using namespace std;

struct Profile { int target, b, c; };
struct Edge { int u, v, weight; };

struct Result {
    int target_row, b_row, c_row;
    array<vector<Profile>, 68> by_gap;
    int profile_count = 0;
    long long supports = 0;
    long long enumerated_graphs = 0;
    long long connected_subsets = 0;
    int upper_bound = 0;
};

int graph_bound(const vector<pair<int, int>>& raw_edges,
                long long& connected_subsets) {
    vector<pair<int, int>> sorted_edges = raw_edges;
    sort(sorted_edges.begin(), sorted_edges.end());
    vector<int> coordinates;
    for (auto [u, v] : sorted_edges) {
        coordinates.push_back(u);
        coordinates.push_back(v);
    }
    sort(coordinates.begin(), coordinates.end());
    coordinates.erase(unique(coordinates.begin(), coordinates.end()),
                      coordinates.end());
    assert(coordinates.size() <= 63);

    vector<Edge> edges;
    array<uint64_t, 64> adjacency{};
    for (auto [a, b] : sorted_edges) {
        int u = lower_bound(coordinates.begin(), coordinates.end(), a)
                - coordinates.begin();
        int v = lower_bound(coordinates.begin(), coordinates.end(), b)
                - coordinates.begin();
        if (!edges.empty() && edges.back().u == u && edges.back().v == v)
            ++edges.back().weight;
        else
            edges.push_back({u, v, 1});
        adjacency[u] |= uint64_t{1} << v;
        adjacency[v] |= uint64_t{1} << u;
    }

    array<int, 6> maximum{};
    vector<uint64_t> frontier;
    for (int i = 0; i < static_cast<int>(coordinates.size()); ++i)
        frontier.push_back(uint64_t{1} << i);

    for (int k = 2; k <= 5; ++k) {
        vector<uint64_t> next;
        for (uint64_t vertices : frontier) {
            uint64_t neighbors = 0;
            for (uint64_t remaining = vertices; remaining;
                 remaining &= remaining - 1)
                neighbors |= adjacency[__builtin_ctzll(remaining)];
            neighbors &= ~vertices;
            while (neighbors) {
                int i = __builtin_ctzll(neighbors);
                neighbors &= neighbors - 1;
                next.push_back(vertices | (uint64_t{1} << i));
            }
        }
        sort(next.begin(), next.end());
        next.erase(unique(next.begin(), next.end()), next.end());
        connected_subsets += next.size();
        for (uint64_t vertices : next) {
            int total = 0;
            for (auto edge : edges)
                if ((vertices >> edge.u & 1) && (vertices >> edge.v & 1))
                    total += edge.weight;
            maximum[k] = max(maximum[k], total);
        }
        frontier.swap(next);
    }
    // Isolated vertices make no contribution.  Two nontrivial components
    // on <=5 vertices have sizes 2+2 or 2+3.  Independence of the maxima is
    // deliberately not required: dropping it only enlarges the upper bound.
    return max({maximum[2], maximum[3], maximum[4], maximum[5],
                2 * maximum[2], maximum[2] + maximum[3]});
}

Result solve(int span, int t, int v, int w) {
    Result result;
    result.target_row = t;
    result.b_row = v;
    result.c_row = w;
    for (int db = 1; db <= span; ++db) {
        for (int dc = 1; dc <= span; ++dc) {
            if ((db - dc) % 2) continue;
            int numerator = (w-t)*db*db + (t-v)*dc*dc
                            - 4*(t-v)*(t-w)*(w-v);
            if (numerator % (w-v)) continue;
            int square = numerator / (w-v);
            if (square <= 0) continue;
            int dt = 0;
            while ((dt + 1) * (dt + 1) <= square) ++dt;
            if (dt * dt != square || dt > span || (dt - db) % 2)
                continue;
            result.by_gap[db].push_back({dt, db, dc});
            ++result.profile_count;
        }
    }

    for (int b4 = 4; b4 <= span; ++b4) {
        for (int b1 = 1; b1 < b4; ++b1) {
            for (int b2 = b1 + 1; b2 < b4; ++b2) {
                for (int b3 = b2 + 1; b3 < b4; ++b3) {
                    array<int, 5> B{0, b1, b2, b3, b4};
                    array<int, 5> reflected{0, b4-b3, b4-b2, b4-b1, b4};
                    if (B > reflected) continue;
                    ++result.supports;
                    vector<pair<int, int>> raw_edges;
                    for (int i = 0; i < 5; ++i) {
                        for (int j = i + 1; j < 5; ++j) {
                            int sum = B[i] + B[j];
                            for (auto p : result.by_gap[B[j] - B[i]]) {
                                // Parity makes these exact divisions, including
                                // negative numerators after translating B.
                                int a0 = (sum - p.target) / 2;
                                int a1 = (sum + p.target) / 2;
                                int c0 = (sum - p.c) / 2;
                                int c1 = (sum + p.c) / 2;
                                if (max({b4, a1, c1}) - min({0, a0, c0}) > span)
                                    continue;
                                raw_edges.push_back({c0, c1});
                            }
                        }
                    }
                    // The full edge weight bounds every induced subgraph.
                    if (static_cast<int>(raw_edges.size()) <= result.upper_bound)
                        continue;
                    ++result.enumerated_graphs;
                    result.upper_bound = max(result.upper_bound,
                        graph_bound(raw_edges, result.connected_subsets));
                }
            }
        }
    }
    return result;
}

void print_result(const Result& result, int span) {
    cout << "{\"target_row\":" << result.target_row
         << ",\"exterior_rows\":[" << result.b_row << ',' << result.c_row << ']'
         << ",\"profile_count\":" << result.profile_count
         << ",\"normalized_five_point_sets\":" << result.supports
         << ",\"graphs_requiring_subset_enumeration\":" << result.enumerated_graphs
         << ",\"connected_subsets_checked\":" << result.connected_subsets
         << ",\"circle_count_upper_bound\":" << result.upper_bound
         << ",\"chord_profiles\":[";
    bool first = true;
    for (int gap = 1; gap <= span; ++gap) {
        for (auto p : result.by_gap[gap]) {
            if (!first) cout << ',';
            first = false;
            cout << '[' << p.target << ',' << p.b << ',' << p.c << ']';
        }
    }
    cout << "]}";
}

int main(int argc, char** argv) {
    int span = argc > 1 ? atoi(argv[1]) : 67;
    int selected_shape = argc > 2 ? atoi(argv[2]) : -1;
    if (span < 4 || span > 67 || selected_shape < -1 || selected_shape > 4) {
        cerr << "Use span 4..67 and optional shape 0..4\n";
        return 2;
    }
    const int shapes[5][3] = {{0,1,2}, {0,1,3}, {0,2,3}, {1,0,2}, {1,0,3}};
    cout << "{\"maximum_horizontal_span\":" << span
         << ",\"method\":\"exhaustive normalized five-point supports and connected graph subsets\""
         << ",\"shapes\":[";
    bool first = true;
    for (int i = 0; i < 5; ++i) {
        if (selected_shape >= 0 && selected_shape != i) continue;
        if (!first) cout << ',';
        first = false;
        print_result(solve(span, shapes[i][0], shapes[i][1], shapes[i][2]), span);
    }
    cout << "]}\n";
    return 0;
}
