"""Shared helpers for tool implementations.

Every handler accepts `(session, arguments)` and returns a plain dict.
The dispatcher in `server.py` wraps the dict in `TextContent` for MCP.
"""

from __future__ import annotations

from typing import Callable

from ..vivado_session import VivadoSession

Handler = Callable[[VivadoSession, dict], dict]


def err(message: str, **extra) -> dict:
    return {"success": False, "error": message, **extra}


def require_args(args: dict, *names: str) -> dict | None:
    """Return an error dict if any named arg is missing/empty, else None."""
    missing = [n for n in names if not args.get(n)]
    if missing:
        return err(f"Missing required arguments: {', '.join(missing)}")
    return None


def require_project_open(session: VivadoSession) -> dict | None:
    """Return an error dict if Vivado is not running, else None.

    Project-presence is best detected via the TCL `current_project` query
    inside each tool that truly needs it; this helper only catches the
    common case where the user forgot `start_session`.
    """
    if not session.is_running:
        return err("Vivado session not running. Call start_session first.")
    return None


def tcl_brace(path: str) -> str:
    """Wrap a string in Tcl braces to handle paths with spaces safely."""
    return "{" + path + "}"
