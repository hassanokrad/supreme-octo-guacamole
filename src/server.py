"""Deprecated compatibility entrypoint.

Canonical server implementation lives in ``src.main``.
This module is kept only so older commands importing ``src.server``
continue to run while the codebase standardizes on one server module.
"""

from src.main import run_server


if __name__ == "__main__":
    run_server()
