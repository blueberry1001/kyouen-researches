#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

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

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            std::cerr << "usage: convert-9-v2-to-v3 INPUT-v2.cert OUTPUT-v3.cert\n";
            return 2;
        }
        std::ifstream in(argv[1], std::ios::binary);
        if (!in) throw std::runtime_error("cannot open input");
        CertHeader old{};
        in.read(reinterpret_cast<char*>(&old), sizeof(old));
        if (!in || std::memcmp(old.magic, "KYOENC2", 7) != 0 || old.version != 2 || old.boardSize != 9)
            throw std::runtime_error("not a 9x9 KYOENC2 certificate");
        if (old.rootLo != (1ULL << 40) || old.rootHi != 0)
            throw std::runtime_error("v2 root is not the centre singleton");

        std::ofstream out(argv[2], std::ios::binary | std::ios::trunc);
        if (!out) throw std::runtime_error("cannot open output");
        CertHeader header = old;
        std::memset(header.magic, 0, sizeof(header.magic));
        std::memcpy(header.magic, "KYOENC3", 7);
        header.version = 3;
        header.nodeCount = old.nodeCount + 1;
        header.rootLo = 0;
        header.rootHi = 0;
        out.write(reinterpret_cast<const char*>(&header), sizeof(header));

        // Empty board is winning via the centre. Its child is the old losing root.
        const CertNode empty{0, 0, 2, 40, 81, 0};
        out.write(reinterpret_cast<const char*>(&empty), sizeof(empty));

        char buffer[1 << 20];
        while (in) {
            in.read(buffer, sizeof(buffer));
            const auto n = in.gcount();
            if (n > 0) out.write(buffer, n);
        }
        if (!out) throw std::runtime_error("copy failed");
        std::cout << "converted nodes=" << header.nodeCount << " root=empty witness=center\n";
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
