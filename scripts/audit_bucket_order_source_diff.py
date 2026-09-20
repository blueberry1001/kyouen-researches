#!/usr/bin/env python3
"""Fail-closed source audit for the bucket-order optimization branch.

Independent of solver outputs. Proves that, relative to base
e9d0460b55b7f058379da2a843ecea33525b86ea, the solver sources/includes
changed ONLY by:

  resume_2.inc
    1. the exact new bucket method line
       (order_children_cache_aware_bucket);
    2. the exact cache-aware impl selection in order_children
       (one new else-if branch);
    3. one new member cache_aware_impl_bucket_ + its setter;
    4. the order-equivalence test exposure (OrderTestChild struct +
       two static for_test methods).

  resume_3.inc
    5. the --cache-aware-order-impl token added to the --certificate
       mode rejection guard.

  resume_4.inc
    6. the --cache-aware-order-impl runtime switch (parse loop +
       validation + solver wiring + stderr log).

All other solver sources/includes (resume_0, resume_1, witness_log,
probe_cert_solver.cpp) must be byte-identical to base. resume_1
(memo capacity constructor) must in particular be byte-identical.

Checks are written as exact expected-diff assertions, not loose
"looks fine" checks: every changed hunk is matched verbatim.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "e9d0460b55b7f058379da2a843ecea33525b86ea"

SOLVER_PATHS = [
    "scripts/probe_cert_solver.cpp",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc",
]

def _resolve_main_gitdir() -> Path | None:
    """Map a Windows worktree .git pointer to the main repo git-dir path
    usable from the current OS (WSL or Windows)."""
    import re as _re
    gitdir_file = ROOT / ".git"
    if not gitdir_file.is_file():
        return None
    pointer = gitdir_file.read_text(encoding="utf-8", errors="replace").strip()
    if pointer.startswith("gitdir:"):
        pointer = pointer[len("gitdir:"):].strip()
    m = _re.match(r"(.*)[/\\\\]\.git[/\\\\]worktrees[/\\\\](.+)$", pointer)
    if not m:
        return None
    cand = m.group(1)
    mm = _re.match(r"^([A-Za-z]):[/\\\\](.*)$", cand)
    if mm:  # Windows drive path
        on_wsl = Path("/mnt").exists() and not Path("C:/").exists()
        if on_wsl:
            cand = ("/mnt/" + mm.group(1).lower() + "/"
                    + mm.group(2).replace("\\\\", "/"))
    return Path(cand) / ".git"


def git_show(path: str) -> bytes:
    # Normal case: this worktree's own git works.
    p = subprocess.run(["git", "show", f"{BASE}:{path}"], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode == 0:
        return p.stdout
    # WSL-in-Windows-worktree case: .git points to a Windows path WSL git
    # cannot follow. Read the same commit from the main repository instead.
    main_gitdir = _resolve_main_gitdir()
    if main_gitdir is not None and main_gitdir.is_dir():
        p = subprocess.run(
            ["git", "--git-dir", str(main_gitdir), "show", f"{BASE}:{path}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0:
            return p.stdout
    raise SystemExit(f"SOURCE AUDIT FAIL: cannot read {BASE}:{path}\n"
                     + p.stderr.decode("utf-8", "replace"))


def fail(msg: str) -> None:
    raise SystemExit(f"SOURCE AUDIT FAIL: {msg}")


# ---- Authorized resume_2 content (all new/changed lines verbatim) ----
R2_BUCKET_METHOD = (
    "private:void order_children_cache_aware_bucket(std::array<Child,V>&ch,int n)"
    "{int w=0;for(int i=0;i<n;++i){if(ch[i].cached==MultiDepthMemo100::Losing)"
    "std::swap(ch[i],ch[w++]);}int m=w;for(int i=w;i<n;++i)"
    "{if(ch[i].cached==0)std::swap(ch[i],ch[m++]);}"
    "auto cnt_key_lt=[](const Child&a,const Child&b)"
    "{if(a.count!=b.count)return a.count<b.count;return a.key<b.key;};"
    "std::sort(ch.begin(),ch.begin()+w,cnt_key_lt);"
    "std::sort(ch.begin()+w,ch.begin()+m,cnt_key_lt);"
    "std::sort(ch.begin()+m,ch.begin()+n,cnt_key_lt);}"
)
R2_ELSE_IF = (
    "else if(cache_aware_impl_bucket_&&depth>kFrozenRootDepth)"
    "{order_children_cache_aware_bucket(ch,n);}"
)
R2_MEMBER = (
    "private:bool cache_aware_impl_bucket_=false;"
    "private:bool below_root_blind_=false;"
    "private:bool root_order_active_=false;int root_order_depth_=-1;"
    "std::vector<Bits> root_order_;int root_diag_depth_=-1;"
    "std::size_t root_children_unique_=0;std::size_t root_children_entered_=0;"
    "int root_witness_move_=-1;std::vector<Bits> root_eval_order_;"
)
R2_SETTER = "public:void set_cache_aware_impl_bucket(bool b){cache_aware_impl_bucket_=b;}"
R2_TEST_STRUCT = (
    "public:struct OrderTestChild{TState ts;Bits legal,key;int count;"
    "std::uint32_t cached;};"
)
R2_TEST_SINGLE = (
    "public:static void order_cache_aware_single_sort_for_test("
    "std::vector<OrderTestChild>&ch){std::sort(ch.begin(),ch.end(),"
    "[](const OrderTestChild&a,const OrderTestChild&b)"
    "{int pa=a.cached==MultiDepthMemo100::Losing?0:(a.cached==0?1:2),"
    "pb=b.cached==MultiDepthMemo100::Losing?0:(b.cached==0?1:2);"
    "if(pa!=pb)return pa<pb;if(a.count!=b.count)return a.count<b.count;"
    "return a.key<b.key;});}"
)
R2_TEST_BUCKET = (
    "public:static void order_cache_aware_bucket_for_test("
    "std::vector<OrderTestChild>&ch){int w=0;int n=(int)ch.size();"
    "for(int i=0;i<n;++i){if(ch[i].cached==MultiDepthMemo100::Losing)"
    "std::swap(ch[i],ch[w++]);}int m=w;for(int i=w;i<n;++i)"
    "{if(ch[i].cached==0)std::swap(ch[i],ch[m++]);}"
    "auto cnt_key_lt=[](const OrderTestChild&a,const OrderTestChild&b)"
    "{if(a.count!=b.count)return a.count<b.count;return a.key<b.key;};"
    "std::sort(ch.begin(),ch.begin()+w,cnt_key_lt);"
    "std::sort(ch.begin()+w,ch.begin()+m,cnt_key_lt);"
    "std::sort(ch.begin()+m,ch.begin()+n,cnt_key_lt);}"
)

# ---- Authorized resume_3 change (one line modified verbatim) ----
R3_OLD = (
    'for(int ai=1;ai<argc;++ai){std::string a=argv[ai];'
    'if(a=="--root-order-file"||a=="--root-depth")'
    'throw std::runtime_error("root-order flags not supported '
    'in --certificate mode");}'
)
R3_NEW = (
    'for(int ai=1;ai<argc;++ai){std::string a=argv[ai];'
    'if(a=="--root-order-file"||a=="--root-depth"||'
    'a=="--cache-aware-order-impl")'
    'throw std::runtime_error("root-order flags not supported '
    'in --certificate mode");}'
)

# ---- Authorized resume_4 changes (two lines, rest verbatim) ----
R4_OLD_FLAGLINE = (
    ' std::string memo_instr_out;for(int ai2=1;ai2<argc;){std::string a='
    'argv[ai2];if(a=="--memo-instr-out"&&ai2+1<argc){memo_instr_out='
    'argv[ai2+1];for(int aj=ai2;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}'
    'else ++ai2;}std::string below_root_order="cache-aware";'
    'for(int ai3=1;ai3<argc;){std::string a=argv[ai3];'
    'if(a=="--below-root-order"&&ai3+1<argc){below_root_order=argv[ai3+1];'
    'for(int aj=ai3;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else ++ai3;}'
    'if(below_root_order!="cache-aware"&&below_root_order!="cache-blind")'
    'throw std::runtime_error("unknown --below-root-order '
    '(want cache-aware|cache-blind)");'
)
R4_NEW_FLAGLINE = R4_OLD_FLAGLINE + (
    'std::string cache_aware_impl="sort";'
    'for(int ai4=1;ai4<argc;){std::string a=argv[ai4];'
    'if(a=="--cache-aware-order-impl"&&ai4+1<argc)'
    '{cache_aware_impl=argv[ai4+1];'
    'for(int aj=ai4;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}'
    'else ++ai4;}'
    'if(cache_aware_impl!="sort"&&cache_aware_impl!="bucket")'
    'throw std::runtime_error("unknown --cache-aware-order-impl '
    '(want sort|bucket)");'
)
R4_OLD_SOLVE = (
    ' Solver solver(shrink,load);if(!memo_instr_out.empty())'
    'solver.set_memo_instr(memo_instr_out);'
    'if(below_root_order=="cache-blind")'
    'solver.set_below_root_order_blind(true);'
    'std::cerr<<"below_root_order="<<below_root_order<<"\\n";'
)
R4_NEW_SOLVE = (
    ' Solver solver(shrink,load);if(!memo_instr_out.empty())'
    'solver.set_memo_instr(memo_instr_out);'
    'if(below_root_order=="cache-blind")'
    'solver.set_below_root_order_blind(true);'
    'if(cache_aware_impl=="bucket")'
    'solver.set_cache_aware_impl_bucket(true);'
    'std::cerr<<"below_root_order="<<below_root_order<<"\\n";'
    'std::cerr<<"cache_aware_impl="<<cache_aware_impl<<"\\n";'
)


def check_unchanged(path: str) -> None:
    cur = (ROOT / path).read_bytes()
    old = git_show(path)
    if cur != old:
        fail(f"unauthorized solver change in {path}")
    print(f"  unchanged: {path}")


def expected_solver_bytes(path: str, old_bytes: bytes) -> bytes:
    """The committed (manual-swap) authorized variant of a solver file,
    reconstructed from the base bytes. Exposed for the sibling audit
    script (audit_cache_aware_bucket_order_source_diff.py), which
    accepts either authorized implementation variant."""
    if path not in ("scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc",
                    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc",
                    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"):
        return old_bytes
    old = old_bytes.decode("utf-8")
    if path.endswith("resume_2.inc"):
        anchor_public = (
            " static constexpr int N=10,V=100;"
            "static constexpr int kFrozenRootDepth=3;"
            "static constexpr std::uint64_t HiMask=(1ULL<<36)-1;"
            "using Clock=std::chrono::steady_clock;"
            "struct TState{std::array<Bits,8>t{};};"
            "struct Child{TState ts;Bits legal,key;int count;"
            "std::uint32_t cached;};\npublic:\n"
        )
        anchor_root_rank = (
            "private:int root_rank(Bits k)const{for(std::size_t j=0;"
            "j<root_order_.size();++j)if(root_order_[j]==k)return(int)j;"
            "return -1;}\n"
        )
        blind_branch = (
            "else if(below_root_blind_&&depth>kFrozenRootDepth){std::sort("
            "ch.begin(),ch.begin()+n,[](const Child&a,const Child&b)"
            "{if(a.count!=b.count)return a.count<b.count;"
            "return a.key<b.key;});}"
        )
        anchor_members = (
            "private:bool below_root_blind_=false;"
            "private:bool root_order_active_=false;"
            "int root_order_depth_=-1;std::vector<Bits> root_order_;"
            "int root_diag_depth_=-1;std::size_t root_children_unique_=0;"
            "std::size_t root_children_entered_=0;int root_witness_move_=-1;"
            "std::vector<Bits> root_eval_order_;\n"
        )
        for needle, what in ((anchor_public, "public anchor"),
                             (anchor_root_rank, "root_rank anchor"),
                             (blind_branch, "blind branch"),
                             (anchor_members, "member line")):
            if old.count(needle) != 1:
                fail(f"base resume_2 {what} count != 1")
        exp = old
        exp = exp.replace(
            anchor_public,
            anchor_public
            + R2_TEST_STRUCT + "\n" + R2_TEST_SINGLE + "\n" + R2_TEST_BUCKET
            + "\n", 1)
        exp = exp.replace(anchor_root_rank,
                          anchor_root_rank + R2_BUCKET_METHOD + "\n", 1)
        exp = exp.replace(blind_branch, blind_branch + R2_ELSE_IF, 1)
        exp = exp.replace(anchor_members, R2_MEMBER + "\n" + R2_SETTER + "\n",
                          1)
        return exp.encode("utf-8")
    if path.endswith("resume_3.inc"):
        if old.count(R3_OLD) != 1:
            fail("base resume_3 guard count != 1")
        return old.replace(R3_OLD, R3_NEW, 1).encode("utf-8")
    # resume_4
    if old.count(R4_OLD_FLAGLINE) != 1 or old.count(R4_OLD_SOLVE) != 1:
        fail("base resume_4 anchors count != 1")
    exp = old.replace(R4_OLD_FLAGLINE, R4_NEW_FLAGLINE, 1)
    exp = exp.replace(R4_OLD_SOLVE, R4_NEW_SOLVE, 1)
    return exp.encode("utf-8")


def main() -> int:
    print(f"base={BASE}")
    # 1. Strictly unchanged files.
    for path in ["scripts/probe_cert_solver.cpp",
                 "scripts/probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc",
                 "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc",
                 "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc"]:
        check_unchanged(path)

    # 2. resume_2: reconstruct expected content from base + authorized
    #    insertions, then require an exact match.
    p2 = "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc"
    old2 = git_show(p2).decode("utf-8")
    cur2 = (ROOT / p2).read_text(encoding="utf-8")

    def once(text: str, needle: str, what: str) -> None:
        if text.count(needle) != 1:
            fail(f"resume_2: expected exactly one {what}")

    # All base anchors must exist exactly once in BOTH old and current.
    anchor_class = "class Solver{\n"
    anchor_public = (
        " static constexpr int N=10,V=100;"
        "static constexpr int kFrozenRootDepth=3;"
        "static constexpr std::uint64_t HiMask=(1ULL<<36)-1;"
        "using Clock=std::chrono::steady_clock;"
        "struct TState{std::array<Bits,8>t{};};"
        "struct Child{TState ts;Bits legal,key;int count;"
        "std::uint32_t cached;};\npublic:\n"
    )
    anchor_root_rank = (
        "private:int root_rank(Bits k)const{for(std::size_t j=0;"
        "j<root_order_.size();++j)if(root_order_[j]==k)return(int)j;"
        "return -1;}\n"
    )
    anchor_order_children_head = (
        "private:void order_children(std::array<Child,V>&ch,int n,int depth)"
    )
    anchor_members = (
        "private:bool below_root_blind_=false;"
        "private:bool root_order_active_=false;"
        "int root_order_depth_=-1;std::vector<Bits> root_order_;"
        "int root_diag_depth_=-1;std::size_t root_children_unique_=0;"
        "std::size_t root_children_entered_=0;int root_witness_move_=-1;"
        "std::vector<Bits> root_eval_order_;\n"
    )
    for a in (anchor_class, anchor_root_rank, anchor_order_children_head,
              anchor_members):
        once(old2, a, f"base anchor in base resume_2: {a[:50]}")
        if old2.count(a) != 1:
            fail("internal: base anchor count")
    if anchor_public not in old2 or old2.count(anchor_public) != 1:
        fail("resume_2 base public anchor missing")

    # Expected transformation of resume_2.
    exp2 = old2
    # 4a. test exposure inserted after 'public:\n' of class Solver.
    exp2 = exp2.replace(
        anchor_public,
        anchor_public
        + R2_TEST_STRUCT + "\n" + R2_TEST_SINGLE + "\n" + R2_TEST_BUCKET
        + "\n", 1)
    # 4b. bucket method inserted after root_rank line.
    exp2 = exp2.replace(anchor_root_rank,
                        anchor_root_rank + R2_BUCKET_METHOD + "\n", 1)
    # 4c. new else-if branch in order_children: base has
    #     'else if(below_root_blind_&&depth>kFrozenRootDepth){...}'
    #     followed by 'else{'. Insert our branch between them.
    blind_branch = (
        "else if(below_root_blind_&&depth>kFrozenRootDepth){std::sort("
        "ch.begin(),ch.begin()+n,[](const Child&a,const Child&b)"
        "{if(a.count!=b.count)return a.count<b.count;"
        "return a.key<b.key;});}"
    )
    once(old2, blind_branch, "cache-blind branch")
    exp2 = exp2.replace(blind_branch, blind_branch + R2_ELSE_IF, 1)
    # 4d. member line gains the new flag prefix; setter added after it.
    once(old2, anchor_members, "member line")
    exp2 = exp2.replace(anchor_members, R2_MEMBER + "\n" + R2_SETTER + "\n",
                        1)
    if exp2 != cur2:
        # Produce a compact mismatch report.
        import difflib
        diff = list(difflib.unified_diff(
            exp2.splitlines(), cur2.splitlines(),
            "expected_resume_2", "current_resume_2", lineterm=""))[:40]
        print("\n".join(diff))
        fail("resume_2 differs by more than the authorized bucket-impl "
             "switch + test exposure")
    once(cur2, R2_BUCKET_METHOD, "bucket method line")
    once(cur2, R2_ELSE_IF, "else-if selection")
    print(f"  authorized diff: {p2}")

    # 3. resume_3: single-line replacement, nothing else.
    p3 = "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc"
    old3 = git_show(p3).decode("utf-8")
    cur3 = (ROOT / p3).read_text(encoding="utf-8")
    if old3.count(R3_OLD) != 1:
        fail("resume_3 base guard line not found exactly once")
    exp3 = old3.replace(R3_OLD, R3_NEW, 1)
    if exp3 != cur3:
        fail("resume_3 differs by more than the authorized "
             "--cache-aware-order-impl certificate guard")
    print(f"  authorized diff: {p3}")

    # 4. resume_4: two-line replacements, nothing else.
    p4 = "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"
    old4 = git_show(p4).decode("utf-8")
    cur4 = (ROOT / p4).read_text(encoding="utf-8")
    if old4.count(R4_OLD_FLAGLINE) != 1:
        fail("resume_4 base flag-parse line not found exactly once")
    if old4.count(R4_OLD_SOLVE) != 1:
        fail("resume_4 base solver-construction line not found exactly once")
    exp4 = old4.replace(R4_OLD_FLAGLINE, R4_NEW_FLAGLINE, 1)
    exp4 = exp4.replace(R4_OLD_SOLVE, R4_NEW_SOLVE, 1)
    if exp4 != cur4:
        fail("resume_4 differs by more than the authorized "
             "--cache-aware-order-impl runtime switch")
    print(f"  authorized diff: {p4}")

    # 5. No other solver-adjacent sources changed vs base (rust solver etc.
    #    are separate; we scope to the frozen 10x10 exact solver unit).
    print("SOURCE AUDIT PASS")
    print("solver_paths_checked=7")
    print("authorized_solver_diff=runtime --cache-aware-order-impl switch, "
          "bucket cache-aware ordering method + selection, order-equivalence "
          "test exposure only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
