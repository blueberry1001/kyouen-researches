#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#pragma pack(push, 1)
struct CertHeader {
    char magic[8];
    std::uint32_t version;
    std::uint32_t boardSize;
    std::uint64_t nodeCount;
    std::uint64_t rootLo;
    std::uint32_t rootHi;
    std::uint32_t forbiddenCount;
};
struct CertNode {
    std::uint64_t lo;
    std::uint32_t hi;
    std::uint8_t outcome; // 1 losing, 2 winning
    std::uint8_t witness; // board index for winning, 255 for losing
    std::uint8_t rank;    // V - number of stones
    std::uint8_t reserved;
};
#pragma pack(pop)
static_assert(sizeof(CertHeader) == 40);
static_assert(sizeof(CertNode) == 16);

class FlatMemo {
public:
    enum : std::uint8_t { Empty = 0, Losing = 1, Winning = 2, Visited = 0x80 };

    explicit FlatMemo(unsigned power)
        : keys_(std::size_t{1} << power),
          values_(std::size_t{1} << power, Empty),
          mask_((std::size_t{1} << power) - 1) {}

    std::uint8_t get(std::uint64_t key) const {
        std::size_t i = mix(key) & mask_;
        while ((values_[i] & 3U) != Empty) {
            if (keys_[i] == key) return values_[i] & 3U;
            i = (i + 1) & mask_;
        }
        return Empty;
    }

    void put(std::uint64_t key, std::uint8_t outcome) {
        std::size_t i = mix(key) & mask_;
        while ((values_[i] & 3U) != Empty) {
            if (keys_[i] == key) {
                values_[i] = (values_[i] & Visited) | outcome;
                return;
            }
            i = (i + 1) & mask_;
        }
        keys_[i] = key;
        values_[i] = outcome;
        ++used_;
        if (used_ * 10 > values_.size() * 8) {
            throw std::runtime_error("memo table over 80%; increase --memo-power");
        }
    }

    bool markCertificateVisited(std::uint64_t key) {
        std::size_t i = mix(key) & mask_;
        while ((values_[i] & 3U) != Empty) {
            if (keys_[i] == key) {
                if ((values_[i] & Visited) != 0) return false;
                values_[i] |= Visited;
                return true;
            }
            i = (i + 1) & mask_;
        }
        throw std::runtime_error("certificate traversal reached an unknown memo state");
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

class Generator {
    using Clock = std::chrono::steady_clock;
    struct Child {
        std::uint64_t state;
        std::uint64_t legal;
        std::uint64_t key;
        int legalCount;
        std::uint8_t cached;
    };

public:
    Generator(int n, unsigned memoPower)
        : n_(n), v_(n * n),
          full_(v_ == 64 ? ~std::uint64_t{0} : ((std::uint64_t{1} << v_) - 1)),
          completion_(std::size_t(v_) * v_ * v_), memo_(memoPower), start_(Clock::now()) {
        if (n_ < 1 || n_ > 8) throw std::invalid_argument("board size must be 1..8");
        buildTransforms();
        buildForbidden();
    }

    void run(const std::string& output) {
        const bool rootWinning = win(0, full_, 0);
        std::cerr << "search complete: n=" << n_
                  << " verdict=" << (rootWinning ? "FIRST" : "SECOND")
                  << " forbidden=" << forbiddenCount_
                  << " states=" << visited_
                  << " maxdepth=" << maxDepth_
                  << " seconds=" << elapsed() << "\n";
        writeCertificate(output);
    }

private:
    int n_;
    int v_;
    std::uint64_t full_;
    std::vector<std::uint64_t> completion_;
    std::array<std::array<std::uint64_t, 64>, 8> transformedBit_{};
    FlatMemo memo_;
    std::uint64_t forbiddenCount_ = 0;
    std::uint64_t visited_ = 0;
    int maxDepth_ = 0;
    Clock::time_point start_;

    double elapsed() const {
        return std::chrono::duration<double>(Clock::now() - start_).count();
    }

    static unsigned defaultMemoPower(int n) {
        if (n <= 4) return 16;
        if (n == 5) return 19;
        if (n == 6) return 21;
        if (n == 7) return 24;
        return 27;
    }

public:
    static unsigned memoPowerFor(int n) { return defaultMemoPower(n); }

private:
    std::size_t idx(int a, int b, int c) const {
        return (std::size_t(a) * v_ + b) * v_ + c;
    }

    static void sort3(int& a, int& b, int& c) {
        if (a > b) std::swap(a, b);
        if (b > c) std::swap(b, c);
        if (a > b) std::swap(a, b);
    }

    static long long det3(
        long long a00, long long a01, long long a02,
        long long a10, long long a11, long long a12,
        long long a20, long long a21, long long a22) {
        return a00 * (a11 * a22 - a12 * a21)
             - a01 * (a10 * a22 - a12 * a20)
             + a02 * (a10 * a21 - a11 * a20);
    }

    bool forbidden(int a, int b, int c, int d) const {
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
            long long z[3][3]{};
            for (int r = 1; r < 4; ++r) {
                int q = 0;
                for (int c2 = 0; c2 < 4; ++c2) {
                    if (c2 != col) z[r - 1][q++] = m[r][c2];
                }
            }
            const long long md = det3(
                z[0][0], z[0][1], z[0][2],
                z[1][0], z[1][1], z[1][2],
                z[2][0], z[2][1], z[2][2]);
            determinant += (col % 2 == 0 ? 1 : -1) * m[0][col] * md;
        }
        return determinant == 0;
    }

    void buildForbidden() {
        for (int a = 0; a < v_; ++a)
            for (int b = a + 1; b < v_; ++b)
                for (int c = b + 1; c < v_; ++c)
                    for (int d = c + 1; d < v_; ++d) {
                        if (!forbidden(a, b, c, d)) continue;
                        ++forbiddenCount_;
                        const int q[4] = {a, b, c, d};
                        for (int omit = 0; omit < 4; ++omit) {
                            int t[3];
                            int p = 0;
                            for (int j = 0; j < 4; ++j) if (j != omit) t[p++] = q[j];
                            completion_[idx(t[0], t[1], t[2])] |= std::uint64_t{1} << q[omit];
                        }
                    }
        std::cerr << "built forbidden=" << forbiddenCount_ << "\n";
    }

    std::pair<int, int> transformPoint(int kind, int x, int y) const {
        switch (kind) {
            case 0: return {x, y};
            case 1: return {n_ - 1 - x, y};
            case 2: return {x, n_ - 1 - y};
            case 3: return {n_ - 1 - x, n_ - 1 - y};
            case 4: return {y, x};
            case 5: return {n_ - 1 - y, x};
            case 6: return {y, n_ - 1 - x};
            default: return {n_ - 1 - y, n_ - 1 - x};
        }
    }

    void buildTransforms() {
        for (int kind = 0; kind < 8; ++kind) {
            for (int p = 0; p < v_; ++p) {
                auto [nx, ny] = transformPoint(kind, p % n_, p / n_);
                transformedBit_[kind][p] = std::uint64_t{1} << (ny * n_ + nx);
            }
        }
    }

    std::uint64_t transform(std::uint64_t state, int kind) const {
        std::uint64_t out = 0;
        while (state) {
            const int p = std::countr_zero(state);
            state &= state - 1;
            out |= transformedBit_[kind][p];
        }
        return out;
    }

    static std::uint64_t flipH8(std::uint64_t x) {
        x = ((x >> 1) & 0x5555555555555555ULL) | ((x & 0x5555555555555555ULL) << 1);
        x = ((x >> 2) & 0x3333333333333333ULL) | ((x & 0x3333333333333333ULL) << 2);
        x = ((x >> 4) & 0x0f0f0f0f0f0f0f0fULL) | ((x & 0x0f0f0f0f0f0f0f0fULL) << 4);
        return x;
    }

    static std::uint64_t flipV8(std::uint64_t x) {
#if defined(_MSC_VER)
        return _byteswap_uint64(x);
#else
        return __builtin_bswap64(x);
#endif
    }

    static std::uint64_t transpose8(std::uint64_t x) {
        std::uint64_t t;
        t = (x ^ (x << 7)) & 0x5500550055005500ULL; x ^= t ^ (t >> 7);
        t = (x ^ (x << 14)) & 0x3333000033330000ULL; x ^= t ^ (t >> 14);
        t = (x ^ (x << 28)) & 0x0f0f0f0f00000000ULL; x ^= t ^ (t >> 28);
        return x;
    }

    std::uint64_t canonical(std::uint64_t state) const {
        if (n_ == 8) {
            const std::uint64_t h = flipH8(state);
            const std::uint64_t v = flipV8(state);
            const std::uint64_t hv = flipV8(h);
            const std::uint64_t t = transpose8(state);
            const std::uint64_t th = flipH8(t);
            const std::uint64_t tv = flipV8(t);
            const std::uint64_t thv = flipV8(th);
            return std::min({state, h, v, hv, t, th, tv, thv});
        }
        std::uint64_t best = state;
        for (int kind = 1; kind < 8; ++kind) best = std::min(best, transform(state, kind));
        return best;
    }

    std::uint64_t addedBans(std::uint64_t state, int v) const {
        int verts[64];
        int count = 0;
        for (auto copy = state; copy; copy &= copy - 1) verts[count++] = std::countr_zero(copy);
        std::uint64_t out = 0;
        for (int i = 0; i < count; ++i)
            for (int j = i + 1; j < count; ++j) {
                int a = verts[i], b = verts[j], c = v;
                sort3(a, b, c);
                out |= completion_[idx(a, b, c)];
            }
        return out;
    }

    std::uint64_t legalFromState(std::uint64_t state) const {
        int verts[64];
        int count = 0;
        for (auto copy = state; copy; copy &= copy - 1) verts[count++] = std::countr_zero(copy);
        std::uint64_t banned = 0;
        for (int i = 0; i < count; ++i)
            for (int j = i + 1; j < count; ++j)
                for (int k = j + 1; k < count; ++k)
                    banned |= completion_[idx(verts[i], verts[j], verts[k])];
        return full_ & ~state & ~banned;
    }

    bool win(std::uint64_t state, std::uint64_t legal, int depth) {
        const std::uint64_t key = canonical(state);
        const auto cached = memo_.get(key);
        if (cached) return cached == FlatMemo::Winning;

        ++visited_;
        maxDepth_ = std::max(maxDepth_, depth);
        if ((visited_ & ((1ULL << 22) - 1)) == 0) {
            std::cerr << "states=" << visited_ << " memo=" << memo_.used()
                      << " depth=" << depth << " rate=" << (visited_ / elapsed() / 1e6) << " M/s\n";
        }

        if (!legal) {
            memo_.put(key, FlatMemo::Losing);
            return false;
        }

        std::array<Child, 64> children{};
        int childCount = 0;
        auto moves = legal;
        while (moves) {
            const int move = std::countr_zero(moves);
            moves &= moves - 1;
            const auto bit = std::uint64_t{1} << move;
            const auto nextState = state | bit;
            const auto nextLegal = (legal & ~bit) & ~addedBans(state, move);
            const auto nextKey = canonical(nextState);
            bool duplicate = false;
            for (int i = 0; i < childCount; ++i) if (children[i].key == nextKey) { duplicate = true; break; }
            if (duplicate) continue;
            children[childCount++] = {
                nextState, nextLegal, nextKey, std::popcount(nextLegal), memo_.get(nextKey)
            };
        }

        std::sort(children.begin(), children.begin() + childCount, [](const Child& a, const Child& b) {
            const int pa = a.cached == FlatMemo::Losing ? 0 : (a.cached == 0 ? 1 : 2);
            const int pb = b.cached == FlatMemo::Losing ? 0 : (b.cached == 0 ? 1 : 2);
            if (pa != pb) return pa < pb;
            if (a.legalCount != b.legalCount) return a.legalCount < b.legalCount;
            return a.key < b.key;
        });

        for (int i = 0; i < childCount; ++i) {
            const bool childWinning = children[i].cached
                ? children[i].cached == FlatMemo::Winning
                : win(children[i].state, children[i].legal, depth + 1);
            if (!childWinning) {
                memo_.put(key, FlatMemo::Winning);
                return true;
            }
        }
        memo_.put(key, FlatMemo::Losing);
        return false;
    }

    void writeCertificate(const std::string& path) {
        std::fstream out(path, std::ios::binary | std::ios::out | std::ios::trunc);
        if (!out) throw std::runtime_error("cannot open output certificate");

        CertHeader header{};
        std::memcpy(header.magic, "KYOENC3", 7);
        header.version = 3;
        header.boardSize = static_cast<std::uint32_t>(n_);
        header.rootLo = 0;
        header.rootHi = 0;
        header.forbiddenCount = static_cast<std::uint32_t>(forbiddenCount_);
        out.write(reinterpret_cast<const char*>(&header), sizeof(header));

        std::vector<std::uint64_t> stack;
        stack.reserve(1 << 20);
        stack.push_back(0);
        std::uint64_t count = 0, losingCount = 0, winningCount = 0;
        const auto certStart = Clock::now();

        while (!stack.empty()) {
            auto state = canonical(stack.back());
            stack.pop_back();
            if (!memo_.markCertificateVisited(state)) continue;
            const auto outcome = memo_.get(state);
            if (outcome != FlatMemo::Losing && outcome != FlatMemo::Winning)
                throw std::runtime_error("invalid memo outcome during certificate traversal");

            const auto legal = legalFromState(state);
            std::uint8_t witness = 255;
            if (outcome == FlatMemo::Winning) {
                ++winningCount;
                auto moves = legal;
                bool found = false;
                while (moves) {
                    const int move = std::countr_zero(moves);
                    moves &= moves - 1;
                    const auto child = canonical(state | (std::uint64_t{1} << move));
                    if (memo_.get(child) == FlatMemo::Losing) {
                        witness = static_cast<std::uint8_t>(move);
                        stack.push_back(child);
                        found = true;
                        break;
                    }
                }
                if (!found) throw std::runtime_error("winning state has no losing witness child");
            } else {
                ++losingCount;
                std::array<std::uint64_t, 64> unique{};
                int uniqueCount = 0;
                auto moves = legal;
                while (moves) {
                    const int move = std::countr_zero(moves);
                    moves &= moves - 1;
                    const auto child = canonical(state | (std::uint64_t{1} << move));
                    bool duplicate = false;
                    for (int i = 0; i < uniqueCount; ++i) if (unique[i] == child) { duplicate = true; break; }
                    if (duplicate) continue;
                    if (memo_.get(child) != FlatMemo::Winning)
                        throw std::runtime_error("losing state has a child not memoized winning");
                    unique[uniqueCount++] = child;
                }
                for (int i = 0; i < uniqueCount; ++i) stack.push_back(unique[i]);
            }

            CertNode node{
                state, 0,
                outcome, witness,
                static_cast<std::uint8_t>(v_ - std::popcount(state)),
                0
            };
            out.write(reinterpret_cast<const char*>(&node), sizeof(node));
            if (!out) throw std::runtime_error("failed writing certificate node");
            ++count;
            if ((count & ((1ULL << 20) - 1)) == 0) {
                const double sec = std::chrono::duration<double>(Clock::now() - certStart).count();
                std::cerr << "certificate nodes=" << count << " stack=" << stack.size()
                          << " rate=" << (count / sec / 1e6) << " M/s\n";
            }
        }

        header.nodeCount = count;
        out.seekp(0);
        out.write(reinterpret_cast<const char*>(&header), sizeof(header));
        out.close();
        const double seconds = std::chrono::duration<double>(Clock::now() - certStart).count();
        std::cerr << "certificate complete: nodes=" << count
                  << " losing=" << losingCount << " winning=" << winningCount
                  << " bytes=" << (sizeof(header) + count * sizeof(CertNode))
                  << " seconds=" << seconds << "\n";
    }
};

int main(int argc, char** argv) {
    try {
        if (argc < 3) {
            std::cerr << "usage: kyouen-certgen-1-to-8 N OUTPUT.cert [MEMO_POWER]\n";
            return 2;
        }
        const int n = std::atoi(argv[1]);
        const unsigned power = argc >= 4 ? static_cast<unsigned>(std::atoi(argv[3]))
                                          : Generator::memoPowerFor(n);
        Generator generator(n, power);
        generator.run(argv[2]);
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
