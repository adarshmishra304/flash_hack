"""
Sequential File Access
OS Concept: Simulates how an OS reads a file sequentially — lines are read
one after another from start to end, exactly as data is laid out on disk.
No random seeking is possible; every byte between start and target must be
traversed first (as with magnetic tapes or unbuffered streams).
"""


def sequential_read(filepath):
    """
    OS: Simulates OS sequential file access — reads lines strictly top to
    bottom, yielding (line_number, line_text) one at a time without buffering
    the entire file. Mirrors how sequential storage devices expose data:
    no jumps, no random access — just a forward-only stream.
    """
    # Simulates OS sequential file access
    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
        line_number = 1
        for line in fh:
            yield line_number, line.rstrip("\n")
            line_number += 1
