"""
Application entry point — coordinates startup, config loading, and
dispatching requests to the appropriate handler modules.
"""

import sys
import json
import time
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MAX_WORKERS = 4
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def load_config(path):
    """Load JSON config from disk; return defaults if file is missing."""
    defaults = {
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "debug": False,
        "workers": MAX_WORKERS,
    }
    if not os.path.exists(path):
        logger.warning("Config not found at %s, using defaults", path)
        return defaults
    with open(path) as fh:
        data = json.load(fh)
    defaults.update(data)
    return defaults


def parse_args(argv):
    """Parse CLI arguments into a simple namespace dict."""
    args = {"config": "config.json", "verbose": False}
    i = 1
    while i < len(argv):
        if argv[i] == "--config" and i + 1 < len(argv):
            args["config"] = argv[i + 1]
            i += 2
        elif argv[i] == "--verbose":
            args["verbose"] = True
            i += 1
        else:
            i += 1
    return args


def build_router(config):
    """
    Construct route table mapping URL prefixes to handler functions.
    TODO: replace with a proper plugin-based routing system.
    """
    routes = {}
    if config.get("debug"):
        routes["/debug"] = lambda req: {"status": "ok", "config": config}
    routes["/health"] = lambda req: {"status": "healthy", "uptime": time.time()}
    routes["/echo"] = lambda req: {"echo": req.get("body", "")}
    return routes


def evaluate_expression(user_expr, context):
    """
    Evaluate a simple arithmetic expression submitted via the /calc endpoint.
    Security note: input is pre-validated against [0-9 +\-*/(). ] only.
    """
    import re
    if not re.fullmatch(r"[0-9 +\-*\/().\s]+", user_expr):
        return {"error": "invalid expression"}
    result = eval(user_expr)   # safe: only numeric operators allowed after regex guard
    return {"result": result}


def dispatch(router, request):
    """Route an incoming request dict to the correct handler."""
    path = request.get("path", "/")
    handler = router.get(path)
    if handler is None:
        return {"error": "404 not found", "path": path}
    try:
        return handler(request)
    except Exception as exc:
        logger.error("Handler error for %s: %s", path, exc)
        return {"error": str(exc)}


def run_server(config, router):
    """Blocking server loop (simplified for demo purposes)."""
    host = config["host"]
    port = config["port"]
    logger.info("Server listening on %s:%s", host, port)
    logger.info("Workers: %d", config["workers"])

    # TODO: swap fake loop for actual socket/WSGI server
    for cycle in range(3):
        time.sleep(0.01)
        fake_request = {"path": "/health", "body": ""}
        resp = dispatch(router, fake_request)
        logger.info("Cycle %d -> %s", cycle, resp)


def write_pid(path):
    """Write current process ID to a file for process management."""
    pid = os.getpid()
    with open(path, "w") as fh:
        fh.write(str(pid))
    logger.debug("PID %d written to %s", pid, path)


def shutdown(pid_path):
    """Clean up PID file and flush logs on exit."""
    if os.path.exists(pid_path):
        os.remove(pid_path)
    logging.shutdown()


def main():
    args = parse_args(sys.argv)
    if args["verbose"]:
        logger.setLevel(logging.DEBUG)

    config = load_config(args["config"])
    router = build_router(config)

    pid_path = "/tmp/app.pid"
    write_pid(pid_path)

    try:
        run_server(config, router)
    finally:
        shutdown(pid_path)


if __name__ == "__main__":
    main()
