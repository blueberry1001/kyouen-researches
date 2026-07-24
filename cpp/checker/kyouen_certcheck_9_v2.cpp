#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
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
static inline bool any(Bits a) { return a.lo || a.hi; }
static inline Bits bitof(int p) { return p < 64 ? Bits{1ULL << p, 0} : Bits{0, 1ULL << (p - 64)}; }
static inline bool has(Bits a, int p) {
    return p < 64 ? ((a.lo >> p) & 1U) != 0 : ((a.hi >> (p - 64)) & 1U) != 0;
}
static inline int takeLsb(Bits& a) {
    if (a.lo) {
        int p = std::countr_zero(a.lo);
        a.lo &= a.lo - 1;
        return p;
    }
    int p = std::countr_zero(a.hi);
    a.hi &= a.hi - 1;
    return p + 64;
}

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
    std::uint8_t outcome;
    std::uint8_t witness;
    std::uint8_t rank;
    std::uint8_t reserved;
};
#pragma pack(pop)
static_assert(sizeof(CertHeader) == 40);
static_assert(sizeof(CertNode) == 16);

class OutcomeTable {
public:
    explicit OutcomeTable(std::size_t nodeCount) {
        unsigned power = 1;
        while ((std::size_t{1} << power) < nodeCount * 2) ++power;
        const std::size_t size = std::size_t{1} << power;
        lows_.resize(size);
        metas_.resize(size);
        mask_ = size - 1;
        std::cerr << "outcome table slots=" << size << "\n";
    }

    void insert(Bits key, std::uint8_t outcome, std::uint8_t rank) {
        std::size_t i = hash(key) & mask_;
        const std::uint32_t meta = (static_cast<std::uint32_t>(key.hi) << 9) | (static_cast<std::uint32_t>(rank) << 2) | outcome;
        while (metas_[i]) {
            if (lows_[i] == key.lo && (metas_[i] >> 9) == key.hi) {
                throw std::runtime_error("duplicate certificate node");
            }
            i = (i + 1) & mask_;
        }
        lows_[i] = key.lo;
        metas_[i] = meta;
        ++used_;
    }

    std::pair<std::uint8_t, std::uint8_t> get(Bits key) const {
        std::size_t i = hash(key) & mask_;
        while (metas_[i]) {
            if (lows_[i] == key.lo && (metas_[i] >> 9) == key.hi) {
                return {static_cast<std::uint8_t>(metas_[i] & 3U), static_cast<std::uint8_t>((metas_[i] >> 2) & 0x7fU)};
            }
            i = (i + 1) & mask_;
        }
        return {0, 0};
    }

    std::size_t used() const { return used_; }

private:
    std::vector<std::uint64_t> lows_;
    std::vector<std::uint32_t> metas_;
    std::size_t mask_ = 0;
    std::size_t used_ = 0;

    static std::uint64_t mix64(std::uint64_t x) {
        x ^= x >> 30;
        x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27;
        x *= 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    static std::uint64_t hash(Bits b) {
        return mix64(b.lo ^ (b.hi * 0x9e3779b97f4a7c15ULL));
    }
};

class Checker {
    static constexpr int N = 9;
    static constexpr int V = 81;
    static constexpr std::uint64_t hiMask = (1ULL << 17) - 1;
public:
    explicit Checker(const std::string& path)
        : path_(path), completion_(std::size_t(V) * V * V) {
        buildTransformMap();
        buildForbidden();
    }

    void run() {
        const auto start = std::chrono::steady_clock::now();
        std::ifstream in(path_, std::ios::binary);
        if (!in) throw std::runtime_error("cannot open certificate");

        CertHeader header{};
        readExact(in, &header, sizeof(header));
        validateHeader(header);

        in.seekg(0, std::ios::end);
        const std::uint64_t actualSize = static_cast<std::uint64_t>(in.tellg());
        const std::uint64_t expectedSize = sizeof(CertHeader) + header.nodeCount * sizeof(CertNode);
        if (actualSize != expectedSize) throw std::runtime_error("certificate file size mismatch");
        in.seekg(sizeof(CertHeader));

        OutcomeTable table(header.nodeCount);
        std::vector<CertNode> nodes;
        nodes.resize(static_cast<std::size_t>(header.nodeCount));
        for (std::uint64_t i = 0; i < header.nodeCount; ++i) {
            readExact(in, &nodes[static_cast<std::size_t>(i)], sizeof(CertNode));
            const CertNode& node = nodes[static_cast<std::size_t>(i)];
            validateNodeEncoding(node);
            const Bits state{node.lo, node.hi};
            if (!(canonical(state) == state)) throw std::runtime_error("non-canonical state in certificate");
            table.insert(state, node.outcome, node.rank);
        }
        if (table.used() != header.nodeCount) throw std::runtime_error("table count mismatch");

        const Bits root{header.rootLo, header.rootHi};
        if (table.get(root).first != 1 || table.get(root).second != 80) throw std::runtime_error("root is not certified losing");

        std::uint64_t checked = 0;
        std::uint64_t losing = 0;
        std::uint64_t winning = 0;
        for (const CertNode& node : nodes) {
            const Bits state{node.lo, node.hi};
            const Bits legal = legalFromState(state);
            if (node.outcome == 2) {
                ++winning;
                if (node.witness >= V) throw std::runtime_error("winning node has invalid witness");
                if (!has(legal, node.witness)) throw std::runtime_error("winning witness is not legal");
                const Bits child = canonical(state | bitof(node.witness));
                if (table.get(child).first != 1 || table.get(child).second >= node.rank) throw std::runtime_error("winning witness does not lead to losing node");
            } else {
                ++losing;
                if (node.witness != 255) throw std::runtime_error("losing node has a witness byte");
                std::array<Bits, V> unique{};
                int uniqueCount = 0;
                Bits moves = legal;
                while (any(moves)) {
                    const int move = takeLsb(moves);
                    const Bits child = canonical(state | bitof(move));
                    bool duplicate = false;
                    for (int i = 0; i < uniqueCount; ++i) {
                        if (unique[i] == child) {
                            duplicate = true;
                            break;
                        }
                    }
                    if (duplicate) continue;
                    unique[uniqueCount++] = child;
                    if (table.get(child).first != 2 || table.get(child).second >= node.rank) {
                        throw std::runtime_error("losing node has a legal child not certified winning");
                    }
                }
            }
            ++checked;
            if ((checked & ((1ULL << 20) - 1)) == 0) {
                const double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                std::cerr << "checked=" << checked << '/' << header.nodeCount
                          << " rate=" << (checked / sec / 1e6) << " M nodes/s\n";
            }
        }

        const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        std::cout << "CERTIFICATE VALID\n"
                  << "nodes=" << header.nodeCount << " losing=" << losing << " winning=" << winning << "\n"
                  << "forbidden=" << forbiddenCount_ << " root=center-after-first-move\n"
                  << "conclusion=9x9 FIRST PLAYER WIN (center is a winning first move)\n"
                  << "seconds=" << seconds << "\n";
    }

private:
    std::string path_;
    std::vector<Bits> completion_;
    std::array<std::array<Bits, V>, 8> transformedBit_{};
    std::uint32_t forbiddenCount_ = 0;

    static void readExact(std::ifstream& in, void* data, std::size_t size) {
        in.read(reinterpret_cast<char*>(data), static_cast<std::streamsize>(size));
        if (!in) throw std::runtime_error("unexpected end of certificate");
    }

    void validateHeader(const CertHeader& h) const {
        if (std::memcmp(h.magic, "KYOENC2", 7) != 0 || h.magic[7] != '\0') {
            throw std::runtime_error("bad certificate magic");
        }
        if (h.version != 2 || h.boardSize != N) throw std::runtime_error("unsupported certificate version or board");
        if (h.forbiddenCount != forbiddenCount_) throw std::runtime_error("forbidden quadruple count mismatch");
        const Bits expectedRoot = canonical(bitof(40));
        if (!(Bits{h.rootLo, h.rootHi} == expectedRoot)) throw std::runtime_error("certificate root is not the center state");
        if (h.rootHi & ~hiMask) throw std::runtime_error("root has bits outside the board");
        if (h.nodeCount == 0) throw std::runtime_error("empty certificate");
    }

    static void validateNodeEncoding(const CertNode& n) {
        if (n.hi & ~hiMask) throw std::runtime_error("node has bits outside the board");
        if (n.outcome != 1 && n.outcome != 2) throw std::runtime_error("invalid node outcome");
        const unsigned stones = std::popcount(n.lo) + std::popcount(n.hi);
        if (n.rank != 81 - stones) throw std::runtime_error("rank does not match stone count");
        if (n.reserved != 0) throw std::runtime_error("reserved byte is nonzero");
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

    void buildForbidden() {
        for (int a = 0; a < V; ++a) {
            for (int b = a + 1; b < V; ++b) {
                for (int c = b + 1; c < V; ++c) {
                    for (int d = c + 1; d < V; ++d) {
                        if (!forbidden(a, b, c, d)) continue;
                        ++forbiddenCount_;
                        const int q[4] = {a, b, c, d};
                        for (int omit = 0; omit < 4; ++omit) {
                            int triple[3];
                            int k = 0;
                            for (int j = 0; j < 4; ++j) if (j != omit) triple[k++] = q[j];
                            completion_[idx(triple[0], triple[1], triple[2])] =
                                completion_[idx(triple[0], triple[1], triple[2])] | bitof(q[omit]);
                        }
                    }
                }
            }
        }
        std::cerr << "recomputed forbidden=" << forbiddenCount_ << "\n";
    }

    void buildTransformMap() {
        for (int p = 0; p < V; ++p) {
            const int x = p % N;
            const int y = p / N;
            for (int kind = 0; kind < 8; ++kind) {
                int nx = x, ny = y;
                switch (kind) {
                    case 0: break;
                    case 1: nx = N - 1 - x; break;
                    case 2: ny = N - 1 - y; break;
                    case 3: nx = N - 1 - x; ny = N - 1 - y; break;
                    case 4: nx = y; ny = x; break;
                    case 5: nx = N - 1 - y; ny = x; break;
                    case 6: nx = y; ny = N - 1 - x; break;
                    case 7: nx = N - 1 - y; ny = N - 1 - x; break;
                }
                transformedBit_[kind][p] = bitof(ny * N + nx);
            }
        }
    }

    Bits transform(Bits state, int kind) const {
        Bits out{};
        while (any(state)) {
            const int p = takeLsb(state);
            out = out | transformedBit_[kind][p];
        }
        return out;
    }

    Bits canonical(Bits state) const {
        Bits result = state;
        for (int kind = 1; kind < 8; ++kind) {
            const Bits candidate = transform(state, kind);
            if (candidate < result) result = candidate;
        }
        return result;
    }

    Bits legalFromState(Bits state) const {
        int vertices[V];
        int count = 0;
        Bits remaining = state;
        while (any(remaining)) vertices[count++] = takeLsb(remaining);

        Bits banned{};
        for (int i = 0; i < count; ++i) {
            for (int j = i + 1; j < count; ++j) {
                for (int k = j + 1; k < count; ++k) {
                    banned = banned | completion_[idx(vertices[i], vertices[j], vertices[k])];
                }
            }
        }
        Bits all{~0ULL, hiMask};
        Bits legal = all & ~state & ~banned;
        legal.hi &= hiMask;
        return legal;
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            std::cerr << "usage: kyouen_certcheck_9 CERTIFICATE\n";
            return 2;
        }
        Checker checker(argv[1]);
        checker.run();
    } catch (const std::exception& e) {
        std::cerr << "CERTIFICATE INVALID: " << e.what() << "\n";
        return 1;
    }
}
