#!/usr/bin/env python3
"""Apply only the preregistered cache-aware bucket-order implementation delta.

The experiment is allowed to change two solver locations only:
  * Solver::order_children + one boolean/setter in resume_2.inc;
  * CLI parsing/wiring for --cache-aware-impl single|bucket in resume_4.inc.

This script fails closed if the frozen pre-patch text is not present exactly once,
or if either file is already partially patched.  --check performs all validation
without writing.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P2 = ROOT / "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc"
P4 = ROOT / "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"

OLD2 = '''public:void set_root_order(int depth,const std::vector<Bits>&keys){root_order_active_=true;root_order_depth_=depth;root_order_=keys;}public:void set_below_root_order_blind(bool b){below_root_blind_=b;}\npublic:Bits canonical_key_of(const std::vector<int>&pts)const{TState s{};for(int v:pts)s=add(s,v);return canonical(s);}\npublic:void set_root_diag(int depth){root_diag_depth_=depth;root_children_unique_=0;root_children_entered_=0;root_witness_move_=-1;root_eval_order_.clear();}\nprivate:int root_rank(Bits k)const{for(std::size_t j=0;j<root_order_.size();++j)if(root_order_[j]==k)return(int)j;return -1;}\nprivate:void order_children(std::array<Child,V>&ch,int n,int depth){if(root_order_active_&&depth==root_order_depth_){if((int)root_order_.size()!=n)throw std::runtime_error("root order size mismatch vs unique root children");std::sort(ch.begin(),ch.begin()+n,[this](const Child&a,const Child&b){int ra=root_rank(a.key),rb=root_rank(b.key);if(ra<0||rb<0)throw std::runtime_error("root order missing child key");if(ra!=rb)return ra<rb;return a.key<b.key;});}else if(below_root_blind_&&depth>kFrozenRootDepth){std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}else{std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){int pa=a.cached==MultiDepthMemo100::Losing?0:(a.cached==0?1:2),pb=b.cached==MultiDepthMemo100::Losing?0:(b.cached==0?1:2);if(pa!=pb)return pa<pb;if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}if(depth==root_diag_depth_){root_children_unique_=(std::size_t)n;root_eval_order_.clear();for(int i=0;i<n;++i)root_eval_order_.push_back(ch[i].key);}}\nprivate:bool below_root_blind_=false;private:bool root_order_active_=false;int root_order_depth_=-1;std::vector<Bits> root_order_;int root_diag_depth_=-1;std::size_t root_children_unique_=0;std::size_t root_children_entered_=0;int root_witness_move_=-1;std::vector<Bits> root_eval_order_;'''

NEW2 = '''public:void set_root_order(int depth,const std::vector<Bits>&keys){root_order_active_=true;root_order_depth_=depth;root_order_=keys;}public:void set_below_root_order_blind(bool b){below_root_blind_=b;}public:void set_cache_aware_bucket_order(bool b){cache_aware_bucket_order_=b;}\npublic:Bits canonical_key_of(const std::vector<int>&pts)const{TState s{};for(int v:pts)s=add(s,v);return canonical(s);}\npublic:void set_root_diag(int depth){root_diag_depth_=depth;root_children_unique_=0;root_children_entered_=0;root_witness_move_=-1;root_eval_order_.clear();}\nprivate:int root_rank(Bits k)const{for(std::size_t j=0;j<root_order_.size();++j)if(root_order_[j]==k)return(int)j;return -1;}\nprivate:void order_children(std::array<Child,V>&ch,int n,int depth){if(root_order_active_&&depth==root_order_depth_){if((int)root_order_.size()!=n)throw std::runtime_error("root order size mismatch vs unique root children");std::sort(ch.begin(),ch.begin()+n,[this](const Child&a,const Child&b){int ra=root_rank(a.key),rb=root_rank(b.key);if(ra<0||rb<0)throw std::runtime_error("root order missing child key");if(ra!=rb)return ra<rb;return a.key<b.key;});}else if(below_root_blind_&&depth>kFrozenRootDepth){std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}else if(cache_aware_bucket_order_&&depth>kFrozenRootDepth){auto first=ch.begin(),last=ch.begin()+n;auto loss_end=std::partition(first,last,[](const Child&c){return c.cached==MultiDepthMemo100::Losing;});auto unknown_end=std::partition(loss_end,last,[](const Child&c){return c.cached==0;});auto within=[](const Child&a,const Child&b){if(a.count!=b.count)return a.count<b.count;return a.key<b.key;};std::sort(first,loss_end,within);std::sort(loss_end,unknown_end,within);std::sort(unknown_end,last,within);}else{std::sort(ch.begin(),ch.begin()+n,[](const Child&a,const Child&b){int pa=a.cached==MultiDepthMemo100::Losing?0:(a.cached==0?1:2),pb=b.cached==MultiDepthMemo100::Losing?0:(b.cached==0?1:2);if(pa!=pb)return pa<pb;if(a.count!=b.count)return a.count<b.count;return a.key<b.key;});}if(depth==root_diag_depth_){root_children_unique_=(std::size_t)n;root_eval_order_.clear();for(int i=0;i<n;++i)root_eval_order_.push_back(ch[i].key);}}\nprivate:bool below_root_blind_=false;bool cache_aware_bucket_order_=false;private:bool root_order_active_=false;int root_order_depth_=-1;std::vector<Bits> root_order_;int root_diag_depth_=-1;std::size_t root_children_unique_=0;std::size_t root_children_entered_=0;int root_witness_move_=-1;std::vector<Bits> root_eval_order_;'''

OLD4A = ''' std::string memo_instr_out;for(int ai2=1;ai2<argc;){std::string a=argv[ai2];if(a=="--memo-instr-out"&&ai2+1<argc){memo_instr_out=argv[ai2+1];for(int aj=ai2;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else ++ai2;}std::string below_root_order="cache-aware";for(int ai3=1;ai3<argc;){std::string a=argv[ai3];if(a=="--below-root-order"&&ai3+1<argc){below_root_order=argv[ai3+1];for(int aj=ai3;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else ++ai3;}if(below_root_order!="cache-aware"&&below_root_order!="cache-blind")throw std::runtime_error("unknown --below-root-order (want cache-aware|cache-blind)");'''
NEW4A = ''' std::string memo_instr_out;for(int ai2=1;ai2<argc;){std::string a=argv[ai2];if(a=="--memo-instr-out"&&ai2+1<argc){memo_instr_out=argv[ai2+1];for(int aj=ai2;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else ++ai2;}std::string below_root_order="cache-aware";for(int ai3=1;ai3<argc;){std::string a=argv[ai3];if(a=="--below-root-order"&&ai3+1<argc){below_root_order=argv[ai3+1];for(int aj=ai3;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else ++ai3;}if(below_root_order!="cache-aware"&&below_root_order!="cache-blind")throw std::runtime_error("unknown --below-root-order (want cache-aware|cache-blind)");std::string cache_aware_impl="single";for(int ai4=1;ai4<argc;){std::string a=argv[ai4];if(a=="--cache-aware-impl"&&ai4+1<argc){cache_aware_impl=argv[ai4+1];for(int aj=ai4;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else ++ai4;}if(cache_aware_impl!="single"&&cache_aware_impl!="bucket")throw std::runtime_error("unknown --cache-aware-impl (want single|bucket)");'''

OLD4B = ''' Solver solver(shrink,load);if(!memo_instr_out.empty())solver.set_memo_instr(memo_instr_out);if(below_root_order=="cache-blind")solver.set_below_root_order_blind(true);std::cerr<<"below_root_order="<<below_root_order<<"\\n";'''
NEW4B = ''' Solver solver(shrink,load);if(!memo_instr_out.empty())solver.set_memo_instr(memo_instr_out);if(below_root_order=="cache-blind")solver.set_below_root_order_blind(true);if(cache_aware_impl=="bucket")solver.set_cache_aware_bucket_order(true);std::cerr<<"below_root_order="<<below_root_order<<" cache_aware_impl="<<cache_aware_impl<<"\\n";'''


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    old_count = text.count(old)
    new_count = text.count(new)
    if new_count:
        raise SystemExit(f"PATCH FAIL: {label} already/partially patched (new_count={new_count})")
    if old_count != 1:
        raise SystemExit(f"PATCH FAIL: {label} frozen old text count={old_count}, want 1")
    out = text.replace(old, new, 1)
    # Reversibility is a cheap guard against accidental extra edits.
    if out.replace(new, old, 1) != text:
        raise SystemExit(f"PATCH FAIL: {label} replacement not exactly reversible")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    t2 = P2.read_text(encoding="utf-8")
    t4 = P4.read_text(encoding="utf-8")
    n2 = replace_exact(t2, OLD2, NEW2, "resume_2 order implementation")
    n4 = replace_exact(t4, OLD4A, NEW4A, "resume_4 CLI parser")
    n4 = replace_exact(n4, OLD4B, NEW4B, "resume_4 solver wiring")

    if args.check:
        print("BUCKET IMPLEMENTATION PATCH CHECK PASS")
        print("authorized replacements=3 across 2 files")
        return

    P2.write_text(n2, encoding="utf-8")
    P4.write_text(n4, encoding="utf-8")
    print("BUCKET IMPLEMENTATION PATCH APPLIED")
    print("resume_2: runtime bucket implementation + setter")
    print("resume_4: --cache-aware-impl single|bucket parser + wiring")


if __name__ == "__main__":
    main()
