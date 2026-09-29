// n=6 grundy + B242 first-move rule check.
// Build: g++ -O2 -std=c++17 -o b242_n6 b242_n6.cpp
#include "kc_core.h"
#include <bits/stdc++.h>
using namespace kc;
using namespace std;

Board B;
unordered_map<u64, int> G;

int grundy(u64 occ) {
    auto it = G.find(occ);
    if (it != G.end()) return it->second;
    u64 lm = legal_mask(B, occ);
    if (lm == 0) { G[occ] = 0; return 0; }
    vector<int> seen;
    while (lm) {
        int p = __builtin_ctzll(lm);
        lm &= lm - 1;
        int g = grundy(occ | (u64(1) << p));
        seen.push_back(g);
    }
    sort(seen.begin(), seen.end());
    seen.erase(unique(seen.begin(), seen.end()), seen.end());
    int g = 0;
    while (g < (int)seen.size() && seen[g] == g) g++;
    G[occ] = g;
    return g;
}

// first response rule: among winning moves, pick min child |L|, tie-break min p
int pick_min_child_L(u64 occ) {
    u64 lm = legal_mask(B, occ);
    int best = -1, best_L = 1e9;
    while (lm) {
        int p = __builtin_ctzll(lm);
        lm &= lm - 1;
        u64 nxt = occ | (u64(1) << p);
        if (grundy(nxt) != 0) continue;
        u64 cl = legal_mask(B, nxt);
        int L = __builtin_popcountll(cl);
        if (L < best_L || (L == best_L && (best < 0 || p < best))) {
            best_L = L; best = p;
        }
    }
    return best;
}

int pick_lex_min(u64 occ) {
    u64 lm = legal_mask(B, occ);
    while (lm) {
        int p = __builtin_ctzll(lm);
        lm &= lm - 1;
        if (grundy(occ | (u64(1) << p)) == 0) return p;
    }
    return -1;
}

bool check_rule(int first, int (*rule)(u64), int max_nodes = 200000) {
    // BFS: first-player-to-move states reachable under rule
    vector<u64> stack;
    u64 after = (u64(1) << first);
    u64 opp = legal_mask(B, after);
    while (opp) {
        int q = __builtin_ctzll(opp);
        opp &= opp - 1;
        stack.push_back(after | (u64(1) << q));
    }
    unordered_set<u64> seen;
    int nodes = 0;
    while (!stack.empty()) {
        u64 S = stack.back(); stack.pop_back();
        if (seen.count(S)) continue;
        seen.insert(S);
        if (++nodes > max_nodes) return false;
        if (grundy(S) == 0) return false;
        int mv = rule(S);
        if (mv < 0) return false;
        u64 nxt = S | (u64(1) << mv);
        if (grundy(nxt) != 0) return false;
        u64 opp = legal_mask(B, nxt);
        while (opp) {
            int q = __builtin_ctzll(opp);
            opp &= opp - 1;
            stack.push_back(nxt | (u64(1) << q));
        }
    }
    return true;
}

int main() {
    build_square(B, 6);
    fprintf(stderr, "n=6 V=%d quads=%zu\n", B.V, B.quads.size());
    // compute grundy from empty (covers all reachable)
    int g0 = grundy(0);
    fprintf(stderr, "grundy computed states=%zu g0=%d\n", G.size(), g0);

    int n_win_first = 0;
    int rule_mlc_ok = 0, rule_lex_ok = 0;
    for (int p = 0; p < B.V; ++p) {
        u64 s = (u64(1) << p);
        int g = grundy(s);
        if (g == 0) n_win_first++;
        else continue;
        bool ok1 = check_rule(p, pick_min_child_L);
        bool ok2 = check_rule(p, pick_lex_min);
        if (ok1) rule_mlc_ok++;
        if (ok2) rule_lex_ok++;
        fprintf(stderr, "p=(%d,%d) win min_child_L=%d lex=%d\n",
                B.pt_x[p], B.pt_y[p], ok1, ok2);
    }
    printf("n_win_first=%d / %d\n", n_win_first, B.V);
    printf("rule_min_child_L_ok=%d\n", rule_mlc_ok);
    printf("rule_lex_min_ok=%d\n", rule_lex_ok);
    printf("states=%zu g0=%d\n", G.size(), g0);
    return 0;
}
