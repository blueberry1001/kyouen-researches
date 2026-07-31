#include <algorithm>
#include <array>
#include <bit>
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

static bool operator==(Bits a, Bits b) { return a.lo == b.lo && a.hi == b.hi; }
static bool operator<(Bits a, Bits b) {
    return a.hi < b.hi || (a.hi == b.hi && a.lo < b.lo);
}
static Bits operator|(Bits a, Bits b) { return {a.lo | b.lo, a.hi | b.hi}; }
static Bits operator&(Bits a, Bits b) { return {a.lo & b.lo, a.hi & b.hi}; }
static Bits operator~(Bits a) { return {~a.lo, ~a.hi}; }
static bool any(Bits a) { return a.lo != 0 || a.hi != 0; }
static Bits bitof(int p) {
    return p < 64 ? Bits{std::uint64_t{1} << p, 0}
                  : Bits{0, std::uint64_t{1} << (p - 64)};
}
static int popcount(Bits a) { return std::popcount(a.lo) + std::popcount(a.hi); }

#pragma pack(push, 1)
struct CertHeaderV4 {
    char magic[8];
    std::uint32_t version;
    std::uint32_t boardSize;
    std::uint64_t nodeCount;
    std::uint64_t rootLo;
    std::uint64_t rootHi;
    std::uint64_t forbiddenCount;
};

struct CertNodeV4 {
    std::uint64_t lo;
    std::uint64_t hi;
    std::uint8_t outcome;
    std::uint8_t witness;
    std::uint8_t rank;
    std::uint8_t flags;
    std::uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(CertHeaderV4) == 48);
static_assert(sizeof(CertNodeV4) == 24);

class SmokeGenerator {
public:
    SmokeGenerator()
        : completion_(std::size_t{kPoints} * kPoints * kPoints),
          full_{~std::uint64_t{0}, (std::uint64_t{1} << (kPoints - 64)) - 1} {
        buildTransforms();
        buildForbidden();
    }

    void run(const std::string& output) {
        Bits root{};
        Bits terminal{};
        int witness = -1;
        bool found = false;

        // Try several deterministic legal walks. We require a nonempty high
        // word so CI exercises the full 100-bit encoding rather than merely
        // parsing a 10x10 header around a 64-bit state.
        for (std::uint64_t seed = 1; seed <= 256 && !found; ++seed) {
            Bits state{};
            Bits parent{};
            int lastMove = -1;
            std::uint64_t rng = seed;
            for (;;) {
                const Bits legal = legalFromState(state);
                if (!any(legal)) break;
                const auto moves = ids(legal);
                rng = rng * 6364136223846793005ULL + 1442695040888963407ULL;
                const int move = moves[static_cast<std::size_t>(rng % moves.size())];
                parent = state;
                lastMove = move;
                state = state | bitof(move);
            }
            if (lastMove < 0) continue;

            const auto [candidateRoot, transformKind] = canonicalWithKind(parent);
            const Bits candidateTerminal = canonical(state);
            const int candidateWitness = transformPointId(transformKind, lastMove);
            if (!(canonical(candidateRoot | bitof(candidateWitness)) == candidateTerminal)) {
                throw std::runtime_error("canonical witness edge mismatch");
            }
            if (any(legalFromState(candidateTerminal))) {
                throw std::runtime_error("greedy terminal state still has a legal move");
            }
            if ((candidateRoot.hi | candidateTerminal.hi) == 0) continue;

            root = candidateRoot;
            terminal = candidateTerminal;
            witness = candidateWitness;
            found = true;
        }

        if (!found) {
            throw std::runtime_error("could not construct a high-word 10x10 smoke certificate");
        }

        CertHeaderV4 header{};
        std::memcpy(header.magic, "KYOENC4", 7);
        header.version = 4;
        header.boardSize = kSize;
        header.nodeCount = 2;
        header.rootLo = root.lo;
        header.rootHi = root.hi;
        header.forbiddenCount = forbiddenCount_;

        const CertNodeV4 rootNode{
            root.lo,
            root.hi,
            2,
            static_cast<std::uint8_t>(witness),
            static_cast<std::uint8_t>(kPoints - popcount(root)),
            0,
            0,
        };
        const CertNodeV4 terminalNode{
            terminal.lo,
            terminal.hi,
            1,
            255,
            static_cast<std::uint8_t>(kPoints - popcount(terminal)),
            0,
            0,
        };

        std::ofstream out(output, std::ios::binary | std::ios::trunc);
        if (!out) throw std::runtime_error("cannot open output certificate");
        out.write(reinterpret_cast<const char*>(&header), sizeof(header));
        out.write(reinterpret_cast<const char*>(&rootNode), sizeof(rootNode));
        out.write(reinterpret_cast<const char*>(&terminalNode), sizeof(terminalNode));
        if (!out) throw std::runtime_error("failed to write KYOENC4 certificate");

        std::cout << "KYOENC4 smoke certificate written\n"
                  << "board=10x10 nodes=2 forbidden=" << forbiddenCount_ << '\n'
                  << "root_stones=" << popcount(root)
                  << " terminal_stones=" << popcount(terminal)
                  << " witness=" << witness << '\n'
                  << "root_hi=" << root.hi << " terminal_hi=" << terminal.hi << '\n';
    }

private:
    static constexpr int kSize = 10;
    static constexpr int kPoints = 100;

    std::vector<Bits> completion_;
    std::array<std::array<Bits, kPoints>, 8> transformedBit_{};
    Bits full_{};
    std::uint64_t forbiddenCount_ = 0;

    static std::size_t index(int a, int b, int c) {
        return (std::size_t(a) * kPoints + b) * kPoints + c;
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
        const int ids4[4] = {a, b, c, d};
        long long m[4][4]{};
        for (int r = 0; r < 4; ++r) {
            const long long x = ids4[r] % kSize;
            const long long y = ids4[r] / kSize;
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
            const long long minor = det3(
                z[0][0], z[0][1], z[0][2],
                z[1][0], z[1][1], z[1][2],
                z[2][0], z[2][1], z[2][2]);
            determinant += (col % 2 == 0 ? 1 : -1) * m[0][col] * minor;
        }
        return determinant == 0;
    }

    void buildForbidden() {
        for (int a = 0; a < kPoints; ++a)
            for (int b = a + 1; b < kPoints; ++b)
                for (int c = b + 1; c < kPoints; ++c)
                    for (int d = c + 1; d < kPoints; ++d) {
                        if (!forbidden(a, b, c, d)) continue;
                        ++forbiddenCount_;
                        const int q[4] = {a, b, c, d};
                        for (int omit = 0; omit < 4; ++omit) {
                            int triple[3];
                            int p = 0;
                            for (int j = 0; j < 4; ++j) {
                                if (j != omit) triple[p++] = q[j];
                            }
                            completion_[index(triple[0], triple[1], triple[2])] =
                                completion_[index(triple[0], triple[1], triple[2])] | bitof(q[omit]);
                        }
                    }
        if (forbiddenCount_ != 54441) {
            throw std::runtime_error("unexpected 10x10 forbidden quadruple count");
        }
    }

    static std::pair<int, int> transformPoint(int kind, int x, int y) {
        switch (kind) {
            case 0: return {x, y};
            case 1: return {kSize - 1 - x, y};
            case 2: return {x, kSize - 1 - y};
            case 3: return {kSize - 1 - x, kSize - 1 - y};
            case 4: return {y, x};
            case 5: return {kSize - 1 - y, x};
            case 6: return {y, kSize - 1 - x};
            default: return {kSize - 1 - y, kSize - 1 - x};
        }
    }

    static int transformPointId(int kind, int p) {
        const auto [x, y] = transformPoint(kind, p % kSize, p / kSize);
        return y * kSize + x;
    }

    void buildTransforms() {
        for (int kind = 0; kind < 8; ++kind)
            for (int p = 0; p < kPoints; ++p)
                transformedBit_[kind][p] = bitof(transformPointId(kind, p));
    }

    Bits transform(Bits state, int kind) const {
        Bits out{};
        for (int p : ids(state)) out = out | transformedBit_[kind][p];
        return out;
    }

    std::pair<Bits, int> canonicalWithKind(Bits state) const {
        Bits best = state;
        int bestKind = 0;
        for (int kind = 1; kind < 8; ++kind) {
            const Bits candidate = transform(state, kind);
            if (candidate < best) {
                best = candidate;
                bestKind = kind;
            }
        }
        return {best, bestKind};
    }

    Bits canonical(Bits state) const { return canonicalWithKind(state).first; }

    Bits legalFromState(Bits state) const {
        const auto points = ids(state);
        Bits banned{};
        for (std::size_t i = 0; i < points.size(); ++i)
            for (std::size_t j = i + 1; j < points.size(); ++j)
                for (std::size_t k = j + 1; k < points.size(); ++k)
                    banned = banned | completion_[index(points[i], points[j], points[k])];
        return full_ & ~state & ~banned;
    }

    static std::vector<int> ids(Bits state) {
        std::vector<int> out;
        while (state.lo) {
            const int p = std::countr_zero(state.lo);
            state.lo &= state.lo - 1;
            out.push_back(p);
        }
        while (state.hi) {
            const int p = std::countr_zero(state.hi);
            state.hi &= state.hi - 1;
            out.push_back(p + 64);
        }
        return out;
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            std::cerr << "usage: kyouen-certgen-v4-smoke OUTPUT.cert\n";
            return 2;
        }
        SmokeGenerator{}.run(argv[1]);
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
