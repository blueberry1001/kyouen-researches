#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

struct Bits {
    std::uint64_t lo = 0;
    std::uint64_t hi = 0;
};

static inline bool operator==(Bits a, Bits b) { return a.lo == b.lo && a.hi == b.hi; }
static inline bool operator<(Bits a, Bits b) {
    return a.hi < b.hi || (a.hi == b.hi && a.lo < b.lo);
}
static inline Bits operator|(Bits a, Bits b) { return {a.lo | b.lo, a.hi | b.hi}; }
static inline Bits operator&(Bits a, Bits b) { return {a.lo & b.lo, a.hi & b.hi}; }
static inline Bits operator~(Bits a) { return {~a.lo, ~a.hi}; }
static inline bool any(Bits a) { return a.lo != 0 || a.hi != 0; }
static inline int popcount(Bits a) { return std::popcount(a.lo) + std::popcount(a.hi); }
static inline Bits bitof(int p) {
    return p < 64 ? Bits{std::uint64_t{1} << p, 0}
                  : Bits{0, std::uint64_t{1} << (p - 64)};
}
static inline bool intersects(Bits a, Bits b) { return any(a & b); }
static inline int take_lsb(Bits& a) {
    if (a.lo != 0) {
        const int p = std::countr_zero(a.lo);
        a.lo &= a.lo - 1;
        return p;
    }
    const int p = std::countr_zero(a.hi);
    a.hi &= a.hi - 1;
    return p + 64;
}

struct BitsHash {
    std::size_t operator()(Bits b) const noexcept {
        auto mix = [](std::uint64_t x) {
            x ^= x >> 30;
            x *= 0xbf58476d1ce4e5b9ULL;
            x ^= x >> 27;
            x *= 0x94d049bb133111ebULL;
            return x ^ (x >> 31);
        };
        return static_cast<std::size_t>(mix(b.lo ^ mix(b.hi + 0x9e3779b97f4a7c15ULL)));
    }
};

class Board {
public:
    explicit Board(int n)
        : n_(n), v_(n * n), full_(make_full(v_)),
          completion_(std::size_t(v_) * v_ * v_), maps_(8, std::vector<int>(v_)) {
        if (n_ <= 0 || v_ > 128) {
            throw std::invalid_argument("board must contain between 1 and 128 points");
        }
        build_maps();
        build_forbidden_quadruples();
    }

    int size() const { return n_; }
    int point_count() const { return v_; }
    Bits full_mask() const { return full_; }
    std::uint64_t forbidden_count() const { return forbidden_count_; }

    Bits mask_from_ids(const std::vector<int>& ids) const {
        Bits out{};
        for (int id : ids) {
            if (id < 0 || id >= v_) throw std::invalid_argument("point id outside board");
            const Bits b = bitof(id);
            if (intersects(out, b)) throw std::invalid_argument("duplicate point id");
            out = out | b;
        }
        return out;
    }

    std::vector<int> ids(Bits mask) const {
        std::vector<int> out;
        out.reserve(popcount(mask));
        while (any(mask)) out.push_back(take_lsb(mask));
        return out;
    }

    bool is_valid(Bits state) const {
        const auto points = ids(state);
        for (int i = 0; i < static_cast<int>(points.size()) - 2; ++i) {
            for (int j = i + 1; j < static_cast<int>(points.size()) - 1; ++j) {
                for (int k = j + 1; k < static_cast<int>(points.size()); ++k) {
                    if (intersects(completion_[index(points[i], points[j], points[k])], state)) {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    Bits legal_mask(Bits state) const {
        Bits banned{};
        const auto points = ids(state);
        for (int i = 0; i < static_cast<int>(points.size()) - 2; ++i) {
            for (int j = i + 1; j < static_cast<int>(points.size()) - 1; ++j) {
                for (int k = j + 1; k < static_cast<int>(points.size()); ++k) {
                    banned = banned | completion_[index(points[i], points[j], points[k])];
                }
            }
        }
        return full_ & ~state & ~banned;
    }

    Bits forbidden_empty_mask(Bits state) const {
        return full_ & ~state & ~legal_mask(state);
    }

    Bits transform(Bits state, int t) const {
        if (t < 0 || t >= 8) throw std::invalid_argument("transform must be 0..7");
        Bits out{};
        while (any(state)) {
            const int p = take_lsb(state);
            out = out | bitof(maps_[t][p]);
        }
        return out;
    }

    Bits canonical(Bits state) const {
        Bits best = state;
        for (int t = 1; t < 8; ++t) {
            const Bits candidate = transform(state, t);
            if (candidate < best) best = candidate;
        }
        return best;
    }

private:
    int n_;
    int v_;
    Bits full_;
    std::vector<Bits> completion_;
    std::vector<std::vector<int>> maps_;
    std::uint64_t forbidden_count_ = 0;

    static Bits make_full(int v) {
        if (v <= 64) {
            return {v == 64 ? ~std::uint64_t{0} : ((std::uint64_t{1} << v) - 1), 0};
        }
        const int high = v - 64;
        return {~std::uint64_t{0},
                high == 64 ? ~std::uint64_t{0} : ((std::uint64_t{1} << high) - 1)};
    }

    std::size_t index(int a, int b, int c) const {
        return (std::size_t(a) * v_ + b) * v_ + c;
    }

    static long long det3(long long a00, long long a01, long long a02,
                          long long a10, long long a11, long long a12,
                          long long a20, long long a21, long long a22) {
        return a00 * (a11 * a22 - a12 * a21)
             - a01 * (a10 * a22 - a12 * a20)
             + a02 * (a10 * a21 - a11 * a20);
    }

    bool is_forbidden_quadruple(int a, int b, int c, int d) const {
        const int points[4] = {a, b, c, d};
        long long matrix[4][4]{};
        for (int row = 0; row < 4; ++row) {
            const long long x = points[row] % n_;
            const long long y = points[row] / n_;
            matrix[row][0] = x * x + y * y;
            matrix[row][1] = x;
            matrix[row][2] = y;
            matrix[row][3] = 1;
        }
        long long determinant = 0;
        for (int col = 0; col < 4; ++col) {
            long long minor[3][3]{};
            for (int row = 1; row < 4; ++row) {
                int out = 0;
                for (int col2 = 0; col2 < 4; ++col2) {
                    if (col2 != col) minor[row - 1][out++] = matrix[row][col2];
                }
            }
            const long long minor_det = det3(
                minor[0][0], minor[0][1], minor[0][2],
                minor[1][0], minor[1][1], minor[1][2],
                minor[2][0], minor[2][1], minor[2][2]);
            determinant += (col % 2 == 0 ? 1 : -1) * matrix[0][col] * minor_det;
        }
        return determinant == 0;
    }

    void build_forbidden_quadruples() {
        for (int a = 0; a < v_; ++a) {
            for (int b = a + 1; b < v_; ++b) {
                for (int c = b + 1; c < v_; ++c) {
                    for (int d = c + 1; d < v_; ++d) {
                        if (!is_forbidden_quadruple(a, b, c, d)) continue;
                        ++forbidden_count_;
                        const int q[4] = {a, b, c, d};
                        for (int omitted = 0; omitted < 4; ++omitted) {
                            int triple[3]{};
                            int out = 0;
                            for (int i = 0; i < 4; ++i) {
                                if (i != omitted) triple[out++] = q[i];
                            }
                            completion_[index(triple[0], triple[1], triple[2])] =
                                completion_[index(triple[0], triple[1], triple[2])] | bitof(q[omitted]);
                        }
                    }
                }
            }
        }
    }

    void build_maps() {
        for (int p = 0; p < v_; ++p) {
            const int x = p % n_;
            const int y = p / n_;
            const int last = n_ - 1;
            const std::array<std::pair<int, int>, 8> transformed = {{
                {x, y}, {last - x, y}, {x, last - y}, {last - x, last - y},
                {y, x}, {last - y, x}, {y, last - x}, {last - y, last - x}
            }};
            for (int t = 0; t < 8; ++t) {
                maps_[t][p] = transformed[t].second * n_ + transformed[t].first;
            }
        }
    }
};

enum class Outcome : std::uint8_t { Losing = 1, Winning = 2 };

class ReferenceSolver {
public:
    ReferenceSolver(const Board& board, std::uint64_t node_limit)
        : board_(board), node_limit_(node_limit) {}

    Outcome solve(Bits state) {
        if (!board_.is_valid(state)) throw std::invalid_argument("invalid position");
        return solve_inner(state);
    }

    int winning_move(Bits state) {
        if (solve(state) == Outcome::Losing) return -1;
        auto moves = board_.ids(board_.legal_mask(state));
        std::sort(moves.begin(), moves.end(), [&](int a, int b) {
            const auto ca = board_.legal_mask(state | bitof(a));
            const auto cb = board_.legal_mask(state | bitof(b));
            if (popcount(ca) != popcount(cb)) return popcount(ca) < popcount(cb);
            return board_.canonical(state | bitof(a)) < board_.canonical(state | bitof(b));
        });
        for (int move : moves) {
            if (solve_inner(state | bitof(move)) == Outcome::Losing) return move;
        }
        return -1;
    }

    std::uint64_t visited() const { return visited_; }

private:
    const Board& board_;
    std::uint64_t node_limit_;
    std::uint64_t visited_ = 0;
    std::unordered_map<Bits, Outcome, BitsHash> memo_;

    Outcome solve_inner(Bits state) {
        const Bits key = board_.canonical(state);
        if (const auto it = memo_.find(key); it != memo_.end()) return it->second;
        if (node_limit_ != 0 && visited_ >= node_limit_) {
            throw std::runtime_error("node limit exceeded");
        }
        ++visited_;
        const Bits legal = board_.legal_mask(state);
        if (!any(legal)) {
            memo_.emplace(key, Outcome::Losing);
            return Outcome::Losing;
        }

        struct Child { int legal_count; Bits key; Bits state; };
        std::vector<Child> children;
        Bits moves = legal;
        while (any(moves)) {
            const int move = take_lsb(moves);
            const Bits child = state | bitof(move);
            const Bits child_key = board_.canonical(child);
            bool duplicate = false;
            for (const auto& old : children) {
                if (old.key == child_key) { duplicate = true; break; }
            }
            if (duplicate) continue;
            children.push_back({popcount(board_.legal_mask(child)), child_key, child});
        }
        std::sort(children.begin(), children.end(), [](const Child& a, const Child& b) {
            if (a.legal_count != b.legal_count) return a.legal_count < b.legal_count;
            return a.key < b.key;
        });
        for (const auto& child : children) {
            if (solve_inner(child.state) == Outcome::Losing) {
                memo_.emplace(key, Outcome::Winning);
                return Outcome::Winning;
            }
        }
        memo_.emplace(key, Outcome::Losing);
        return Outcome::Losing;
    }
};

struct Options {
    int size = 0;
    std::string ids;
    bool serve = false;
    bool solve = false;
    std::uint64_t node_limit = 0;
    std::string format = "json";
};

static std::string require_value(int argc, char** argv, int& i, const char* option) {
    if (++i >= argc) throw std::invalid_argument(std::string(option) + " requires a value");
    return argv[i];
}

static Options parse_options(int argc, char** argv) {
    Options out;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--size") out.size = std::stoi(require_value(argc, argv, i, "--size"));
        else if (arg == "--ids") out.ids = require_value(argc, argv, i, "--ids");
        else if (arg == "--serve") out.serve = true;
        else if (arg == "--solve") out.solve = true;
        else if (arg == "--node-limit") out.node_limit = std::stoull(require_value(argc, argv, i, "--node-limit"));
        else if (arg == "--format") out.format = require_value(argc, argv, i, "--format");
        else if (arg == "--help" || arg == "-h") {
            std::cout << "usage: kyouen-query --size N [--ids CSV] [--serve] [--solve] "
                         "[--node-limit N] [--format json|kv]\n";
            std::exit(0);
        } else throw std::invalid_argument("unknown option: " + arg);
    }
    if (out.size <= 0) throw std::invalid_argument("--size is required");
    if (out.format != "json" && out.format != "kv") throw std::invalid_argument("--format must be json or kv");
    return out;
}

static std::string trim(std::string value) {
    while (!value.empty() && (value.back() == '\r' || value.back() == '\n' || value.back() == ' ' || value.back() == '\t')) value.pop_back();
    std::size_t start = 0;
    while (start < value.size() && (value[start] == ' ' || value[start] == '\t')) ++start;
    return value.substr(start);
}

static std::vector<int> parse_ids(std::string_view text) {
    std::vector<int> out;
    if (text.empty()) return out;
    std::size_t start = 0;
    while (start <= text.size()) {
        const std::size_t comma = text.find(',', start);
        const std::size_t end = comma == std::string_view::npos ? text.size() : comma;
        const auto part = text.substr(start, end - start);
        if (part.empty()) throw std::invalid_argument("empty point id");
        out.push_back(std::stoi(std::string(part)));
        if (comma == std::string_view::npos) break;
        start = comma + 1;
    }
    return out;
}

static std::string join_ids(const Board& board, Bits bits) {
    std::ostringstream out;
    const auto ids = board.ids(bits);
    for (std::size_t i = 0; i < ids.size(); ++i) {
        if (i) out << ',';
        out << ids[i];
    }
    return out.str();
}

static std::string json_array(const Board& board, Bits bits) {
    std::ostringstream out;
    out << '[';
    const auto ids = board.ids(bits);
    for (std::size_t i = 0; i < ids.size(); ++i) {
        if (i) out << ',';
        out << ids[i];
    }
    out << ']';
    return out.str();
}

struct QueryResult {
    bool valid = false;
    Bits legal{};
    Bits forbidden{};
    Bits canonical{};
    std::array<Bits, 8> transforms{};
    std::string outcome = "NA";
    int winning_move = -1;
    std::uint64_t visited = 0;
};

static QueryResult run_query(const Board& board, Bits state, const Options& options) {
    QueryResult result;
    result.valid = board.is_valid(state);
    result.legal = board.legal_mask(state);
    result.forbidden = board.forbidden_empty_mask(state);
    result.canonical = board.canonical(state);
    for (int t = 0; t < 8; ++t) result.transforms[t] = board.transform(state, t);
    if (options.solve) {
        if (!result.valid) {
            result.outcome = "INVALID";
        } else {
            ReferenceSolver solver(board, options.node_limit);
            const Outcome outcome = solver.solve(state);
            result.outcome = outcome == Outcome::Winning ? "WIN" : "LOSS";
            result.winning_move = outcome == Outcome::Winning ? solver.winning_move(state) : -1;
            result.visited = solver.visited();
        }
    }
    return result;
}

static void print_kv(const Board& board, const QueryResult& result) {
    std::cout << "valid=" << (result.valid ? 1 : 0)
              << ";legal=" << join_ids(board, result.legal)
              << ";forbidden=" << join_ids(board, result.forbidden)
              << ";canonical=" << join_ids(board, result.canonical);
    for (int t = 0; t < 8; ++t) {
        std::cout << ";t" << t << '=' << join_ids(board, result.transforms[t]);
    }
    std::cout << ";forbidden_quadruples=" << board.forbidden_count()
              << ";outcome=" << result.outcome
              << ";winning_move=";
    if (result.winning_move < 0) std::cout << "NA";
    else std::cout << result.winning_move;
    std::cout << ";visited=" << result.visited << '\n';
}

static void print_json(const Board& board, const QueryResult& result) {
    std::cout << '{'
              << "\"valid\":" << (result.valid ? "true" : "false")
              << ",\"legal_ids\":" << json_array(board, result.legal)
              << ",\"forbidden_ids\":" << json_array(board, result.forbidden)
              << ",\"canonical_ids\":" << json_array(board, result.canonical)
              << ",\"transforms\":[";
    for (int t = 0; t < 8; ++t) {
        if (t) std::cout << ',';
        std::cout << json_array(board, result.transforms[t]);
    }
    std::cout << "]"
              << ",\"forbidden_quadruples\":" << board.forbidden_count()
              << ",\"outcome\":\"" << result.outcome << "\""
              << ",\"winning_move\":";
    if (result.winning_move < 0) std::cout << "null";
    else std::cout << result.winning_move;
    std::cout << ",\"visited\":" << result.visited << "}\n";
}

static void emit(const Board& board, const QueryResult& result, const Options& options) {
    if (options.format == "kv") print_kv(board, result);
    else print_json(board, result);
    std::cout.flush();
}

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const Board board(options.size);
        if (options.serve) {
            std::string line;
            while (std::getline(std::cin, line)) {
                line = trim(std::move(line));
                try {
                    const Bits state = board.mask_from_ids(parse_ids(line));
                    emit(board, run_query(board, state, options), options);
                } catch (const std::exception& e) {
                    if (options.format == "kv") std::cout << "error=" << e.what() << '\n';
                    else std::cout << "{\"error\":\"query failed\"}\n";
                    std::cout.flush();
                }
            }
        } else {
            const Bits state = board.mask_from_ids(parse_ids(options.ids));
            emit(board, run_query(board, state, options), options);
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
