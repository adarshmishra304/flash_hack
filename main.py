"""
code-review-tool — CLI entry point
Demonstrates:
  DAA : Naive and Horspool string matching, multi-pattern search, LCS similarity
  OS  : Sequential file access (forward-only stream) and direct/random access (seek)
"""

import argparse
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algorithms.horspool import build_shift_table
from filesystem.sequential import sequential_read
from filesystem.direct import build_line_index, direct_read
from core.scanner import scan_directory
from core.reporter import generate_report
from core.similarity import similarity_score, check_all_pairs
from benchmark.generate_large_file import generate_large_file
from benchmark.compare import run_benchmark


# ── helpers ──────────────────────────────────────────────────────────────────

def load_patterns(path):
    """Read patterns file, one pattern per non-blank line."""
    if not os.path.exists(path):
        print("ERROR: patterns file not found: {}".format(path))
        sys.exit(1)
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def collect_py_files(directory):
    """Return all .py files under directory."""
    files = []
    for root, _dirs, fnames in os.walk(directory):
        for f in fnames:
            if f.endswith(".py"):
                files.append(os.path.join(root, f))
    return sorted(files)


# ── sub-commands ──────────────────────────────────────────────────────────────

def cmd_scan(args):
    """
    Scan a directory for pattern violations using the chosen algorithm.
    Uses sequential access for scanning and direct access for context.
    """
    patterns = load_patterns(args.patterns)
    algorithm = args.algorithm

    print("\n" + "=" * 56)
    print("  CODE REVIEW TOOL — Scan")
    print("  Directory : {}".format(args.dir))
    print("  Patterns  : {}".format(", ".join(patterns)))
    print("  Algorithm : {}".format(algorithm.title()))
    print("=" * 56)

    if algorithm == "horspool":
        print("\n  [Horspool Shift Tables — one per pattern]")
        for p in patterns:
            build_shift_table(p, verbose=True)

    source_files = []
    for root, _dirs, files in os.walk(args.dir):
        for f in sorted(files):
            if os.path.splitext(f)[1] in {".py", ".c", ".java"}:
                source_files.append(os.path.join(root, f))

    print("  Scanning {} file(s)...\n".format(len(source_files)))

    violations = scan_directory(args.dir, patterns, algorithm=algorithm, verbose=False)

    meta = {
        "algorithm": algorithm,
        "patterns": patterns,
        "files_scanned": len(source_files),
    }
    generate_report(violations, args.output, meta)


def cmd_benchmark(args):
    """
    Generate a large test file (if needed) and benchmark Naive vs Horspool.
    """
    patterns = load_patterns(args.patterns)

    large_file = args.file
    if not os.path.exists(large_file):
        print("\n  Generating large test file...")
        generate_large_file(large_file, num_lines=12000)

    run_benchmark(large_file, patterns)


def cmd_similarity(args):
    """
    Compare all .py files in a directory for copy-paste similarity using LCS.
    """
    files = collect_py_files(args.dir)
    if len(files) < 2:
        print("Need at least 2 Python files to compare.")
        return

    sep  = "=" * 56
    thin = "-" * 56

    print("\n" + sep)
    print("  SIMILARITY CHECK  (LCS-based, threshold > 0.70)")
    print("  Directory: {}".format(args.dir))
    print(sep)
    print("  Files found:")
    for f in files:
        print("    - {}".format(os.path.relpath(f)))
    print(thin)

    suspicious = check_all_pairs(files)

    if not suspicious:
        print("\n  No suspiciously similar file pairs found (all scores <= 0.70).\n")
    else:
        print("\n  Suspicious pairs:")
        for pair in suspicious:
            print("    {:.4f}  {}  <-->  {}".format(
                pair["score"],
                os.path.relpath(pair["file1"]),
                os.path.relpath(pair["file2"]),
            ))
        print()

    # Show all pair scores for completeness
    print("  All pairwise scores:")
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            score = similarity_score(files[i], files[j])
            flag = "  <<< SUSPICIOUS" if score > 0.70 else ""
            print("    {:.4f}  {}  <-->  {}{}".format(
                score,
                os.path.relpath(files[i]),
                os.path.relpath(files[j]),
                flag,
            ))
    print()
    print(sep + "\n")


def cmd_demo_access(args):
    """
    Demonstrate OS sequential vs direct file access methods side-by-side.
    """
    filepath = args.file
    if not os.path.exists(filepath):
        print("ERROR: file not found: {}".format(filepath))
        sys.exit(1)

    sep  = "=" * 60
    thin = "-" * 60

    print("\n" + sep)
    print("  OS FILE ACCESS DEMO")
    print("  File: {}".format(filepath))
    print(sep)

    # ── 1. Sequential Access ─────────────────────────────────────────────────
    print("""
  [1] SEQUENTIAL ACCESS
  ┌─────────────────────────────────────────────────────────┐
  │ OS Concept: Sequential access reads bytes in order,     │
  │ from start to end, like a tape drive or unbuffered      │
  │ stream. No seeking is possible — to reach line N you    │
  │ must first pass through lines 1 to N-1.                 │
  └─────────────────────────────────────────────────────────┘
  Reading first 5 lines one-by-one via sequential_read():
""")
    for ln, text in sequential_read(filepath):
        print("    Line {:>3} | {}".format(ln, text))
        if ln >= 5:
            break

    # ── 2. Direct Access ─────────────────────────────────────────────────────
    print("""
  [2] DIRECT / RANDOM ACCESS
  ┌─────────────────────────────────────────────────────────┐
  │ OS Concept: Direct access uses a pre-built index of     │
  │ byte offsets (like a disk's block address table).       │
  │ file.seek(offset) jumps instantly to any line — O(1)   │
  │ retrieval after a one-time O(n) indexing pass.          │
  └─────────────────────────────────────────────────────────┘
  Building byte-offset index with build_line_index()...
""")
    line_index = build_line_index(filepath)
    total = len(line_index)
    print("    Index built: {} lines indexed.\n".format(total))

    target_lines = [10, 30, 55]
    print("  Jumping directly to lines {} via direct_read():".format(target_lines))
    for target in target_lines:
        if target > total:
            print("    Line {:>3} | (beyond file length of {})".format(target, total))
            continue
        offset = line_index[target]
        text = direct_read(filepath, line_index, target)
        print("    Line {:>3} | [byte offset {:>6}] | {}".format(target, offset, text))

    print("""
  [COMPARISON SUMMARY]
  ┌──────────────────┬──────────────────────────────────────┐
  │ Sequential       │ Reads every byte from top; no jumps. │
  │                  │ Cost: O(n) to reach line n.          │
  ├──────────────────┼──────────────────────────────────────┤
  │ Direct (seek)    │ Jumps to any line in O(1) after a    │
  │                  │ one-time O(n) index build.           │
  │                  │ Ideal for repeated random lookups.   │
  └──────────────────┴──────────────────────────────────────┘
""")
    print(sep + "\n")


# ── argument parser ──────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="code-review-tool",
        description="CLI code review tool — DAA (string matching) + OS (file access) demo",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="Scan directory for pattern violations")
    p_scan.add_argument("--dir",       required=True,  help="Directory to scan")
    p_scan.add_argument("--patterns",  required=True,  help="Path to patterns file")
    p_scan.add_argument("--output",    default="report.txt", help="Output report path")
    p_scan.add_argument("--algorithm", default="horspool", choices=["horspool", "naive"],
                        help="Search algorithm (default: horspool)")

    # benchmark
    p_bench = sub.add_parser("benchmark", help="Benchmark Horspool vs Naive on a large file")
    p_bench.add_argument("--file",     required=True,  help="Large test file path")
    p_bench.add_argument("--patterns", required=True,  help="Path to patterns file")

    # similarity
    p_sim = sub.add_parser("similarity", help="Detect copy-paste between files")
    p_sim.add_argument("--dir",        required=True,  help="Directory with .py files")

    # demo-access
    p_demo = sub.add_parser("demo-access", help="Demonstrate sequential vs direct file access")
    p_demo.add_argument("--file",      required=True,  help="Source file to demonstrate with")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "scan":        cmd_scan,
        "benchmark":   cmd_benchmark,
        "similarity":  cmd_similarity,
        "demo-access": cmd_demo_access,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
