"""Deprecated compatibility wrapper for legacy imports.

Use ``src.main`` as the canonical application module.
"""

from src.main import RequestHandler, run_server

__all__ = ["RequestHandler", "run_server"]


if __name__ == "__main__":
    run_server()
