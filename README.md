# code-review-tool

A CLI-based static code reviewer demonstrating two core CS concepts:

- **DAA** — Naive and Horspool string-matching algorithms, multi-pattern search, LCS similarity
- **OS** — Sequential (forward-only) and Direct (seek-based) file access methods

---

## Project Structure

```
code-review-tool/
├── main.py                      # CLI entry point (argparse)
├── patterns.txt                 # Banned patterns, one per line
├── algorithms/
│   ├── naive.py                 # Brute-force O(n·m) search
│   ├── horspool.py              # Boyer-Moore-Horspool with shift table
│   └── multi_pattern.py        # Single-pass search for N patterns
├── filesystem/
│   ├── sequential.py            # OS sequential access (yield line by line)
│   └── direct.py               # OS direct access (byte-offset index + seek)
├── core/
│   ├── scanner.py               # Directory walk; combines OS + DAA
│   ├── reporter.py              # Structured report writer
│   └── similarity.py           # LCS-based copy-paste detector
├── benchmark/
│   ├── generate_large_file.py  # Produces 12 000-line synthetic Python file
│   └── compare.py              # Horspool vs Naive timing + comparison table
└── sample_code/                 # Three realistic Python files with violations
```

---

## How to Run

### 1. Scan a directory

```bash
python main.py scan --dir ./sample_code --patterns patterns.txt
python main.py scan --dir ./sample_code --patterns patterns.txt --output report.txt
python main.py scan --dir ./sample_code --patterns patterns.txt --algorithm naive
```

Walks the directory, runs the chosen algorithm on every `.py / .c / .java` file,
prints the Horspool shift table for each pattern, and writes a full report.

### 2. Benchmark

```bash
python main.py benchmark --file ./benchmark/large_test.py --patterns patterns.txt
```

Generates `large_test.py` (12 000 lines) if it does not exist, then runs both
algorithms on every pattern and prints a side-by-side comparison table.

### 3. Similarity check

```bash
python main.py similarity --dir ./sample_code
```

Computes pairwise LCS-based similarity scores; flags pairs above 0.70 as
potential copy-paste.

### 4. Demo file access

```bash
python main.py demo-access --file ./sample_code/main_sample.py
```

Reads the first 5 lines sequentially, then jumps directly to lines 10, 30, 55
using `file.seek()`, explaining both access methods.

---

## Algorithm Explanations

### Naive vs Horspool

| Property | Naive | Horspool |
|---|---|---|
| Preprocessing | None | O(m) shift table |
| Best case | O(n) | O(n/m) |
| Worst case | O(n·m) | O(n·m) |
| Typical speedup | 1× | 3–8× on natural text |

**Naive** slides the pattern one position at a time and compares character by
character — simple but wasteful.

**Horspool** (a simplification of Boyer-Moore) preprocesses the pattern into a
*bad-character shift table*. When a mismatch occurs it consults the character
currently under the pattern's last position in the text and jumps forward by
the precomputed amount — often several characters at once.

---

## File Access Explanations

### Sequential Access

`filesystem/sequential.py` — yields `(line_number, line_text)` one at a time
without loading the whole file. Mirrors a forward-only stream (magnetic tape,
unbuffered pipe): to reach line N you must read lines 1 … N-1 first.

### Direct / Random Access

`filesystem/direct.py` — `build_line_index()` makes a single sequential pass
to record the byte offset of every line's first byte. After that,
`direct_read(filepath, index, line_number)` calls `file.seek(offset)` to jump
instantly to that line — O(1) retrieval per call, analogous to an OS looking
up a disk block via an inode or FAT entry.

**In the scan flow both methods are used together:**
- Sequential access drives the per-line pattern-matching pass.
- Direct access fetches the ±2 surrounding lines for each violation's context.
