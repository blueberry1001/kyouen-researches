// Order-equivalence test harness for the cache-aware below-root child
// ordering implementations (S: single std::sort, B: three-bucket partition
// + per-bucket sort).
//
// This is NOT the endpoint solver binary. It includes the frozen solver
// parts (resume_4's main is #define-disabled), re-exposes the two below-root
// cache-aware ordering paths on synthetic child arrays, and adds per-call
// comparison instrumentation. It exists only to prove order equivalence
// before any exact-solver run, per the frozen order-equivalence gate in
// docs/10X10_CACHE_AWARE_BUCKET_ORDER_OPT_PREREG.md.
//
// Fixture premise (explicit): canonical child keys are unique after the
// solver's duplicate-elimination stage, so (class, count, key) is a total
// order and duplicate keys are NOT generated. Duplicate-key inputs are
// excluded by premise, not tested.
#include <set>
#include <sstream>
#include <type_traits>
#define main solver_main_disabled_in_test_harness
#include "probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc"
#include "probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"
#undef main
// The test targets the LIVE solver ordering methods exposed by the solver
// (Solver::order_cache_aware_{single_sort,bucket}_for_test on
// Solver::OrderTestChild, added as the preregistered minimal exposure).
// Mirror copies of the comparators below provide an independent compiled
// cross-check of the same rules.
namespace order_equiv {
using ::Bits;
constexpr std::uint32_t LOSING = MultiDepthMemo100::Losing;   // 1
constexpr std::uint32_t WINNING = MultiDepthMemo100::Winning;  // 2
struct Child {
    Bits ts_lo{}, ts_hi{};   // inert payload stand-in
    Bits legal{};
    Bits key{};
    int count = 0;
    std::uint32_t cached = 0;
};
static_assert(std::is_trivially_copyable_v<Child>);

std::uint64_t g_comparisons = 0;
std::uint64_t g_calls = 0;

static inline int cls(std::uint32_t c) {
    return c == LOSING ? 0 : (c == 0 ? 1 : 2);
}

// S: the exact single-std::sort cache-aware comparator from the frozen base
// e9d0460 order_children else-branch (cached class, then count asc, then
// canonical key asc).
static void order_single(std::vector<Child>& ch) {
    ++g_calls;
    std::sort(ch.begin(), ch.end(), [](const Child& a, const Child& b) {
        ++g_comparisons;
        int pa = cls(a.cached), pb = cls(b.cached);
        if (pa != pb) return pa < pb;
        if (a.count != b.count) return a.count < b.count;
        return a.key < b.key;
    });
}

// B: the exact three-bucket procedure added to the solver
// (order_children_cache_aware_bucket): partition cached LOSS to the front,
// unknown (cached==0) after it, cached WIN last; then sort each bucket by
// (count asc, canonical key asc).
static void order_bucket(std::vector<Child>& ch) {
    ++g_calls;
    const int n = (int)ch.size();
    int w = 0;
    for (int i = 0; i < n; ++i)
        if (ch[i].cached == LOSING) std::swap(ch[i], ch[w++]);
    int m = w;
    for (int i = w; i < n; ++i)
        if (ch[i].cached == 0) std::swap(ch[i], ch[m++]);
    auto cnt_key_lt = [](const Child& a, const Child& b) {
        ++g_comparisons;
        if (a.count != b.count) return a.count < b.count;
        return a.key < b.key;
    };
    std::sort(ch.begin(), ch.begin() + w, cnt_key_lt);
    std::sort(ch.begin() + w, ch.begin() + m, cnt_key_lt);
    std::sort(ch.begin() + m, ch.begin() + n, cnt_key_lt);
}

static std::string key_str(Bits k) {
    std::ostringstream os;
    os << k.hi << ":" << k.lo;
    return os.str();
}

struct Failure { std::string msg; };

static void require_eq(const std::vector<Child>& a, const std::vector<Child>& b,
                       const std::string& label, std::vector<Failure>& fails) {
    if (a.size() != b.size()) {
        fails.push_back({label + ": size differs " +
                         std::to_string(a.size()) + " vs " +
                         std::to_string(b.size())});
        return;
    }
    for (std::size_t i = 0; i < a.size(); ++i)
        if (!(a[i].key == b[i].key)) {
            fails.push_back({label + ": first divergence at index " +
                            std::to_string(i) + ": S=" + key_str(a[i].key) +
                            " B=" + key_str(b[i].key)});
            return;
        }
}

static Child make_child(std::uint64_t lo, std::uint64_t hi, int count,
                        std::uint32_t cls_pick) {
    Child c;
    c.key = Bits{lo, hi};
    c.count = count;
    c.cached = cls_pick == 0 ? 0 : (cls_pick == 1 ? LOSING : WINNING);
    return c;
}

using OrderChild = Solver::OrderTestChild;
static OrderChild to_solver_child(const Child& c) {
    OrderChild o;
    o.ts = {};            // inert for ordering
    o.legal = c.legal;
    o.key = c.key;
    o.count = c.count;
    o.cached = c.cached;
    return o;
}
static std::vector<OrderChild> to_solver_children(const std::vector<Child>& ch) {
    std::vector<OrderChild> out;
    out.reserve(ch.size());
    for (const auto& c : ch) out.push_back(to_solver_child(c));
    return out;
}

// Compare the LIVE solver ordering methods on the same fixture: convert,
// run Solver::order_cache_aware_single_sort_for_test vs
// Solver::order_cache_aware_bucket_for_test, require equal key sequences.
static void require_live_eq(const std::vector<Child>& fixture,
                            const std::string& label,
                            std::vector<Failure>& fails) {
    std::vector<OrderChild> a = to_solver_children(fixture);
    std::vector<OrderChild> b = a;
    Solver::order_cache_aware_single_sort_for_test(a);
    Solver::order_cache_aware_bucket_for_test(b);
    if (a.size() != b.size()) {
        fails.push_back({label + " [live]: size differs"});
        return;
    }
    for (std::size_t i = 0; i < a.size(); ++i)
        if (!(a[i].key == b[i].key)) {
            fails.push_back({label + " [live]: divergence at " +
                            std::to_string(i) + ": S=" + key_str(a[i].key) +
                            " B=" + key_str(b[i].key)});
            return;
        }
}

// Deterministic 64-bit RNG (splitmix64); no platform stdlib variation.
struct Rng {
    std::uint64_t s = 0;
    std::uint64_t next() {
        s += 0x9E3779B97F4A7C15ULL;
        std::uint64_t z = s;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    std::uint64_t below(std::uint64_t n) { return next() % n; }
};

}  // namespace order_equiv

int main() {
    using namespace order_equiv;
    std::vector<Failure> fails;
    std::uint64_t cases = 0;

    struct Case { const char* label; std::vector<Child> ch; };
    std::vector<Case> cases_vec;

    // n=0
    cases_vec.push_back({"n0", {}});
    // n=1 per class
    cases_vec.push_back({"n1_loss", {make_child(5, 0, 3, 1)}});
    cases_vec.push_back({"n1_unknown", {make_child(5, 0, 3, 0)}});
    cases_vec.push_back({"n1_win", {make_child(5, 0, 3, 2)}});
    // all LOSS / all unknown / all WIN (with count and key variety)
    cases_vec.push_back({"all_loss", {make_child(9, 0, 7, 1),
                                      make_child(3, 0, 7, 1),
                                      make_child(5, 0, 2, 1)}});
    cases_vec.push_back({"all_unknown", {make_child(9, 0, 7, 0),
                                         make_child(3, 0, 7, 0),
                                         make_child(5, 0, 2, 0)}});
    cases_vec.push_back({"all_win", {make_child(9, 0, 7, 2),
                                     make_child(3, 0, 7, 2),
                                     make_child(5, 0, 2, 2)}});
    // same count, only keys differ (within every class)
    cases_vec.push_back({"same_count_key_only", {
        make_child(30, 0, 5, 1), make_child(20, 0, 5, 1),
        make_child(10, 0, 5, 1), make_child(33, 0, 5, 0),
        make_child(22, 0, 5, 0), make_child(11, 0, 5, 0),
        make_child(99, 0, 5, 2), make_child(77, 0, 5, 2),
        make_child(55, 0, 5, 2)}});
    // same class, counts differ
    cases_vec.push_back({"same_class_count_diff", {
        make_child(1, 0, 9, 1), make_child(2, 0, 1, 1),
        make_child(3, 0, 5, 1)}});
    // three classes mixed
    std::vector<Child> mixed = {
        make_child(101, 0, 4, 2), make_child(102, 0, 9, 0),
        make_child(103, 0, 1, 1), make_child(104, 0, 4, 0),
        make_child(105, 0, 9, 1), make_child(106, 0, 1, 2),
        make_child(107, 0, 4, 1), make_child(108, 0, 9, 2),
        make_child(109, 0, 1, 0), make_child(110, 0, 6, 0)};
    cases_vec.push_back({"mixed_identity", mixed});
    {  // adversarial: reversed input
        std::vector<Child> rev(mixed.rbegin(), mixed.rend());
        cases_vec.push_back({"mixed_reverse", rev});
    }
    {  // adversarial: LOSS/WIN interleaved, unknowns appended
        std::vector<Child> adv;
        for (int i = 0; i < 20; ++i)
            adv.push_back(make_child((std::uint64_t)(100 + i), 0,
                                      (i * 7) % 11, (i % 2) ? 1 : 2));
        for (int i = 0; i < 5; ++i)
            adv.push_back(make_child((std::uint64_t)(200 + i), 0, i, 0));
        cases_vec.push_back({"adversarial_interleave", adv});
    }
    {  // all same count across classes; keys reversed within classes
        std::vector<Child> t;
        for (int i = 19; i >= 0; --i)
            t.push_back(make_child((std::uint64_t)(300 + i), 0, 8,
                                    i % 3 == 0 ? 1 : (i % 3 == 1 ? 0 : 2)));
        cases_vec.push_back({"all_same_count", t});
    }

    for (auto& c : cases_vec) {
        std::vector<Child> a = c.ch, b = c.ch;
        order_single(a);
        order_bucket(b);
        require_eq(a, b, c.label, fails);
        require_live_eq(c.ch, c.label, fails);
        ++cases;
    }

    // Exhaustive permutations, 4 children (L, U, U, W; same count):
    // 4! = 24.
    {
        const std::vector<Child> base = {
            make_child(10, 0, 3, 1), make_child(20, 0, 3, 0),
            make_child(30, 0, 3, 0), make_child(40, 0, 3, 2)};
        int idx[4] = {0, 1, 2, 3};
        do {
            std::vector<Child> perm;
            for (int i = 0; i < 4; ++i) perm.push_back(base[idx[i]]);
            std::vector<Child> a = perm, b = perm;
            order_single(a);
            order_bucket(b);
            require_eq(a, b, "perm4", fails);
            require_live_eq(perm, "perm4", fails);
            ++cases;
        } while (std::next_permutation(idx, idx + 4));
    }
    // Exhaustive permutations, 5 children (L, L, U, U, W): 5! = 120.
    {
        const std::vector<Child> base = {
            make_child(10, 0, 5, 1), make_child(20, 0, 5, 1),
            make_child(30, 0, 5, 0), make_child(40, 0, 5, 0),
            make_child(50, 0, 5, 2)};
        int idx[5] = {0, 1, 2, 3, 4};
        do {
            std::vector<Child> perm;
            for (int i = 0; i < 5; ++i) perm.push_back(base[idx[i]]);
            std::vector<Child> a = perm, b = perm;
            order_single(a);
            order_bucket(b);
            require_eq(a, b, "perm5", fails);
            require_live_eq(perm, "perm5", fails);
            ++cases;
        } while (std::next_permutation(idx, idx + 5));
    }

    // Deterministic random fixtures: 24,000 core cases, every third also
    // reversed (adversarial). Class-mix modes cover: all-LOSS, all-unknown,
    // all-WIN, 2-class subsets, and 3-class mixes. Duplicate keys are
    // excluded by premise (solver uniqueness guarantee).
    {
        const std::uint64_t seed0 = 0xC0FFEE123456789ULL;
        const int n_cases = 24000;
        for (int t = 0; t < n_cases; ++t) {
            Rng r;
            r.s = seed0 + (std::uint64_t)t * 0x2545F4914F6CDD1DULL;
            r.next();
            const int n = (int)(2 + r.below(99));          // n in [2, 100]
            const std::uint32_t mode = (std::uint32_t)r.below(8);
            std::set<std::uint64_t> used;
            std::vector<Child> ch;
            ch.reserve((std::size_t)n);
            for (int i = 0; i < n; ++i) {
                std::uint64_t k = 0;
                do { k = 1 + r.below((1ULL << 60) - 2); } while (!used.insert(k).second);
                std::uint32_t cached;
                switch (mode) {
                    case 0: cached = 1; break;                  // all LOSS
                    case 1: cached = 0; break;                   // all unknown
                    case 2: cached = 2; break;                   // all WIN
                    case 3: cached = r.below(2) == 0 ? 1 : 0; break;  // L+U
                    case 4: cached = r.below(2) == 0 ? 1 : 2; break;  // L+W
                    case 5: cached = r.below(2) == 0 ? 0 : 2; break;  // U+W
                    default: cached = (std::uint32_t)r.below(3); break;  // 3-class
                }
                const int count = r.below(4) == 0 ? 3 : (int)r.below(31);
                ch.push_back(make_child(k, 0, count, cached));
            }
            std::vector<Child> a = ch, b = ch;
            order_single(a);
            order_bucket(b);
            require_eq(a, b, "rand#" + std::to_string(t), fails);
            require_live_eq(ch, "rand#" + std::to_string(t), fails);
            ++cases;
            if (t % 3 == 0) {
                std::vector<Child> ra(ch.rbegin(), ch.rend());
                std::vector<Child> x = ra, y = ra;
                order_single(x);
                order_bucket(y);
                require_eq(x, y, "randrev#" + std::to_string(t), fails);
                require_live_eq(ra, "randrev#" + std::to_string(t), fails);
                ++cases;
            }
        }
    }

    std::cout << "order_equivalence_cases=" << cases << "\n";
    std::cout << "ordering_calls=" << g_calls << "\n";
    std::cout << "total_comparisons=" << g_comparisons << "\n";
    if (!fails.empty()) {
        std::cout << "ORDER EQUIVALENCE FAIL count=" << fails.size() << "\n";
        for (std::size_t i = 0; i < fails.size() && i < 20; ++i)
            std::cout << "FAIL " << fails[i].msg << "\n";
        return 1;
    }
    std::cout << "live_solver_method_checks=included (S::order_cache_aware_single_sort_for_test"
              << " == B::order_cache_aware_bucket_for_test)\n";
    std::cout << "ORDER EQUIVALENCE PASS (S==B exact key sequences, "
              << cases << " mirror cases + "
              << "same fixtures via live Solver methods)\n";
    return 0;
}
