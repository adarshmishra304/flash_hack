"""
Report Generator
Produces both a structured file report and a terminal summary of all
violations found during a scan. Groups output by file then by pattern
for easy review.
"""

import os
from datetime import datetime


def generate_report(violations, output_path, meta):
    """
    Formats violations into a structured report written to output_path and
    summarised on the terminal. Groups by file, then by pattern.
    meta dict must contain: algorithm (str), patterns (list), files_scanned (int).
    """
    algorithm = meta.get("algorithm", "horspool").title()
    patterns = meta.get("patterns", [])
    files_scanned = meta.get("files_scanned", 0)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Group: file -> pattern -> [violations]
    by_file = {}
    for v in violations:
        fp = v["file"]
        pat = v["pattern"]
        by_file.setdefault(fp, {}).setdefault(pat, []).append(v)

    lines = []
    sep = "=" * 56
    thin = "-" * 56

    lines.append(sep)
    lines.append("  CODE REVIEW REPORT")
    lines.append("  Generated : {}".format(timestamp))
    lines.append("  Algorithm : {}".format(algorithm))
    lines.append(sep)
    lines.append("")

    for filepath, pat_dict in sorted(by_file.items()):
        lines.append("FILE: {}".format(filepath))
        lines.append(thin)
        for pattern, vlist in sorted(pat_dict.items()):
            lines.append('  [PATTERN: "{}"]'.format(pattern))
            for v in sorted(vlist, key=lambda x: x["line"]):
                ln = v["line"]
                ctx = v["context"]
                lines.append("    Line {:>4} | {}".format(ln, ctx))
                lines.append("      Context:")
                for surr_ln, surr_text in v["surrounding"]:
                    if surr_text is None:
                        continue
                    marker = "  > " if surr_ln == ln else "    "
                    lines.append("  {}  {:>4} | {}".format(marker, surr_ln, surr_text))
            lines.append("")
        lines.append("")

    lines.append(sep)
    lines.append("  SUMMARY")
    lines.append("    Files scanned    : {}".format(files_scanned))
    lines.append("    Violations found : {}".format(len(violations)))
    lines.append("    Patterns checked : {}".format(", ".join(patterns)))
    lines.append(sep)

    report_text = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    # Terminal summary
    print("\n" + sep)
    print("  CODE REVIEW REPORT SUMMARY")
    print("  Generated : {}".format(timestamp))
    print("  Algorithm : {}".format(algorithm))
    print(sep)

    for filepath, pat_dict in sorted(by_file.items()):
        rel = os.path.relpath(filepath)
        total_hits = sum(len(vl) for vl in pat_dict.values())
        print("\n  FILE: {} ({} violation{})".format(
            rel, total_hits, "s" if total_hits != 1 else ""))
        for pattern, vlist in sorted(pat_dict.items()):
            lnums = ", ".join(str(v["line"]) for v in sorted(vlist, key=lambda x: x["line"]))
            print('    [PATTERN: "{}"]: lines {}'.format(pattern, lnums))

    print("\n" + thin)
    print("  Files scanned    : {}".format(files_scanned))
    print("  Violations found : {}".format(len(violations)))
    print("  Patterns checked : {}".format(", ".join(patterns)))
    print("  Report written   : {}".format(output_path))
    print(sep + "\n")
