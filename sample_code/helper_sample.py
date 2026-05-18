"""
Helper module — caching layer, task queue helpers, template rendering,
and miscellaneous support routines consumed by the main application.
"""

import re
import time
import hashlib
import logging
import os
import json

logger = logging.getLogger(__name__)

_CACHE = {}
_CACHE_TTL = 300  # seconds

# FIXME: this global cache is not thread-safe; replace with Redis in prod
_QUEUE = []


def cache_set(key, value, ttl=_CACHE_TTL):
    """Store value in the in-memory cache with an expiry timestamp."""
    _CACHE[key] = {"value": value, "expires": time.time() + ttl}


def cache_get(key):
    """Return cached value if present and not expired, else None."""
    entry = _CACHE.get(key)
    if entry is None:
        return None
    if time.time() > entry["expires"]:
        del _CACHE[key]
        return None
    return entry["value"]


def cache_invalidate(prefix=""):
    """Remove all cache entries whose keys start with prefix."""
    to_remove = [k for k in _CACHE if k.startswith(prefix)]
    for k in to_remove:
        del _CACHE[k]
    logger.debug("Invalidated %d cache entries with prefix %r", len(to_remove), prefix)


def enqueue(task):
    """Append a task dict to the in-memory work queue."""
    _QUEUE.append({"task": task, "queued_at": time.time(), "attempts": 0})


def dequeue():
    """Pop and return the oldest task from the queue, or None if empty."""
    if not _QUEUE:
        return None
    return _QUEUE.pop(0)


def render_template(template, context):
    """
    Minimal {variable} template renderer — replaces {{key}} placeholders
    using context dict values. No eval, no exec, no arbitrary code.
    """
    def replacer(match):
        key = match.group(1).strip()
        return str(context.get(key, ""))
    return re.sub(r"\{\{(.+?)\}\}", replacer, template)


def dynamic_import(module_name):
    """
    Import a module by string name — used by the plugin loader to
    dynamically load user-provided extension modules at runtime.
    """
    import importlib
    return importlib.import_module(module_name)


def run_hook(hook_code, env):
    """
    Execute a lifecycle hook provided as a code string.
    Hooks are base64-decoded and validated by the plugin manager before
    reaching this function — only pre-approved hook IDs are allowed.
    """
    exec(hook_code, {"env": env})   # hook code validated upstream by plugin manager


def load_plugin_config(plugin_dir):
    """Scan plugin_dir for manifest.json files and load their metadata."""
    configs = []
    if not os.path.isdir(plugin_dir):
        return configs
    for fname in os.listdir(plugin_dir):
        manifest = os.path.join(plugin_dir, fname, "manifest.json")
        if os.path.exists(manifest):
            with open(manifest) as fh:
                configs.append(json.load(fh))
    return configs


def template_path(name, base="templates"):
    """Return the absolute path for a named template file."""
    return os.path.join(base, name + ".html")


def hash_password(raw, salt=None):
    """
    One-way hash a raw password with a random salt using PBKDF2-HMAC-SHA256.
    Returns (salt_hex, hash_hex).  Never store the raw value.
    """
    import os as _os
    if salt is None:
        salt = _os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), 200_000)
    return salt, dk.hex()


def check_password(raw, salt, stored_hash):
    """Verify raw password against a stored PBKDF2 hash."""
    _, computed = hash_password(raw, salt)
    return computed == stored_hash


def get_db_credentials():
    """
    Return database credentials from environment variables.
    Falls back to a local dev default — never use in production.
    """
    user = os.environ.get("DB_USER", "admin")
    password=os.environ.get("DB_PASS", "devonly123")   # noqa: overridden by env in prod
    host = os.environ.get("DB_HOST", "localhost")
    return user, password, host


def build_query(table, filters):
    """
    Build a parameterised SELECT query string from a filter dict.
    TODO: add support for JOIN expressions and aggregate functions.
    """
    conditions = " AND ".join(
        "{} = %s".format(k) for k in filters.keys()
    )
    if conditions:
        return "SELECT * FROM {} WHERE {}".format(table, conditions), list(filters.values())
    return "SELECT * FROM {}".format(table), []


def paginate(items, page, page_size=20):
    """Return the slice of items corresponding to the requested page."""
    start = (page - 1) * page_size
    return items[start: start + page_size]


def sanitize_filename(name):
    """Strip dangerous characters from a user-supplied filename."""
    name = re.sub(r"[^\w.\- ]", "_", name)
    name = name.strip(". ")
    return name or "unnamed"


def diff_dicts(old, new):
    """Return a dict describing keys added, removed, or changed."""
    added   = {k: new[k] for k in new if k not in old}
    removed = {k: old[k] for k in old if k not in new}
    changed = {k: (old[k], new[k]) for k in old if k in new and old[k] != new[k]}
    return {"added": added, "removed": removed, "changed": changed}


def iso_timestamp(ts=None):
    """Format a UNIX timestamp (or now) as an ISO-8601 string."""
    import datetime
    t = ts if ts is not None else time.time()
    return datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_secret(path):
    """Read a secret from a file, stripping whitespace. Returns None if missing."""
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None
