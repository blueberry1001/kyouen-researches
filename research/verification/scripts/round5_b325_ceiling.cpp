// n=6 (or any n<=8) grundy + Klocal ceiling stats for B325/B327/B329/B330
// Build: g++ -O2 -std=c++20 -o /tmp/ceil6 round5_b325_ceiling.cpp
#include "kc_core.h"
#include <cstdio>
#include <cstdint>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <map>
#include <set>
#include <chrono>
using namespace std;
using namespace kc;

static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

int main(int argc, char** argv) {
    int n = (argc > 1) ? atoi(argv[1]) : 6;
    Board b;
    build_square(b, n);
    fprintf(stderr, "n=%d V=%d\n", n, b.V);

    // Enumerate all safe states via BFS layers
    vector<u64> states;
    states.push_back(0);
    unordered_map<u64,int> idx;
    idx.reserve(8000000);
    idx[0] = 0;
    vector<int> by_k_start; // index into states for each k
    // We'll store popcount and sort later
    double t0 = now_s();
    for (size_t i = 0; i < states.size(); ++i) {
        u64 occ = states[i];
        u64 lm = legal_mask(b, occ);
        while (lm) {
            int v = __builtin_ctzll(lm);
            lm &= lm - 1;
            u64 ch = occ | (1ULL << v);
            if (idx.find(ch) == idx.end()) {
                idx[ch] = (int)states.size();
                states.push_back(ch);
            }
        }
        if ((i & 0xFFFFF) == 0) fprintf(stderr, "  enum %zu / visited, %zu states\n", i, states.size());
    }
    fprintf(stderr, "enumerated %zu states in %.1fs\n", states.size(), now_s() - t0);

    // sort by popcount descending index ranges
    vector<int> order(states.size());
    for (size_t i = 0; i < order.size(); ++i) order[i] = (int)i;
    sort(order.begin(), order.end(), [&](int a, int b) {
        return __builtin_popcountll(states[a]) > __builtin_popcountll(states[b]);
    });

    int maxk = __builtin_popcountll(states[order[0]]);
    vector<int> g(states.size(), -1);
    vector<int> Klocal(states.size(), -1);
    vector<int> nL(states.size(), 0);

    // process from high k to low k
    t0 = now_s();
    for (int id : order) {
        u64 occ = states[id];
        int k = __builtin_popcountll(occ);
        u64 lm = legal_mask(b, occ);
        nL[id] = __builtin_popcountll(lm);
        if (lm == 0) {
            g[id] = 0;
            Klocal[id] = k;
            continue;
        }
        // collect children g
        int mex_seen[64] = {0};
        int bestK = k;
        bool any = false;
        u64 m = lm;
        while (m) {
            int v = __builtin_ctzll(m);
            m &= m - 1;
            u64 ch = occ | (1ULL << v);
            int cid = idx[ch];
            int cg = g[cid];
            if (cg >= 0 && cg < 64) mex_seen[cg] = 1;
            if (Klocal[cid] > bestK) bestK = Klocal[cid];
            any = true;
        }
        (void)any;
        int mex = 0;
        while (mex < 64 && mex_seen[mex]) ++mex;
        g[id] = mex;
        Klocal[id] = bestK;
    }
    fprintf(stderr, "grundy+Klocal done %.1fs maxk=%d maxg=%d\n", now_s()-t0, maxk,
            *max_element(g.begin(), g.end()));

    // Ceiling stats
    map<int,int> min_slack_by_h;
    map<int,pair<int,int>> slack_ex; // h -> (slack, id)
    int n_ceiling = 0;
    int max_deficit = 0;
    int n_b327 = 0;
    vector<pair<int,int>> b327_ex;
    // B330 cells (h, mu)
    // mu: min achievable total from occ
    vector<int> mu(states.size(), -1);
    for (int id : order) {
        u64 occ = states[id];
        int k = __builtin_popcountll(occ);
        u64 lm = legal_mask(b, occ);
        if (lm == 0) { mu[id] = k; continue; }
        int best = n+2; // large
        u64 m = lm;
        while (m) {
            int v = __builtin_ctzll(m); m &= m-1;
            int cid = idx[occ | (1ULL << v)];
            if (mu[cid] < best) best = mu[cid];
        }
        mu[id] = best;
    }

    map<pair<int,int>, pair<int,int>> cell_minmax; // (h,mu) -> (min_g, max_g)
    map<pair<int,int>, pair<int,int>> cell_minmax_id;

    for (size_t id = 0; id < states.size(); ++id) {
        int k = __builtin_popcountll(states[id]);
        int hv = Klocal[id] - k;
        int gv = g[id];
        int L = nL[id];
        if (gv == hv) {
            n_ceiling++;
            int slack = L - hv;
            auto it = min_slack_by_h.find(hv);
            if (it == min_slack_by_h.end() || slack < it->second) {
                min_slack_by_h[hv] = slack;
                slack_ex[hv] = {slack, (int)id};
            }
        }
        // B327
        int deficit = hv - gv;
        if (deficit > 0) {
            u64 occ = states[id];
            u64 lm = legal_mask(b, occ);
            bool has_zero = false;
            u64 m = lm;
            while (m && !has_zero) {
                int v = __builtin_ctzll(m); m &= m-1;
                int cid = idx[occ | (1ULL << v)];
                int h2 = Klocal[cid] - __builtin_popcountll(states[cid]);
                if (h2 - g[cid] == 0) has_zero = true;
            }
            if (has_zero) {
                n_b327++;
                if (deficit > max_deficit) {
                    max_deficit = deficit;
                    b327_ex.clear();
                    b327_ex.push_back({deficit, (int)id});
                } else if (deficit == max_deficit && b327_ex.size() < 3) {
                    b327_ex.push_back({deficit, (int)id});
                }
            }
        }
        // B330
        auto key = make_pair(hv, mu[id]);
        auto it = cell_minmax.find(key);
        if (it == cell_minmax.end()) {
            cell_minmax[key] = {gv, gv};
            cell_minmax_id[key] = {(int)id, (int)id};
        } else {
            if (gv < it->second.first) { it->second.first = gv; cell_minmax_id[key].first = (int)id; }
            if (gv > it->second.second) { it->second.second = gv; cell_minmax_id[key].second = (int)id; }
        }
    }

    int max_spread = 0;
    pair<int,int> spread_cell = {0,0};
    pair<int,int> spread_ids = {0,0};
    int n_ge3 = 0;
    for (auto& kv : cell_minmax) {
        int spread = kv.second.second - kv.second.first;
        if (spread >= 3) n_ge3++;
        if (spread > max_spread) {
            max_spread = spread;
            spread_cell = kv.first;
            spread_ids = cell_minmax_id[kv.first];
        }
    }

    // B329: holes at each k and required pairs
    // layer hist
    map<int, map<int,int>> hist;
    for (size_t id = 0; id < states.size(); ++id) {
        int k = __builtin_popcountll(states[id]);
        hist[k][g[id]]++;
    }

    printf("{\n");
    printf("  \"n\": %d,\n", n);
    printf("  \"n_states\": %zu,\n", states.size());
    printf("  \"max_g\": %d,\n", *max_element(g.begin(), g.end()));
    printf("  \"K_global\": %d,\n", Klocal[0]);
    printf("  \"n_ceiling_g_eq_h\": %d,\n", n_ceiling);
    printf("  \"B325_min_slack_by_h\": {");
    bool first = true;
    for (auto& kv : min_slack_by_h) {
        if (!first) printf(", ");
        printf("\"%d\": %d", kv.first, kv.second);
        first = false;
    }
    printf("},\n");
    printf("  \"B325_examples\": {");
    first = true;
    for (auto& kv : slack_ex) {
        if (!first) printf(", ");
        int id = kv.second.second;
        printf("\"%d\": {\"slack\": %d, \"occ\": %llu, \"k\": %d, \"g\": %d, \"h\": %d, \"L\": %d}",
               kv.first, kv.second.first, (unsigned long long)states[id],
               __builtin_popcountll(states[id]), g[id], kv.first, nL[id]);
        first = false;
    }
    printf("},\n");
    printf("  \"B327_max_deficit\": %d,\n", max_deficit);
    printf("  \"B327_count\": %d,\n", n_b327);
    printf("  \"B327_examples\": [");
    first = true;
    for (auto& kv : b327_ex) {
        if (!first) printf(", ");
        int id = kv.second;
        printf("{\"deficit\": %d, \"occ\": %llu, \"k\": %d, \"g\": %d, \"h\": %d}",
               kv.first, (unsigned long long)states[id],
               __builtin_popcountll(states[id]), g[id],
               Klocal[id] - __builtin_popcountll(states[id]));
        first = false;
    }
    printf("],\n");
    printf("  \"B330_max_spread\": %d,\n", max_spread);
    printf("  \"B330_cell\": [%d, %d],\n", spread_cell.first, spread_cell.second);
    printf("  \"B330_n_cells_spread_ge3\": %d,\n", n_ge3);
    printf("  \"B330_examples\": {");
    {
        int ida = spread_ids.first, idb = spread_ids.second;
        printf("\"low\": {\"g\": %d, \"occ\": %llu, \"k\": %d}, \"high\": {\"g\": %d, \"occ\": %llu, \"k\": %d}",
               g[ida], (unsigned long long)states[ida], __builtin_popcountll(states[ida]),
               g[idb], (unsigned long long)states[idb], __builtin_popcountll(states[idb]));
    }
    printf("},\n");
    // layer hist + holes
    printf("  \"layer_hist\": {");
    first = true;
    for (auto& kv : hist) {
        if (!first) printf(", ");
        printf("\"%d\": {", kv.first);
        bool f2 = true;
        for (auto& gv : kv.second) {
            if (!f2) printf(", ");
            printf("\"%d\": %d", gv.first, gv.second);
            f2 = false;
        }
        printf("}");
        first = false;
    }
    printf("},\n");
    printf("  \"holes_by_k\": {");
    first = true;
    for (auto& kv : hist) {
        set<int> present;
        for (auto& gv : kv.second) present.insert(gv.first);
        int mx = present.empty() ? -1 : *present.rbegin();
        vector<int> missing;
        for (int a = 0; a <= mx; ++a) if (!present.count(a)) missing.push_back(a);
        if (missing.empty()) continue;
        if (!first) printf(", ");
        printf("\"%d\": [", kv.first);
        for (size_t i = 0; i < missing.size(); ++i) {
            if (i) printf(", ");
            printf("%d", missing[i]);
        }
        printf("]");
        first = false;
    }
    printf("},\n");
    // required pairs at layers with holes
    printf("  \"required_pairs\": {");
    first = true;
    for (auto& kv : hist) {
        set<int> present;
        for (auto& gv : kv.second) present.insert(gv.first);
        int mx = present.empty() ? -1 : *present.rbegin();
        vector<int> missing;
        for (int a = 0; a <= mx; ++a) if (!present.count(a)) missing.push_back(a);
        if (missing.empty()) continue;
        // for each missing a, count antecedent / violations at this layer
        if (!first) printf(", ");
        printf("\"%d\": {", kv.first);
        bool f2 = true;
        for (int a : missing) {
            int ante = 0, viol = 0;
            // scan states at this k
            for (size_t id = 0; id < states.size(); ++id) {
                if (__builtin_popcountll(states[id]) != kv.first) continue;
                u64 occ = states[id];
                u64 lm = legal_mask(b, occ);
                bool has[64] = {false};
                u64 m = lm;
                while (m) {
                    int v = __builtin_ctzll(m); m &= m-1;
                    int cg = g[idx[occ | (1ULL << v)]];
                    if (cg >= 0 && cg < 64) has[cg] = true;
                }
                bool ok = true;
                for (int x = 0; x < a; ++x) if (!has[x]) { ok = false; break; }
                if (!ok) continue;
                ante++;
                if (!has[a]) viol++;
            }
            if (!f2) printf(", ");
            printf("\"%d\": {\"antecedent_true\": %d, \"violations\": %d}", a, ante, viol);
            f2 = false;
        }
        printf("}");
        first = false;
    }
    printf("}\n");
    printf("}\n");
    return 0;
}
