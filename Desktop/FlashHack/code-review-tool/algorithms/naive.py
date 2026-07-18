"""
Naive (Brute-Force) String Matching Algorithm
DAA Concept: O(n*m) worst-case — slides pattern one position at a time,
comparing every character without any intelligence about mismatches.
"""


def naive_search(text, pattern):
    """
    DAA: Naive string matching — slides pattern left to right, character by
    character. No preprocessing; every mismatch causes a shift of exactly 1.
    Returns (matches, comparisons) where matches is a list of dicts with
    position, line, column, and context for each occurrence found.
    """
    matches = []
    comparisons = 0
    n = len(text)
    m = len(pattern)

    if m == 0 or n == 0:
        return [], 0

    lines = text.split("\n")
    line_starts = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1  # +1 for newline

    def pos_to_line_col(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        line_num = lo + 1
        col = pos - line_starts[lo] + 1
        return line_num, col

    for i in range(n - m + 1):
        j = 0
        while j < m:
            comparisons += 1
            if text[i + j] != pattern[j]:
                break
            j += 1
        if j == m:
            line_num, col = pos_to_line_col(i)
            context_line = lines[line_num - 1] if line_num <= len(lines) else ""
            matches.append({
                "pos": i,
                "line": line_num,
                "col": col,
                "context": context_line,
            })

    return matches, comparisons
