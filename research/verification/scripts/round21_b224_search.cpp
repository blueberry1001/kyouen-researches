// Bounded local search over complete D4 orbits of geometric curves.
// Usage: binary input.txt initial_ids.txt output.json seconds seed
// The output is an existence witness, never a global minimum certificate.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <set>
#include <stdexcept>
#include <vector>

using U = uint32_t;
struct Solver {
    int v, ng;
    U target;
    std::vector<U> quads;
    std::vector<int> group;
    std::vector<bool> active;
    std::vector<std::vector<U>> triples;
    std::vector<int8_t> memo;
    uint64_t states = 0, limit = 0;
    bool win(U s) {
        auto &value = memo[s];
        if (value >= 0) return value;
        if (limit && ++states > limit) throw std::runtime_error("search node budget");
        for (int p = 0; p < v; ++p) {
            U bit = U(1) << p;
            if (s & bit) continue;
            bool legal = true;
            for (U t : triples[p]) if ((s & t) == t) { legal = false; break; }
            if (legal && !win(s | bit)) { value = 1; return true; }
        }
        value = 0;
        return false;
    }
    bool matches() {
        triples.assign(v, {});
        for (size_t i = 0; i < quads.size(); ++i) if (active[group[i]]) {
            U q = quads[i];
            for (int p = 0; p < v; ++p) if (q & (U(1) << p))
                triples[p].push_back(q ^ (U(1) << p));
        }
        std::fill(memo.begin(), memo.end(), int8_t(-1));
        states = 0;
        for (int p = 0; p < v; ++p)
            if ((!win(U(1) << p)) != bool(target & (U(1) << p))) return false;
        return true;
    }
};

int main(int argc, char** argv) {
    if (argc != 6) return 2;
    const double seconds = std::stod(argv[4]);
    const unsigned seed = std::stoul(argv[5]);
    auto start = std::chrono::steady_clock::now();
    auto elapsed = [&]() {
        return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    };
    Solver s;
    int nq;
    std::ifstream input(argv[1]);
    if (!(input >> s.v >> nq >> s.ng >> s.target) || s.v != 25) return 3;
    s.quads.resize(nq); s.group.resize(nq);
    for (int i = 0; i < nq; ++i) if (!(input >> s.quads[i] >> s.group[i])) return 4;
    std::map<int, std::vector<int>> orbit_map;
    for (int gi = 0; gi < s.ng; ++gi) {
        int representative;
        if (!(input >> representative)) return 5;
        orbit_map[representative].push_back(gi);
    }
    std::vector<std::vector<int>> blocks;
    for (const auto &entry : orbit_map) blocks.push_back(entry.second);
    std::set<int> initial;
    std::ifstream initial_file(argv[2]);
    int id;
    while (initial_file >> id) initial.insert(id);
    if (initial.empty()) return 6;
    std::vector<bool> current(blocks.size(), false);
    for (size_t bi = 0; bi < blocks.size(); ++bi) {
        for (int gi : blocks[bi]) if (initial.count(gi)) current[bi] = true;
        for (int gi : blocks[bi]) if (bool(initial.count(gi)) != current[bi]) return 7;
    }
    s.active.assign(s.ng, false);
    s.memo.resize(U(1) << s.v, -1);
    uint64_t trials = 0, skips = 0, accepted = 0;
    auto apply = [&](const std::vector<bool>& candidate) {
        for (size_t bi = 0; bi < blocks.size(); ++bi)
            for (int gi : blocks[bi]) s.active[gi] = candidate[bi];
    };
    auto matches = [&](const std::vector<bool>& candidate) {
        apply(candidate);
        ++trials;
        try { return s.matches(); }
        catch (const std::runtime_error&) { ++skips; return false; }
    };
    auto count = [&](const std::vector<bool>& candidate) {
        int size = 0;
        for (size_t bi = 0; bi < blocks.size(); ++bi) if (candidate[bi]) size += blocks[bi].size();
        return size;
    };
    auto best = current;
    int best_count = count(best);
    s.limit = 0;
    if (!matches(best)) return 8;
    s.limit = 1000000;
    std::mt19937 rng(seed);
    auto save = [&]() {
        apply(best);
        std::ofstream out(argv[3]);
        out << "{\"mode\":\"orbit-local\",\"seed\":" << seed << ",\"kept_group_ids\":[";
        bool first = true;
        for (int gi = 0; gi < s.ng; ++gi) if (s.active[gi]) {
            if (!first) out << ',';
            first = false; out << gi;
        }
        int kept_quads = 0;
        for (int gi : s.group) kept_quads += s.active[gi];
        out << "],\"winning_first_move_mask\":" << s.target
            << ",\"kept_quads\":" << kept_quads << ",\"trials\":" << trials
            << ",\"budget_skips\":" << skips << ",\"accepted\":" << accepted
            << ",\"seconds\":" << elapsed() << "}\n";
    };
    save();
    auto attempt = [&](const std::vector<bool>& candidate) {
        const int size = count(candidate);
        if (size > best_count+8 || !matches(candidate)) return false;
        ++accepted;
        current = candidate;
        if (size < best_count) {
            best = candidate;
            best_count = size;
            save();
            std::cout << "improved kept=" << size << " trials=" << trials << " seconds=" << elapsed() << std::endl;
        }
        return true;
    };
    // First test every pair of active orbit deletions, restarting after success.
    while (elapsed() < seconds) {
        std::vector<std::pair<int,int>> pairs;
        for (size_t a = 0; a < current.size(); ++a) if (current[a])
            for (size_t b = a+1; b < current.size(); ++b) if (current[b]) pairs.emplace_back(a,b);
        std::shuffle(pairs.begin(), pairs.end(), rng);
        bool improved = false;
        for (auto [a,b] : pairs) {
            if (elapsed() >= seconds) break;
            auto candidate = current;
            candidate[a] = candidate[b] = false;
            if (attempt(candidate)) { improved = true; break; }
        }
        if (!improved) break;
    }
    // Random deletions and exchanges escape nonmonotone local minima.
    while (elapsed() < seconds && trials < 10000) {
        if (trials % 100 == 0) current = best;
        std::vector<int> present, absent;
        for (size_t bi = 0; bi < current.size(); ++bi)
            (current[bi] ? present : absent).push_back(bi);
        std::shuffle(present.begin(), present.end(), rng);
        std::shuffle(absent.begin(), absent.end(), rng);
        auto candidate = current;
        const int remove = 1+rng()%4, add = rng()%3;
        for (int i = 0; i < remove && i < int(present.size()); ++i) candidate[present[i]] = false;
        for (int i = 0; i < add && i < int(absent.size()); ++i) candidate[absent[i]] = true;
        attempt(candidate);
        if (trials % 100 == 0)
            std::cout << "trials=" << trials << " best=" << best_count << " skips=" << skips << std::endl;
    }
    s.limit = 0;
    if (!matches(best)) return 9;
    save();
    std::cout << "done kept=" << best_count << " trials=" << trials << " seconds=" << elapsed() << std::endl;
}
