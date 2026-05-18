"""
Similarity Checker
DAA Concept: Uses longest common substring (LCS) with a sliding window
approach — O(n*m) — to detect potential copy-paste between files.
A score > 0.7 flags the pair as a likely copy.
"""

import os


def similarity_score(file1, file2):
    """
    DAA: Computes a similarity score between two files using the longest
    common substring length divided by max(len1, len2). The LCS search is
    implemented as a DP table (O(n*m)) operating at character level.
    Returns a float in [0.0, 1.0]; higher means more similar.
    """
    with open(file1, "r", encoding="utf-8", errors="replace") as fh:
        s1 = fh.read()
    with open(file2, "r", encoding="utf-8", errors="replace") as fh:
        s2 = fh.read()

    if not s1 or not s2:
        return 0.0

    n, m = len(s1), len(s2)
    # DP table for longest common substring
    # Use rolling arrays to keep memory O(min(n,m))
    if n < m:
        s1, s2, n, m = s2, s1, m, n

    prev = [0] * (m + 1)
    curr = [0] * (m + 1)
    longest = 0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > longest:
                    longest = curr[j]
            else:
                curr[j] = 0
        prev, curr = curr, [0] * (m + 1)

    score = longest / max(n, m)
    return round(score, 4)


def check_all_pairs(files):
    """
    DAA: Compares every (file1, file2) pair using similarity_score and
    returns pairs whose score exceeds 0.7 — a heuristic threshold for
    likely copy-paste. Complexity: O(k^2 * n * m) for k files of length n, m.
    Returns list of dicts: [{file1, file2, score}].
    """
    suspicious = []
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            score = similarity_score(files[i], files[j])
            if score > 0.7:
                suspicious.append({
                    "file1": files[i],
                    "file2": files[j],
                    "score": score,
                })
    return suspicious
