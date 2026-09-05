#!/usr/bin/env python3
import argparse
import math


def exact_two_sided_binom(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    pk_num = math.comb(n, k)
    total_num = sum(
        math.comb(n, j)
        for j in range(n + 1)
        if math.comb(n, j) <= pk_num
    )
    return min(1.0, total_num / (2 ** n))


def holm_adjust(raw):
    m = len(raw)
    order = sorted(range(m), key=lambda i: raw[i])
    adjusted = [1.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * raw[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def parse_spec(text):
    # LABEL:baseline_only:added_only:remaining
    parts = text.split(":")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "expected LABEL:baseline_only:added_only:remaining"
        )
    label = parts[0]
    try:
        a, b, r = map(int, parts[1:])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("counts must be integers") from exc
    if min(a, b, r) < 0:
        raise argparse.ArgumentTypeError("counts must be non-negative")
    return label, a, b, r


def optimistic_raw_p(a: int, b: int, remaining: int):
    """Smallest attainable p if every unresolved parent can become discordant.

    To maximize imbalance, all remaining discordances are assigned to the side
    that is already larger. If tied, either side is equivalent.
    This deliberately ignores cross-comparison dependence, so it is an
    optimistic lower bound on the attainable p-value.
    """
    if a >= b:
        aa, bb = a + remaining, b
    else:
        aa, bb = a, b + remaining
    return exact_two_sided_binom(min(aa, bb), aa + bb), aa, bb


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Optimistic reachability check for the four pre-registered 9x9 "
            "factorial Holm-corrected exact binomial tests."
        )
    )
    parser.add_argument(
        "comparison",
        nargs="+",
        type=parse_spec,
        help="LABEL:baseline_only:added_only:remaining",
    )
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()

    if not (0.0 < args.alpha < 1.0):
        raise SystemExit("--alpha must be between 0 and 1")
    labels = [x[0] for x in args.comparison]
    if len(set(labels)) != len(labels):
        raise SystemExit("duplicate comparison label")

    optimistic = []
    projected = []
    for label, a, b, r in args.comparison:
        p, aa, bb = optimistic_raw_p(a, b, r)
        optimistic.append(p)
        projected.append((label, a, b, r, aa, bb, p))

    adjusted = holm_adjust(optimistic)

    print(
        "Interpretation: every unresolved parent is assumed to become a "
        "discordance on the most favorable side independently for each "
        "comparison. Therefore these are optimistic lower bounds, not "
        "predictions."
    )
    print(
        "comparison,current_baseline_only,current_added_only,remaining,"
        "optimistic_baseline_only,optimistic_added_only,"
        "optimistic_raw_p,optimistic_holm_p,rejection_still_reachable"
    )
    any_reachable = False
    for row, p_adj in zip(projected, adjusted):
        label, a, b, r, aa, bb, p = row
        reachable = p_adj < args.alpha
        any_reachable |= reachable
        print(
            f"{label},{a},{b},{r},{aa},{bb},{p:.12g},{p_adj:.12g},"
            f"{int(reachable)}"
        )

    print(f"any_rejection_still_reachable={int(any_reachable)}")
    if not any_reachable:
        print(
            "All four comparisons are mathematically unable to reject under "
            "the pre-registered Holm family at the requested alpha, even "
            "under this deliberately over-optimistic completion."
        )


if __name__ == "__main__":
    main()
