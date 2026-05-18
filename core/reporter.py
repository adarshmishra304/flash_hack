"""
Report Generator — formats violations + algorithm comparison into terminal
output and a structured report file.
"""

import os
from datetime import datetime


def _daa_table_lines(daa_stats, sep_char="-", width=62):
    """Build the DAA comparison table as a list of strings."""
    thin = sep_char * width
    lines = []
    lines.append("  DAA: Naive vs Horspool (comparisons made per pattern)")
    lines.append(thin)
    lines.append("  {:<16} {:>12} {:>12} {:>8} {:>6}".format(
        "Pattern", "Naive Cmps", "Horse Cmps", "Speedup", "Hits"))
    lines.append(thin)

    total_naive = total_horse = 0
    for s in daa_stats:
        speedup = (s["naive_cmp"] / s["horse_cmp"]) if s["horse_cmp"] else float("inf")
        lines.append("  {:<16} {:>12,} {:>12,} {:>7.2f}x {:>5}".format(
            s["pattern"][:16],
            s["naive_cmp"],
            s["horse_cmp"],
            speedup,
            s["horse_hits"],
        ))
        total_naive += s["naive_cmp"]
        total_horse += s["horse_cmp"]

    lines.append(thin)
    total_speedup = (total_naive / total_horse) if total_horse else float("inf")
    lines.append("  {:<16} {:>12,} {:>12,} {:>7.2f}x".format(
        "TOTAL", total_naive, total_horse, total_speedup))
    lines.append("  Horspool made {:.2f}x fewer comparisons than Naive".format(total_speedup))
    return lines


def _os_table_lines(os_stats, sep_char="-", width=62):
    """Build the OS access comparison table as a list of strings."""
    thin = sep_char * width
    lines = []
    lines.append("  OS: Sequential vs Direct File Access")
    lines.append(thin)
    lines.append("  {:<28} {:>12} {:>12}".format("Method", "Count", "Time (ms)"))
    lines.append(thin)

    seq_ms = os_stats["sequential_time"] * 1000
    dir_ms = os_stats["direct_time"] * 1000

    lines.append("  {:<28} {:>12} {:>11.3f}".format(
        "Sequential read (scan pass)",
        "{:,} lines".format(os_stats["sequential_lines"]),
        seq_ms,
    ))
    lines.append("  {:<28} {:>12} {:>11.3f}".format(
        "Direct seek (context fetch)",
        "{:,} seeks".format(os_stats["direct_calls"]),
        dir_ms,
    ))
    lines.append(thin)
    lines.append("  Sequential: forward-only stream — reads every line once")
    lines.append("  Direct    : file.seek(offset) jumps instantly to any line")
    if dir_ms > 0:
        lines.append("  Ratio     : {:.2f}x more time in sequential (larger scope)".format(
            seq_ms / dir_ms if dir_ms else 0))
    return lines


def _print_comparison(comparison):
    """Print the full comparison section to the terminal."""
    daa   = comparison.get("daa", [])
    os_st = comparison.get("os", {})
    sep   = "=" * 62
    thin  = "-" * 62

    print("\n" + sep)
    print("  ALGORITHM & ACCESS METHOD COMPARISON")
    print(sep)

    if daa:
        print()
        for ln in _daa_table_lines(daa):
            print(ln)

    if os_st:
        print()
        for ln in _os_table_lines(os_st):
            print(ln)

    print()
    print(sep)


def _format_comparison(comparison):
    """Return the comparison section as a list of strings for the file report."""
    daa   = comparison.get("daa", [])
    os_st = comparison.get("os", {})
    sep   = "=" * 62
    lines = []

    lines.append(sep)
    lines.append("  ALGORITHM & ACCESS METHOD COMPARISON")
    lines.append(sep)

    if daa:
        lines.append("")
        lines.extend(_daa_table_lines(daa))

    if os_st:
        lines.append("")
        lines.extend(_os_table_lines(os_st))

    lines.append("")
    lines.append(sep)
    return lines


def generate_report(violations, output_path, meta):
    """
    Writes a structured report to output_path and prints a summary to the
    terminal. Includes a comparison table showing Naive vs Horspool (DAA)
    and Sequential vs Direct access (OS).
    """
    algorithm    = meta.get("algorithm", "horspool").title()
    patterns     = meta.get("patterns", [])
    files_scanned = meta.get("files_scanned", 0)
    comparison   = meta.get("comparison", {})
    timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    by_file = {}
    for v in violations:
        by_file.setdefault(v["file"], {}).setdefault(v["pattern"], []).append(v)

    sep  = "=" * 62
    thin = "-" * 62

    # ── Build file report ─────────────────────────────────────────────────────
    report_lines = []
    report_lines.append(sep)
    report_lines.append("  CODE REVIEW REPORT")
    report_lines.append("  Generated : {}".format(timestamp))
    report_lines.append("  Algorithm : {}".format(algorithm))
    report_lines.append(sep)
    report_lines.append("")

    for filepath, pat_dict in sorted(by_file.items()):
        report_lines.append("FILE: {}".format(filepath))
        report_lines.append(thin)
        for pattern, vlist in sorted(pat_dict.items()):
            report_lines.append('  [PATTERN: "{}"]'.format(pattern))
            for v in sorted(vlist, key=lambda x: x["line"]):
                ln  = v["line"]
                ctx = v["context"]
                report_lines.append("    Line {:>4} | {}".format(ln, ctx.rstrip()))
                report_lines.append("      Context:")
                for surr_ln, surr_text in v["surrounding"]:
                    if surr_text is None:
                        continue
                    marker = "  > " if surr_ln == ln else "    "
                    report_lines.append("  {}  {:>4} | {}".format(marker, surr_ln, surr_text.rstrip()))
            report_lines.append("")
        report_lines.append("")

    report_lines.append(sep)
    report_lines.append("  SUMMARY")
    report_lines.append("    Files scanned    : {}".format(files_scanned))
    report_lines.append("    Violations found : {}".format(len(violations)))
    report_lines.append("    Patterns checked : {}".format(", ".join(patterns)))
    report_lines.append(sep)
    report_lines.append("")

    if comparison:
        report_lines.extend(_format_comparison(comparison))

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(report_lines))

    # ── Terminal: summary ─────────────────────────────────────────────────────
    print("\n" + sep)
    print("  SUMMARY")
    print(sep)

    if by_file:
        for filepath, pat_dict in sorted(by_file.items()):
            rel = os.path.relpath(filepath)
            total_hits = sum(len(vl) for vl in pat_dict.values())
            print("\n  FILE: {} — {} violation{}".format(
                rel, total_hits, "s" if total_hits != 1 else ""))
            for pattern, vlist in sorted(pat_dict.items()):
                lnums = ", ".join(
                    str(v["line"]) for v in sorted(vlist, key=lambda x: x["line"]))
                print('    [PATTERN: "{}"]: lines {}'.format(pattern, lnums))
    else:
        print("\n  No violations found.")

    print("\n" + thin)
    print("  Files scanned    : {}".format(files_scanned))
    print("  Violations found : {}".format(len(violations)))
    print("  Patterns checked : {}".format(", ".join(patterns)))
    print("  Report written   : {}".format(output_path))
    print(sep)

    # ── Terminal: comparison tables ───────────────────────────────────────────
    if comparison:
        _print_comparison(comparison)
