"""JSON output utilities for CLI — structured events on stdout, logs on stderr."""

import json
import sys


def emit(event: str, **data):
    """Print a JSON event line to stdout. Logs go to stderr."""
    obj = {"event": event, **data}
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def emit_error(message: str, code: int = 1):
    """Print an error event and exit."""
    emit("error", message=message)
    sys.exit(code)
