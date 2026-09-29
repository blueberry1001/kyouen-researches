// Greedily remove whole circle/line bundles while preserving all 25 first-move labels.
// Usage: binary input.txt output.json. No claim of minimum family size.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
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
    uint64_t states = 0;
    uint64_t limit = 0;
    bool win(U s) {
        auto &value = memo[s];
        if (value >= 0) return value;
        ++states;
        if (limit && states > limit) throw std::runtime_error("search node budget");
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
    void prepare() {
        triples.assign(v, {});
        for (size_t i = 0; i < quads.size(); ++i) if (active[group[i]]) {
            U q = quads[i];
            for (int p = 0; p < v; ++p) if (q & (U(1) << p))
                triples[p].push_back(q ^ (U(1) << p));
        }
        std::fill(memo.begin(), memo.end(), int8_t(-1));
        states = 0;
    }
    bool matches() {
        prepare();
        for (int p = 0; p < v; ++p)
            if ((!win(U(1) << p)) != bool(target & (U(1) << p))) return false;
        return true;
    }
};

int main(int argc, char** argv) {
    if (argc != 3 && argc != 4) return 2;
    std::string mode = argc == 4 ? argv[3] : "group";
    bool sample_mode = mode == "sample";
    bool orbit_mode = mode != "group";
    auto start = std::chrono::steady_clock::now();
    std::ifstream in(argv[1]);
    Solver s;
    int nq;
    if (!(in >> s.v >> nq >> s.ng >> s.target) || s.v != 25) return 3;
    s.quads.resize(nq); s.group.resize(nq);
    for (int i = 0; i < nq; ++i) if (!(in >> s.quads[i] >> s.group[i])) return 4;
    std::map<int, std::vector<int>> block_map;
    for (int gi = 0; gi < s.ng; ++gi) {
        int representative;
        if (!(in >> representative)) return 7;
        block_map[orbit_mode ? representative : gi].push_back(gi);
    }
    std::vector<std::vector<int>> blocks;
    for (const auto &entry : block_map) blocks.push_back(entry.second);
    s.active.assign(s.ng, true);
    s.memo.resize(U(1) << s.v, -1);
    if (!s.matches()) return 5;
    std::mt19937 rng(200224);
    int trials = 0, accepted = 0;
    std::vector<int> order(blocks.size());
    std::iota(order.begin(), order.end(), 0);
    int budget_skips = 0;
    if (sample_mode) {
        std::vector<double> weights(blocks.size(), 0);
        for (size_t bi = 0; bi < blocks.size(); ++bi)
            for (int gi : blocks[bi]) weights[bi] += std::count(s.group.begin(), s.group.end(), gi);
        std::vector<int> by_weight = order;
        std::sort(by_weight.begin(), by_weight.end(), [&](int a, int b) { return weights[a] > weights[b]; });
        std::discrete_distribution<int> distribution(weights.begin(), weights.end());
        bool found = false;
        for (int attempt = 0; attempt < 100; ++attempt) {
            std::fill(s.active.begin(), s.active.end(), false);
            std::vector<bool> selected(blocks.size(), false);
            int count = attempt < 15 ? attempt+1 : 3 + attempt%7;
            for (int i = 0; i < count; ++i) {
                int bi;
                if (attempt < 15) bi = by_weight[i];
                else do { bi = distribution(rng); } while (selected[bi]);
                selected[bi] = true;
                for (int gi : blocks[bi]) s.active[gi] = true;
            }
            ++trials;
            s.limit = 1000000;
            try { found = s.matches(); }
            catch (const std::runtime_error&) { ++budget_skips; }
            if (found) break;
            if (attempt % 10 == 9) std::cout << "samples=" << attempt+1 << " budget_skips=" << budget_skips << std::endl;
        }
        s.limit = 0;
        if (!found) {
            std::ofstream out(argv[2]);
            out << "{\"mode\":\"sample\",\"witness\":null,\"attempts\":" << trials
                << ",\"budget_skips\":" << budget_skips << "}\n";
            return 0;
        }
        accepted = std::count(s.active.begin(), s.active.end(), false);
        std::cout << "sample found, kept=" << s.ng-accepted << std::endl;
    }
    for (int pass = 0; pass < 3; ++pass) {
        std::shuffle(order.begin(), order.end(), rng);
        int changed = 0;
        for (int bi : order) if (s.active[blocks[bi][0]]) {
            for (int gi : blocks[bi]) s.active[gi] = false;
            ++trials;
            if (s.matches()) { accepted += blocks[bi].size(); ++changed; }
            else for (int gi : blocks[bi]) s.active[gi] = true;
            if (trials % 25 == 0)
                std::cout << "tested=" << trials << " kept=" << s.ng-accepted << std::endl;
        }
        if (!changed) break;
    }
    if (!s.matches()) return 6;
    auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::ofstream out(argv[2]);
    out << "{\"mode\":\"" << mode
        << "\",\"seed\":200224,\"kept_group_ids\":[";
    bool first = true;
    int kept_quads = 0;
    for (int gi = 0; gi < s.ng; ++gi) if (s.active[gi]) {
        if (!first) out << ',';
        first = false; out << gi;
    }
    for (int gi : s.group) kept_quads += s.active[gi];
    out << "],\"winning_first_move_mask\":" << s.target
        << ",\"kept_quads\":" << kept_quads
        << ",\"trials\":" << trials << ",\"seconds\":" << elapsed
        << ",\"final_solver_states\":" << s.states << "}\n";
    std::cout << "done, kept=" << s.ng-accepted << " quads=" << kept_quads
              << " seconds=" << elapsed << std::endl;
}
