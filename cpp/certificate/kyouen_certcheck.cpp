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
#include <utility>
#include <vector>

struct Bits {
    std::uint64_t lo = 0;
    std::uint64_t hi = 0;
};
static inline bool operator==(Bits a, Bits b) { return a.lo == b.lo && a.hi == b.hi; }
static inline bool operator<(Bits a, Bits b) { return a.hi < b.hi || (a.hi == b.hi && a.lo < b.lo); }
static inline Bits operator|(Bits a, Bits b) { return {a.lo | b.lo, a.hi | b.hi}; }
static inline Bits operator&(Bits a, Bits b) { return {a.lo & b.lo, a.hi & b.hi}; }
static inline Bits operator~(Bits a) { return {~a.lo, ~a.hi}; }
static inline bool any(Bits a) { return a.lo != 0 || a.hi != 0; }
static inline Bits bitof(int p) { return p < 64 ? Bits{1ULL << p, 0} : Bits{0, 1ULL << (p - 64)}; }
static inline bool has(Bits a, int p) { return p < 64 ? ((a.lo >> p) & 1U) : ((a.hi >> (p - 64)) & 1U); }
static inline int popcount(Bits a) { return std::popcount(a.lo) + std::popcount(a.hi); }
static inline int takeLsb(Bits& a) {
    if (a.lo) {
        const int p = std::countr_zero(a.lo);
        a.lo &= a.lo - 1;
        return p;
    }
    const int p = std::countr_zero(a.hi);
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
        const std::uint32_t meta = (static_cast<std::uint32_t>(key.hi) << 9)
                                 | (static_cast<std::uint32_t>(rank) << 2) | outcome;
        while (metas_[i]) {
            if (lows_[i] == key.lo && (metas_[i] >> 9) == key.hi)
                throw std::runtime_error("duplicate certificate node");
            i = (i + 1) & mask_;
        }
        lows_[i] = key.lo;
        metas_[i] = meta;
        ++used_;
    }

    std::pair<std::uint8_t, std::uint8_t> get(Bits key) const {
        std::size_t i = hash(key) & mask_;
        while (metas_[i]) {
            if (lows_[i] == key.lo && (metas_[i] >> 9) == key.hi)
                return {static_cast<std::uint8_t>(metas_[i] & 3U),
                        static_cast<std::uint8_t>((metas_[i] >> 2) & 0x7fU)};
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
public:
    explicit Checker(std::string path) : path_(std::move(path)) {}

    void run() {
        const auto start = Clock::now();
        std::ifstream in(path_, std::ios::binary);
        if (!in) throw std::runtime_error("cannot open certificate");
        CertHeader header{};
        readExact(in, &header, sizeof(header));
        validateHeader(header);
        n_ = static_cast<int>(header.boardSize);
        v_ = n_ * n_;
        hiMask_ = v_ <= 64 ? 0 : ((1ULL << (v_ - 64)) - 1);
        completion_.assign(std::size_t(v_) * v_ * v_, {});
        buildTransforms();
        buildForbidden();
        if (forbiddenCount_ != header.forbiddenCount)
            throw std::runtime_error("forbidden quadruple count mismatch");

        in.seekg(0, std::ios::end);
        const auto actualSize = static_cast<std::uint64_t>(in.tellg());
        const auto expectedSize = sizeof(CertHeader) + header.nodeCount * sizeof(CertNode);
        if (actualSize != expectedSize) throw std::runtime_error("certificate file size mismatch");
        in.seekg(sizeof(CertHeader));

        OutcomeTable table(header.nodeCount);
        std::vector<CertNode> nodes(static_cast<std::size_t>(header.nodeCount));
        for (auto& node : nodes) {
            readExact(in, &node, sizeof(node));
            validateNode(node);
            const Bits state{node.lo, node.hi};
            if (!(canonical(state) == state)) throw std::runtime_error("non-canonical state in certificate");
            const Bits banned = bannedFromState(state);
            if (any(banned & state)) throw std::runtime_error("certificate contains an illegal state");
            table.insert(state, node.outcome, node.rank);
        }
        if (table.used() != header.nodeCount) throw std::runtime_error("node count mismatch");

        const Bits root{header.rootLo, header.rootHi};
        if (!(root == Bits{})) throw std::runtime_error("classification certificate root must be the empty board");
        const auto rootEntry = table.get(root);
        if (rootEntry.first == 0) throw std::runtime_error("root not present in certificate");
        if (rootEntry.second != v_) throw std::runtime_error("root rank mismatch");

        std::uint64_t checked = 0, losing = 0, winning = 0;
        for (const CertNode& node : nodes) {
            const Bits state{node.lo, node.hi};
            const Bits legal = legalFromState(state);
            if (node.outcome == 2) {
                ++winning;
                if (node.witness >= v_) throw std::runtime_error("winning node has invalid witness");
                if (!has(legal, node.witness)) throw std::runtime_error("winning witness is not legal");
                const Bits child = canonical(state | bitof(node.witness));
                const auto childEntry = table.get(child);
                if (childEntry.first != 1 || childEntry.second >= node.rank)
                    throw std::runtime_error("winning witness does not lead to smaller-rank losing node");
            } else {
                ++losing;
                if (node.witness != 255) throw std::runtime_error("losing node carries a witness");
                std::array<Bits, 81> unique{};
                int uniqueCount = 0;
                Bits moves = legal;
                while (any(moves)) {
                    const int move = takeLsb(moves);
                    const Bits child = canonical(state | bitof(move));
                    bool duplicate = false;
                    for (int i = 0; i < uniqueCount; ++i) if (unique[i] == child) { duplicate = true; break; }
                    if (duplicate) continue;
                    unique[uniqueCount++] = child;
                    const auto childEntry = table.get(child);
                    if (childEntry.first != 2 || childEntry.second >= node.rank)
                        throw std::runtime_error("losing node has a legal child not certified winning at smaller rank");
                }
            }
            ++checked;
            if ((checked & ((1ULL << 20) - 1)) == 0) {
                const double sec = std::chrono::duration<double>(Clock::now() - start).count();
                std::cerr << "checked=" << checked << '/' << header.nodeCount
                          << " rate=" << checked / sec / 1e6 << " M nodes/s\n";
            }
        }

        const double seconds = std::chrono::duration<double>(Clock::now() - start).count();
        std::cout << "CERTIFICATE VALID\n"
                  << "board=" << n_ << 'x' << n_ << " nodes=" << header.nodeCount
                  << " losing=" << losing << " winning=" << winning << "\n"
                  << "forbidden=" << forbiddenCount_ << " root=empty\n"
                  << "conclusion=" << n_ << 'x' << n_ << ' '
                  << (rootEntry.first == 2 ? "FIRST PLAYER WIN" : "SECOND PLAYER WIN") << "\n"
                  << "seconds=" << seconds << "\n";
    }

private:
    using Clock = std::chrono::steady_clock;
    std::string path_;
    int n_ = 0;
    int v_ = 0;
    std::uint64_t hiMask_ = 0;
    std::vector<Bits> completion_;
    std::array<std::array<Bits, 81>, 8> transformedBit_{};
    std::uint32_t forbiddenCount_ = 0;

    static void readExact(std::ifstream& in, void* data, std::size_t size) {
        in.read(reinterpret_cast<char*>(data), static_cast<std::streamsize>(size));
        if (!in) throw std::runtime_error("unexpected end of certificate");
    }

    void validateHeader(const CertHeader& h) const {
        if (std::memcmp(h.magic, "KYOENC3", 7) != 0 || h.version != 3)
            throw std::runtime_error("unsupported certificate format");
        if (h.boardSize < 1 || h.boardSize > 9)
            throw std::runtime_error("board size outside 1..9");
        if (h.nodeCount == 0) throw std::runtime_error("empty certificate");
    }

    void validateNode(const CertNode& node) const {
        if (node.outcome != 1 && node.outcome != 2) throw std::runtime_error("invalid outcome byte");
        if (node.reserved != 0) throw std::runtime_error("nonzero reserved byte");
        if (v_ <= 64) {
            if (node.hi != 0) throw std::runtime_error("high bits used on <=8x8 board");
            if (v_ < 64 && (node.lo >> v_) != 0) throw std::runtime_error("bits outside board");
        } else if ((static_cast<std::uint64_t>(node.hi) & ~hiMask_) != 0) {
            throw std::runtime_error("high bits outside board");
        }
        const Bits state{node.lo, node.hi};
        if (node.rank != v_ - popcount(state)) throw std::runtime_error("rank is not remaining board points");
        if (node.outcome == 1 && node.witness != 255) throw std::runtime_error("losing node witness must be 255");
    }

    std::size_t idx(int a, int b, int c) const {
        return (std::size_t(a) * v_ + b) * v_ + c;
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
                for (int c2 = 0; c2 < 4; ++c2) if (c2 != col) z[r - 1][q++] = m[r][c2];
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
                            int t[3], p = 0;
                            for (int j = 0; j < 4; ++j) if (j != omit) t[p++] = q[j];
                            completion_[idx(t[0], t[1], t[2])] =
                                completion_[idx(t[0], t[1], t[2])] | bitof(q[omit]);
                        }
                    }
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
        for (int kind = 0; kind < 8; ++kind)
            for (int p = 0; p < v_; ++p) {
                auto [nx, ny] = transformPoint(kind, p % n_, p / n_);
                transformedBit_[kind][p] = bitof(ny * n_ + nx);
            }
    }

    Bits transform(Bits state, int kind) const {
        Bits out{};
        while (any(state)) out = out | transformedBit_[kind][takeLsb(state)];
        return out;
    }

    Bits canonical(Bits state) const {
        Bits best = state;
        for (int kind = 1; kind < 8; ++kind) {
            const Bits t = transform(state, kind);
            if (t < best) best = t;
        }
        return best;
    }

    Bits bannedFromState(Bits state) const {
        int verts[81];
        int count = 0;
        Bits copy = state;
        while (any(copy)) verts[count++] = takeLsb(copy);
        Bits banned{};
        for (int i = 0; i < count; ++i)
            for (int j = i + 1; j < count; ++j)
                for (int k = j + 1; k < count; ++k)
                    banned = banned | completion_[idx(verts[i], verts[j], verts[k])];
        return banned;
    }

    Bits legalFromState(Bits state) const {
        Bits all{~0ULL, hiMask_};
        if (v_ < 64) all.lo = (1ULL << v_) - 1;
        Bits legal = all & ~state & ~bannedFromState(state);
        legal.hi &= hiMask_;
        return legal;
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            std::cerr << "usage: kyouen-certcheck CERTIFICATE.cert\n";
            return 2;
        }
        Checker(argv[1]).run();
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
