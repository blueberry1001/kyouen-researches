#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

struct Mask81 {
    uint64_t lo = 0;
    uint64_t hi = 0;
};

static inline Mask81 operator|(Mask81 a, Mask81 b) {
    return {a.lo | b.lo, a.hi | b.hi};
}

static inline bool operator==(Mask81 a, Mask81 b) {
    return a.lo == b.lo && a.hi == b.hi;
}

static inline void add_bit(Mask81& m, int i) {
    if (i < 64) m.lo |= 1ULL << i;
    else m.hi |= 1ULL << (i - 64);
}

static inline bool has_bit(Mask81 m, int i) {
    return i < 64 ? ((m.lo >> i) & 1ULL) : ((m.hi >> (i - 64)) & 1ULL);
}

static inline int popcount(Mask81 m) {
    return __builtin_popcountll(m.lo) + __builtin_popcountll(m.hi);
}

static inline Mask81 without(Mask81 a, Mask81 b) {
    return {a.lo & ~b.lo, a.hi & ~b.hi};
}

static inline int triple_index(int a, int b, int c) {
    if (a > b) std::swap(a, b);
    if (b > c) std::swap(b, c);
    if (a > b) std::swap(a, b);
    return (a * 81 + b) * 81 + c;
}

static inline uint32_t key4(int a, int b, int c, int d) {
    return static_cast<uint32_t>((((a * 81) + b) * 81 + c) * 81 + d);
}

static long long det3(
    long long a, long long b, long long c,
    long long d, long long e, long long f,
    long long g, long long h, long long i) {
    return a * (e * i - f * h)
         - b * (d * i - f * g)
         + c * (d * h - e * g);
}

static bool forbidden4(int a, int b, int c, int d) {
    const int p[4] = {a, b, c, d};
    long long x[4], y[4], z[4];
    for (int k = 0; k < 4; ++k) {
        x[k] = p[k] % 9;
        y[k] = p[k] / 9;
        z[k] = x[k] * x[k] + y[k] * y[k];
    }
    return det3(
        x[1] - x[0], y[1] - y[0], z[1] - z[0],
        x[2] - x[0], y[2] - y[0], z[2] - z[0],
        x[3] - x[0], y[3] - y[0], z[3] - z[0]) == 0;
}

static int transform_point(int v, int g) {
    const int x = v % 9;
    const int y = v / 9;
    int nx = 0, ny = 0;
    switch (g) {
        case 0: nx = x;     ny = y;     break;
        case 1: nx = 8 - y; ny = x;     break;
        case 2: nx = 8 - x; ny = 8 - y; break;
        case 3: nx = y;     ny = 8 - x; break;
        case 4: nx = 8 - x; ny = y;     break;
        case 5: nx = x;     ny = 8 - y; break;
        case 6: nx = y;     ny = x;     break;
        default:nx = 8 - y; ny = 8 - x; break;
    }
    return ny * 9 + nx;
}

struct CanonicalParent {
    uint32_t key;
    std::array<int, 4> parent;
    int transform;
};

static CanonicalParent canonical_parent(const std::array<int, 4>& p) {
    CanonicalParent best{UINT32_MAX, {}, 0};
    for (int g = 0; g < 8; ++g) {
        std::array<int, 4> q;
        for (int i = 0; i < 4; ++i) q[i] = transform_point(p[i], g);
        std::sort(q.begin(), q.end());
        const uint32_t k = key4(q[0], q[1], q[2], q[3]);
        if (k < best.key) best = {k, q, g};
    }
    return best;
}

struct Row {
    std::array<int, 4> parent;
    int pair_top;
    int other_top;
};

static std::string parent_text(const std::array<int, 4>& p) {
    return std::to_string(p[0]) + "," + std::to_string(p[1]) + "," +
           std::to_string(p[2]) + "," + std::to_string(p[3]);
}

static void write_csv(
    const std::string& path,
    const std::unordered_map<uint32_t, Row>& rows,
    const char* other_name) {
    std::vector<std::pair<uint32_t, Row>> ordered(rows.begin(), rows.end());
    std::sort(ordered.begin(), ordered.end(),
              [](const auto& a, const auto& b) { return a.first < b.first; });
    std::ofstream f(path);
    f << "canonical_parent,pair_top," << other_name << "\n";
    for (const auto& [key, row] : ordered) {
        (void)key;
        f << '"' << parent_text(row.parent) << "\"," << row.pair_top << ','
          << row.other_top << '\n';
    }
}

int main(int argc, char** argv) {
    std::string prefix;
    if (argc == 3 && std::string(argv[1]) == "--csv-prefix") {
        prefix = argv[2];
    } else if (argc != 1) {
        std::cerr << "usage: " << argv[0] << " [--csv-prefix PATH_PREFIX]\n";
        return 2;
    }

    std::vector<Mask81> completion(81 * 81 * 81);
    std::unordered_set<uint32_t> forbidden;
    forbidden.reserve(40000);
    long long n_forbidden = 0;

    for (int a = 0; a < 81; ++a)
    for (int b = a + 1; b < 81; ++b)
    for (int c = b + 1; c < 81; ++c)
    for (int d = c + 1; d < 81; ++d) {
        if (!forbidden4(a, b, c, d)) continue;
        ++n_forbidden;
        forbidden.insert(key4(a, b, c, d));
        const int q[4] = {a, b, c, d};
        for (int omit = 0; omit < 4; ++omit) {
            int t[3], j = 0;
            for (int k = 0; k < 4; ++k) if (k != omit) t[j++] = q[k];
            add_bit(completion[triple_index(t[0], t[1], t[2])], q[omit]);
        }
    }

    long long parents = 0;
    long long candidates = 0;
    long long raw_gt_union = 0;
    long long raw_gt_unique = 0;
    long long diff_union = 0, disjoint_union = 0, strict_union = 0;
    long long diff_unique = 0, disjoint_unique = 0, strict_unique = 0;
    int max_over_union = 0, max_over_unique = 0;
    std::unordered_map<uint32_t, Row> canon_union, canon_unique;

    for (int a = 0; a < 81; ++a)
    for (int b = a + 1; b < 81; ++b)
    for (int c = b + 1; c < 81; ++c)
    for (int d = c + 1; d < 81; ++d) {
        if (forbidden.count(key4(a, b, c, d))) continue;
        ++parents;

        const std::array<int, 4> p = {a, b, c, d};
        Mask81 occupied;
        for (int z : p) add_bit(occupied, z);

        const Mask81 existing =
            completion[triple_index(a, b, c)] |
            completion[triple_index(a, b, d)] |
            completion[triple_index(a, c, d)] |
            completion[triple_index(b, c, d)];

        int best_pair = -1, best_union = -1, best_unique = -1;
        int n_pair = 0, n_union = 0, n_unique = 0;
        int pair_move = -1, union_move = -1, unique_move = -1;
        Mask81 top_pair, top_union, top_unique;

        for (int v = 0; v < 81; ++v) {
            if (has_bit(occupied, v) || has_bit(existing, v)) continue;
            ++candidates;

            int raw = 0;
            Mask81 uni;
            for (int i = 0; i < 4; ++i) {
                for (int j = i + 1; j < 4; ++j) {
                    const Mask81 m = completion[triple_index(p[i], p[j], v)];
                    raw += popcount(m);
                    uni = uni | m;
                }
            }

            const int union_score = popcount(uni);
            const int true_unique = popcount(without(uni, existing));
            if (raw > union_score) ++raw_gt_union;
            if (raw > true_unique) ++raw_gt_unique;
            max_over_union = std::max(max_over_union, raw - union_score);
            max_over_unique = std::max(max_over_unique, raw - true_unique);

            auto update_top = [&](int score, int& best, int& count,
                                  int& move, Mask81& set) {
                if (score > best) {
                    best = score;
                    count = 1;
                    move = v;
                    set = {};
                    add_bit(set, v);
                } else if (score == best) {
                    ++count;
                    add_bit(set, v);
                }
            };
            update_top(raw, best_pair, n_pair, pair_move, top_pair);
            update_top(union_score, best_union, n_union, union_move, top_union);
            update_top(true_unique, best_unique, n_unique, unique_move, top_unique);
        }

        auto intersection_size = [](Mask81 x, Mask81 y) {
            return popcount({x.lo & y.lo, x.hi & y.hi});
        };

        if (!(top_pair == top_union)) {
            ++diff_union;
            if (intersection_size(top_pair, top_union) == 0) ++disjoint_union;
            if (n_pair == 1 && n_union == 1) {
                ++strict_union;
                const auto k = canonical_parent(p);
                canon_union.emplace(
                    k.key,
                    Row{k.parent,
                        transform_point(pair_move, k.transform),
                        transform_point(union_move, k.transform)});
            }
        }

        if (!(top_pair == top_unique)) {
            ++diff_unique;
            if (intersection_size(top_pair, top_unique) == 0) ++disjoint_unique;
            if (n_pair == 1 && n_unique == 1) {
                ++strict_unique;
                const auto k = canonical_parent(p);
                canon_unique.emplace(
                    k.key,
                    Row{k.parent,
                        transform_point(pair_move, k.transform),
                        transform_point(unique_move, k.transform)});
            }
        }
    }

    auto pct = [](long long x, long long n) { return 100.0 * x / n; };
    std::cout << "forbidden_4sets=" << n_forbidden << '\n';
    std::cout << "safe_4stone_parents=" << parents << '\n';
    std::cout << "safe_parent_candidate_pairs=" << candidates << '\n';
    std::cout << "candidate raw>union=" << raw_gt_union << " ("
              << pct(raw_gt_union, candidates) << "%), max_overcount="
              << max_over_union << '\n';
    std::cout << "candidate raw>true_unique=" << raw_gt_unique << " ("
              << pct(raw_gt_unique, candidates) << "%), max_gap="
              << max_over_unique << '\n';
    std::cout << "pair vs union: top_set_diff=" << diff_union << " ("
              << pct(diff_union, parents) << "%), disjoint=" << disjoint_union
              << " (" << pct(disjoint_union, parents) << "%), strict_unique_diff="
              << strict_union << " (" << pct(strict_union, parents)
              << "%), D4_orbits=" << canon_union.size() << '\n';
    std::cout << "pair vs true_unique: top_set_diff=" << diff_unique << " ("
              << pct(diff_unique, parents) << "%), disjoint=" << disjoint_unique
              << " (" << pct(disjoint_unique, parents) << "%), strict_unique_diff="
              << strict_unique << " (" << pct(strict_unique, parents)
              << "%), D4_orbits=" << canon_unique.size() << '\n';

    if (!prefix.empty()) {
        write_csv(prefix + "-pair-vs-union.csv", canon_union, "union_top");
        write_csv(prefix + "-pair-vs-true-unique.csv", canon_unique,
                  "true_unique_top");
    }
}
