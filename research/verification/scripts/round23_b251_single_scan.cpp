// B251 scan: remove exactly one four-set from the complete standard family.
// Each D4 representative is solved independently; budget exhaustion is UNKNOWN.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
using U = uint64_t;
struct Solver {
    int v;
    uint64_t states = 0, limit;
    std::vector<U> quads;
    std::vector<std::vector<U>> triples;
    std::vector<int8_t> dense;
    std::unordered_map<U, int8_t> sparse;
    void put(U s, int8_t value) {
        if (dense.empty()) sparse[s] = value;
        else dense[s] = value;
    }
    bool win(U s) {
        if (dense.empty()) {
            auto hit = sparse.find(s);
            if (hit != sparse.end()) return hit->second;
        } else if (dense[s] >= 0) return dense[s];
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
    int run(int removed) {
        triples.assign(v, {});
        for (size_t qi = 0; qi < quads.size(); ++qi) if (int(qi) != removed) {
            U q = quads[qi];
            for (int p = 0; p < v; ++p) if (q & (U(1) << p))
                triples[p].push_back(q ^ (U(1) << p));
        }
        std::fill(dense.begin(), dense.end(), int8_t(-1));
        sparse.clear();
        states = 0;
        try { return win(0); } catch (const std::runtime_error&) { return -1; }
    }
};
int main(int argc, char** argv) {
    if (argc != 4) return 2;
    Solver s;
    int nq, count;
    std::ifstream in(argv[1]);
    if (!(in >> s.v >> nq >> count) || s.v < 4 || s.v > 49) return 3;
    s.limit = std::stoull(argv[3]);
    s.quads.resize(nq);
    for (U &q : s.quads) if (!(in >> q)) return 4;
    std::vector<int> representatives(count);
    for (int &qi : representatives) if (!(in >> qi) || qi < 0 || qi >= nq) return 5;
    if (s.v <= 25) s.dense.resize(U(1) << s.v, -1);
    int standard = s.run(-1);
    std::cout << "standard=" << standard << " states=" << s.states << std::endl;
    std::ofstream out(argv[2]);
    out << "{\"v\":" << s.v << ",\"node_budget\":" << s.limit
        << ",\"standard_outcome\":" << standard << ",\"standard_states\":" << s.states << ",\"cases\":[";
    int flips = 0, unknowns = 0;
    for (int i = 0; i < count; ++i) {
        int outcome = s.run(representatives[i]);
        unknowns += outcome < 0;
        bool flip = standard >= 0 && outcome >= 0 && outcome != standard;
        flips += flip;
        if (i) out << ',';
        out << "{\"removed_index\":" << representatives[i] << ",\"outcome\":" << outcome
            << ",\"states\":" << s.states << "}" << std::flush;
        if ((i+1)%25 == 0 || flip)
            std::cout << "tested=" << i+1 << " flips=" << flips << " unknown=" << unknowns << std::endl;
    }
    out << "]}\n";
    std::cout << "done tested=" << count << " flips=" << flips << " unknown=" << unknowns << std::endl;
}
