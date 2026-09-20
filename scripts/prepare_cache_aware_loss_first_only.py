#!/usr/bin/env python3
"""Fail-closed preparer for the preregistered loss-first-only ablation.

Implements only the frozen delta in
``docs/10X10_CACHE_AWARE_LOSS_FIRST_ONLY_PREREG.md``.  Production and safety
harness deliberately call the same ordering primitive.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P2 = ROOT / "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc"
P4 = ROOT / "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"

R2_TEST_OLD = "public:static void order_cache_aware_bucket_for_test(std::vector<OrderTestChild>&ch){int w=0;int n=(int)ch.size();for(int i=0;i<n;++i){if(ch[i].cached==MultiDepthMemo100::Losing)std::swap(ch[i],ch[w++]);}int m=w;for(int i=w;i<n;++i){if(ch[i].cached==0)std::swap(ch[i],ch[m++]);}auto cnt_key_lt=[](const OrderTestChild&a,const OrderTestChild&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;};std::sort(ch.begin(),ch.begin()+w,cnt_key_lt);std::sort(ch.begin()+w,ch.begin()+m,cnt_key_lt);std::sort(ch.begin()+m,ch.end(),cnt_key_lt);}\n"
R2_TEST_NEW = R2_TEST_OLD + "public:template<class It>static void order_loss_first_range(It first,It last){using T=typename std::iterator_traits<It>::value_type;std::sort(first,last,[](const T&a,const T&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});auto loss=std::find_if(first,last,[](const T&c){return c.cached==MultiDepthMemo100::Losing;});if(loss!=last&&loss!=first)std::rotate(first,loss,std::next(loss));}\npublic:static void order_loss_first_only_for_test(std::vector<OrderTestChild>&ch){order_loss_first_range(ch.begin(),ch.end());}\n"

R2_BUCKET_OLD = "private:void order_children_cache_aware_bucket(std::array<Child,V>&ch,int n){int w=0;for(int i=0;i<n;++i){if(ch[i].cached==MultiDepthMemo100::Losing)std::swap(ch[i],ch[w++]);}int m=w;for(int i=w;i<n;++i){if(ch[i].cached==0)std::swap(ch[i],ch[m++]);}auto cnt_key_lt=[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;};std::sort(ch.begin(),ch.begin()+w,cnt_key_lt);std::sort(ch.begin()+w,ch.begin()+m,cnt_key_lt);std::sort(ch.begin()+m,ch.begin()+n,cnt_key_lt);}\n"
R2_BUCKET_NEW = R2_BUCKET_OLD + "private:void order_children_loss_first_only(std::array<Child,V>&ch,int n){order_loss_first_range(ch.begin(),ch.begin()+n);}\n"

R2_BRANCH_OLD = "else if(cache_aware_nohit_fastpath_&&depth>kFrozenRootDepth&&!any_cached){std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}else if(cache_aware_impl_bucket_&&depth>kFrozenRootDepth){order_children_cache_aware_bucket(ch,n);}"
R2_BRANCH_NEW = "else if(cache_aware_nohit_fastpath_&&depth>kFrozenRootDepth&&!any_cached){std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}else if(cache_aware_loss_first_only_&&depth>kFrozenRootDepth){order_children_loss_first_only(ch,n);}else if(cache_aware_impl_bucket_&&depth>kFrozenRootDepth){order_children_cache_aware_bucket(ch,n);}"

R2_MEMBER_OLD = "private:bool cache_aware_nohit_fastpath_=false;private:bool cache_aware_impl_bucket_=false;private:bool below_root_blind_=false;"
R2_MEMBER_NEW = "private:bool cache_aware_loss_first_only_=false;private:bool cache_aware_nohit_fastpath_=false;private:bool cache_aware_impl_bucket_=false;private:bool below_root_blind_=false;"
R2_SETTER_OLD = "public:void set_cache_aware_impl_bucket(bool b){cache_aware_impl_bucket_=b;}public:void set_cache_aware_nohit_fastpath(bool b){cache_aware_nohit_fastpath_=b;}"
R2_SETTER_NEW = R2_SETTER_OLD + "public:void set_cache_aware_loss_first_only(bool b){cache_aware_loss_first_only_=b;}"

R4_VALIDATE_OLD = 'if(cache_aware_impl!="sort"&&cache_aware_impl!="bucket"&&cache_aware_impl!="nohit")throw std::runtime_error("unknown --cache-aware-order-impl (want sort|bucket|nohit)");'
R4_VALIDATE_NEW = 'if(cache_aware_impl!="sort"&&cache_aware_impl!="bucket"&&cache_aware_impl!="nohit"&&cache_aware_impl!="loss-first")throw std::runtime_error("unknown --cache-aware-order-impl (want sort|bucket|nohit|loss-first)");'
R4_WIRE_OLD = 'if(cache_aware_impl=="bucket")solver.set_cache_aware_impl_bucket(true);if(cache_aware_impl=="nohit")solver.set_cache_aware_nohit_fastpath(true);'
R4_WIRE_NEW = R4_WIRE_OLD + 'if(cache_aware_impl=="loss-first")solver.set_cache_aware_loss_first_only(true);'

REPLACEMENTS = {
    P2: [
        (R2_TEST_OLD, R2_TEST_NEW, "resume_2 shared loss-first test primitive"),
        (R2_BUCKET_OLD, R2_BUCKET_NEW, "resume_2 loss-first production wrapper"),
        (R2_BRANCH_OLD, R2_BRANCH_NEW, "resume_2 loss-first dispatch"),
        (R2_MEMBER_OLD, R2_MEMBER_NEW, "resume_2 member"),
        (R2_SETTER_OLD, R2_SETTER_NEW, "resume_2 setter"),
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
        print("LOSS-FIRST-ONLY PREP APPLY PASS")
    else:
        print("LOSS-FIRST-ONLY PREP CHECK PASS")
    print("solver_files=2")
    print("extra_memo_lookups=0")
    print("shared_primitive=production_and_test")
    print("authorized_delta=blind count/key sort; B-earliest cached LOSS rotate-to-front; runtime loss-first switch only")

if __name__ == "__main__":
    main()
