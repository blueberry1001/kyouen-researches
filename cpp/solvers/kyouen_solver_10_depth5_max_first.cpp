// Experimental wrapper for the preregistered depth-5 ordering test.
//
// It reuses the exact production solver implementation and changes only the
// std::sort call in resume_3.inc.  At parent depth 5 (children have 6 stones),
// children are ordered by the existing cache priority, then legal-move count
// descending, then canonical key descending.  All other depths use the exact
// production comparator passed by the solver.
//
// Keep this as a separate binary so the baseline implementation remains
// untouched for the fresh-process A/B test.
#include "parts/kyouen_solver_10_kyoenc4_witness_log.inc"
#include "parts/kyouen_solver_10_kyoenc4_resume_0.inc"
#include "parts/kyouen_solver_10_kyoenc4_resume_1.inc"
#include "parts/kyouen_solver_10_kyoenc4_resume_2.inc"

namespace std {
template<class It, class Comp>
void kyouen_depth5_max_first_sort(It first, It last, Comp baseline_comp) {
    if (first != last && ::popcount(first->key) == 6) {
        std::sort(first, last, [](const auto& a, const auto& b) {
            const int pa = a.cached == MultiDepthMemo100::Losing ? 0 :
                           (a.cached == 0 ? 1 : 2);
            const int pb = b.cached == MultiDepthMemo100::Losing ? 0 :
                           (b.cached == 0 ? 1 : 2);
            if (pa != pb) return pa < pb;
            if (a.count != b.count) return a.count > b.count;
            return b.key < a.key;
        });
        return;
    }
    std::sort(first, last, baseline_comp);
}
}

#define sort kyouen_depth5_max_first_sort
#include "parts/kyouen_solver_10_kyoenc4_resume_3.inc"
#undef sort
#include "parts/kyouen_solver_10_kyoenc4_resume_4.inc"
