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

struct Bits {
    std::uint64_t lo = 0;
    std::uint64_t hi = 0; // only bits 0..16 are used
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
    return p < 64 ? Bits{1ULL << p, 0} : Bits{0, 1ULL << (p - 64)};
}
static inline bool has(Bits a, int p) {
    return p < 64 ? ((a.lo >> p) & 1U) != 0 : ((a.hi >> (p - 64)) & 1U) != 0;
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
            const std::uint32_t m = metas_[i];
            if (lows_[i] == key.lo && keyHi(m) == key.hi) {
                return m & valueMask;
            }
            i = (i + 1) & mask_;
        }
        return 0;
    }

    void put(Bits key, std::uint32_t value) {
        std::size_t i = mix(key) & mask_;
        const std::uint32_t meta = (std::uint32_t(key.hi) << 2) | value;
        while (metas_[i]) {
            if (lows_[i] == key.lo && keyHi(metas_[i]) == key.hi) {
                const std::uint32_t certFlag = metas_[i] & visitedFlag;
                metas_[i] = meta | certFlag;
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

    // Returns true exactly once for each stored key.
    bool markCertificateVisited(Bits key) {
        std::size_t i = mix(key) & mask_;
        while (metas_[i]) {
            if (lows_[i] == key.lo && keyHi(metas_[i]) == key.hi) {
                if (metas_[i] & visitedFlag) return false;
                metas_[i] |= visitedFlag;
                return true;
            }
            i = (i + 1) & mask_;
        }
        throw std::runtime_error("certificate traversal reached an unknown memo key");
    }

    std::size_t used() const { return used_; }

private:
    static constexpr std::uint32_t valueMask = 3U;
    static constexpr std::uint32_t hiMask = (1U << 17) - 1U;
    static constexpr std::uint32_t visitedFlag = 1U << 31;

    std::vector<std::uint64_t> lows_;
    std::vector<std::uint32_t> metas_;
    std::size_t mask_;
    std::size_t used_ = 0;

    static std::uint32_t keyHi(std::uint32_t meta) {
        return (meta >> 2) & hiMask;
    }
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

#pragma pack(push, 1)
struct CertHeader {
    char magic[8];                 // "KYOENC1\0"
    std::uint32_t version;         // 1
    std::uint32_t boardSize;       // 9
    std::uint64_t nodeCount;
    std::uint64_t rootLo;
    std::uint32_t rootHi;
    std::uint32_t forbiddenCount;
};

struct CertNode {
    std::uint64_t lo;
    std::uint32_t hi;
    std::uint8_t outcome;          // 1 = losing, 2 = winning
    std::uint8_t witness;          // 0..80 for winning, 255 for losing
    std::uint16_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(CertHeader) == 40);
static_assert(sizeof(CertNode) == 16);

class Solver9Certificate {
    static constexpr int N = 9;
    static constexpr int V = 81;
    static constexpr std::uint64_t hiMask = (1ULL << 17) - 1;
    using Clock = std::chrono::steady_clock;

    struct TState { std::array<Bits, 8> t{}; };
    struct Child {
        TState ts;
        Bits legal;
        Bits key;
        int count;
        int move;
        std::uint32_t cached;
    };

public:
    explicit Solver9Certificate(unsigned memoPower = 28)
        : completion_(std::size_t(V) * V * V),
          memo_(memoPower),
          start_(Clock::now()) {
        buildMaps();
        buildForbiddenQuadruples();
    }

    void run(const std::string& certificatePath) {
        constexpr int center = 40;
        TState root{};
        TState afterCenter = add(root, center);
        Bits legal{~0ULL, hiMask};
        legal = legal & ~bitof(center);

        const bool result = win(afterCenter, legal, 1);
        if (result) {
            throw std::runtime_error("unexpected result: player after center is winning");
        }

        const double solveSeconds = elapsedSeconds();
        std::cerr << "solved center: LOSS, states=" << visited_
                  << " memo=" << memo_.used()
                  << " maxdepth=" << maxDepth_
                  << " seconds=" << solveSeconds << "\n";

        writeCertificate(canonical(afterCenter), certificatePath);
    }

private:
    std::vector<Bits> completion_;
    std::array<std::array<Bits, V>, 8> transformedBit_{};
    FlatMemo81 memo_;
    std::uint64_t forbiddenCount_ = 0;
    std::uint64_t visited_ = 0;
    int maxDepth_ = 0;
    Clock::time_point start_;

    double elapsedSeconds() const {
        return std::chrono::duration<double>(Clock::now() - start_).count();
    }

    static long long det3(
        long long a00, long long a01, long long a02,
        long long a10, long long a11, long long a12,
        long long a20, long long a21, long long a22) {
        return a00 * (a11 * a22 - a12 * a21)
             - a01 * (a10 * a22 - a12 * a20)
             + a02 * (a10 * a21 - a11 * a20);
    }

    static bool forbidden(int a, int b, int c, int d) {
        const int ids[4] = {a, b, c, d};
        long long m[4][4]{};
        for (int r = 0; r < 4; ++r) {
            const long long x = ids[r] % N;
            const long long y = ids[r] / N;
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

    static constexpr std::size_t idx(int a, int b, int c) {
        return (std::size_t(a) * V + b) * V + c;
    }

    static void sort3(int& a, int& b, int& c) {
        if (a > b) std::swap(a, b);
        if (b > c) std::swap(b, c);
        if (a > b) std::swap(a, b);
    }

    void buildMaps() {
        for (int p = 0; p < V; ++p) {
            const int x = p % N;
            const int y = p / N;
            const int nx[8] = {x, N - 1 - x, x, N - 1 - x, y, N - 1 - y, y, N - 1 - y};
            const int ny[8] = {y, y, N - 1 - y, N - 1 - y, x, x, N - 1 - x, N - 1 - x};
            for (int k = 0; k < 8; ++k) {
                transformedBit_[k][p] = bitof(ny[k] * N + nx[k]);
            }
        }
    }

    void buildForbiddenQuadruples() {
        for (int a = 0; a < V; ++a) {
            for (int b = a + 1; b < V; ++b) {
                for (int c = b + 1; c < V; ++c) {
                    for (int d = c + 1; d < V; ++d) {
                        if (!forbidden(a, b, c, d)) continue;
                        ++forbiddenCount_;
                        const int q[4] = {a, b, c, d};
                        for (int omit = 0; omit < 4; ++omit) {
                            int t[3];
                            int p = 0;
                            for (int j = 0; j < 4; ++j) {
                                if (j != omit) t[p++] = q[j];
                            }
                            completion_[idx(t[0], t[1], t[2])] =
                                completion_[idx(t[0], t[1], t[2])] | bitof(q[omit]);
                        }
                    }
                }
            }
        }
        std::cerr << "built forbidden=" << forbiddenCount_ << "\n";
    }

    TState add(const TState& s, int v) const {
        TState r = s;
        for (int k = 0; k < 8; ++k) r.t[k] = r.t[k] | transformedBit_[k][v];
        return r;
    }

    static Bits canonical(const TState& s) {
        Bits r = s.t[0];
        for (int k = 1; k < 8; ++k) if (s.t[k] < r) r = s.t[k];
        return r;
    }

    Bits transform(Bits s, int kind) const {
        Bits out{};
        while (any(s)) {
            const int p = take_lsb(s);
            out = out | transformedBit_[kind][p];
        }
        return out;
    }

    Bits canonical(Bits s) const {
        Bits r = s;
        for (int k = 1; k < 8; ++k) {
            Bits t = transform(s, k);
            if (t < r) r = t;
        }
        return r;
    }

    Bits addedBans(Bits state, int v) const {
        int verts[V];
        int k = 0;
        Bits s = state;
        while (any(s)) verts[k++] = take_lsb(s);
        Bits out{};
        for (int i = 0; i < k; ++i) {
            for (int j = i + 1; j < k; ++j) {
                int a = verts[i], b = verts[j], c = v;
                sort3(a, b, c);
                out = out | completion_[idx(a, b, c)];
            }
        }
        return out;
    }

    Bits legalFromState(Bits state) const {
        int verts[V];
        int k = 0;
        Bits s = state;
        while (any(s)) verts[k++] = take_lsb(s);

        Bits banned{};
        for (int i = 0; i < k; ++i) {
            for (int j = i + 1; j < k; ++j) {
                for (int l = j + 1; l < k; ++l) {
                    banned = banned | completion_[idx(verts[i], verts[j], verts[l])];
                }
            }
        }
        Bits all{~0ULL, hiMask};
        Bits legal = all & ~state & ~banned;
        legal.hi &= hiMask;
        return legal;
    }

    bool win(const TState& state, Bits legal, int depth) {
        const Bits key = canonical(state);
        const auto cached = memo_.get(key);
        if (cached) return cached == FlatMemo81::Winning;

        ++visited_;
        if (depth > maxDepth_) {
            maxDepth_ = depth;
            std::cerr << "depth " << depth << " at " << visited_ << " states\n";
        }
        if ((visited_ & ((1ULL << 22) - 1)) == 0) {
            std::cerr << "states=" << visited_
                      << " memo=" << memo_.used()
                      << " depth=" << depth
                      << " rate=" << (visited_ / elapsedSeconds() / 1e6) << " M/s\n";
        }

        if (!any(legal)) {
            memo_.put(key, FlatMemo81::Losing);
            return false;
        }

        std::array<Child, V> children{};
        int n = 0;
        Bits moves = legal;
        while (any(moves)) {
            const int v = take_lsb(moves);
            const Bits bit = bitof(v);
            const TState ns = add(state, v);
            Bits nl = (legal & ~bit) & ~addedBans(state.t[0], v);
            nl.hi &= hiMask;
            const Bits nk = canonical(ns);

            bool duplicate = false;
            for (int i = 0; i < n; ++i) {
                if (children[i].key == nk) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate) continue;

            const auto cv = memo_.get(nk);
            children[n++] = {ns, nl, nk, popcount(nl), v, cv};
        }

        std::sort(children.begin(), children.begin() + n, [](const Child& a, const Child& b) {
            const int pa = a.cached == FlatMemo81::Losing ? 0 : (a.cached == 0 ? 1 : 2);
            const int pb = b.cached == FlatMemo81::Losing ? 0 : (b.cached == 0 ? 1 : 2);
            if (pa != pb) return pa < pb;
            if (a.count != b.count) return a.count < b.count;
            return a.key < b.key;
        });

        for (int i = 0; i < n; ++i) {
            const bool childWin = children[i].cached
                ? children[i].cached == FlatMemo81::Winning
                : win(children[i].ts, children[i].legal, depth + 1);
            if (!childWin) {
                memo_.put(key, FlatMemo81::Winning);
                return true;
            }
        }

        memo_.put(key, FlatMemo81::Losing);
        return false;
    }

    void writeCertificate(Bits root, const std::string& path) {
        std::fstream out(path, std::ios::binary | std::ios::out | std::ios::trunc);
        if (!out) throw std::runtime_error("cannot open certificate output: " + path);

        CertHeader header{};
        std::memcpy(header.magic, "KYOENC1", 7);
        header.version = 1;
        header.boardSize = N;
        header.nodeCount = 0;
        header.rootLo = root.lo;
        header.rootHi = static_cast<std::uint32_t>(root.hi);
        header.forbiddenCount = static_cast<std::uint32_t>(forbiddenCount_);
        out.write(reinterpret_cast<const char*>(&header), sizeof(header));

        std::vector<Bits> stack;
        stack.reserve(1 << 20);
        stack.push_back(root);
        std::uint64_t count = 0;
        std::uint64_t losingCount = 0;
        std::uint64_t winningCount = 0;
        auto certStart = Clock::now();

        while (!stack.empty()) {
            Bits state = stack.back();
            stack.pop_back();
            state = canonical(state);
            if (!memo_.markCertificateVisited(state)) continue;

            const std::uint32_t outcome = memo_.get(state);
            if (outcome != FlatMemo81::Losing && outcome != FlatMemo81::Winning) {
                throw std::runtime_error("invalid memo outcome during certificate traversal");
            }

            const Bits legal = legalFromState(state);
            std::uint8_t witness = 255;

            if (outcome == FlatMemo81::Winning) {
                ++winningCount;
                Bits moves = legal;
                bool found = false;
                while (any(moves)) {
                    const int v = take_lsb(moves);
                    const Bits child = canonical(state | bitof(v));
                    if (memo_.get(child) == FlatMemo81::Losing) {
                        witness = static_cast<std::uint8_t>(v);
                        stack.push_back(child);
                        found = true;
                        break;
                    }
                }
                if (!found) throw std::runtime_error("winning memo node has no losing witness child");
            } else {
                ++losingCount;
                std::array<Bits, V> unique{};
                int uniqueCount = 0;
                Bits moves = legal;
                while (any(moves)) {
                    const int v = take_lsb(moves);
                    const Bits child = canonical(state | bitof(v));
                    bool duplicate = false;
                    for (int i = 0; i < uniqueCount; ++i) {
                        if (unique[i] == child) {
                            duplicate = true;
                            break;
                        }
                    }
                    if (duplicate) continue;
                    if (memo_.get(child) != FlatMemo81::Winning) {
                        throw std::runtime_error("losing memo node has a non-winning legal child");
                    }
                    unique[uniqueCount++] = child;
                }
                for (int i = 0; i < uniqueCount; ++i) stack.push_back(unique[i]);
            }

            const CertNode node{
                state.lo,
                static_cast<std::uint32_t>(state.hi),
                static_cast<std::uint8_t>(outcome),
                witness,
                0
            };
            out.write(reinterpret_cast<const char*>(&node), sizeof(node));
            if (!out) throw std::runtime_error("failed while writing certificate");

            ++count;
            if ((count & ((1ULL << 20) - 1)) == 0) {
                const double seconds = std::chrono::duration<double>(Clock::now() - certStart).count();
                std::cerr << "certificate nodes=" << count
                          << " stack=" << stack.size()
                          << " rate=" << (count / seconds / 1e6) << " M/s\n";
            }
        }

        header.nodeCount = count;
        out.seekp(0);
        out.write(reinterpret_cast<const char*>(&header), sizeof(header));
        out.close();

        const double certSeconds = std::chrono::duration<double>(Clock::now() - certStart).count();
        std::cerr << "certificate complete: nodes=" << count
                  << " losing=" << losingCount
                  << " winning=" << winningCount
                  << " bytes=" << (sizeof(header) + count * sizeof(CertNode))
                  << " seconds=" << certSeconds << "\n";
    }
};

int main(int argc, char** argv) {
    try {
        const std::string path = argc >= 2 ? argv[1] : "kyouen9.cert";
        const unsigned power = argc >= 3 ? static_cast<unsigned>(std::atoi(argv[2])) : 28;
        Solver9Certificate solver(power);
        solver.run(path);
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
