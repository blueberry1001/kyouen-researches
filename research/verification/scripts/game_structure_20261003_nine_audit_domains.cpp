// Independent boundary checks for the frozen 9x9 experiment.
// Build directly; the relative include makes this portable with the repository.
#define main original_nine_main
#include "game_structure_20261003_nine.cpp"
#undef main
#include <cassert>

int main() {
    initialize();
    assert(encode(0) == 0);
    assert(encode(B(1) << 80) == 81);
    assert(encode((B(1) << 20) - 1) == 2143508038974053704ULL);
    assert(encode(((B(1) << 20) - 1) << 61) == 6837944227813170423ULL);
    bool caught = false;
    try {
        encode((B(1) << 21) - 1);
    } catch (const std::runtime_error& error) {
        caught = std::string(error.what()).find("rank domain exceeded") != std::string::npos;
    }
    assert(caught);
    caught = false;
    try {
        encode(B(1) << 81);
    } catch (const std::runtime_error& error) {
        caught = std::string(error.what()).find("outside board") != std::string::npos;
    }
    assert(caught);
    assert(count(ALL) == 81 && U(ALL >> 64) == 131071);
    for (int t = 0; t < 8; ++t) {
        B image = 0;
        for (int p = 0; p < 81; ++p) image |= transform[t][p];
        assert(image == ALL);
    }
    puts("rank extremes, 21-stone guard, outside-board guard and D4 domains PASS");
}
