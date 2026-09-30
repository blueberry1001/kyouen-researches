// Exact P/N scan of fixed four-point prohibition families on boards of <=49 points.
// A node-budget exhaustion is UNKNOWN, never a losing or winning result.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
using U = uint64_t;
struct Solver {
    int v;
    uint64_t states = 0, limit;
    std::vector<std::vector<U>> triples;
    std::vector<int8_t> memo;
    std::unordered_map<U, int8_t> sparse;
    void put(U s, int8_t value) {
        if (memo.empty()) sparse[s] = value;
        else memo[s] = value;
    }
    bool win(U s) {
        if (memo.empty()) {
            auto found = sparse.find(s);
            if (found != sparse.end()) return found->second;
        } else if (memo[s] >= 0) return memo[s];
        if (++states > limit) throw std::runtime_error("node budget");
        for (int p = 0; p < v; ++p) {
            U bit = U(1) << p;
            if (s & bit) continue;
            bool legal = true;
            for (U t : triples[p]) if ((s & t) == t) { legal = false; break; }
            if (legal && !win(s | bit)) { put(s, 1); return true; }
        }
        put(s, 0);
        return false;
    }
};
int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::ifstream in(argv[1]);
    int nq, cases;
    Solver s;
    if (!(in >> s.v >> nq >> cases) || s.v < 1 || s.v > 49) return 3;
    s.limit = std::stoull(argv[3]);
    std::vector<U> quads(nq);
    for (U &q : quads) if (!(in >> q)) return 4;
    if (s.v <= 25) s.memo.resize(U(1) << s.v);
    std::ofstream out(argv[2]);
    out << "{\"node_budget\":" << s.limit << ",\"cases\":[";
    for (int ci = 0; ci < cases; ++ci) {
        std::string name;
        int count;
        if (!(in >> name >> count)) return 5;
        s.triples.assign(s.v, {});
        std::vector<int> kept(count);
        for (int &qi : kept) {
            if (!(in >> qi) || qi < 0 || qi >= nq) return 6;
            U q = quads[qi];
            for (int p = 0; p < s.v; ++p) if (q & (U(1) << p))
                s.triples[p].push_back(q ^ (U(1) << p));
        }
        std::fill(s.memo.begin(), s.memo.end(), int8_t(-1));
        s.sparse.clear();
        s.states = 0;
        int outcome = -1;
        try { outcome = s.win(0); } catch (const std::runtime_error&) {}
        if (ci) out << ',';
        out << "{\"name\":\"" << name << "\",\"outcome\":" << outcome
            << ",\"states\":" << s.states << ",\"kept_indices\":[";
        for (int i = 0; i < count; ++i) { if (i) out << ','; out << kept[i]; }
        out << "]}" << std::flush;
        std::cout << name << " outcome=" << outcome << " states=" << s.states << std::endl;
    }
    out << "]}\n";
}
