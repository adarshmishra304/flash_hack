"""
Direct (Random) File Access
OS Concept: Simulates how an OS supports direct/random access — by recording
the byte offset of each line's start during a one-time index pass, we can
later use file.seek() to jump instantly to any line. This mirrors how OSes
expose block-addressed storage: O(1) random reads after O(n) indexing.
"""


def build_line_index(filepath):
    """
    OS: Builds a byte-offset index for direct file access. Reads the file
    once sequentially to record where each line starts in the file. After
    this one-time cost, any line can be fetched in O(1) via seek — analogous
    to an OS maintaining an inode / FAT entry for direct block lookup.
    Returns {line_number: byte_offset}.
    """
    index = {}
    with open(filepath, "rb") as fh:
        line_number = 1
        while True:
            offset = fh.tell()
            line = fh.readline()
            if not line:
                break
            index[line_number] = offset
            line_number += 1
    return index


def direct_read(filepath, line_index, line_number):
    """
    OS: Simulates OS direct/random file access — uses file.seek(byte_offset)
    to jump directly to the requested line without reading any preceding
    bytes. This is the OS equivalent of seeking to a specific disk block
    using its logical block address (LBA), enabling O(1) retrieval.
    Returns the line text (stripped of trailing newline).
    """
    # Simulates OS direct/random file access
    offset = line_index.get(line_number)
    if offset is None:
        return ""
    with open(filepath, "rb") as fh:
        fh.seek(offset)
        line = fh.readline()
    return line.decode("utf-8", errors="replace").rstrip("\n")
