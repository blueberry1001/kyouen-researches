// Independent B251 recheck: completion masks indexed by sorted triples,
// incremental legal bitsets, reverse move order. No scan solver is included.
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
    U full;
    std::vector<U> quads, completions, base;
    std::unordered_map<U, int8_t> memo;
    size_t key(int a, int b, int c) const {
        if (a > b) std::swap(a,b);
        if (b > c) std::swap(b,c);
        if (a > b) std::swap(a,b);
        return (a*v+b)*v+c;
    }
    U after(U s, U legal, int p) const {
        legal &= ~(U(1) << p);
        while (s) {
            int a = __builtin_ctzll(s);
            s &= s-1;
            U tail = s;
            while (tail) {
                int b = __builtin_ctzll(tail);
                tail &= tail-1;
                legal &= ~completions[key(a,b,p)];
            }
        }
        return legal;
    }
    bool win(U s, U legal) {
        auto hit = memo.find(s);
        if (hit != memo.end()) return hit->second;
        if (++states > limit) throw std::runtime_error("node budget");
        U candidates = legal;
        while (candidates) {
            int p = 63-__builtin_clzll(candidates);
            U bit = U(1) << p;
            candidates ^= bit;
            if (!win(s | bit, after(s, legal, p))) { memo[s] = 1; return true; }
        }
        memo[s] = 0;
        return false;
    }
    void prepare() {
        base.assign(v*v*v, 0);
        for (U q : quads) {
            std::vector<int> ids;
            for (U tail = q; tail; tail &= tail-1) ids.push_back(__builtin_ctzll(tail));
            if (ids.size() != 4) throw std::runtime_error("invalid quad");
            for (int i = 0; i < 4; ++i) {
                std::vector<int> triple;
                for (int j = 0; j < 4; ++j) if (j != i) triple.push_back(ids[j]);
                base[key(triple[0], triple[1], triple[2])] |= U(1) << ids[i];
            }
        }
    }
    int run(int removed) {
        completions = base;
        if (removed >= 0) {
            std::vector<int> ids;
            for (U tail = quads[removed]; tail; tail &= tail-1) ids.push_back(__builtin_ctzll(tail));
            for (int i = 0; i < 4; ++i) {
                std::vector<int> triple;
                for (int j = 0; j < 4; ++j) if (j != i) triple.push_back(ids[j]);
                completions[key(triple[0], triple[1], triple[2])] &= ~(U(1) << ids[i]);
            }
        }
        memo.clear(); states = 0;
        try { return win(0, full); } catch (const std::runtime_error&) { return -1; }
    }
};
int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::ifstream in(argv[1]);
    Solver s;
    int nq, count;
    if (!(in >> s.v >> nq >> count) || s.v < 4 || s.v > 49) return 3;
    s.full = (U(1) << s.v)-1; s.limit = std::stoull(argv[3]);
    s.quads.resize(nq);
    for (U &q : s.quads) if (!(in >> q)) return 4;
    std::vector<int> reps(count);
    for (int &qi : reps) if (!(in >> qi) || qi < 0 || qi >= nq) return 5;
    s.prepare();
    int standard = s.run(-1), unknowns = 0;
    std::cout << "standard=" << standard << " states=" << s.states << std::endl;
    std::ofstream out(argv[2]);
    out << "{\"v\":" << s.v << ",\"node_budget\":" << s.limit << ",\"standard_outcome\":" << standard
        << ",\"standard_states\":" << s.states << ",\"cases\":[";
    for (int i = 0; i < count; ++i) {
        int outcome = s.run(reps[i]);
        unknowns += outcome < 0;
        if (i) out << ',';
        out << "{\"removed_index\":" << reps[i] << ",\"outcome\":" << outcome
            << ",\"states\":" << s.states << "}" << std::flush;
        if ((i+1)%25 == 0) std::cout << "verified=" << i+1 << " unknown=" << unknowns << std::endl;
    }
    out << "]}\n";
    std::cout << "done verified=" << count << " unknown=" << unknowns << std::endl;
}
