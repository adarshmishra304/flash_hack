"""
code-review-tool
Usage:
    script review       <file>              algorithm scan only
    script agent-review <file>              algorithm scan + Claude agent
    script review       <file> --patterns <patterns.txt>
    script review       <file> --output   <report.txt>
    script agent-review <file> --output   <report.txt>
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env from the project root if it exists
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _v = _v.strip()
                if _v and not os.environ.get(_k.strip()):
                    os.environ[_k.strip()] = _v

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


def run_scan(filepath, patterns):
    """
    Core scan pipeline — returns (violations, comparison_data).
    Runs Naive + Horspool on the full file text, collects timing and
    comparison counts, uses direct access to fetch violation context.
    """
    with open(filepath, "r", errors="replace") as fh:
        full_text = fh.read()

    # OS: sequential read pass (timed)
    t0 = time.perf_counter()
    line_texts = {}
    for ln, text in sequential_read(filepath):
        line_texts[ln] = text
    seq_time = time.perf_counter() - t0
    total_lines = len(line_texts)

    # OS: build direct-access byte-offset index
    line_index = build_line_index(filepath)

    print("  [Sequential] {} lines read in {:.2f} ms".format(total_lines, seq_time * 1000))
    print("  [Direct]     Byte-offset index built ({} entries)".format(total_lines))
    print(THIN)

    daa_stats  = []
    violations = []
    seen       = set()
    direct_calls = 0
    direct_time  = 0.0

    for pattern in patterns:
        # DAA: Naive (metrics only)
        t0 = time.perf_counter()
        _, naive_cmp = naive_search(full_text, pattern)
        naive_t = time.perf_counter() - t0

        # DAA: Horspool (primary)
        t0 = time.perf_counter()
        horse_matches, horse_cmp = horspool_search(full_text, pattern)
        horse_t = time.perf_counter() - t0

        daa_stats.append({
            "pattern":    pattern,
            "naive_cmp":  naive_cmp,
            "naive_time": naive_t,
            "naive_hits": len(horse_matches),
            "horse_cmp":  horse_cmp,
            "horse_time": horse_t,
            "horse_hits": len(horse_matches),
        })

        for m in horse_matches:
            ln = m["line"]
            if (ln, pattern) in seen:
                continue
            seen.add((ln, pattern))

            # OS: direct access for surrounding context
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

    comparison = {
        "daa": daa_stats,
        "os": {
            "sequential_lines": total_lines,
            "sequential_time":  seq_time,
            "direct_calls":     direct_calls,
            "direct_time":      direct_time,
        },
    }
    return violations, comparison


def print_violations(violations):
    """Print the violations section to the terminal."""
    print("\n  RESULTS")
    print(SEP)

    if not violations:
        print("  No violations found.\n")
        return

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


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_review(filepath, patterns, output):
    """Algorithm-only review: Horspool scan + comparison report."""
    print("\n" + SEP)
    print("  CODE REVIEW")
    print("  File     : {}".format(os.path.abspath(filepath)))
    print("  Patterns : {}".format(", ".join(patterns)))
    print(SEP)

    print("\n  [Horspool Shift Tables]")
    print(THIN)
    for p in patterns:
        build_shift_table(p, verbose=True)

    violations, comparison = run_scan(filepath, patterns)
    print_violations(violations)

    meta = {
        "algorithm":    "horspool",
        "patterns":     patterns,
        "files_scanned": 1,
        "comparison":   comparison,
    }
    generate_report(violations, output, meta)


def cmd_agent_review(filepath, patterns, output):
    """Full agentic review: algorithm scan first, then Claude agent analysis."""
    from agents.reviewer import AgentReviewer

    print("\n" + SEP)
    print("  AGENT REVIEW")
    print("  File     : {}".format(os.path.abspath(filepath)))
    print("  Patterns : {}".format(", ".join(patterns)))
    print(SEP)

    print("\n  [Horspool Shift Tables]")
    print(THIN)
    for p in patterns:
        build_shift_table(p, verbose=True)

    violations, comparison = run_scan(filepath, patterns)
    print_violations(violations)

    meta = {
        "algorithm":    "horspool",
        "patterns":     patterns,
        "files_scanned": 1,
        "comparison":   comparison,
    }
    generate_report(violations, output, meta)

    # Hand off to Claude agent
    agent = AgentReviewer()
    agent.run(violations, filepath, output)


# ── CLI ───────────────────────────────────────────────────────────────────────

_USAGE = """\
Usage:
  script review       <file>                      algorithm scan only
  script agent-review <file>                      scan + Claude agent review
  script review       <file> --patterns <file>    custom patterns
  script review       <file> --output   <file>    custom output path
"""


def _make_parser(prog):
    p = argparse.ArgumentParser(prog=prog)
    p.add_argument("file",       help="Source file to review")
    p.add_argument("--patterns", default=None,         help="Patterns file (default: patterns.txt)")
    p.add_argument("--output",   default="report.txt", help="Output report path")
    return p


def main():
    argv = sys.argv[1:]

    if not argv:
        print(_USAGE)
        sys.exit(0)

    command = argv[0]

    if command == "review":
        args     = _make_parser("script review").parse_args(argv[1:])
        patterns = load_patterns(args.patterns or _DEFAULT_PATTERNS)
        cmd_review(args.file, patterns, args.output)

    elif command == "agent-review":
        args     = _make_parser("script agent-review").parse_args(argv[1:])
        patterns = load_patterns(args.patterns or _DEFAULT_PATTERNS)
        cmd_agent_review(args.file, patterns, args.output)

    else:
        print("Unknown command: {!r}\n".format(command))
        print(_USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
