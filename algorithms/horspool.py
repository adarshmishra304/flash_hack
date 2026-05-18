"""
Boyer-Moore-Horspool String Matching Algorithm
DAA Concept: O(n/m) best-case via bad-character heuristic — preprocesses the
pattern into a shift table so mismatches allow large jumps, drastically
reducing comparisons compared to naive search.
"""


def build_shift_table(pattern, verbose=False):
    """
    DAA: Preprocessing step of Horspool — builds a 256-entry bad-character
    shift table. Default shift = len(pattern). For each char c in pattern
    (excluding last): shift[c] = len(pattern) - 1 - index. This tells us
    how far to jump when c appears as the last compared character in text.
    """
    m = len(pattern)
    table = {}

    # Default: all ASCII chars shift by full pattern length
    for i in range(256):
        table[chr(i)] = m

    # Override for chars that appear in pattern[0..m-2]
    for i in range(m - 1):
        table[pattern[i]] = m - 1 - i

    if verbose:
        print("\n  [Horspool] Bad-Character Shift Table for pattern: {!r}".format(pattern))
        print("  (showing only non-default entries; default shift = {})".format(m))
        non_default = {
            c: s for c, s in table.items()
            if s != m and c.isprintable()
        }
        if non_default:
            for c, s in sorted(non_default.items()):
                print("    '{}' -> shift {}".format(c, s))
        else:
            print("    (all characters use default shift)")
        print()

    return table


def horspool_search(text, pattern, verbose=False):
    """
    DAA: Horspool string search — aligns pattern right-to-left comparison,
    then uses the shift table on the text character under pattern's last
    position to skip positions. Far fewer comparisons than naive on average.
    Returns (matches, comparisons).
    """
    matches = []
    comparisons = 0
    n = len(text)
    m = len(pattern)

    if m == 0 or n == 0:
        return [], 0

    table = build_shift_table(pattern, verbose=verbose)

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
        line_num = lo + 1
        col = pos - line_starts[lo] + 1
        return line_num, col

    i = m - 1  # align pattern's last char with text[i]
    while i < n:
        j = m - 1
        k = i
        while j >= 0 and k >= 0:
            comparisons += 1
            if text[k] != pattern[j]:
                break
            j -= 1
            k -= 1

        if j == -1:
            pos = i - m + 1
            line_num, col = pos_to_line_col(pos)
            context_line = lines[line_num - 1] if line_num <= len(lines) else ""
            matches.append({
                "pos": pos,
                "line": line_num,
                "col": col,
                "context": context_line,
            })

        shift_char = text[i] if i < n else chr(0)
        i += table.get(shift_char, m)

    return matches, comparisons
