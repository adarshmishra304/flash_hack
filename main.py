"""
code-review-tool
Usage:
    python main.py <file>                          # review a file
    python main.py <file> --patterns patterns.txt  # custom patterns file
    python main.py <file> --output report.txt      # custom report output
    python main.py benchmark --file <file>         # Horspool vs Naive benchmark

Demonstrates:
  DAA : Horspool string matching with bad-character shift table
  OS  : Sequential access (line scan) + Direct access (seek for context)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algorithms.horspool import build_shift_table, horspool_search
from filesystem.direct import build_line_index, direct_read
from filesystem.sequential import sequential_read
from core.reporter import generate_report
from benchmark.generate_large_file import generate_large_file
from benchmark.compare import run_benchmark

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
    """
    DAA + OS: Full review pipeline for a single file.
      1. Print Horspool shift tables for all patterns (DAA).
      2. sequential_read() streams the file line-by-line (OS sequential).
      3. horspool_search() matches each pattern per line (DAA).
      4. direct_read() fetches ±2 context lines via seek (OS direct).
      5. Write structured report to disk and print summary.
    """
    if not os.path.exists(filepath):
        print("ERROR: file not found: {}".format(filepath))
        sys.exit(1)

    print("\n" + SEP)
    print("  CODE REVIEW")
    print("  File     : {}".format(os.path.abspath(filepath)))
    print("  Patterns : {}".format(", ".join(patterns)))
    print(SEP)

    # ── DAA: Horspool shift tables ────────────────────────────────────────────
    print("\n  [DAA] Horspool Bad-Character Shift Tables")
    print(THIN)
    for p in patterns:
        build_shift_table(p, verbose=True)

    # ── OS: build direct-access byte-offset index ─────────────────────────────
    line_index = build_line_index(filepath)
    total_lines = len(line_index)
    print("  [OS] Sequential scan starting  — {} lines to read".format(total_lines))
    print("  [OS] Direct-access index ready — {} byte offsets indexed".format(total_lines))
    print(THIN)

    # ── Scan: sequential pass + horspool per line ─────────────────────────────
    violations = []
    seen = set()  # (line_num, pattern) dedup

    for line_num, line_text in sequential_read(filepath):   # OS: sequential
        for pattern in patterns:
            if (line_num, pattern) in seen:
                continue
            matches, _ = horspool_search(line_text, pattern)  # DAA: horspool
            if not matches:
                continue
            seen.add((line_num, pattern))

            # OS: direct access — jump to surrounding lines for context
            surrounding = []
            for ln in range(max(1, line_num - 2), min(total_lines, line_num + 2) + 1):
                surrounding.append((ln, direct_read(filepath, line_index, ln)))

            violations.append({
                "file": filepath,
                "line": line_num,
                "pattern": pattern,
                "context": line_text,
                "surrounding": surrounding,
            })

    # ── Terminal output ───────────────────────────────────────────────────────
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

    # ── Write report ──────────────────────────────────────────────────────────
    meta = {
        "algorithm": "horspool",
        "patterns": patterns,
        "files_scanned": 1,
    }
    generate_report(violations, output, meta)


def cmd_benchmark(args):
    patterns = load_patterns(args.patterns if args.patterns else _DEFAULT_PATTERNS)
    if not os.path.exists(args.file):
        print("  Generating large test file...")
        generate_large_file(args.file, num_lines=12000)
    run_benchmark(args.file, patterns)


_USAGE = """\
Usage:
  script review <file>                           review a source file
  script review <file> --patterns <file.txt>     custom patterns file
  script review <file> --output   <report.txt>   custom output path
  script benchmark --file <file>                 Horspool vs Naive benchmark

Examples:
  script review myapp.py
  script review /path/to/utils.py --output my_report.txt
  script benchmark --file benchmark/large_test.py
"""


def main():
    argv = sys.argv[1:]

    if not argv:
        print(_USAGE)
        sys.exit(0)

    command = argv[0]

    # ── review ────────────────────────────────────────────────────────────────
    if command == "review":
        p = argparse.ArgumentParser(prog="script review")
        p.add_argument("file",       help="Source file to review")
        p.add_argument("--patterns", default=None,         help="Patterns file (default: patterns.txt)")
        p.add_argument("--output",   default="report.txt", help="Output report path")
        args = p.parse_args(argv[1:])
        patterns_path = args.patterns if args.patterns else _DEFAULT_PATTERNS
        patterns = load_patterns(patterns_path)
        review_file(args.file, patterns, args.output)

    # ── benchmark ─────────────────────────────────────────────────────────────
    elif command == "benchmark":
        p = argparse.ArgumentParser(prog="script benchmark")
        p.add_argument("--file",     required=True, help="File to benchmark on")
        p.add_argument("--patterns", default=None,  help="Patterns file (default: patterns.txt)")
        args = p.parse_args(argv[1:])
        cmd_benchmark(args)

    else:
        print("Unknown command: {!r}\n".format(command))
        print(_USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
