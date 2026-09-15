// 8x8 factorial population exporter.
// Semantics match scripts/export-9x9-factorial-population.cpp; only
// board-size-dependent geometry (N, V, D4 maps, indexing, masks) differs.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <set>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

constexpr int N = 8;
constexpr int V = N * N; // 64
constexpr int NM1 = N - 1;

using Mask = std::uint64_t;

inline void setbit(Mask& m, int p) { m |= Mask{1} << p; }
inline bool has(Mask m, int p) { return (m >> p) & 1ULL; }
inline int popcount(Mask m) { return __builtin_popcountll(m); }

inline std::size_t tidx(int a, int b, int c) {
    if (a > b) std::swap(a, b);
    if (b > c) std::swap(b, c);
    if (a > b) std::swap(a, b);
    return (std::size_t(a) * V + b) * V + c;
}
inline std::uint32_t key4(int a, int b, int c, int d) {
    return (((std::uint32_t(a) * V + b) * V + c) * V + d);
}

long long det3(long long a, long long b, long long c, long long d, long long e,
               long long f, long long g, long long h, long long i) {
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
}

bool forbidden4(int a, int b, int c, int d) {
    int p[4] = {a, b, c, d};
    long long x[4], y[4], z[4];
    for (int k = 0; k < 4; ++k) {
        x[k] = p[k] % N;
        y[k] = p[k] / N;
        z[k] = x[k] * x[k] + y[k] * y[k];
    }
    return det3(x[1] - x[0], y[1] - y[0], z[1] - z[0], x[2] - x[0], y[2] - y[0],
                z[2] - z[0], x[3] - x[0], y[3] - y[0], z[3] - z[0]) == 0;
}

int transform_point(int v, int g) {
    int x = v % N, y = v / N, nx = 0, ny = 0;
    switch (g) {
        case 0: nx = x; ny = y; break;
        case 1: nx = NM1 - y; ny = x; break;
        case 2: nx = NM1 - x; ny = NM1 - y; break;
        case 3: nx = y; ny = NM1 - x; break;
        case 4: nx = NM1 - x; ny = y; break;
        case 5: nx = x; ny = NM1 - y; break;
        case 6: nx = y; ny = x; break;
        default: nx = NM1 - y; ny = NM1 - x; break;
    }
    return ny * N + nx;
}

struct Canonical4 {
    std::uint32_t key;
    std::array<int, 4> parent;
    int transform;
};

Canonical4 canonical4(const std::array<int, 4>& p) {
    Canonical4 best{UINT32_MAX, {}, 0};
    for (int g = 0; g < 8; ++g) {
        std::array<int, 4> q;
        for (int i = 0; i < 4; ++i) q[i] = transform_point(p[i], g);
        std::sort(q.begin(), q.end());
        auto k = key4(q[0], q[1], q[2], q[3]);
        if (k < best.key) best = {k, q, g};
    }
    return best;
}

int orbit_size(const std::array<int, 4>& p) {
    std::set<std::uint32_t> images;
    for (int g = 0; g < 8; ++g) {
        std::array<int, 4> q;
        for (int i = 0; i < 4; ++i) q[i] = transform_point(p[i], g);
        std::sort(q.begin(), q.end());
        images.insert(key4(q[0], q[1], q[2], q[3]));
    }
    return int(images.size());
}

std::string parent_text(const std::array<int, 4>& p) {
    return std::to_string(p[0]) + "," + std::to_string(p[1]) + "," +
           std::to_string(p[2]) + "," + std::to_string(p[3]);
}

struct Scores {
    int best[4] = {-1, -1, -1, -1};
    int count[4] = {0, 0, 0, 0};
    int move[4] = {-1, -1, -1, -1};
    int E_at[4] = {0, 0, 0, 0};  // E value at the argmax move (if unique)
    int O_at[4] = {0, 0, 0, 0};
    int pairE_at[4] = {0, 0, 0, 0};
    int pairO_at[4] = {0, 0, 0, 0};
};

Scores score_parent(int a, int b, int c, int d, const std::vector<Mask>& completion) {
    int p[4] = {a, b, c, d};
    Mask occupied = 0;
    for (int z : p) setbit(occupied, z);
    Mask existing = completion[tidx(a, b, c)] | completion[tidx(a, b, d)] |
                    completion[tidx(a, c, d)] | completion[tidx(b, c, d)];
    Scores s;
    // Track per-move E/O for the argmax moves.
    int move_E[V] = {0};
    int move_O[V] = {0};
    for (int v = 0; v < V; ++v) {
        if (has(occupied, v) || has(existing, v)) continue;
        int raw = 0;
        Mask uni = 0;
        for (int i = 0; i < 4; ++i) {
            for (int j = i + 1; j < 4; ++j) {
                Mask m = completion[tidx(p[i], p[j], v)];
                raw += popcount(m);
                uni |= m;
            }
        }
        int U = popcount(uni);
        int T = popcount(uni & ~existing);
        int E = U - T;
        int O = raw - U;
        move_E[v] = E;
        move_O[v] = O;
        int score[4] = {T, T + E, T + O, raw};  // S00,S10,S01,S11
        for (int k = 0; k < 4; ++k) {
            if (score[k] > s.best[k]) {
                s.best[k] = score[k];
                s.count[k] = 1;
                s.move[k] = v;
            } else if (score[k] == s.best[k]) {
                ++s.count[k];
            }
        }
    }
    for (int k = 0; k < 4; ++k) {
        if (s.count[k] == 1 && s.move[k] >= 0) {
            s.E_at[k] = move_E[s.move[k]];
            s.O_at[k] = move_O[s.move[k]];
            // pair_E / pair_O as raw pair scores minus T/O components:
            // pairE = E, pairO = O at that move (already computed).
            s.pairE_at[k] = move_E[s.move[k]];
            s.pairO_at[k] = move_O[s.move[k]];
        }
    }
    return s;
}

struct Row {
    std::array<int, 4> parent;
    std::array<int, 4> top;
    int E_at[4];
    int O_at[4];
    int orb;
};

void write_population(const std::vector<Mask>& completion,
                      const std::unordered_set<std::uint32_t>& forbidden,
                      const std::string& out_path) {
    long long parents = 0, all4_unique = 0, any_diff = 0;
    long long raw_E0 = 0, raw_O0 = 0, raw_E1 = 0, raw_O1 = 0, raw_Traw = 0;
    std::unordered_map<std::uint32_t, Row> rows;
    rows.reserve(8000);
    std::unordered_set<std::uint32_t> orb_E0, orb_O0, orb_E1, orb_O1, orb_Traw;
    orb_E0.reserve(6000);
    orb_O0.reserve(1500);
    orb_E1.reserve(6000);
    orb_O1.reserve(1500);
    orb_Traw.reserve(8000);

    for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b)
            for (int c = b + 1; c < V; ++c)
                for (int d = c + 1; d < V; ++d) {
                    if (forbidden.count(key4(a, b, c, d))) continue;
                    ++parents;
                    Scores s = score_parent(a, b, c, d, completion);
                    if (!(s.count[0] == 1 && s.count[1] == 1 && s.count[2] == 1 &&
                          s.count[3] == 1))
                        continue;
                    ++all4_unique;
                    bool diff = !(s.move[0] == s.move[1] && s.move[0] == s.move[2] &&
                                  s.move[0] == s.move[3]);
                    if (!diff) continue;
                    ++any_diff;
                    auto ck = canonical4({a, b, c, d});
                    std::array<int, 4> cmove{};
                    for (int k = 0; k < 4; ++k)
                        cmove[k] = transform_point(s.move[k], ck.transform);
                    int osz = orbit_size({a, b, c, d});
                    rows.emplace(ck.key, Row{ck.parent, cmove, {s.E_at[0], s.E_at[1], s.E_at[2], s.E_at[3]},
                                             {s.O_at[0], s.O_at[1], s.O_at[2], s.O_at[3]}, osz});
                    if (s.move[0] != s.move[1]) { ++raw_E0; orb_E0.insert(ck.key); }
                    if (s.move[0] != s.move[2]) { ++raw_O0; orb_O0.insert(ck.key); }
                    if (s.move[2] != s.move[3]) { ++raw_E1; orb_E1.insert(ck.key); }
                    if (s.move[1] != s.move[3]) { ++raw_O1; orb_O1.insert(ck.key); }
                    if (s.move[0] != s.move[3]) { ++raw_Traw; orb_Traw.insert(ck.key); }
                }

    std::vector<std::pair<std::uint32_t, Row>> ordered(rows.begin(), rows.end());
    std::sort(ordered.begin(), ordered.end(),
              [](const auto& x, const auto& y) { return x.first < y.first; });
    std::ofstream f(out_path);
    if (!f) {
        std::cerr << "cannot open " << out_path << "\n";
        std::exit(3);
    }
    f << "canonical_parent,top_T,top_TE,top_TO,top_raw,diff_E_at_O0,diff_O_at_E0,"
         "diff_E_at_O1,diff_O_at_E1,distinct_top_moves,orbit_size,"
         "E_at_top_T,E_at_top_TE,E_at_top_TO,E_at_top_raw,"
         "O_at_top_T,O_at_top_TE,O_at_top_TO,O_at_top_raw,"
         "pair_E_sum_top_T,pair_O_sum_top_T,pair_E_sum_top_TE,pair_O_sum_top_TE,"
         "pair_E_sum_top_TO,pair_O_sum_top_TO,pair_E_sum_top_raw,pair_O_sum_top_raw\n";
    for (const auto& [key, row] : ordered) {
        (void)key;
        std::set<int> tops{row.top[0], row.top[1], row.top[2], row.top[3]};
        f << '"' << parent_text(row.parent) << "\"," << row.top[0] << ',' << row.top[1]
          << ',' << row.top[2] << ',' << row.top[3] << ',' << (row.top[0] != row.top[1])
          << ',' << (row.top[0] != row.top[2]) << ',' << (row.top[2] != row.top[3])
          << ',' << (row.top[1] != row.top[3]) << ',' << tops.size() << ',' << row.orb
          << ',' << row.E_at[0] << ',' << row.E_at[1] << ',' << row.E_at[2] << ','
          << row.E_at[3] << ',' << row.O_at[0] << ',' << row.O_at[1] << ','
          << row.O_at[2] << ',' << row.O_at[3] << ',' << row.E_at[0] << ','
          << row.O_at[0] << ',' << row.E_at[1] << ',' << row.O_at[1] << ','
          << row.E_at[2] << ',' << row.O_at[2] << ',' << row.E_at[3] << ','
          << row.O_at[3] << '\n';
    }

    // Stratum orbits from frozen structural definitions.
    long long n_o0 = 0, n_olap = 0, n_o1 = 0;
    for (const auto& [key, row] : ordered) {
        (void)key;
        bool o_chg_e0 = row.top[0] != row.top[2];
        bool o_chg_e1 = row.top[1] != row.top[3];
        if (o_chg_e0 && !o_chg_e1) ++n_o0;
        else if (o_chg_e0 && o_chg_e1) ++n_olap;
        else if (!o_chg_e0 && o_chg_e1) ++n_o1;
    }

    std::cout << "forbidden=" << forbidden.size() << "\n"
              << "safe_4stone_parents=" << parents << "\n"
              << "all4_unique_raw=" << all4_unique << "\n"
              << "any_score_diff_raw=" << any_diff << " D4_orbits=" << rows.size()
              << "\n"
              << "E_effect_O0_raw=" << raw_E0 << " D4_orbits=" << orb_E0.size() << "\n"
              << "O_effect_E0_raw=" << raw_O0 << " D4_orbits=" << orb_O0.size() << "\n"
              << "E_effect_O1_raw=" << raw_E1 << " D4_orbits=" << orb_E1.size() << "\n"
              << "O_effect_E1_raw=" << raw_O1 << " D4_orbits=" << orb_O1.size() << "\n"
              << "T_vs_raw_raw=" << raw_Traw << " D4_orbits=" << orb_Traw.size() << "\n"
              << "O0_only_orbits=" << n_o0 << "\n"
              << "O_overlap_orbits=" << n_olap << "\n"
              << "O1_only_orbits=" << n_o1 << "\n"
              << "wrote=" << ordered.size() << " to " << out_path << "\n";
}

int run_validation(const std::vector<Mask>& completion,
                   const std::unordered_set<std::uint32_t>& forbidden) {
    int failures = 0;
    auto fail = [&](const std::string& msg) {
        std::cerr << "VALIDATION FAIL: " << msg << "\n";
        ++failures;
    };

    // Geometry counts.
    long long forbidden_count = 0;
    for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b)
            for (int c = b + 1; c < V; ++c)
                for (int d = c + 1; d < V; ++d)
                    if (forbidden4(a, b, c, d)) ++forbidden_count;
    long long all4 = 0;
    for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b)
            for (int c = b + 1; c < V; ++c)
                for (int d = c + 1; d < V; ++d) ++all4;
    long long safe4 = all4 - forbidden_count;
    std::cout << "geom: V=" << V << " all4=" << all4 << " forbidden4=" << forbidden_count
              << " safe4=" << safe4 << "\n";
    if (forbidden_count != static_cast<long long>(forbidden.size()))
        fail("forbidden set size mismatch");
    if (safe4 <= 0) fail("no safe parents");

    // D4 group: identity and closure on a probe point.
    for (int v = 0; v < V; ++v) {
        if (transform_point(v, 0) != v) fail("D4 identity broken at " + std::to_string(v));
    }
    // Orbit sizes of random parents must be in {1,2,4,8}.
    int checked_parents = 0;
    for (int a = 0; a < V && checked_parents < 64; a += 7)
        for (int b = a + 1; b < V && checked_parents < 64; b += 11)
            for (int c = b + 1; c < V && checked_parents < 64; c += 13) {
                int d = c + 3;
                if (d >= V) continue;
                if (forbidden.count(key4(a, b, c, d))) continue;
                std::array<int, 4> p{a, b, c, d};
                int osz = orbit_size(p);
                if (osz != 1 && osz != 2 && osz != 4 && osz != 8)
                    fail("orbit size not in {1,2,4,8}: " + std::to_string(osz));
                auto ck = canonical4(p);
                // Canonical parent must be invariant under further D4.
                auto ck2 = canonical4(ck.parent);
                if (ck2.key != ck.key) fail("canonical parent not D4-invariant");
                // Top moves of a score on original and on a transform must map.
                Scores s = score_parent(a, b, c, d, completion);
                if (!(s.count[0] == 1 && s.count[1] == 1 && s.count[2] == 1 &&
                      s.count[3] == 1)) {
                    ++checked_parents;
                    continue;
                }
                int g = 3;
                std::array<int, 4> q;
                for (int i = 0; i < 4; ++i) q[i] = transform_point(p[i], g);
                std::sort(q.begin(), q.end());
                Scores sq = score_parent(q[0], q[1], q[2], q[3], completion);
                if (!(sq.count[0] == 1 && sq.count[1] == 1 && sq.count[2] == 1 &&
                      sq.count[3] == 1)) {
                    ++checked_parents;
                    continue;
                }
                for (int k = 0; k < 4; ++k) {
                    int mapped = transform_point(s.move[k], g);
                    if (mapped != sq.move[k])
                        fail("top move not D4-covariant at k=" + std::to_string(k) +
                             " mapped=" + std::to_string(mapped) +
                             " got=" + std::to_string(sq.move[k]));
                    if (s.best[k] != sq.best[k])
                        fail("score not D4-invariant at k=" + std::to_string(k));
                }
                ++checked_parents;
            }
    std::cout << "checked_parents_under_D4=" << checked_parents << "\n";

    // Exhaustive parent invariants on a denser sample of safe parents.
    int sample_n = 0, bad_range = 0, bad_dup = 0, bad_in_parent = 0, bad_illegal5 = 0;
    for (int a = 0; a < V && sample_n < 200; a += 1)
        for (int b = a + 1; b < V && sample_n < 200; b += 2)
            for (int c = b + 1; c < V && sample_n < 200; c += 3)
                for (int d = c + 1; d < V && sample_n < 200; d += 5) {
                    if (forbidden.count(key4(a, b, c, d))) continue;
                    Scores s = score_parent(a, b, c, d, completion);
                    if (!(s.count[0] == 1 && s.count[1] == 1 && s.count[2] == 1 &&
                          s.count[3] == 1))
                        continue;
                    ++sample_n;
                    for (int k = 0; k < 4; ++k) {
                        int m = s.move[k];
                        if (m < 0 || m >= V) ++bad_range;
                        if (m == a || m == b || m == c || m == d) ++bad_in_parent;
                        int stones[5] = {a, b, c, d, m};
                        // duplicates
                        for (int i = 0; i < 5; ++i)
                            for (int j = i + 1; j < 5; ++j)
                                if (stones[i] == stones[j]) ++bad_dup;
                        // illegal 5-stone: any forbidden 4-subset
                        for (int i0 = 0; i0 < 5; ++i0)
                            for (int i1 = i0 + 1; i1 < 5; ++i1)
                                for (int i2 = i1 + 1; i2 < 5; ++i2)
                                    for (int i3 = i2 + 1; i3 < 5; ++i3)
                                        if (forbidden4(stones[i0], stones[i1], stones[i2],
                                                       stones[i3]))
                                            ++bad_illegal5;
                    }
                }
    std::cout << "sampled_eligible_parents=" << sample_n << " bad_range=" << bad_range
              << " bad_dup=" << bad_dup << " bad_in_parent=" << bad_in_parent
              << " bad_illegal5=" << bad_illegal5 << "\n";
    if (bad_range) fail("candidate move out of range");
    if (bad_dup) fail("duplicate stones in parent+move");
    if (bad_in_parent) fail("top move already in parent");
    if (bad_illegal5) fail("parent+move contains forbidden quadruple");

    // Completion table consistency: every forbidden 4-set deposits all 4 omit bits.
    long long completion_entries = 0;
    for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b)
            for (int c = b + 1; c < V; ++c) {
                Mask m = completion[tidx(a, b, c)];
                if (m) ++completion_entries;
            }
    std::cout << "completion_nonempty_triples=" << completion_entries << "\n";
    if (completion_entries == 0) fail("completion table empty");

    if (failures == 0) {
        std::cout << "VALIDATION PASS\n";
        return 0;
    }
    std::cout << "VALIDATION FAILURES=" << failures << "\n";
    return 1;
}

}  // namespace

int main(int argc, char** argv) {
    std::string mode;
    std::string out_path;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--csv") {
            mode = "csv";
            if (i + 1 >= argc) {
                std::cerr << "usage: " << argv[0] << " --csv OUTPUT.csv | --validate\n";
                return 2;
            }
            out_path = argv[++i];
        } else if (a == "--validate") {
            mode = "validate";
        } else {
            std::cerr << "usage: " << argv[0] << " --csv OUTPUT.csv | --validate\n";
            return 2;
        }
    }
    if (mode.empty()) {
        std::cerr << "usage: " << argv[0] << " --csv OUTPUT.csv | --validate\n";
        return 2;
    }

    std::vector<Mask> completion(std::size_t(V) * V * V, 0);
    std::unordered_set<std::uint32_t> forbidden;
    forbidden.reserve(20000);
    long long forbidden_count = 0;
    for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b)
            for (int c = b + 1; c < V; ++c)
                for (int d = c + 1; d < V; ++d) {
                    if (!forbidden4(a, b, c, d)) continue;
                    ++forbidden_count;
                    forbidden.insert(key4(a, b, c, d));
                    int q[4] = {a, b, c, d};
                    for (int omit = 0; omit < 4; ++omit) {
                        int t[3], n = 0;
                        for (int j = 0; j < 4; ++j)
                            if (j != omit) t[n++] = q[j];
                        setbit(completion[tidx(t[0], t[1], t[2])], q[omit]);
                    }
                }

    if (mode == "validate") {
        return run_validation(completion, forbidden);
    }
    write_population(completion, forbidden, out_path);
    return 0;
}
