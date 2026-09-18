// Cycle 6: full enumeration and exchange-structure analysis of maximal
// safe (kyouen-free) sets on n x n boards.
//
// Modes:
//   maxsafe_enum.exe count  n K            -> number of safe K-sets
//   maxsafe_enum.exe enum   n K out.bin    -> enumerate all safe K-sets (u64 each)
//   maxsafe_enum.exe analyze n K in.bin pfx -> per-set stats, swaps, components, cell freq
//
// A safe K-set of maximum size is automatically maximal (saturated):
// K_6 = 11, K_7 = 14 are established (UNSAT at K+1), so enumerating safe
// K-sets enumerates the maximal safe sets.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

using u64 = std::uint64_t;

static int N, V;
static std::vector<std::vector<u64>> triples_by_pt; // per point: "other 3" masks of forbidden quads
static int n_quads_total = 0;

static void build_geometry() {
    V = N * N;
    std::vector<std::array<long long, 4>> rows(V);
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++)
            rows[y * N + x] = {(long long)x * x + (long long)y * y, x, y, 1};
    triples_by_pt.assign(V, {});
    n_quads_total = 0;
    for (int a = 0; a < V - 3; a++)
    for (int b = a + 1; b < V - 2; b++)
    for (int c = b + 1; c < V - 1; c++)
    for (int d = c + 1; d < V; d++) {
        long long m[4][4];
        int ids[4] = {a, b, c, d};
        for (int i = 0; i < 4; i++)
            for (int j = 0; j < 4; j++)
                m[i][j] = rows[ids[i]][j];
        long long det = 0;
        for (int i = 0; i < 4; i++) {
            long long mm[3][3];
            int ri = 0;
            for (int r2 = 0; r2 < 4; r2++) {
                if (r2 == i) continue;
                int ci = 0;
                for (int c2 = 1; c2 < 4; c2++) mm[ri][ci++] = m[r2][c2];
                ri++;
            }
            long long det3 =
                mm[0][0]*(mm[1][1]*mm[2][2]-mm[1][2]*mm[2][1])
              - mm[0][1]*(mm[1][0]*mm[2][2]-mm[1][2]*mm[2][0])
              + mm[0][2]*(mm[1][0]*mm[2][1]-mm[1][1]*mm[2][0]);
            det += (i % 2 == 0 ? 1 : -1) * m[i][0] * det3;
        }
        if (det == 0) {
            n_quads_total++;
            for (int t = 0; t < 4; t++) {
                u64 o = 0;
                for (int s = 0; s < 4; s++)
                    if (s != t) o |= 1ULL << ids[s];
                triples_by_pt[ids[t]].push_back(o);
            }
        }
    }
}

// ---- D4 transforms ----
static std::vector<std::array<int, 64>> d4_perm; // 8 permutations of point indices

static void build_d4() {
    d4_perm.assign(8, {});
    int t = 0;
    for (int m : {0, 1, 2, 3, 4, 5, 6, 7}) {
        bool flip_x = m & 1, flip_y = m & 2, trans = m & 4;
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++) {
                int sx = flip_x ? (N - 1 - x) : x;
                int sy = flip_y ? (N - 1 - y) : y;
                int nx = trans ? sy : sx;
                int ny = trans ? sx : sy;
                d4_perm[t][y * N + x] = ny * N + nx;
            }
        t++;
    }
}

static inline u64 apply_perm(const std::array<int, 64>& p, u64 mask) {
    u64 out = 0;
    u64 m = mask;
    while (m) {
        int i = __builtin_ctzll(m);
        m &= m - 1;
        out |= 1ULL << p[i];
    }
    return out;
}

static inline u64 canonical_key(u64 mask) {
    u64 best = ~0ULL;
    for (int t = 0; t < 8; t++) {
        u64 c = apply_perm(d4_perm[t], mask);
        if (c < best) best = c;
    }
    return best;
}

static inline int stabilizer_size(u64 mask) {
    int s = 0;
    for (int t = 0; t < 8; t++)
        if (apply_perm(d4_perm[t], mask) == mask) s++;
    return s;
}

// ---- enumeration of all safe K-sets ----
static int ccount[64];
static u64 chosen_set = 0;
static int g_target = 0;
static long long node_count = 0;
static long long n_found = 0;
static std::vector<u64> *out_sets = nullptr;
static std::vector<int> undo_stack;

static void dfs_enum(u64 cand, int count) {
    ++node_count;
    if (count == g_target) {
        if (out_sets) out_sets->push_back(chosen_set);
        ++n_found;
        return;
    }
    if (count + __builtin_popcountll(cand) < g_target) return;
    while (cand) {
        int u = __builtin_ctzll(cand);
        size_t mark = undo_stack.size();
        u64 newcand = cand & ~(1ULL << u);
        for (u64 o : triples_by_pt[u]) {
            int pc = __builtin_popcountll(o & chosen_set);
            if (pc == 2) {
                int w = __builtin_ctzll(o & ~chosen_set);
                if (ccount[w]++ == 0) newcand &= ~(1ULL << w);
                undo_stack.push_back(w);
            }
        }
        chosen_set |= 1ULL << u;
        dfs_enum(newcand, count + 1);
        chosen_set &= ~(1ULL << u);
        while ((int)undo_stack.size() > (int)mark) {
            ccount[undo_stack.back()]--;
            undo_stack.pop_back();
        }
        cand &= ~(1ULL << u);
        if (count + __builtin_popcountll(cand) < g_target) return;
    }
}

// ---- analysis ----
struct SetStats {
    u64 mask;
    u64 canon;
    int orbit_size;
    int stab;
    int num_empty;
    int rho;
    int swap_pairs;      // # of (v, r) single-stone swaps
    int swap_destinct;   // distinct destination sets
    int min_blockers, max_blockers;
    int tau1_count;      // # empty v with tau(v) == 1
    int v_with_tau[8];   // histogram of tau values (index 1..6)
};

// simple open-addressing map mask -> id
struct MaskMap {
    std::vector<u64> keys;
    std::vector<int> vals;
    size_t mask_;
    size_t used_ = 0;
    explicit MaskMap(size_t n) { init(n); }
    void init(size_t n) {
        size_t sz = 1024;
        while (sz < n * 2) sz <<= 1;
        keys.assign(sz, 0);
        vals.assign(sz, -1);
        mask_ = sz - 1;
    }
    static inline u64 mix(u64 x) {
        x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27; x *= 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    inline int get(u64 k) const {
        size_t i = mix(k) & mask_;
        while (vals[i] >= 0) {
            if (keys[i] == k) return vals[i];
            i = (i + 1) & mask_;
        }
        return -1;
    }
    inline void put(u64 k, int v) {
        size_t i = mix(k) & mask_;
        while (vals[i] >= 0) {
            if (keys[i] == k) { vals[i] = v; return; }
            i = (i + 1) & mask_;
        }
        keys[i] = k;
        vals[i] = v;
        ++used_;
    }
};

// minimal hitting-set size of the blocker triple family of empty point v
// blockers: triples T (subset of S) with T u {v} forbidden.
// Returns tau and (for tau == 1) the set of valid removed stones.
static int tau_of(const u64 *blockers, int nb, u64 S, u64 *valid_r1) {
    if (nb == 0) return 0; // v is addable (S not maximal)
    // tau = 1: common stone in all blockers
    u64 inter = ~0ULL;
    for (int i = 0; i < nb; i++) inter &= blockers[i];
    if (inter) {
        if (valid_r1) *valid_r1 = inter;
        return 1;
    }
    if (valid_r1) *valid_r1 = 0;
    // active stones = union of blockers
    u64 act = 0;
    for (int i = 0; i < nb; i++) act |= blockers[i];
    // tau = 2
    u64 a = act;
    while (a) {
        int r1 = __builtin_ctzll(a);
        a &= a - 1;
        u64 b = a; // avoid re-testing symmetric pairs
        while (b) {
            int r2 = __builtin_ctzll(b);
            b &= b - 1;
            u64 hit = (1ULL << r1) | (1ULL << r2);
            bool ok = true;
            for (int i = 0; i < nb; i++)
                if (!(blockers[i] & hit)) { ok = false; break; }
            if (ok) return 2;
        }
    }
    // tau = 3
    u64 c1 = act;
    while (c1) {
        int r1 = __builtin_ctzll(c1);
        c1 &= c1 - 1;
        u64 c2 = c1;
        while (c2) {
            int r2 = __builtin_ctzll(c2);
            c2 &= c2 - 1;
            u64 c3 = c2;
            while (c3) {
                int r3 = __builtin_ctzll(c3);
                c3 &= c3 - 1;
                u64 hit = (1ULL << r1) | (1ULL << r2) | (1ULL << r3);
                bool ok = true;
                for (int i = 0; i < nb; i++)
                    if (!(blockers[i] & hit)) { ok = false; break; }
                if (ok) return 3;
            }
        }
    }
    return 4; // fallback (should be rare / never for these boards)
}

// analyse one set: fills stats; optionally records swap edges
struct SwapEdge { int from, to, remove_p, add_p; };
static long long edges_unresolved = 0; // swaps whose destination was not in the set list

static void analyze_set(u64 S, const MaskMap &map, SetStats &st,
                        std::vector<SwapEdge> &edges) {
    u64 empties = ((N * N == 64) ? ~0ULL : ((1ULL << (N * N)) - 1)) & ~S;
    st.mask = S;
    st.canon = canonical_key(S);
    st.stab = stabilizer_size(S);
    st.orbit_size = 8 / st.stab;
    st.num_empty = __builtin_popcountll(empties);
    st.rho = 99;
    st.swap_pairs = 0;
    st.min_blockers = 1 << 30;
    st.max_blockers = 0;
    st.tau1_count = 0;
    for (int i = 0; i < 8; i++) st.v_with_tau[i] = 0;
    int self_id = map.get(S);
    (void)self_id;
    u64 e = empties;
    static u64 blockers[1024];
    while (e) {
        int v = __builtin_ctzll(e);
        e &= e - 1;
        int nb = 0;
        for (u64 o : triples_by_pt[v]) {
            if ((o & S) == o) {
                if (nb < 1024) blockers[nb++] = o;
            }
        }
        if (nb < st.min_blockers) st.min_blockers = nb;
        if (nb > st.max_blockers) st.max_blockers = nb;
        u64 valid_r1 = 0;
        int tau = tau_of(blockers, nb, S, &valid_r1);
        if (tau >= 1 && tau <= 6) st.v_with_tau[tau]++;
        if (tau < st.rho) st.rho = tau;
        if (tau == 1) {
            st.tau1_count++;
            u64 r = valid_r1;
            while (r) {
                int rr = __builtin_ctzll(r);
                r &= r - 1;
                u64 S2 = (S & ~(1ULL << rr)) | (1ULL << v);
                int to = map.get(S2);
                st.swap_pairs++;
                if (to >= 0 && self_id >= 0)
                    edges.push_back({self_id, to, rr, v});
                else
                    ++edges_unresolved;
            }
        }
    }
    st.swap_destinct = -1; // filled by caller after dedup
}

// ---- full analysis (per-set stats, swaps, components, cell frequency) ----
static int run_analyze(std::vector<u64> &sets, const char *prefix) {
    size_t cnt = sets.size();
    MaskMap map(cnt);
    for (size_t i = 0; i < cnt; i++) map.put(sets[i], (int)i);

    std::vector<SetStats> stats(cnt);
    std::vector<SwapEdge> edges;
    edges.reserve(cnt * 4);
    for (size_t i = 0; i < cnt; i++) analyze_set(sets[i], map, stats[i], edges);
    fprintf(stderr, "analyzed %zu sets, %zu swap edges\n", cnt, edges.size());

    // distinct swap destinations per set (edges are appended grouped by from)
    std::vector<int> distinct(cnt, 0);
    {
        size_t i = 0;
        std::vector<int> tmp;
        while (i < edges.size()) {
            int from = edges[i].from;
            tmp.clear();
            size_t j = i;
            while (j < edges.size() && edges[j].from == from) {
                int to = edges[j].to;
                bool dup = false;
                for (int t : tmp) if (t == to) { dup = true; break; }
                if (!dup) tmp.push_back(to);
                j++;
            }
            distinct[from] = (int)tmp.size();
            i = j;
        }
    }

    char path[512];
    snprintf(path, sizeof(path), "%s_exchange_n%d.csv", prefix, N);
    FILE *csv = fopen(path, "w");
    fprintf(csv, "id,canonical_key_hex,orbit_size,stabilizer,num_empty,rho,"
                 "swap_pairs,swap_destinct,tau1_empty,min_blockers,max_blockers,tau_hist\n");
    for (size_t i = 0; i < cnt; i++) {
        auto &s = stats[i];
        char hist[160] = {0};
        char part[32];
        for (int t = 1; t <= 6; t++) {
            if (s.v_with_tau[t]) {
                snprintf(part, sizeof(part), "%s%d:%d", hist[0] ? ";" : "", t, s.v_with_tau[t]);
                strncat(hist, part, sizeof(hist) - strlen(hist) - 1);
            }
        }
        fprintf(csv, "%zu,%016llx,%d,%d,%d,%d,%d,%d,%d,%d,%d,\"%s\"\n",
                i, (unsigned long long)s.canon, s.orbit_size, s.stab, s.num_empty,
                s.rho, s.swap_pairs, distinct[i], s.tau1_count,
                s.min_blockers, s.max_blockers, hist);
    }
    fclose(csv);
    fprintf(stderr, "wrote %s\n", path);

    // ---- swap edge list with canonical keys ----
    snprintf(path, sizeof(path), "%s_swap_edges_n%d.csv", prefix, N);
    csv = fopen(path, "w");
    fprintf(csv, "from_id,to_id,from_canon_hex,to_canon_hex,removed_point,removed_x,removed_y,"
                 "added_point,added_x,added_y\n");
    for (auto &e : edges) {
        fprintf(csv, "%d,%d,%016llx,%016llx,%d,%d,%d,%d,%d,%d\n",
                e.from, e.to,
                (unsigned long long)stats[e.from].canon,
                (unsigned long long)stats[e.to].canon,
                e.remove_p, e.remove_p % N, e.remove_p / N,
                e.add_p, e.add_p % N, e.add_p / N);
    }
    fclose(csv);
    fprintf(stderr, "wrote %s (%zu edges, %lld unresolved)\n", path, edges.size(), edges_unresolved);

    // ---- components of the 1-swap graph ----
    std::vector<std::vector<int>> adj(cnt);
    for (auto &e : edges) adj[e.from].push_back(e.to);
    std::vector<int> comp(cnt, -1);
    std::vector<long long> comp_sizes;
    for (size_t i = 0; i < cnt; i++) {
        if (comp[i] >= 0) continue;
        int cid = (int)comp_sizes.size();
        long long size = 0;
        std::vector<int> stack{(int)i};
        comp[i] = cid;
        while (!stack.empty()) {
            int u = stack.back();
            stack.pop_back();
            size++;
            for (int v : adj[u])
                if (comp[v] < 0) { comp[v] = cid; stack.push_back(v); }
        }
        comp_sizes.push_back(size);
    }
    snprintf(path, sizeof(path), "%s_exchange_components_n%d.csv", prefix, N);
    csv = fopen(path, "w");
    fprintf(csv, "component_id,size\n");
    for (size_t i = 0; i < comp_sizes.size(); i++)
        fprintf(csv, "%zu,%lld\n", i, comp_sizes[i]);
    fclose(csv);
    fprintf(stderr, "wrote %s (%zu components)\n", path, comp_sizes.size());

    // ---- cell frequency by D4 cell orbit ----
    std::vector<long long> freq(V, 0);
    for (size_t i = 0; i < cnt; i++) {
        u64 m = sets[i];
        while (m) {
            int p = __builtin_ctzll(m);
            m &= m - 1;
            freq[p]++;
        }
    }
    std::vector<int> cell_rep(V, -1);
    for (int p = 0; p < V; p++) {
        if (cell_rep[p] >= 0) continue;
        int rep = __builtin_ctzll(canonical_key(1ULL << p));
        for (int t = 0; t < 8; t++) cell_rep[d4_perm[t][rep]] = rep;
    }
    snprintf(path, sizeof(path), "%s_cell_frequency_n%d.csv", prefix, N);
    csv = fopen(path, "w");
    fprintf(csv, "point,x,y,orbit_rep_x,orbit_rep_y,orbit_size,freq,freq_per_orbit_avg\n");
    for (int p = 0; p < V; p++) {
        int rep = cell_rep[p];
        int osize = 0;
        for (int t = 0; t < 8; t++) if (d4_perm[t][rep] == rep) osize++;
        osize = 8 / osize;
        fprintf(csv, "%d,%d,%d,%d,%d,%d,%lld,%.4f\n",
                p, p % N, p / N, rep % N, rep / N, osize, freq[p],
                (double)freq[p] / (double)cnt);
    }
    fclose(csv);
    fprintf(stderr, "wrote %s\n", path);

    // ---- summary ----
    std::vector<long long> rho_hist(8, 0), swap_hist(16, 0), t1_hist(16, 0);
    std::vector<u64> orbit_keys;
    for (size_t i = 0; i < cnt; i++) {
        if (stats[i].rho >= 0 && stats[i].rho < 8) rho_hist[stats[i].rho]++;
        int sp = stats[i].swap_pairs;
        swap_hist[sp < 15 ? sp : 15]++;
        int t1 = stats[i].tau1_count;
        t1_hist[t1 < 15 ? t1 : 15]++;
        orbit_keys.push_back(stats[i].canon);
    }
    std::sort(orbit_keys.begin(), orbit_keys.end());
    orbit_keys.erase(std::unique(orbit_keys.begin(), orbit_keys.end()), orbit_keys.end());

    printf("{\n  \"n\": %d,\n  \"K\": %d,\n  \"count\": %zu,\n  \"d4_orbits\": %zu,\n",
           N, g_target, cnt, orbit_keys.size());
    printf("  \"rho_hist\": {");
    {
        bool f1 = true;
        for (int r = 0; r < 8; r++)
            if (rho_hist[r]) { printf("%s\"%d\": %lld", f1 ? "" : ", ", r, rho_hist[r]); f1 = false; }
    }
    printf("},\n  \"swap_pairs_hist\": {");
    {
        bool f1 = true;
        for (int r = 0; r < 16; r++)
            if (swap_hist[r]) { printf("%s\"%d%s\": %lld", f1 ? "" : ", ", r, r == 15 ? "+" : "", swap_hist[r]); f1 = false; }
    }
    printf("},\n  \"tau1_empty_hist\": {");
    {
        bool f1 = true;
        for (int r = 0; r < 16; r++)
            if (t1_hist[r]) { printf("%s\"%d%s\": %lld", f1 ? "" : ", ", r, r == 15 ? "+" : "", t1_hist[r]); f1 = false; }
    }
    printf("},\n  \"components\": %zu,\n  \"component_size_hist\": {", comp_sizes.size());
    {
        std::sort(comp_sizes.begin(), comp_sizes.end());
        size_t i = 0;
        bool first = true;
        while (i < comp_sizes.size()) {
            size_t j = i;
            while (j < comp_sizes.size() && comp_sizes[j] == comp_sizes[i]) j++;
            printf("%s\"%lld\": %zu", first ? "" : ", ", comp_sizes[i], j - i);
            first = false;
            i = j;
        }
    }
    printf("}\n}\n");
    return 0;
}

// ---- main ----
static u64 full_mask() { return (N * N == 64) ? ~0ULL : ((1ULL << (N * N)) - 1); }

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s count|enum|analyze n K [out.bin|in.bin prefix]\n", argv[0]);
        return 2;
    }
    const char *mode = argv[1];
    N = atoi(argv[2]);
    g_target = atoi(argv[3]);
    build_geometry();
    build_d4();
    fprintf(stderr, "n=%d V=%d quads=%d K=%d\n", N, V, n_quads_total, g_target);

    if (strcmp(mode, "count") == 0) {
        dfs_enum(full_mask(), 0);
        printf("{\"n\": %d, \"K\": %d, \"count\": %lld, \"nodes\": %lld}\n",
               N, g_target, n_found, node_count);
        return 0;
    }

    if (strcmp(mode, "enum") == 0) {
        if (argc < 5) { fprintf(stderr, "need out.bin\n"); return 2; }
        std::vector<u64> sets;
        out_sets = &sets;
        dfs_enum(full_mask(), 0);
        out_sets = nullptr;
        FILE *f = fopen(argv[4], "wb");
        if (!f) { fprintf(stderr, "cannot write %s\n", argv[4]); return 1; }
        fwrite(sets.data(), sizeof(u64), sets.size(), f);
        fclose(f);
        printf("{\"n\": %d, \"K\": %d, \"count\": %lld, \"nodes\": %lld, \"file\": \"%s\"}\n",
               N, g_target, n_found, node_count, argv[4]);
        return 0;
    }

    if (strcmp(mode, "analyze") == 0) {
        if (argc < 6) { fprintf(stderr, "need in.bin prefix\n"); return 2; }
        FILE *f = fopen(argv[4], "rb");
        if (!f) { fprintf(stderr, "cannot read %s\n", argv[4]); return 1; }
        fseek(f, 0, SEEK_END);
        long long sz = ftell(f);
        fseek(f, 0, SEEK_SET);
        size_t cnt = (size_t)(sz / sizeof(u64));
        std::vector<u64> sets(cnt);
        if (fread(sets.data(), sizeof(u64), cnt, f) != cnt) {
            fprintf(stderr, "short read\n");
            return 1;
        }
        fclose(f);
        fprintf(stderr, "loaded %zu sets\n", cnt);
        return run_analyze(sets, argv[5]);
    }

    fprintf(stderr, "unknown mode %s\n", mode);
    return 2;
}

