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


def run_design_cmd(session: VivadoSession, cmd: str, timeout: float | None = None):
    """Run a command that needs an open design (report_*), opening one if needed.

    After launch_runs / wait_on_run only checkpoints exist on disk, so a plain
    report right after a build fails with "No open design". In that case open
    the most advanced completed run (impl_1, else synth_1) and retry. The run
    that was opened is recorded on the result as `opened_run`.
    """
    r = session.run_tcl(cmd, timeout_override=timeout)
    r.opened_run = None
    if r.success or "No open design" not in r.output:
        return r
    for run in ("impl_1", "synth_1"):
        o = session.run_tcl(
            f'if {{[get_property -quiet PROGRESS [get_runs -quiet {run}]] eq "100%"}} '
            f'{{open_run {run}; set mcp_opened ok}} else {{set mcp_opened skip}}',
            timeout_override=900,
        )
        if o.success and o.output.strip().endswith("ok"):
            retry = session.run_tcl(cmd, timeout_override=timeout)
            retry.opened_run = run
            return retry
    return r


def tcl_brace(path: str) -> str:
    """Wrap a string in Tcl braces to handle paths with spaces safely."""
    return "{" + path + "}"
