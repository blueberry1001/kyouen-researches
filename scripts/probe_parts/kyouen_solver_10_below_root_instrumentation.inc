// Included inside class Solver, after the core geometry helpers and before win().
// This instrumentation is observational only and is enabled exclusively when
// KYOEN_BELOW_ROOT_INSTRUMENT is present in the process environment.
static constexpr int kBelowRootDepths = 20;

struct BelowRootInstrumentation {
    int nesting = 0;
    int root_depth = -1;
    Bits root_key{};

    std::array<std::uint64_t, kBelowRootDepths> expanded{};
    std::array<std::uint64_t, kBelowRootDepths> terminal{};
    std::array<std::uint64_t, kBelowRootDepths> entry_get{};
    std::array<std::uint64_t, kBelowRootDepths> entry_hit_loss{};
    std::array<std::uint64_t, kBelowRootDepths> entry_hit_win{};
    std::array<std::uint64_t, kBelowRootDepths> child_get{};
    std::array<std::uint64_t, kBelowRootDepths> child_hit_loss{};
    std::array<std::uint64_t, kBelowRootDepths> child_hit_win{};
    std::array<std::uint64_t, kBelowRootDepths> put_loss{};
    std::array<std::uint64_t, kBelowRootDepths> put_win{};
    std::array<std::uint64_t, kBelowRootDepths> children_generated{};
    std::array<std::uint64_t, kBelowRootDepths> children_duplicate{};
    std::array<std::uint64_t, kBelowRootDepths> unique_children{};
    std::array<std::uint64_t, kBelowRootDepths> cached_loss_children{};
    std::array<std::uint64_t, kBelowRootDepths> cached_win_children{};
    std::array<std::uint64_t, kBelowRootDepths> unknown_children{};
    std::array<std::uint64_t, kBelowRootDepths> children_entered{};
    std::array<std::uint64_t, kBelowRootDepths> win_nodes{};
    std::array<std::uint64_t, kBelowRootDepths> loss_nodes{};
    std::array<std::uint64_t, kBelowRootDepths> cutoff_index_sum{};
    std::array<std::uint64_t, kBelowRootDepths> work_into_win_child{};
    std::array<std::uint64_t, kBelowRootDepths> work_into_loss_child{};
    std::array<std::uint64_t, kBelowRootDepths> calls_into_win_child{};
    std::array<std::uint64_t, kBelowRootDepths> calls_into_loss_child{};
    std::array<std::uint64_t, kBelowRootDepths> late_entry_hit_win{};
    std::array<std::uint64_t, kBelowRootDepths> late_entry_hit_loss{};
};

bool below_root_enabled_ = std::getenv("KYOEN_BELOW_ROOT_INSTRUMENT") != nullptr;
BelowRootInstrumentation below_root_{};

static bool below_root_depth_ok(int depth) {
    return depth >= 0 && depth < kBelowRootDepths;
}

void below_root_begin(int depth, Bits key) {
    if (!below_root_enabled_) return;
    if (below_root_.nesting == 0) {
        below_root_ = BelowRootInstrumentation{};
        below_root_.root_depth = depth;
        below_root_.root_key = key;
    }
    ++below_root_.nesting;
}

void below_root_entry(int depth, std::uint32_t cached) {
    if (!below_root_enabled_ || !below_root_depth_ok(depth)) return;
    ++below_root_.entry_get[depth];
    if (cached == MultiDepthMemo100::Losing) ++below_root_.entry_hit_loss[depth];
    if (cached == MultiDepthMemo100::Winning) ++below_root_.entry_hit_win[depth];
}

void below_root_expanded(int depth) {
    if (below_root_enabled_ && below_root_depth_ok(depth)) ++below_root_.expanded[depth];
}

void below_root_terminal(int depth) {
    if (below_root_enabled_ && below_root_depth_ok(depth)) ++below_root_.terminal[depth];
}

void below_root_generated(int depth) {
    if (below_root_enabled_ && below_root_depth_ok(depth)) ++below_root_.children_generated[depth];
}

void below_root_duplicate(int depth) {
    if (below_root_enabled_ && below_root_depth_ok(depth)) ++below_root_.children_duplicate[depth];
}

void below_root_child_prefetch(int depth, std::uint32_t cached) {
    if (!below_root_enabled_ || !below_root_depth_ok(depth)) return;
    ++below_root_.child_get[depth];
    ++below_root_.unique_children[depth];
    if (cached == MultiDepthMemo100::Losing) {
        ++below_root_.child_hit_loss[depth];
        ++below_root_.cached_loss_children[depth];
    } else if (cached == MultiDepthMemo100::Winning) {
        ++below_root_.child_hit_win[depth];
        ++below_root_.cached_win_children[depth];
    } else {
        ++below_root_.unknown_children[depth];
    }
}

void below_root_child_entered(int depth) {
    if (below_root_enabled_ && below_root_depth_ok(depth)) ++below_root_.children_entered[depth];
}

void below_root_recursive_result(int depth, bool child_winning, std::uint64_t visited_delta) {
    if (!below_root_enabled_ || !below_root_depth_ok(depth)) return;
    if (child_winning) {
        ++below_root_.calls_into_win_child[depth];
        below_root_.work_into_win_child[depth] += visited_delta;
        if (visited_delta == 0) ++below_root_.late_entry_hit_win[depth];
    } else {
        ++below_root_.calls_into_loss_child[depth];
        below_root_.work_into_loss_child[depth] += visited_delta;
        if (visited_delta == 0) ++below_root_.late_entry_hit_loss[depth];
    }
}

void below_root_cutoff(int depth, int one_based_index) {
    if (!below_root_enabled_ || !below_root_depth_ok(depth)) return;
    below_root_.cutoff_index_sum[depth] += static_cast<std::uint64_t>(one_based_index);
}

void below_root_put(int depth, bool winning) {
    if (!below_root_enabled_ || !below_root_depth_ok(depth)) return;
    if (winning) {
        ++below_root_.put_win[depth];
        ++below_root_.win_nodes[depth];
    } else {
        ++below_root_.put_loss[depth];
        ++below_root_.loss_nodes[depth];
    }
}

template<class A>
static std::uint64_t below_root_sum(const A& a) {
    std::uint64_t s = 0;
    for (auto v : a) s += v;
    return s;
}

[[noreturn]] static void below_root_fail(const char* what, int depth) {
    throw std::runtime_error(std::string("below-root counter invariant failed at depth ") +
                             std::to_string(depth) + ": " + what);
}

void below_root_validate(const Stats& st) const {
    if (!below_root_enabled_) return;
    if (st.maxdepth >= kBelowRootDepths) {
        throw std::runtime_error("below-root depth range 0..19 is insufficient for this solve");
    }
    for (int d = 0; d < kBelowRootDepths; ++d) {
        const auto entry_hits = below_root_.entry_hit_loss[d] + below_root_.entry_hit_win[d];
        const auto child_hits = below_root_.child_hit_loss[d] + below_root_.child_hit_win[d];
        const auto puts = below_root_.put_loss[d] + below_root_.put_win[d];
        const auto nodes = below_root_.loss_nodes[d] + below_root_.win_nodes[d];
        if (below_root_.entry_get[d] != below_root_.expanded[d] + entry_hits)
            below_root_fail("entry_get != expanded + entry_hits", d);
        if (child_hits > below_root_.child_get[d])
            below_root_fail("child hits exceed child_get", d);
        if (below_root_.child_get[d] != below_root_.unique_children[d])
            below_root_fail("child_get != unique_children", d);
        if (below_root_.unique_children[d] + below_root_.children_duplicate[d] !=
            below_root_.children_generated[d])
            below_root_fail("unique + duplicate != generated", d);
        if (below_root_.unique_children[d] != below_root_.cached_loss_children[d] +
                                               below_root_.cached_win_children[d] +
                                               below_root_.unknown_children[d])
            below_root_fail("cached/unknown split != unique_children", d);
        if (puts != below_root_.expanded[d])
            below_root_fail("puts != expanded", d);
        if (nodes != below_root_.expanded[d])
            below_root_fail("win_nodes + loss_nodes != expanded", d);
        if (below_root_.terminal[d] > below_root_.loss_nodes[d])
            below_root_fail("terminal exceeds loss_nodes", d);
        if (below_root_.children_entered[d] > below_root_.unique_children[d])
            below_root_fail("children_entered exceeds unique_children", d);
        if (below_root_.calls_into_win_child[d] + below_root_.calls_into_loss_child[d] >
            below_root_.unknown_children[d])
            below_root_fail("recursive calls exceed unknown_children", d);
        if (below_root_.late_entry_hit_win[d] > below_root_.calls_into_win_child[d])
            below_root_fail("late WIN hits exceed WIN calls", d);
        if (below_root_.late_entry_hit_loss[d] > below_root_.calls_into_loss_child[d])
            below_root_fail("late LOSS hits exceed LOSS calls", d);
        if (below_root_.cutoff_index_sum[d] < below_root_.win_nodes[d])
            below_root_fail("cutoff index sum smaller than win_nodes", d);
        if (st.depth_visited[static_cast<std::size_t>(d)] != below_root_.expanded[d])
            below_root_fail("expanded disagrees with existing depth_visited", d);
    }
    if (below_root_sum(below_root_.expanded) != st.visited)
        throw std::runtime_error("below-root sum(expanded) != visited");
}

void below_root_emit(bool outcome, const Stats& st) const {
    if (!below_root_enabled_) return;
    std::cerr
        << "below_root_csv_header,root_lo,root_hi,root_depth,outcome,depth,visited,maxdepth,memo,"
        << "expanded,terminal,entry_get,entry_hit_loss,entry_hit_win,child_get,child_hit_loss,child_hit_win,"
        << "put_loss,put_win,children_generated,children_duplicate,unique_children,cached_loss_children,"
        << "cached_win_children,unknown_children,children_entered,win_nodes,loss_nodes,cutoff_index_sum,"
        << "work_into_win_child,work_into_loss_child,calls_into_win_child,calls_into_loss_child,"
        << "late_entry_hit_win,late_entry_hit_loss\n";

    auto emit_common = [&](auto depth_value, int d) {
        std::cerr << "below_root_csv," << below_root_.root_key.lo << ',' << below_root_.root_key.hi
                  << ',' << below_root_.root_depth << ',' << (outcome ? "WIN" : "LOSS") << ','
                  << depth_value << ',' << st.visited << ',' << st.maxdepth << ',' << memo_.used() << ','
                  << below_root_.expanded[d] << ',' << below_root_.terminal[d] << ','
                  << below_root_.entry_get[d] << ',' << below_root_.entry_hit_loss[d] << ','
                  << below_root_.entry_hit_win[d] << ',' << below_root_.child_get[d] << ','
                  << below_root_.child_hit_loss[d] << ',' << below_root_.child_hit_win[d] << ','
                  << below_root_.put_loss[d] << ',' << below_root_.put_win[d] << ','
                  << below_root_.children_generated[d] << ',' << below_root_.children_duplicate[d] << ','
                  << below_root_.unique_children[d] << ',' << below_root_.cached_loss_children[d] << ','
                  << below_root_.cached_win_children[d] << ',' << below_root_.unknown_children[d] << ','
                  << below_root_.children_entered[d] << ',' << below_root_.win_nodes[d] << ','
                  << below_root_.loss_nodes[d] << ',' << below_root_.cutoff_index_sum[d] << ','
                  << below_root_.work_into_win_child[d] << ',' << below_root_.work_into_loss_child[d] << ','
                  << below_root_.calls_into_win_child[d] << ',' << below_root_.calls_into_loss_child[d] << ','
                  << below_root_.late_entry_hit_win[d] << ',' << below_root_.late_entry_hit_loss[d] << '\n';
    };
    for (int d = 0; d < kBelowRootDepths; ++d) emit_common(d, d);

    std::cerr << "below_root_total," << below_root_.root_key.lo << ',' << below_root_.root_key.hi
              << ',' << below_root_.root_depth << ',' << (outcome ? "WIN" : "LOSS") << ",TOTAL,"
              << st.visited << ',' << st.maxdepth << ',' << memo_.used() << ','
              << below_root_sum(below_root_.expanded) << ',' << below_root_sum(below_root_.terminal) << ','
              << below_root_sum(below_root_.entry_get) << ',' << below_root_sum(below_root_.entry_hit_loss) << ','
              << below_root_sum(below_root_.entry_hit_win) << ',' << below_root_sum(below_root_.child_get) << ','
              << below_root_sum(below_root_.child_hit_loss) << ',' << below_root_sum(below_root_.child_hit_win) << ','
              << below_root_sum(below_root_.put_loss) << ',' << below_root_sum(below_root_.put_win) << ','
              << below_root_sum(below_root_.children_generated) << ',' << below_root_sum(below_root_.children_duplicate) << ','
              << below_root_sum(below_root_.unique_children) << ',' << below_root_sum(below_root_.cached_loss_children) << ','
              << below_root_sum(below_root_.cached_win_children) << ',' << below_root_sum(below_root_.unknown_children) << ','
              << below_root_sum(below_root_.children_entered) << ',' << below_root_sum(below_root_.win_nodes) << ','
              << below_root_sum(below_root_.loss_nodes) << ',' << below_root_sum(below_root_.cutoff_index_sum)
              << ",NA,NA," << below_root_sum(below_root_.calls_into_win_child) << ','
              << below_root_sum(below_root_.calls_into_loss_child) << ','
              << below_root_sum(below_root_.late_entry_hit_win) << ','
              << below_root_sum(below_root_.late_entry_hit_loss) << '\n';
    std::cerr << "below_root_meta,total_work_fields=NA_cross_depth_subtree_deltas_overlap\n";
}

void below_root_leave(bool outcome, const Stats& st) {
    if (!below_root_enabled_) return;
    if (below_root_.nesting <= 0) throw std::runtime_error("below-root nesting underflow");
    const bool top = below_root_.nesting == 1;
    --below_root_.nesting;
    if (top) {
        below_root_validate(st);
        below_root_emit(outcome, st);
    }
}
