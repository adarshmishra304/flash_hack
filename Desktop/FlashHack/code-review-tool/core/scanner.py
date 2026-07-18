"""
Directory Scanner
Combines DAA (string matching) and OS (file access) concepts:
  - Sequential access to scan each file line-by-line (OS)
  - Horspool or Naive search on each line (DAA)
  - Direct access to fetch surrounding context lines (OS)
"""

import os
from filesystem.sequential import sequential_read
from filesystem.direct import build_line_index, direct_read
from algorithms.horspool import horspool_search
from algorithms.naive import naive_search

_SUPPORTED_EXTS = {".py", ".c", ".java"}


def _collect_files(directory):
    """Walk directory tree and return paths of supported source files."""
    collected = []
    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if os.path.splitext(fname)[1] in _SUPPORTED_EXTS:
                collected.append(os.path.join(root, fname))
    return collected


def scan_directory(directory, patterns, algorithm="horspool", verbose=True):
    """
    DAA + OS: Orchestrates a full directory scan.
    - OS sequential_read drives the per-line iteration (sequential access).
    - DAA horspool_search or naive_search detects pattern occurrences.
    - OS direct_read fetches ±2 surrounding lines for context (direct access).
    Returns a list of violation dicts, one per (file, line, pattern) hit.
    """
    search_fn = horspool_search if algorithm == "horspool" else naive_search

    source_files = _collect_files(directory)
    all_violations = []

    for filepath in source_files:
        # --- OS: build direct-access index once per file ---
        line_index = build_line_index(filepath)
        total_lines = len(line_index)

        # --- OS: sequential pass to get full text for algorithm ---
        line_texts = {}
        for ln, text in sequential_read(filepath):
            line_texts[ln] = text

        full_text = "\n".join(line_texts.get(i, "") for i in range(1, total_lines + 1))

        for pattern in patterns:
            if verbose and algorithm == "horspool":
                matches, _ = search_fn(full_text, pattern, verbose=False)
            else:
                matches, _ = search_fn(full_text, pattern)

            seen_lines = set()
            for m in matches:
                ln = m["line"]
                if ln in seen_lines:
                    continue
                seen_lines.add(ln)

                # --- OS: direct access for surrounding context ---
                surrounding = []
                for offset in [-2, -1, 1, 2]:
                    target = ln + offset
                    if 1 <= target <= total_lines:
                        surrounding.append((target, direct_read(filepath, line_index, target)))
                    else:
                        surrounding.append((target, None))

                all_violations.append({
                    "file": filepath,
                    "line": ln,
                    "pattern": pattern,
                    "context": line_texts.get(ln, ""),
                    "surrounding": surrounding,
                })

    return all_violations
