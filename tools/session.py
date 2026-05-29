"""Session lifecycle tools: start/stop/status/health/host."""

from __future__ import annotations

from mcp.types import Tool

TOOLS = [
    Tool(
        name="start_session",
        description=(
            "Start a persistent Vivado TCL session. Must be called before "
            "project/design tools. Vivado startup is ~30s; the session is "
            "reused across tool calls."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "vivado_path": {
                    "type": "string",
                    "description": "Path to vivado(.bat) executable (default: 'vivado' from PATH).",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="stop_session",
        description="Stop the Vivado TCL session and free resources.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="session_status",
        description="Get statistics for the current Vivado session (commands run, timing, errors).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="check_session_health",
        description=(
            "Verify the Vivado process is responsive. With auto_recover=true "
            "the session is restarted if it hangs."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "auto_recover": {
                    "type": "boolean",
                    "description": "Restart session if unhealthy (default: true)",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="get_host_status",
        description=(
            "Get host hostname, free memory, and session state. If free memory "
            "is below 64GB, switch to a beefier host for large designs."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


def _start_session(session, args):
    session.vivado_path = args.get("vivado_path", session.vivado_path or "vivado")
    r = session.start()
    return {"success": r.success, "message": r.output, "elapsed_ms": r.elapsed_ms}


def _stop_session(session, args):
    r = session.stop()
    return {"success": r.success, "message": r.output}


def _session_status(session, args):
    return session.get_stats()


def _check_session_health(session, args):
    auto_recover = args.get("auto_recover", True)
    if not session.is_running:
        if auto_recover:
            r = session.start()
            return {
                "healthy": r.success,
                "action": "started",
                "message": "Session was not running, started new session",
                "elapsed_ms": r.elapsed_ms,
            }
        return {"healthy": False, "action": "none", "message": "Session not running (auto_recover=false)"}

    if session.is_healthy():
        return {"healthy": True, "action": "none", "message": "Session is healthy and responsive"}

    if auto_recover:
        r = session.ensure_healthy()
        return {
            "healthy": r.success,
            "action": "restarted",
            "message": "Session was unresponsive, restarted",
            "elapsed_ms": r.elapsed_ms,
        }
    return {"healthy": False, "action": "none", "message": "Session is unresponsive (auto_recover=false)"}


def _get_host_status(session, args):
    import socket

    import psutil

    mem = psutil.virtual_memory()
    free_gb = mem.available / (1024 ** 3)
    return {
        "hostname": socket.gethostname(),
        "memory_free_gb": round(free_gb, 1),
        "memory_total_gb": round(mem.total / (1024 ** 3), 1),
        "memory_percent_used": mem.percent,
        "vivado_session_active": session.is_running,
        "suggestion": (
            f"Low memory ({free_gb:.1f}GB free). Use vivado-snoke instead."
            if free_gb < 64
            else None
        ),
    }


HANDLERS = {
    "start_session": _start_session,
    "stop_session": _stop_session,
    "session_status": _session_status,
    "check_session_health": _check_session_health,
    "get_host_status": _get_host_status,
}
