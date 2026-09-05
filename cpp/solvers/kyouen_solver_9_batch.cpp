#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Bits {
    std::uint64_t lo = 0, hi = 0;
};
static inline bool operator==(Bits a, Bits b) { return a.lo == b.lo && a.hi == b.hi; }
static inline bool operator<(Bits a, Bits b) {
    return a.hi < b.hi || (a.hi == b.hi && a.lo < b.lo);
}
static inline Bits operator|(Bits a, Bits b) { return {a.lo | b.lo, a.hi | b.hi}; }
static inline Bits operator&(Bits a, Bits b) { return {a.lo & b.lo, a.hi & b.hi}; }
static inline Bits operator~(Bits a) { return {~a.lo, ~a.hi}; }
static inline bool any(Bits a) { return a.lo || a.hi; }
static inline int popcount(Bits a) { return std::popcount(a.lo) + std::popcount(a.hi); }
static inline Bits bitof(int p) {
    return p < 64 ? Bits{1ULL << p, 0} : Bits{0, 1ULL << (p - 64)};
}
static inline bool has(Bits a, int p) {
    return p < 64 ? ((a.lo >> p) & 1ULL) : ((a.hi >> (p - 64)) & 1ULL);
}
static inline int take_lsb(Bits& a) {
    if (a.lo) {
        int p = std::countr_zero(a.lo);
        a.lo &= a.lo - 1;
        return p;
    }
    int p = std::countr_zero(a.hi);
    a.hi &= a.hi - 1;
    return p + 64;
}

class FlatMemo81 {
public:
    enum : std::uint32_t { Losing = 1, Winning = 2 };

    explicit FlatMemo81(unsigned power)
        : lows_(std::size_t{1} << power),
          metas_(std::size_t{1} << power),
          mask_((std::size_t{1} << power) - 1) {}

    std::uint32_t get(Bits key) const {
        std::size_t i = mix(key) & mask_;
        while (metas_[i]) {
            std::uint32_t m = metas_[i];
            if (lows_[i] == key.lo && (m >> 2) == key.hi) return m & 3;
            i = (i + 1) & mask_;
        }
        return 0;
    }

    void put(Bits key, std::uint32_t value) {
        std::size_t i = mix(key) & mask_;
        const std::uint32_t meta = (std::uint32_t(key.hi) << 2) | value;
        while (metas_[i]) {
            if (lows_[i] == key.lo && (metas_[i] >> 2) == key.hi) {
                metas_[i] = meta;
                return;
            }
            i = (i + 1) & mask_;
        }
        lows_[i] = key.lo;
        metas_[i] = meta;
        ++used_;
        if (used_ * 10 > metas_.size() * 8) {
            throw std::runtime_error("memo table over 80%");
        }
    }

    std::size_t used() const { return used_; }

private:
    std::vector<std::uint64_t> lows_;
    std::vector<std::uint32_t> metas_;
    std::size_t mask_, used_ = 0;

    static std::uint64_t mix64(std::uint64_t x) {
        x ^= x >> 30;
        x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27;
        x *= 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    static std::uint64_t mix(Bits b) {
        return mix64(b.lo ^ (b.hi * 0x9e3779b97f4a7c15ULL));
    }
};

class Solver9Batch {
    static constexpr int N = 9, V = 81;
    struct TState { std::array<Bits, 8> t{}; };
    struct Child {
        TState state;
        Bits legal, key;
        int legal_count;
        std::uint32_t cached;
    };

public:
    explicit Solver9Batch(unsigned memo_power)
        : completion_(std::size_t(V) * V * V), memo_(memo_power) {
        build_maps();
        build_forbidden_quadruples();
    }

    bool solve_state(const std::vector<int>& stones) {
        Bits occupied{};
        TState state{};
        for (int v : stones) {
            if (v < 0 || v >= V || has(occupied, v)) {
                throw std::runtime_error("bad state: point must be unique and in 0..80");
            }
            occupied = occupied | bitof(v);
            state = add(state, v);
        }
        if (any(danger_from_occupied(occupied) & occupied)) {
            throw std::runtime_error("bad state: already contains a forbidden quadruple");
        }
        return win(state, legal_from_occupied(occupied));
    }

    std::uint64_t visited() const { return visited_; }
    std::size_t memo_used() const { return memo_.used(); }
    std::uint64_t forbidden_count() const { return forbidden_count_; }

private:
    std::vector<Bits> completion_;
    std::array<std::array<Bits, V>, 8> tbit_{};
    FlatMemo81 memo_;
    std::uint64_t forbidden_count_ = 0, visited_ = 0;

    static long long det3(long long a00, long long a01, long long a02,
                          long long a10, long long a11, long long a12,
                          long long a20, long long a21, long long a22) {
        return a00 * (a11 * a22 - a12 * a21)
             - a01 * (a10 * a22 - a12 * a20)
             + a02 * (a10 * a21 - a11 * a20);
    }

    static bool forbidden(int a, int b, int c, int d) {
        int ids[4] = {a, b, c, d};
        long long m[4][4]{};
        for (int r = 0; r < 4; ++r) {
            long long x = ids[r] % N, y = ids[r] / N;
            m[r][0] = x * x + y * y;
            m[r][1] = x;
            m[r][2] = y;
            m[r][3] = 1;
        }
        long long determinant = 0;
        for (int col = 0; col < 4; ++col) {
            long long z[3][3]{};
            for (int r = 1; r < 4; ++r) {
                int q = 0;
                for (int c2 = 0; c2 < 4; ++c2) {
                    if (c2 != col) z[r - 1][q++] = m[r][c2];
                }
            }
            long long md = det3(z[0][0], z[0][1], z[0][2],
                                z[1][0], z[1][1], z[1][2],
                                z[2][0], z[2][1], z[2][2]);
            determinant += (col % 2 == 0 ? 1 : -1) * m[0][col] * md;
        }
        return determinant == 0;
    }

    static constexpr std::size_t idx(int a, int b, int c) {
        return (std::size_t(a) * V + b) * V + c;
    }
    static void sort3(int& a, int& b, int& c) {
        if (a > b) std::swap(a, b);
        if (b > c) std::swap(b, c);
        if (a > b) std::swap(a, b);
    }

    void build_maps() {
        for (int p = 0; p < V; ++p) {
            int x = p % N, y = p / N;
            int nx[8] = {x, N - 1 - x, x, N - 1 - x,
                         y, N - 1 - y, y, N - 1 - y};
            int ny[8] = {y, y, N - 1 - y, N - 1 - y,
                         x, x, N - 1 - x, N - 1 - x};
            for (int k = 0; k < 8; ++k) {
                tbit_[k][p] = bitof(ny[k] * N + nx[k]);
            }
        }
    }

    void build_forbidden_quadruples() {
        for (int a = 0; a < V; ++a)
        for (int b = a + 1; b < V; ++b)
        for (int c = b + 1; c < V; ++c)
        for (int d = c + 1; d < V; ++d) {
            if (!forbidden(a, b, c, d)) continue;
            ++forbidden_count_;
            int q[4] = {a, b, c, d};
            for (int omit = 0; omit < 4; ++omit) {
                int t[3], p = 0;
                for (int j = 0; j < 4; ++j) if (j != omit) t[p++] = q[j];
                completion_[idx(t[0], t[1], t[2])] =
                    completion_[idx(t[0], t[1], t[2])] | bitof(q[omit]);
            }
        }
    }

    TState add(TState state, int v) const {
        for (int k = 0; k < 8; ++k) state.t[k] = state.t[k] | tbit_[k][v];
        return state;
    }

    static Bits canonical(const TState& state) {
        Bits result = state.t[0];
        for (int k = 1; k < 8; ++k) if (state.t[k] < result) result = state.t[k];
        return result;
    }

    Bits added_bans(Bits occupied, int v) const {
        int verts[V], n = 0;
        while (any(occupied)) verts[n++] = take_lsb(occupied);
        Bits result{};
        for (int i = 0; i < n; ++i)
        for (int j = i + 1; j < n; ++j) {
            int a = verts[i], b = verts[j], c = v;
            sort3(a, b, c);
            result = result | completion_[idx(a, b, c)];
        }
        return result;
    }

    Bits danger_from_occupied(Bits occupied) const {
        int verts[V], n = 0;
        while (any(occupied)) verts[n++] = take_lsb(occupied);
        Bits result{};
        for (int i = 0; i < n; ++i)
        for (int j = i + 1; j < n; ++j)
        for (int k = j + 1; k < n; ++k) {
            result = result | completion_[idx(verts[i], verts[j], verts[k])];
        }
        return result;
    }

    Bits legal_from_occupied(Bits occupied) const {
        Bits all{~0ULL, (1ULL << 17) - 1};
        Bits legal = (all & ~occupied) & ~danger_from_occupied(occupied);
        legal.hi &= (1ULL << 17) - 1;
        return legal;
    }

    bool win(const TState& state, Bits legal) {
        Bits key = canonical(state);
        if (auto cached = memo_.get(key)) return cached == FlatMemo81::Winning;
        ++visited_;
        if (!any(legal)) {
            memo_.put(key, FlatMemo81::Losing);
            return false;
        }

        std::array<Child, V> children{};
        int n = 0;
        Bits moves = legal;
        while (any(moves)) {
            int v = take_lsb(moves);
            TState next_state = add(state, v);
            Bits next_legal = (legal & ~bitof(v)) & ~added_bans(state.t[0], v);
            next_legal.hi &= (1ULL << 17) - 1;
            Bits next_key = canonical(next_state);

            bool duplicate = false;
            for (int i = 0; i < n; ++i) {
                if (children[i].key == next_key) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate) continue;

            auto cached = memo_.get(next_key);
            children[n++] = {next_state, next_legal, next_key,
                             popcount(next_legal), cached};
        }

        std::sort(children.begin(), children.begin() + n,
                  [](const Child& a, const Child& b) {
            int pa = a.cached == FlatMemo81::Losing ? 0 : (a.cached ? 2 : 1);
            int pb = b.cached == FlatMemo81::Losing ? 0 : (b.cached ? 2 : 1);
            if (pa != pb) return pa < pb;
            if (a.legal_count != b.legal_count) return a.legal_count < b.legal_count;
            return a.key < b.key;
        });

        for (int i = 0; i < n; ++i) {
            bool child_win = children[i].cached
                ? children[i].cached == FlatMemo81::Winning
                : win(children[i].state, children[i].legal);
            if (!child_win) {
                memo_.put(key, FlatMemo81::Winning);
                return true;
            }
        }
        memo_.put(key, FlatMemo81::Losing);
        return false;
    }
};

static std::vector<std::string> parse_csv_fields(const std::string& line) {
    std::vector<std::string> result;
    std::string field;
    bool quoted = false;
    for (char c : line) {
        if (c == '"') {
            quoted = !quoted;
            field += c;
        } else if (c == ',' && !quoted) {
            result.push_back(field);
            field.clear();
        } else {
            field += c;
        }
    }
    result.push_back(field);
    return result;
}

static std::vector<int> parse_state(std::string text) {
    if (!text.empty() && text.front() == '"') text.erase(text.begin());
    if (!text.empty() && text.back() == '"') text.pop_back();
    std::vector<int> result;
    std::stringstream stream(text);
    std::string token;
    while (std::getline(stream, token, ',')) result.push_back(std::stoi(token));
    return result;
}

int main(int argc, char** argv) {
    try {
        std::string input_path, output_path;
        unsigned memo_power = 28;
        long long limit = -1;

        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--input" && i + 1 < argc) input_path = argv[++i];
            else if (arg == "--output" && i + 1 < argc) output_path = argv[++i];
            else if (arg == "--memo-power" && i + 1 < argc) memo_power = std::stoul(argv[++i]);
            else if (arg == "--limit" && i + 1 < argc) limit = std::stoll(argv[++i]);
            else {
                std::cerr << "usage: " << argv[0]
                          << " --input CSV --output CSV [--memo-power N] [--limit N]\n";
                return 2;
            }
        }
        if (input_path.empty() || output_path.empty()) {
            throw std::runtime_error("--input and --output are required");
        }

        std::ifstream input(input_path);
        std::ofstream output(output_path);
        if (!input || !output) throw std::runtime_error("cannot open input/output file");

        std::string line;
        if (!std::getline(input, line)) throw std::runtime_error("empty input");
        auto header = parse_csv_fields(line);
        if (header.size() != 3 || header[0] != "canonical_parent" || header[1] != "pair_top") {
            throw std::runtime_error("expected canonical_parent,pair_top,<other_top> CSV");
        }

        Solver9Batch solver(memo_power);
        output << "canonical_parent,pair_top," << header[2]
               << ",pair_child_outcome," << header[2]
               << "_child_outcome,visited_delta,memo_used\n";

        long long row = 0;
        while (std::getline(input, line)) {
            if (line.empty()) continue;
            if (limit >= 0 && row >= limit) break;
            auto fields = parse_csv_fields(line);
            if (fields.size() != 3) throw std::runtime_error("malformed CSV row");

            auto parent = parse_state(fields[0]);
            if (parent.size() != 4) throw std::runtime_error("expected four-stone parent");
            int pair_top = std::stoi(fields[1]);
            int other_top = std::stoi(fields[2]);

            auto pair_state = parent;
            auto other_state = parent;
            pair_state.push_back(pair_top);
            other_state.push_back(other_top);

            std::uint64_t before = solver.visited();
            bool pair_win = solver.solve_state(pair_state);
            bool other_win = solver.solve_state(other_state);
            std::uint64_t delta = solver.visited() - before;

            output << fields[0] << ',' << pair_top << ',' << other_top << ','
                   << (pair_win ? "WIN" : "LOSS") << ','
                   << (other_win ? "WIN" : "LOSS") << ','
                   << delta << ',' << solver.memo_used() << '\n';
            output.flush();

            ++row;
            std::cerr << "row=" << row << " visited_delta=" << delta
                      << " memo=" << solver.memo_used() << '\n';
        }

        std::cerr << "done rows=" << row
                  << " forbidden=" << solver.forbidden_count()
                  << " visited=" << solver.visited()
                  << " memo=" << solver.memo_used() << '\n';
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
