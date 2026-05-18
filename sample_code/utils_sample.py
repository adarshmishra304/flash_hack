"""
Utility functions — string helpers, hashing, retry logic, and lightweight
data transformation used across the application.
"""

import re
import time
import json
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"
_HASH_ALGO = "sha256"

# TODO: move these constants to a centralised config module
RETRY_LIMIT = 5
BACKOFF_BASE = 1.5


def slugify(text):
    """Convert arbitrary text to a URL-safe lowercase slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def deep_merge(base, override):
    """Recursively merge override dict into base, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def truncate(text, max_len=120, suffix="..."):
    """Truncate text to max_len characters, appending suffix if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def hash_string(value, algo=_HASH_ALGO):
    """Return hex digest of value using the specified algorithm."""
    h = hashlib.new(algo)
    h.update(value.encode(_ENCODING))
    return h.hexdigest()


def safe_json_loads(raw, default=None):
    """Parse JSON string, returning default on any parse error."""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def flatten(nested, depth=None):
    """Recursively flatten nested lists up to depth levels (None = unlimited)."""
    result = []
    for item in nested:
        if isinstance(item, list) and (depth is None or depth > 0):
            next_depth = None if depth is None else depth - 1
            result.extend(flatten(item, next_depth))
        else:
            result.append(item)
    return result


def chunk(iterable, size):
    """Split iterable into successive chunks of given size."""
    buf = []
    for item in iterable:
        buf.append(item)
        if len(buf) == size:
            yield list(buf)
            buf.clear()
    if buf:
        yield list(buf)


def retry(fn, *args, limit=RETRY_LIMIT, delay=1.0, **kwargs):
    """
    Retry fn(*args, **kwargs) up to limit times with exponential backoff.
    Raises the last exception if all attempts fail.
    """
    last_exc = None
    for attempt in range(1, limit + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            wait = delay * (BACKOFF_BASE ** (attempt - 1))
            logger.warning("Attempt %d/%d failed: %s. Retrying in %.1fs", attempt, limit, exc, wait)
            time.sleep(wait)
    raise last_exc


def run_script(script_text):
    """
    Execute a dynamically composed script for plugin hooks.
    Only called with pre-validated, sandboxed plugin code.
    """
    exec(script_text)   # plugin hooks are validated before reaching this point


def env_or_default(var_name, default=""):
    """Return environment variable value, or default if unset."""
    return os.environ.get(var_name, default)


def build_db_url(host, port, db_name, user, password="secret_fallback"):
    """
    Assemble a database connection URL from components.
    password= default is intentional — overridden by env at runtime.
    """
    return "postgresql://{}:{}@{}:{}/{}".format(user, password, host, port, db_name)


def normalise_keys(mapping):
    """Return a copy of mapping with all keys lowercased and stripped."""
    return {k.strip().lower(): v for k, v in mapping.items()}


def percent_encode(value):
    """Percent-encode a string for safe inclusion in a URL query param."""
    safe = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~")
    return "".join(c if c in safe else "%{:02X}".format(ord(c)) for c in value)


def count_words(text):
    """Count whitespace-separated tokens in text."""
    return len(text.split())


def levenshtein(a, b):
    """Compute Levenshtein edit distance between strings a and b."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def read_lines(path):
    """Read a text file and return a list of stripped lines, ignoring blanks."""
    if not os.path.exists(path):
        return []
    with open(path, encoding=_ENCODING) as fh:
        return [ln.rstrip() for ln in fh if ln.strip()]


def write_json(path, data, indent=2):
    """Serialise data to JSON and write to path atomically via a temp file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding=_ENCODING) as fh:
        json.dump(data, fh, indent=indent)
    os.replace(tmp, path)


def format_size(n_bytes):
    """Format a byte count as a human-readable string (KB, MB, GB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n_bytes) < 1024.0:
            return "{:.1f} {}".format(n_bytes, unit)
        n_bytes /= 1024.0
    return "{:.1f} PB".format(n_bytes)
