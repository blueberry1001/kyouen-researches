// n11_pipe.cpp -- disk-resident, spill-based layer pipeline for the kyouen game.
//
// Replaces the load-both-levels-in-RAM approach of n11_enum121.cpp, which died
// with std::bad_alloc at n=11 level 6 (level 5 alone is 3.0 GB and level 6
// needs several more GB in the same address space).
//
// One level transition k -> k+1 is four passes over the data:
//
//   A (gen)   level_k.bin is streamed in chunks of --chunk states (the only
//             thing in RAM).  Each chunk is swept once per v in [0,V); legal
//             children whose top point is v are emitted into a flat, v-ordered
//             buffer and written to seg_<c>.bin, with the per-v record counts
//             in seg_<c>.idx.  Chunks are independent, so this pass is
//             OpenMP-parallel over c with no shared mutable state.
//   B (cat)   seg files are concatenated per v into blk_<v>.bin, parallel over
//             v.  Because the chunks are in ascending state order and each
//             chunk's v-block is ascending, the concatenation is ascending:
//             blk_<v>.bin is sorted without ever sorting anything.
//   C (merge) the V sorted blk files are merged with a V-way heap (V entries,
//             buffer path length x Buf) into level_{k+1}.bin.
//
// Peak RAM = one chunk (16 B/state) x nthreads + V merge buffers.  A whole
// level is never resident.
//
//   g++ -O2 -march=native -std=c++20 -pthread -fopenmp -o n11_pipe n11_pipe.cpp
//
// Why a chunk is sorted without a sort pass: the key is the 128-bit value
// (hi, lo) = the point set in lexicographic order, and setting a bit only ever
// increases a word, so for a fixed v the order of parents is the order of
// children.  blk_v is therefore produced in ascending order.  --checkmerge
// re-checks this exactly, per chunk and per v, at run time, and aborts if the
// invariant is ever violated.
//
// Legality, O(1) amortised per (state, v).  Within a chunk the v loop carries
// a status word per point:
//     entry[p] (lo word for p < 64, hi word otherwise) == 1<<p  means "p is
//     free and worth testing"; any other value means "p is occupied" and its
//     value is the accumulated occupied mask of that half.  A child is safe
//     iff no point of it is part of a forbidden 4-set, and
//     "some point of C is in a forbidden 4-set" is monotone in C, so testing
//     every point of the finished child against the finished child is exactly
//     equivalent to the incremental "is the new move legal" test.  After
//     processing v the entry is set to the child's own mask, so the check
//     for a later v is a single bit test plus a subset test.
#include "kc_core121.h"

#include <algorithm>
#include <cerrno>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/types.h>
#include <unistd.h>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

using kc::u64;
using kc::Bits;
using kc::Board;

// ---------------------------------------------------------------- utilities
static double now_s() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

static long rss_mb() {
    FILE* f = fopen("/proc/self/status", "r");
    if (!f) return -1;
    char line[256];
    long v = -1;
    while (fgets(line, sizeof line, f))
        if (!strncmp(line, "VmHWM:", 6)) { sscanf(line + 6, "%ld", &v); break; }
    fclose(f);
    return v / 1024;
}

static u64 free_bytes(const char* p) {
    struct statvfs st;
    if (statvfs(p, &st) != 0) return 0;
    return (u64)st.f_bavail * (u64)st.f_frsize;
}

static bool make_dir(const std::string& d) {
    if (mkdir(d.c_str(), 0755) == 0) return true;
    return errno == EEXIST;
}

static u64 ceil_div(u64 a, u64 b) { return a / b + (a % b ? 1 : 0); }

static std::string human(u64 bytes) {
    char b[64];
    if (bytes >= (1ull << 30)) snprintf(b, sizeof b, "%.1f GiB", (double)bytes / (1ull << 30));
    else if (bytes >= (1ull << 20)) snprintf(b, sizeof b, "%.1f MiB", (double)bytes / (1ull << 20));
    else snprintf(b, sizeof b, "%llu B", (unsigned long long)bytes);
    return std::string(b);
}

// Sequential (single-threaded) streaming helper.  `fn(off, raw, len)` sees a
// raw buffer of 2*len u64 words holding (lo, hi) pairs, 8 B per state.
struct LevelFile {
    std::string path;
    explicit LevelFile(std::string p) : path(std::move(p)) {}
    u64 header() const {
        FILE* f = fopen(path.c_str(), "rb");
        if (!f) { fprintf(stderr, "pipe: cannot open %s\n", path.c_str()); exit(9); }
        u64 c = 0;
        if (fread(&c, 8, 1, f) != 1) { fclose(f); fprintf(stderr, "pipe: no header %s\n", path.c_str()); exit(9); }
        fclose(f);
        return c;
    }
};

static void read_chunk(const std::string& path, u64 off, u64 len, std::vector<u64>& raw) {
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) { fprintf(stderr, "pipe: cannot open %s\n", path.c_str()); exit(9); }
    if (fseeko(f, (off_t)(8 + 16 * off), SEEK_SET) != 0) {
        fclose(f); fprintf(stderr, "pipe: seek off %" PRIu64 "\n", off); exit(9);
    }
    raw.resize((size_t)len * 2);
    if (len && fread(raw.data(), 8, (size_t)len * 2, f) != (size_t)len * 2) {
        fclose(f);
        fprintf(stderr, "pipe: short chunk read off=%" PRIu64 " want=%zu\n", off, (size_t)len * 2);
        exit(9);
    }
    fclose(f);
}

// ------------------------------------------------------------------ options
struct Options {
    int n = 0;
    bool quads_only = false;
    std::string dir = "/tmp/n11_pipe";
    long maxlevel = 1L << 30;
    u64 chunk = 1ull << 22;        // states per chunk, 16 B each in RAM
    long threads = 0;              // 0 = all cores
    bool checkmerge = false;
    long memgb = 12;               // RAM budget, used to bound chunk x threads
    long minfreegb = 120;          // stop below this much free space
    std::string start;             // copy this file in as level 0 (resume)
    std::string check;             // --check mode
};

static int do_check(const std::string& path) {
    LevelFile lf(path);
    u64 c = lf.header();
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) { fprintf(stderr, "pipe: cannot open %s\n", path.c_str()); return 9; }
    std::vector<u64> raw((size_t)2 * (1u << 19));
    u64 off = 0, prev_hi = 0, prev_lo = 0, recs = 0, dups = 0;
    bool first = true, sorted = true;
    while (off < c) {
        u64 len = (c - off < (1u << 19)) ? c - off : (1u << 19);
        if (fread(raw.data(), 8, (size_t)len * 2, f) != (size_t)len * 2) {
            printf("{\"file\": \"%s\", \"ok\": false, \"error\": \"short read at %llu\"}\n",
                   path.c_str(), (unsigned long long)off);
            fclose(f);
            return 9;
        }
        for (u64 i = 0; i < len; ++i) {
            // On disk the pair is (lo, hi); the ORDER is (hi, lo), i.e. hi
            // compared first.  Comparing lo first would validate the wrong
            // key and silently accept an unsorted level.
            u64 lo = raw[2 * (size_t)i], hi = raw[2 * (size_t)i + 1];
            if (!first) {
                if (hi == prev_hi && lo == prev_lo) ++dups;
                else if (!(prev_hi < hi || (prev_hi == hi && prev_lo < lo))) sorted = false;
            }
            prev_hi = hi; prev_lo = lo; first = false; ++recs;
        }
        off += len;
    }
    fclose(f);
    bool ok = (sorted && recs == c);
    printf("{\"file\": \"%s\", \"header_count\": %llu, \"records\": %llu, "
           "\"bytes\": %llu, \"file_bytes\": %llu, \"sorted\": %s, \"dups\": %llu, \"ok\": %s}\n",
           path.c_str(), (unsigned long long)c, (unsigned long long)recs,
           (unsigned long long)(16 * c), (unsigned long long)(8 + 16 * c),
           sorted ? "true" : "false", (unsigned long long)dups, ok ? "true" : "false");
    return ok ? 0 : 9;
}

int main(int argc, char** argv) {
    Options o;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--enum") { if (i + 1 < argc) o.n = atoi(argv[++i]); }
        else if (a == "--quads") o.quads_only = true;
        else if (a.rfind("--dir=", 0) == 0) o.dir = a.substr(6);
        else if (a == "--dir") { if (i + 1 < argc) o.dir = argv[++i]; }
        else if (a.rfind("--maxlevel=", 0) == 0) o.maxlevel = atol(a.c_str() + 11);
        else if (a == "--maxlevel") { if (i + 1 < argc) o.maxlevel = atol(argv[++i]); }
        else if (a.rfind("--chunk=", 0) == 0) o.chunk = strtoull(a.c_str() + 8, nullptr, 10);
        else if (a.rfind("--threads=", 0) == 0) o.threads = atol(a.c_str() + 10);
        else if (a == "--checkmerge") o.checkmerge = true;
        else if (a.rfind("--memgb=", 0) == 0) o.memgb = atol(a.c_str() + 8);
        else if (a.rfind("--minfreegb=", 0) == 0) o.minfreegb = atol(a.c_str() + 13);
        else if (a.rfind("--start=", 0) == 0) o.start = a.substr(8);
        else if (a == "--check") { if (i + 1 < argc) o.check = argv[++i]; }
        else { fprintf(stderr, "pipe: unknown arg %s\n", a.c_str()); return 2; }
    }

    if (!o.check.empty()) return do_check(o.check);
    if (o.n <= 0) {
        fprintf(stderr,
                "usage: --enum <n> [--dir=DIR] [--maxlevel K] [--chunk=LM] [--threads=T]\n"
                "          [--start=FILE] [--checkmerge] [--memgb=X] [--minfreegb=X]\n"
                "       --quads <n>\n       --check FILE\n");
        return 2;
    }
    if (o.n * o.n > 128) { fprintf(stderr, "pipe: n*n must be <= 128\n"); return 2; }

    double t0 = now_s();
    Board B;
    kc::build_square(B, o.n);
    long long c4 = 1;
    for (int i = 0; i < 4; ++i) c4 = c4 * (B.V - 3 + i) / (i + 1);
    fprintf(stderr, "[n=%d] V=%d C(V,4)=%lld F=%zu build %.1fs rss=%ldMB\n",
            o.n, B.V, c4, B.quads.size(), now_s() - t0, rss_mb());
    fflush(stderr);
    if (o.quads_only) {
        printf("{\"n\": %d, \"V\": %d, \"F\": %zu, \"C_V_4\": %lld, \"build_seconds\": %.2f}\n",
               o.n, B.V, B.quads.size(), c4, now_s() - t0);
        return 0;
    }

    if (!make_dir(o.dir)) { fprintf(stderr, "pipe: mkdir %s failed\n", o.dir.c_str()); return 9; }
    sync();   // a multi-hundred-GB write must not live only in the 19 GB cache

    const int V = B.V;
    const int SL = (V < 64) ? V : 64;          // points living in the lo word
    auto level_path = [&](int k) { return o.dir + "/level_" + std::to_string(k) + ".bin"; };
    auto seg_path   = [&](long c) { return o.dir + "/seg_"   + std::to_string(c) + ".bin"; };
    auto segidx_path= [&](long c) { return o.dir + "/seg_"   + std::to_string(c) + ".idx"; };
    auto blk_path   = [&](int v)  { return o.dir + "/blk_"   + std::to_string(v) + ".bin"; };
    const std::vector<std::vector<Bits>>& tpp = B.triples_by_pt;

    int nthreads = o.threads > 0 ? (int)o.threads
                                 : (omp_get_max_threads() > 0 ? omp_get_max_threads() : 1);
    u64 chunk = o.chunk;
    if (o.memgb > 0) {
        // keep chunk x threads inside the RAM budget: 16 B read + ~40 B emitted
        u64 per_state = 16 + 40;
        u64 cap = ((u64)o.memgb << 30) / (per_state * (u64)nthreads);
        if (chunk > cap) chunk = cap;
    }
    if (chunk < 1024) chunk = 1024;
    u64 merge_buf = (512ull << 20) / ((u64)V * 16ull);      // states per run
    if (merge_buf < 4096) merge_buf = 4096;
    fprintf(stderr, "[pipe] dir=%s chunk=%" PRIu64 " (%.0f MB) threads=%d merge_buf=%" PRIu64
                    " checkmerge=%d\n",
            o.dir.c_str(), chunk, chunk * 16.0 / (1 << 20), nthreads, merge_buf,
            (int)o.checkmerge);
    fflush(stderr);

    // ------------------------------------------------------------- level 0
    std::vector<size_t> sizes;
    u64 total = 0;
    {
        std::string p = level_path(0);
        FILE* f = fopen(p.c_str(), "wb");
        if (!f) { fprintf(stderr, "pipe: cannot write %s\n", p.c_str()); return 9; }
        Bits zero{0, 0};
        u64 c = 1;
        fwrite(&c, 8, 1, f);
        fwrite(&zero.lo, 8, 1, f);
        fwrite(&zero.hi, 8, 1, f);
        fclose(f);
        if (!o.start.empty()) {
            LevelFile src(o.start);
            u64 c0 = src.header();
            FILE* g = fopen(o.start.c_str(), "rb");
            if (!g) { fprintf(stderr, "pipe: cannot read --start\n"); return 9; }
            f = fopen(p.c_str(), "wb");
            if (fwrite(&c0, 8, 1, f) != 1) { fclose(g); fclose(f); fprintf(stderr, "pipe: hdr\n"); return 9; }
            std::vector<u64> tmp(1 << 16);
            for (u64 off = 0; off < c0; ) {
                u64 len = (c0 - off < (1u << 15)) ? c0 - off : (1u << 15);
                if (fread(tmp.data(), 8, (size_t)len * 2, g) != (size_t)len * 2) {
                    fclose(g); fclose(f); fprintf(stderr, "pipe: short --start read\n"); return 9;
                }
                fwrite(tmp.data(), 8, (size_t)len * 2, f);
                off += len;
            }
            fclose(g);
            fclose(f);
            c = c0;
            fprintf(stderr, "[pipe] resumed level 0 from %s (%" PRIu64 " states)\n", o.start.c_str(), c);
        }
        sizes.push_back((size_t)c);
        total = c;
        fprintf(stderr, "  level 0: %" PRIu64 " states (%.1fs)\n", c, now_s() - t0);
        fflush(stderr);
    }

    long peak_rss = rss_mb();
    long widest_level = 0, widest_k = -1;
    u64 widest_bytes = 0;
    double widest_secs = 0;
    std::string stop_reason = "maxlevel";
    bool stopped_disk = false;
    double growth = 1.0;

    // ============================================================ pipeline
    for (long k = 0; k < o.maxlevel; ++k) {
        int nk = (int)k + 1;
        double tk = now_s();
        LevelFile cur(level_path((int)k));
        u64 cur_n = cur.header();
        if (cur_n == 0) { stop_reason = "empty_level"; break; }

        // --- capacity gate.  One transition writes seg (8 B/state) + blk
        //     (8 B/state) + level_{k+1} (16 B/state) of the *next* level, so
        //     32 B/state times the estimated next-level size.  Estimate with
        //     the last observed growth ratio; below the threshold we stop
        //     cleanly instead of filling the filesystem.
        u64 est_next = (u64)((double)cur_n * (growth < 1.0 ? 1.0 : growth));
        u64 need = 32ull * est_next + (2ull << 30);
        u64 freeb = free_bytes(o.dir.c_str());
        if (freeb < ((u64)o.minfreegb << 30) || freeb < need) {
            stopped_disk = true;
            stop_reason = "disk_full";
            fprintf(stderr,
                    "[pipe] STOP before level %d: need ~%s (32 B/state x %" PRIu64
                    " estimated states) + 2 GiB slack, have %s free, minfree=%ld GiB. "
                    "No further writes issued.\n",
                    nk, human(need).c_str(), est_next, human(freeb).c_str(), o.minfreegb);
            fflush(stderr);
            break;
        }

        u64 nch = ceil_div(cur_n, chunk);
        double tA0 = now_s();

        // counts[c*V + v] = number of children emitted by chunk c into block v
        std::vector<u64> counts((size_t)(nch * V), 0);
        // The emit loop must run v ASCENDING, because the fixed point
        // (flo/fhi) that makes legality O(1) is only valid when every u < v has
        // already been processed.  So the permutation below is applied purely to
        // the ORDER IN WHICH THE V BLOCKS ARE WRITTEN AND LATER CONCATENATED,
        // never to the order children are generated in.
        //
        // blk_v must be ascending, and the k-way merge only produces a sorted
        // level if consecutive blocks are themselves mutually ordered.  Block v
        // holds children whose top point is v, i.e. bit v set and no higher
        // bit, so every value in block v is confined to a leading range:
        //     v >= 64 : hi has bit v-64 set and nothing above it, hi = 0 below
        //                => hi in [2^(v-64), 2^(v-63)),  ASCENDING as v rises
        //     v <  64 : hi = 0 (no point >= 64 present) and lo has bit v set
        //                with nothing above it
        //                => lo in [2^v, 2^(v+1)),        ASCENDING as v rises
        // and every v >= 64 block has hi >= 1, so it sits strictly above every
        // v <  64 block, whose hi is 0.  The two rules agree, so the blocks are
        // mutually ordered and mutually disjoint exactly in ASCENDING v:
        //     v = 0, 1, 2, ..., V-1
        // which is why concatenating in ascending v and V-way merging yields a
        // sorted level with no sort pass anywhere.
        std::vector<int> vmap((size_t)V);      // vmap[slot] = v, ascending blocks
        {
            int w = 0;
            for (int v = 0; v < V; ++v) vmap[(size_t)w++] = v;
        }
        // Chunks are independent, so pass A is OpenMP-parallel over c.  Under
        // --checkmerge a second counting pass predicts the same counts, so any
        // divergence between prediction and emission is a hard error; the
        // ascending-order proofs are checked at the block level in pass C,
        // where the merged layout actually exists.
        int nthreads_gen = o.checkmerge ? 1 : nthreads;
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1) num_threads(nthreads_gen)
#endif
        for (long c = 0; c < (long)nch; ++c) {
            u64 off = (u64)c * chunk;
            u64 len = (cur_n - off < chunk) ? (cur_n - off) : chunk;
            std::vector<u64> raw;
            read_chunk(level_path((int)k), off, len, raw);
            // On disk the records are INTERLEAVED (lo, hi, lo, hi, ...), so
            // the i-th state is at raw[2i], raw[2i+1].  Reading it as a
            // deinterleaved block (all lo then all hi) silently transposes the
            // two words for every state, which for v < 64 shows up as a
            // point landing in the wrong block and as a descending level.
            const long L = (long)len;
            auto LO = [&](long i) { return raw[2 * i]; };
            auto HI = [&](long i) { return raw[2 * i + 1]; };

            std::vector<u64> flo((size_t)V), fhi((size_t)V);
            std::vector<std::vector<u64>> obuf((size_t)V);
            std::vector<u64> cnt((size_t)V, 0);
            for (int p = 0; p < SL; ++p) flo[(size_t)p] = u64(1) << p;
            for (int p = SL; p < V; ++p) fhi[(size_t)p] = u64(1) << (p - 64);
            if (SL < V) for (int p = 0; p < V; ++p) { /* flo[SL..V-1] unused */ }

            for (int v = 0; v < V; ++v) {
                const u64 vlo = (v < SL) ? (u64(1) << v) : 0ull;
                const u64 vhi = (v >= 64) ? (u64(1) << (v - 64)) : 0ull;
                // Counting pass (only under --checkmerge) so the emit pass can
                // be reserved exactly, exercising the growth path honestly.
                // It must be a pure function of the PARENT: flo/fhi carry the
                // fixed-point state of the emit loop, so they are read as
                // "p is a parent point" = entry != 1<<p, which is exactly the
                // semantics the emit pass assigns.  Touching them here would
                // desynchronise the two passes and corrupt the segment layout.
                if (o.checkmerge) {
                    for (long i = 0; i < L; ++i) {
                        const u64 lv = LO(i), hv = HI(i);
                        if (hv > vhi || (hv == vhi && lv >= vlo)) continue;
                        const u64 nhi = hv | vhi, nlo = lv | vlo;
                        bool dead = false;
                        for (int s = 64; s < V && !dead; ++s) {
                            if (!(nhi & fhi[(size_t)s])) continue;
                            for (const Bits& t : tpp[(size_t)s])
                                if ((t.lo & ~nlo) == 0 && (t.hi & ~nhi) == 0) { dead = true; break; }
                        }
                        if (!dead)
                            for (int s = 0; s < SL && !dead; ++s) {
                                if (!(nlo & flo[(size_t)s])) continue;
                                for (const Bits& t : tpp[(size_t)s])
                                    if ((t.lo & ~nlo) == 0 && (t.hi & ~nhi) == 0) { dead = true; break; }
                            }
                        if (!dead) ++cnt[(size_t)v];
                    }
                    obuf[(size_t)v].reserve((size_t)cnt[(size_t)v] * 2);
                }
                for (long i = 0; i < L; ++i) {
                    const u64 lv = LO(i), hv = HI(i);
                    // v is the TOP point of the child => the parent carries no
                    // point >= v, i.e. parent < bit(v).  Emitting when only
                    // "parent does not contain v" would re-emit the same child
                    // at the parent's own top point, and the level would come
                    // out both unsorted and duplicated.
                    if (hv > vhi || (hv == vhi && lv >= vlo)) continue;
                    const u64 nhi = hv | vhi, nlo = lv | vlo;
                    bool dead = false;
                    for (int s = 64; s < V && !dead; ++s) {
                        if (!(nhi & fhi[(size_t)s])) continue;
                        for (const Bits& t : tpp[(size_t)s])
                            if ((t.lo & ~nlo) == 0 && (t.hi & ~nhi) == 0) { dead = true; break; }
                    }
                    if (!dead)
                        for (int s = 0; s < SL && !dead; ++s) {
                            if (!(nlo & flo[(size_t)s])) continue;
                            for (const Bits& t : tpp[(size_t)s])
                                if ((t.lo & ~nlo) == 0 && (t.hi & ~nhi) == 0) { dead = true; break; }
                        }
                    if (dead) continue;
                    obuf[(size_t)v].push_back(nlo);
                    obuf[(size_t)v].push_back(nhi);
                    // v is now occupied: remember the child's own masks
                    if (v < SL) flo[(size_t)v] = nlo; else fhi[(size_t)v] = nhi;
                }
                if (o.checkmerge) {
                    // Within one chunk, children of a fixed v come out in
                    // ascending order because the parent sweep is ascending and
                    // setting a bit preserves order.  Verified, not assumed.
                    const std::vector<u64>& b = obuf[(size_t)v];
                    for (size_t j = 2; j + 1 < b.size(); j += 2) {
                        Bits p0{b[j - 1], b[j - 2]}, c0{b[j + 1], b[j]};
                        if (!(p0 < c0)) {
                            fprintf(stderr,
                                    "[pipe] CHECKMERGE FAIL: blk_%d not ascending within "
                                    "chunk %ld\n", v, c);
                            exit(9);
                        }
                    }
                }
            }
            // `counts` is what the concatenate and merge passes trust, so it is
            // always taken from the actual buffer length.  The --checkmerge
            // counting pass is an independent prediction that must agree; a
            // disagreement means the reserved size or the layout is wrong.
            for (int v = 0; v < V; ++v) {
                u64 actual = obuf[(size_t)v].size() / 2;
                if (o.checkmerge && actual != cnt[(size_t)v]) {
                    fprintf(stderr,
                            "[pipe] COUNT MISMATCH blk_%d: predicted %" PRIu64
                            " emitted %" PRIu64 "\n", v, cnt[(size_t)v], actual);
                    exit(9);
                }
                counts[(size_t)((u64)c * V + v)] = actual;
                cnt[(size_t)v] = actual;
            }

            // Write the chunk's flat segment in vmap order: slot w holds the
            // children whose top point is vmap[w].  Slot order, not v order, is
            // what makes the per-v concatenation ascend.
            std::string sp = seg_path(c), ip = segidx_path(c);
            FILE* f = fopen(sp.c_str(), "wb");
            if (!f) { fprintf(stderr, "pipe: cannot write %s\n", sp.c_str()); exit(9); }
            for (int w = 0; w < V; ++w) {
                const std::vector<u64>& b = obuf[(size_t)vmap[(size_t)w]];
                if (b.empty()) continue;
                if (fwrite(b.data(), 8, b.size(), f) != b.size()) {
                    fprintf(stderr, "pipe: short seg write %s\n", sp.c_str()); exit(9);
                }
            }
            fclose(f);
            f = fopen(ip.c_str(), "wb");
            if (!f) { fprintf(stderr, "pipe: cannot write %s\n", ip.c_str()); exit(9); }
            for (int w = 0; w < V; ++w) {
                u64 n = cnt[(size_t)vmap[(size_t)w]];
                if (fwrite(&n, 8, 1, f) != 1) { fprintf(stderr, "pipe: idx write\n"); exit(9); }
            }
            fclose(f);
        }
        double tA = now_s() - tA0;

        u64 emitted = 0;
        for (u64 i = 0; i < (u64)nch * V; ++i) emitted += counts[(size_t)i];
        double tB0 = now_s();

        // ------------------------------------- B: concatenate per v (sorted)
        // Segment slot w holds the v-block vmap[w], so blk_v is the byte-wise
        // concatenation over chunks c of slot slotof[v] of seg_<c>.  Since the
        // chunks ascend and each slot is itself ascending, and adjacent slots
        // ascend by the vmap argument, the result is ascending.
        std::vector<int> slotof((size_t)V);
        for (int w = 0; w < V; ++w) slotof[(size_t)vmap[(size_t)w]] = w;
        std::vector<u64> off_in_seg((size_t)nch * (V + 1), 0);
        for (long c = 0; c < (long)nch; ++c) {
            u64 acc = 0;
            for (int w = 0; w < V; ++w) {
                off_in_seg[(size_t)c * (V + 1) + w] = acc;
                acc += counts[(size_t)((u64)c * V + vmap[(size_t)w])];
            }
            off_in_seg[(size_t)c * (V + 1) + V] = acc;
        }
        std::vector<u64> bcnt((size_t)V, 0);
        for (long c = 0; c < (long)nch; ++c)
            for (int v = 0; v < V; ++v) bcnt[(size_t)v] += counts[(size_t)((u64)c * V + v)];

        const long cbuf_states = 1u << 17;    // 2 MiB per copy buffer
        int cthreads = (int)std::min<long>((long)nthreads, (long)V);
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1) num_threads(cthreads)
#endif
        for (int v = 0; v < V; ++v) {
            std::string bp = blk_path(v);
            FILE* f = fopen(bp.c_str(), "wb");
            if (!f) { fprintf(stderr, "pipe: cannot write %s\n", bp.c_str()); exit(9); }
            if (bcnt[(size_t)v] == 0) { fclose(f); continue; }
            std::vector<u64> tmp((size_t)cbuf_states * 2);
            for (long c = 0; c < (long)nch; ++c) {
                u64 n = counts[(size_t)((u64)c * V + v)];
                if (!n) continue;
                FILE* g = fopen(seg_path(c).c_str(), "rb");
                if (!g) { fprintf(stderr, "pipe: reopen %s\n", seg_path(c).c_str()); exit(9); }
                if (fseeko(g, (off_t)(8 * off_in_seg[(size_t)c * (V + 1) + slotof[v]]), SEEK_SET) != 0) {
                    fclose(g); fprintf(stderr, "pipe: seg seek\n"); exit(9);
                }
                for (u64 d = 0; d < n; ) {
                    u64 want = (n - d < (u64)cbuf_states) ? n - d : (u64)cbuf_states;
                    if (fread(tmp.data(), 8, (size_t)want * 2, g) != (size_t)want * 2) {
                        fclose(g); fprintf(stderr, "pipe: short seg read v=%d c=%ld\n", v, c); exit(9);
                    }
                    if (fwrite(tmp.data(), 8, (size_t)want * 2, f) != (size_t)want * 2) {
                        fclose(g); fprintf(stderr, "pipe: short blk write v=%d\n", v); exit(9);
                    }
                    d += want;
                }
                fclose(g);
            }
            fclose(f);
        }
        double tB = now_s() - tB0;
        for (long c = 0; c < (long)nch; ++c) {   // segments are now redundant
            remove(seg_path(c).c_str());
            remove(segidx_path(c).c_str());
        }

        // --------------------------------------------- C: V-way heap merge
        double tC0 = now_s();
        std::vector<FILE*> fh((size_t)V, nullptr);
        std::vector<std::vector<u64>> buf((size_t)V);
        std::vector<u64> bpos((size_t)V, 0), bcap((size_t)V, 0), left((size_t)V, 0);
        std::vector<int> heap;
        heap.reserve((size_t)V);
        // Fills the current run buffer of v from its block file.  Records still
        // unread in the file are counted in left[]; records in the buffer are
        // counted in bcap[].  Returns false when the block is exhausted.
        auto refill = [&](int v) {
            u64 want = (left[(size_t)v] < merge_buf) ? left[(size_t)v] : merge_buf;
            if (want) {
                if (fread(buf[(size_t)v].data(), 8, (size_t)want * 2, fh[(size_t)v]) != (size_t)want * 2) {
                    fprintf(stderr, "pipe: short merge read blk_%d\n", v); exit(9);
                }
                left[(size_t)v] -= want;
            }
            bpos[(size_t)v] = 0;
            bcap[(size_t)v] = want;
            return want > 0;
        };
        // std::make_heap/pop_heap build a MAX-heap for a `less` comparator:
        // pop order came out 9,5,3,1 in a standalone test, i.e. DESCENDING.
        // The merge needs ASCENDING, so the comparator is a `greater`, and the
        // block indices are used directly as the heap elements.
        auto hless = [&](int a, int b) {
            const std::vector<u64>& A = buf[(size_t)a];
            const std::vector<u64>& C = buf[(size_t)b];
            u64 ah = A[2 * bpos[(size_t)a] + 1], al = A[2 * bpos[(size_t)a]];
            u64 bh = C[2 * bpos[(size_t)b] + 1], bl = C[2 * bpos[(size_t)b]];
            if (ah != bh) return ah > bh;
            return al > bl;
        };
        for (int v = 0; v < V; ++v) {
            if (bcnt[(size_t)v] == 0) continue;
            fh[(size_t)v] = fopen(blk_path(v).c_str(), "rb");
            if (!fh[(size_t)v]) { fprintf(stderr, "pipe: reopen blk_%d\n", v); exit(9); }
            buf[(size_t)v].resize((size_t)merge_buf * 2);
            left[(size_t)v] = bcnt[(size_t)v];
            if (refill(v)) heap.push_back(v);
        }
        // The heap is a k-way merge, so it only yields a sorted level if the
        // block files are sorted AND mutually ordered along vmap.  Verify both
        // directly: each block's first value, and the first values of adjacent
        // slots, must ascend.
        if (o.checkmerge) {
            for (int w = 0; w + 1 < V; ++w) {
                int va = vmap[(size_t)w], vb = vmap[(size_t)w + 1];
                if (!bcnt[(size_t)va] || !bcnt[(size_t)vb]) continue;
                u64 ahi = buf[(size_t)va][1], alo = buf[(size_t)va][0];
                u64 bhi = buf[(size_t)vb][1], blo = buf[(size_t)vb][0];
                // va's smallest member must be below vb's smallest member
                if (!(ahi < bhi || (ahi == bhi && alo < blo))) {
                    fprintf(stderr,
                            "[pipe] CHECKMERGE FAIL: blk_%d and blk_%d are not ordered "
                            "along vmap (slot %d: %016" PRIx64 "/%016" PRIx64 " vs %016" PRIx64
                            "/%016" PRIx64 ")\n",
                            va, vb, w, ahi, alo, bhi, blo);
                    exit(9);
                }
            }
        }
        std::make_heap(heap.begin(), heap.end(), hless);

        std::string outp = level_path(nk);
        FILE* out = fopen(outp.c_str(), "wb");
        if (!out) { fprintf(stderr, "pipe: cannot write %s\n", outp.c_str()); return 9; }
        u64 zero = 0;
        if (fwrite(&zero, 8, 1, out) != 1) { fclose(out); fprintf(stderr, "pipe: hdr\n"); return 9; }
        u64 merged = 0;
        std::vector<u64> wbuf;
        wbuf.reserve((size_t)merge_buf * 2);
        while (!heap.empty()) {
            std::pop_heap(heap.begin(), heap.end(), hless);
            int v = heap.back();
            heap.pop_back();
            wbuf.push_back(buf[(size_t)v][2 * bpos[(size_t)v]]);
            wbuf.push_back(buf[(size_t)v][2 * bpos[(size_t)v] + 1]);
            ++bpos[(size_t)v];
            ++merged;
            // run buffer exhausted: pull the next run from this block
            if (bpos[(size_t)v] >= bcap[(size_t)v]) {
                if (refill(v)) {
                    std::push_heap(heap.begin(), heap.end(), hless);
                }
            }
            if (wbuf.size() >= (size_t)merge_buf * 2) {
                if (fwrite(wbuf.data(), 8, wbuf.size(), out) != wbuf.size()) {
                    fprintf(stderr, "pipe: short merge write\n"); fclose(out); return 9;
                }
                wbuf.clear();
            }
        }
        if (!wbuf.empty() && fwrite(wbuf.data(), 8, wbuf.size(), out) != wbuf.size()) {
            fprintf(stderr, "pipe: short merge write\n"); fclose(out); return 9;
        }
        if (fseeko(out, 0, SEEK_SET) != 0 || fwrite(&merged, 8, 1, out) != 1) {
            fclose(out); fprintf(stderr, "pipe: header rewrite\n"); return 9;
        }
        fclose(out);
        for (int v = 0; v < V; ++v) if (fh[(size_t)v]) fclose(fh[(size_t)v]);
        double tC = now_s() - tC0;

        if (merged != emitted) {
            fprintf(stderr, "[pipe] INTERNAL: emitted %" PRIu64 " but merged %" PRIu64 "\n",
                    emitted, merged);
            return 9;
        }

        double tsecs = now_s() - tk;
        long rss = rss_mb();
        if (rss > peak_rss) peak_rss = rss;
        sizes.push_back((size_t)merged);
        total += merged;
        if ((long)merged > widest_level) { widest_level = (long)merged; widest_k = nk; widest_bytes = 16ull * merged; widest_secs = tsecs; }
        if (k > 0) growth = (double)merged / (double)cur_n;
        fprintf(stderr,
                "  level %d: %" PRIu64 " states  bytes=%s  rss=%ldMB  gen=%.1fs cat=%.1fs "
                "merge=%.1fs  tot=%.1fs  free=%s\n",
                nk, merged, human(16ull * merged).c_str(), rss, tA, tB, tC, tsecs,
                human(free_bytes(o.dir.c_str())).c_str());
        fflush(stderr);

        for (int v = 0; v < V; ++v) remove(blk_path(v).c_str());
        if (k >= 1) remove(level_path((int)(k - 1)).c_str());
        sync();
        if (merged == 0) { stop_reason = "empty_level"; break; }
    }

    if ((long)sizes.size() - 1 >= o.maxlevel && !stopped_disk) stop_reason = "maxlevel";

    printf("{\n  \"n\": %d,\n  \"V\": %d,\n  \"F\": %zu,\n  \"words_per_state\": 2,\n"
           "  \"bytes_per_state\": 16,\n  \"K\": %zu,\n  \"stop_reason\": \"%s\",\n"
           "  \"n_safe_subsets\": %llu,\n  \"level_sizes\": [",
           o.n, V, B.quads.size(), sizes.size() - 1, stop_reason.c_str(),
           (unsigned long long)total);
    for (size_t i = 0; i < sizes.size(); ++i) printf("%s%zu", i ? "," : "", sizes[i]);
    printf("],\n  \"widest_level\": %ld,\n  \"widest_size\": %ld,\n"
           "  \"widest_bytes\": %llu,\n  \"widest_level_secs\": %.1f,\n"
           "  \"peak_rss_mb\": %ld,\n  \"chunk_states\": %" PRIu64 ",\n"
           "  \"threads\": %d,\n  \"enum_seconds\": %.1f\n}\n",
           widest_k, widest_level, (unsigned long long)widest_bytes, widest_secs,
           peak_rss, chunk, nthreads, now_s() - t0);
    return stopped_disk ? 3 : 0;
}
