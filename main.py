"""
code-review-tool
Usage:
    script review <file>
    script review <file> --patterns <patterns.txt>
    script review <file> --output   <report.txt>
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algorithms.horspool import build_shift_table, horspool_search
from algorithms.naive import naive_search
from filesystem.sequential import sequential_read
from filesystem.direct import build_line_index, direct_read
from core.reporter import generate_report

_DEFAULT_PATTERNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns.txt")

SEP  = "=" * 60
THIN = "-" * 60


def load_patterns(path):
    if not os.path.exists(path):
        print("ERROR: patterns file not found: {}".format(path))
        sys.exit(1)
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def review_file(filepath, patterns, output):
    if not os.path.exists(filepath):
        print("ERROR: file not found: {}".format(filepath))
        sys.exit(1)

    print("\n" + SEP)
    print("  CODE REVIEW")
    print("  File     : {}".format(os.path.abspath(filepath)))
    print("  Patterns : {}".format(", ".join(patterns)))
    print(SEP)

    # DAA: print Horspool shift tables
    print("\n  [Horspool Shift Tables]")
    print(THIN)
    for p in patterns:
        build_shift_table(p, verbose=True)

    # ── Read full file text once (used by both algorithms) ────────────────────
    with open(filepath, "r", errors="replace") as fh:
        full_text = fh.read()

    # ── OS: sequential read pass (timed) ─────────────────────────────────────
    t0 = time.perf_counter()
    line_texts = {}
    for ln, text in sequential_read(filepath):
        line_texts[ln] = text
    seq_time = time.perf_counter() - t0
    total_lines = len(line_texts)

    # ── OS: build direct-access byte-offset index ─────────────────────────────
    line_index = build_line_index(filepath)

    print("  [Sequential] {} lines read in {:.2f} ms".format(total_lines, seq_time * 1000))
    print("  [Direct]     Byte-offset index built ({} entries)".format(total_lines))
    print(THIN)

    # ── DAA: run Naive + Horspool on full text per pattern (timed) ────────────
    daa_stats = []
    violations = []
    seen = set()

    direct_calls = 0
    direct_time  = 0.0

    for pattern in patterns:
        # Naive (for comparison metrics only)
        t0 = time.perf_counter()
        naive_matches, naive_cmp = naive_search(full_text, pattern)
        naive_t = time.perf_counter() - t0

        # Horspool (primary — used for violations)
        t0 = time.perf_counter()
        horse_matches, horse_cmp = horspool_search(full_text, pattern)
        horse_t = time.perf_counter() - t0

        daa_stats.append({
            "pattern":    pattern,
            "naive_cmp":  naive_cmp,
            "naive_time": naive_t,
            "naive_hits": len(naive_matches),
            "horse_cmp":  horse_cmp,
            "horse_time": horse_t,
            "horse_hits": len(horse_matches),
        })

        # Collect violations from horspool matches
        for m in horse_matches:
            ln = m["line"]
            if (ln, pattern) in seen:
                continue
            seen.add((ln, pattern))

            # OS: direct access to fetch surrounding context lines (timed)
            surrounding = []
            for ctx_ln in range(max(1, ln - 2), min(total_lines, ln + 2) + 1):
                t0 = time.perf_counter()
                ctx_text = direct_read(filepath, line_index, ctx_ln)
                direct_time += time.perf_counter() - t0
                direct_calls += 1
                surrounding.append((ctx_ln, ctx_text))

            violations.append({
                "file":       filepath,
                "line":       ln,
                "pattern":    pattern,
                "context":    line_texts.get(ln, ""),
                "surrounding": surrounding,
            })

    # ── Terminal: violations ──────────────────────────────────────────────────
    print("\n  RESULTS")
    print(SEP)

    if not violations:
        print("  No violations found.\n")
    else:
        by_pattern = {}
        for v in violations:
            by_pattern.setdefault(v["pattern"], []).append(v)

        for pattern, hits in by_pattern.items():
            print('\n  [PATTERN: "{}"]'.format(pattern))
            print(THIN)
            for h in sorted(hits, key=lambda x: x["line"]):
                print("    Line {:>4} |  {}".format(h["line"], h["context"].rstrip()))
                print("             Context:")
                for ctx_ln, ctx_text in h["surrounding"]:
                    marker = "  >>>" if ctx_ln == h["line"] else "     "
                    print("    {}  {:>4} |  {}".format(marker, ctx_ln, ctx_text.rstrip()))
                print()

    # ── Build comparison data for report ─────────────────────────────────────
    comparison = {
        "daa": daa_stats,
        "os": {
            "sequential_lines": total_lines,
            "sequential_time":  seq_time,
            "direct_calls":     direct_calls,
            "direct_time":      direct_time,
        },
    }

    meta = {
        "algorithm":    "horspool",
        "patterns":     patterns,
        "files_scanned": 1,
        "comparison":   comparison,
    }
    generate_report(violations, output, meta)


_USAGE = """\
Usage:
  script review <file>
  script review <file> --patterns <patterns.txt>
  script review <file> --output   <report.txt>
"""


def main():
    argv = sys.argv[1:]

    if not argv or argv[0] != "review":
        print(_USAGE)
        sys.exit(0)

    p = argparse.ArgumentParser(prog="script review")
    p.add_argument("file",       help="Source file to review")
    p.add_argument("--patterns", default=None,         help="Patterns file (default: patterns.txt)")
    p.add_argument("--output",   default="report.txt", help="Output report path")
    args = p.parse_args(argv[1:])

    patterns = load_patterns(args.patterns or _DEFAULT_PATTERNS)
    review_file(args.file, patterns, args.output)


if __name__ == "__main__":
    main()
