#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

// 共円ゲーム（2人・完全指摘）の厳密な勝敗探索。
// 「共円または共線を生む手を打ったら負け」は、
// 安全な手だけを合法手とし、合法手がなくなった側が負け、と等価。
//
// 4点判定は整数行列式、局面は64ビット、盤の回転・反転を同一視する。
// 実用上は n <= 7 を想定。n=8 は探索量が急増する。

class FlatMemo {
public:
    enum : std::uint8_t { Empty = 0, Losing = 1, Winning = 2 };

    explicit FlatMemo(unsigned power)
        : keys_(std::size_t{1} << power),
          values_(std::size_t{1} << power, Empty),
          mask_((std::size_t{1} << power) - 1) {}

    std::uint8_t get(std::uint64_t key) const {
        std::size_t i = mix(key) & mask_;
        while (values_[i] != Empty) {
            if (keys_[i] == key) return values_[i];
            i = (i + 1) & mask_;
        }
        return Empty;
    }

    void put(std::uint64_t key, std::uint8_t value) {
        std::size_t i = mix(key) & mask_;
        while (values_[i] != Empty) {
            if (keys_[i] == key) {
                values_[i] = value;
                return;
            }
            i = (i + 1) & mask_;
        }
        keys_[i] = key;
        values_[i] = value;
        ++used_;
        if (used_ * 10 > values_.size() * 8) {
            throw std::runtime_error("メモ表が80%を超えました。容量を増やしてください");
        }
    }

    std::size_t used() const { return used_; }

private:
    std::vector<std::uint64_t> keys_;
    std::vector<std::uint8_t> values_;
    std::size_t mask_;
    std::size_t used_ = 0;

    static std::uint64_t mix(std::uint64_t x) {
        x ^= x >> 30;
        x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27;
        x *= 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
};

class Solver {
public:
    explicit Solver(int n)
        : n_(n),
          vertex_count_(n * n),
          full_mask_(vertex_count_ == 64 ? ~std::uint64_t{0}
                                         : ((std::uint64_t{1} << vertex_count_) - 1)),
          completion_(std::size_t(vertex_count_) * vertex_count_ * vertex_count_),
          memo_(memo_power_for(n)) {
        if (n <= 0 || vertex_count_ > 64) {
            throw std::invalid_argument("1 <= n <= 8 を指定してください");
        }
        build_forbidden_quadruples();
        build_dihedral_transforms();
    }

    void run() {
        const bool first_wins = is_winning(0);
        std::cout << n_ << "x" << n_ << ": "
                  << (first_wins ? "先手必勝" : "後手必勝") << '\n';
        std::cout << "危険な4点組: " << forbidden_count_ << '\n';
        std::cout << "探索した対称性代表局面: " << visited_ << '\n';

        std::vector<int> winning_first_moves;
        for (int v = 0; v < vertex_count_; ++v) {
            if (!is_winning(std::uint64_t{1} << v)) {
                winning_first_moves.push_back(v);
            }
        }

        std::cout << "必勝初手 " << winning_first_moves.size() << " 個:";
        for (int v : winning_first_moves) {
            std::cout << " (" << (v % n_) << ',' << (v / n_) << ')';
        }
        std::cout << '\n';
    }

private:
    struct Child {
        std::uint64_t state;
        int legal_move_count;
    };

    int n_;
    int vertex_count_;
    std::uint64_t full_mask_;
    std::vector<std::uint64_t> completion_;
    std::array<std::array<std::uint64_t, 64>, 8> transformed_bit_{};
    FlatMemo memo_;
    std::uint64_t visited_ = 0;
    std::uint64_t forbidden_count_ = 0;

    static unsigned memo_power_for(int n) {
        if (n <= 5) return 19; // 524,288 slots
        if (n == 6) return 21; // 2,097,152 slots
        if (n == 7) return 23; // 8,388,608 slots
        return 26;             // n=8: experimental, large memory
    }

    static long long det3(long long a00, long long a01, long long a02,
                          long long a10, long long a11, long long a12,
                          long long a20, long long a21, long long a22) {
        return a00 * (a11 * a22 - a12 * a21)
             - a01 * (a10 * a22 - a12 * a20)
             + a02 * (a10 * a21 - a11 * a20);
    }

    std::size_t triple_index(int a, int b, int c) const {
        return (std::size_t(a) * vertex_count_ + b) * vertex_count_ + c;
    }

    bool is_forbidden_quadruple(int a, int b, int c, int d) const {
        const int ids[4] = {a, b, c, d};
        long long m[4][4]{};
        for (int r = 0; r < 4; ++r) {
            const long long x = ids[r] % n_;
            const long long y = ids[r] / n_;
            m[r][0] = x * x + y * y;
            m[r][1] = x;
            m[r][2] = y;
            m[r][3] = 1;
        }

        long long determinant = 0;
        for (int col = 0; col < 4; ++col) {
            long long minor[3][3]{};
            for (int r = 1; r < 4; ++r) {
                int out_col = 0;
                for (int c2 = 0; c2 < 4; ++c2) {
                    if (c2 != col) minor[r - 1][out_col++] = m[r][c2];
                }
            }
            const long long minor_det = det3(
                minor[0][0], minor[0][1], minor[0][2],
                minor[1][0], minor[1][1], minor[1][2],
                minor[2][0], minor[2][1], minor[2][2]);
            determinant += (col % 2 == 0 ? 1 : -1) * m[0][col] * minor_det;
        }
        return determinant == 0; // 共円または共線
    }

    void build_forbidden_quadruples() {
        for (int a = 0; a < vertex_count_; ++a)
            for (int b = a + 1; b < vertex_count_; ++b)
                for (int c = b + 1; c < vertex_count_; ++c)
                    for (int d = c + 1; d < vertex_count_; ++d) {
                        if (!is_forbidden_quadruple(a, b, c, d)) continue;
                        ++forbidden_count_;
                        const int ids[4] = {a, b, c, d};
                        for (int omitted = 0; omitted < 4; ++omitted) {
                            int triple[3]{};
                            int p = 0;
                            for (int j = 0; j < 4; ++j) {
                                if (j != omitted) triple[p++] = ids[j];
                            }
                            completion_[triple_index(triple[0], triple[1], triple[2])]
                                |= std::uint64_t{1} << ids[omitted];
                        }
                    }
    }

    std::pair<int, int> transform_point(int transform, int x, int y) const {
        if (transform >= 4) {
            x = n_ - 1 - x;
            transform -= 4;
        }
        for (int i = 0; i < transform; ++i) {
            const int next_x = y;
            const int next_y = n_ - 1 - x;
            x = next_x;
            y = next_y;
        }
        return {x, y};
    }

    void build_dihedral_transforms() {
        for (int t = 0; t < 8; ++t) {
            for (int v = 0; v < vertex_count_; ++v) {
                const auto [x, y] = transform_point(t, v % n_, v / n_);
                transformed_bit_[t][v] = std::uint64_t{1} << (y * n_ + x);
            }
        }
    }

    std::uint64_t transform_state(std::uint64_t state, int transform) const {
        std::uint64_t result = 0;
        while (state) {
            const int v = __builtin_ctzll(state);
            state &= state - 1;
            result |= transformed_bit_[transform][v];
        }
        return result;
    }

    std::uint64_t canonical(std::uint64_t state) const {
        std::uint64_t best = state;
        for (int t = 1; t < 8; ++t) {
            best = std::min(best, transform_state(state, t));
        }
        return best;
    }

    std::uint64_t banned_moves(std::uint64_t state) const {
        int vertices[64]{};
        int count = 0;
        for (std::uint64_t copy = state; copy; copy &= copy - 1) {
            vertices[count++] = __builtin_ctzll(copy);
        }

        std::uint64_t banned = 0;
        for (int i = 0; i < count - 2; ++i)
            for (int j = i + 1; j < count - 1; ++j)
                for (int k = j + 1; k < count; ++k) {
                    banned |= completion_[triple_index(vertices[i], vertices[j], vertices[k])];
                }
        return banned;
    }

    bool is_winning(std::uint64_t raw_state) {
        const std::uint64_t state = canonical(raw_state);
        const std::uint8_t cached = memo_.get(state);
        if (cached != FlatMemo::Empty) return cached == FlatMemo::Winning;
        ++visited_;

        std::uint64_t legal = full_mask_ & ~state & ~banned_moves(state);
        if (legal == 0) {
            memo_.put(state, FlatMemo::Losing);
            return false;
        }

        std::array<Child, 64> children{};
        int child_count = 0;
        while (legal) {
            const int v = __builtin_ctzll(legal);
            legal &= legal - 1;
            const std::uint64_t child = canonical(state | (std::uint64_t{1} << v));

            bool duplicate = false;
            for (int i = 0; i < child_count; ++i) {
                if (children[i].state == child) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate) continue;

            const std::uint64_t child_legal =
                full_mask_ & ~child & ~banned_moves(child);
            children[child_count++] = {
                child,
                static_cast<int>(__builtin_popcountll(child_legal))
            };
        }

        std::sort(children.begin(), children.begin() + child_count,
                  [](const Child& a, const Child& b) {
                      return a.legal_move_count < b.legal_move_count;
                  });

        for (int i = 0; i < child_count; ++i) {
            if (!is_winning(children[i].state)) {
                memo_.put(state, FlatMemo::Winning);
                return true;
            }
        }

        memo_.put(state, FlatMemo::Losing);
        return false;
    }
};

int main(int argc, char** argv) {
    try {
        const int n = argc >= 2 ? std::atoi(argv[1]) : 5;
        Solver solver(n);
        solver.run();
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
