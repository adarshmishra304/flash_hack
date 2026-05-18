"""
Multi-Pattern Search (Single-Pass Horspool-inspired)
DAA Concept: Extension of Horspool to handle multiple patterns in one pass
over the text — at each position, check all patterns simultaneously using
per-pattern shift tables, minimising total comparisons.
"""

from .horspool import build_shift_table


def multi_pattern_search(text, patterns):
    """
    DAA: Single-pass multi-pattern search. Builds a shift table per pattern,
    then for each alignment position applies the minimum shift across all
    patterns and checks each pattern whose last character aligns. This avoids
    re-scanning the text once per pattern, reducing total work significantly.
    Returns {pattern: [match_dicts]} and total comparisons across all patterns.
    """
    if not patterns or not text:
        return {p: [] for p in patterns}, 0

    tables = {p: build_shift_table(p) for p in patterns}
    results = {p: [] for p in patterns}
    comparisons = 0

    n = len(text)

    lines = text.split("\n")
    line_starts = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1

    def pos_to_line_col(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        ln = lo + 1
        col = pos - line_starts[lo] + 1
        return ln, col

    # Start at the position of the longest pattern's last char
    max_m = max(len(p) for p in patterns)
    i = max_m - 1

    while i < n:
        min_shift = max_m  # will pick minimum valid shift

        for p in patterns:
            m = len(p)
            if i < m - 1:
                continue  # pattern can't fit yet

            # Check alignment: compare right-to-left
            j = m - 1
            k = i
            matched = True
            while j >= 0:
                comparisons += 1
                if text[k] != p[j]:
                    matched = False
                    break
                j -= 1
                k -= 1

            if matched:
                pos = i - m + 1
                ln, col = pos_to_line_col(pos)
                ctx = lines[ln - 1] if ln <= len(lines) else ""
                results[p].append({"pos": pos, "line": ln, "col": col, "context": ctx})

            shift_char = text[i] if i < n else chr(0)
            shift = tables[p].get(shift_char, m)
            if shift < min_shift:
                min_shift = shift

        i += max(1, min_shift)

    return results, comparisons
