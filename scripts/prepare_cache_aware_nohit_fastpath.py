#!/usr/bin/env python3
"""Fail-closed preparer for the preregistered cache-aware no-hit fast path.

This script applies only the frozen implementation delta for experiment
10x10-cache-aware-nohit-fastpath.  It deliberately preserves the historical
single-sort path and the completed bucket experiment, adding a third runtime
choice, ``--cache-aware-order-impl nohit``.

The optimization is semantics-preserving by construction: during the existing
child prefetch loop we OR the already-fetched ``cv`` values into ``any_cached``.
At cache-aware nodes below the frozen root, when ``any_cached`` is false every
child has the same cached class (unknown), so the historical comparator
``(cached_class, count, key)`` is exactly equivalent to ``(count, key)``.
No additional memo lookup is introduced.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P2 = ROOT / "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc"
P3 = ROOT / "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc"
P4 = ROOT / "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"

# resume_2: pass any_cached into the ordering routine.
R2_SIG_OLD = "private:void order_children(std::array<Child,V>&ch,int n,int depth){"
R2_SIG_NEW = "private:void order_children(std::array<Child,V>&ch,int n,int depth,bool any_cached){"

# Add the fast path after cache-blind and before the old bucket experiment.
R2_BRANCH_OLD = (
    "else if(below_root_blind_&&depth>kFrozenRootDepth){std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}"
    "else if(cache_aware_impl_bucket_&&depth>kFrozenRootDepth){order_children_cache_aware_bucket(ch,n);}"
)
R2_BRANCH_NEW = (
    "else if(below_root_blind_&&depth>kFrozenRootDepth){std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}"
    "else if(cache_aware_nohit_fastpath_&&depth>kFrozenRootDepth&&!any_cached){std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}"
    "else if(cache_aware_impl_bucket_&&depth>kFrozenRootDepth){order_children_cache_aware_bucket(ch,n);}"
)

R2_MEMBER_OLD = "private:bool cache_aware_impl_bucket_=false;private:bool below_root_blind_=false;"
R2_MEMBER_NEW = "private:bool cache_aware_nohit_fastpath_=false;private:bool cache_aware_impl_bucket_=false;private:bool below_root_blind_=false;"

R2_SETTER_OLD = "public:void set_cache_aware_impl_bucket(bool b){cache_aware_impl_bucket_=b;}"
R2_SETTER_NEW = (
    "public:void set_cache_aware_impl_bucket(bool b){cache_aware_impl_bucket_=b;}"
    "public:void set_cache_aware_nohit_fastpath(bool b){cache_aware_nohit_fastpath_=b;}"
)

# resume_3: derive any_cached for free from the existing prefetch result.
R3_INIT_OLD = "std::array<Child,V>ch{};int n=0;Bits moves=legal;while(any(moves)){"
R3_INIT_NEW = "std::array<Child,V>ch{};int n=0;bool any_cached=false;Bits moves=legal;while(any(moves)){"

R3_CV_OLD = "auto cv=memo_.get(nk,depth+1);ch[n++]={ns,nl,nk,popcount(nl),cv};"
R3_CV_NEW = "auto cv=memo_.get(nk,depth+1);if(cv)any_cached=true;ch[n++]={ns,nl,nk,popcount(nl),cv};"

R3_CALL_OLD = "order_children(ch,n,depth);"
R3_CALL_NEW = "order_children(ch,n,depth,any_cached);"

# resume_4: expose the preregistered implementation as a third runtime option.
R4_VALIDATE_OLD = (
    'if(cache_aware_impl!="sort"&&cache_aware_impl!="bucket")throw std::runtime_error("unknown --cache-aware-order-impl (want sort|bucket)");'
)
R4_VALIDATE_NEW = (
    'if(cache_aware_impl!="sort"&&cache_aware_impl!="bucket"&&cache_aware_impl!="nohit")throw std::runtime_error("unknown --cache-aware-order-impl (want sort|bucket|nohit)");'
)

R4_WIRE_OLD = 'if(cache_aware_impl=="bucket")solver.set_cache_aware_impl_bucket(true);'
R4_WIRE_NEW = (
    'if(cache_aware_impl=="bucket")solver.set_cache_aware_impl_bucket(true);'
    'if(cache_aware_impl=="nohit")solver.set_cache_aware_nohit_fastpath(true);'
)

REPLACEMENTS = {
    P2: [
        (R2_SIG_OLD, R2_SIG_NEW, "resume_2 order_children signature"),
        (R2_BRANCH_OLD, R2_BRANCH_NEW, "resume_2 no-hit branch"),
        (R2_MEMBER_OLD, R2_MEMBER_NEW, "resume_2 member"),
        (R2_SETTER_OLD, R2_SETTER_NEW, "resume_2 setter"),
    ],
    P3: [
        (R3_INIT_OLD, R3_INIT_NEW, "resume_3 any_cached init"),
        (R3_CV_OLD, R3_CV_NEW, "resume_3 OR existing cv"),
        (R3_CALL_OLD, R3_CALL_NEW, "resume_3 order call"),
    ],
    P4: [
        (R4_VALIDATE_OLD, R4_VALIDATE_NEW, "resume_4 option validation"),
        (R4_WIRE_OLD, R4_WIRE_NEW, "resume_4 wiring"),
    ],
}


def transform(path: Path, text: str) -> str:
    original = text
    for old, new, label in REPLACEMENTS[path]:
        if text.count(old) != 1:
            raise SystemExit(f"PREP FAIL: {label}: expected old anchor exactly once, got {text.count(old)}")
        if new in text:
            raise SystemExit(f"PREP FAIL: {label}: new text already present")
        text = text.replace(old, new, 1)

    # Reverse reconstruction is the core fail-closed check: the proposed file
    # must map byte-for-byte back to the pre-implementation file.
    reversed_text = text
    for old, new, label in reversed(REPLACEMENTS[path]):
        if reversed_text.count(new) != 1:
            raise SystemExit(f"PREP FAIL: reverse {label}: new anchor count != 1")
        reversed_text = reversed_text.replace(new, old, 1)
    if reversed_text != original:
        raise SystemExit(f"PREP FAIL: reverse reconstruction mismatch for {path.name}")
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the frozen delta; default is check-only")
    args = ap.parse_args()

    outputs: dict[Path, str] = {}
    for path in REPLACEMENTS:
        if not path.is_file():
            raise SystemExit(f"PREP FAIL: missing {path}")
        outputs[path] = transform(path, path.read_text(encoding="utf-8"))

    if args.apply:
        for path, text in outputs.items():
            path.write_text(text, encoding="utf-8")
        print("NOHIT FASTPATH PREP APPLY PASS")
    else:
        print("NOHIT FASTPATH PREP CHECK PASS")
    print("solver_files=3")
    print("extra_memo_lookups=0")
    print("authorized_delta=existing cv OR -> any_cached; no-hit count/key sort; runtime nohit switch only")


if __name__ == "__main__":
    main()
