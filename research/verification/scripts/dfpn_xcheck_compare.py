#!/usr/bin/env python3
# Compare DFS vs df-pn outcomes row by row. Exit 1 on any mismatch.
import csv, sys

def load_dfs(path):
    out = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            parent = row["canonical_parent"].strip()
            move = row["move"].strip()
            stones = tuple(sorted(
                ([int(x) for x in parent.split(",")] if parent else []) + [int(move)]))
            # child_outcome is from the CHILD's perspective? No: check header
            # semantics of kyouen_solver_N_root: it solves parent+move as root
            # and reports child_outcome = WIN/LOSS for the side to move at the
            # child? Actually solve_root(p) returns win(state) = "position is
            # winning for the player who just moved first on this line"...
            # For cross-check we only need CONSISTENCY: map both to the same
            # convention. DFS solver reports child_outcome with the same
            # solve_root, so direct string compare is valid.
            out[stones] = row["child_outcome"].strip()
    return out

def load_dfpn(path):
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line.startswith("[done]"):
                continue
            # [done] [roots{0,7}] WIN expansions=...
            tag = line.split("[", 2)[2].split("]")[0]
            assert tag.startswith("roots{"), line
            stones = tuple(sorted(int(x) for x in tag[6:-1].split(",") if x != ""))
            outcome = line.split()[2]
            assert outcome in ("WIN", "LOSS"), line
            out[stones] = outcome
    return out

def flip(o):
    return "LOSS" if o == "WIN" else "WIN"

def main():
    n = sys.argv[1]
    dfs = load_dfs("/mnt/d/ghq/build11/xcheck-logs/dfs%s.csv" % n)
    dfpn = load_dfpn("/mnt/d/ghq/build11/xcheck-logs/dfpn%s.log" % n)
    # CONVENTION: DFS child_outcome = outcome for the side TO MOVE at the
    # child root. df-pn outcome = "first player on this line eventually wins"
    # (side that moved first from empty). At a root with k stones, side to
    # move = first player iff k even. So dfpn and dfs agree iff:
    #   k even: dfpn == dfs ; k odd: dfpn == flip(dfs).
    keys = sorted(set(dfs) & set(dfpn))
    print("n=%s common roots: %d (dfs=%d dfpn=%d)" % (n, len(keys), len(dfs), len(dfpn)))
    bad = 0
    for k in keys:
        expect = dfs[k] if len(k) % 2 == 0 else flip(dfs[k])
        mark = "OK " if expect == dfpn[k] else "MISMATCH"
        if expect != dfpn[k]:
            bad += 1
        print("%s stones=%s k=%d dfs=%s expect=%s dfpn=%s" % (
            mark, ",".join(map(str, k)), len(k), dfs[k], expect, dfpn[k]))
    only_dfs = sorted(set(dfs) - set(dfpn))
    only_dfpn = sorted(set(dfpn) - set(dfs))
    if only_dfs:
        print("dfs-only (dfpn skipped/unsafe): %d" % len(only_dfs))
    if only_dfpn:
        print("dfpn-only: %d" % len(only_dfpn))
    print("MISMATCHES=%d" % bad)
    return 1 if bad else 0

sys.exit(main())
