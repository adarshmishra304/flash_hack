"""
Benchmark: Horspool vs Naive
DAA Concept: Empirically measures time and comparison-count differences
between Naive O(n*m) and Horspool O(n/m) best-case search over a large
real-world-like file, making the theoretical gap concrete.
"""

import time
import os
from algorithms.naive import naive_search
from algorithms.horspool import horspool_search, build_shift_table


def _count_lines(filepath):
    count = 0
    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
        for _ in fh:
            count += 1
    return count


def run_benchmark(filepath, patterns):
    """
    DAA: Benchmarks naive_search vs horspool_search on every pattern over
    the given file. Measures wall-clock time and exact comparison counts,
    then prints a formatted comparison table showing speedup. Prints the
    Horspool shift table for each pattern before the table for educational
    transparency.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    num_lines = _count_lines(filepath)

    sep  = "=" * 68
    thin = "-" * 68

    print("\n" + sep)
    print("  BENCHMARK: Horspool vs Naive String Matching")
    print("  File: {} | Lines: {:,} | Patterns: {}".format(
        os.path.basename(filepath), num_lines, len(patterns)))
    print(sep)

    # Print shift tables
    print("\n  [Horspool Shift Tables]")
    for pattern in patterns:
        build_shift_table(pattern, verbose=True)

    # Run searches
    results = []
    for pattern in patterns:
        t0 = time.perf_counter()
        naive_matches, naive_cmp = naive_search(text, pattern)
        t_naive = time.perf_counter() - t0

        t0 = time.perf_counter()
        horse_matches, horse_cmp = horspool_search(text, pattern, verbose=False)
        t_horse = time.perf_counter() - t0

        results.append({
            "pattern": pattern,
            "naive_time": t_naive,
            "naive_cmp": naive_cmp,
            "naive_hits": len(naive_matches),
            "horse_time": t_horse,
            "horse_cmp": horse_cmp,
            "horse_hits": len(horse_matches),
        })

    # Table header
    print(sep)
    print("{:<18} {:<12} {:>10} {:>14}  {:>6}".format(
        "Pattern", "Algorithm", "Time (s)", "Comparisons", "Hits"))
    print(thin)

    total_naive_time = 0.0
    total_naive_cmp  = 0
    total_horse_time = 0.0
    total_horse_cmp  = 0

    for r in results:
        pat = r["pattern"][:16]
        print("{:<18} {:<12} {:>10.4f} {:>14,}  {:>6}".format(
            pat, "Naive", r["naive_time"], r["naive_cmp"], r["naive_hits"]))
        print("{:<18} {:<12} {:>10.4f} {:>14,}  {:>6}".format(
            "", "Horspool", r["horse_time"], r["horse_cmp"], r["horse_hits"]))
        print(thin)
        total_naive_time += r["naive_time"]
        total_naive_cmp  += r["naive_cmp"]
        total_horse_time += r["horse_time"]
        total_horse_cmp  += r["horse_cmp"]

    print("{:<18} {:<12} {:>10.4f} {:>14,}".format(
        "TOTAL", "Naive", total_naive_time, total_naive_cmp))
    print("{:<18} {:<12} {:>10.4f} {:>14,}".format(
        "TOTAL", "Horspool", total_horse_time, total_horse_cmp))
    print(thin)

    if total_horse_cmp > 0:
        speedup = total_naive_cmp / total_horse_cmp
        time_ratio = total_naive_time / total_horse_time if total_horse_time > 0 else float("inf")
        print("  Speedup: {:.2f}x fewer comparisons with Horspool".format(speedup))
        print("  Time  : {:.2f}x faster with Horspool".format(time_ratio))

    print(sep + "\n")
