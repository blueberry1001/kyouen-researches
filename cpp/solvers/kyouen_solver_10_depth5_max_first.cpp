// Experimental wrapper for the preregistered depth-5 ordering test.
//
// It reuses the exact production solver implementation and changes only the
// std::sort call in resume_3.inc. At parent depth 5, children have six stones;
// those children are ordered by legal-move count descending, then canonical
// key descending. All other depths use the exact production comparator.
//
// Keep this as a separate binary so the baseline implementation remains
// untouched for the fresh-process A/B test.
#include <algorithm>
#include <bit>

namespace std {
template<class It, class Comp>
void kyouen_depth5_max_first_sort(It first, It last, Comp baseline_comp) {
    if (first != last &&
        (std::popcount(first->key.lo) + std::popcount(first->key.hi) == 6)) {
        // Depth-6 children are outside the memoized depth range (9..17), so
        // cached is necessarily zero here. The frozen rule is therefore just
        // count DESC, then canonical key DESC.
        std::sort(first, last, [](const auto& a, const auto& b) {
            if (a.count != b.count) return a.count > b.count;
            return b.key < a.key;
        });
        return;
    }
    std::sort(first, last, baseline_comp);
}
}

#include "parts/kyouen_solver_10_kyoenc4_witness_log.inc"
#include "parts/kyouen_solver_10_kyoenc4_resume_0.inc"
#include "parts/kyouen_solver_10_kyoenc4_resume_1.inc"
#include "parts/kyouen_solver_10_kyoenc4_resume_2.inc"
#define sort kyouen_depth5_max_first_sort
#include "parts/kyouen_solver_10_kyoenc4_resume_3.inc"
#undef sort
#include "parts/kyouen_solver_10_kyoenc4_resume_4.inc"
